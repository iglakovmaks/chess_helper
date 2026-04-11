#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_NAME="ChessHelper"
APP_SRC="$ROOT_DIR/dist/${APP_NAME}.app"
VOL_NAME="ChessHelper"
OUT_DMG="$ROOT_DIR/release/${APP_NAME}.dmg"
TMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/chesshelper-dmg.XXXXXX")"
TMP_DMG="$TMP_DIR/${APP_NAME}-rw.dmg"
BG_SWIFT="$TMP_DIR/make_bg.swift"
BG_PNG="$TMP_DIR/background.png"
FONT_TTF="$ROOT_DIR/Righteous-Regular.ttf"
MOUNT_DIR="/Volumes/${VOL_NAME}"
DEVICE=""

cleanup() {
  if [[ -n "$DEVICE" ]]; then
    hdiutil detach "$DEVICE" -force >/dev/null 2>&1 || true
  fi
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

if [[ ! -d "$APP_SRC" ]]; then
  echo "Не найдено приложение: $APP_SRC" >&2
  exit 1
fi

mkdir -p "$ROOT_DIR/release"

if mount | grep -q "on ${MOUNT_DIR} "; then
  hdiutil detach "$MOUNT_DIR" -force >/dev/null 2>&1 || true
fi

cat > "$BG_SWIFT" <<'SWIFT'
import AppKit
import CoreText
import Foundation

let args = CommandLine.arguments
guard args.count >= 2 else {
    fputs("Missing output path\\n", stderr)
    exit(1)
}

let outputPath = args[1]
let width: CGFloat = 720
let height: CGFloat = 460
let size = NSSize(width: width, height: height)
let fontPath = args.count >= 3 ? args[2] : ""

if !fontPath.isEmpty {
    let fontURL = URL(fileURLWithPath: fontPath)
    _ = CTFontManagerRegisterFontsForURL(fontURL as CFURL, .process, nil)
}

let image = NSImage(size: size)
image.lockFocus()

NSColor(calibratedRed: 0x40/255.0, green: 0x43/255.0, blue: 0x4E/255.0, alpha: 1).setFill()
NSBezierPath(rect: NSRect(x: 0, y: 0, width: width, height: height)).fill()

let paragraph = NSMutableParagraphStyle()
paragraph.alignment = .center
let titleFont = NSFont(name: "Righteous", size: 64) ?? NSFont.systemFont(ofSize: 60, weight: .bold)
let titleAttrs: [NSAttributedString.Key: Any] = [
    .font: titleFont,
    .foregroundColor: NSColor(calibratedRed: 0xF8/255.0, green: 0xF4/255.0, blue: 0xEF/255.0, alpha: 1),
    .paragraphStyle: paragraph
]
("Chess Helper" as NSString).draw(
    in: NSRect(x: 0, y: 370, width: width, height: 72),
    withAttributes: titleAttrs
)

image.unlockFocus()

guard let tiffData = image.tiffRepresentation,
      let rep = NSBitmapImageRep(data: tiffData),
      let pngData = rep.representation(using: .png, properties: [:]) else {
    fputs("Failed to encode PNG\\n", stderr)
    exit(1)
}

let outputURL = URL(fileURLWithPath: outputPath)

do {
    try pngData.write(to: outputURL)
} catch {
    fputs("Failed to write PNG: \(error)\\n", stderr)
    exit(1)
}
SWIFT

swift "$BG_SWIFT" "$BG_PNG" "$FONT_TTF"

hdiutil create -ov -size 260m -fs HFS+ -volname "$VOL_NAME" -type UDIF "$TMP_DMG" >/dev/null
ATTACH_OUTPUT="$(hdiutil attach "$TMP_DMG" -readwrite -noverify -noautoopen)"
DEVICE="$(awk '/^\/dev\// {print $1; exit}' <<< "$ATTACH_OUTPUT")"

if [[ -z "$DEVICE" ]]; then
  echo "Не удалось подключить временный DMG" >&2
  exit 1
fi

cp -R "$APP_SRC" "$MOUNT_DIR/"
mkdir -p "$MOUNT_DIR/.background"
cp "$BG_PNG" "$MOUNT_DIR/.background/background.png"

osascript <<APPLE
 tell application "Finder"
   tell disk "$VOL_NAME"
     open
     if exists item "Applications" of container window then
       delete item "Applications" of container window
     end if
     make new alias file at container window to POSIX file "/Applications" with properties {name:"Applications"}
     set current view of container window to icon view
     set toolbar visible of container window to false
     set statusbar visible of container window to false
     set bounds of container window to {140, 120, 860, 580}
     set opts to the icon view options of container window
     set arrangement of opts to not arranged
     set icon size of opts to 128
      set text size of opts to 14
     set background picture of opts to file ".background:background.png"
     set position of item "${APP_NAME}.app" of container window to {190, 260}
     set position of item "Applications" of container window to {520, 260}
     update without registering applications
     delay 1
     close
     open
     delay 1
   end tell
 end tell
APPLE

bless --folder "$MOUNT_DIR" --openfolder "$MOUNT_DIR" >/dev/null 2>&1 || true
sync

hdiutil detach "$DEVICE" -force >/dev/null
DEVICE=""

hdiutil convert "$TMP_DMG" -format UDZO -imagekey zlib-level=9 -ov -o "$OUT_DMG" >/dev/null

echo "Готово: $OUT_DMG"

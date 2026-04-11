from __future__ import annotations

import argparse
import os
import platform
import shutil
import stat
import subprocess
import sys
import zipfile
from pathlib import Path

APP_NAME = "ChessHelper"
UI_FONT_FILE = "Righteous-Regular.ttf"


def configure_console_output() -> None:
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if stream is None:
            continue
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def run(cmd: list[str], *, cwd: Path) -> None:
    print(f"$ {' '.join(cmd)}")
    subprocess.run(cmd, cwd=cwd, check=True)


def find_stockfish(explicit_path: str | None) -> Path:
    if explicit_path:
        candidate = Path(explicit_path).expanduser().resolve()
        if candidate.exists():
            return candidate
        raise FileNotFoundError(f"Stockfish не найден по пути: {candidate}")

    env_path = os.environ.get("STOCKFISH_PATH")
    if env_path:
        candidate = Path(env_path).expanduser().resolve()
        if candidate.exists():
            return candidate

    for name in ("stockfish", "stockfish.exe"):
        from_path = shutil.which(name)
        if from_path:
            return Path(from_path).resolve()

    raise FileNotFoundError(
        "Stockfish не найден. Установите stockfish в PATH, "
        "или передайте --stockfish, или задайте STOCKFISH_PATH."
    )


def resolve_bundle_targets(dist_dir: Path) -> list[Path]:
    app_dir = dist_dir / APP_NAME
    app_bundle = dist_dir / f"{APP_NAME}.app"
    targets: list[Path] = []

    if app_dir.exists():
        targets.append(app_dir)
    if app_bundle.exists():
        targets.append(app_bundle / "Contents" / "MacOS")

    if targets:
        return targets

    raise FileNotFoundError(
        f"Не найден результат сборки в {dist_dir}. Ожидался {app_dir} или {app_bundle}."
    )


def resolve_icon_source(root: Path, explicit_icon: str | None) -> Path | None:
    if explicit_icon:
        icon_path = Path(explicit_icon).expanduser().resolve()
        if not icon_path.exists():
            raise FileNotFoundError(f"Иконка не найдена: {icon_path}")
        return icon_path

    default_icon = root / "icon.png"
    if default_icon.exists():
        return default_icon.resolve()

    return None


def prepare_icon_for_platform(root: Path, icon_source: Path) -> Path:
    system_name = platform.system().lower()
    suffix = icon_source.suffix.lower()

    if system_name == "darwin":
        if suffix == ".icns":
            return icon_source
        if suffix != ".png":
            raise ValueError("Для macOS используйте .png или .icns")

        if not shutil.which("sips") or not shutil.which("iconutil"):
            raise RuntimeError("Для конвертации иконки на macOS нужны утилиты sips и iconutil")

        temp_root = root / ".icon_build"
        iconset_dir = temp_root / "AppIcon.iconset"
        if temp_root.exists():
            shutil.rmtree(temp_root)
        iconset_dir.mkdir(parents=True, exist_ok=True)

        for size in (16, 32, 64, 128, 256, 512):
            out_1x = iconset_dir / f"icon_{size}x{size}.png"
            out_2x = iconset_dir / f"icon_{size}x{size}@2x.png"
            run(
                [
                    "sips",
                    "-z",
                    str(size),
                    str(size),
                    str(icon_source),
                    "--out",
                    str(out_1x),
                ],
                cwd=root,
            )
            run(
                [
                    "sips",
                    "-z",
                    str(size * 2),
                    str(size * 2),
                    str(icon_source),
                    "--out",
                    str(out_2x),
                ],
                cwd=root,
            )

        icns_path = temp_root / f"{APP_NAME}.icns"
        run(
            [
                "iconutil",
                "-c",
                "icns",
                str(iconset_dir),
                "-o",
                str(icns_path),
            ],
            cwd=root,
        )
        return icns_path

    if system_name.startswith("win"):
        if suffix == ".ico":
            return icon_source
        if suffix == ".png":
            try:
                from PIL import Image
            except Exception as exc:
                raise ValueError(
                    "Для Windows нужен .ico. Установите Pillow (`python -m pip install pillow`) "
                    "или передайте --icon с .ico файлом."
                ) from exc

            temp_root = root / ".icon_build"
            temp_root.mkdir(parents=True, exist_ok=True)
            ico_path = temp_root / f"{APP_NAME}.ico"
            with Image.open(icon_source) as src:
                src.convert("RGBA").save(
                    ico_path,
                    format="ICO",
                    sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
                )
            return ico_path
        raise ValueError("Для Windows используйте .ico или .png (автоконвертация в .ico).")

    # На Linux PyInstaller использует переданный путь как есть.
    return icon_source


def zip_dist(target_path: Path, release_dir: Path) -> Path:
    system_name = platform.system().lower()
    machine = platform.machine().lower().replace(" ", "")
    archive_name = f"{APP_NAME}-{system_name}-{machine}.zip"
    archive_path = release_dir / archive_name

    release_dir.mkdir(parents=True, exist_ok=True)
    if archive_path.exists():
        archive_path.unlink()

    base_parent = target_path.parent
    with zipfile.ZipFile(archive_path, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        if target_path.is_file():
            archive.write(target_path, target_path.name)
        else:
            for item in sorted(target_path.rglob("*")):
                if item.is_dir():
                    continue
                arcname = item.relative_to(base_parent)
                archive.write(item, arcname)

    return archive_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Собрать ChessHelper как desktop-приложение (PyInstaller)"
    )
    parser.add_argument(
        "--stockfish",
        type=str,
        default=None,
        help="Путь к бинарнику Stockfish (если не указан, ищется в STOCKFISH_PATH/PATH)",
    )
    parser.add_argument(
        "--icon",
        type=str,
        default=None,
        help="Путь к иконке приложения. Если не указать, будет использован icon.png (если есть).",
    )
    parser.add_argument(
        "--no-zip",
        action="store_true",
        help="Не упаковывать сборку в zip-архив",
    )
    return parser.parse_args()


def main() -> None:
    configure_console_output()
    args = parse_args()
    root = Path(__file__).resolve().parent
    dist_dir = root / "dist"
    build_dir = root / "build"
    spec_file = root / f"{APP_NAME}.spec"
    icon_source = resolve_icon_source(root, args.icon)
    icon_path: Path | None = None

    stockfish_src = find_stockfish(args.stockfish)
    print(f"Stockfish: {stockfish_src}")
    if icon_source is not None:
        icon_path = prepare_icon_for_platform(root, icon_source)
        print(f"Иконка: {icon_path}")
    else:
        print("Иконка: не задана (сборка без custom icon)")

    for path in (dist_dir, build_dir):
        if path.exists():
            shutil.rmtree(path)
    if spec_file.exists():
        spec_file.unlink()

    pyinstaller_check = subprocess.run(
        [sys.executable, "-m", "PyInstaller", "--version"],
        cwd=root,
        capture_output=True,
        text=True,
    )
    if pyinstaller_check.returncode != 0:
        raise RuntimeError(
            "PyInstaller не найден в текущем Python. Установите: python -m pip install pyinstaller"
        )

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onedir",
        "--windowed",
        "--name",
        APP_NAME,
        "app.py",
    ]
    if icon_path is not None:
        cmd.extend(["--icon", str(icon_path)])
    font_file = root / UI_FONT_FILE
    if font_file.exists():
        data_sep = ";" if platform.system().lower().startswith("win") else ":"
        cmd.extend(["--add-data", f"{font_file}{data_sep}."])
        print(f"Добавлен шрифт: {font_file.name}")

    run(cmd, cwd=root)

    target_dirs = resolve_bundle_targets(dist_dir)
    stockfish_name = "stockfish.exe" if platform.system().lower().startswith("win") else "stockfish"
    copied_paths: list[Path] = []

    for target_dir in target_dirs:
        stockfish_dst = target_dir / stockfish_name
        shutil.copy2(stockfish_src, stockfish_dst)

        if platform.system().lower() != "windows":
            mode = stockfish_dst.stat().st_mode
            stockfish_dst.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

        copied_paths.append(stockfish_dst)

    print("Скопирован движок:")
    for dst in copied_paths:
        print(f"  - {dst}")

    if not args.no_zip:
        app_bundle = dist_dir / f"{APP_NAME}.app"
        app_dir = dist_dir / APP_NAME
        package_root = app_bundle if app_bundle.exists() else app_dir
        archive_path = zip_dist(package_root, root / "release")
        print(f"Готов архив: {archive_path}")

    print("Сборка завершена.")
    print(f"Результат: {dist_dir}")


if __name__ == "__main__":
    main()

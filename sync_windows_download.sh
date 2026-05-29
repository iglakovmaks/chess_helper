#!/usr/bin/env bash
set -euo pipefail

REPO="iglakovmaks/chess_helper"
RELEASE_TAG="windows-latest"
ASSET_NAME="ChessHelper-Setup.exe"
TARGET_SETUP="website/downloads/ChessHelper-Setup.exe"

if ! command -v gh >/dev/null 2>&1; then
  echo "gh CLI not found. Install GitHub CLI first." >&2
  exit 1
fi

TMP_DIR=$(mktemp -d)
trap 'rm -rf "${TMP_DIR}"' EXIT

gh release download "${RELEASE_TAG}" \
  --repo "${REPO}" \
  -p "${ASSET_NAME}" \
  -D "${TMP_DIR}"

SRC_SETUP=$(find "${TMP_DIR}" -type f -name "${ASSET_NAME}" | head -n 1)
if [[ -z "${SRC_SETUP}" ]]; then
  echo "${ASSET_NAME} not found in release '${RELEASE_TAG}'" >&2
  exit 1
fi

mkdir -p "$(dirname "${TARGET_SETUP}")"
cp -f "${SRC_SETUP}" "${TARGET_SETUP}"

echo "Updated: ${TARGET_SETUP}"
ls -lh "${TARGET_SETUP}"
shasum -a 256 "${TARGET_SETUP}"

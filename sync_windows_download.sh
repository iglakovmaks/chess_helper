#!/usr/bin/env bash
set -euo pipefail

REPO="iglakovmaks/chess_helper_archive_20260413"
WORKFLOW_NAME="Build Windows Release"
ARTIFACT_NAME="ChessHelper-windows"
TARGET="website/downloads/ChessHelper-windows-amd64.zip"

if ! command -v gh >/dev/null 2>&1; then
  echo "gh CLI not found. Install GitHub CLI first." >&2
  exit 1
fi

RUN_ID="${1:-}"
if [[ -z "${RUN_ID}" ]]; then
  RUN_ID=$(gh run list \
    --repo "${REPO}" \
    --workflow "${WORKFLOW_NAME}" \
    --limit 20 \
    --json databaseId,status,conclusion \
    --jq '.[] | select(.status=="completed" and .conclusion=="success") | .databaseId' \
    | head -n 1)
fi

if [[ -z "${RUN_ID}" ]]; then
  echo "No successful runs found for workflow '${WORKFLOW_NAME}'" >&2
  exit 1
fi

echo "Using run: ${RUN_ID}"

TMP_DIR=$(mktemp -d)
trap 'rm -rf "${TMP_DIR}"' EXIT

gh run download "${RUN_ID}" \
  --repo "${REPO}" \
  -n "${ARTIFACT_NAME}" \
  -D "${TMP_DIR}"

SRC=$(find "${TMP_DIR}" -type f -name "ChessHelper-windows-amd64.zip" | head -n 1)
if [[ -z "${SRC}" ]]; then
  echo "ChessHelper-windows-amd64.zip not found inside artifact" >&2
  exit 1
fi

mkdir -p "$(dirname "${TARGET}")"
cp -f "${SRC}" "${TARGET}"

echo "Updated: ${TARGET}"
ls -lh "${TARGET}"
shasum -a 256 "${TARGET}"

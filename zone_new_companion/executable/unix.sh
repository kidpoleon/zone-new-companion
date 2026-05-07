#!/usr/bin/env bash
set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_ROOT="$(cd "${APP_DIR}/.." && pwd)"

export QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-wayland}"

# Prefer a bundled PyInstaller binary when present.
BIN_CANDIDATES=(
  "${REPO_ROOT}/dist/zone-new-companion"
  "${REPO_ROOT}/dist/zone-new-companion.exe"
  "${REPO_ROOT}/zone_new_companion"
)

for candidate in "${BIN_CANDIDATES[@]}"; do
  if [[ -f "${candidate}" && -x "${candidate}" ]]; then
    if ! "${candidate}" "$@"; then
      export QT_QPA_PLATFORM="xcb"
      exec "${candidate}" "$@"
    fi
  fi
done

# Fallback to running from source.
cd "${REPO_ROOT}"
if [[ -f ".venv/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source ".venv/bin/activate"
fi

if ! python3 main.py "$@"; then
  export QT_QPA_PLATFORM="xcb"
  exec python3 main.py "$@"
fi


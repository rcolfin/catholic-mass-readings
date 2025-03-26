#!/usr/bin/env bash

# Removes old conda, poetry, uv and micromamba installations

PYTHON_ROOT_PATH=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )/.." &> /dev/null && pwd )

PATHS_TO_REMOVE=(
    ~/.cache/conda
    ~/.cache/pip
    ~/.cache/pypoetry
    ~/.cache/uv
    ~/.cache/pre-commit
    ~/.local/bin/micromamba
    ~/micromamba
)

function log() {
    >&2 echo "$(date '+%Y-%m-%d %H:%M:%S') ${*}"
}

set -euo pipefail

VENV_PATHS=$(find "${PYTHON_ROOT_PATH}" -name ".venv" -prune | tr '\n' ' ')
IFS=' ' read -ra VENV_PATHS_TO_REMOVE <<< "$VENV_PATHS"
PATHS_TO_REMOVE+=("${VENV_PATHS_TO_REMOVE[@]}")

for PATH_TO_REMOVE in "${PATHS_TO_REMOVE[@]}"
do
    if [ -e "${PATH_TO_REMOVE}" ]; then
        log "rm -rf ${PATH_TO_REMOVE}"
        rm -rf "${PATH_TO_REMOVE}"
    fi
done

#!/usr/bin/env bash

# Resolves and updates the lock file for all the dependencies across all the uv enabled Python packages.

set -euo pipefail

SCRIPT_PATH=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
SCRIPT_NAME=$( basename "${BASH_SOURCE[0]}" )
PYTHON_ROOT_PATH=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )/.." &> /dev/null && pwd )

if ! command -v "uv" &> /dev/null; then
    exec "${SCRIPT_PATH}/console.sh" "${SCRIPT_PATH}/${SCRIPT_NAME}"
fi

# shellcheck disable=SC2207
PACKAGE_PATHS=$(find "${PYTHON_ROOT_PATH}" -maxdepth 2 -name "pyproject.toml" -not -path '*.venv*' -exec dirname {} \;)
FAILED=()

for PACKAGE_PATH in ${PACKAGE_PATHS}; do
    PACKAGE_NAME=$(basename "${PACKAGE_PATH}")
    pushd "${PACKAGE_PATH}" >/dev/null ||  { FAILED+=("${PACKAGE_NAME}"); continue; }
    uv lock || { FAILED+=("${PACKAGE_NAME}"); }
    popd >/dev/null || { continue; }
done

if [ ${#FAILED[@]} -gt 0 ]; then
    >&2 echo "The following packages failed to lock: ${FAILED[*]}"
    exit 1
fi

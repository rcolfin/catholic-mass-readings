#!/usr/bin/env bash

SCRIPT_PATH=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
PACKAGE_NAME=$(basename "$(pwd)")

if grep -q uv "pyproject.toml" >/dev/null 2>&1; then
    echo "Installing dependencies for ${PACKAGE_NAME}..."
    exec "${SCRIPT_PATH}/console.sh" uv lock --no-update
fi

>&2 echo "No uv dependencies available for ${PACKAGE_NAME}."
exit 1

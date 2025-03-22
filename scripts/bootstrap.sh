#!/usr/bin/env bash

SCRIPT_PATH=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

if grep -q uv "pyproject.toml" >/dev/null 2>&1; then
    echo "Installing dependencies for $(basename "$(pwd)")..."
    exec "${SCRIPT_PATH}/console.sh" uv sync
fi

>&2 echo "No uv dependencies available for $(basename "$(pwd)")."
exit 1

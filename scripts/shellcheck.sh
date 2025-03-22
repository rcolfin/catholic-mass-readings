#!/usr/bin/env bash

# Runs shell check against all scripts

set -euo pipefail

ROOT_PATH=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )/.." &> /dev/null && pwd )

SCRIPTS=$(find "${ROOT_PATH}" -type f -name '*.sh' -not -path '*.venv*')

pushd "${ROOT_PATH}" >/dev/null

for SCRIPT in ${SCRIPTS}; do
    echo uvx --from shellcheck-py shellcheck "${SCRIPT}"
    uvx --from shellcheck-py shellcheck "${SCRIPT}"
done

popd >/dev/null

#!/usr/bin/env bash

set -euo pipefail

function log() {
    >&2 echo "${@}"
}

# shellcheck disable=SC2016
PACKAGE_PATHS=$(git diff --name-only --cached --diff-filter=ACMR \
                    | tr "/" " " \
                    | awk '{print $1}' \
                    | xargs -l sh -c 'find "$0" -type f -name pyproject.toml -printf "%h\n"')

if [ -z "${PACKAGE_PATHS}" ]; then
    log "No Python packages found."
    exit 0
fi

FAILED=()
for PACKAGE_PATH in ${PACKAGE_PATHS}; do
    PACKAGE_NAME=$(basename "${PACKAGE_PATH}")
    pushd "${PACKAGE_PATH}" >/dev/null ||  { FAILED+=("${PACKAGE_NAME}"); continue; }

    log "Running mypy $PWD"
    uv run --frozen "mypy" "." || { FAILED+=("${PACKAGE_NAME}"); }

    popd >/dev/null || { continue; }
done

if [ ${#FAILED[@]} -gt 0 ]; then
    log "The following packages failed to be checked: ${FAILED[*]}"
    exit 1
fi

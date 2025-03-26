#!/usr/bin/env bash

SCRIPT_PATH=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
SCRIPT_NAME=$( basename "${BASH_SOURCE[0]}" )
WORKING_PATH=$( cd -- "$PWD" &> /dev/null && pwd )

function run_cmd() {
    local CMD="$1"
    shift 1

    if uv run --frozen which "$CMD" &> /dev/null; then
        echo uv run --frozen "$CMD" "$@"
        uv run --frozen "$CMD" "$@"
    fi
}

if ! command -v "uv" &> /dev/null; then
    # shellcheck disable=SC2164
    cd "${WORKING_PATH}" >/dev/null 2>&1
    exec "${SCRIPT_PATH}/console.sh" "${SCRIPT_PATH}/${SCRIPT_NAME}"
fi

if command -v "ruff" &> /dev/null; then
    run_cmd ruff check "$WORKING_PATH" --fix
    run_cmd ruff format "$WORKING_PATH"
else
    run_cmd black "$WORKING_PATH"
    run_cmd isort "$WORKING_PATH"
fi

run_cmd mypy "$WORKING_PATH"
run_cmd pytest

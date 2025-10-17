#!/usr/bin/env bash

SCRIPT_PATH=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
SCRIPT_NAME=$(basename "${BASH_SOURCE[0]}")
BASH_SCRIPT_SOURCED=false
[[ "${BASH_SOURCE[0]}" != "${0}" ]] && BASH_SCRIPT_SOURCED=true
PYTHON_VERSION=3.14
export BASH_SILENCE_DEPRECATION_WARNING=1

function log() {
    >&2 echo "$(date '+%Y-%m-%d %H:%M:%S') ${*}"
}

function fail() {
    log ERROR "$@"
    if [ "${BASH_SCRIPT_SOURCED}" == true ]; then
        return 1
    fi
    exit 1
}

function install() {
    if [ -f ~/.local/bin/uv ]; then
        return 0
    fi

    curl -LsSf https://astral.sh/uv/install.sh | sh || { fail "Failed to install uv."; return 1; }
    export PATH="/home/rcolfin/.local/bin:$PATH"

    uv tool update-shell
    uv python install "${PYTHON_VERSION}" || { fail "Failed to install Python ${PYTHON_VERSION}."; return 1; }
}

function activate() {
    "${SCRIPT_PATH}/${SCRIPT_NAME}" || return 1
    # shellcheck disable=SC1090
    if [ -f ~/.bash_profile ]; then
        source ~/.bash_profile >/dev/null 2>&1
    elif [ -f ~/.bashrc ]; then
        source ~/.bashrc >/dev/null 2>&1
    fi

    if [ ! -f .venv/bin/activate ] && grep -q uv "pyproject.toml" >/dev/null 2>&1; then
        uv venv
    fi

    # shellcheck disable=SC1091
    [ -f .venv/bin/activate ] && source ".venv/bin/activate"
}

function main() {
    if [ "${BASH_SCRIPT_SOURCED}" == true ]; then
        activate
    else
        install
    fi
}

main

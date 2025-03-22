#!/usr/bin/env bash

SCRIPT_PATH=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
SCRIPT_NAME=$(basename "${BASH_SOURCE[0]}")
BASH_SCRIPT_SOURCED=false
[[ "${BASH_SOURCE[0]}" != "${0}" ]] && BASH_SCRIPT_SOURCED=true
PACKAGES=(uv pre-commit)
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

function get_mamba_exe() {
    local SCRIPT

    if [ -n "${MAMBA_EXE+x}" ] && [ -f "${MAMBA_EXE}" ]; then
        echo "${MAMBA_EXE}"
        return
    fi

    SCRIPT=$(cat <<EOF
if [ -f ~/.bash_profile ]; then
    source ~/.bash_profile >/dev/null 2>&1
elif [ -f ~/.bashrc ]; then
    source ~/.bashrc >/dev/null 2>&1
fi
exec echo "\$MAMBA_EXE"
EOF
)

    exec /bin/bash --init-file <(echo "$SCRIPT")
}

function get_mamba_root_prefix() {
    local SCRIPT

    if [ -n "${MAMBA_ROOT_PREFIX+x}" ] && [ -d "${MAMBA_ROOT_PREFIX}" ]; then
        echo "${MAMBA_ROOT_PREFIX}"
        return
    fi

    SCRIPT=$(cat <<EOF
if [ -f ~/.bash_profile ]; then
    source ~/.bash_profile >/dev/null 2>&1
elif [ -f ~/.bashrc ]; then
    source ~/.bashrc >/dev/null 2>&1
fi
exec echo "\$MAMBA_ROOT_PREFIX"
EOF
)

    exec /bin/bash --init-file <(echo "$SCRIPT")
}

function install() {
    local MAMBA_EXE
    local MAMBA_ROOT_PREFIX

    MAMBA_EXE=$(get_mamba_exe)
    MAMBA_ROOT_PREFIX=$(get_mamba_root_prefix)

    if [ -z "${MAMBA_EXE+x}" ] || [ ! -f "${MAMBA_EXE}" ] || [ -z "${MAMBA_ROOT_PREFIX:+x}" ] || [ ! -d "${MAMBA_ROOT_PREFIX}" ]; then
        "${SCRIPT_PATH}/install-micromamba.sh" || { fail "Failed to install micromamba."; return 1; }
        MAMBA_EXE=$(get_mamba_exe)
        MAMBA_ROOT_PREFIX=$(get_mamba_root_prefix)
    fi

    export MAMBA_ROOT_PREFIX

    eval "$("${MAMBA_EXE}" shell hook --shell bash)" || { fail "Failed to install shell hooks."; return 1; }

    "micromamba" activate || { fail "Failed to activate micromamba."; return 1; }

    local MISSING_PACKAGES
    local PACKAGE

    MISSING_PACKAGES=()
    for PACKAGE in "${PACKAGES[@]}"; do
        if "micromamba" list | grep -q "${PACKAGE}"; then
            continue
        fi

        MISSING_PACKAGES+=("${PACKAGE}")
    done

    if [  ${#MISSING_PACKAGES[@]} -le 0 ]; then
        return  # all packages are present.
    fi

    mkdir -p ~/.mamba/pkgs
    log INFO "installing ${MISSING_PACKAGES[*]}."
    "micromamba" install "${MISSING_PACKAGES[@]}" -y -q || { fail "Failed to install ${MISSING_PACKAGES[*]}."; return 1; }
}

function activate() {
    "${SCRIPT_PATH}/${SCRIPT_NAME}" || return 1
    # shellcheck disable=SC1090
    if [ -f ~/.bash_profile ]; then
        source ~/.bash_profile >/dev/null 2>&1
    elif [ -f ~/.bashrc ]; then
        source ~/.bashrc >/dev/null 2>&1
    fi
    "micromamba" activate
}

function main() {
    if [ "${BASH_SCRIPT_SOURCED}" == true ]; then
        activate
    else
        install
    fi
}

main

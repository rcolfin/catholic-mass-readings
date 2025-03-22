#!/usr/bin/env bash

SCRIPT_PATH=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

SCRIPT=$(cat <<EOF
source "${SCRIPT_PATH}/setup-uv.sh"
[ "$#" -gt 0 ] && exec $@
EOF
)

exec /bin/bash --init-file <(echo "$SCRIPT")

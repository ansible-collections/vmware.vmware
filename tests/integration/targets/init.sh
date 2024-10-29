#!/usr/bin/env bash
# shellcheck disable=SC2155,SC2086

export DEFAULT_COLLECTIONS_PATH="$ANSIBLE_COLLECTIONS_PATH/ansible_collections"

export ANSIBLE_TURBO_LOOKUP_TTL=1
export ENABLE_TURBO_MODE=1


# Check if the variable is already set (e.g., in CI)
if [ -z "$ANSIBLE_COLLECTIONS_PATH" ]; then
    # If not, use base collections path
    ANSIBLE_COLLECTIONS_PATH="$DEFAULT_COLLECTIONS_PATH"
fi

echo "ANSIBLE_COLLECTIONS_PATH: $ANSIBLE_COLLECTIONS_PATH"
BASE_DIR=$(dirname "$(realpath "${BASH_SOURCE[0]}")")
export ANSIBLE_ROLES_PATH=${BASE_DIR}

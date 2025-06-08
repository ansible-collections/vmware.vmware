#!/usr/bin/env bash

set -eux

teardown() {
    ansible-playbook teardown.yml
    rm -f "roles"
}

symlink_roles_path() {
    # ansible-test copies what it *thinks* the test needs to a temp working directory.
    # This causes issues since this test uses runme.sh instead of a pseudo ansible role
    # with a meta/main.yml for dependencies. So we hack out a symlink to the other test
    # targets. Then the playbooks can import setup_* roles without issue
    currentDir="$(pwd)"
    case "$(pwd)" in
        # running via ansible-test
        *"tests/output/.tmp/integration"*)
            rolesPath=${currentDir%"/output/.tmp/integration"*};
            rolesPath="$rolesPath/integration/targets"
            ;;
        # running some other way, likely calling ./runme.sh
        *)
            rolesPath="$currentDir/.."
            ;;
    esac
    ln -s "$rolesPath/" "roles"
}

export ANSIBLE_INVENTORY_ENABLED=vmware.vmware.esxi_hosts
trap teardown EXIT

symlink_roles_path

# Generates a string starting with 'test-' followed by 4 random lowercase characters
tiny_prefix="test-vmware-$(uuidgen | tr -d '-' | cut -c1-4 | tr '[:upper:]' '[:lower:]')"

ansible-playbook "setup.yml" -e tiny_prefix="$tiny_prefix"
./test_session/vars.sh

ansible-playbook -i "files/test.esxi_hosts.yml" test.yml

teardown

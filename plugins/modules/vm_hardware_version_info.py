#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2026, Ansible Eco Content Team (github.com/eco-ansible-content)
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function
__metaclass__ = type


DOCUMENTATION = r'''
---
module: vm_hardware_version_info
short_description: Gather information about a VM's hardware version and any scheduled upgrades.
description:
    - This module is used to gather detailed information about a virtual machine's virtual hardware version.
    - Gather the current version, available versions, and information about pending upgrades for one VM.
    - If you just need the current version for multiple VMs, M(vmware.vmware.vm_info) is more efficient.

author:
    - Mike Morency (@mikemorency)

options:
    datacenter:
        description:
            - The name of the datacenter that contains the VM.
            - This is only used to build the full folder path when O(folder) is a relative path.
        type: str
        aliases: [ datacenter_name ]
    name:
        description:
            - The name of the VM to gather information about.
            - VM names in vCenter are not necessarily unique. If multiple VMs have the same name, use O(name_match)
              to select one, or use O(folder) to limit the search.
            - Exactly one of O(name), O(uuid), or O(moid) is required.
        type: str
    name_match:
        description:
            - If multiple VMs match the given name, use the first or last one found.
        default: first
        choices: [ first, last ]
        type: str
    uuid:
        description:
            - The UUID of the VM to gather information about.
            - By default, this is the BIOS UUID. Set O(use_instance_uuid) to V(true) to use the vCenter instance
              UUID instead.
            - Exactly one of O(name), O(uuid), or O(moid) is required.
        type: str
    moid:
        description:
            - The managed object ID (MOID) of the VM to gather information about, for example V(vm-1234).
            - The MOID is only unique within a single vCenter instance.
            - Exactly one of O(name), O(uuid), or O(moid) is required.
        type: str
    use_instance_uuid:
        description:
            - Whether O(uuid) is the vCenter instance UUID rather than the BIOS UUID.
        default: false
        type: bool
    folder:
        description:
            - The absolute or relative path of the folder to search for the VM.
            - This is used to narrow the search when O(name) or O(moid) is supplied. It is ignored when O(uuid) is used.
            - The path can be given with or without the C(<datacenter>/vm/) prefix,
              for example V(datacenter_name/vm/path/to/folder) or V(path/to/folder).
        type: str
        required: false
    folder_paths_are_absolute:
        description:
            - If true, any folder path parameters are treated as absolute paths.
            - If false, the module will try to determine whether the path is absolute or relative.
            - This option is useful when your environment has a complex folder structure and the module
              incorrectly prepends the datacenter name or other folder names to the path.
        type: bool
        required: false
        default: false

extends_documentation_fragment:
    - vmware.vmware.base_options
'''

EXAMPLES = r'''
- name: Gather hardware version info for a VM by name
  vmware.vmware.vm_hardware_version_info:
    name: app-server-01
  register: _hw_info

- name: Gather hardware version info for a VM in a specific folder
  vmware.vmware.vm_hardware_version_info:
    name: app-server-01
    folder: /DC01/vm/app-servers
  register: _hw_info

- name: Gather hardware version info using the VM MOID
  vmware.vmware.vm_hardware_version_info:
    moid: vm-1234
  register: _hw_info

- name: Gather hardware version info using the BIOS UUID
  vmware.vmware.vm_hardware_version_info:
    uuid: 4219a8ef-2b53-9f6e-4f0f-5b0c3e1b8d9a
  register: _hw_info

- name: Report the current version and scheduled upgrade status
  ansible.builtin.debug:
    msg: >-
      {{ _hw_info.current }} is the current version.
      Scheduled upgrade status is {{ _hw_info.scheduled_upgrade.status | default('not scheduled') }}.
'''

RETURN = r'''
vm:
    description:
        - Identifying information about the target VM.
    returned: always
    type: dict
    contains:
        moid:
            description:
                - The managed object ID of the VM.
            type: str
            sample: vm-79828
        name:
            description:
                - The name of the VM.
            type: str
            sample: test-d9c1-vm
current:
    description:
        - The current hardware version of the VM.
    returned: always
    type: str
    sample: vmx-19
available:
    description:
        - The hardware versions that this VM can be upgraded to, as reported by the VM's host.
        - This list is sorted from newest version to oldest version.
    returned: always
    type: list
    elements: str
    sample: ['vmx-21', 'vmx-20', 'vmx-19']
scheduled_upgrade:
    description:
        - Information about a hardware upgrade that is scheduled to happen the next time the VM is powered off.
        - This is an empty dictionary if no upgrade has been scheduled.
    returned: always
    type: dict
    contains:
        version:
            description:
                - The hardware version the VM will be upgraded to.
            type: str
            sample: vmx-21
        policy:
            description:
                - When the upgrade is allowed to run.
                - Typically V(onSoftPowerOff) (next guest power off) or V(always) (next power off).
            type: str
            sample: onSoftPowerOff
        status:
            description:
                - The status of the scheduled upgrade.
                - Typically V(none), V(pending), V(success), or V(failed).
            type: str
            sample: pending
        error:
            description:
                - Details about why the scheduled upgrade failed.
                - This is null if there was no failure.
            type: dict
            sample: {'message': 'Cannot upgrade the virtual hardware version.'}
            contains:
                message:
                    description:
                        - The localized message describing the failure.
                    type: str
'''
from ansible.module_utils.basic import AnsibleModule
from ansible_collections.vmware.vmware.plugins.module_utils._module_pyvmomi_base import (
    ModulePyvmomiBase
)
from ansible_collections.vmware.vmware.plugins.module_utils.argument_spec import (
    base_argument_spec
)


class VmHardwareInfoModule(ModulePyvmomiBase):
    def __init__(self, module):
        super().__init__(module)
        self.vm = self.get_vms_using_params(fail_on_missing=True)[0]

    def _get_all_supported_versions(self):
        config_option_descriptors = self.vm.environmentBrowser.QueryConfigOptionDescriptor()
        all_supported_versions = set()
        for option_desc in config_option_descriptors:
            if not option_desc.upgradeSupported:
                continue
            all_supported_versions.add(option_desc.key)

        return sorted(all_supported_versions, reverse=True)

    def _get_scheduled_upgrade_info(self):
        upgrade_info = getattr(self.vm.config, 'scheduledHardwareUpgradeInfo', None)
        if upgrade_info is None:
            return {}

        policy = upgrade_info.upgradePolicy
        if policy == 'never':
            return {}

        fault = getattr(upgrade_info, 'fault', None)
        if fault is not None:
            fault = {
                "message": fault.localizedMessage,
            }

        return {
            'version': upgrade_info.versionKey,
            'policy': policy,
            'status': upgrade_info.scheduledHardwareUpgradeStatus,
            'error': fault
        }

    def get_hardware_version_info(self):
        return {
            'current': self.vm.config.version,
            'available': self._get_all_supported_versions(),
            'scheduled_upgrade': self._get_scheduled_upgrade_info()
        }


def main():
    module = AnsibleModule(
        argument_spec={
            **base_argument_spec(),
            **dict(
                datacenter=dict(type='str', aliases=['datacenter_name']),
                name=dict(type='str', required=False),
                name_match=dict(type='str', choices=['first', 'last'], default='first'),
                uuid=dict(type='str'),
                moid=dict(type='str'),
                use_instance_uuid=dict(type='bool', default=False),
                folder=dict(type='str', required=False),
                folder_paths_are_absolute=dict(type='bool', required=False, default=False),
            )
        },
        supports_check_mode=True,
        mutually_exclusive=[
            ['name', 'uuid', 'moid']
        ],
        required_one_of=[
            ['name', 'uuid', 'moid']
        ],
    )

    vm_module = VmHardwareInfoModule(module)
    module.exit_json(
        **{
            'vm': {
                'moid': vm_module.vm._GetMoId(),
                'name': vm_module.vm.name
            }
        },
        **vm_module.get_hardware_version_info())


if __name__ == '__main__':
    main()

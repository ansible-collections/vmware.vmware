#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2025, Ansible Cloud Team (@ansible-collections)
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function
__metaclass__ = type


DOCUMENTATION = r'''
---
module: vm_advanced_settings
short_description: Manages the advanced settings for a VM
description:
    - Manages the advanced settings for a VM.
author:
    - Ansible Cloud Team (@ansible-collections)

options:
    datacenter:
        description:
            - The name of the datacenter to search for the VM.
            - This is only used if O(folder) is also used.
        type: str
        required: false
        aliases: [datacenter_name]
    state:
        description:
            - Set the state of the advanced settings on the VM.
            - If present, the specified advanced settings are added to the VM if they are missing or the value is incorrect.
            - If absent, the specified advanced settings are removed. If a setting is provided with an empty value,
              then the setting will be removed regardless of the current value on the VM.
            - If pure, the specified advanced settings will replace all advanced settings currently on the VM.
            - By default VMware will add settings to a VM when it is created. This module will manage those settings as well.
              If you use the pure state, be aware that it manages all settings on the VM, not just user defined ones.
        choices: [present, absent, pure]
        default: present
        type: str
    name:
        description:
            - Name of the virtual machine to work with.
            - Virtual machine names in vCenter are not necessarily unique, which may be problematic, see O(name_match).
            - This is required if O(moid) or O(uuid) is not supplied.
        type: str
    name_match:
        description:
            - If multiple virtual machines matching the name, use the first or last found.
        default: first
        choices: [ first, last ]
        type: str
    uuid:
        description:
            - UUID of the instance to manage if known, this is VMware's unique identifier.
            - This is required if O(name) or O(moid) is not supplied.
        type: str
    moid:
        description:
            - Managed Object ID of the instance to manage if known, this is a unique identifier only within a single vCenter instance.
            - This is required if O(name) or O(uuid) is not supplied.
        type: str
    use_instance_uuid:
        description:
            - Whether to use the VMware instance UUID rather than the BIOS UUID.
        default: false
        type: bool
    folder:
        description:
            - Destination folder, absolute or relative path to find an existing guest.
            - Should be the full folder path, with or without the 'datacenter/vm/' prefix
            - For example 'datacenter_name/vm/path/to/folder' or 'path/to/folder'
        type: str
        required: false
    settings:
        description:
            - A dictionary that describes the advanced settings you want to manage.
            - All settings values are converted to strings. The case of the string is taken into consideration when checking for changes.
              For example 'True' != 'TRUE'.
        type: dict
        required: true

extends_documentation_fragment:
    - vmware.vmware.base_options
'''

EXAMPLES = r'''
- name: Make Sure The Following Advanced Settings Are Present
    vmware.vmware.vm_advanced_settings:
    hostname: "{{ vcenter_hostname }}"
    username: "{{ vcenter_username }}"
    password: "{{ vcenter_password }}"
    validate_certs: false
    name: my-test-vm
    settings:
        one: 1
        two: 2
        three: 3
    state: present

- name: Remove The Following Advanced Settings
    vmware.vmware.vm_advanced_settings:
    hostname: "{{ vcenter_hostname }}"
    username: "{{ vcenter_username }}"
    password: "{{ vcenter_password }}"
    validate_certs: false
    name: "{{ vm }}"
    settings:
        one: 1    # remove advanced setting if it has both key == 'one' and value == 1
        two: ""   # remove any advanced setting with the key 'two', regardless of value
    state: absent

# Note: By default, VMware adds advanced settings to new VMs for things like pci bridges and VMware tools.
# Using state == pure means these settings will also be removed/managed.
- name: Remove All Advanced Settings
  vmware.vmware.vm_advanced_settings:
    hostname: "{{ vcenter_hostname }}"
    username: "{{ vcenter_username }}"
    password: "{{ vcenter_password }}"
    validate_certs: false
    name: "{{ vm }}"
    settings: {}
    state: pure

- name: Make Advanced Settings Match The Settings Below
  vmware.vmware.vm_advanced_settings:
    hostname: "{{ vcenter_hostname }}"
    username: "{{ vcenter_username }}"
    password: "{{ vcenter_password }}"
    validate_certs: false
    name: "{{ vm }}"
    settings:
      one: 1
      two: 2
      three: 3
    state: pure
'''

RETURN = r'''
vm:
    description:
        - Information about the target VM
    returned: On success
    type: dict
    sample:
        moid: vm-79828,
        name: test-d9c1-vm
'''

try:
    from pyVmomi import vim
except ImportError:
    pass

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils._text import to_native

from ansible_collections.vmware.vmware.plugins.module_utils._module_pyvmomi_base import (
    ModulePyvmomiBase
)
from ansible_collections.vmware.vmware.plugins.module_utils.argument_spec import (
    base_argument_spec
)
from ansible_collections.vmware.vmware.plugins.module_utils._type_utils import (
    convert_vmodl_option_set_to_py_dict,
    convert_py_primitive_to_vmodl_type
)
from ansible_collections.vmware.vmware.plugins.module_utils._vsphere_tasks import (
    RunningTaskMonitor,
    TaskError
)


class VmModule(ModulePyvmomiBase):
    REQUIRED_SETTINGS = {
        "svga.present": True
    }
    def __init__(self, module):
        super().__init__(module)
        self.vm = self.get_vms_using_params(fail_on_missing=True)[0]
        self.current_settings = convert_vmodl_option_set_to_py_dict(self.vm.config.extraConfig)
        self.new_settings = self.current_settings.copy()

    def convert_value_for_vim_option(self, value):
        try:
            return convert_py_primitive_to_vmodl_type(value, truthy_strings_as_bool=False)
        except TypeError:
            return value

    def __get_settings_to_remove(self):
        removed_settings = {}
        for remove_k, remove_v in self.params['settings'].items():
            if remove_k not in self.current_settings:
                continue

            if str(remove_v) and self.current_settings[remove_k] != str(remove_v):
                continue

            removed_settings[remove_k] = self.current_settings[remove_k]
            del self.new_settings[remove_k]

        return removed_settings

    def __get_settings_to_update(self):
        settings_to_update = {}
        for add_k, add_v in self.params['settings'].items():
            if add_k in self.current_settings and self.current_settings[add_k] == str(add_v):
                continue

            settings_to_update[add_k] = add_v
            self.new_settings[add_k] = add_v

        return settings_to_update

    def __get_pure_settings_changes(self):
        self.new_settings = self.params['settings'].copy()
        settings_to_update = self.params['settings'].copy()
        settings_to_remove = {}
        for current_k, current_v in self.current_settings.items():
            if current_k not in self.new_settings:
                settings_to_remove[current_k] = current_v
                continue

            if str(self.new_settings[current_k]) != current_v:
                settings_to_remove[current_k] = current_v
                continue

            del settings_to_update[current_k]

        return settings_to_update, settings_to_remove

    def get_settings_changes(self):
        settings_to_update, settings_to_remove = dict(), dict()
        if self.params['state'] == 'present':
            settings_to_update = self.__get_settings_to_update()
        elif self.params['state'] == 'absent':
            settings_to_remove = self.__get_settings_to_remove()
        else:
            settings_to_update, settings_to_remove = self.__get_pure_settings_changes()

        return settings_to_update, settings_to_remove

    def apply_new_settings(self):
        config_spec = vim.vm.ConfigSpec()
        config_spec.extraConfig = []
        for k, v in self.new_settings.items():
            option = vim.option.OptionValue()
            option.key = k
            option.value = self.convert_value_for_vim_option(v)
            config_spec.extraConfig.append(option)

        try:
            task = self.vm.ReconfigVM_Task(config_spec)
            _, task_result = RunningTaskMonitor(task).wait_for_completion()   # pylint: disable=disallowed-name
        except TaskError as err:
            self.module.fail_json(settings=self.new_settings, msg="Failed to update settings due to %s exception %s" % (type(err), to_native(err)))
        except Exception as generic_exc:
            self.module.fail_json(
                msg="Failed to update settings due to exception %s" % to_native(generic_exc),
                settings=self.new_settings
            )

        return task_result


def main():
    module = AnsibleModule(
        argument_spec={
            **base_argument_spec(), **dict(
                datacenter=dict(type='str', required=False, aliases=['datacenter_name']),
                state=dict(type='str', default='present', choices=['present', 'absent', 'pure']),
                name=dict(type='str'),
                name_match=dict(type='str', choices=['first', 'last'], default='first'),
                uuid=dict(type='str'),
                moid=dict(type='str'),
                use_instance_uuid=dict(type='bool', default=False),
                folder=dict(type='str', required=False),
                settings=dict(type='dict', required=True),
            )
        },
        supports_check_mode=True,
        mutually_exclusive=[
            ['name', 'uuid', 'moid'],
        ],
        required_one_of=[
            ['name', 'uuid', 'moid']
        ],
    )

    vm_module = VmModule(module)

    result = dict(
        vm=dict(name=vm_module.vm.name, moid=vm_module.vm._GetMoId()),
        changed=False,
        result=dict(),
        removed_settings=dict(),
        updated_settings=dict()
    )

    settings_to_update, settings_to_remove = vm_module.get_settings_changes()
    if settings_to_update or settings_to_remove:
        result['changed'] = True
        result['removed_settings'] = settings_to_remove
        result['updated_settings'] = settings_to_update
        result['new_settings'] = vm_module.new_settings
        if not module.check_mode:
            result['result'] = vm_module.apply_new_settings()

    module.exit_json(**result)


if __name__ == '__main__':
    main()

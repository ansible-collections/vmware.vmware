#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2025, Ansible Cloud Team (@ansible-collections)
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function
__metaclass__ = type


DOCUMENTATION = r'''
---
module: guest_custom_attributes
short_description: Manage custom attributes from VMware for the given virtual machine
description:
    - This module can be used to add, remove and update custom attributes for the given virtual machine.
author:
    - Ansible Cloud Team (@ansible-collections)
    - Lorenzo Andreasi (@lollo03)
options:
    name:
        description:
            - Name of the virtual machine to work with.
            - This is required parameter, if O(uuid) or O(moid) is not supplied.
        type: str
    state:
        description:
            - The action to take.
            - If set to V(present), then custom attribute is added or updated.
            - If set to V(absent), then custom attribute value is removed.
        default: 'present'
        choices: ['present', 'absent']
        type: str
    uuid:
        description:
            - UUID of the virtual machine to manage if known. This is VMware's unique identifier.
            - This is required parameter, if O(name) or O(moid) is not supplied.
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
            - Should be the full folder path, with or without the 'datacenter/vm/' prefix.
            - For example 'datacenter_name/vm/path/to/folder' or 'path/to/folder'.
            - This is required parameter, if O(name) is supplied and multiple virtual machines with same name are found.
        type: str
    datacenter:
        description:
            - Datacenter name where the virtual machine is located in.
        type: str
    folder_paths_are_absolute:
        description:
            - If true, any folder path parameters are treated as absolute paths.
            - If false, modules will try to intelligently determine if the path is absolute
              or relative.
            - This option is useful when your environment has a complex folder structure. By default,
              modules will try to intelligently determine if the path is absolute or relative.
              They may mistakenly prepend the datacenter name or other folder names, and this option
              can be used to avoid this.
        default: false
        type: bool
    attributes:
        description:
            - A dictionary of custom attributes to manage.
            - The keys are the attribute names, the values are the attribute values.
            - Values are not required and will be ignored if O(state=absent).
        default: {}
        type: dict

extends_documentation_fragment:
    - vmware.vmware.base_options
'''

EXAMPLES = r'''
- name: Add virtual machine custom attributes
  vmware.vmware.guest_custom_attributes:
    hostname: "{{ vcenter_hostname }}"
    username: "{{ vcenter_username }}"
    password: "{{ vcenter_password }}"
    uuid: 421e4592-c069-924d-ce20-7e7533fab926
    state: present
    attributes:
      MyAttribute: MyValue
  delegate_to: localhost
  register: attributes

- name: Add multiple virtual machine custom attributes
  vmware.vmware.guest_custom_attributes:
    hostname: "{{ vcenter_hostname }}"
    username: "{{ vcenter_username }}"
    password: "{{ vcenter_password }}"
    uuid: 421e4592-c069-924d-ce20-7e7533fab926
    state: present
    attributes:
      MyAttribute: MyValue
      MyAttribute2: MyValue2
  delegate_to: localhost
  register: attributes

- name: Remove virtual machine custom attribute
  vmware.vmware.guest_custom_attributes:
    hostname: "{{ vcenter_hostname }}"
    username: "{{ vcenter_username }}"
    password: "{{ vcenter_password }}"
    uuid: 421e4592-c069-924d-ce20-7e7533fab926
    state: absent
    attributes:
      MyAttribute:
  delegate_to: localhost
  register: attributes

- name: Remove virtual machine custom attribute using Virtual Machine MoID
  vmware.vmware.guest_custom_attributes:
    hostname: "{{ vcenter_hostname }}"
    username: "{{ vcenter_username }}"
    password: "{{ vcenter_password }}"
    moid: vm-42
    state: absent
    attributes:
      MyAttribute:
  delegate_to: localhost
  register: attributes
'''

RETURN = r'''
custom_attributes:
    description: metadata about the virtual machine custom attributes
    returned: always
    type: dict
    sample: {
        "mycustom": "my_custom_value",
        "mycustom_2": "my_custom_value_2",
        "sample_1": "sample_1_value",
        "sample_2": "sample_2_value",
        "sample_3": "sample_3_value"
    }
'''

try:
    from pyVmomi import vim
except ImportError:
    pass

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.vmware.vmware.plugins.module_utils._module_pyvmomi_base import (
    ModulePyvmomiBase
)
from ansible_collections.vmware.vmware.plugins.module_utils.argument_spec import (
    base_argument_spec
)


class VmCustomAttributesModule(ModulePyvmomiBase):
    def __init__(self, module):
        super().__init__(module)
        self.diff_config = dict(before={}, after={})
        self.result_fields = {}
        self.update_custom_attributes = []
        self.changed = False

    def _get_existing_attributes(self, user_attributes):
        existing_attributes = {}
        for field_def in self.custom_field_mgr:
            if field_def.managedObjectType not in (vim.VirtualMachine, None):
                continue
            if field_def.name in user_attributes:
                existing_attributes[field_def.name] = {
                    "key": field_def.key,
                    "name": field_def.name,
                    "value": "",
                }
        return existing_attributes

    def _populate_current_values(self, existing_attributes, vm):
        for vm_custom_value in vm.customValue:
            if vm_custom_value.name in existing_attributes:
                existing_attributes[vm_custom_value.name]["value"] = vm_custom_value.value

    def _compute_changes(self, existing_attributes, user_attributes):
        update_attributes = []
        user_attributes_for_diff = {}

        for attr_name, attr_value in user_attributes.items():
            if attr_name in existing_attributes:
                current_value = existing_attributes[attr_name]["value"]
                if attr_value != current_value:
                    update_attributes.append({
                        "name": attr_name,
                        "value": attr_value,
                        "key": existing_attributes[attr_name]["key"],
                    })
                user_attributes_for_diff[attr_name] = attr_value
            elif self.params['state'] == "present":
                update_attributes.append({
                    "name": attr_name,
                    "value": attr_value,
                })
                user_attributes_for_diff[attr_name] = attr_value

        return update_attributes, user_attributes_for_diff

    def check_exists(self, vm, user_attributes):
        existing_attributes = self._get_existing_attributes(user_attributes)
        self._populate_current_values(existing_attributes, vm)

        self.update_custom_attributes, user_attributes_for_diff = self._compute_changes(
            existing_attributes, user_attributes
        )

        if self.update_custom_attributes:
            self.changed = True

        self.diff_config['before']['custom_attributes'] = {
            name: attrs["value"]
            for name, attrs in sorted(existing_attributes.items())
        }
        self.diff_config['after']['custom_attributes'] = dict(
            sorted(user_attributes_for_diff.items())
        )

    def set_custom_field(self, vm, user_attributes):
        self.check_exists(vm, user_attributes)
        if self.module.check_mode:
            self.module.exit_json(changed=self.changed, diff=self.diff_config)

        for field in self.update_custom_attributes:
            if 'key' in field:
                self.content.customFieldsManager.SetField(entity=vm, key=field['key'], value=field['value'])
            else:
                field_key = self.content.customFieldsManager.AddFieldDefinition(
                    name=field['name'], moType=vim.VirtualMachine
                )
                self.content.customFieldsManager.SetField(entity=vm, key=field_key.key, value=field['value'])

            self.result_fields[field['name']] = field['value']

        return {'changed': self.changed, 'custom_attributes': self.result_fields}

    def remove_custom_field(self, vm, user_attributes):
        empty_attributes = dict.fromkeys(user_attributes, "")
        self.check_exists(vm, empty_attributes)
        if self.module.check_mode:
            self.module.exit_json(changed=self.changed, diff=self.diff_config)

        for field in self.update_custom_attributes:
            self.content.customFieldsManager.SetField(entity=vm, key=field['key'], value=field['value'])
            self.result_fields[field['name']] = field['value']

        return {'changed': self.changed, 'custom_attributes': self.result_fields}


def main():
    argument_spec = base_argument_spec()
    argument_spec.update(
        datacenter=dict(type='str'),
        name=dict(type='str'),
        folder=dict(type='str'),
        uuid=dict(type='str'),
        moid=dict(type='str'),
        use_instance_uuid=dict(type='bool', default=False),
        folder_paths_are_absolute=dict(type='bool', required=False, default=False),
        state=dict(type='str', default='present', choices=['absent', 'present']),
        attributes=dict(type='dict', default={}),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_one_of=[
            ['name', 'uuid', 'moid']
        ],
    )

    if module.params.get('folder'):
        module.params['folder'] = module.params['folder'].rstrip('/')

    pyv = VmCustomAttributesModule(module)
    results = {'changed': False}

    vm = pyv.get_vms_using_params(fail_on_missing=True)[0]
    if module.params['state'] == "present":
        results = pyv.set_custom_field(vm, module.params['attributes'])
    elif module.params['state'] == "absent":
        results = pyv.remove_custom_field(vm, module.params['attributes'])

    module.exit_json(**results)


if __name__ == '__main__':
    main()

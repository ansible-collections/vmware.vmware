#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2018, Ansible Project
# Copyright: (c) 2018, Abhijeet Kasurde <akasurde@redhat.com>
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
    - Jimmy Conner (@cigamit)
    - Abhijeet Kasurde (@Akasurde)
    - Ansible Cloud Team (@ansible-collections)
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
    attributes:
        description:
            - A list of name and value of custom attributes that needs to be managed.
            - Value of custom attribute is not required and will be ignored, if O(state=absent).
        suboptions:
            name:
                description:
                    - Name of the attribute.
                type: str
                required: true
            value:
                description:
                    - Value of the attribute.
                type: str
                default: ''
        default: []
        type: list
        elements: dict

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
      - name: MyAttribute
        value: MyValue
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
      - name: MyAttribute
        value: MyValue
      - name: MyAttribute2
        value: MyValue2
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
      - name: MyAttribute
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
      - name: MyAttribute
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

    def set_custom_field(self, vm, user_fields):
        self.check_exists(vm, user_fields)
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

        return {'changed': self.changed, 'failed': False, 'custom_attributes': self.result_fields}

    def remove_custom_field(self, vm, user_fields):
        for v in user_fields:
            v['value'] = ''

        self.check_exists(vm, user_fields)
        if self.module.check_mode:
            self.module.exit_json(changed=self.changed, diff=self.diff_config)

        for field in self.update_custom_attributes:
            self.content.customFieldsManager.SetField(entity=vm, key=field['key'], value=field['value'])
            self.result_fields[field['name']] = field['value']

        return {'changed': self.changed, 'failed': False, 'custom_attributes': self.result_fields}

    def check_exists(self, vm, user_fields):
        existing_custom_attributes = []
        for k, n in [
            (x.key, x.name) for x in self.custom_field_mgr
            if x.managedObjectType == vim.VirtualMachine or x.managedObjectType is None
            for v in user_fields
            if x.name == v['name']
        ]:
            existing_custom_attributes.append({
                "key": k,
                "name": n
            })

        for e in existing_custom_attributes:
            for v in vm.customValue:
                if e['key'] == v.key:
                    e['value'] = v.value

            if 'value' not in e:
                e['value'] = ''

        _user_fields_for_diff = []
        for v in user_fields:
            for e in existing_custom_attributes:
                if v['name'] == e['name'] and v['value'] != e['value']:
                    self.update_custom_attributes.append({
                        "name": v['name'],
                        "value": v['value'],
                        "key": e['key']
                    })

                if v['name'] == e['name']:
                    _user_fields_for_diff.append({
                        "name": v['name'],
                        "value": v['value']
                    })

            if v['name'] not in [x['name'] for x in existing_custom_attributes] and self.params['state'] == "present":
                self.update_custom_attributes.append(v)
                _user_fields_for_diff.append({
                    "name": v['name'],
                    "value": v['value']
                })

        if self.update_custom_attributes:
            self.changed = True

        self.diff_config['before']['custom_attributes'] = sorted(
            [x for x in existing_custom_attributes if x.pop('key', None)], key=lambda k: k['name']
        )
        self.diff_config['after']['custom_attributes'] = sorted(_user_fields_for_diff, key=lambda k: k['name'])


def main():
    argument_spec = base_argument_spec()
    argument_spec.update(
        datacenter=dict(type='str'),
        name=dict(type='str'),
        folder=dict(type='str'),
        uuid=dict(type='str'),
        moid=dict(type='str'),
        use_instance_uuid=dict(type='bool', default=False),
        state=dict(type='str', default='present', choices=['absent', 'present']),
        attributes=dict(
            type='list',
            default=[],
            elements='dict',
            options=dict(
                name=dict(type='str', required=True),
                value=dict(type='str', default=''),
            )
        ),
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
    results = {'changed': False, 'failed': False, 'instance': dict()}

    vm = pyv.get_vms_using_params(fail_on_missing=False)
    if not vm:
        vm_id = (module.params.get('name') or module.params.get('uuid') or module.params.get('moid'))
        module.fail_json(msg="Unable to manage custom attributes for non-existing"
                             " virtual machine %s" % vm_id)

    vm = vm[0]
    if module.params['state'] == "present":
        results = pyv.set_custom_field(vm, module.params['attributes'])
    elif module.params['state'] == "absent":
        results = pyv.remove_custom_field(vm, module.params['attributes'])

    module.exit_json(**results)


if __name__ == '__main__':
    main()

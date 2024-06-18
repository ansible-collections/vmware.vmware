#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2023, Ansible Cloud Team (@ansible-collections)
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: folder_template
short_description: Create a template in a local VCenter folder from an existing VM
description:
- >-
  This module creates a template in a local VCenter folder from an existing VM. The folder must already exist.
  The VM must be powered off, and is otherwise unchanged.
author:
- Ansible Cloud Team (@ansible-collections)
requirements:
- pyvmomi
options:
  vm_name:
    description:
      - The name of the vm to be used to create the template
    type: str
    required: True
  folder:
    description:
      - The name of the folder that the new template should be placed in
    type: str
    required: True
  name:
    description:
      - The name to give to the new template.
    type: str
  datastore:
    description:
      - The name of datastore to use as storage for the template.
    type: str
  resource_pool:
    description:
      - The resource pool to place the template in.
    type: str
  wait_for_template:
    description:
      - If true, the module will wait until the template is created to exit.
    type: bool
    default: True
attributes:
  check_mode:
    description: The check_mode support.
    support: full
extends_documentation_fragment:
- vmware.vmware.vmware.vcenter_documentation

'''

EXAMPLES = r'''
- name: Create A New Template Called my_vm_template
  vmware.vmware.folder_template:
    hostname: "https://vcenter"
    username: "username"
    password: "password"
    vm_name: "my_vm"
    folder: "my_templates"

- name: Create A New Template Called my_template
  vmware.vmware.folder_template:
    hostname: "https://vcenter"
    username: "username"
    password: "password"
    vm_name: "my_vm"
    name: "my_template"
    folder: "my_templates"
'''

RETURN = r'''
'''

import time
import traceback

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.vmware.vmware.plugins.module_utils.vmware import PyVmomi, vmware_argument_spec

PYVMOMI_IMP_ERR = None
try:
    from pyVmomi import vim
    HAS_PYVMOMI = True
except ImportError:
    PYVMOMI_IMP_ERR = traceback.format_exc()
    HAS_PYVMOMI = False


class VmwareFolderTemplate(PyVmomi):
    def __init__(self, module):
        super(VmwareFolderTemplate, self).__init__(module)

        self.vm_name = self.params.get("vm_name")
        self.name = self.params.get("name")
        if not self.name:
            self.name = self.vm_name + "_template"
        self.folder = self.params.get("folder")
        self.datastore = self.params.get("datastore")
        self.resource_pool = self.params.get("resource_pool")
        self.wait_for_template = self.params.get("wait_for_template")

    def check_if_template_exists(self):
        template = self.get_vm_by_name(self.name, fail_on_missing=False)
        if template:
            if template.config.template:
                return True
            else:
                self.module.fail_json("A virtual machine already exists with desired template name, %s." % self.name)

        return False

    def create_template_in_folder(self):
        vm = self.get_vm_by_name(self.vm_name, fail_on_missing=True)
        if vm.runtime.powerState != 'poweredOff':
            self.module.fail_json(msg="VM must be in powered off state before creating a template from it.")

        template_location_spec = self.__create_template_location_spec()
        template_spec = vim.vm.CloneSpec(powerOn=False, template=True, location=template_location_spec)
        folder = self.get_folder_by_name(self.folder, fail_on_missing=True)
        if self.module.check_mode:
            return

        task = vm.Clone(
            name=self.name,
            folder=folder,
            spec=template_spec)

        if self.wait_for_template:
            self.__wait_for_template(task)

    def __create_template_location_spec(self):
        template_location_spec = vim.vm.RelocateSpec()
        if self.datastore:
            template_location_spec.datastore = self.get_datastore_by_name(self.datastore, fail_on_missing=True)
        if self.resource_pool:
            template_location_spec.pool = self.get_resource_pool_by_name(self.resource_pool, fail_on_missing=True)

        return template_location_spec

    def __wait_for_template(self, task):
        """
        Waits and provides updates on a vSphere task
        """

        while task.info.state == vim.TaskInfo.State.running:
            time.sleep(2)

        if task.info.state == vim.TaskInfo.State.success:
            return
        else:
            self.module.fail_json(msg=task.info.error)


def main():
    module = AnsibleModule(
        argument_spec={
            **vmware_argument_spec(), **dict(
                vm_name=dict(
                    type='str',
                    required=True
                ),
                name=dict(
                    type='str',
                    required=False,
                    default=None
                ),
                folder=dict(
                    type='str',
                    required=True
                ),
                datastore=dict(
                    type='str',
                    required=False
                ),
                resource_pool=dict(
                    type='str',
                    required=False
                ),
                wait_for_template=dict(
                    type='bool',
                    required=False,
                    default=True
                ),
            )
        },
        supports_check_mode=True,
    )

    result = dict(
        changed=False,
    )

    folder_template = VmwareFolderTemplate(module)
    if not folder_template.check_if_template_exists():
        folder_template.create_template_in_folder()
        result['changed'] = True

    module.exit_json(**result)


if __name__ == '__main__':
    main()

#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2023, Ansible Cloud Team (@ansible-collections)
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function
__metaclass__ = type


DOCUMENTATION = r'''
---
module: guest_info
short_description: Gather guest information
description:
- This module gather vm guest information.
author:
- Ansible Cloud Team (@ansible-collections)
options:
  guest_username:
    description:
      - The username to be used to connect to guest vm and fetch environment info.
    type: str
  guest_password:
    description:
      - The password of the user to be used to connect to guest vm and fetch environment info.
    type: str
  guest_name:
    description:
      - The name of the guest virtual machine to obtain info from.
    type: str
attributes:
  check_mode:
    description: The check_mode support.
    support: full
extends_documentation_fragment:
- vmware.vmware.vmware_rest_client.documentation

'''

EXAMPLES = r'''
- name: Gather guest vm info
  vmware.vmware.guest_info:
    hostname: "https://vcenter"
    username: "username"
    password: "password"
    guest_name: "my_vm"
'''

RETURN = r'''
guest:
    description:
        - Information about guest.
    returned: On success
    type: list
    sample: [{
        "env": {},
        "family": "LINUX",
        "full_name": {
            "args": "[]",
            "default_message": "Red Hat Enterprise Linux 9 (64-bit)",
            "id": "vmsg.guestos.rhel9_64Guest.label",
            "localized": "None",
            "params": "None"
        },
        "host_name": "localhost.localdomain",
        "ip_address": "10.185.246.15",
        "name": "RHEL_9_64"
    }]
'''

from collections import defaultdict

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.vmware.vmware.plugins.module_utils.vmware import PyVmomi
from ansible_collections.vmware.vmware.plugins.module_utils.vmware_rest_client import VmwareRestClient


class VmwareGuestInfo(PyVmomi):
    def __init__(self, module):
        self.module = module
        self.params = module.params
        self.vmware_client = VmwareRestClient(module)

    def _get_env(self, vm):
        guest = self.vmware_client.api_client.vcenter.vm.guest
        try:
            return guest.Environment.list(
                vm=vm,
                credentials={
                    'type': 'USERNAME_PASSWORD',
                    'user_name': self.params.get('guest_username'),
                    'password': self.params.get('guest_password'),
                    'interactive_session': False
                },
                names=set()
            )
        except Exception:
            return {}

    def _get_identity(self, vm):
        r = defaultdict(dict)
        guest = self.vmware_client.api_client.vcenter.vm.guest
        try:
            identity = guest.Identity.get(vm=vm)
        except Exception:
            return None

        self._vvars(identity, r)
        return r

    def get_guest_info(self):
        guests = []

        if self.params.get('guest_name'):
            vms = self._get_vm(self.params.get('guest_name'))
        else:
            vms = self.vmware_client.api_client.vcenter.VM.list()

        for vm in vms:
            r = self._get_identity(str(vm.vm))
            if r is None:
                continue
            if self.params.get('guest_username') and self.params.get('guest_password'):
                r['env'] = self._get_env(str(vm.vm))

            guests.append(r)

        return guests

    def _vvars(self, vmware_obj, r):
        for k, v in vars(vmware_obj).items():
            if not k.startswith('_'):
                if hasattr(v, '__dict__') and not isinstance(v, str):
                    self._vvars(v, r[k])
                else:
                    r[k] = str(v)

    def _get_vm(self, vm_name):
        names = set([vm_name])
        vms = self.vmware_client.api_client.vcenter.VM.list(
            self.vmware_client.api_client.VM.FilterSpec(names=names)
        )

        if len(vms) == 0:
            return None

        return vms[0]


def main():
    argument_spec = VmwareRestClient.vmware_client_argument_spec()
    argument_spec.update(
        dict(
            guest_username=dict(type='str'),
            guest_password=dict(type='str', no_log=True),
            guest_name=dict(type='str'),
        )
    )
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_together=[
            ('guest_username', 'guest_password'),
        ],
    )

    vmware_appliance_mgr = VmwareGuestInfo(module)
    guests = vmware_appliance_mgr.get_guest_info()
    module.exit_json(changed=False, guests=guests)


if __name__ == '__main__':
    main()

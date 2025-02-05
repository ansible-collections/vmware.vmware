#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2023, Ansible Cloud Team (@ansible-collections)
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function
__metaclass__ = type


DOCUMENTATION = r'''
---
module: esxi_connection
short_description: Manage VMware ESXi host connection status in vCenter
description:
    - Manage VMware ESXi host connection status in vCenter. Disconnecting hosts temporarily
      disables monitoring for the host and it's VMs. However they will still show up in vCenter.
    - This module does not manage the addition, removal, or placement of hosts in vCenter.
      That functionality is in vmware.vmware.esxi_host

author:
    - Ansible Cloud Team (@ansible-collections)

seealso:
    - module: vmware.vmware.esxi_host

options:
    datacenter:
        description:
            - The name of the datacenter.
        type: str
        required: true
        aliases: [datacenter_name]
    esxi_host_name:
        description:
            - ESXi hostname to manage.
        required: true
        type: str
        aliases: [name]
    state:
        description:
            - Sets the connection status of the host in vCenter
        default: connected
        choices: ['connected', 'disconnected']
        type: str

extends_documentation_fragment:
    - vmware.vmware.base_options
'''

EXAMPLES = r'''
- name: Create Cluster
  vmware.vmware.cluster:
    hostname: '{{ vcenter_hostname }}'
    username: '{{ vcenter_username }}'
    password: '{{ vcenter_password }}'
    datacenter_name: datacenter
    cluster_name: cluster

- name: Delete Cluster
  vmware.vmware.cluster:
    hostname: "{{ vcenter_hostname }}"
    username: "{{ vcenter_username }}"
    password: "{{ vcenter_password }}"
    datacenter: datacenter
    name: cluster
    state: absent
'''

RETURN = r'''
cluster:
    description:
        - Identifying information about the cluster
        - If the cluster was removed, only the name is returned
    returned: On success
    type: dict
    sample: {
        "cluster": {
            "moid": "domain-c111111",
            "name": "example-cluster"
        },
    }
'''

try:
    from pyVmomi import vim, vmodl
except ImportError:
    pass

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils._text import to_native

from ansible_collections.vmware.vmware.plugins.module_utils._module_pyvmomi_base import (
    ModulePyvmomiBase
)
from ansible_collections.vmware.vmware.plugins.module_utils._vmware_argument_spec import (
    base_argument_spec
)
from ansible_collections.vmware.vmware.plugins.module_utils._vmware_tasks import (
    TaskError,
    RunningTaskMonitor
)


class VmwareHostConnection(ModulePyvmomiBase):
    def __init__(self, module):
        super().__init__(module)
        self.datacenter = self.get_datacenter_by_name_or_moid(self.params.get('datacenter'), fail_on_missing=True)
        self.host = self.get_esxi_host_by_name_or_moid(identifier=self.params['esxi_host_name'], fail_on_missing=True)

    def reconnect_host(self):
        reconnect_spec = vim.HostSystem.ReconnectSpec()
        reconnect_spec.syncState = True
        try:
            task = self.host.ReconnectHost_Task(reconnectSpec=reconnect_spec)
            _, task_result = RunningTaskMonitor(task).wait_for_completion()   # pylint: disable=disallowed-name
        except (vmodl.RuntimeFault, vmodl.MethodFault)as vmodl_fault:
            self.module.fail_json(msg=to_native(vmodl_fault.msg))
        except TaskError as task_e:
            self.module.fail_json(msg=to_native(task_e))
        except Exception as generic_exc:
            self.module.fail_json(msg=(
                "Failed to exit maintenance mode on %s due to exception %s" %
                (self.params['esxi_host_name'], to_native(generic_exc))
            ))

        return task_result

    def disconnect_host(self):
        try:
            task = self.host.DisconnectHost_Task()
            _, task_result = RunningTaskMonitor(task).wait_for_completion()   # pylint: disable=disallowed-name
        except (vmodl.RuntimeFault, vmodl.MethodFault)as vmodl_fault:
            self.module.fail_json(msg=to_native(vmodl_fault.msg))
        except TaskError as task_e:
            self.module.fail_json(msg=to_native(task_e))
        except Exception as generic_exc:
            self.module.fail_json(msg=(
                "Failed to disconnect host %s due to exception %s" %
                (self.params['esxi_host_name'], to_native(generic_exc))
            ))
        return task_result


def main():
    module = AnsibleModule(
        argument_spec={
            **base_argument_spec(), **dict(
                datacenter=dict(type='str', required=True, aliases=['datacenter_name']),
                state=dict(type='str', default='connected', choices=['connected', 'disconnected']),
                esxi_host_name=dict(type='str', required=True, aliases=['name']),
            )
        },
        supports_check_mode=True,
    )

    vmware_host_connection = VmwareHostConnection(module)
    result = dict(changed=False, host=dict(
        name=vmware_host_connection.host.name,
        moid=vmware_host_connection.host._GetMoId()
    ))
    if module.params['state'] == vmware_host_connection.host.runtime.connectionState:
        module.exit_json(**result)

    result['changed'] = True
    if module.check_mode:
        module.exit_json(**result)

    if module.params['state'] == 'disconnected':
        vmware_host_connection.disconnect_host()
    else:
        vmware_host_connection.reconnect_host()

    module.exit_json(**result)


if __name__ == '__main__':
    main()

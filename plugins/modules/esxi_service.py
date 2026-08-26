#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2024, Ansible Eco Content Team (@ansible-collections/eco-ansible-content)
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function
__metaclass__ = type


DOCUMENTATION = r'''
---
module: esxi_service
short_description: Manage the state and startup policy of a service on an ESXi host
description:
    - Start, stop, or restart a service on an ESXi host and/or manage its startup policy.
    - This module cannot create or remove services. The set of services available on an ESXi host
      is fixed, so this module only manages the state and startup policy of services that already exist.
author:
    - Ansible Eco Content Team (@ansible-collections/eco-ansible-content)

version_added: '2.10.0'

options:
    esxi_host_name:
        description:
            - Name of the ESXi host as defined in vCenter.
        required: true
        type: str
        aliases: ['name']
    service_name:
        description:
            - The key of the service to manage, for example V(ntpd) or V(TSM-SSH).
            - This must be a valid, existing ESXi service. The module fails if the service is not found.
        required: true
        type: str
    state:
        description:
            - The desired running state of the service.
            - If O(state=started), the service is started if it is not already running.
            - If O(state=stopped), the service is stopped if it is running.
            - If O(state=restarted), the service is always restarted, so the module always reports a change.
            - If this option is not set, the running state of the service is left unchanged. Omit it when
              you only want to manage O(service_policy).
        required: false
        type: str
        choices: ['started', 'stopped', 'restarted']
    service_policy:
        description:
            - The startup policy of the service.
            - If V(on), the service starts when the host starts up.
            - If V(automatic), the service starts only if it has open firewall ports, and stops when they are all closed.
            - If V(off), the service does not start when the host starts up.
        required: false
        type: str
        choices: ['automatic', 'off', 'on']


extends_documentation_fragment:
    - vmware.vmware.base_options
'''

EXAMPLES = r'''
- name: Start The NTP Service On A Host
  vmware.vmware.esxi_service:
    hostname: '{{ vcenter_hostname }}'
    username: '{{ vcenter_username }}'
    password: '{{ vcenter_password }}'
    name: my_esxi_host
    service_name: ntpd
    state: started

- name: Stop The NTP Service On A Host
  vmware.vmware.esxi_service:
    name: my_esxi_host
    service_name: ntpd
    state: stopped

- name: Restart The SSH Service On A Host
  vmware.vmware.esxi_service:
    name: my_esxi_host
    service_name: TSM-SSH
    state: restarted

- name: Set Only The Startup Policy Of A Service
  vmware.vmware.esxi_service:
    name: my_esxi_host
    service_name: ntpd
    service_policy: 'on'

- name: Start A Service And Enable It At Host Startup
  vmware.vmware.esxi_service:
    name: my_esxi_host
    service_name: ntpd
    state: started
    service_policy: 'on'
'''

RETURN = r'''
host:
    description:
        - Identifying information about the host.
    returned: always
    type: dict
    sample: {
        "host": {
            "moid": "host-111111",
            "name": "10.10.10.10"
        },
    }
'''

try:
    from pyVmomi import vim, vmodl
except ImportError:
    pass

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.common.text.converters import to_native

from ansible_collections.vmware.vmware.plugins.module_utils._module_pyvmomi_base import (
    ModulePyvmomiBase
)
from ansible_collections.vmware.vmware.plugins.module_utils.argument_spec import (
    base_argument_spec
)


class EsxiServiceModule(ModulePyvmomiBase):
    def __init__(self, module):
        """
        Resolves the ESXi host and the service to manage from the module params.
        Looks up the host by name or MOID, grabs its service system, and finds the
        target service. Fails the module if the host or service cannot be found.
        """
        super(EsxiServiceModule, self).__init__(module)
        self.host = self.get_esxi_host_by_name_or_moid(
            identifier=self.params['esxi_host_name'],
            fail_on_missing=True
        )
        self.service_system = self.host.configManager.serviceSystem
        self.service = self.get_service()

    def get_service(self):
        """
        Finds the service on the host that matches the user provided service_name.
        Returns:
            The matching vim.host.Service object. Fails the module if no service matches.
        """
        for service in self.service_system.serviceInfo.service:
            if service.key == self.params['service_name']:
                return service

        self.module.fail_json(msg=(
            "Unable to find service %s on ESXi host %s. Please check that you specified a valid service name. "
            "This module cannot create services." % (self.params['service_name'], self.params['esxi_host_name'])
        ))

    def ensure_state(self):
        """
        Applies the desired running state to the service if a change is needed.
        A restart is always treated as a change. Honors check mode.
        Returns:
            bool, True if the running state changed (or would change), otherwise False
        """
        state = self.params['state']
        if state == 'started':
            change_needed, service_call = not self.service.running, self.service_system.StartService
        elif state == 'stopped':
            change_needed, service_call = self.service.running, self.service_system.StopService
        elif state == 'restarted':
            change_needed, service_call = True, self.service_system.RestartService
        else:
            # state was not provided, so leave the running state untouched
            return False

        if change_needed and not self.module.check_mode:
            self.run_service_call(service_call, id=self.service.key)
        return change_needed

    def ensure_policy(self):
        """
        Applies the desired startup policy to the service if a change is needed. Honors check mode.
        Returns:
            bool, True if the policy changed (or would change), otherwise False
        """
        desired = self.params['service_policy']
        change_needed = desired is not None and self.service.policy != desired
        if change_needed and not self.module.check_mode:
            self.run_service_call(self.service_system.UpdateServicePolicy, id=self.service.key, policy=desired)
        return change_needed

    def run_service_call(self, service_call, **kwargs):
        """
        Runs a serviceSystem call, translating vSphere faults into a clean module failure.
        Args:
            service_call: the bound serviceSystem method to call, e.g. StartService
            kwargs: arguments to pass to the call, e.g. id=... or policy=...
        """
        try:
            service_call(**kwargs)
        except (vim.fault.InvalidState, vim.fault.NotFound, vim.fault.HostConfigFault,
                vmodl.fault.InvalidArgument, vmodl.RuntimeFault, vmodl.MethodFault) as fault:
            self.module.fail_json(msg=to_native(getattr(fault, 'msg', fault)))
        except Exception as generic_exc:
            self.module.fail_json(msg=(
                "Failed to manage service %s on host %s due to exception %s" %
                (self.params['service_name'], self.params['esxi_host_name'], to_native(generic_exc))
            ))


def main():
    module = AnsibleModule(
        argument_spec={
            **base_argument_spec(), **dict(
                esxi_host_name=dict(type='str', required=True, aliases=['name']),
                service_name=dict(type='str', required=True),
                state=dict(type='str', required=False, choices=['started', 'stopped', 'restarted']),
                service_policy=dict(type='str', required=False, choices=['automatic', 'off', 'on']),
            )
        },
        required_one_of=[
            ['state', 'service_policy'],
        ],
        supports_check_mode=True,
    )

    esxi_service = EsxiServiceModule(module)

    result = dict(
        changed=False,
        host=dict(
            name=module.params['esxi_host_name'],
            moid=esxi_service.host._GetMoId()
        )
    )

    state_changed = esxi_service.ensure_state()
    policy_changed = esxi_service.ensure_policy()
    result['changed'] = state_changed or policy_changed

    module.exit_json(**result)


if __name__ == '__main__':
    main()

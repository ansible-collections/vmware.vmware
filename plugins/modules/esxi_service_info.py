#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2026, Ansible Eco Content Team (github.com/eco-ansible-content)
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function
__metaclass__ = type


DOCUMENTATION = r'''
---
module: esxi_service_info
short_description: Gather information about the services on an ESXi host
description:
    - Gather information about the services available on an ESXi host, including each
      service's running state, startup policy, and source package.
author:
    - Mike Morency (@mikemorency)

version_added: '2.10.0'

options:
    esxi_host_name:
        description:
            - Name of the ESXi host as defined in vCenter.
        required: true
        type: str
        aliases: ['name']
    service_names:
        description:
            - A list of service keys to gather information about, for example V(ntpd) or V(TSM-SSH).
            - Only information about services in this list is returned.
            - If this option is not set or is empty, information about all services on the host is returned.
        required: false
        type: list
        elements: str


extends_documentation_fragment:
    - vmware.vmware.base_options
'''

EXAMPLES = r'''
- name: Gather Info About All Services On A Host
  vmware.vmware.esxi_service_info:
    hostname: '{{ vcenter_hostname }}'
    username: '{{ vcenter_username }}'
    password: '{{ vcenter_password }}'
    name: my_esxi_host
  register: host_services

- name: Gather Info About Specific Services On A Host
  vmware.vmware.esxi_service_info:
    name: my_esxi_host
    service_names:
      - ntpd
      - TSM-SSH
  register: host_services

- name: Print The Running State Of The NTP Service
  ansible.builtin.debug:
    msg: "ntpd running: {{ (host_services.services | selectattr('key', 'equalto', 'ntpd') | first).running }}"
'''

RETURN = r'''
host:
    description:
        - Identifying information about the host.
    returned: always
    type: dict
    sample: {
        "moid": "host-111111",
        "name": "10.10.10.10"
    }
exists:
    description:
        - Whether any services were returned.
        - This is V(false) when the host has no matching services, for example when O(service_names)
          only contains service keys that do not exist on the host.
    returned: always
    type: bool
    sample: true
services:
    description:
        - A list of the services on the host.
        - If O(service_names) is set, only the requested services are included.
    returned: always
    type: list
    elements: dict
    sample: [
        {
            "key": "DCUI",
            "label": "Direct Console UI",
            "policy": "on",
            "required": false,
            "running": true,
            "source_package_desc": "This VIB contains all of the base functionality of vSphere ESXi.",
            "source_package_name": "esx-base",
            "uninstallable": false
        },
        {
            "key": "ntpd",
            "label": "NTP Daemon",
            "policy": "off",
            "required": false,
            "running": false,
            "source_package_desc": "This VIB contains all of the base functionality of vSphere ESXi.",
            "source_package_name": "esx-base",
            "uninstallable": false
        }
    ]
'''

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.vmware.vmware.plugins.module_utils._module_pyvmomi_base import (
    ModulePyvmomiBase
)
from ansible_collections.vmware.vmware.plugins.module_utils.argument_spec import (
    base_argument_spec
)


class EsxiServiceInfoModule(ModulePyvmomiBase):
    def __init__(self, module):
        """
        Resolves the ESXi host to gather service information from, looking it up by
        name or MOID. Fails the module if the host cannot be found.
        """
        super(EsxiServiceInfoModule, self).__init__(module)
        self.host = self.get_esxi_host_by_name_or_moid(
            identifier=self.params['esxi_host_name'],
            fail_on_missing=True
        )

    def gather_service_info(self):
        """
        Gathers information about the services on the host, optionally filtered by the
        service_names provided by the user.
        Returns:
            A list of dicts. Each dict describes a single service.
        """
        service_names = self.params['service_names']
        services = []
        service_system = self.host.configManager.serviceSystem
        if service_system and service_system.serviceInfo:
            for service in service_system.serviceInfo.service:
                if service_names and service.key not in service_names:
                    continue
                services.append(self.service_to_dict(service))

        return services

    @staticmethod
    def service_to_dict(service):
        """
        Converts a vim.host.Service object into a serializable dict.
        Args:
            service: the vim.host.Service object to convert
        Returns:
            dict describing the service
        """
        return dict(
            key=service.key,
            label=service.label,
            policy=service.policy,
            running=service.running,
            required=service.required,
            uninstallable=service.uninstallable,
            source_package_name=service.sourcePackage.sourcePackageName if service.sourcePackage else None,
            source_package_desc=service.sourcePackage.description if service.sourcePackage else None,
        )


def main():
    module = AnsibleModule(
        argument_spec={
            **base_argument_spec(), **dict(
                esxi_host_name=dict(type='str', required=True, aliases=['name']),
                service_names=dict(type='list', elements='str', required=False),
            )
        },
        supports_check_mode=True,
    )

    esxi_service_info = EsxiServiceInfoModule(module)
    services = esxi_service_info.gather_service_info()

    module.exit_json(
        changed=False,
        exists=bool(services),
        host=dict(
            name=module.params['esxi_host_name'],
            moid=esxi_service_info.host._GetMoId()
        ),
        services=services
    )


if __name__ == '__main__':
    main()

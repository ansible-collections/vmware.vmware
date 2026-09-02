#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2026, Ansible Eco Content Team (github.com/eco-ansible-content)
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type


DOCUMENTATION = r"""
---
module: esxi_info
short_description: Gathers information about one or more ESXi hosts
description:
    - Gathers information about one or more ESXi hosts, such as CPU, memory, network, datastore,
      product, and vSAN details.
    - You can search for a single host by name or MOID, or gather information about all hosts,
      optionally limited to a specific cluster or datacenter.
author:
    - Mike Morency (@mikemorency)

version_added: '2.10.0'

options:
    esxi_host_name:
        description:
            - The name of the ESXi host on which to gather info.
            - If this option and O(moid) are not set, information about all hosts in scope is returned.
        type: str
        required: false
        aliases: [name]
    moid:
        description:
            - The managed object ID of the ESXi host on which to gather info.
            - If this option and O(name) are not set, information about all hosts in scope is returned.
        type: str
        required: false
    cluster:
        description:
            - The name of a cluster used to limit the hosts included when gathering information about all hosts.
            - This has no effect if O(name) or O(moid) is set.
        type: str
        required: false
        aliases: [cluster_name]
    datacenter:
        description:
            - The name of a datacenter used to limit the hosts included when gathering information about all hosts.
            - This has no effect if O(name) or O(moid) is set.
        type: str
        required: false
        aliases: [datacenter_name]
    gather_tags:
        description:
            - If true, gather any tags attached to the host(s).
            - This has no affect if the O(schema) is set to V(vsphere). In that case, add 'tag' to O(properties) or leave O(properties) unset.
        type: bool
        default: false
        required: false
    schema:
        description:
            - Specify the output schema desired.
            - The V(summary) output schema is the curated output from the module.
            - The V(vsphere) output schema is the vSphere API class definition.
        choices: ['summary', 'vsphere']
        default: 'summary'
        type: str
    properties:
        description:
            - If the schema is 'vsphere', gather these specific properties only.
        type: list
        elements: str

extends_documentation_fragment:
    - vmware.vmware.base_options
    - vmware.vmware.additional_rest_options
"""

EXAMPLES = r"""
- name: Gather Information About A Single Host
  vmware.vmware.esxi_info:
    hostname: '{{ vcenter_hostname }}'
    username: '{{ vcenter_username }}'
    password: '{{ vcenter_password }}'
    esxi_host_name: my_esxi_host

- name: Gather Information About All Hosts In A Datacenter
  vmware.vmware.esxi_info:
    datacenter: my_datacenter

- name: Gather Information About All Hosts In A Cluster With Their Tags
  vmware.vmware.esxi_info:
    cluster: my_cluster
    gather_tags: true

- name: Gather Specific Properties About A Host
  vmware.vmware.esxi_info:
    esxi_host_name: my_esxi_host
    schema: vsphere
    properties:
      - hardware.memorySize
      - config.product.version
      - overallStatus
"""

RETURN = r"""
hosts:
    description:
        - A list of dictionaries describing the hosts found by the search parameters.
        - When O(schema=summary), each dictionary contains the curated set of facts shown in the sample.
        - When O(schema=vsphere), each dictionary contains the vSphere API properties requested in O(properties).
    returned: always
    type: list
    elements: dict
    sample: [
        {
            "all_ipv4_addresses": [
                "10.10.10.10"
            ],
            "bios_release_date": "2011-01-01T00:00:00+00:00",
            "bios_version": "0.5.1",
            "cluster": "my_cluster",
            "connection_state": "connected",
            "cpu_cores": 2,
            "cpu_model": "Intel Xeon E312xx (Sandy Bridge)",
            "cpu_pkgs": 2,
            "cpu_threads": 2,
            "datacenter": "my_datacenter",
            "datastores": [
                {
                    "capacity": 13421772800,
                    "free_space": 12486443008,
                    "name": "datastore1"
                }
            ],
            "in_maintenance_mode": false,
            "interfaces": [
                {
                    "device": "vmk0",
                    "ipv4": {
                        "address": "10.10.10.10",
                        "netmask": "255.255.255.0"
                    },
                    "macaddress": "52:54:00:56:7d:59",
                    "mtu": 1500
                }
            ],
            "memory_free_mb": 2702,
            "memory_total_mb": 4095,
            "moid": "host-111111",
            "name": "10.10.10.10",
            "os_type": "vmnix-x86",
            "power_state": "poweredOn",
            "product_build": "4887370",
            "product_name": "VMware ESXi",
            "product_version": "6.5.0",
            "service_tag": "NA",
            "system_model": "KVM",
            "system_uuid": "4c4c4544-0052-3410-804c-b2c04f4e3632",
            "system_vendor": "Red Hat",
            "tags": [],
            "uptime": 1791680,
            "vsan_cluster_uuid": null,
            "vsan_health": "unknown",
            "vsan_node_uuid": null
        }
    ]
"""

try:
    from pyVmomi import vim
except ImportError:
    pass
from ansible.module_utils.basic import AnsibleModule
from ansible_collections.vmware.vmware.plugins.module_utils._module_pyvmomi_base import (
    ModulePyvmomiBase,
)
from ansible_collections.vmware.vmware.plugins.module_utils.argument_spec import (
    rest_compatible_argument_spec,
)
from ansible_collections.vmware.vmware.plugins.module_utils._module_rest_base import (
    ModuleRestBase,
)
from ansible_collections.vmware.vmware.plugins.module_utils.facts._converters import (
    vmware_obj_to_json,
)
from ansible_collections.vmware.vmware.plugins.module_utils.facts._esxi import EsxiFacts


class EsxiInfo(ModulePyvmomiBase):
    def __init__(self, module):
        super(EsxiInfo, self).__init__(module)
        self.rest_client = None
        if module.params["gather_tags"]:
            self.rest_client = ModuleRestBase(module)

    def get_hosts(self):
        """
        Gets the ESXi hosts matching the search parameters input by the user.
        Returns: List of hosts to gather info about
        """
        identifier = self.params.get("name") or self.params.get("moid")
        if identifier:
            return [
                self.get_esxi_host_by_name_or_moid(
                    identifier=identifier, fail_on_missing=True
                )
            ]

        if self.params.get("cluster"):
            cluster = self.get_cluster_by_name_or_moid(
                self.params.get("cluster"), fail_on_missing=True
            )
            return list(cluster.host)

        search_folder = None
        if self.params.get("datacenter"):
            datacenter = self.get_datacenter_by_name_or_moid(
                self.params.get("datacenter"), fail_on_missing=True
            )
            search_folder = datacenter.hostFolder

        return self.get_all_objs_by_type(
            [vim.HostSystem], folder=search_folder, recurse=True
        )

    def gather_info_for_hosts(self):
        """
        Gather information about one or more ESXi hosts
        """
        all_host_info = []
        for host in self.get_hosts():
            if self.params["schema"] == "summary":
                host_info = EsxiFacts(host).all_facts()
                host_info["tags"] = self._get_tags(host)
            else:
                try:
                    host_info = vmware_obj_to_json(host, self.params["properties"])
                except AttributeError as e:
                    self.module.fail_json(msg=str(e))

            all_host_info.append(host_info)

        return all_host_info

    def _get_tags(self, host):
        """
        Gets the tags on a host. Tags are formatted as a list of dictionaries corresponding to each tag
        """
        output = []
        if not self.params.get("gather_tags"):
            return output

        tags = self.rest_client.get_tags_by_host_moid(host._moId)
        for tag in tags:
            output.append(self.rest_client.format_tag_identity_as_dict(tag))

        return output


def main():
    module = AnsibleModule(
        argument_spec={
            **rest_compatible_argument_spec(),
            **dict(
                name=dict(type="str", required=False, aliases=["esxi_host_name"]),
                moid=dict(type="str", required=False),
                cluster=dict(type="str", required=False, aliases=["cluster_name"]),
                datacenter=dict(
                    type="str", required=False, aliases=["datacenter_name"]
                ),
                gather_tags=dict(type="bool", default=False),
                schema=dict(
                    type="str", choices=["summary", "vsphere"], default="summary"
                ),
                properties=dict(type="list", elements="str"),
            ),
        },
        supports_check_mode=True,
        mutually_exclusive=[("name", "moid")],
    )
    if module.params["schema"] != "vsphere" and module.params.get("properties"):
        module.fail_json(
            msg="The option 'properties' is only valid when the schema is 'vsphere'"
        )

    esxi_info = EsxiInfo(module)
    hosts = esxi_info.gather_info_for_hosts()
    module.exit_json(changed=False, hosts=hosts)


if __name__ == "__main__":
    main()

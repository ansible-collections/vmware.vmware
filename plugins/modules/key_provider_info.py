#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2026, Ansible Cloud Team (@ansible-collections)
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type


DOCUMENTATION = r"""
---
module: key_provider_info
short_description: Gather information about one or more key providers in a vCenter instance.
description:
    - This module allows you to gather information about one or more key providers in a vCenter instance.

author:
    - Ansible Cloud Team (@ansible-collections)

options:
    provider_name:
        description:
            - The name or ID of the key provider to gather information about.
            - If this is not provided, all key providers will be returned.
            - Only one of O(provider_name) or O(type) is allowed.
        type: str
        required: false
        aliases: [name, id]

    type:
        description:
            - The type of key provider to gather information about.
            - If this is not provided, all key provider types will be returned.
            - Only one of O(provider_name) or O(type) is allowed.
        type: str
        required: false
        choices: [standard, native]

extends_documentation_fragment:
    - vmware.vmware.base_options
"""

EXAMPLES = r"""
- name: Gather information about all key providers
  vmware.vmware.key_provider_info:
    hostname: "{{ vcenter_hostname }}"
    username: "{{ vcenter_username }}"
    password: "{{ vcenter_password }}"

- name: Gather information about a specific key provider
  vmware.vmware.key_provider_info:
    provider_name: my-standard-key-provider

- name: Gather information about native key providers only
  vmware.vmware.key_provider_info:
    type: native

- name: Gather information about standard key providers only
  vmware.vmware.key_provider_info:
    type: standard
"""

RETURN = r"""
key_providers:
    description:
        - Dictionary of key providers in the vCenter instance.
        - The key is the provider ID, the value is a dictionary with provider information.
        - Each provider includes id, type, and default.
        - Native providers also include backed_up and tpm_required.
        - Standard providers include a servers list with KMIP server details
          (id, address, port, username, proxy_address, proxy_port).
    returned: always
    type: dict
    sample: {
        "default-native-key-provider": {
            "backed_up": true,
            "default": true,
            "id": "default-native-key-provider",
            "type": "native",
            "tpm_required": true
        },
        "my-native-key-provider": {
            "backed_up": false,
            "default": false,
            "id": "my-native-key-provider",
            "tpm_required": true,
            "type": "native"
        },
        "my-standard-key-provider": {
            "default": false,
            "id": "my-standard-key-provider",
            "servers": [
                {
                    "address": "10.0.0.1",
                    "id": "kms-server-1",
                    "port": 5696,
                    "proxy_address": "10.0.0.2",
                    "proxy_port": 5697,
                    "username": "kmsuser"
                },
                {
                    "address": "10.0.0.3",
                    "id": "kms-server-2",
                    "port": 5696,
                    "proxy_address": "",
                    "proxy_port": null,
                    "username": ""
                }
            ],
            "type": "standard"
        }
    }
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.vmware.vmware.plugins.module_utils._module_pyvmomi_base import (
    ModulePyvmomiBase,
)
from ansible_collections.vmware.vmware.plugins.module_utils.argument_spec import (
    base_argument_spec,
)


class KeyProviderInfoModule(ModulePyvmomiBase):
    TYPE_MAP = {
        "nativeProvider": "native",
        "vCenter": "standard",
    }

    def __init__(self, module):
        super().__init__(module)
        self.crypto_manager = self.si.content.cryptoManager

    def kmip_server_to_dict(self, kmip_server):
        out = {
            "id": kmip_server.name,
            "address": kmip_server.address,
            "port": kmip_server.port,
            "username": kmip_server.userName,
            "proxy_address": kmip_server.proxyAddress,
            "proxy_port": kmip_server.proxyPort,
        }
        return out

    def kmip_cluster_to_dict(self, kmip_cluster):
        out = {
            "id": kmip_cluster.clusterId.id,
            "type": self.TYPE_MAP.get(kmip_cluster.managementType),
            "default": kmip_cluster.useAsDefault,
        }
        if getattr(kmip_cluster, "servers", None) is not None:
            out["servers"] = [
                self.kmip_server_to_dict(server) for server in kmip_cluster.servers
            ]

        if getattr(kmip_cluster, "tpmRequired", None) is not None:
            out["tpm_required"] = kmip_cluster.tpmRequired

        if getattr(kmip_cluster, "hasBackup", None) is not None:
            out["backed_up"] = kmip_cluster.hasBackup

        return out

    def gather_key_provider_info(self):
        out = {}
        name_filter = self.module.params.get("provider_name")
        type_filter = self.module.params.get("type")
        for kmip_cluster in self.crypto_manager.kmipServers:
            if name_filter and kmip_cluster.clusterId.id != name_filter:
                continue

            if (
                type_filter
                and self.TYPE_MAP.get(kmip_cluster.managementType) != type_filter
            ):
                continue

            out[kmip_cluster.clusterId.id] = self.kmip_cluster_to_dict(kmip_cluster)
        return out


def main():
    argument_spec = base_argument_spec()
    argument_spec.update(
        dict(
            provider_name=dict(type="str", required=False, aliases=["name", "id"]),
            type=dict(type="str", choices=["standard", "native"], required=False),
        )
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        mutually_exclusive=[["provider_name", "type"]],
    )

    result = dict(
        changed=False,
    )

    provider_module = KeyProviderInfoModule(module)
    result["key_providers"] = provider_module.gather_key_provider_info()
    module.exit_json(**result)


if __name__ == "__main__":
    main()

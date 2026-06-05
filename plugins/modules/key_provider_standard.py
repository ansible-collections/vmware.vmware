#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2026, Ansible Cloud Team (@ansible-collections)
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type


DOCUMENTATION = r"""
---
module: key_provider_standard
short_description: Manage a standard key provider in a vCenter instance.
description:
    - This module allows you to create, update, and delete a standard key provider in a vCenter instance.
    - Standard key providers leverage a third-party key management service (KMS) to encrypt and decrypt data.
    - You define a provider 'cluster' that contains one or more external KMS servers.
    - When adding a new KMS server to a provider 'cluster', vCenter will attempt to connect to the server
      and verify its certificate chain. You can view the status of the connection and retry the validation
      via the vCenter UI.

author:
    - Ansible Cloud Team (@ansible-collections)

options:
    provider_name:
        description:
            - The name or ID of the key provider to manage. The name and ID are interchangeable.
            - This is used as a unique identifier for the key provider cluster in vSphere.
            - Each provider has one or more member KMS servers.
        type: str
        required: true
        aliases: [name, id]

    state:
        description:
            - Whether to ensure the key provider is present or absent.
        type: str
        default: present
        choices: [present, absent]

    default_provider:
        description:
            - Whether to set the key provider as the default provider for the vCenter instance.
        type: bool
        default: false

    always_update_password:
        description:
            - If true and O(kms_servers[].password) is set, this module will always report a change and
              set the password value to O(kms_servers[].password) .
            - If false, other properties are still checked for differences. If a difference is found,
              the value of O(kms_servers[].password) is still used.
            - If O(kms_servers[].password) is unset, this parameter is ignored.
            - This option is needed because there is no way to check the current password value and
              compare it against the desired password value.
        default: true
        type: bool

    kms_servers_state:
        description:
            - Whether to ensure the KMS servers are present or absent in the key provider cluster.
        type: str
        default: present
        choices: [present, absent]

    kms_servers:
        description:
            - List of KMS servers to manage in the key provider cluster.
            - This parameter is required when O(state) is V(present).
        type: list
        elements: dict
        required: false
        suboptions:
            id:
                description:
                    - The ID or name of the KMS server.
                    - This must be unique within the key provider cluster, but does not need to be globally unique.
                type: str
                required: true
            address:
                description:
                    - The address (IP or FQDN) of the KMS server.
                    - This should be reachable from the vCenter server.
                    - This parameter is required when O(kms_servers_state) is V(present).
                type: str
                required: false
            port:
                description:
                    - The port number of the KMS server.
                    - This parameter is required when O(kms_servers_state) is V(present).
                type: int
                required: false
            proxy_address:
                description:
                    - The address (IP or FQDN) of the proxy server to use to connect to the KMS server.
                type: str
                required: false
            proxy_port:
                description:
                    - The port number of the proxy server.
                type: int
                required: false
            username:
                description:
                    - The username to use to authenticate to the KMS server.
                type: str
                required: false
            password:
                description:
                    - The password to use to authenticate to the KMS server.
                    - Because the password is encrypted in vCenter, this parameter cannot
                      be checked for idempotency. See O(always_update_password) for more details.
                type: str
                required: false

extends_documentation_fragment:
    - vmware.vmware.base_options
"""

EXAMPLES = r"""
- name: Ensure a standard key provider is absent
  vmware.vmware.key_provider_standard:
    provider_name: my-standard-key-provider
    state: absent

- name: Create a standard key provider with a KMS server
  vmware.vmware.key_provider_standard:
    provider_name: my-standard-key-provider
    state: present
    kms_servers:
      - id: kms-server-1
        address: 10.0.0.1
        port: 5696
        proxy_address: 10.0.0.2
        proxy_port: 5697
        username: kmsuser
        password: kms-password

- name: Update a KMS server without forcing a password change
  vmware.vmware.key_provider_standard:
    provider_name: my-standard-key-provider
    state: present
    always_update_password: false
    kms_servers:
      - id: kms-server-1
        address: 10.0.0.1
        port: 5696
        proxy_address: 10.0.0.2
        proxy_port: 5697
        username: kmsuser
        password: kms-password

- name: Add a second KMS server to the key provider cluster
  vmware.vmware.key_provider_standard:
    provider_name: my-standard-key-provider
    state: present
    kms_servers:
      - id: kms-server-2
        address: 10.0.0.3
        port: 5696

- name: Remove a KMS server from the key provider cluster
  vmware.vmware.key_provider_standard:
    provider_name: my-standard-key-provider
    state: present
    kms_servers_state: absent
    kms_servers:
      - id: kms-server-1

- name: Set a standard key provider as the default
  vmware.vmware.key_provider_standard:
    provider_name: my-standard-key-provider
    state: present
    default_provider: true
    kms_servers:
      - id: kms-server-1
        address: 10.0.0.1
        port: 5696
"""

RETURN = r"""
modified_kms_servers:
    description:
        - List of KMS server IDs that were created, updated, or removed.
        - Empty when no KMS server changes were needed.
    returned: when O(state) is V(present)
    type: list
    sample: ["kms-server-1"]
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
    base_argument_spec,
)


class StandardKeyProviderModule(ModulePyvmomiBase):
    CLUSTER_SERVER_UPDATE_FIELDS = {
        "address": "address",
        "port": "port",
        "proxy_address": "proxyAddress",
        "proxy_port": "proxyPort",
        "username": "userName",
    }

    def __init__(self, module):
        super().__init__(module)
        self.provider_name = module.params.get("provider_name")
        self._cluster_provider_obj = None
        self.crypto_manager = self.si.content.cryptoManager

    @property
    def cluster_provider_obj(self):
        if self._cluster_provider_obj is None:
            for kmip_cluster in self.crypto_manager.kmipServers:
                if kmip_cluster.clusterId.id == self.provider_name:
                    self._cluster_provider_obj = kmip_cluster
                    break
        return self._cluster_provider_obj

    def _create_kmip_server_spec(self, server):
        server_spec = vim.encryption.KmipServerSpec()
        server_spec.clusterId = vim.encryption.KeyProviderId(id=self.provider_name)
        if server.get("password"):
            server_spec.password = server.get("password")
        server_spec.info = vim.encryption.KmipServerInfo()
        server_spec.info.name = server.get("id")
        server_spec.info.address = server.get("address")
        server_spec.info.port = server.get("port")
        server_spec.info.proxyAddress = server.get("proxy_address")
        server_spec.info.proxyPort = server.get("proxy_port")
        server_spec.info.userName = server.get("username")
        return server_spec

    def perform_present_server_action(self, param_server, server_action_function):
        server_spec = self._create_kmip_server_spec(param_server)
        server_action_function(server=server_spec)

    def create_key_provider(self):
        """
        vCenter is really weird when creating a new key provider cluster. You need to create the KMIP server first, and that will create
        the cluster if needed.
        """
        for server in self.params.get("kms_servers"):
            server_spec = self._create_kmip_server_spec(server)
            self.crypto_manager.RegisterKmipServer(server=server_spec)

    def remove_kmip_server(self, server_id):
        self.crypto_manager.RemoveKmipServer(
            self.cluster_provider_obj.clusterId, serverName=server_id
        )

    def set_default_key_provider(self):
        self.crypto_manager.MarkDefault(clusterId=self.cluster_provider_obj.clusterId)

    def delete_key_provider(self):
        self.crypto_manager.UnregisterKmsCluster(
            clusterId=self.cluster_provider_obj.clusterId
        )

    def get_present_server_action_function(self, param_server):
        existing_server = self.get_existing_server(param_server.get("id"))
        if existing_server is None:
            return self.crypto_manager.RegisterKmipServer

        if param_server.get("password") and self.params.get("always_update_password"):
            return self.crypto_manager.UpdateKmipServer

        for param_name, attr_name in self.CLUSTER_SERVER_UPDATE_FIELDS.items():
            if param_server.get(param_name) is None:
                continue

            if getattr(existing_server, attr_name) != param_server.get(param_name):
                return self.crypto_manager.UpdateKmipServer

        return None

    def get_existing_server(self, server_id):
        for _s in self.cluster_provider_obj.servers:
            if _s.name == server_id:
                return _s
        return None


def update_cluster_servers_if_needed(provider_module, result, module):
    for param_server in module.params.get("kms_servers"):
        param_server_id = param_server.get("id")
        if module.params.get("kms_servers_state") == "present":
            server_action_function = provider_module.get_present_server_action_function(
                param_server
            )
            if server_action_function is not None:
                result["changed"] = True
                result["modified_kms_servers"].append(param_server_id)
                if not module.check_mode:
                    provider_module.perform_present_server_action(
                        param_server, server_action_function
                    )

        elif provider_module.get_existing_server(param_server_id) is not None:
            result["changed"] = True
            result["modified_kms_servers"].append(param_server_id)
            if not module.check_mode:
                provider_module.remove_kmip_server(param_server_id)


def do_present_state(module, provider_module, result):
    result["modified_kms_servers"] = list()
    if provider_module.cluster_provider_obj is None:
        result["changed"] = True
        result["modified_kms_servers"] = [
            s["id"] for s in module.params.get("kms_servers")
        ]
        if not module.check_mode:
            provider_module.create_key_provider()
    else:
        update_cluster_servers_if_needed(provider_module, result, module)

    if module.params.get("default_provider") and not getattr(
        provider_module.cluster_provider_obj, "useAsDefault", False
    ):
        result["changed"] = True
        if not module.check_mode:
            provider_module.set_default_key_provider()


def main():
    argument_spec = base_argument_spec()
    argument_spec.update(
        dict(
            state=dict(type="str", choices=["present", "absent"], default="present"),
            provider_name=dict(type="str", required=True, aliases=["name", "id"]),
            default_provider=dict(type="bool", default=False),
            always_update_password=dict(type="bool", default=True),
            kms_servers_state=dict(
                type="str", choices=["present", "absent"], default="present"
            ),
            kms_servers=dict(
                type="list",
                elements="dict",
                required=False,
                options=dict(
                    id=dict(type="str", required=True),
                    address=dict(type="str", required=False),
                    port=dict(type="int", required=False),
                    proxy_address=dict(type="str", required=False),
                    proxy_port=dict(type="int", required=False),
                    username=dict(type="str", required=False),
                    password=dict(type="str", required=False, no_log=True),
                ),
            ),
        )
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_if=[
            ("state", "present", ("kms_servers",)),
        ],
    )

    result = dict(
        changed=False,
    )

    if (
        module.params.get("state") == "present"
        and module.params.get("kms_servers_state") == "present"
    ):
        for server in module.params.get("kms_servers") or []:
            if server.get("address") is None or server.get("port") is None:
                module.fail_json(
                    msg="address and port are required for each KMS server when kms_servers_state is present."
                )

    provider_module = StandardKeyProviderModule(module)
    if module.params.get("state") == "present":
        do_present_state(module, provider_module, result)

    elif module.params.get("state") == "absent" and provider_module.cluster_provider_obj is not None:
        result["changed"] = True
        if not module.check_mode:
            provider_module.delete_key_provider()

    module.exit_json(**result)


if __name__ == "__main__":
    main()

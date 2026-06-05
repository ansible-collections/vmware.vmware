#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2026, Ansible Cloud Team (@ansible-collections)
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type


DOCUMENTATION = r"""
---
module: key_provider_native
short_description: Manage a native key provider in a vCenter instance.
description:
    - This module allows you to create, update, and delete a native key provider in a vCenter instance.
    - Native key providers leverage the built-in cryptography libraries of the ESXi and vCenter appliance
      to encrypt and decrypt data.
    - You can optionally require TPM protection on the ESXi hosts that use the key provider.

author:
    - Ansible Cloud Team (@ansible-collections)

requirements:
    - vSphere Automation SDK

options:
    provider_name:
        description:
            - The name or ID of the key provider to manage. The name and ID are interchangeable.
            - This is used as a unique identifier for the key provider in vSphere.
        type: str
        required: true
        aliases: [name, id]

    state:
        description:
            - Whether to ensure the key provider is present or absent.
        type: str
        default: present
        choices: [present, absent]

    tpm_required:
        description:
            - Whether to require ESXi hosts to have TPM protection before they can use the key provider.
            - This setting cannot be changed once the provider is created. It is only used when creating new providers.
        type: bool
        default: true

    default_provider:
        description:
            - Whether to set the key provider as the default provider for the vCenter instance.
        type: bool
        default: false

    export_password:
        description:
            - The password to use when exporting or backing up the key provider. This is used to encrypt the exported key provider data (as a P12 file).
            - Since this module does not actually perform the backup for you, this password is only applied to the backup
              if you use the export URL and token from the module's return values to perform the backup.
            - If no password is provided, the key provider data will be exported without encryption.
            - If you choose to backup the key provider via the web UI, you can provide a password there instead.
        type: str
        required: false

    disable_export_outputs:
        description:
            - If true, the module will not return the export URL and token.
            - This is useful if you want to perform the backup via the web UI or other means and do not want to expose backup options in the logs
              or memory.
        type: bool
        default: false

notes:
    - Key providers must be backed up and 'activated' before they can be used. You can do this at any time in vCenter, or use the module's
      return values to perform the backup. See the examples below for more details.


extends_documentation_fragment:
    - vmware.vmware.base_options
    - vmware.vmware.additional_rest_options
"""

EXAMPLES = r"""
- name: Ensure a native key provider is absent
  vmware.vmware.key_provider_native:
    provider_name: my-native-key-provider
    state: absent

- name: Create a native key provider
  vmware.vmware.key_provider_native:
    provider_name: my-native-key-provider
    state: present
    tpm_required: true
    default_provider: false

- name: Create a key provider and back it up to activate it
  block:
    - name: Create a native key provider and return export details for backup
      vmware.vmware.key_provider_native:
        provider_name: my-native-key-provider
        state: present
        tpm_required: true
        export_password: backup-password
      register: native_key_provider
    - name: Backup and activate the native key provider
      ansible.builtin.get_url:
        url: "{{ native_key_provider.export_info.url }}"
        dest: "/tmp/native_key_provider.p12"
        headers:
        Authorization: "Bearer {{ native_key_provider.export_info.token }}"
      when: native_key_provider is ansible.builtin.changed

- name: Set a native key provider as the default and do not log export information
  vmware.vmware.key_provider_native:
    provider_name: my-native-key-provider
    state: present
    default_provider: true
    disable_export_outputs: true
"""

RETURN = r"""
export_info:
    description:
        - Information needed to export and back up a newly created native key provider.
        - Use the URL and token to download the key provider backup before the export token expires.
        - This information is only available once, immediately after creation.
        - You can perform the backup without this information via the vCenter web UI.
        - Note that the token value may be considered sensitive. You can reduce the risk of its exposure
          by setting the O(export_password) parameter, or by not logging it using the O(disable_export_outputs) parameter.
    returned: when a new key provider was created and O(disable_export_outputs) is V(false)
    type: dict
    sample: {
        "url": "https://vcenter.example.com/api/vcenter/crypto-manager/kms/providers/my-native-key-provider/export",
        "token": "abc123exampletoken",
        "expires_at": "2026-05-18T16:57:06"
    }
"""

try:
    from com.vmware.vapi.std.errors_client import NotFound
except ImportError:
    pass

try:
    from pyVmomi import vim
except ImportError:
    pass

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.vmware.vmware.plugins.module_utils._module_rest_base import (
    ModuleRestBase,
)
from ansible_collections.vmware.vmware.plugins.module_utils._module_pyvmomi_base import (
    ModulePyvmomiBase,
)
from ansible_collections.vmware.vmware.plugins.module_utils.argument_spec import (
    rest_compatible_argument_spec,
)


class NativeKeyProviderModule(ModuleRestBase):
    def __init__(self, module):
        super().__init__(module)
        self.provider_name = module.params.get("provider_name")
        self.providers_service = self.api_client.vcenter.crypto_manager.kms.Providers
        self._pyvmomi_crypto_manager = None

    @property
    def pyvmomi_crypto_manager(self):
        if self._pyvmomi_crypto_manager is None:
            pyvmomi = ModulePyvmomiBase(self.module)
            self._pyvmomi_crypto_manager = pyvmomi.si.content.cryptoManager
        return self._pyvmomi_crypto_manager

    def get_key_provider(self):
        try:
            return self.providers_service.get(self.provider_name)
        except NotFound:
            return None

    def is_provider_cluster_default(self):
        default_provider_id = self.pyvmomi_crypto_manager.GetDefaultKmsCluster()
        return default_provider_id.id == self.provider_name

    def create_key_provider(self):
        spec = self.providers_service.CreateSpec(
            self.provider_name,
            constraints=self.providers_service.ConstraintsSpec(
                tpm_required=self.params.get("tpm_required")
            ),
        )
        return self.providers_service.create(spec)

    def prepare_key_provider_export(self):
        export_spec = self.providers_service.ExportSpec(provider=self.provider_name)
        if self.params.get("export_password"):
            export_spec.password = self.params.get("export_password")
        export_response = self.providers_service.export(export_spec)

        token = export_response.location.download_token
        return dict(
            url=export_response.location.url,
            token=token.token,
            expires_at=token.expiry,
        )

    def set_default_key_provider(self):
        provider_id = vim.encryption.KeyProviderId()
        provider_id.id = self.provider_name
        self.pyvmomi_crypto_manager.MarkDefault(clusterId=provider_id)

    def delete_key_provider(self):
        self.providers_service.delete(self.provider_name)


def do_present_state(module, provider_module, provider, result):
    if provider is None:
        result["changed"] = True
        if not module.check_mode:
            provider_module.create_key_provider()
            if not module.params.get("disable_export_outputs"):
                result["export_info"] = (
                    provider_module.prepare_key_provider_export()
                )

    if (
        module.params.get("default_provider")
        and not provider_module.is_provider_cluster_default()
    ):
        result["changed"] = True
        if not module.check_mode:
            provider_module.set_default_key_provider()


def main():
    argument_spec = rest_compatible_argument_spec()
    argument_spec.update(
        dict(
            state=dict(type="str", choices=["present", "absent"], default="present"),
            provider_name=dict(type="str", required=True, aliases=["name", "id"]),
            tpm_required=dict(type="bool", default=True),
            default_provider=dict(type="bool", default=False),
            disable_export_outputs=dict(type="bool", default=False),
            export_password=dict(type="str", required=False, no_log=True),
        )
    )

    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)

    result = dict(changed=False)

    provider_module = NativeKeyProviderModule(module)
    provider = provider_module.get_key_provider()
    if module.params.get("state") == "present":
        do_present_state(module, provider_module, provider, result)

    elif module.params.get("state") == "absent" and provider is not None:
        result["changed"] = True
        if not module.check_mode:
            provider_module.delete_key_provider()

    module.exit_json(**result)


if __name__ == "__main__":
    main()

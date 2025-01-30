#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2019, Ansible Project
# Copyright: (c) 2019, Pavan Bidkar <pbidkar@vmware.com>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function
__metaclass__ = type


DOCUMENTATION = r'''
---
module: content_library
short_description: Manage a content library.
description:
    - Create, update, or destroy a content library.
author:
    - Ansible Cloud Team (@ansible-collections)
requirements:
    - vSphere Automation SDK

extends_documentation_fragment:
    - vmware.vmware.base_options
    - vmware.vmware.additional_rest_options

options:
    name:
        description:
            - The name of the content library to manage.
            - The name and type of content library are used when determining which library should be managed.
        type: str
        required: true
        aliases: [library_name]
    type:
        description:
            - The type of content library to manage.
            - The type of a library cannot be updated once the library is created.
            - The name and type of content library are used when determining which library should be managed.
        type: str
        required: true
        aliases: [library_type]
        choices: [local, subscribed]
    description:
        description:
            - The description for the content library.
        type: str
        default: Library created by Ansible
        aliases: [library_description]
    datastore:
        description:
            - The name of the datastore that should be a storage backing for the library.
            - This parameter is required when O(state) is V(present)
            - This parameter only takes affect when the library is first created. You cannot change the
              storage backing for an existing library, and the module will not check this value in that case.
        type: str
        required: false
        aliases: [datastore_name]
    subscription_url:
        description:
            - The URL of the remote library to which you want to subscribe.
            - This parameter is required if O(state) is V(present) and O(type) is V(subscribed).
        type: str
        required: false
    ssl_thumbprint:
        description:
            - The SSL thumbprint that is presented by the subscription URL endpoint.
            - This parameter is required if O(subscription_url) starts with V(https:).
        type: str
        required: false
    update_on_demand:
        description:
            - Whether to download all content on demand, or download all content ahead of time.
            - This parameter is required if O(state) is V(present) and O(type) is V(subscribed).
        type: bool
        default: false
    state:
        description:
            - Whether the content library should be present or absent.
        type: str
        default: present
        choices: [present, absent]
'''

EXAMPLES = r'''
- name: Create template in content library from Virtual Machine
  vmware.vmware.content_template:
    hostname: '{{ vcenter_hostname }}'
    username: '{{ vcenter_username }}'
    password: '{{ vcenter_password }}'
    template: mytemplate
    library: mylibrary
    vm_name: myvm
    host: myhost
'''

RETURN = r'''
template_info:
  description: Template creation message and template_id
  returned: on success
  type: dict
  sample: {
        "msg": "Template 'mytemplate'.",
        "template_id": "template-1009"
    }
'''
import uuid
from ansible.module_utils.basic import AnsibleModule
from ansible_collections.vmware.vmware.plugins.module_utils._vmware_argument_spec import rest_compatible_argument_spec
from ansible.module_utils.common.text.converters import to_native
from ansible_collections.vmware.vmware.plugins.module_utils._module_rest_base import ModuleRestBase
from ansible_collections.vmware.vmware.plugins.module_utils._module_pyvmomi_base import ModulePyvmomiBase

try:
    from com.vmware.content_client import LibraryModel
    from com.vmware.content.library_client import StorageBacking, SubscriptionInfo
    from com.vmware.vapi.std.errors_client import ResourceInaccessible
except ImportError:
    pass


class VmwareContentLibrary(ModuleRestBase):
    def __init__(self, module):
        """Constructor."""
        super().__init__(module)
        if self.params['state'] == 'present':
            self.pyvmomi = ModulePyvmomiBase(module)

        if self.params['library_type'] == 'local':
            self.library_service = self.api_client.content.LocalLibrary
        else:
            self.library_service = self.api_client.content.SubscribedLibrary

    def sub_url_is_https(self):
        return self.params.get('subscription_url', '').startswith('https://')

    def get_matching_libraries(self):
        found = []
        for library in self.get_content_library_ids(self.params['name']):
            if library.type.lower() == self.params['library_type']:
                found += [library]

        return found

    def __set_subscription_spec(self, create_spec):
        subscription_info = SubscriptionInfo()
        subscription_info.on_demand = self.params['update_on_demand']
        subscription_info.automatic_sync_enabled = True
        subscription_info.subscription_url = self.params['subscription_url']
        subscription_info.authentication_method = SubscriptionInfo.AuthenticationMethod.NONE

        if self.sub_url_is_https():
            subscription_info.ssl_thumbprint = self.params['ssl_thumbprint']
        create_spec.subscription_info = subscription_info

    def create_library_spec(self, datastore_id: str = None):
        create_spec = LibraryModel()
        create_spec.name = self.params['name']
        create_spec.description = self.params['description']
        create_spec.type = getattr(create_spec.LibraryType, self.params['type'].upper())
        if datastore_id:
            create_spec.storage_backings = [
                StorageBacking(type=StorageBacking.Type.DATASTORE, datastore_id=datastore_id)
            ]
        # Build subscribed specification
        if self.params['type'] == "subscribed":
            self.__set_subscription_spec(create_spec)

        return create_spec

    def create_library(self):
        datastore = self.pyvmomi.get_datastore_by_name_or_moid(self.params['datastore'], fail_on_missing=True)
        create_spec = self.create_library_spec(datastore_id=datastore._GetMoId())
        try:
            library_id = self.library_service.create(
                create_spec=create_spec,
                client_token=str(uuid.uuid4())
            )
        except ResourceInaccessible as e:
            self.module.fail_json(msg=(
                "vCenter Failed to make connection to %s with exception: %s. If using HTTPS, check "
                "that the SSL thumbprint is valid" % (self.subscription_url, to_native(e))
            ))
        return library_id

    def library_needs_updating(self, existing_library):
        if existing_library.description != self.params['description']:
            return True

        if self.params['type'] == "local":
            return

        if any(
            (existing_library.subscription_info.subscription_url != self.params['subscription_url']),
            (existing_library.subscription_info.on_demand != self.params['update_on_demand'])
        ):
            return True

        if self.sub_url_is_https():
            return (existing_library.subscription_info.ssl_thumbprint != self.params['ssl_thumbprint'])

    def update_library(self, existing_library):
        create_spec = self.create_library_spec()
        try:
            self.library_service.update(
                existing_library.id,
                create_spec
            )
        except ResourceInaccessible as e:
            self.module.fail_json(msg=(
                "vCenter Failed to make connection to %s with exception: %s. If using HTTPS, check "
                "that the SSL thumbprint is valid" % (self.subscription_url, to_native(e))
            ))
        return existing_library.id


def main():
    argument_spec = rest_compatible_argument_spec()
    argument_spec.update(
        name=dict(type='str', required=True, aliases=['library_name']),
        type=dict(type='str', required=True, aliases=['library_type'], choices=['local', 'subscribed']),
        description=dict(type='str', required=False, aliases=['library_description'], default="Library created by Ansible"),
        datastore=dict(type='str', required=False, aliases=['datastore_name']),
        subscription_url=dict(type='str', required=False),
        ssl_thumbprint=dict(type='str', required=False),
        update_on_demand=dict(type='bool', default=False),
        state=dict(type='str', default='present', choices=['present', 'absent']),
    )
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_if=[
            ('state', 'present', ('datastore'), False)
        ]
    )

    if module.params.get('state') =='present' and module.params.get('type') == 'subscribed' and not module.params.get('subscription_url'):
        module.fail_json(msg="Parameter subscription_url is required when state is present for a subscribed library")
    if module.params.get('subscription_url', '').startswith('https://') and not module.params.get('ssl_thumbprint'):
        module.fail_json(msg="Parameter ssl_thumbprint is required when managing a subscribed library with an HTTPS URL")

    result = {'changed': False, 'library_name': module.params['name'], 'library_type': module.params['type']}
    vmware_library = VmwareContentLibrary(module)
    libraries = vmware_library.get_matching_libraries()
    if len(libraries) > 1:
        module.fail_json(msg='More than one library has the same name and type. Cannot determine which one to manage.')

    if module.params['state'] == 'present':
        if not libraries:
            result['changed'] = True
            if not module.check_mode:
                result['library_id'] = vmware_library.create_library()
        else:
            if vmware_library.library_needs_updating(libraries[0]):
                result['changed'] = True
                if not module.check_mode:
                    result['library_id'] = vmware_library.update_library()
            else:
                result['library_id'] = libraries[0].id

        module.exit_json(**result)

    elif module.params['state'] == 'absent':
        if libraries:
            result['changed'] = True
            if not module.check_mode:
                vmware_library.library_service.delete(library_id=libraries[0].id)

    module.exit_json(**result)


if __name__ == '__main__':
    main()

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
module: content_template
short_description: Manage template in content library from virtual machine.
description:
- Module to manage template in content library from virtual machine.
- Content Library feature is introduced in vSphere 6.0 version.
- This module does not work with vSphere version older than 67U2.
author:
- Ansible Cloud Team (@ansible-collections)
requirements:
- vSphere Automation SDK
options:
    template:
        description:
        - The name of template to manage.
        type: str
        required: true
    library:
        description:
        - The name of the content library where the template will be created.
        type: str
        required: true
    vm_name:
        description:
        - The name of the VM to be used to create template.
        - This attribute is required only when the state attribute is set to present
        type: str
    host:
        description:
        - Host onto which the virtual machine template should be placed.
        - If O(host) and O(resource_pool) are both specified, O(resource_pool)
          must belong to O(host).
        - If O(host) and O(cluster) are both specified, O(host) must be a member of O(cluster).
        - This attribute was added in vSphere API 6.8.
        type: str
    resource_pool:
        description:
        - Resource pool into which the virtual machine template should be placed.
        - This attribute was added in vSphere API 6.8.
        - If not specified, the system will attempt to choose a suitable resource pool
          for the virtual machine template; if a resource pool cannot be
          chosen, the library item creation operation will fail.
        type: str
    cluster:
        description:
        - Cluster onto which the virtual machine template should be placed.
        - If O(cluster) and O(resource_pool) are both specified,
          O(resource_pool) must belong to O(cluster).
        - If O(cluster) and O(host) are both specified, O(host) must be a member of O(cluster).
        - This attribute was added in vSphere API 6.8.
        type: str
    folder:
        description:
        - Virtual machine folder into which the virtual machine template should be placed.
        - This attribute was added in vSphere API 6.8.
        - If not specified, the virtual machine template will be placed in the same
          folder as the source virtual machine.
        type: str
    state:
        description:
        - State of the template in content library.
        - If C(present), the template will be created in content library.
        - If C(absent), the template will be deleted from content library.
        type: str
        default: present
        choices:
        - present
        - absent
extends_documentation_fragment:
    - vmware.vmware.base_options
    - vmware.vmware.additional_rest_options
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

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.vmware.vmware.plugins.module_utils._module_rest_base import ModuleRestBase
from ansible_collections.vmware.vmware.plugins.module_utils._vmware_argument_spec import rest_compatible_argument_spec
from ansible.module_utils._text import to_native

HAS_VAUTOMATION_PYTHON_SDK = False
try:
    from com.vmware.vcenter.vm_template_client import LibraryItems
    from com.vmware.vapi.std.errors_client import Error
    HAS_VAUTOMATION_PYTHON_SDK = True
except ImportError:
    pass


class VmwareContentTemplate(ModuleRestBase):
    def __init__(self, module):
        """Constructor."""
        super(VmwareContentTemplate, self).__init__(module)

        # Initialize member variables
        self.module = module
        self._template_service = self.api_client.vcenter.vm_template.LibraryItems
        self.result = {'changed': False}

        # Get parameters
        self.template = self.params.get('template')
        self.host = self.params.get('host')
        self.cluster = self.params.get('cluster')
        self.resource_pool = self.params.get('resource_pool')
        self.library_id = self.get_content_library_ids(name=self.params.get('library'), fail_on_missing=True)[0]
        self.folder = self.params.get('folder')
        self.vm_name = self.params.get('vm_name')

    def create_template_from_vm(self):
        _template = self.get_library_item_ids(name=self.template, library_id=self.library_id)
        if _template:
            self.result['template_info'] = dict(
                msg="Template '%s' already exists." % self.template,
                template_id=_template[0],
            )
            return

        # Create template placement specs
        placement_spec = LibraryItems.CreatePlacementSpec()
        placement_spec.host = self.get_host_by_name(self.host)
        placement_spec.resource_pool = self.get_resource_pool_by_name(self.resource_pool)
        placement_spec.cluster = self.get_cluster_by_name(self.cluster)
        placement_spec.folder = self.get_folder_by_name(self.folder)
        create_spec = LibraryItems.CreateSpec(
            name=self.template,
            placement=placement_spec,
            library=self.library_id,
            source_vm=self.get_vm_obj_by_name(self.vm_name),
        )
        template_id = ''
        try:
            template_id = self._template_service.create(create_spec)
        except Error as error:
            self.module.fail_json(msg="%s" % self.get_error_message(error))
        except Exception as err:
            self.module.fail_json(msg="%s" % to_native(err))

        if not template_id:
            self.result['template_info'] = dict(
                msg="Template creation failed",
            )
            self.module.fail_json(**self.result)
        self.result['changed'] = True
        self.result['template_info'] = dict(
            msg="Template '%s'." % self.template,
            template_id=template_id,
        )

    def delete_template(self):
        _template = self.get_library_item_ids(name=self.template, library_id=self.library_id)
        if not _template:
            self.result['template_info'] = dict(
                msg="Template '%s' doesn't exists." % self.template,
            )
            return
        template_id = _template[0]

        try:
            self.api_client.content.library.Item.delete(template_id)
        except Exception as err:
            self.module.fail_json(msg="%s" % to_native(err))

        self.result['changed'] = True
        self.result['template_info'] = dict(
            msg="Template '%s' has been deleted." % self.template,
            template_id=template_id,
        )


def main():
    argument_spec = rest_compatible_argument_spec()
    argument_spec.update(
        template=dict(type='str', required=True),
        library=dict(type='str', required=True),
        vm_name=dict(type='str'),
        host=dict(type='str'),
        cluster=dict(type='str'),
        resource_pool=dict(type='str'),
        folder=dict(type='str'),
        state=dict(type='str', default='present', choices=['present', 'absent']),
    )
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_one_of=[('host', 'resource_pool', 'cluster')],
        required_if=[('state', 'present', ["vm_name"])]
    )

    result = {'failed': False, 'changed': False}
    vmware_contentlib = VmwareContentTemplate(module)
    if module.check_mode:
        result.update(
            vm_name=module.params['name'],
            changed=True,
            desired_operation='{} template'.format(module.params.get('state')),
        )
        module.exit_json(**result)
    if module.params.get('state') == 'present':
        vmware_contentlib.create_template_from_vm()
    else:
        vmware_contentlib.delete_template()
    module.exit_json(**vmware_contentlib.result)


if __name__ == '__main__':
    main()

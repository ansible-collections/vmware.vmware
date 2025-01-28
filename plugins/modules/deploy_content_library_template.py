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
module: deploy_content_library_template
short_description: Deploy a virtual machine from a template in a content library.
description:
    - Create or destroy a VM based on a template in a content library.
    - The module basis idempotentency on if the deployed VM exists or not, not the storage or power settings applied at deployment time.
author:
    - Ansible Cloud Team (@ansible-collections)

requirements:
    - vSphere Automation SDK

seealso:
    - module: vmware.vmware.deploy_content_library_ovf

extends_documentation_fragment:
    - vmware.vmware.base_options
    - vmware.vmware.additional_rest_options

options:
    datacenter:
        description:
            - The name of the datacenter to use when searching for and deploying resources.
        type: str
        required: true
        aliases: [datacenter_name]
    library_item_name:
        description:
            - The name of content library template to use when deploying the VM.
            - This option is mutually exclusive with O(library_item_id).
            - One of either O(library_item_name) or O(library_item_id) is required when O(state) is V(present).
        type: str
        required: false
        aliases: [template_name]
    library_item_id:
        description:
            - The ID of content library template to use when deploying the VM.
            - This option is mutually exclusive with O(library_item_name).
            - One of either O(library_item_name) or O(library_item_id) is required when O(state) is V(present).
        type: str
        required: false
        aliases: [template_id]
    library_name:
        description:
            - The name of the content library where the template exists.
            - >-
              This is an optional parameter, but may be required if you use O(template_name) and have
              multiple templates in different libraries with the same name.
            - This option is mutually exclusive with O(library_id).
        type: str
        required: false
    library_id:
        description:
            - The ID of the content library where the template exists.
            - >-
              This is an optional parameter, but may be required if you use O(template_name) and have
              multiple templates in different libraries with the same name.
            - This option is mutually exclusive with O(library_name).
        type: str
        required: false
    vm_name:
        description:
            - The name of the VM to deploy.
        type: str
        required: true
    esxi_host:
        description:
            - The name of the ESXi host onto which the virtual machine should be deployed.
            - If O(esxi_host) and O(resource_pool) are both specified, O(resource_pool) must belong to O(esxi_host).
            - If O(esxi_host) and O(cluster) are both specified, O(esxi_host) must be a member of O(cluster).
            - Changing this option will not result in the VM being redeployed (it does not affect idempotency).
        type: str
        aliases: [host]
    resource_pool:
        description:
            - The name of a resource pool into which the virtual machine should be deployed.
            - Changing this option will not result in the VM being redeployed (it does not affect idempotency).
        type: str
    cluster:
        description:
            - The name of the cluster where the VM should be deployed.
            - If O(cluster) and O(resource_pool) are both specified, O(resource_pool) must belong to O(cluster).
            - If O(cluster) and O(esxi_host) are both specified, O(esxi_host) must be a member of O(cluster).
            - Changing this option will not result in the VM being redeployed (it does not affect idempotency).
        type: str
        required: false
        aliases: [cluster_name]
    folder:
        description:
            - Virtual machine folder into which the virtual machine should be deployed.
            - This can be the absolute folder path, or a relative folder path under /<datacenter>/vm/.
              See the examples for more info.
            - This option is required if you have more than one VM with the same name in the datacenter.
            - Changing this option will result in the VM being redeployed, since it affects where the module looks
              for the deployed VM.
        type: str
        required: false
    power_on_after_deploy:
        description:
            - Whether or not the VM should be powered on once it has been deployed.
            - This is only applied when the VM is deployed. If the VM already exists, the power state is not modified.
            - Changing this option will not result in the VM being redeployed (it does not affect idempotency).
        type: bool
        default: false
        required: false
    state:
        description:
            - Whether the deployed VM should be present or absent.
            - The VM must be in a powered off status when O(state) is V(absent)
        type: str
        default: present
        choices: [present, absent]
    datastore:
        description:
            - Name of the datastore to store deployed VM and disk.
            - Required if O(state) is V(present) and O(datastore_cluster) is not provided.
        type: str
        required: false
    datastore_cluster:
        description:
            - Name of the datastore cluster to store deployed VM and disk.
            - Please make sure Storage DRS is active for recommended datastore from the given datastore cluster.
            - If Storage DRS is not enabled, datastore with largest free storage space is selected.
            - Required if O(state) is V(present) and O(datastore) is not provided.
        type: str
        required: false
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
from ansible_collections.vmware.vmware.plugins.module_utils._vmware_argument_spec import rest_compatible_argument_spec
from ansible_collections.vmware.vmware.plugins.module_utils._module_deploy_content_library_base import VmwareContentDeploy
from ansible.module_utils.common.text.converters import to_native

try:
    from com.vmware.vcenter.vm_template_client import LibraryItems as TemplateLibraryItems
    from com.vmware.vapi.std.errors_client import Error
except ImportError:
    pass


class VmwareContentDeployTemplate(VmwareContentDeploy):
    def __init__(self, module):
        """Constructor."""
        super(VmwareContentDeployTemplate, self).__init__(module)

        self.template_service = self.rest_base.api_client.vcenter.vm_template.LibraryItems

    def create_deploy_spec(self):
        placement_spec = TemplateLibraryItems.DeployPlacementSpec(folder=self.get_deployment_folder()._GetMoId())
        if self.params.get('esxi_host'):
            placement_spec.host = self.get_esxi_host_by_name_or_moid(
                self.params['esxi_host'],
                fail_on_missing=True
            )._GetMoId()

        if self.params.get('resource_pool'):
            placement_spec.resource_pool = self.get_resource_pool_by_name_or_moid(
                self.params['resource_pool'],
                fail_on_missing=True
            )._GetMoId()

        if self.params.get('cluster'):
            placement_spec.cluster = self.get_cluster_by_name_or_moid(
                self.params['cluster'],
                fail_on_missing=True,
                datacenter=self.datacenter
            )._GetMoId()

        vm_home_storage_spec = TemplateLibraryItems.DeploySpecVmHomeStorage(
            datastore=to_native(self.datastore_id)
        )
        disk_storage_spec = TemplateLibraryItems.DeploySpecDiskStorage(
            datastore=to_native(self.datastore_id)
        )

        return TemplateLibraryItems.DeploySpec(
            name=self.params['vm_name'],
            placement=placement_spec,
            vm_home_storage=vm_home_storage_spec,
            disk_storage=disk_storage_spec,
            powered_on=self.params['power_on_after_deploy']
        )

    def deploy(self, deploy_spec):
        try:
            return self.template_service.deploy(
                self.library_item_id,
                deploy_spec
            )
        except Error as error:
            self.module.fail_json(msg=' ,'.join([err.default_message % err.args for err in error.messages]))
        except Exception as err:
            self._fail(msg="%s" % to_native(err))


def main():
    argument_spec = rest_compatible_argument_spec()
    argument_spec.update(
        library_name=dict(type='str', required=False),
        library_id=dict(type='str', required=False),
        library_item_name=dict(type='str', required=False, aliases=['template_name']),
        library_item_id=dict(type='str', required=False, aliases=['template_id']),
        vm_name=dict(type='str', required=True),
        esxi_host=dict(type='str', required=False, aliases=['host']),
        cluster=dict(type='str', required=False, aliases=['cluster_name']),
        resource_pool=dict(type='str', required=False),
        folder=dict(type='str', required=False),
        datacenter=dict(type='str', required=True, aliases=['datacenter_name']),
        datastore=dict(type='str', required=False),
        datastore_cluster=dict(type='str', required=False),
        power_on_after_deploy=dict(type='bool', default=False),
        state=dict(type='str', default='present', choices=['present', 'absent']),
    )
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        mutually_exclusive=[
            ('library_name', 'library_id'),
            ('library_item_name', 'library_item_id'),
            ('datastore', 'datastore_cluster'),
        ],
        required_if=[
            ('state', 'present', ('library_name', 'library_id', 'library_item_name', 'library_item_id'), True),
            ('state', 'present', ('datastore', 'datastore_cluster'), True),
        ]
    )

    result = {'changed': False, 'vm_name': module.params['vm_name']}
    vmware_template = VmwareContentDeployTemplate(module)
    vm = vmware_template.get_deployed_vm()

    if module.params['state'] == 'present':
        if vm:
            result['vm_moid'] = vm._GetMoId()
        else:
            result['changed'] = True
            spec = vmware_template.create_deploy_spec()
            if module.check_mode:
                module.exit_json(**result)
            vm_id = vmware_template.deploy(spec)
            result['vm_moid'] = vm_id

    elif module.params['state'] == 'absent':
        if vm:
            result['changed'] = True
            if module.check_mode:
                module.exit_json(**result)
            vmware_template.delete_vm(vm)

    module.exit_json(**result)


if __name__ == '__main__':
    main()

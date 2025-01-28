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
import re

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.vmware.vmware.plugins.module_utils._vmware_folder_paths import format_folder_path_as_vm_fq_path
from ansible_collections.vmware.vmware.plugins.module_utils._module_rest_base import ModuleRestBase
from ansible_collections.vmware.vmware.plugins.module_utils._module_pyvmomi_base import ModulePyvmomiBase
from ansible_collections.vmware.vmware.plugins.module_utils._vmware_argument_spec import rest_compatible_argument_spec
from ansible.module_utils.common.text.converters import to_native
from ansible_collections.vmware.vmware.plugins.module_utils._vmware_tasks import (
    TaskError,
    RunningTaskMonitor
)

try:
    from com.vmware.vcenter.vm_template_client import LibraryItems as TemplateLibraryItems
    from com.vmware.vcenter.ovf_client import LibraryItem as OvfLibraryItems
    from com.vmware.vapi.std.errors_client import Error
except ImportError:
    pass

try:
    from pyVmomi import vim, vmodl
except ImportError:
    pass


class VmwareContentTemplate(ModulePyvmomiBase):
    def __init__(self, module):
        """Constructor."""
        super(VmwareContentTemplate, self).__init__(module)
        self.rest_base = ModuleRestBase(module)

        # Initialize member variables
        self.template_service = self.rest_base.api_client.vcenter.vm_template.LibraryItems
        self.ovf_service = self.api_client.vcenter.ovf.LibraryItem
        self.datacenter = self.get_datacenter_by_name_or_moid(self.params['datacenter'], fail_on_missing=True)
        self._library_item_id = self.params.get('library_item_id')

    @property
    def datastore_id(self):
        if self.params.get('datastore'):
            return self.get_datastore_by_name_or_moid(
                self.params['datastore'],
                fail_on_missing=True,
            )._GetMoId()

        # Find the datastore by the given datastore cluster name
        if self.params.get('datastore_cluster'):
            dsc = self._pyv.find_datastore_cluster_by_name(self.datastore_cluster)
            if dsc:
                self.datastore = self._pyv.get_recommended_datastore(dsc)
                self._datastore_id = self.get_datastore_by_name(self.datacenter, self.datastore)
            else:
                self._fail(msg="Failed to find the datastore cluster %s" % self.datastore_cluster)

    def get_deployment_folder(self):
        if not self.params.get('folder'):
            fq_folder = format_folder_path_as_vm_fq_path('', self.params['datacenter'])
        else:
            fq_folder = self.params.get('folder').strip('/')
            if not re.match('^%s' % self.params['datacenter'], fq_folder, re.I):
                # this is not a fully qualified path
                fq_folder = format_folder_path_as_vm_fq_path(fq_folder, self.params['datacenter'])

        return self.get_folder_by_absolute_path(fq_folder, fail_on_missing=True)

    @property
    def library_item_id(self):
        if self._library_item_id:
            return self._library_item_id

        if self.params['library_id']:
            library_id = self.params['library_id']
        else:
            library_ids = self.rest_base.get_content_library_ids(
                name=self.params['library_name'],
                fail_on_missing=True
            )
            if len(library_ids) > 1:
                self.module.fail_json(msg=(
                    "Found multiple libraries with the name %s. Try specifying library_id instead" %
                    self.params['library_name']
                ))
            library_id = library_ids[0]

        item_ids = self.rest_base.get_library_item_ids(
            name=self.params['library_item_name'],
            library_id=library_id,
            fail_on_missing=True
        )
        if len(item_ids) > 1:
            self.module.fail_json(msg=(
                "Found multiple library items (templates) with the name %s. Try specifying library_item_id instead" %
                self.params['library_item_name']
            ))
        self._library_item_id = item_ids[0]
        return self._library_item_id

    def create_template_deploy_spec(self):
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

    def create_ovf_deploy_spec(self):
        deployment_target = OvfLibraryItems.DeploymentTarget(
            resource_pool_id=self.get_resource_pool_by_name_or_moid(
                self.params['resource_pool'],
                fail_on_missing=True
            )._GetMoId(),
            folder_id=self.get_deployment_folder()._GetMoId()
        )

        ovf_summary = self.ovf_service.filter(
            ovf_library_item_id=self.library_item_id,
            target=deployment_target
        )

        deploy_spec = OvfLibraryItems.ResourcePoolDeploymentSpec(
            name=self.params['vm_name'],
            annotation=ovf_summary.annotation,
            accept_all_eula=True,
            network_mappings=None,
            storage_mappings=None,
            storage_provisioning=self.params['storage_provisioning'],
            storage_profile_id=None,
            locale=None,
            flags=None,
            additional_parameters=None,
            default_datastore_id=self.datastore_id
        )

        return deployment_target, deploy_spec

    def deploy_ovf(self, deployment_target, deploy_spec):
        try:
            response = self.ovf_service.deploy(
                self.library_item_id,
                deployment_target,
                deploy_spec
            )
        except Error as error:
            self._fail(msg="%s" % self.get_error_message(error))
        except Exception as err:
            self._fail(msg="%s" % to_native(err))

        if not response.succeeded:
            self.module.fail_json(msg=(
                "Failed to deploy OVF %s to VM %s" % (self.library_item_id, self.params['vm_name'])
            ))

        return response.resource_id.id

    def deploy_template(self, deploy_spec):
        try:
            return self.template_service.deploy(
                self.library_item_id,
                deploy_spec
            )
        except Error as error:
            self._fail(msg="%s" % self.get_error_message(error))
        except Exception as err:
            self._fail(msg="%s" % to_native(err))

    def get_deployed_vm(self):
        folder = self.get_deployment_folder()
        return self.get_objs_by_name_or_moid(
            vimtype=[vim.VirtualMachine],
            name=self.params['vm_name'],
            search_root_folder=folder
        )

    def delete_vm(self, vm):
        if vm.runtime.powerState.lower() == "poweredon":
            self.module.fail_json(msg="Cannot delete a VM in the powered on state: %s" % vm.name)
        try:
            task = vm.Destroy_Task()
            _, task_result = RunningTaskMonitor(task).wait_for_completion()   # pylint: disable=disallowed-name
        except (vmodl.RuntimeFault, vmodl.MethodFault)as vmodl_fault:
            self.module.fail_json(msg=to_native(vmodl_fault.msg))
        except TaskError as task_e:
            self.module.fail_json(msg=to_native(task_e))
        except Exception as generic_exc:
            self.module.fail_json(msg="Failed to delete VM due to exception %s" % to_native(generic_exc))

        return task_result


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
        ],
        required_if=[
            ('state', 'present', ('library_name', 'library_id',' library_item_name', 'library_item_id'), True),
        ]
    )

    result = {'changed': False}
    vmware_template = VmwareContentTemplate(module)
    vm = vmware_template.get_deployed_vm()

    if module.params['state'] == 'present':
        if not vm:
            result['changed'] = True
            spec = vmware_template.create_deploy_spec()
            vm = vmware_template.deploy_template(spec)
        result['vm_moid'] = vm._GetMoId()
        result['vm_name'] = vm.name

    elif module.params['state'] == 'absent':
        if vm:
            result['changed'] = True
            vmware_template.delete_vm(vm)

    module.exit(**result)



if __name__ == '__main__':
    main()

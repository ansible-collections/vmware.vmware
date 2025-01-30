# Copyright: (c) 2024, Ansible Cloud Team
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import absolute_import, division, print_function

__metaclass__ = type

import re
from abc import abstractmethod
from ansible_collections.vmware.vmware.plugins.module_utils._vmware_folder_paths import format_folder_path_as_vm_fq_path
from ansible_collections.vmware.vmware.plugins.module_utils._module_rest_base import ModuleRestBase
from ansible_collections.vmware.vmware.plugins.module_utils._module_pyvmomi_base import ModulePyvmomiBase
from ansible.module_utils.common.text.converters import to_native
from ansible_collections.vmware.vmware.plugins.module_utils._vmware_tasks import (
    TaskError,
    RunningTaskMonitor
)

try:
    from pyVmomi import vim, vmodl
except ImportError:
    pass


class VmwareContentDeploy(ModulePyvmomiBase):
    def __init__(self, module):
        """Constructor."""
        super(VmwareContentDeploy, self).__init__(module)
        self.rest_base = ModuleRestBase(module)

        # Initialize member variables
        self.datacenter = self.get_datacenter_by_name_or_moid(self.params['datacenter'], fail_on_missing=True)
        self._library_item_id = self.params.get('library_item_id')

    @property
    def datastore_id(self):
        if self.params.get('datastore'):
            return self.get_datastore_by_name_or_moid(
                self.params['datastore'],
                fail_on_missing=True,
            )._GetMoId()

        if self.params.get('datastore_cluster'):
            dsc = self.get_datastore_cluster_by_name_or_moid(
                self.params['datastore_cluster'],
                fail_on_missing=True,
                datacenter=self.datacenter
            )
            datastore = self.get_sdrs_recommended_datastore_from_ds_cluster(dsc)
            if not datastore:
                datastore = self.get_datastore_with_max_free_space(dsc.childEntity)
            return datastore._GetMoId()

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
                "Found multiple library items with the name %s. Try specifying library_item_id, library_name, or library_id" %
                self.params['library_item_name']
            ))
        self._library_item_id = item_ids[0]
        return self._library_item_id

    @abstractmethod
    def create_deploy_spec(self):
        raise NotImplementedError

    @abstractmethod
    def deploy(self):
        raise NotImplementedError

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

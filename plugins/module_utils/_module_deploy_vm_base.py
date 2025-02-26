# Copyright: (c) 2024, Ansible Cloud Team
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import absolute_import, division, print_function

__metaclass__ = type

from abc import abstractmethod
from ansible_collections.vmware.vmware.plugins.module_utils._vmware_folder_paths import format_folder_path_as_vm_fq_path
from ansible_collections.vmware.vmware.plugins.module_utils._module_pyvmomi_base import ModulePyvmomiBase

try:
    from pyVmomi import vim
except ImportError:
    pass


def vm_deploy_module_argument_spec():
    return dict(
        vm_name=dict(type='str', required=True),
        vm_folder=dict(type='str', required=False, aliases=['folder']),
        cluster=dict(type='str', required=False, aliases=['cluster_name']),
        resource_pool=dict(type='str', required=False),
        datacenter=dict(type='str', required=True, aliases=['datacenter_name']),
        datastore=dict(type='str', required=False),
        datastore_cluster=dict(type='str', required=False),
    )


class ModuleVmDeployBase(ModulePyvmomiBase):
    def __init__(self, module):
        super().__init__(module)
        self.datacenter = self.get_datacenter_by_name_or_moid(self.params['datacenter'], fail_on_missing=True)
        self._vm_folder = None
        self._datastore = None
        self._resource_pool = None

    @property
    def datastore(self):
        if self._datastore:
            return self._datastore

        if self.params.get('datastore'):
            self._datastore = self.get_datastore_by_name_or_moid(
                self.params['datastore'],
                fail_on_missing=True,
            )
        elif self.params.get('datastore_cluster'):
            dsc = self.get_datastore_cluster_by_name_or_moid(
                self.params['datastore_cluster'],
                fail_on_missing=True,
                datacenter=self.datacenter
            )
            datastore = self.get_sdrs_recommended_datastore_from_ds_cluster(dsc)
            if not datastore:
                datastore = self.get_datastore_with_max_free_space(dsc.childEntity)
            self._datastore = datastore

        return self._datastore

    @property
    def resource_pool(self):
        if self._resource_pool:
            return self._resource_pool

        if self.params['resource_pool']:
            self._resource_pool = self.get_resource_pool_by_name_or_moid(
                self.params['resource_pool'],
                fail_on_missing=True
            )
        elif self.params['cluster']:
            cluster = self.get_cluster_by_name_or_moid(
                self.params['cluster'],
                fail_on_missing=True,
                datacenter=self.datacenter
            )
            self._resource_pool = cluster.resourcePool

        return self._resource_pool

    @property
    def vm_folder(self):
        if self._vm_folder:
            return self._vm_folder
        if not self.params.get('vm_folder'):
            fq_folder = format_folder_path_as_vm_fq_path('', self.params['datacenter'])
        else:
            fq_folder = format_folder_path_as_vm_fq_path(self.params.get('vm_folder'), self.params['datacenter'])

        self._vm_folder = self.get_folder_by_absolute_path(fq_folder, fail_on_missing=True)
        return self._vm_folder

    @property
    def library_item_id(self):
        if self._library_item_id:
            return self._library_item_id

        if self.params['library_id']:
            library_id = self.params['library_id']
        elif self.params['library_name']:
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
        else:
            library_id = None

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

    def get_deployed_vm(self):
        vms = self.get_objs_by_name_or_moid(
            vimtype=[vim.VirtualMachine],
            name=self.params['vm_name'],
            search_root_folder=self.vm_folder
        )
        if vms:
            return vms[0]
        return None

    @abstractmethod
    def create_deploy_spec(self):
        raise NotImplementedError

    @abstractmethod
    def deploy(self):
        raise NotImplementedError

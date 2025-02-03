# Copyright: (c) 2024, Ansible Cloud Team
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

try:
    from pyVmomi import (
        vim,
        vmodl
    )
except ImportError:
    pass
    # handled in base class

from ansible_collections.vmware.vmware.plugins.module_utils.clients._pyvmomi import PyvmomiClient


class ModulePyvmomiBase(PyvmomiClient):
    def __init__(self, module):
        super().__init__(module.params)
        self.module = module
        self.params = module.params

    def is_vcenter(self):
        """
        Check if given hostname is vCenter or ESXi host
        Returns: True if given connection is with vCenter server
                 False if given connection is with ESXi server

        """
        api_type = None
        try:
            api_type = self.content.about.apiType
        except (vmodl.RuntimeFault, vim.fault.VimFault) as exc:
            self.module.fail_json(msg="Failed to get status of vCenter server : %s" % exc.msg)

        if api_type == 'VirtualCenter':
            return True
        elif api_type == 'HostAgent':
            return False

    def get_objs_by_name_or_moid(self, vimtype, name, return_all=False, search_root_folder=None):
        """
        Get any vsphere objects associated with a given text name or MOID and vim type.
        Different objects have different unique-ness requirements for the name parameter, so
        you may get one or more objects back. The MOID should always be unique
        Args:
            vimtype: The type of object to search for
            name: The name or the ID of the object to search for
            return_all: If true, return all the objects that were found.
                        Useful when names must be unique
            search_root_folder: The folder object that should be used as the starting point
                                for searches. Useful for restricting search results to a
                                certain datacenter (search_root_folder=datacenter.hostFolder)
        Returns:
            list(object) or list() if no matches are found
        """
        if not search_root_folder:
            search_root_folder = self.content.rootFolder

        obj = list()
        container = self.content.viewManager.CreateContainerView(
            search_root_folder, vimtype, True)

        for c in container.view:
            if name in [c.name, c._GetMoId()]:
                if return_all is False:
                    return c
                else:
                    obj.append(c)

        if len(obj) > 0:
            return obj
        else:
            # for backwards-compat
            return None

    def get_standard_portgroup_by_name_or_moid(self, identifier, fail_on_missing=False):
        """
        Get a portgroup from type 'STANDARD_PORTGROUP' based on name or MOID
        Args:
            identifier: The name or the ID of the portgroup
            fail_on_missing: If true, an error will be thrown if no networks are found
        Returns:
            The standard portgroup object
        """
        pg = self.get_objs_by_name_or_moid([vim.Network], identifier)
        if not pg and fail_on_missing:
            self.module.fail_json(msg="Unable to find standard portgroup with name or MOID %s" % identifier)
        return pg

    def get_dvs_portgroup_by_name_or_moid(self, identifier, fail_on_missing=False):
        """
        Get a portgroup from type 'DISTRIBUTED_PORTGROUP' based on name or MOID
        Args:
            identifier: The name or the ID of the portgroup
            fail_on_missing: If true, an error will be thrown if no networks are found
        Returns:
            The distributed portgroup object
        """
        pg = self.get_objs_by_name_or_moid([vim.dvs.DistributedVirtualPortgroup], identifier)
        if not pg and fail_on_missing:
            self.module.fail_json(msg="Unable to find distributed portgroup with name or MOID %s" % identifier)
        return pg

    def get_vm_using_params(
            self, name_param='name', uuid_param='uuid', moid_param='moid', fail_on_missing=False,
            name_match_param='name_match', use_instance_uuid_param='use_instance_uuid'):
        """
            Get the vms matching the common module params related to vm identification: name, uuid, or moid. Since
            MOID and UUID are unique identifiers, they are tried first. If they are not set, a search by name is tried
            which may give one or more vms.
            This also supports the 'name_match' parameter and the 'use_instance_uuid' parameters. The VM identification
            parameter keys can be changed if your module uses different keys, like vm_name instead of just name
            Args:
                name_param: Set the parameter key that corredsponds to the VM name
                uuid_param: Set the parameter key that corredsponds to the VM UUID
                moid_param: Set the parameter key that corredsponds to the VM MOID
                name_match_param: Set the parameter key that corredsponds to the name_match option
                use_instance_uuid_param: Set the parameter key that corredsponds use_instance_uuid option
                fail_on_missing: If true, an error will be thrown if no VMs are found
            Returns:
                list(vm), or None if no matches were found
        """
        if self.params.get(moid_param):
            _search_type, _search_id, _search_value = 'moid', moid_param, self.params.get(moid_param)
        elif self.params.get(uuid_param):
            _search_type, _search_id, _search_value = 'uuid', uuid_param, self.params.get(uuid_param)
        elif self.params.get(name_param):
            _search_type, _search_id, _search_value = 'name', name_param, self.params.get(name_param)
        else:
            if fail_on_missing:
                self.module.fail_json(msg="Could not find any supported VM identifier params (name, uuid, or moid)")
            else:
                return None

        if _search_type == 'uuid':
            _vm = self.si.content.searchIndex.FindByUuid(
                instanceUuid=self.params.get(use_instance_uuid_param, True),
                uuid=_search_value,
                vmSearch=True
            )
            vms = [_vm] if _vm else None
        else:
            vms = self.get_objs_by_name_or_moid([vim.VirtualMachine], _search_value, return_all=True)

        if vms and _search_type == 'name' and self.params.get(name_match_param):
            if self.params.get(name_match_param) == 'first':
                return [vms[0]]
            elif self.params.get(name_match_param) == 'last':
                return [vms[-1]]
            else:
                self.module.fail_json(msg="Unrecognized name_match option '%s' " % self.params.get(name_match_param))

        if not vms and fail_on_missing:
            self.module.fail_json(msg="Unable to find VM with %s %s" % (_search_id, _search_value))

        return vms

    def get_folders_by_name_or_moid(self, identifier, fail_on_missing=False):
        """
            Get all folders with the given name or MOID. Names are not unique
            in a given cluster, so multiple folder objects can be returned
            Args:
                identifier: Name or MOID of the folder to search for
                fail_on_missing: If true, an error will be thrown if no folders are found
            Returns:
                list(folder object) or None
        """
        folder = self.get_objs_by_name_or_moid([vim.Folder], identifier, return_all=True)
        if not folder and fail_on_missing:
            self.module.fail_json(msg="Unable to find folder with name or MOID %s" % identifier)
        return folder

    def get_folder_by_absolute_path(self, folder_path, fail_on_missing=False):
        """
            Get a folder with the given path. Paths are unique when they are absolute so only
            one folder can be returned at most. An absolute path might look like
            'Datacenter Name/vm/my/folder/structure'
            Args:
                folder_path: The absolute path to a folder to search for
                fail_on_missing: If true, an error will be thrown if no folders are found
            Returns:
                folder object or None
        """
        folder = self.si.content.searchIndex.FindByInventoryPath(folder_path)

        if not folder and fail_on_missing:
            self.module.fail_json(msg="Unable to find folder with absolute path %s" % folder_path)
        return folder

    def get_datastore_by_name_or_moid(self, identifier, fail_on_missing=False):
        """
            Get the datastore matching the given name or MOID. Datastore names must be unique
            in a given cluster, so only one object is returned at most.
            Args:
                identifier: Name or MOID of the datastore to search for
                fail_on_missing: If true, an error will be thrown if no datastores are found
            Returns:
                datastore object or None
        """
        ds = self.get_objs_by_name_or_moid([vim.Datastore], identifier)
        if not ds and fail_on_missing:
            self.module.fail_json(msg="Unable to find datastore with name or MOID %s" % identifier)
        return ds

    def get_datastore_cluster_by_name_or_moid(self, identifier, fail_on_missing=False, datacenter=None):
        """
            Get the datastore cluster matching the given name or MOID. Datastore cluster names must
            be unique in a given datacenter, so only one object is returned at most.
            Args:
                identifier: Name or MOID of the datastore cluster to search for
                fail_on_missing: If true, an error will be thrown if no clusters are found
                datacenter: The datacenter object to use as a filter when searching for clusters. If
                            not provided then all datacenters will be examined
            Returns:
                datastore cluster object or None

        """
        search_folder = None
        if datacenter and hasattr(datacenter, 'datastoreFolder'):
            search_folder = datacenter.hostFolder

        data_store_cluster = self.get_objs_by_name_or_moid(
            [vim.StoragePod],
            identifier,
            return_all=False,
            search_root_folder=search_folder
        )

        if not data_store_cluster and fail_on_missing:
            self.module.fail_json(msg="Unable to find datastore cluster with name or MOID %s" % identifier)

        return data_store_cluster

    def get_resource_pool_by_name_or_moid(self, identifier, fail_on_missing=False):
        """
            Get the resource pool matching the given name or MOID. Pool names must be unique
            in a given cluster, so only one object is returned at most.
            Args:
                identifier: Name or MOID of the pool to search for
                fail_on_missing: If true, an error will be thrown if no pools are found
            Returns:
                resource pool object or None
        """
        pool = self.get_objs_by_name_or_moid([vim.ResourcePool], identifier)
        if not pool and fail_on_missing:
            self.module.fail_json(msg="Unable to find resource pool with name %s" % identifier)
        return pool

    def get_all_vms(self, folder=None, recurse=True):
        """
            Get all virtual machines in a folder. Can recurse through folder tree if needed. If no folder
            is provided, then the datacenter root folder is used
            Args:
                folder: vim.Folder, the folder object to use as a base for the search. If
                        none is provided, the datacenter root will be used
                recurse: If true, the search will recurse through the folder structure
            Returns:
                list of vim.VirtualMachine
        """
        return self.get_all_objs_by_type([vim.VirtualMachine], folder=folder, recurse=recurse)

    def get_datacenter_by_name_or_moid(self, identifier, fail_on_missing=False):
        """
            Get the datacenter matching the given name or MOID. Datacenter names must be unique
            in a given vcenter, so only one object is returned at most.
            Args:
                identifier: Name or MOID of the datacenter to search for
                fail_on_missing: If true, an error will be thrown if no datacenters are found
            Returns:
                datacenter object or None
        """
        ds = self.get_objs_by_name_or_moid([vim.Datacenter], identifier)
        if not ds and fail_on_missing:
            self.module.fail_json(msg="Unable to find datacenter with name or MOID %s" % identifier)
        return ds

    def get_cluster_by_name_or_moid(self, identifier, fail_on_missing=False, datacenter=None):
        """
            Get the cluster matching the given name or MOID. Cluster names must be unique
            in a given vcenter, so only one object is returned at most.
            Args:
                identifier: Name or MOID of the cluster to search for
                fail_on_missing: If true, an error will be thrown if no clusters are found
                datacenter: The datacenter object to use as a filter when searching for clusters. If
                            not provided then all datacenters will be examined
            Returns:
                cluster object or None
        """
        search_folder = None
        if datacenter and hasattr(datacenter, 'hostFolder'):
            search_folder = datacenter.hostFolder

        cluster = self.get_objs_by_name_or_moid(
            [vim.ClusterComputeResource],
            identifier,
            return_all=False,
            search_root_folder=search_folder
        )

        if not cluster and fail_on_missing:
            self.module.fail_json(msg="Unable to find cluster with name or MOID %s" % identifier)

        return cluster

    def get_esxi_host_by_name_or_moid(self, identifier, fail_on_missing=False):
        """
            Get the ESXi host matching the given name or MOID. ESXi names must be unique in a
            vCenter, so at most one host is returned.
            Args:
                identifier: Name or MOID of the ESXi host to search for
                fail_on_missing: If true, an error will be thrown if no hosts are found
            Returns:
                esxi host object or None
        """
        esxi_host = self.get_objs_by_name_or_moid(
            [vim.HostSystem],
            identifier,
            return_all=False,
        )

        if not esxi_host and fail_on_missing:
            self.module.fail_json(msg="Unable to find ESXi host with name or MOID %s" % identifier)

        return esxi_host

    def get_sdrs_recommended_datastore_from_ds_cluster(self, ds_cluster):
        """
            Returns the Storage DRS recommended datastore from a datastore cluster
            Args:
                ds_cluster: datastore cluster managed object

            Returns:
                Datastore object, or none if sdrs is not configured for the cluster

        """
        # Check if Datastore Cluster provided by user is SDRS ready
        if not ds_cluster.podStorageDrsEntry.storageDrsConfig.podConfig.enabled:
            return None

        pod_sel_spec = vim.storageDrs.PodSelectionSpec()
        pod_sel_spec.storagePod = ds_cluster
        storage_spec = vim.storageDrs.StoragePlacementSpec()
        storage_spec.podSelectionSpec = pod_sel_spec
        storage_spec.type = 'create'

        rec = self.content.storageResourceManager.RecommendDatastores(storageSpec=storage_spec)
        rec_action = rec.recommendations[0].action[0]
        return rec_action.destination

    def get_datastore_with_max_free_space(self, datastores):
        """
            Returns the datasotre object with the maximum amount of freespace from a list of datastores.
            Args:
                datastores: list of datastore managed objects

            Returns:
                Datastore object

        """
        datastore = None
        datastore_freespace = 0
        for ds in datastores:
            if isinstance(ds, vim.Datastore) and ds.summary.freeSpace > datastore_freespace:
                if ds.summary.maintenanceMode == 'normal' and ds.summary.accessible:
                    datastore = ds
                    datastore_freespace = ds.summary.freeSpace

        return datastore

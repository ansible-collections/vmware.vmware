from ansible_collections.vmware.vmware.plugins.module_utils._folder_paths import (
    format_folder_path_as_vm_fq_path,
)
from ansible_collections.vmware.vmware.plugins.module_utils._module_pyvmomi_base import (
    ModulePyvmomiBase,
)


def vm_placement_argument_spec(omit_params=[]):
    arg_spec = dict(
        folder=dict(type="str", required=False, aliases=["vm_folder"]),
        cluster=dict(type="str", required=False, aliases=["cluster_name"]),
        esxi_host=dict(type="str", required=False),
        resource_pool=dict(type="str", required=False),
        datacenter=dict(type="str", required=False, aliases=["datacenter_name"]),
        datastore=dict(type="str", required=False),
        datastore_cluster=dict(type="str", required=False),
    )
    for param in omit_params:
        if param in arg_spec:
            del arg_spec[param]

    return arg_spec


class VmPlacement(ModulePyvmomiBase):
    def __init__(self, module):
        super().__init__(module)
        self._datacenter = None
        self._folder = None
        self._datastore = None
        self._resource_pool = None
        self._esxi_host = None

    def get_datacenter(self, param="datacenter"):
        if self._datacenter:
            return self._datacenter

        self._datacenter = self.get_datacenter_by_name_or_moid(
            self.params[param], fail_on_missing=True
        )
        return self._datacenter

    def get_datastore(
        self, datastore_param="datastore", datastore_cluster_param="datastore_cluster"
    ):
        if self._datastore:
            return self._datastore

        if self.params.get(datastore_param):
            self._datastore = self.get_datastore_by_name_or_moid(
                self.params[datastore_param],
                fail_on_missing=True,
            )
        elif self.params.get(datastore_cluster_param):
            dsc = self.get_datastore_cluster_by_name_or_moid(
                self.params[datastore_cluster_param],
                fail_on_missing=True,
                datacenter=self.get_datacenter(),
            )
            datastore = self.get_datastore_with_max_free_space(dsc.childEntity)
            self._datastore = datastore

        return self._datastore

    def get_resource_pool(
        self, resource_pool_param="resource_pool", cluster_param="cluster"
    ):
        if self._resource_pool:
            return self._resource_pool

        if self.params.get(resource_pool_param):
            self._resource_pool = self.get_resource_pool_by_name_or_moid(
                self.params[resource_pool_param], fail_on_missing=True
            )
        elif self.params.get(cluster_param):
            cluster = self.get_cluster_by_name_or_moid(
                self.params[cluster_param],
                fail_on_missing=True,
                datacenter=self.get_datacenter(),
            )
            self._resource_pool = cluster.resourcePool

        return self._resource_pool

    def get_folder(self, folder_param="folder", datacenter_param="datacenter"):
        if self._folder:
            return self._folder
        if not self.params.get(folder_param):
            fq_folder = format_folder_path_as_vm_fq_path(
                "", self.params[datacenter_param]
            )
        else:
            fq_folder = format_folder_path_as_vm_fq_path(
                self.params.get(folder_param), self.params[datacenter_param]
            )

        self._folder = self.get_folder_by_absolute_path(fq_folder, fail_on_missing=True)
        return self._folder

    def get_esxi_host(self, param="esxi_host"):
        if self._esxi_host or self.params[param] is None:
            return self._esxi_host

        self._esxi_host = self.get_esxi_host_by_name_or_moid(
            self.params[param], fail_on_missing=True
        )
        return self._esxi_host

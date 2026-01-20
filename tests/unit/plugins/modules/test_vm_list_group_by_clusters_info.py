from __future__ import absolute_import, division, print_function
__metaclass__ = type

import sys
import pytest

from ansible_collections.vmware.vmware.plugins.modules.vm_list_group_by_clusters_info import (
    main as module_main
)
from ansible_collections.vmware.vmware.plugins.module_utils.clients.pyvmomi import (
    PyvmomiClient
)
from ansible_collections.vmware.vmware.plugins.module_utils.clients.rest import (
    VmwareRestClient
)
from ...common.utils import (
    run_module, ModuleTestCase
)
from ...common.vmware_object_mocks import (
    create_mock_vsphere_object
)

pytestmark = pytest.mark.skipif(
    sys.version_info < (2, 7), reason="requires python2.7 or higher"
)


def create_mock_cluster():
    cluster = create_mock_vsphere_object(name="cluster1")
    cluster.cluster = cluster._moid
    return cluster


def create_mock_folder():
    folder = create_mock_vsphere_object(name="folder1")
    folder.folder = folder._moid
    return folder


class TestVmwareVMList(ModuleTestCase):

    def __prepare(self, mocker):
        self.rest_client = mocker.Mock()
        mocker.patch.object(VmwareRestClient, 'connect_to_api', return_value=self.rest_client)
        self.rest_client.vcenter.Cluster.list.return_value = [create_mock_cluster()]
        self.rest_client.vcenter.Folder.list.return_value = [create_mock_folder()]
        self.mock_vm = create_mock_vsphere_object(name="vm1")
        self.rest_client.vcenter.VM.list.return_value = [self.mock_vm]
        self.rest_client.vcenter.VM.get.return_value = self.mock_vm
        self.rest_client.vcenter.Host.list.return_value = [create_mock_vsphere_object()]

        mocker.patch.object(PyvmomiClient, 'connect_to_api', return_value=(mocker.Mock(), mocker.Mock()))
        mocker.patch(
            "ansible_collections.vmware.vmware.plugins.modules.vm_list_group_by_clusters_info.ModulePyvmomiBase.get_cluster_by_name_or_moid",
            return_value=create_mock_cluster(),
        )
        mocker.patch(
            "ansible_collections.vmware.vmware.plugins.modules.vm_list_group_by_clusters_info.ModulePyvmomiBase.get_folders_by_name_or_moid",
            return_value=[create_mock_folder()],
        )
        mocker.patch(
            "ansible_collections.vmware.vmware.plugins.modules.vm_list_group_by_clusters_info.get_folder_path_of_vsphere_object",
            return_value="",
        )

    def test_defaults(self, mocker):
        self.__prepare(mocker)

        module_args = dict(
        )

        result = run_module(module_entry=module_main, module_args=module_args)

        assert result["changed"] is False
        assert result["vm_list_group_by_clusters_info"] != {}

    def test_use_absolute_path_for_group_name(self, mocker):
        self.__prepare(mocker)

        module_args = dict(
            use_absolute_path_for_group_name=True
        )

        result = run_module(module_entry=module_main, module_args=module_args)

        assert result["changed"] is False
        assert result["vm_list_group_by_clusters_info"] != {}
        assert result["vm_list_group_by_clusters_info"]["/cluster1"]["/folder1"][0]["name"] == self.mock_vm.name

    def test_detailed_vms(self, mocker):
        self.__prepare(mocker)

        module_args = dict(
            detailed_vms=True
        )

        result = run_module(module_entry=module_main, module_args=module_args)

        assert result["changed"] is False
        assert result["vm_list_group_by_clusters_info"] != {}
        assert result["vm_list_group_by_clusters_info"]["cluster1"]["folder1"][0]["name"] == self.mock_vm.name

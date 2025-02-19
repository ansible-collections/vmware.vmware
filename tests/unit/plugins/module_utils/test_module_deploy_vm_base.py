from __future__ import absolute_import, division, print_function
__metaclass__ = type

import sys
import pytest

from ansible_collections.vmware.vmware.plugins.modules.deploy_folder_template import (
    VmwareFolderTemplate
)
from ansible_collections.vmware.vmware.plugins.module_utils.clients._pyvmomi import (
    PyvmomiClient
)

from ...common.vmware_object_mocks import (
    MockVmwareObject
)

pytestmark = pytest.mark.skipif(
    sys.version_info < (2, 7), reason="requires python2.7 or higher"
)


class TestDeployContentLibraryOvf():

    def __prepare(self, mocker):
        mocker.patch.object(PyvmomiClient, 'connect_to_api', return_value=(mocker.Mock(), mocker.Mock()))
        self.mock_module = mocker.Mock()
        self.mock_module.params = dict(
            hostname="127.0.0.1",
            username="administrator@local",
            password="123456",
            add_cluster=False,
            vm_name='foo',
            vm_folder='foo/bar',
            library_item_id='111',
            datastore='foo',
            datacenter='foo',
            resource_pool='foo'
        )

        mocker.patch.object(VmwareFolderTemplate, 'get_datacenter_by_name_or_moid', return_value=MockVmwareObject())

    def test_datastore(self, mocker):
        self.__prepare(mocker)
        mocker.patch.object(VmwareFolderTemplate, 'get_datastore_by_name_or_moid', return_value=MockVmwareObject())
        test_module = VmwareFolderTemplate(self.mock_module)
        assert test_module.datastore._GetMoId()

    def test_resource_pool(self, mocker):
        self.__prepare(mocker)
        mocker.patch.object(VmwareFolderTemplate, 'get_resource_pool_by_name_or_moid', return_value=MockVmwareObject())
        test_module = VmwareFolderTemplate(self.mock_module)
        assert test_module.resource_pool._GetMoId()

    def test_vm_folder(self, mocker):
        self.__prepare(mocker)
        folder_obj = MockVmwareObject()
        mocker.patch.object(VmwareFolderTemplate, 'get_folder_by_absolute_path', return_value=folder_obj)
        test_module = VmwareFolderTemplate(self.mock_module)
        assert test_module.vm_folder is folder_obj

    def test_get_deployed_vm(self, mocker):
        self.__prepare(mocker)
        mocker.patch.object(VmwareFolderTemplate, 'get_objs_by_name_or_moid', return_value=[mocker.Mock()])
        test_module = VmwareFolderTemplate(self.mock_module)
        assert test_module.get_deployed_vm()

        mocker.patch.object(VmwareFolderTemplate, 'get_objs_by_name_or_moid', return_value=[])
        assert test_module.get_deployed_vm() is None

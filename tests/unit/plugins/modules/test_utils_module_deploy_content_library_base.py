from __future__ import absolute_import, division, print_function
__metaclass__ = type

import sys
import pytest

from ansible_collections.vmware.vmware.plugins.module_utils._module_deploy_content_library_base import (
    VmwareContentDeploy
)
from ansible_collections.vmware.vmware.plugins.module_utils.clients._pyvmomi import (
    PyvmomiClient
)
from ansible_collections.vmware.vmware.plugins.module_utils.clients._rest import (
    VmwareRestClient
)

from .common.vmware_object_mocks import (
    MockVmwareObject
)

pytestmark = pytest.mark.skipif(
    sys.version_info < (2, 7), reason="requires python2.7 or higher"
)


class TestDeployContentLibraryOvf():

    def __prepare(self, mocker):
        mocker.patch.object(PyvmomiClient, 'connect_to_api', return_value=(mocker.Mock(), mocker.Mock()))
        mocker.patch.object(VmwareRestClient, 'connect_to_api', return_value=mocker.Mock())
        self.mock_module = mocker.Mock()
        self.mock_module.params = dict(
            hostname="127.0.0.1",
            username="administrator@local",
            password="123456",
            add_cluster=False,
            vm_name='foo',
            library_item_id='111',
            datastore='foo',
            datacenter='foo',
            resource_pool='foo'
        )

        mocker.patch.object(VmwareContentDeploy, 'get_resource_pool_by_name_or_moid', return_value=MockVmwareObject())
        mocker.patch.object(VmwareContentDeploy, 'get_datastore_by_name_or_moid', return_value=MockVmwareObject())
        mocker.patch.object(VmwareContentDeploy, 'get_datacenter_by_name_or_moid', return_value=MockVmwareObject())
        mocker.patch.object(VmwareContentDeploy, 'delete_vm', return_value={})

    def test_delete(self, mocker):
        self.__prepare(mocker)
        test_module = VmwareContentDeploy(self.mock_module)
        test_module.delete_vm()

    def test_get_deployment_folder(self, mocker):
        self.__prepare(mocker)
        test_module = VmwareContentDeploy(self.mock_module)
        assert test_module.get_deployment_folder()

    def test_datastore_id(self, mocker):
        self.__prepare(mocker)
        test_module = VmwareContentDeploy(self.mock_module)
        assert test_module.datastore_id

    def test_library_item_id(self, mocker):
        self.__prepare(mocker)
        test_module = VmwareContentDeploy(self.mock_module)
        assert test_module.library_item_id

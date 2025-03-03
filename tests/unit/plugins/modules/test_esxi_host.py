from __future__ import absolute_import, division, print_function
__metaclass__ = type

import sys
import pytest

from ansible_collections.vmware.vmware.plugins.modules.esxi_host import (
    VmwareHost,
    main as module_main
)
from ansible_collections.vmware.vmware.plugins.module_utils.clients._pyvmomi import (
    PyvmomiClient
)
from ...common.utils import (
    AnsibleExitJson, ModuleTestCase, set_module_args,
)
from ...common.vmware_object_mocks import (
    create_mock_vsphere_object,
    MockVsphereTask
)

pytestmark = pytest.mark.skipif(
    sys.version_info < (2, 7), reason="requires python2.7 or higher"
)


class TestEsxiHost(ModuleTestCase):

    def __prepare(self, mocker):
        mocker.patch.object(PyvmomiClient, 'connect_to_api', return_value=(mocker.Mock(), mocker.Mock()))
        self.test_esxi = create_mock_vsphere_object()
        self.test_esxi.runtime.inMaintenanceMode = True
        self.mock_cluster = mocker.Mock()
        self.mock_folder = mocker.Mock()
        self.mock_folder._GetMoId.return_value = '1'

        mocker.patch.object(VmwareHost, 'get_datacenter_by_name_or_moid')
        mocker.patch.object(VmwareHost, 'get_cluster_by_name_or_moid', return_value=self.mock_cluster)
        mocker.patch.object(VmwareHost, 'get_folder_by_absolute_path', return_value=self.mock_folder)

    def test_no_change(self, mocker):
        self.__prepare(mocker)

        self.test_esxi.parent = self.mock_cluster
        mocker.patch.object(VmwareHost, 'get_esxi_host_by_name_or_moid', return_value=self.test_esxi)
        set_module_args(
            hostname="127.0.0.1",
            username="administrator@local",
            password="123456",
            add_cluster=True,
            datacenter='foo',
            esxi_host_name=self.test_esxi.name,
            esxi_username="foo",
            esxi_password="foo"
        )
        with pytest.raises(AnsibleExitJson) as c:
            module_main()

        assert c.value.args[0]["changed"] is False

        self.test_esxi.parent.parent = self.mock_folder
        mocker.patch.object(VmwareHost, 'get_esxi_host_by_name_or_moid', return_value=self.test_esxi)
        set_module_args(
            hostname="127.0.0.1",
            username="administrator@local",
            password="123456",
            add_cluster=False,
            datacenter='foo',
            folder='bar',
            esxi_host_name=self.test_esxi.name,
            esxi_username="foo",
            esxi_password="foo"
        )
        with pytest.raises(AnsibleExitJson) as c:
            module_main()

        assert c.value.args[0]["changed"] is False

        mocker.patch.object(VmwareHost, 'get_esxi_host_by_name_or_moid', return_value=None)

        set_module_args(
            hostname="127.0.0.1",
            username="administrator@local",
            password="123456",
            add_cluster=True,
            datacenter='foo',
            esxi_host_name=self.test_esxi.name,
            state='absent'
        )
        with pytest.raises(AnsibleExitJson) as c:
            module_main()

        assert c.value.args[0]["changed"] is False

    def test_state_present(self, mocker):
        self.__prepare(mocker)

        self.test_esxi.parent = self.mock_folder
        self.mock_folder.AddStandaloneHost.return_value = MockVsphereTask()
        self.mock_folder.AddStandaloneHost.return_value.info.result = self.test_esxi
        mocker.patch.object(VmwareHost, 'get_esxi_host_by_name_or_moid', return_value=None)
        set_module_args(
            hostname="127.0.0.1",
            username="administrator@local",
            password="123456",
            add_cluster=False,
            datacenter='foo',
            folder="foo/vm/bar",
            esxi_host_name=self.test_esxi.name,
            ssl_thumbprint='fdsfadf',
            esxi_username="foo",
            esxi_password="foo"
        )
        with pytest.raises(AnsibleExitJson) as c:
            module_main()

        assert c.value.args[0]["changed"] is True

    def test_state_present_move(self, mocker):
        self.__prepare(mocker)

        self.test_esxi.parent = self.mock_folder
        self.mock_cluster.MoveHostInto_Task.return_value = MockVsphereTask()
        mocker.patch.object(VmwareHost, 'get_esxi_host_by_name_or_moid', return_value=self.test_esxi)
        set_module_args(
            hostname="127.0.0.1",
            username="administrator@local",
            password="123456",
            add_cluster=True,
            datacenter='foo',
            esxi_host_name=self.test_esxi.name,
            ssl_thumbprint='fdsfadf',
            esxi_username="foo",
            esxi_password="foo"
        )
        with pytest.raises(AnsibleExitJson) as c:
            module_main()

        assert c.value.args[0]["changed"] is True

    def test_state_absent(self, mocker):
        self.__prepare(mocker)

        self.test_esxi.parent = self.mock_folder
        self.mock_folder.Destroy_Task.return_value = MockVsphereTask()
        mocker.patch.object(VmwareHost, 'get_esxi_host_by_name_or_moid', return_value=self.test_esxi)
        set_module_args(
            hostname="127.0.0.1",
            username="administrator@local",
            password="123456",
            add_cluster=False,
            datacenter='foo',
            folder="foo/vm/bar",
            esxi_host_name=self.test_esxi.name,
            state='absent',
            esxi_username="foo",
            esxi_password="foo"
        )
        with pytest.raises(AnsibleExitJson) as c:
            module_main()

        assert c.value.args[0]["changed"] is True

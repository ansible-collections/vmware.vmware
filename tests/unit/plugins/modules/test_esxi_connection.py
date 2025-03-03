from __future__ import absolute_import, division, print_function
__metaclass__ = type

import sys
import pytest

from ansible_collections.vmware.vmware.plugins.modules.esxi_connection import (
    VmwareHostConnection,
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


class TestEsxiConnection(ModuleTestCase):

    def __prepare(self, mocker):
        mocker.patch.object(PyvmomiClient, 'connect_to_api', return_value=(mocker.Mock(), mocker.Mock()))
        self.test_esxi = create_mock_vsphere_object()

        mocker.patch.object(VmwareHostConnection, 'get_datacenter_by_name_or_moid')
        mocker.patch.object(VmwareHostConnection, 'get_esxi_host_by_name_or_moid', return_value=self.test_esxi)

    def test_no_change(self, mocker):
        self.__prepare(mocker)
        self.test_esxi.runtime.connectionState = 'connected'

        set_module_args(
            hostname="127.0.0.1",
            username="administrator@local",
            password="123456",
            add_cluster=False,
            datacenter="",
            esxi_host_name=self.test_esxi.name,
            state="connected"
        )
        with pytest.raises(AnsibleExitJson) as c:
            module_main()

        assert c.value.args[0]["changed"] is False

        self.test_esxi.runtime.connectionState = 'disconnected'

        set_module_args(
            hostname="127.0.0.1",
            username="administrator@local",
            password="123456",
            add_cluster=False,
            datacenter="",
            esxi_host_name=self.test_esxi.name,
            state="disconnected"
        )
        with pytest.raises(AnsibleExitJson) as c:
            module_main()

        assert c.value.args[0]["changed"] is False

    def test_state_connected(self, mocker):
        self.__prepare(mocker)
        self.test_esxi.runtime.connectionState = 'disconnected'
        self.test_esxi.ReconnectHost_Task.return_value = MockVsphereTask()

        set_module_args(
            hostname="127.0.0.1",
            username="administrator@local",
            password="123456",
            add_cluster=False,
            datacenter="",
            esxi_host_name=self.test_esxi.name,
            state="connected"
        )
        with pytest.raises(AnsibleExitJson) as c:
            module_main()

        assert c.value.args[0]["changed"] is True

    def test_state_disconnected(self, mocker):
        self.__prepare(mocker)
        self.test_esxi.runtime.connectionState = 'connected'
        self.test_esxi.DisconnectHost_Task.return_value = MockVsphereTask()

        set_module_args(
            hostname="127.0.0.1",
            username="administrator@local",
            password="123456",
            add_cluster=False,
            datacenter="",
            esxi_host_name=self.test_esxi.name,
            state="disconnected"
        )
        with pytest.raises(AnsibleExitJson) as c:
            module_main()

        assert c.value.args[0]["changed"] is True

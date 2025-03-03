from __future__ import absolute_import, division, print_function
__metaclass__ = type

import sys
import pytest
from unittest import mock

from ansible_collections.vmware.vmware.plugins.modules.folder import (
    VmwareFolder,
    main as module_main
)
from ansible_collections.vmware.vmware.plugins.module_utils.clients._pyvmomi import (
    PyvmomiClient
)
from ...common.utils import (
    AnsibleExitJson, ModuleTestCase, set_module_args,
)
from ...common.vmware_object_mocks import (
    MockVmwareObject,
    MockVsphereTask
)

pytestmark = pytest.mark.skipif(
    sys.version_info < (2, 7), reason="requires python2.7 or higher"
)


class TestEsxiMaintenanceMode(ModuleTestCase):

    def __prepare(self, mocker):
        mocker.patch.object(PyvmomiClient, 'connect_to_api', return_value=(mocker.Mock(), mocker.Mock()))
        self.mock_folder = MockVmwareObject()

    def test_state_present_no_change(self, mocker):
        self.__prepare(mocker)
        mocker.patch.object(VmwareFolder, 'get_folder_by_absolute_path', return_value=self.mock_folder)

        set_module_args(
            hostname="127.0.0.1",
            username="administrator@local",
            password="123456",
            add_cluster=False,
            absolute_path="/DC0/host/test"
        )

        with pytest.raises(AnsibleExitJson) as c:
            module_main()

        assert c.value.args[0]["changed"] is False
        assert c.value.args[0]["folder"]["moid"] is self.mock_folder._moId

        set_module_args(
            hostname="127.0.0.1",
            username="administrator@local",
            password="123456",
            add_cluster=False,
            relative_path="test",
            datacenter="DC0",
            folder_type="host"
        )

        with pytest.raises(AnsibleExitJson) as c:
            module_main()

        assert c.value.args[0]["changed"] is False
        assert c.value.args[0]["folder"]["moid"] is self.mock_folder._moId

    def test_state_absent_no_change(self, mocker):
        self.__prepare(mocker)
        mocker.patch.object(VmwareFolder, 'get_folder_by_absolute_path', return_value=None)

        set_module_args(
            hostname="127.0.0.1",
            username="administrator@local",
            password="123456",
            add_cluster=False,
            state="absent",
            relative_path="test",
            datacenter="DC0",
            folder_type="host"
        )

        with pytest.raises(AnsibleExitJson) as c:
            module_main()

        assert c.value.args[0]["changed"] is False

    def test_state_absent_with_change(self, mocker):
        self.__prepare(mocker)
        mocker.patch.object(VmwareFolder, 'get_folder_by_absolute_path', return_value=self.mock_folder)
        self.mock_folder.Destroy = mock.Mock(return_value=MockVsphereTask())

        set_module_args(
            hostname="127.0.0.1",
            username="administrator@local",
            password="123456",
            add_cluster=False,
            absolute_path="/DC0/host/test",
            state="absent"
        )

        with pytest.raises(AnsibleExitJson) as c:
            module_main()

        assert c.value.args[0]["changed"] is True
        self.mock_folder.Destroy.assert_called_once()

    def test_state_present_with_change(self, mocker):
        self.__prepare(mocker)
        mocker.patch.object(VmwareFolder, 'get_folder_by_absolute_path', side_effect=[
            None, self.mock_folder, None
        ])
        self.mock_folder.CreateFolder = mock.Mock(return_value=MockVmwareObject(moid="2"))

        set_module_args(
            hostname="127.0.0.1",
            username="administrator@local",
            password="123456",
            add_cluster=False,
            absolute_path="/DC0/host/test",
            state="present"
        )

        with pytest.raises(AnsibleExitJson) as c:
            module_main()

        assert c.value.args[0]["changed"] is True
        assert c.value.args[0]["folder"]["moid"] == "2"

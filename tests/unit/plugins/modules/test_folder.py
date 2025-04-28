from __future__ import absolute_import, division, print_function
__metaclass__ = type

import sys
import pytest
from unittest import mock

from ansible_collections.vmware.vmware.plugins.modules.folder import (
    VmwareFolder,
    main as module_main
)
from ansible_collections.vmware.vmware.plugins.module_utils.clients.pyvmomi import (
    PyvmomiClient
)
from ...common.utils import (
    run_module, ModuleTestCase
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

        module_args = dict(
            absolute_path="/DC0/host/test"
        )

        result = run_module(module_entry=module_main, module_args=module_args)

        assert result["changed"] is False
        assert result["folder"]["moid"] is self.mock_folder._moId

        module_args = dict(
            relative_path="test",
            datacenter="DC0",
            folder_type="host"
        )

        result = run_module(module_entry=module_main, module_args=module_args)

        assert result["changed"] is False
        assert result["folder"]["moid"] is self.mock_folder._moId

    def test_state_absent_no_change(self, mocker):
        self.__prepare(mocker)
        mocker.patch.object(VmwareFolder, 'get_folder_by_absolute_path', return_value=None)

        module_args = dict(
            state="absent",
            relative_path="test",
            datacenter="DC0",
            folder_type="host"
        )

        result = run_module(module_entry=module_main, module_args=module_args)

        assert result["changed"] is False

    def test_state_absent_with_change(self, mocker):
        self.__prepare(mocker)
        mocker.patch.object(VmwareFolder, 'get_folder_by_absolute_path', return_value=self.mock_folder)
        self.mock_folder.Destroy = mock.Mock(return_value=MockVsphereTask())

        module_args = dict(
            absolute_path="/DC0/host/test",
            state="absent"
        )

        result = run_module(module_entry=module_main, module_args=module_args)

        assert result["changed"] is True
        self.mock_folder.Destroy.assert_called_once()

    def test_state_present_with_change(self, mocker):
        self.__prepare(mocker)
        mocker.patch.object(VmwareFolder, 'get_folder_by_absolute_path', side_effect=[
            None, self.mock_folder, None
        ])
        self.mock_folder.CreateFolder = mock.Mock(return_value=MockVmwareObject(moid="2"))

        module_args = dict(
            absolute_path="/DC0/host/test",
            state="present"
        )

        result = run_module(module_entry=module_main, module_args=module_args)

        assert result["changed"] is True
        assert result["folder"]["moid"] == "2"

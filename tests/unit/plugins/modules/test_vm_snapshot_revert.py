from __future__ import absolute_import, division, print_function
__metaclass__ = type

from unittest.mock import patch

from ansible_collections.vmware.vmware.plugins.modules.vm_snapshot_revert import (
    VmSnapshotRevertModule,
    main as module_main
)
from ansible_collections.vmware.vmware.plugins.module_utils.clients.pyvmomi import (
    PyvmomiClient
)
from ...common.utils import (
    run_module, ModuleTestCase
)
from ...common.vmware_object_mocks import (
    create_mock_vsphere_object,
    MockVsphereTask
)


class TestVmSnapshotRevert(ModuleTestCase):

    def __prepare(self, mocker):
        mocker.patch.object(PyvmomiClient, 'connect_to_api', return_value=(mocker.Mock(), mocker.Mock()))
        self.vm_mock = create_mock_vsphere_object()
        mocker.patch.object(VmSnapshotRevertModule, 'get_vms_using_params', return_value=([self.vm_mock]))

        self.snapshot_obj_mock = mocker.Mock()
        self.snapshot_obj_mock.RevertToSnapshot_Task.return_value = MockVsphereTask()

        self.snapshot_1_mock = mocker.Mock()
        self.snapshot_1_mock.name = 'snap1'
        self.snapshot_1_mock.id = 1
        self.snapshot_1_mock.snapshot = self.snapshot_obj_mock
        self.snapshot_1_mock.childSnapshotList = []

        self.snapshot_2_mock = mocker.Mock()
        self.snapshot_2_mock.name = 'snap2'
        self.snapshot_2_mock.id = 2
        self.snapshot_2_mock.snapshot = self.snapshot_obj_mock
        self.snapshot_2_mock.childSnapshotList = [self.snapshot_1_mock]

        self.vm_mock.snapshot.rootSnapshotList = [self.snapshot_2_mock]

    def test_no_snapshot_found(self, mocker):
        self.__prepare(mocker)
        self.vm_mock.snapshot.rootSnapshotList = []
        module_args = dict(
            name="vm1",
            snapshot_name="snap3"
        )
        run_module(module_entry=module_main, module_args=module_args, expect_success=False)

    def test_revert_to_snapshot(self, mocker):
        self.__prepare(mocker)
        module_args = dict(
            name="vm1",
            snapshot_name="snap1"
        )
        result = run_module(module_entry=module_main, module_args=module_args, expect_success=True)
        assert result["changed"] is True
        assert result["snapshot"]["name"] == "snap1"
        assert result["snapshot"]["id"] == 1
        self.snapshot_obj_mock.RevertToSnapshot_Task.assert_called_once()

    def test_revert_to_snapshot_id(self, mocker):
        self.__prepare(mocker)
        module_args = dict(
            name="vm1",
            snapshot_id=1
        )
        result = run_module(module_entry=module_main, module_args=module_args, expect_success=True)
        assert result["changed"] is True
        assert result["snapshot"]["name"] == "snap1"
        assert result["snapshot"]["id"] == 1
        self.snapshot_obj_mock.RevertToSnapshot_Task.assert_called_once()


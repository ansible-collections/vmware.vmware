from __future__ import absolute_import, division, print_function
__metaclass__ = type

import sys
import pytest

from ansible_collections.vmware.vmware.plugins.modules.vm_snapshot_info import (
    VmSnapshotInfoModule,
    main as module_main
)
from ansible_collections.vmware.vmware.plugins.module_utils.clients.pyvmomi import (
    PyvmomiClient
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


class MockSnapshotTree:
    """Minimal stand-in for a pyVmomi VirtualMachineSnapshotTree node."""
    def __init__(self, snap_id, name, children=None):
        self.id = snap_id
        self.name = name
        self.description = "%s description" % name
        self.createTime = "2024-12-24T15:27:37.041577+00:00"
        self.state = "poweredOff"
        self.quiesced = False
        self.childSnapshotList = children or []
        self.snapshot = object()


class MockSnapshotInfo:
    """Stand-in for vm.snapshot (a VirtualMachineSnapshotInfo data object)."""
    def __init__(self, root_snapshot_list, current_snapshot=None):
        self.rootSnapshotList = root_snapshot_list
        self.currentSnapshot = current_snapshot


class TestVmSnapshotInfo(ModuleTestCase):

    def __prepare(self, mocker):
        mocker.patch.object(PyvmomiClient, 'connect_to_api', return_value=(mocker.Mock(), mocker.Mock()))
        self.test_vm = create_mock_vsphere_object()
        mocker.patch.object(VmSnapshotInfoModule, 'get_vms_using_params', return_value=[self.test_vm])

        # snap1 -> snap2 -> snap3, plus an independent snap4
        self.snap3 = MockSnapshotTree(3, "snap3")
        self.snap2 = MockSnapshotTree(2, "snap2", children=[self.snap3])
        self.snap1 = MockSnapshotTree(1, "snap1", children=[self.snap2])
        self.snap4 = MockSnapshotTree(4, "snap4")

    def test_no_snapshots(self, mocker):
        self.__prepare(mocker)
        self.test_vm.snapshot = None

        result = run_module(module_entry=module_main, module_args=dict(moid="vm-42"))

        assert result["changed"] is False
        assert result["vm"]["moid"] == self.test_vm._GetMoId()
        assert result["vm"]["name"] == self.test_vm.name
        assert result["current_snapshot"] == {}
        assert result["snapshots"] == []
        assert result["snapshots_tree"] == {}

    def test_gather_all_snapshots(self, mocker):
        self.__prepare(mocker)
        self.test_vm.snapshot = MockSnapshotInfo(
            [self.snap1, self.snap4], current_snapshot=self.snap3.snapshot
        )

        result = run_module(module_entry=module_main, module_args=dict(moid="vm-42"))

        assert result["changed"] is False
        assert [snap["id"] for snap in result["snapshots"]] == [1, 2, 3, 4]
        assert set(result["snapshots_tree"].keys()) == {1, 4}
        assert set(result["snapshots_tree"][1]["children"].keys()) == {2}

    def test_current_snapshot_reported(self, mocker):
        self.__prepare(mocker)
        self.test_vm.snapshot = MockSnapshotInfo(
            [self.snap1], current_snapshot=self.snap2.snapshot
        )

        result = run_module(module_entry=module_main, module_args=dict(moid="vm-42"))

        assert result["current_snapshot"]["id"] == 2
        assert result["current_snapshot"]["name"] == "snap2"

    def test_no_current_snapshot(self, mocker):
        self.__prepare(mocker)
        self.test_vm.snapshot = MockSnapshotInfo([self.snap1], current_snapshot=None)

        result = run_module(module_entry=module_main, module_args=dict(moid="vm-42"))

        assert result["current_snapshot"] == {}
        assert [snap["id"] for snap in result["snapshots"]] == [1, 2, 3]

    def test_request_single_snapshot_by_name(self, mocker):
        self.__prepare(mocker)
        self.test_vm.snapshot = MockSnapshotInfo(
            [self.snap1], current_snapshot=self.snap1.snapshot
        )

        result = run_module(
            module_entry=module_main,
            module_args=dict(moid="vm-42", snapshot_name="snap2")
        )

        assert len(result["snapshots"]) == 1
        assert result["snapshots"][0]["id"] == 2
        assert result["snapshots"][0]["parent_id"] == 1
        assert result["snapshots"][0]["child_ids"] == [3]
        assert set(result["snapshots_tree"].keys()) == {2}
        assert result["snapshots_tree"][2]["children"] == {}

    def test_request_single_snapshot_by_id(self, mocker):
        self.__prepare(mocker)
        self.test_vm.snapshot = MockSnapshotInfo(
            [self.snap1], current_snapshot=self.snap1.snapshot
        )

        result = run_module(
            module_entry=module_main,
            module_args=dict(moid="vm-42", snapshot_id=3)
        )

        assert len(result["snapshots"]) == 1
        assert result["snapshots"][0]["id"] == 3
        assert set(result["snapshots_tree"].keys()) == {3}

    def test_request_missing_snapshot_returns_empty(self, mocker):
        self.__prepare(mocker)
        self.test_vm.snapshot = MockSnapshotInfo(
            [self.snap1], current_snapshot=self.snap1.snapshot
        )

        result = run_module(
            module_entry=module_main,
            module_args=dict(moid="vm-42", snapshot_name="does-not-exist")
        )

        assert result["snapshots"] == []
        assert result["snapshots_tree"] == []
        # current_snapshot is still reported independently of the requested filter
        assert result["current_snapshot"]["id"] == 1

    def test_snapshot_name_and_id_mutually_exclusive(self, mocker):
        self.__prepare(mocker)
        self.test_vm.snapshot = MockSnapshotInfo([self.snap1])

        result = run_module(
            module_entry=module_main,
            module_args=dict(moid="vm-42", snapshot_name="snap1", snapshot_id=1),
            expect_success=False
        )

        assert result["failed"] is True

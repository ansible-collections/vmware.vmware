from __future__ import absolute_import, division, print_function
__metaclass__ = type

import sys
import pytest

from ansible_collections.vmware.vmware.plugins.modules.vm_snapshot import (
    VmSnapshotModule,
    main as module_main
)
from ansible_collections.vmware.vmware.plugins.module_utils.clients.pyvmomi import (
    PyvmomiClient
)
from ...common.utils import (
    run_module, ModuleTestCase
)
from ...common.vmware_object_mocks import (
    MockVsphereTask
)

pytestmark = pytest.mark.skipif(
    sys.version_info < (2, 7), reason="requires python2.7 or higher"
)


class TestVmSnapshot(ModuleTestCase):

    def __prepare(self, mocker):
        self.content_mock = mocker.MagicMock()
        mocker.patch.object(PyvmomiClient, 'connect_to_api', return_value=(mocker.Mock(), self.content_mock))
        self.vm_mock = mocker.MagicMock()
        mocker.patch.object(VmSnapshotModule, 'get_vms_using_params', return_value=([self.vm_mock]))
        self.vm_mock.configure_mock(
            **{
                "RemoveAllSnapshots_Task.return_value": MockVsphereTask(),
                "CreateSnapshot_Task.return_value": MockVsphereTask()
            }
        )

        self.snap1_mock = mocker.MagicMock()
        self.snap1_mock.name = 'snap1'
        self.snap1_mock.snapshot.RenameSnapshot.return_value = MockVsphereTask()
        self.snap1_mock.snapshot.RemoveSnapshot_Task.return_value = MockVsphereTask()

        self.snap2_mock = mocker.MagicMock()
        self.snap2_mock.name = 'snap2'

        self.snap3_mock = mocker.MagicMock()
        self.snap3_mock.name = 'snap2'

        self.snap3_mock.childSnapshotList = [self.snap2_mock]
        self.snap2_mock.childSnapshotList = [self.snap1_mock]

    def test_take_snapshot(self, mocker):
        self.__prepare(mocker)

        module_args = dict(
            datacenter="DC0",
            folder="DC0/vm/e2e-qe",
            name="vm1",
            state="present",
            snapshot_name="snap1",
            description="snap1_description"
        )

        self.vm_mock.snapshot = None
        result = run_module(module_entry=module_main, module_args=module_args)

        assert result["changed"] is True

    def test_rename_snapshot(self, mocker):
        self.__prepare(mocker)

        module_args = dict(
            datacenter="DC0",
            folder="DC0/vm/e2e-qe",
            name="vm1",
            state="present",
            snapshot_name="snap1",
            new_snapshot_name="im_renamed",
            description="im_redescribed"
        )

        self.vm_mock.snapshot = self.snap3_mock
        self.snap3_mock.rootSnapshotList = [self.snap3_mock]
        result = run_module(module_entry=module_main, module_args=module_args)

        assert result["changed"] is True

    def test_remove_snapshot(self, mocker):
        self.__prepare(mocker)

        module_args = dict(
            datacenter="DC0",
            folder="DC0/vm/e2e-qe",
            name="vm1",
            state="absent",
            snapshot_name="snap1"
        )

        self.vm_mock.snapshot = self.snap3_mock
        self.snap3_mock.rootSnapshotList = [self.snap3_mock]
        result = run_module(module_entry=module_main, module_args=module_args)

        assert result["changed"] is True

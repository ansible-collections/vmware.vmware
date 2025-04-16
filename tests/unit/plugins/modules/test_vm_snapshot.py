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
    AnsibleExitJson, ModuleTestCase, set_module_args,
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

        set_module_args(
            hostname="127.0.0.1",
            username="administrator@local",
            password="123456",
            datacenter="DC0",
            folder="DC0/vm/e2e-qe",
            name="vm1",
            state="present",
            snapshot_name="snap1",
            description="snap1_description",
            validate_certs=False,
            add_cluster=False
        )

        self.vm_mock.snapshot = None
        with pytest.raises(AnsibleExitJson) as c:
            module_main()

        assert c.value.args[0]["changed"] is True

    def test_rename_snapshot(self, mocker):
        self.__prepare(mocker)

        set_module_args(
            hostname="127.0.0.1",
            username="administrator@local",
            password="123456",
            datacenter="DC0",
            folder="DC0/vm/e2e-qe",
            name="vm1",
            state="present",
            snapshot_name="snap1",
            new_snapshot_name="im_renamed",
            description="im_redescribed",
            validate_certs=False,
            add_cluster=False
        )

        self.vm_mock.snapshot = self.snap3_mock
        self.snap3_mock.rootSnapshotList = [self.snap3_mock]
        with pytest.raises(AnsibleExitJson) as c:
            module_main()

        assert c.value.args[0]["changed"] is True

    def test_remove_snapshot(self, mocker):
        self.__prepare(mocker)

        set_module_args(
            hostname="127.0.0.1",
            username="administrator@local",
            password="123456",
            datacenter="DC0",
            folder="DC0/vm/e2e-qe",
            name="vm1",
            state="absent",
            snapshot_name="snap1",
            validate_certs=False,
            add_cluster=False
        )

        self.vm_mock.snapshot = self.snap3_mock
        self.snap3_mock.rootSnapshotList = [self.snap3_mock]
        with pytest.raises(AnsibleExitJson) as c:
            module_main()

        assert c.value.args[0]["changed"] is True

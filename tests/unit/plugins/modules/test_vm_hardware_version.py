from __future__ import absolute_import, division, print_function
__metaclass__ = type

import sys
import pytest
from datetime import datetime

from ansible_collections.vmware.vmware.plugins.modules.vm_hardware_version import (
    HwVersion,
    VmHardwareModule,
    main as module_main
)
from ansible_collections.vmware.vmware.plugins.module_utils.clients.pyvmomi import (
    PyvmomiClient
)
from ansible_collections.vmware.vmware.plugins.module_utils._vsphere_tasks import (
    RunningTaskMonitor, TaskError
)
from ...common.utils import (
    run_module, ModuleTestCase
)
from ...common.vmware_object_mocks import (
    MockVsphereTask
)

from pyVmomi import vim

pytestmark = pytest.mark.skipif(
    sys.version_info < (2, 7), reason="requires python2.7 or higher"
)

TASK_METHODS = ('PowerOffVM_Task', 'CreateSnapshot_Task', 'UpgradeVM_Task', 'PowerOnVM_Task', 'ReconfigVM_Task')


class TestHwVersion():

    @pytest.mark.parametrize("value", [19, "19", "vmx-19", HwVersion(19)])
    def test_parse(self, value):
        assert HwVersion(value).version == 19

    @pytest.mark.parametrize("value", ["vmx-abc", "abc", ""])
    def test_parse_invalid(self, value):
        with pytest.raises(ValueError):
            HwVersion(value)

    def test_str_and_int(self):
        assert str(HwVersion(9)) == "vmx-09"
        assert str(HwVersion("vmx-21")) == "vmx-21"
        assert int(HwVersion("vmx-21")) == 21
        assert repr(HwVersion(21)) == "HwVersion('vmx-21')"

    def test_comparisons(self):
        assert HwVersion(19) == HwVersion("vmx-19")
        assert HwVersion(19) == "vmx-19"
        assert HwVersion(19) == 19
        assert HwVersion(17) < HwVersion(19)
        assert HwVersion(17) < "vmx-19"
        assert HwVersion(21) > 19
        assert HwVersion(19) >= "19"
        assert HwVersion(19) <= HwVersion(19)
        assert max([HwVersion(17), HwVersion(21), HwVersion(19)]) == 21

    def test_compare_with_invalid_value(self):
        assert (HwVersion(19) == "not-a-version") is False
        assert (HwVersion(19) != "not-a-version") is True
        with pytest.raises(TypeError):
            assert HwVersion(19) < "not-a-version"

    def test_hash(self):
        assert len({HwVersion(19), HwVersion("vmx-19"), HwVersion(21)}) == 2


class TestVmHardwareVersion(ModuleTestCase):

    def __prepare(self, mocker, current_version="vmx-17", supported_versions=None, power_state="poweredoff"):
        mocker.patch.object(PyvmomiClient, 'connect_to_api', return_value=(mocker.Mock(), mocker.Mock()))

        if supported_versions is None:
            supported_versions = ["vmx-17", "vmx-19", "vmx-21"]

        self.vm_mock = mocker.MagicMock()
        self.vm_mock.name = "test-vm"
        self.vm_mock._GetMoId.return_value = "vm-123"
        self.vm_mock.config.template = False
        self.vm_mock.config.version = current_version
        self.vm_mock.summary.runtime.powerState.lower.return_value = power_state
        self.vm_mock.environmentBrowser.QueryConfigOptionDescriptor.return_value = \
            self.option_descriptors(supported_versions)
        for task_method in TASK_METHODS:
            getattr(self.vm_mock, task_method).return_value = MockVsphereTask()
        mocker.patch.object(VmHardwareModule, 'get_vms_using_params', return_value=([self.vm_mock]))

        self.snapshot_ref = mocker.Mock()
        self.snapshot_tree = mocker.Mock()
        self.snapshot_tree.id = 12
        self.snapshot_tree.name = "hw-upgrade-vmx-17-20251016-101500"
        self.snapshot_tree.snapshot = self.snapshot_ref
        self.snapshot_tree.childSnapshotList = []
        self.vm_mock.snapshot.rootSnapshotList = [self.snapshot_tree]

        self.wait_mock = mocker.patch.object(
            RunningTaskMonitor, 'wait_for_completion', return_value=(True, {'result': self.snapshot_ref})
        )

    def option_descriptors(self, versions, upgrade_supported=True):
        return [
            vim.vm.ConfigOptionDescriptor(key=v, upgradeSupported=upgrade_supported)
            for v in versions
        ]

    def task_calls(self):
        """
        Get the names of the vSphere task methods called on the VM, in the order they were called.
        """
        return [c[0] for c in self.vm_mock.method_calls if c[0] in TASK_METHODS]

    def test_no_change(self, mocker):
        self.__prepare(mocker, current_version="vmx-19")

        result = run_module(module_entry=module_main, module_args=dict(name="test-vm", version="vmx-19"))

        assert result["changed"] is False
        assert result["power_cycled"] is False
        assert result["snapshot"] == dict()
        assert result["vm"] == dict(moid="vm-123", name="test-vm")
        assert "diff" not in result
        assert self.task_calls() == []

    def test_no_change_powered_on(self, mocker):
        self.__prepare(mocker, current_version="vmx-19", power_state="poweredon")

        result = run_module(module_entry=module_main, module_args=dict(name="test-vm", version="19"))

        assert result["changed"] is False
        assert result["power_cycled"] is False
        assert self.task_calls() == []

    @pytest.mark.parametrize("version", ["vmx-19", "19", 19])
    def test_upgrade_version_formats(self, mocker, version):
        self.__prepare(mocker)

        result = run_module(module_entry=module_main, module_args=dict(name="test-vm", version=version))

        assert result["changed"] is True
        assert result["power_cycled"] is False
        assert result["snapshot"] == dict()
        assert result["diff"] == dict(before=dict(version="vmx-17"), after=dict(version="vmx-19"))
        assert self.task_calls() == ['UpgradeVM_Task']
        self.vm_mock.UpgradeVM_Task.assert_called_once_with(version="vmx-19")

    def test_upgrade_passes_timeout(self, mocker):
        self.__prepare(mocker)

        run_module(module_entry=module_main, module_args=dict(name="test-vm", version="19", timeout=1800))

        self.wait_mock.assert_called_once_with(timeout=1800)

    def test_upgrade_latest(self, mocker):
        self.__prepare(mocker)

        result = run_module(module_entry=module_main, module_args=dict(name="test-vm", version="latest"))

        assert result["changed"] is True
        assert result["diff"]["after"]["version"] == "vmx-21"
        self.vm_mock.UpgradeVM_Task.assert_called_once_with(version="vmx-21")
        # the supported versions should be looked up once and then cached
        self.vm_mock.environmentBrowser.QueryConfigOptionDescriptor.assert_called_once()

    def test_latest_no_change(self, mocker):
        self.__prepare(mocker, current_version="vmx-21")

        result = run_module(module_entry=module_main, module_args=dict(name="test-vm", version="latest"))

        assert result["changed"] is False
        assert self.task_calls() == []

    def test_latest_ignores_versions_without_upgrade_support(self, mocker):
        self.__prepare(mocker)
        self.vm_mock.environmentBrowser.QueryConfigOptionDescriptor.return_value = (
            self.option_descriptors(["vmx-17", "vmx-19"]) +
            self.option_descriptors(["vmx-21"], upgrade_supported=False)
        )

        result = run_module(module_entry=module_main, module_args=dict(name="test-vm", version="latest"))

        assert result["changed"] is True
        self.vm_mock.UpgradeVM_Task.assert_called_once_with(version="vmx-19")

    def test_check_mode(self, mocker):
        self.__prepare(mocker, power_state="poweredon")

        result = run_module(module_entry=module_main, module_args=dict(
            name="test-vm",
            version="19",
            allow_power_cycling=True,
            snapshot_before_upgrade=True,
            _ansible_check_mode=True
        ))

        assert result["changed"] is True
        assert result["power_cycled"] is True
        assert result["snapshot"] == dict()
        assert result["diff"] == dict(before=dict(version="vmx-17"), after=dict(version="vmx-19"))
        assert self.task_calls() == []

    def test_check_mode_power_cycle_not_allowed_fails(self, mocker):
        self.__prepare(mocker, power_state="poweredon")

        result = run_module(
            module_entry=module_main,
            module_args=dict(name="test-vm", version="19", _ansible_check_mode=True),
            expect_success=False
        )

        assert result["failed"] is True
        assert self.task_calls() == []

    def test_powered_on_power_cycle_not_allowed_fails(self, mocker):
        self.__prepare(mocker, power_state="poweredon")

        result = run_module(
            module_entry=module_main,
            module_args=dict(name="test-vm", version="19"),
            expect_success=False
        )

        assert result["failed"] is True
        assert self.task_calls() == []

    def test_powered_on_power_cycle(self, mocker):
        self.__prepare(mocker, power_state="poweredon")

        result = run_module(module_entry=module_main, module_args=dict(
            name="test-vm",
            version="19",
            allow_power_cycling=True
        ))

        assert result["changed"] is True
        assert result["power_cycled"] is True
        assert result["snapshot"] == dict()
        assert self.task_calls() == ['PowerOffVM_Task', 'UpgradeVM_Task', 'PowerOnVM_Task']

    @pytest.mark.parametrize("power_state", ["suspended", "poweredon"])
    def test_any_non_powered_off_state_requires_power_cycle(self, mocker, power_state):
        self.__prepare(mocker, power_state=power_state)

        result = run_module(module_entry=module_main, module_args=dict(
            name="test-vm",
            version="19",
            allow_power_cycling=True
        ))

        assert result["power_cycled"] is True
        assert self.task_calls() == ['PowerOffVM_Task', 'UpgradeVM_Task', 'PowerOnVM_Task']

    def test_powered_off_with_power_cycling_allowed(self, mocker):
        self.__prepare(mocker)

        result = run_module(module_entry=module_main, module_args=dict(
            name="test-vm",
            version="19",
            allow_power_cycling=True
        ))

        assert result["changed"] is True
        assert result["power_cycled"] is False
        assert self.task_calls() == ['UpgradeVM_Task']

    def test_snapshot_before_upgrade(self, mocker):
        self.__prepare(mocker)
        datetime_mock = mocker.patch(
            'ansible_collections.vmware.vmware.plugins.modules.vm_hardware_version.datetime'
        )
        datetime_mock.now.return_value = datetime(2025, 10, 16, 10, 15, 0)

        result = run_module(module_entry=module_main, module_args=dict(
            name="test-vm",
            version="19",
            snapshot_before_upgrade=True
        ))

        assert result["changed"] is True
        assert result["snapshot"] == dict(id=12, name="hw-upgrade-vmx-17-20251016-101500")
        assert self.task_calls() == ['CreateSnapshot_Task', 'UpgradeVM_Task']
        self.vm_mock.CreateSnapshot_Task.assert_called_once_with(
            name="hw-upgrade-vmx-17-20251016-101500",
            description="Created by vmware.vmware.vm_hardware_version at version vmx-17",
            memory=False,
            quiesce=False
        )

    def test_snapshot_with_power_cycle(self, mocker):
        self.__prepare(mocker, power_state="poweredon")

        result = run_module(module_entry=module_main, module_args=dict(
            name="test-vm",
            version="19",
            allow_power_cycling=True,
            snapshot_before_upgrade=True
        ))

        assert result["changed"] is True
        assert result["power_cycled"] is True
        assert result["snapshot"]["id"] == 12
        # the snapshot is taken after the power off and before the upgrade
        assert self.task_calls() == ['PowerOffVM_Task', 'CreateSnapshot_Task', 'UpgradeVM_Task', 'PowerOnVM_Task']

    def test_snapshot_found_in_child_snapshots(self, mocker):
        self.__prepare(mocker)
        new_snapshot_tree = mocker.Mock()
        new_snapshot_tree.id = 13
        new_snapshot_tree.name = "new-snap"
        new_snapshot_tree.snapshot = self.snapshot_ref
        new_snapshot_tree.childSnapshotList = []
        self.snapshot_tree.snapshot = mocker.Mock()
        self.snapshot_tree.childSnapshotList = [new_snapshot_tree]

        result = run_module(module_entry=module_main, module_args=dict(
            name="test-vm",
            version="19",
            snapshot_before_upgrade=True
        ))

        assert result["snapshot"] == dict(id=13, name="new-snap")

    def test_no_snapshot_when_no_change(self, mocker):
        self.__prepare(mocker, current_version="vmx-19")

        result = run_module(module_entry=module_main, module_args=dict(
            name="test-vm",
            version="19",
            snapshot_before_upgrade=True
        ))

        assert result["changed"] is False
        assert result["snapshot"] == dict()
        self.vm_mock.CreateSnapshot_Task.assert_not_called()

    def test_downgrade_fails(self, mocker):
        self.__prepare(mocker, current_version="vmx-19")

        result = run_module(
            module_entry=module_main,
            module_args=dict(name="test-vm", version="vmx-17"),
            expect_success=False
        )

        assert result["failed"] is True
        assert result["desired_version"] == "vmx-17"
        assert result["current_version"] == "vmx-19"
        assert self.task_calls() == []

    def test_ignore_downgrades(self, mocker):
        self.__prepare(mocker, current_version="vmx-21", power_state="poweredon")

        result = run_module(module_entry=module_main, module_args=dict(
            name="test-vm",
            version="vmx-17",
            ignore_downgrades=True,
            snapshot_before_upgrade=True
        ))

        assert result["changed"] is False
        assert result["power_cycled"] is False
        assert result["snapshot"] == dict()
        assert "diff" not in result
        assert self.task_calls() == []

    def test_ignore_downgrades_still_upgrades(self, mocker):
        self.__prepare(mocker)

        result = run_module(module_entry=module_main, module_args=dict(
            name="test-vm",
            version="vmx-19",
            ignore_downgrades=True
        ))

        assert result["changed"] is True
        self.vm_mock.UpgradeVM_Task.assert_called_once_with(version="vmx-19")

    def test_unavailable_version_fails(self, mocker):
        self.__prepare(mocker)

        result = run_module(
            module_entry=module_main,
            module_args=dict(name="test-vm", version="vmx-20"),
            expect_success=False
        )

        assert result["failed"] is True
        assert result["desired_version"] == "vmx-20"
        assert sorted(result["available_versions"]) == ["vmx-17", "vmx-19", "vmx-21"]
        assert self.task_calls() == []

    def test_version_without_upgrade_support_fails(self, mocker):
        self.__prepare(mocker)
        self.vm_mock.environmentBrowser.QueryConfigOptionDescriptor.return_value = (
            self.option_descriptors(["vmx-17", "vmx-19"]) +
            self.option_descriptors(["vmx-21"], upgrade_supported=False)
        )

        result = run_module(
            module_entry=module_main,
            module_args=dict(name="test-vm", version="vmx-21"),
            expect_success=False
        )

        assert result["failed"] is True
        assert sorted(result["available_versions"]) == ["vmx-17", "vmx-19"]
        assert self.task_calls() == []

    @pytest.mark.parametrize("version", ["19", "latest"])
    def test_no_supported_versions_fails(self, mocker, version):
        self.__prepare(mocker)
        self.vm_mock.environmentBrowser.QueryConfigOptionDescriptor.return_value = \
            self.option_descriptors(["vmx-17", "vmx-19"], upgrade_supported=False)

        result = run_module(
            module_entry=module_main,
            module_args=dict(name="test-vm", version=version),
            expect_success=False
        )

        assert result["failed"] is True
        assert self.task_calls() == []

    @pytest.mark.parametrize("version", ["abc", "vmx-abc", "vmx19.1"])
    def test_invalid_version_fails(self, mocker, version):
        self.__prepare(mocker)

        result = run_module(
            module_entry=module_main,
            module_args=dict(name="test-vm", version=version),
            expect_success=False
        )

        assert result["failed"] is True
        assert self.task_calls() == []

    def test_template_fails(self, mocker):
        self.__prepare(mocker)
        self.vm_mock.config.template = True

        result = run_module(
            module_entry=module_main,
            module_args=dict(name="test-vm", version="19"),
            expect_success=False
        )

        assert result["failed"] is True
        assert self.task_calls() == []

    def test_upgrade_task_error_leaves_vm_powered_off(self, mocker):
        self.__prepare(mocker, power_state="poweredon")
        self.wait_mock.side_effect = [
            (True, {'result': None}),
            TaskError("boom", parent_error=Exception("boom")),
        ]

        result = run_module(
            module_entry=module_main,
            module_args=dict(name="test-vm", version="19", allow_power_cycling=True),
            expect_success=False
        )

        assert result["failed"] is True
        assert result["error_code"] == "TASK_ERROR"
        assert result["msg"] == "Unable to upgrade VM. boom"
        assert self.task_calls() == ['PowerOffVM_Task', 'UpgradeVM_Task']
        self.vm_mock.PowerOnVM_Task.assert_not_called()

    def test_snapshot_task_error_skips_upgrade(self, mocker):
        self.__prepare(mocker)
        self.wait_mock.side_effect = TaskError("no space", parent_error=Exception("no space"))

        result = run_module(
            module_entry=module_main,
            module_args=dict(name="test-vm", version="19", snapshot_before_upgrade=True),
            expect_success=False
        )

        assert result["failed"] is True
        assert result["error_code"] == "TASK_ERROR"
        assert result["msg"] == "Unable to take snapshot VM. no space"
        self.vm_mock.UpgradeVM_Task.assert_not_called()

    def test_power_off_vim_fault(self, mocker):
        self.__prepare(mocker, power_state="poweredon")
        self.vm_mock.PowerOffVM_Task.side_effect = vim.fault.InvalidState(msg="bad state")

        result = run_module(
            module_entry=module_main,
            module_args=dict(name="test-vm", version="19", allow_power_cycling=True),
            expect_success=False
        )

        assert result["failed"] is True
        assert result["error_code"] == "VIM_FAULT"
        assert result["msg"] == "Unable to power off VM. bad state"
        self.vm_mock.UpgradeVM_Task.assert_not_called()
        self.vm_mock.PowerOnVM_Task.assert_not_called()

    def test_upgrade_vim_fault(self, mocker):
        self.__prepare(mocker)
        self.vm_mock.UpgradeVM_Task.side_effect = vim.fault.AlreadyUpgraded(msg="already upgraded")

        result = run_module(
            module_entry=module_main,
            module_args=dict(name="test-vm", version="19"),
            expect_success=False
        )

        assert result["failed"] is True
        assert result["error_code"] == "VIM_FAULT"
        assert result["msg"] == "Unable to upgrade VM. already upgraded"

    def __prepare_scheduled(self, mocker, pending=None, **kwargs):
        self.__prepare(mocker, **kwargs)
        # a bare MagicMock would look like a pending upgrade, so always set this explicitly
        self.vm_mock.config.scheduledHardwareUpgradeInfo = pending

    @staticmethod
    def pending_info(version="vmx-19", status="pending", policy="onSoftPowerOff"):
        return vim.vm.ScheduledHardwareUpgradeInfo(
            upgradePolicy=policy,
            versionKey=version,
            scheduledHardwareUpgradeStatus=status
        )

    def scheduled_spec(self):
        self.vm_mock.ReconfigVM_Task.assert_called_once()
        return self.vm_mock.ReconfigVM_Task.call_args.kwargs['spec']

    @pytest.mark.parametrize("policy, vsphere_policy", [
        ("next_guest_power_off", "onSoftPowerOff"),
        ("next_power_off", "always"),
    ])
    def test_schedule_upgrade(self, mocker, policy, vsphere_policy):
        self.__prepare_scheduled(mocker)

        result = run_module(module_entry=module_main, module_args=dict(
            name="test-vm", version="vmx-19", upgrade_policy=policy
        ))

        assert result["changed"] is True
        assert result["power_cycled"] is False
        assert result["snapshot"] == dict()
        assert result["diff"] == dict(before=dict(version="vmx-17"), after=dict(version="vmx-19"))
        assert self.task_calls() == ['ReconfigVM_Task']
        spec = self.scheduled_spec()
        assert spec.scheduledHardwareUpgradeInfo.upgradePolicy == vsphere_policy
        assert spec.scheduledHardwareUpgradeInfo.versionKey == "vmx-19"

    def test_schedule_upgrade_latest(self, mocker):
        self.__prepare_scheduled(mocker)

        result = run_module(module_entry=module_main, module_args=dict(
            name="test-vm", version="latest", upgrade_policy="next_power_off"
        ))

        assert result["changed"] is True
        assert result["diff"]["after"]["version"] == "vmx-21"
        assert self.scheduled_spec().scheduledHardwareUpgradeInfo.versionKey == "vmx-21"

    def test_schedule_upgrade_passes_timeout(self, mocker):
        self.__prepare_scheduled(mocker)

        run_module(module_entry=module_main, module_args=dict(
            name="test-vm", version="19", upgrade_policy="next_power_off", timeout=1800
        ))

        self.wait_mock.assert_called_once_with(timeout=1800)

    def test_schedule_upgrade_powered_on_does_not_power_cycle(self, mocker):
        self.__prepare_scheduled(mocker, power_state="poweredon")

        result = run_module(module_entry=module_main, module_args=dict(
            name="test-vm", version="19", upgrade_policy="next_guest_power_off"
        ))

        assert result["changed"] is True
        assert result["power_cycled"] is False
        assert self.task_calls() == ['ReconfigVM_Task']

    def test_schedule_upgrade_ignores_snapshot_option(self, mocker):
        self.__prepare_scheduled(mocker)

        result = run_module(module_entry=module_main, module_args=dict(
            name="test-vm",
            version="19",
            upgrade_policy="next_power_off",
            snapshot_before_upgrade=True,
            allow_power_cycling=True
        ))

        assert result["changed"] is True
        assert result["snapshot"] == dict()
        assert self.task_calls() == ['ReconfigVM_Task']

    def test_schedule_upgrade_check_mode(self, mocker):
        self.__prepare_scheduled(mocker)

        result = run_module(module_entry=module_main, module_args=dict(
            name="test-vm", version="19", upgrade_policy="next_power_off", _ansible_check_mode=True
        ))

        assert result["changed"] is True
        assert result["diff"] == dict(before=dict(version="vmx-17"), after=dict(version="vmx-19"))
        assert self.task_calls() == []

    def test_already_scheduled_is_idempotent(self, mocker):
        self.__prepare_scheduled(mocker, pending=self.pending_info(version="vmx-19", status="pending"))

        result = run_module(module_entry=module_main, module_args=dict(
            name="test-vm", version="vmx-19", upgrade_policy="next_guest_power_off"
        ))

        assert result["changed"] is False
        assert result["diff"] == dict(before=dict(version="vmx-17"), after=dict(version="vmx-19"))
        assert self.task_calls() == []

    def test_already_scheduled_latest_is_idempotent(self, mocker):
        self.__prepare_scheduled(mocker, pending=self.pending_info(version="vmx-21", status="pending", policy="always"))

        result = run_module(module_entry=module_main, module_args=dict(
            name="test-vm", version="latest", upgrade_policy="next_power_off"
        ))

        assert result["changed"] is False
        assert self.task_calls() == []

    def test_already_scheduled_check_mode(self, mocker):
        self.__prepare_scheduled(mocker, pending=self.pending_info(policy="always"))

        result = run_module(module_entry=module_main, module_args=dict(
            name="test-vm", version="19", upgrade_policy="next_power_off", _ansible_check_mode=True
        ))

        assert result["changed"] is False
        assert self.task_calls() == []

    def test_scheduled_with_different_policy_is_rescheduled(self, mocker):
        self.__prepare_scheduled(mocker, pending=self.pending_info(version="vmx-19", policy="onSoftPowerOff"))

        result = run_module(module_entry=module_main, module_args=dict(
            name="test-vm", version="vmx-19", upgrade_policy="next_power_off"
        ))

        assert result["changed"] is True
        assert self.scheduled_spec().scheduledHardwareUpgradeInfo.upgradePolicy == "always"

    def test_scheduled_for_different_version_is_rescheduled(self, mocker):
        self.__prepare_scheduled(mocker, pending=self.pending_info(version="vmx-19", status="pending"))

        result = run_module(module_entry=module_main, module_args=dict(
            name="test-vm", version="vmx-21", upgrade_policy="next_power_off"
        ))

        assert result["changed"] is True
        assert result["diff"]["after"]["version"] == "vmx-21"
        assert self.scheduled_spec().scheduledHardwareUpgradeInfo.versionKey == "vmx-21"

    @pytest.mark.parametrize("status", ["none", "success", "failed"])
    def test_non_pending_status_is_rescheduled(self, mocker, status):
        self.__prepare_scheduled(mocker, pending=self.pending_info(version="vmx-19", status=status))

        result = run_module(module_entry=module_main, module_args=dict(
            name="test-vm", version="vmx-19", upgrade_policy="next_guest_power_off"
        ))

        assert result["changed"] is True
        assert self.task_calls() == ['ReconfigVM_Task']

    def test_no_pending_check_uses_none_info(self, mocker):
        self.__prepare_scheduled(mocker, pending=None)
        module = VmHardwareModule.__new__(VmHardwareModule)
        module.vm = self.vm_mock
        module._desired_version = HwVersion(19)

        assert module.is_pending_upgrade_task_needed() is True

    def test_schedule_not_needed_when_already_at_version(self, mocker):
        self.__prepare_scheduled(mocker, current_version="vmx-19")

        result = run_module(module_entry=module_main, module_args=dict(
            name="test-vm", version="19", upgrade_policy="next_power_off"
        ))

        assert result["changed"] is False
        assert "diff" not in result
        assert self.task_calls() == []

    def test_schedule_downgrade_fails(self, mocker):
        self.__prepare_scheduled(mocker, current_version="vmx-19")

        result = run_module(
            module_entry=module_main,
            module_args=dict(name="test-vm", version="vmx-17", upgrade_policy="next_power_off"),
            expect_success=False
        )

        assert result["failed"] is True
        assert self.task_calls() == []

    def test_schedule_ignore_downgrades(self, mocker):
        self.__prepare_scheduled(mocker, current_version="vmx-21")

        result = run_module(module_entry=module_main, module_args=dict(
            name="test-vm", version="vmx-17", upgrade_policy="next_power_off", ignore_downgrades=True
        ))

        assert result["changed"] is False
        assert "diff" not in result
        assert self.task_calls() == []

    def test_schedule_unavailable_version_fails(self, mocker):
        self.__prepare_scheduled(mocker)

        result = run_module(
            module_entry=module_main,
            module_args=dict(name="test-vm", version="vmx-20", upgrade_policy="next_power_off"),
            expect_success=False
        )

        assert result["failed"] is True
        assert sorted(result["available_versions"]) == ["vmx-17", "vmx-19", "vmx-21"]
        assert self.task_calls() == []

    def test_schedule_task_error(self, mocker):
        self.__prepare_scheduled(mocker)
        self.wait_mock.side_effect = TaskError("boom", parent_error=Exception("boom"))

        result = run_module(
            module_entry=module_main,
            module_args=dict(name="test-vm", version="19", upgrade_policy="next_power_off"),
            expect_success=False
        )

        assert result["failed"] is True
        assert result["error_code"] == "TASK_ERROR"
        assert result["msg"] == "Unable to schedule upgrade VM. boom"

    def test_schedule_vim_fault(self, mocker):
        self.__prepare_scheduled(mocker)
        self.vm_mock.ReconfigVM_Task.side_effect = vim.fault.InvalidState(msg="bad state")

        result = run_module(
            module_entry=module_main,
            module_args=dict(name="test-vm", version="19", upgrade_policy="next_power_off"),
            expect_success=False
        )

        assert result["failed"] is True
        assert result["error_code"] == "VIM_FAULT"
        assert result["msg"] == "Unable to schedule upgrade VM. bad state"

    def test_schedule_upgrade_unsupported_policy_fails(self, mocker):
        # argument_spec choices prevent this from the playbook, so call the method directly
        self.__prepare_scheduled(mocker)
        module = VmHardwareModule.__new__(VmHardwareModule)
        module.vm = self.vm_mock
        module.params = dict(upgrade_policy="now")
        module.module = mocker.Mock()
        module.module.fail_json.side_effect = RuntimeError("fail_json")

        with pytest.raises(RuntimeError, match="fail_json"):
            module.schedule_upgrade()

        self.vm_mock.ReconfigVM_Task.assert_not_called()

    def test_schedule_when_existing_policy_is_never(self, mocker):
        self.__prepare_scheduled(mocker, pending=self.pending_info(version="vmx-19", policy="never"))

        result = run_module(module_entry=module_main, module_args=dict(
            name="test-vm", version="vmx-19", upgrade_policy="next_guest_power_off"
        ))

        assert result["changed"] is True
        assert self.scheduled_spec().scheduledHardwareUpgradeInfo.upgradePolicy == "onSoftPowerOff"

    @pytest.mark.parametrize("policy", ["now", "next_guest_power_off", "next_power_off"])
    def test_version_required_unless_policy_is_never(self, mocker, policy):
        self.__prepare_scheduled(mocker)

        result = run_module(
            module_entry=module_main,
            module_args=dict(name="test-vm", upgrade_policy=policy),
            expect_success=False
        )

        assert result["failed"] is True
        assert "version" in result["msg"]
        assert self.task_calls() == []

    @pytest.mark.parametrize("policy", ["onSoftPowerOff", "always"])
    def test_cancel_scheduled_upgrade(self, mocker, policy):
        self.__prepare_scheduled(mocker, pending=self.pending_info(policy=policy))

        result = run_module(module_entry=module_main, module_args=dict(
            name="test-vm", upgrade_policy="never"
        ))

        assert result["changed"] is True
        assert result["power_cycled"] is False
        assert result["snapshot"] == dict()
        assert "diff" not in result
        assert self.task_calls() == ['ReconfigVM_Task']
        info = self.scheduled_spec().scheduledHardwareUpgradeInfo
        assert info.upgradePolicy == "never"
        assert info.versionKey is None

    @pytest.mark.parametrize("status", ["success", "failed"])
    def test_cancel_scheduled_upgrade_with_non_pending_status(self, mocker, status):
        self.__prepare_scheduled(mocker, pending=self.pending_info(status=status, policy="always"))

        result = run_module(module_entry=module_main, module_args=dict(
            name="test-vm", upgrade_policy="never"
        ))

        assert result["changed"] is True
        assert self.task_calls() == ['ReconfigVM_Task']

    def test_cancel_with_no_scheduled_upgrade_info(self, mocker):
        self.__prepare_scheduled(mocker, pending=None)

        result = run_module(module_entry=module_main, module_args=dict(
            name="test-vm", upgrade_policy="never"
        ))

        assert result["changed"] is False
        assert self.task_calls() == []

    def test_cancel_already_canceled_is_idempotent(self, mocker):
        # vSphere keeps the info object after a cancel, with the policy set to never
        self.__prepare_scheduled(mocker, pending=self.pending_info(status="none", policy="never"))

        result = run_module(module_entry=module_main, module_args=dict(
            name="test-vm", upgrade_policy="never"
        ))

        assert result["changed"] is False
        assert self.task_calls() == []

    def test_cancel_check_mode(self, mocker):
        self.__prepare_scheduled(mocker, pending=self.pending_info())

        result = run_module(module_entry=module_main, module_args=dict(
            name="test-vm", upgrade_policy="never", _ansible_check_mode=True
        ))

        assert result["changed"] is True
        assert self.task_calls() == []

    def test_cancel_ignores_version(self, mocker):
        # a downgrade or unavailable version would normally fail, but version is not used when canceling
        self.__prepare_scheduled(mocker, current_version="vmx-21", pending=self.pending_info())

        result = run_module(module_entry=module_main, module_args=dict(
            name="test-vm", version="vmx-17", upgrade_policy="never"
        ))

        assert result["changed"] is True
        assert self.task_calls() == ['ReconfigVM_Task']
        self.vm_mock.environmentBrowser.QueryConfigOptionDescriptor.assert_not_called()

    def test_cancel_does_not_power_cycle(self, mocker):
        self.__prepare_scheduled(mocker, power_state="poweredon", pending=self.pending_info())

        result = run_module(module_entry=module_main, module_args=dict(
            name="test-vm", upgrade_policy="never", allow_power_cycling=True, snapshot_before_upgrade=True
        ))

        assert result["changed"] is True
        assert result["power_cycled"] is False
        assert result["snapshot"] == dict()
        assert self.task_calls() == ['ReconfigVM_Task']

    def test_cancel_task_error(self, mocker):
        self.__prepare_scheduled(mocker, pending=self.pending_info())
        self.wait_mock.side_effect = TaskError("boom", parent_error=Exception("boom"))

        result = run_module(
            module_entry=module_main,
            module_args=dict(name="test-vm", upgrade_policy="never"),
            expect_success=False
        )

        assert result["failed"] is True
        assert result["error_code"] == "TASK_ERROR"
        assert result["msg"] == "Unable to cancel scheduled upgrade for VM. boom"

    def test_cancel_vim_fault(self, mocker):
        self.__prepare_scheduled(mocker, pending=self.pending_info())
        self.vm_mock.ReconfigVM_Task.side_effect = vim.fault.InvalidState(msg="bad state")

        result = run_module(
            module_entry=module_main,
            module_args=dict(name="test-vm", upgrade_policy="never"),
            expect_success=False
        )

        assert result["failed"] is True
        assert result["error_code"] == "VIM_FAULT"
        assert result["msg"] == "Unable to cancel scheduled upgrade for VM. bad state"

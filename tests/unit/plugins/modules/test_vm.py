from __future__ import absolute_import, division, print_function
__metaclass__ = type

import sys
import pytest

from ansible_collections.vmware.vmware.plugins.modules.vm import (
    VmModule,
    main as module_main
)
from ansible_collections.vmware.vmware.plugins.module_utils.clients.pyvmomi import (
    PyvmomiClient
)
from ansible_collections.vmware.vmware.plugins.module_utils._vsphere_tasks import (
    RunningTaskMonitor, TaskError
)
from ...common.utils import (
    run_module, ModuleTestCase, AnsibleFailJson
)

try:
    from pyVmomi import vim
except ImportError:
    pass

pytestmark = pytest.mark.skipif(
    sys.version_info < (2, 7), reason="requires python2.7 or higher"
)


class TestVm(ModuleTestCase):

    def __prepare(self, mocker, vm=None, changes_required=True):
        mocker.patch.object(PyvmomiClient, 'connect_to_api', return_value=(mocker.Mock(), mocker.Mock()))

        # The VM the module thinks already exists (None means it must be created).
        self.vm_mock = mocker.MagicMock()
        self.vm_mock.name = "test-vm"
        self.vm_mock._GetMoId.return_value = "vm-123"
        self.vm_mock.summary.runtime.powerState.lower.return_value = "poweredoff"
        mocker.patch.object(VmModule, 'get_vms_using_params', return_value=([vm] if vm else []))

        # The change set is produced by the configuration machinery, which has its own
        # unit tests. Here we stub it so we can drive the module's high level behavior.
        self.change_set = mocker.MagicMock()
        self.change_set.are_changes_required.return_value = changes_required
        self.change_set.changes = {}
        self.change_set.power_cycle_required = False

        self.configurator = mocker.MagicMock()
        self.configurator.stage_configuration_changes.return_value = self.change_set
        self.configurator.change_set = self.change_set

        self.builder = mocker.MagicMock()
        self.builder.create_configurator.return_value = self.configurator
        mocker.patch(
            'ansible_collections.vmware.vmware.plugins.modules.vm.ConfigurationBuilder',
            return_value=self.builder
        )

        # Any task that does run resolves to a freshly "created" VM.
        mocker.patch.object(
            RunningTaskMonitor, 'wait_for_completion',
            return_value=(True, {'result': self.vm_mock})
        )

    def test_state_present_create(self, mocker):
        self.__prepare(mocker, vm=None)
        vm_folder = self.builder.placement.get_folder.return_value

        result = run_module(module_entry=module_main, module_args=dict(name="test-vm"))

        assert result["changed"] is True
        assert result["vm"]["moid"] == "vm-123"
        assert result["vm"]["name"] == "test-vm"
        vm_folder.CreateVM_Task.assert_called_once()

    def test_state_present_create_check_mode(self, mocker):
        self.__prepare(mocker, vm=None)
        vm_folder = self.builder.placement.get_folder.return_value

        result = run_module(module_entry=module_main, module_args=dict(
            name="test-vm",
            _ansible_check_mode=True
        ))

        assert result["changed"] is True
        assert result["vm"]["moid"] == ""
        assert result["vm"]["name"] == "test-vm"
        vm_folder.CreateVM_Task.assert_not_called()

    def test_state_present_update(self, mocker):
        self.__prepare(mocker, vm=self.mock_existing_vm(mocker))

        result = run_module(module_entry=module_main, module_args=dict(moid="vm-123"))

        assert result["changed"] is True
        self.existing_vm.ReconfigVM_Task.assert_called_once()

    def test_state_present_update_no_change(self, mocker):
        self.__prepare(mocker, vm=self.mock_existing_vm(mocker), changes_required=False)

        result = run_module(module_entry=module_main, module_args=dict(moid="vm-123"))

        assert result["changed"] is False
        self.existing_vm.ReconfigVM_Task.assert_not_called()

    def test_state_present_update_check_mode(self, mocker):
        self.__prepare(mocker, vm=self.mock_existing_vm(mocker))

        result = run_module(module_entry=module_main, module_args=dict(
            moid="vm-123",
            _ansible_check_mode=True
        ))

        assert result["changed"] is True
        self.existing_vm.ReconfigVM_Task.assert_not_called()

    def test_state_absent(self, mocker):
        self.__prepare(mocker, vm=self.mock_existing_vm(mocker))

        result = run_module(module_entry=module_main, module_args=dict(
            moid="vm-123",
            state="absent"
        ))

        assert result["changed"] is True
        self.existing_vm.Destroy_Task.assert_called_once()
        self.existing_vm.UnregisterVM.assert_not_called()

    def test_state_absent_delete_from_inventory(self, mocker):
        self.__prepare(mocker, vm=self.mock_existing_vm(mocker))

        result = run_module(module_entry=module_main, module_args=dict(
            moid="vm-123",
            state="absent",
            delete_from_inventory=True
        ))

        assert result["changed"] is True
        self.existing_vm.UnregisterVM.assert_called_once()
        self.existing_vm.Destroy_Task.assert_not_called()

    def test_state_absent_no_vm(self, mocker):
        self.__prepare(mocker, vm=None)

        result = run_module(module_entry=module_main, module_args=dict(
            moid="vm-123",
            state="absent"
        ))

        assert result["changed"] is False

    def test_state_absent_check_mode(self, mocker):
        self.__prepare(mocker, vm=self.mock_existing_vm(mocker))

        result = run_module(module_entry=module_main, module_args=dict(
            moid="vm-123",
            state="absent",
            _ansible_check_mode=True
        ))

        assert result["changed"] is True
        self.existing_vm.Destroy_Task.assert_not_called()
        self.existing_vm.UnregisterVM.assert_not_called()

    def test_state_present_update_with_power_cycle(self, mocker):
        self.__prepare(mocker, vm=self.mock_existing_vm(mocker))
        self.change_set.power_cycle_required = True
        # The VM is powered on before the update and powered off in between the two
        # power state checks, so both the power off and power on tasks run.
        self.existing_vm.summary.runtime.powerState.lower.side_effect = ["poweredon", "poweredoff"]

        result = run_module(module_entry=module_main, module_args=dict(
            moid="vm-123",
            allow_power_cycling=True
        ))

        assert result["changed"] is True
        assert result["power_cycled_for_update"] is True
        self.existing_vm.PowerOffVM_Task.assert_called_once()
        self.existing_vm.ReconfigVM_Task.assert_called_once()
        self.existing_vm.PowerOnVM_Task.assert_called_once()

    def test_update_power_cycle_not_allowed_fails(self, mocker):
        self.__prepare(mocker, vm=self.mock_existing_vm(mocker))
        self.change_set.power_cycle_required = True
        self.existing_vm.summary.runtime.powerState.lower.return_value = "poweredon"
        self.builder.error_handler.fail_with_generic_power_cycle_error.side_effect = \
            AnsibleFailJson("power cycling is not allowed")

        run_module(
            module_entry=module_main,
            module_args=dict(moid="vm-123", allow_power_cycling=False),
            expect_success=False
        )

        self.builder.error_handler.fail_with_generic_power_cycle_error.assert_called_once()
        self.existing_vm.ReconfigVM_Task.assert_not_called()

    def test_update_task_error_fails(self, mocker):
        self.__prepare(mocker, vm=self.mock_existing_vm(mocker))
        mocker.patch.object(
            RunningTaskMonitor, 'wait_for_completion',
            side_effect=TaskError("boom", parent_error=Exception("boom"))
        )

        result = run_module(
            module_entry=module_main,
            module_args=dict(moid="vm-123"),
            expect_success=False
        )

        assert result["failed"] is True
        assert result["error_code"] == "TASK_ERROR"

    def test_update_invalid_power_state_retries_with_power_cycle(self, mocker):
        self.__prepare(mocker, vm=self.mock_existing_vm(mocker))
        # First reconfigure fails because the VM is powered on, so the module powers it
        # off and retries. The remaining tasks (power off, retry, power on) succeed.
        mocker.patch.object(
            RunningTaskMonitor, 'wait_for_completion',
            side_effect=[
                TaskError("bad power state", parent_error=vim.fault.InvalidPowerState()),
                (True, {'result': self.existing_vm}),
                (True, {'result': self.existing_vm}),
                (True, {'result': self.existing_vm}),
            ]
        )
        self.existing_vm.summary.runtime.powerState.lower.side_effect = ["poweredon", "poweredoff"]

        result = run_module(module_entry=module_main, module_args=dict(
            moid="vm-123",
            allow_power_cycling=True
        ))

        assert result["changed"] is True
        assert result["power_cycled_for_update"] is True
        self.existing_vm.PowerOffVM_Task.assert_called_once()
        self.existing_vm.PowerOnVM_Task.assert_called_once()
        assert self.existing_vm.ReconfigVM_Task.call_count == 2

    def mock_existing_vm(self, mocker):
        """
        Build a mock representing a VM that already exists in vCenter, and is powered off
        so delete/update paths do not attempt a power cycle.
        """
        self.existing_vm = mocker.MagicMock()
        self.existing_vm.name = "test-vm"
        self.existing_vm._GetMoId.return_value = "vm-123"
        self.existing_vm.summary.runtime.powerState.lower.return_value = "poweredoff"
        return self.existing_vm

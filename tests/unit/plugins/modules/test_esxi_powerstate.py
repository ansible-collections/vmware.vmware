from __future__ import absolute_import, division, print_function
__metaclass__ = type

import sys
import pytest

from ansible_collections.vmware.vmware.plugins.modules.esxi_powerstate import (
    EsxiPowerstateModule,
    main as module_main
)
from ansible_collections.vmware.vmware.plugins.module_utils.clients.pyvmomi import (
    PyvmomiClient
)
from ansible_collections.vmware.vmware.plugins.module_utils._vsphere_tasks import (
    RunningTaskMonitor,
    TaskError
)
from ...common.utils import (
    run_module, ModuleTestCase
)
from ...common.vmware_object_mocks import (
    MockEsxiHost
)
from datetime import datetime
from pyVmomi import vim, vmodl

pytestmark = pytest.mark.skipif(
    sys.version_info < (2, 7), reason="requires python2.7 or higher"
)


class TestEsxiPowerstate(ModuleTestCase):

    def __prepare(self, mocker):
        self.content_mock = mocker.MagicMock()
        mocker.patch.object(PyvmomiClient, 'connect_to_api', return_value=(mocker.Mock(), self.content_mock))
        self.test_esxi = MockEsxiHost(name="test")

        mocker.patch.object(EsxiPowerstateModule, 'get_esxi_host_by_name_or_moid', return_value=self.test_esxi)
        mocker.patch.object(RunningTaskMonitor, 'wait_for_completion', return_value=(True, True))
        # Default to no pre-existing scheduled tasks on the host.
        self.content_mock.scheduledTaskManager.RetrieveEntityScheduledTask.return_value = []

    def _mock_existing_task(self, mocker, name, method_name, run_at, enabled=True, description=""):
        """
        Builds a mock ScheduledTask that mimics what vCenter returns from
        RetrieveEntityScheduledTask, for reconcile testing.
        """
        task = mocker.MagicMock()
        task.info.name = name
        task.info.enabled = enabled
        task.info.description = description
        task.info.action.name = method_name
        task.info.scheduler.runAt = run_at
        return task

    def test_no_change(self, mocker):
        self.__prepare(mocker)
        self.test_esxi.runtime.powerState = "poweredOn"

        module_args = dict(
            name=self.test_esxi.name,
            state="powered-on"
        )

        result = run_module(module_entry=module_main, module_args=module_args)

        assert result["changed"] is False
        assert result["host"]["name"] == self.test_esxi.name

    def test_shutdown(self, mocker):
        self.__prepare(mocker)
        self.test_esxi.runtime.powerState = "poweredOn"

        module_args = dict(
            name=self.test_esxi.name,
            state="powered-off",
            force=True
        )

        result = run_module(module_entry=module_main, module_args=module_args)

        assert result["changed"] is True

    def test_reboot(self, mocker):
        self.__prepare(mocker)
        self.test_esxi.runtime.powerState = "poweredOn"

        module_args = dict(
            name=self.test_esxi.name,
            state="restarted",
            force=True
        )

        result = run_module(module_entry=module_main, module_args=module_args)

        assert result["changed"] is True

    def test_standby(self, mocker):
        self.__prepare(mocker)
        self.test_esxi.runtime.powerState = "poweredOn"

        module_args = dict(
            name=self.test_esxi.name,
            state="standby",
            evacuate_powered_off_vms=True
        )

        result = run_module(module_entry=module_main, module_args=module_args)

        assert result["changed"] is True

    def test_power_up_from_standby(self, mocker):
        self.__prepare(mocker)
        self.test_esxi.runtime.powerState = "standBy"

        module_args = dict(
            name=self.test_esxi.name,
            state="powered-on"
        )

        result = run_module(module_entry=module_main, module_args=module_args)

        assert result["changed"] is True

    def test_power_up_from_poweredoff_fails(self, mocker):
        self.__prepare(mocker)
        self.test_esxi.runtime.powerState = "poweredOff"

        module_args = dict(
            name=self.test_esxi.name,
            state="powered-on"
        )

        result = run_module(module_entry=module_main, module_args=module_args, expect_success=False)

        assert result["failed"] is True
        assert "fully powered off" in result["msg"]

    def test_check_mode(self, mocker):
        self.__prepare(mocker)
        self.test_esxi.runtime.powerState = "poweredOn"

        module_args = dict(
            name=self.test_esxi.name,
            state="powered-off",
            _ansible_check_mode=True
        )

        result = run_module(module_entry=module_main, module_args=module_args)

        assert result["changed"] is True

    def test_task_error(self, mocker):
        self.__prepare(mocker)
        self.test_esxi.runtime.powerState = "poweredOn"
        mocker.patch.object(RunningTaskMonitor, 'wait_for_completion', side_effect=TaskError("boom"))

        module_args = dict(
            name=self.test_esxi.name,
            state="restarted",
            force=True
        )

        result = run_module(module_entry=module_main, module_args=module_args, expect_success=False)

        assert result["failed"] is True

    def test_scheduled_power_off(self, mocker):
        self.__prepare(mocker)
        self.test_esxi.runtime.powerState = "poweredOn"
        mocker.patch.object(EsxiPowerstateModule, 'is_vcenter', return_value=True)

        module_args = dict(
            name=self.test_esxi.name,
            state="powered-off",
            scheduled_at="09/03/2030 10:18",
            scheduled_task_name="task_00001",
            scheduled_task_description="Sample task to shutdown host",
            scheduled_task_enabled=True
        )

        result = run_module(module_entry=module_main, module_args=module_args)

        assert result["changed"] is True
        self.content_mock.scheduledTaskManager.CreateScheduledTask.assert_called_once()

    def test_scheduled_create_defaults_when_unspecified(self, mocker):
        self.__prepare(mocker)
        self.test_esxi.runtime.powerState = "poweredOn"
        mocker.patch.object(EsxiPowerstateModule, 'is_vcenter', return_value=True)

        # No existing task, and the user did not specify description or enabled. The API
        # requires both, so create defaults (empty description, enabled) must be used.
        module_args = dict(
            name=self.test_esxi.name,
            state="powered-off",
            scheduled_at="09/03/2030 10:18",
            scheduled_task_name="task_00001"
        )

        result = run_module(module_entry=module_main, module_args=module_args)

        assert result["changed"] is True
        self.content_mock.scheduledTaskManager.CreateScheduledTask.assert_called_once()
        spec = self.content_mock.scheduledTaskManager.CreateScheduledTask.call_args[0][1]
        assert spec.description == ""
        assert spec.enabled is True

    def test_scheduled_no_change_when_task_matches(self, mocker):
        self.__prepare(mocker)
        self.test_esxi.runtime.powerState = "poweredOn"
        mocker.patch.object(EsxiPowerstateModule, 'is_vcenter', return_value=True)

        existing = self._mock_existing_task(
            mocker,
            name="task_00001",
            method_name="ShutdownHost_Task",
            run_at=datetime(2030, 3, 9, 10, 18),
            enabled=True,
            description="my task"
        )
        self.content_mock.scheduledTaskManager.RetrieveEntityScheduledTask.return_value = [existing]

        module_args = dict(
            name=self.test_esxi.name,
            state="powered-off",
            scheduled_at="09/03/2030 10:18",
            scheduled_task_name="task_00001",
            scheduled_task_description="my task",
            scheduled_task_enabled=True
        )

        result = run_module(module_entry=module_main, module_args=module_args)

        assert result["changed"] is False
        self.content_mock.scheduledTaskManager.CreateScheduledTask.assert_not_called()
        existing.ReconfigureScheduledTask.assert_not_called()

    def test_scheduled_ignores_description_when_not_specified(self, mocker):
        self.__prepare(mocker)
        self.test_esxi.runtime.powerState = "poweredOn"
        mocker.patch.object(EsxiPowerstateModule, 'is_vcenter', return_value=True)

        # Existing task has a description, but the user did not specify one, so it must not
        # be compared and the task should be considered a match.
        existing = self._mock_existing_task(
            mocker,
            name="task_00001",
            method_name="ShutdownHost_Task",
            run_at=datetime(2030, 3, 9, 10, 18),
            enabled=True,
            description="some pre-existing description"
        )
        self.content_mock.scheduledTaskManager.RetrieveEntityScheduledTask.return_value = [existing]

        module_args = dict(
            name=self.test_esxi.name,
            state="powered-off",
            scheduled_at="09/03/2030 10:18",
            scheduled_task_name="task_00001",
            scheduled_task_enabled=True
        )

        result = run_module(module_entry=module_main, module_args=module_args)

        assert result["changed"] is False
        existing.ReconfigureScheduledTask.assert_not_called()

    def test_scheduled_reconfigure_when_task_drifts(self, mocker):
        self.__prepare(mocker)
        self.test_esxi.runtime.powerState = "poweredOn"
        mocker.patch.object(EsxiPowerstateModule, 'is_vcenter', return_value=True)

        # Existing task has a different run time than requested, so it should be reconfigured.
        existing = self._mock_existing_task(
            mocker,
            name="task_00001",
            method_name="ShutdownHost_Task",
            run_at=datetime(2030, 3, 9, 8, 0),
            enabled=True,
            description="my task"
        )
        self.content_mock.scheduledTaskManager.RetrieveEntityScheduledTask.return_value = [existing]

        module_args = dict(
            name=self.test_esxi.name,
            state="powered-off",
            scheduled_at="09/03/2030 10:18",
            scheduled_task_name="task_00001",
            scheduled_task_description="my task",
            scheduled_task_enabled=True
        )

        result = run_module(module_entry=module_main, module_args=module_args)

        assert result["changed"] is True
        existing.ReconfigureScheduledTask.assert_called_once()
        self.content_mock.scheduledTaskManager.CreateScheduledTask.assert_not_called()

    def test_scheduled_reconfigure_carries_forward_unspecified(self, mocker):
        self.__prepare(mocker)
        self.test_esxi.runtime.powerState = "poweredOn"
        mocker.patch.object(EsxiPowerstateModule, 'is_vcenter', return_value=True)

        # The run time drifts, but the user did not specify description or enabled, so the
        # existing values must be carried forward into the reconfigure spec (both are
        # required by the API).
        existing = self._mock_existing_task(
            mocker,
            name="task_00001",
            method_name="ShutdownHost_Task",
            run_at=datetime(2030, 3, 9, 8, 0),
            enabled=False,
            description="keep me"
        )
        self.content_mock.scheduledTaskManager.RetrieveEntityScheduledTask.return_value = [existing]

        module_args = dict(
            name=self.test_esxi.name,
            state="powered-off",
            scheduled_at="09/03/2030 10:18",
            scheduled_task_name="task_00001"
        )

        result = run_module(module_entry=module_main, module_args=module_args)

        assert result["changed"] is True
        existing.ReconfigureScheduledTask.assert_called_once()
        spec = existing.ReconfigureScheduledTask.call_args[0][0]
        assert spec.description == "keep me"
        assert spec.enabled is False

    def test_scheduled_reconfigure_when_enabled_drifts(self, mocker):
        self.__prepare(mocker)
        self.test_esxi.runtime.powerState = "poweredOn"
        mocker.patch.object(EsxiPowerstateModule, 'is_vcenter', return_value=True)

        # Existing task is disabled, but the user requested it enabled.
        existing = self._mock_existing_task(
            mocker,
            name="task_00001",
            method_name="ShutdownHost_Task",
            run_at=datetime(2030, 3, 9, 10, 18),
            enabled=False
        )
        self.content_mock.scheduledTaskManager.RetrieveEntityScheduledTask.return_value = [existing]

        module_args = dict(
            name=self.test_esxi.name,
            state="powered-off",
            scheduled_at="09/03/2030 10:18",
            scheduled_task_name="task_00001",
            scheduled_task_enabled=True
        )

        result = run_module(module_entry=module_main, module_args=module_args)

        assert result["changed"] is True
        existing.ReconfigureScheduledTask.assert_called_once()

    def test_scheduled_check_mode_create(self, mocker):
        self.__prepare(mocker)
        self.test_esxi.runtime.powerState = "poweredOn"
        mocker.patch.object(EsxiPowerstateModule, 'is_vcenter', return_value=True)

        # No existing task, so a change would occur, but check mode must not create it.
        module_args = dict(
            name=self.test_esxi.name,
            state="powered-off",
            scheduled_at="09/03/2030 10:18",
            scheduled_task_name="task_00001",
            _ansible_check_mode=True
        )

        result = run_module(module_entry=module_main, module_args=module_args)

        assert result["changed"] is True
        self.content_mock.scheduledTaskManager.CreateScheduledTask.assert_not_called()

    def test_scheduled_check_mode_no_change(self, mocker):
        self.__prepare(mocker)
        self.test_esxi.runtime.powerState = "poweredOn"
        mocker.patch.object(EsxiPowerstateModule, 'is_vcenter', return_value=True)

        # An identical task already exists, so check mode must report no change.
        existing = self._mock_existing_task(
            mocker,
            name="task_00001",
            method_name="ShutdownHost_Task",
            run_at=datetime(2030, 3, 9, 10, 18)
        )
        self.content_mock.scheduledTaskManager.RetrieveEntityScheduledTask.return_value = [existing]

        module_args = dict(
            name=self.test_esxi.name,
            state="powered-off",
            scheduled_at="09/03/2030 10:18",
            scheduled_task_name="task_00001",
            _ansible_check_mode=True
        )

        result = run_module(module_entry=module_main, module_args=module_args)

        assert result["changed"] is False
        self.content_mock.scheduledTaskManager.CreateScheduledTask.assert_not_called()
        existing.ReconfigureScheduledTask.assert_not_called()

    def test_scheduled_check_mode_reconfigure(self, mocker):
        self.__prepare(mocker)
        self.test_esxi.runtime.powerState = "poweredOn"
        mocker.patch.object(EsxiPowerstateModule, 'is_vcenter', return_value=True)

        # A drifted task exists; check mode must detect the change but not reconfigure it.
        existing = self._mock_existing_task(
            mocker,
            name="task_00001",
            method_name="ShutdownHost_Task",
            run_at=datetime(2030, 3, 9, 8, 0)
        )
        self.content_mock.scheduledTaskManager.RetrieveEntityScheduledTask.return_value = [existing]

        module_args = dict(
            name=self.test_esxi.name,
            state="powered-off",
            scheduled_at="09/03/2030 10:18",
            scheduled_task_name="task_00001",
            _ansible_check_mode=True
        )

        result = run_module(module_entry=module_main, module_args=module_args)

        assert result["changed"] is True
        existing.ReconfigureScheduledTask.assert_not_called()

    def test_scheduled_requires_vcenter(self, mocker):
        self.__prepare(mocker)
        self.test_esxi.runtime.powerState = "poweredOn"
        mocker.patch.object(EsxiPowerstateModule, 'is_vcenter', return_value=False)

        module_args = dict(
            name=self.test_esxi.name,
            state="powered-off",
            scheduled_at="09/03/2030 10:18"
        )

        result = run_module(module_entry=module_main, module_args=module_args, expect_success=False)

        assert result["failed"] is True
        assert "vCenter" in result["msg"]

    def test_scheduled_duplicate_name(self, mocker):
        self.__prepare(mocker)
        self.test_esxi.runtime.powerState = "poweredOn"
        mocker.patch.object(EsxiPowerstateModule, 'is_vcenter', return_value=True)
        self.content_mock.scheduledTaskManager.CreateScheduledTask.side_effect = vim.fault.DuplicateName(msg="dup")

        module_args = dict(
            name=self.test_esxi.name,
            state="powered-off",
            scheduled_at="09/03/2030 10:18",
            scheduled_task_name="task_00001"
        )

        result = run_module(module_entry=module_main, module_args=module_args, expect_success=False)

        assert result["failed"] is True

    def test_scheduled_past_time(self, mocker):
        self.__prepare(mocker)
        self.test_esxi.runtime.powerState = "poweredOn"
        mocker.patch.object(EsxiPowerstateModule, 'is_vcenter', return_value=True)
        self.content_mock.scheduledTaskManager.CreateScheduledTask.side_effect = vmodl.fault.InvalidArgument(msg="bad")

        module_args = dict(
            name=self.test_esxi.name,
            state="powered-off",
            scheduled_at="09/03/2000 10:18"
        )

        result = run_module(module_entry=module_main, module_args=module_args, expect_success=False)

        assert result["failed"] is True
        assert "already passed" in result["msg"]

    def test_scheduled_invalid_date(self, mocker):
        self.__prepare(mocker)
        self.test_esxi.runtime.powerState = "poweredOn"
        mocker.patch.object(EsxiPowerstateModule, 'is_vcenter', return_value=True)

        module_args = dict(
            name=self.test_esxi.name,
            state="powered-off",
            scheduled_at="not-a-date"
        )

        result = run_module(module_entry=module_main, module_args=module_args, expect_success=False)

        assert result["failed"] is True

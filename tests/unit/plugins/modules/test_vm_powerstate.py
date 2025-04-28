from __future__ import absolute_import, division, print_function
__metaclass__ = type

import sys
import pytest

from ansible_collections.vmware.vmware.plugins.modules.vm_powerstate import (
    VmPowerstateModule,
    main as module_main
)
from ansible_collections.vmware.vmware.plugins.module_utils.clients.pyvmomi import (
    PyvmomiClient
)
from ...common.utils import (
    run_module, ModuleTestCase
)
from ansible_collections.vmware.vmware.plugins.module_utils._vsphere_tasks import RunningTaskMonitor, VmQuestionHandler

pytestmark = pytest.mark.skipif(
    sys.version_info < (2, 7), reason="requires python2.7 or higher"
)


class TestVmPowerstate(ModuleTestCase):

    def __prepare(self, mocker):
        self.content_mock = mocker.MagicMock()
        mocker.patch.object(PyvmomiClient, 'connect_to_api', return_value=(mocker.Mock(), self.content_mock))
        self.vm_mock = mocker.MagicMock()
        self.vm_mock.configure_mock(
            **{
                "summary.runtime.powerState.lower.return_value": "poweredon",
                "runtime.question": False
            }
        )
        self.content_mock.configure_mock(
            **{
                "content.scheduledTaskManager.CreateScheduledTask.return_value": True
            }
        )
        mocker.patch.object(VmPowerstateModule, 'get_vms_using_params', return_value=([self.vm_mock]))

        mocker.patch.object(VmQuestionHandler, 'handle_vm_questions')

    def test_no_change(self, mocker):
        self.__prepare(mocker)

        module_args = dict(
            datacenter="DC0",
            folder="DC0/vm/e2e-qe",
            name="vm1",
            state="powered-on"
        )

        result = run_module(module_entry=module_main, module_args=module_args)

        assert result["changed"] is False

    def test_power_on(self, mocker):
        self.__prepare(mocker)

        module_args = dict(
            datacenter="DC0",
            folder="DC0/vm/e2e-qe",
            name="vm1",
            state="powered-on"
        )

        mocker.patch.object(RunningTaskMonitor, 'wait_for_completion', return_value=(True, True))
        self.vm_mock.configure_mock(
            **{
                "PowerOn.return_value": type('', (object,), {"info": type('', (object,), {"state": "success"})()})(),
                "summary.runtime.powerState.lower.return_value": "poweredoff"
            }
        )

        result = run_module(module_entry=module_main, module_args=module_args)

        assert result["changed"] is True

    def test_power_off(self, mocker):
        self.__prepare(mocker)

        module_args = dict(
            datacenter="DC0",
            folder="DC0/vm/e2e-qe",
            name="vm1",
            state="powered-off"
        )

        mocker.patch.object(RunningTaskMonitor, 'wait_for_completion', return_value=(True, True))
        self.vm_mock.configure_mock(
            **{
                "PowerOff.return_value": type('', (object,), {"info": type('', (object,), {"state": "success"})()})()
            }
        )

        result = run_module(module_entry=module_main, module_args=module_args)

        assert result["changed"] is True

    def test_scheduled_power_off(self, mocker):
        self.__prepare(mocker)

        module_args = dict(
            datacenter="DC0",
            folder="DC0/vm/e2e-qe",
            name="vm1",
            state="powered-off",
            scheduled_at="09/03/2025 10:18",
            scheduled_task_name="task_00001",
            scheduled_task_description="Sample task to poweroff VM",
            scheduled_task_enabled=True
        )

        mocker.patch.object(VmPowerstateModule, 'is_vcenter', return_value=True)

        result = run_module(module_entry=module_main, module_args=module_args)

        assert result["changed"] is True

from __future__ import absolute_import, division, print_function
__metaclass__ = type

import sys
import pytest

try:
    from pyVmomi import vmodl
except ImportError:
    pass

from ansible_collections.vmware.vmware.plugins.modules.vmware_guest_powerstate import (
    VmwareGuestPowerstateModule,
    main as module_main
)
from ansible_collections.vmware.vmware.plugins.module_utils.clients._pyvmomi import (
    PyvmomiClient
)
from .common.utils import (
    AnsibleExitJson, AnsibleFailJson, ModuleTestCase, set_module_args,
)
from .common.vmware_object_mocks import (
    MockEsxiHost, MockVmwareObject
)
from ansible_collections.vmware.vmware.plugins.module_utils._vmware_tasks import TaskError, RunningTaskMonitor

pytestmark = pytest.mark.skipif(
    sys.version_info < (2, 7), reason="requires python2.7 or higher"
)


class TestVmwareGuestPowerstate(ModuleTestCase):

    def __prepare(self, mocker):
        self.content_mock = mocker.MagicMock()
        mocker.patch.object(PyvmomiClient, 'connect_to_api', return_value=(mocker.Mock(), self.content_mock))
        self.vm_mock = mocker.MagicMock()
        mocker.patch.object(VmwareGuestPowerstateModule, 'get_vm_using_params', return_value=([self.vm_mock]))

        mocker.patch.object(VmwareGuestPowerstateModule, 'current_state_matches_desired_state', return_value=False)
        mocker.patch.object(VmwareGuestPowerstateModule, 'answer_question')
        mocker.patch.object(VmwareGuestPowerstateModule, 'make_answer_response', return_value=[])

    def test_no_change(self, mocker):
        self.__prepare(mocker)

        set_module_args(
            hostname="127.0.0.1",
            username="administrator@local",
            password="123456",
            datacenter="DC0",
            folder="DC0/vm/e2e-qe",
            name="vm1",
            state="powered-on",
            validate_certs=False,
            add_cluster=False
        )

        mocker.patch.object(VmwareGuestPowerstateModule, 'current_state_matches_desired_state', return_value=True)

        with pytest.raises(AnsibleExitJson) as c:
            module_main()

        assert c.value.args[0]["changed"] is False

    def test_power_on(self, mocker):
        self.__prepare(mocker)

        set_module_args(
            hostname="127.0.0.1",
            username="administrator@local",
            password="123456",
            datacenter="DC0",
            folder="DC0/vm/e2e-qe",
            name="vm1",
            state="powered-on",
            validate_certs=False,
            add_cluster=False
        )

        mocker.patch.object(RunningTaskMonitor, 'wait_for_completion', return_value=(True, True))
        self.vm_mock.configure_mock(
            **{
                "PowerOn.return_value": {"info": {"state": "success"}}
            }
        )

        with pytest.raises(AnsibleExitJson) as c:
            module_main()

        assert c.value.args[0]["changed"] is True

    def test_power_off(self, mocker):
        self.__prepare(mocker)

        set_module_args(
            hostname="127.0.0.1",
            username="administrator@local",
            password="123456",
            datacenter="DC0",
            folder="DC0/vm/e2e-qe",
            name="vm1",
            state="powered-off",
            validate_certs=False,
            add_cluster=False
        )

        mocker.patch.object(RunningTaskMonitor, 'wait_for_completion', return_value=(True, True))
        self.vm_mock.configure_mock(
            **{
                "PowerOff.return_value": {"info": {"state": "success"}}
            }
        )

        with pytest.raises(AnsibleExitJson) as c:
            module_main()

        assert c.value.args[0]["changed"] is True

    def test_scheduled_power_off_invalid_argument(self, mocker):
        self.__prepare(mocker)

        set_module_args(
            hostname="127.0.0.1",
            username="administrator@local",
            password="123456",
            datacenter="DC0",
            folder="DC0/vm/e2e-qe",
            name="vm1",
            state="powered-off",
            validate_certs=False,
            add_cluster=False,
            scheduled_at="09/03/2024 10:18",
            scheduled_task_name="task_00001",
            scheduled_task_description="Sample task to poweroff VM",
            scheduled_task_enabled=True
        )

        self.content_mock.configure_mock(
            **{
                "content.scheduledTaskManager.CreateScheduledTask.return_value": True
            }
        )

        with pytest.raises(AnsibleFailJson) as c:
            module_main()

    def test_scheduled_power_off(self, mocker):
        self.__prepare(mocker)

        set_module_args(
            hostname="127.0.0.1",
            username="administrator@local",
            password="123456",
            datacenter="DC0",
            folder="DC0/vm/e2e-qe",
            name="vm1",
            state="powered-off",
            validate_certs=False,
            add_cluster=False,
            scheduled_at="09/03/2025 10:18",
            scheduled_task_name="task_00001",
            scheduled_task_description="Sample task to poweroff VM",
            scheduled_task_enabled=True
        )

        mocker.patch.object(VmwareGuestPowerstateModule, 'is_vcenter', return_value=True)

        with pytest.raises(AnsibleExitJson) as c:
            module_main()

        assert c.value.args[0]["changed"] is True
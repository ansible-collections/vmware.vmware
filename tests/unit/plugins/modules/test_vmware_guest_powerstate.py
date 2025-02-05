from __future__ import absolute_import, division, print_function
__metaclass__ = type

import sys
import pytest

from ansible_collections.vmware.vmware.plugins.modules.vmware_guest_powerstate import (
    VmwareGuestPowerstateModule,
    main as module_main
)
from ansible_collections.vmware.vmware.plugins.module_utils.clients._pyvmomi import (
    PyvmomiClient
)
from .common.utils import (
    AnsibleExitJson, ModuleTestCase, set_module_args,
)
from .common.vmware_object_mocks import (
    MockEsxiHost, MockVmwareObject
)
from ansible_collections.community.vmware.plugins.module_utils import vmware

pytestmark = pytest.mark.skipif(
    sys.version_info < (2, 7), reason="requires python2.7 or higher"
)


class TestVmwareGuestPowerstate(ModuleTestCase):

    def __prepare(self, mocker):
        mocker.patch.object(PyvmomiClient, 'connect_to_api', return_value=(mocker.Mock(), mocker.Mock()))

        self.vm_mock = MockVmwareObject()
        self.pyv_mock = mocker.MagicMock()
        self.pyv_mock.configure_mock(
            **{
                "get_vm.return_value": self.vm_mock,
                "is_vcenter.return_value": True,
                "content.return_value": None
            }
        )

        mocker.patch.object(VmwareGuestPowerstateModule, 'get_vm', return_value=(self.vm_mock, self.pyv_mock))

        mocker.patch.object(VmwareGuestPowerstateModule, 'current_state_matches_desired_state', return_value=False)
        mocker.patch.object(vmware, 'check_answer_question_status', return_value=False)
        mocker.patch.object(vmware, 'answer_question')
        mocker.patch.object(vmware, 'make_answer_response', return_value=[])
        mocker.patch.object(vmware, 'gather_vm_facts', return_value=mocker.Mock())
        mocker.patch.object(vmware, 'set_vm_power_state', return_value=dict(changed=True))

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

        with pytest.raises(AnsibleExitJson) as c:
            module_main()

        assert c.value.args[0]["changed"] is True
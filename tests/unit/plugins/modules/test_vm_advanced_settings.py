from __future__ import absolute_import, division, print_function
__metaclass__ = type

import sys
import pytest

from ansible_collections.vmware.vmware.plugins.modules.vm_advanced_settings import (
    VmAdvancedSettingsModule,
    main as module_main
)
from ansible_collections.vmware.vmware.plugins.module_utils.clients.pyvmomi import (
    PyvmomiClient
)
from ...common.utils import (
    AnsibleExitJson, ModuleTestCase, set_module_args,
)
from ...common.vmware_object_mocks import (
    create_mock_vsphere_object,
    MockVsphereTask
)

from pyVmomi import vim

pytestmark = pytest.mark.skipif(
    sys.version_info < (2, 7), reason="requires python2.7 or higher"
)


class TestVmPowerstate(ModuleTestCase):

    def __prepare(self, mocker):
        mocker.patch.object(PyvmomiClient, 'connect_to_api', return_value=(mocker.Mock(), mocker.Mock()))
        self.vm_mock = create_mock_vsphere_object()
        mocker.patch.object(VmAdvancedSettingsModule, 'get_vms_using_params', return_value=([self.vm_mock]))
        self.vm_mock.config.extraConfig = dict()
        self.vm_mock.ReconfigVM_Task.return_value = MockVsphereTask()

    def option_set(self, data):
        out = []
        for k, v in data.items():
            option = vim.option.OptionValue()
            option.key, option.value = k, v
            out.append(option)
        return out

    def test_no_change(self, mocker):
        self.__prepare(mocker)

        set_module_args(
            hostname="127.0.0.1",
            username="administrator@local",
            password="123456",
            name="vm1",
            state="present",
            settings=dict(),
            validate_certs=False,
            add_cluster=False
        )

        with pytest.raises(AnsibleExitJson) as c:
            module_main()

        assert c.value.args[0]["changed"] is False

    def test_add_settings(self, mocker):
        self.__prepare(mocker)

        self.vm_mock.config.extraConfig = self.option_set(dict(one=1, two=2))
        set_module_args(
            hostname="127.0.0.1",
            username="administrator@local",
            password="123456",
            name="vm1",
            state="present",
            settings=dict(two=10, three=3),
            validate_certs=False,
            add_cluster=False
        )

        with pytest.raises(AnsibleExitJson) as c:
            module_main()

        assert c.value.args[0]["changed"] is True
        self.vm_mock.ReconfigVM_Task.assert_called_once()
        assert c.value.args[0]["updated_settings"] == dict(
            two={'old': 2, 'new': 10},
            three={'old': None, 'new': 3}
        )

    def test_remove_settings(self, mocker):
        self.__prepare(mocker)

        self.vm_mock.config.extraConfig = self.option_set(dict(one=1, two=2))
        set_module_args(
            hostname="127.0.0.1",
            username="administrator@local",
            password="123456",
            name="vm1",
            state="absent",
            settings=dict(two="", three=3, one=10),
            validate_certs=False,
            add_cluster=False
        )

        with pytest.raises(AnsibleExitJson) as c:
            module_main()

        assert c.value.args[0]["changed"] is True
        self.vm_mock.ReconfigVM_Task.assert_called_once()
        assert c.value.args[0]["updated_settings"] == dict(
            two={'old': 2, 'new': None},
        )

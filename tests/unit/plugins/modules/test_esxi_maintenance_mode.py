from __future__ import absolute_import, division, print_function
__metaclass__ = type

import sys
import pytest

from ansible_collections.vmware.vmware.plugins.modules.esxi_maintenance_mode import (
    EsxiMaintenanceModeModule,
    main as module_main
)
from ansible_collections.vmware.vmware.plugins.module_utils.clients._pyvmomi import (
    PyvmomiClient
)
from ...common.utils import (
    AnsibleExitJson, ModuleTestCase, set_module_args,
)
from ...common.vmware_object_mocks import (
    MockEsxiHost
)

pytestmark = pytest.mark.skipif(
    sys.version_info < (2, 7), reason="requires python2.7 or higher"
)


class TestEsxiMaintenanceMode(ModuleTestCase):

    def __prepare(self, mocker):
        mocker.patch.object(PyvmomiClient, 'connect_to_api', return_value=(mocker.Mock(), mocker.Mock()))
        self.test_esxi = MockEsxiHost(name="test")

        mocker.patch.object(EsxiMaintenanceModeModule, 'get_esxi_host_by_name_or_moid', return_value=self.test_esxi)

    def test_no_change(self, mocker):
        self.__prepare(mocker)

        set_module_args(
            hostname="127.0.0.1",
            username="administrator@local",
            password="123456",
            add_cluster=False,
            name=self.test_esxi.name,
            enable_maintenance_mode=False
        )
        self.test_esxi.runtime.inMaintenanceMode = False

        with pytest.raises(AnsibleExitJson) as c:
            module_main()

        assert c.value.args[0]["changed"] is False

        set_module_args(
            hostname="127.0.0.1",
            username="administrator@local",
            password="123456",
            add_cluster=False,
            name=self.test_esxi.name,
            enable_maintenance_mode=True
        )
        self.test_esxi.runtime.inMaintenanceMode = True

        with pytest.raises(AnsibleExitJson) as c:
            module_main()

        assert c.value.args[0]["changed"] is False

    def test_enable(self, mocker):
        self.__prepare(mocker)

        set_module_args(
            hostname="127.0.0.1",
            username="administrator@local",
            password="123456",
            add_cluster=False,
            name=self.test_esxi.name,
            enable_maintenance_mode=True
        )
        self.test_esxi.runtime.inMaintenanceMode = False

        with pytest.raises(AnsibleExitJson) as c:
            module_main()

        assert c.value.args[0]["changed"] is True

    def test_disable(self, mocker):
        self.__prepare(mocker)

        set_module_args(
            hostname="127.0.0.1",
            username="administrator@local",
            password="123456",
            add_cluster=False,
            name=self.test_esxi.name,
            enable_maintenance_mode=False
        )
        self.test_esxi.runtime.inMaintenanceMode = True

        with pytest.raises(AnsibleExitJson) as c:
            module_main()

        assert c.value.args[0]["changed"] is True

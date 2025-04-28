from __future__ import absolute_import, division, print_function
__metaclass__ = type

import sys
import pytest

from ansible_collections.vmware.vmware.plugins.modules.esxi_maintenance_mode import (
    EsxiMaintenanceModeModule,
    main as module_main
)
from ansible_collections.vmware.vmware.plugins.module_utils.clients.pyvmomi import (
    PyvmomiClient
)
from ...common.utils import (
    run_module, ModuleTestCase
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

        module_args = dict(
            name=self.test_esxi.name,
            enable_maintenance_mode=False
        )
        self.test_esxi.runtime.inMaintenanceMode = False

        result = run_module(module_entry=module_main, module_args=module_args)

        assert result["changed"] is False

        module_args = dict(
            name=self.test_esxi.name,
            enable_maintenance_mode=True
        )
        self.test_esxi.runtime.inMaintenanceMode = True

        result = run_module(module_entry=module_main, module_args=module_args)

        assert result["changed"] is False

    def test_enable(self, mocker):
        self.__prepare(mocker)

        module_args = dict(
            name=self.test_esxi.name,
            enable_maintenance_mode=True
        )
        self.test_esxi.runtime.inMaintenanceMode = False

        result = run_module(module_entry=module_main, module_args=module_args)
        assert result["changed"] is True

    def test_disable(self, mocker):
        self.__prepare(mocker)

        module_args = dict(
            name=self.test_esxi.name,
            enable_maintenance_mode=False
        )
        self.test_esxi.runtime.inMaintenanceMode = True

        result = run_module(module_entry=module_main, module_args=module_args)
        assert result["changed"] is True

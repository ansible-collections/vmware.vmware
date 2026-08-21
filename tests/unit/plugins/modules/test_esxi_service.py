from __future__ import absolute_import, division, print_function
__metaclass__ = type

import sys
import pytest

from ansible_collections.vmware.vmware.plugins.modules.esxi_service import (
    EsxiServiceModule,
    main as module_main
)
from ansible_collections.vmware.vmware.plugins.module_utils.clients.pyvmomi import (
    PyvmomiClient
)
from ...common.utils import (
    run_module, ModuleTestCase
)
from ...common.vmware_object_mocks import (
    MockEsxiHost, MockHostService, MockServiceSystem
)

pytestmark = pytest.mark.skipif(
    sys.version_info < (2, 7), reason="requires python2.7 or higher"
)


class TestEsxiService(ModuleTestCase):

    def __prepare(self, mocker, services=None):
        mocker.patch.object(PyvmomiClient, 'connect_to_api', return_value=(mocker.Mock(), mocker.Mock()))
        self.test_esxi = MockEsxiHost(name="test")
        if services is not None:
            self.test_esxi.configManager.serviceSystem = MockServiceSystem(services=services)
        mocker.patch.object(EsxiServiceModule, 'get_esxi_host_by_name_or_moid', return_value=self.test_esxi)

    def test_start_when_stopped(self, mocker):
        self.__prepare(mocker, services=[MockHostService(key="ntpd", running=False, policy="off")])

        result = run_module(module_entry=module_main, module_args=dict(
            name=self.test_esxi.name,
            service_name="ntpd",
            state="started",
        ))
        assert result["changed"] is True

    def test_start_when_running(self, mocker):
        self.__prepare(mocker, services=[MockHostService(key="ntpd", running=True, policy="on")])

        result = run_module(module_entry=module_main, module_args=dict(
            name=self.test_esxi.name,
            service_name="ntpd",
            state="started",
        ))
        assert result["changed"] is False

    def test_stop_when_running(self, mocker):
        self.__prepare(mocker, services=[MockHostService(key="ntpd", running=True, policy="on")])

        result = run_module(module_entry=module_main, module_args=dict(
            name=self.test_esxi.name,
            service_name="ntpd",
            state="stopped",
        ))
        assert result["changed"] is True

    def test_restart_always_changes(self, mocker):
        self.__prepare(mocker, services=[MockHostService(key="ntpd", running=True, policy="on")])

        result = run_module(module_entry=module_main, module_args=dict(
            name=self.test_esxi.name,
            service_name="ntpd",
            state="restarted",
        ))
        assert result["changed"] is True

    def test_policy_only_change(self, mocker):
        self.__prepare(mocker, services=[MockHostService(key="ntpd", running=False, policy="off")])

        result = run_module(module_entry=module_main, module_args=dict(
            name=self.test_esxi.name,
            service_name="ntpd",
            service_policy="on",
        ))
        assert result["changed"] is True

    def test_policy_no_change(self, mocker):
        self.__prepare(mocker, services=[MockHostService(key="ntpd", running=False, policy="on")])

        result = run_module(module_entry=module_main, module_args=dict(
            name=self.test_esxi.name,
            service_name="ntpd",
            service_policy="on",
        ))
        assert result["changed"] is False

    def test_service_not_found(self, mocker):
        self.__prepare(mocker, services=[MockHostService(key="ntpd")])

        result = run_module(
            module_entry=module_main,
            module_args=dict(
                name=self.test_esxi.name,
                service_name="does-not-exist",
                state="started",
            ),
            expect_success=False,
        )
        assert result["failed"] is True

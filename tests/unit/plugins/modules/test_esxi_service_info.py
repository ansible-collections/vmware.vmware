from __future__ import absolute_import, division, print_function
__metaclass__ = type

import sys
import pytest

from ansible_collections.vmware.vmware.plugins.modules.esxi_service_info import (
    EsxiServiceInfoModule,
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


class TestEsxiServiceInfo(ModuleTestCase):

    def __prepare(self, mocker, services=None):
        mocker.patch.object(PyvmomiClient, 'connect_to_api', return_value=(mocker.Mock(), mocker.Mock()))
        self.test_esxi = MockEsxiHost(name="test")
        if services is not None:
            self.test_esxi.configManager.serviceSystem = MockServiceSystem(services=services)
        mocker.patch.object(EsxiServiceInfoModule, 'get_esxi_host_by_name_or_moid', return_value=self.test_esxi)

    def test_gather_all_services(self, mocker):
        self.__prepare(mocker, services=[
            MockHostService(key="ntpd", running=True, policy="on", label="NTP Daemon"),
            MockHostService(key="TSM-SSH", running=False, policy="off", label="SSH"),
        ])

        result = run_module(module_entry=module_main, module_args=dict(
            name=self.test_esxi.name,
        ))

        assert result["changed"] is False
        assert result["exists"] is True
        assert result["host"]["name"] == self.test_esxi.name
        assert result["host"]["moid"] == self.test_esxi._GetMoId()

        services = {s["key"]: s for s in result["services"]}
        assert set(services.keys()) == {"ntpd", "TSM-SSH"}
        assert services["ntpd"] == dict(
            key="ntpd",
            label="NTP Daemon",
            policy="on",
            running=True,
            required=False,
            uninstallable=False,
            source_package_name="esx-base",
            source_package_desc="ESXi base package",
        )
        assert services["TSM-SSH"]["running"] is False
        assert services["TSM-SSH"]["policy"] == "off"

    def test_filter_service_names(self, mocker):
        self.__prepare(mocker, services=[
            MockHostService(key="ntpd", running=True, policy="on"),
            MockHostService(key="TSM-SSH", running=False, policy="off"),
            MockHostService(key="DCUI", running=True, policy="on"),
        ])

        result = run_module(module_entry=module_main, module_args=dict(
            name=self.test_esxi.name,
            service_names=["ntpd", "DCUI"],
        ))

        assert result["exists"] is True
        assert {s["key"] for s in result["services"]} == {"ntpd", "DCUI"}

    def test_no_matching_services_sets_exists_false(self, mocker):
        self.__prepare(mocker, services=[
            MockHostService(key="ntpd"),
        ])

        result = run_module(module_entry=module_main, module_args=dict(
            name=self.test_esxi.name,
            service_names=["does-not-exist"],
        ))

        assert result["exists"] is False
        assert result["services"] == []

    def test_empty_service_names_returns_all(self, mocker):
        self.__prepare(mocker, services=[
            MockHostService(key="ntpd"),
            MockHostService(key="TSM-SSH"),
        ])

        result = run_module(module_entry=module_main, module_args=dict(
            name=self.test_esxi.name,
            service_names=[],
        ))

        assert {s["key"] for s in result["services"]} == {"ntpd", "TSM-SSH"}

    def test_service_without_source_package(self, mocker):
        self.__prepare(mocker, services=[
            MockHostService(key="ntpd", source_package=False),
        ])

        result = run_module(module_entry=module_main, module_args=dict(
            name=self.test_esxi.name,
        ))

        service = next(s for s in result["services"] if s["key"] == "ntpd")
        assert service["source_package_name"] is None
        assert service["source_package_desc"] is None

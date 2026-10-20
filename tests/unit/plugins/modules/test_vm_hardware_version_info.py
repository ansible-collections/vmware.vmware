from __future__ import absolute_import, division, print_function
__metaclass__ = type

import sys
import pytest
from types import SimpleNamespace

from ansible_collections.vmware.vmware.plugins.modules.vm_hardware_version_info import (
    VmHardwareInfoModule,
    main as module_main
)
from ansible_collections.vmware.vmware.plugins.module_utils.clients.pyvmomi import (
    PyvmomiClient
)
from ...common.utils import (
    run_module, ModuleTestCase
)

from pyVmomi import vim

pytestmark = pytest.mark.skipif(
    sys.version_info < (2, 7), reason="requires python2.7 or higher"
)


class TestVmHardwareVersionInfo(ModuleTestCase):

    def __prepare(self, mocker, current_version="vmx-17", supported_versions=None, scheduled=None):
        mocker.patch.object(PyvmomiClient, 'connect_to_api', return_value=(mocker.Mock(), mocker.Mock()))

        if supported_versions is None:
            supported_versions = ["vmx-17", "vmx-19", "vmx-21"]

        self.vm_mock = mocker.MagicMock()
        self.vm_mock.name = "test-vm"
        self.vm_mock._GetMoId.return_value = "vm-123"
        self.vm_mock.config.version = current_version
        self.vm_mock.config.scheduledHardwareUpgradeInfo = scheduled
        self.vm_mock.environmentBrowser.QueryConfigOptionDescriptor.return_value = \
            self.option_descriptors(supported_versions)
        mocker.patch.object(VmHardwareInfoModule, 'get_vms_using_params', return_value=[self.vm_mock])

    def option_descriptors(self, versions, upgrade_supported=True):
        return [
            vim.vm.ConfigOptionDescriptor(key=v, upgradeSupported=upgrade_supported)
            for v in versions
        ]

    @staticmethod
    def scheduled_info(version="vmx-21", policy="onSoftPowerOff", status="pending", fault=None):
        # the real vim data object only accepts a real fault object, so use a stand-in
        return SimpleNamespace(
            versionKey=version,
            upgradePolicy=policy,
            scheduledHardwareUpgradeStatus=status,
            fault=fault
        )

    def test_info_no_scheduled_upgrade(self, mocker):
        self.__prepare(mocker)

        result = run_module(module_entry=module_main, module_args=dict(name="test-vm"))

        assert result["changed"] is False
        assert result["vm"] == dict(moid="vm-123", name="test-vm")
        assert result["current"] == "vmx-17"
        assert sorted(result["available"]) == ["vmx-17", "vmx-19", "vmx-21"]
        assert result["scheduled_upgrade"] == dict()

    @pytest.mark.parametrize("module_args", [
        dict(name="test-vm"),
        dict(uuid="4219a8ef-2b53-9f6e-4f0f-5b0c3e1b8d9a"),
        dict(moid="vm-123"),
    ])
    def test_info_vm_identifiers(self, mocker, module_args):
        self.__prepare(mocker)

        result = run_module(module_entry=module_main, module_args=module_args)

        assert result["vm"] == dict(moid="vm-123", name="test-vm")

    def test_info_pending_upgrade(self, mocker):
        self.__prepare(mocker, scheduled=self.scheduled_info())

        result = run_module(module_entry=module_main, module_args=dict(name="test-vm"))

        assert result["scheduled_upgrade"] == dict(
            version="vmx-21",
            policy="onSoftPowerOff",
            status="pending",
            error=None
        )

    @pytest.mark.parametrize("status", ["none", "pending", "success", "failed"])
    def test_info_upgrade_statuses(self, mocker, status):
        self.__prepare(mocker, scheduled=self.scheduled_info(status=status, policy="always"))

        result = run_module(module_entry=module_main, module_args=dict(name="test-vm"))

        assert result["scheduled_upgrade"]["status"] == status
        assert result["scheduled_upgrade"]["policy"] == "always"

    def test_info_failed_upgrade_includes_error(self, mocker):
        fault = SimpleNamespace(localizedMessage="Cannot upgrade the virtual hardware version.")
        self.__prepare(mocker, scheduled=self.scheduled_info(status="failed", fault=fault))

        result = run_module(module_entry=module_main, module_args=dict(name="test-vm"))

        assert result["scheduled_upgrade"]["status"] == "failed"
        assert result["scheduled_upgrade"]["error"] == dict(
            message="Cannot upgrade the virtual hardware version."
        )

    def test_info_upgrade_without_fault_attribute(self, mocker):
        scheduled = SimpleNamespace(
            versionKey="vmx-19", upgradePolicy="always", scheduledHardwareUpgradeStatus="pending"
        )
        self.__prepare(mocker, scheduled=scheduled)

        result = run_module(module_entry=module_main, module_args=dict(name="test-vm"))

        assert result["scheduled_upgrade"]["error"] is None

    def test_info_ignores_versions_without_upgrade_support(self, mocker):
        self.__prepare(mocker)
        self.vm_mock.environmentBrowser.QueryConfigOptionDescriptor.return_value = (
            self.option_descriptors(["vmx-17", "vmx-19"]) +
            self.option_descriptors(["vmx-21"], upgrade_supported=False)
        )

        result = run_module(module_entry=module_main, module_args=dict(name="test-vm"))

        assert sorted(result["available"]) == ["vmx-17", "vmx-19"]

    def test_info_no_supported_versions(self, mocker):
        self.__prepare(mocker, supported_versions=[])

        result = run_module(module_entry=module_main, module_args=dict(name="test-vm"))

        assert result["available"] == []

    def test_info_deduplicates_versions(self, mocker):
        self.__prepare(mocker, supported_versions=["vmx-19", "vmx-19", "vmx-21"])

        result = run_module(module_entry=module_main, module_args=dict(name="test-vm"))

        assert sorted(result["available"]) == ["vmx-19", "vmx-21"]

    def test_info_check_mode(self, mocker):
        self.__prepare(mocker, scheduled=self.scheduled_info())

        result = run_module(
            module_entry=module_main,
            module_args=dict(name="test-vm", _ansible_check_mode=True)
        )

        assert result["changed"] is False
        assert result["current"] == "vmx-17"
        assert result["scheduled_upgrade"]["version"] == "vmx-21"

    def test_info_makes_no_changes(self, mocker):
        self.__prepare(mocker)

        run_module(module_entry=module_main, module_args=dict(name="test-vm"))

        self.vm_mock.ReconfigVM_Task.assert_not_called()
        self.vm_mock.UpgradeVM_Task.assert_not_called()

    def test_info_requires_vm_identifier(self, mocker):
        self.__prepare(mocker)

        result = run_module(module_entry=module_main, module_args=dict(), expect_success=False)

        assert result["failed"] is True

    def test_info_identifiers_are_mutually_exclusive(self, mocker):
        self.__prepare(mocker)

        result = run_module(
            module_entry=module_main,
            module_args=dict(name="test-vm", moid="vm-123"),
            expect_success=False
        )

        assert result["failed"] is True

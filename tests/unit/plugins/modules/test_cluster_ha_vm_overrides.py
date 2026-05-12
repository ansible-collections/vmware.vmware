from __future__ import absolute_import, division, print_function

__metaclass__ = type

import sys
import pytest
from unittest.mock import Mock, patch

from ansible_collections.vmware.vmware.plugins.modules.cluster_ha_vm_overrides import (
    VMwareHaVmOverrides,
    main as module_main,
)
from ansible_collections.vmware.vmware.plugins.module_utils.clients.pyvmomi import (
    PyvmomiClient,
)
from ...common.utils import run_module, ModuleTestCase
from ...common.vmware_object_mocks import MockCluster, create_mock_vsphere_object

pytestmark = pytest.mark.skipif(
    sys.version_info < (2, 7), reason="requires python2.7 or higher"
)


class MockDasVmConfigInfo(Mock):
    pass


class MockDasVmConfigSpec(Mock):
    pass


class TestVMwareHaVmOverrides(ModuleTestCase):

    def _mock_ha_vm_config(self, mocker, vm=None, restart_priority="medium", isolation_response="none"):
        mock_config = mocker.Mock()
        if vm is None:
            vm = create_mock_vsphere_object()
        mock_config.key = vm
        mock_das = mocker.Mock()
        mock_das.restartPriority = restart_priority
        mock_das.isolationResponse = isolation_response
        mock_das.restartPriorityTimeout = None
        mock_das.vmToolsMonitoringSettings = None
        mock_das.vmComponentProtectionSettings = None
        mock_config.dasSettings = mock_das
        return mock_config

    def __prepare(self, mocker):
        mocker.patch.object(
            PyvmomiClient, "connect_to_api", return_value=(mocker.Mock(), mocker.Mock())
        )
        self.test_cluster = MockCluster()
        self.test_cluster.configurationEx.dasConfig = mocker.Mock()
        self.test_cluster.configurationEx.dasConfig.enabled = True
        self.test_cluster.configurationEx.dasVmConfig = []

        self.base_args = dict(
            datacenter="foo",
            cluster=self.test_cluster.name,
            state="present",
            append=True,
            vm_overrides=[
                {
                    "virtual_machine": "vm-1234567890",
                    "restart_priority": "high",
                    "host_isolation_response": "shutdown",
                }
            ],
        )

        mocker.patch.object(
            VMwareHaVmOverrides,
            "get_datacenter_by_name_or_moid",
            return_value=mocker.Mock(),
        )
        mocker.patch.object(
            VMwareHaVmOverrides,
            "get_cluster_by_name_or_moid",
            return_value=self.test_cluster,
        )

        self.test_vm = create_mock_vsphere_object()
        mocker.patch.object(
            VMwareHaVmOverrides,
            "get_objs_by_name_or_moid",
            return_value=[self.test_vm],
        )

    @patch(
        "ansible_collections.vmware.vmware.plugins.modules.cluster_ha_vm_overrides.vim.cluster.DasVmConfigInfo",
        new=MockDasVmConfigInfo,
    )
    @patch(
        "ansible_collections.vmware.vmware.plugins.modules.cluster_ha_vm_overrides.vim.cluster.DasVmConfigSpec",
        new=MockDasVmConfigSpec,
    )
    def test_present_no_existing_config(self, mocker):
        self.__prepare(mocker)
        module_args = self.base_args

        result = run_module(module_entry=module_main, module_args=module_args)
        assert result["changed"] is True

        module_args = {**self.base_args, **{"vm_overrides": []}}
        result = run_module(module_entry=module_main, module_args=module_args)
        assert result["changed"] is False

        module_args = {**self.base_args, **{"state": "present", "append": False}}
        result = run_module(module_entry=module_main, module_args=module_args)
        assert result["changed"] is True

    @patch(
        "ansible_collections.vmware.vmware.plugins.modules.cluster_ha_vm_overrides.vim.cluster.DasVmConfigInfo",
        new=MockDasVmConfigInfo,
    )
    @patch(
        "ansible_collections.vmware.vmware.plugins.modules.cluster_ha_vm_overrides.vim.cluster.DasVmConfigSpec",
        new=MockDasVmConfigSpec,
    )
    def test_present_with_existing_config(self, mocker):
        self.__prepare(mocker)
        existing_vm = create_mock_vsphere_object(name="foo", moid="vm-1234567890")
        self.test_cluster.configurationEx.dasVmConfig = [
            self._mock_ha_vm_config(mocker, existing_vm)
        ]

        module_args = self.base_args
        result = run_module(module_entry=module_main, module_args=module_args)
        assert result["changed"] is True

        module_args = {**self.base_args, **{"append": False}}
        result = run_module(module_entry=module_main, module_args=module_args)
        assert result["changed"] is True

        module_args = {
            **self.base_args,
            **{
                "vm_overrides": [
                    {
                        "virtual_machine": existing_vm._GetMoId(),
                        "restart_priority": "high",
                        "host_isolation_response": "shutdown",
                    }
                ]
            },
        }
        mocker.patch.object(
            VMwareHaVmOverrides, "get_objs_by_name_or_moid", return_value=[existing_vm]
        )
        self.test_cluster.configurationEx.dasVmConfig = [
            self._mock_ha_vm_config(
                mocker,
                existing_vm,
                restart_priority="high",
                isolation_response="shutdown",
            )
        ]
        result = run_module(module_entry=module_main, module_args=module_args)
        assert result["changed"] is False

    @patch(
        "ansible_collections.vmware.vmware.plugins.modules.cluster_ha_vm_overrides.vim.cluster.DasVmConfigInfo",
        new=MockDasVmConfigInfo,
    )
    @patch(
        "ansible_collections.vmware.vmware.plugins.modules.cluster_ha_vm_overrides.vim.cluster.DasVmConfigSpec",
        new=MockDasVmConfigSpec,
    )
    def test_absent_with_existing_config(self, mocker):
        self.__prepare(mocker)
        existing_vm = create_mock_vsphere_object(name="foo", moid="vm-1234567890")
        self.test_cluster.configurationEx.dasVmConfig = [
            self._mock_ha_vm_config(mocker, existing_vm)
        ]

        module_args = {**self.base_args, **{"state": "absent"}}
        result = run_module(module_entry=module_main, module_args=module_args)
        assert result["changed"] is False

        module_args = {
            **self.base_args,
            **{
                "state": "absent",
                "vm_overrides": [{"virtual_machine": existing_vm._GetMoId()}],
            },
        }
        mocker.patch.object(
            VMwareHaVmOverrides, "get_objs_by_name_or_moid", return_value=[existing_vm]
        )
        result = run_module(module_entry=module_main, module_args=module_args)
        assert result["changed"] is True

    @patch(
        "ansible_collections.vmware.vmware.plugins.modules.cluster_ha_vm_overrides.vim.cluster.DasVmConfigInfo",
        new=MockDasVmConfigInfo,
    )
    @patch(
        "ansible_collections.vmware.vmware.plugins.modules.cluster_ha_vm_overrides.vim.cluster.DasVmConfigSpec",
        new=MockDasVmConfigSpec,
    )
    def test_present_add_with_monitoring_and_storage_options(self, mocker):
        self.__prepare(mocker)
        module_args = {
            **self.base_args,
            "vm_overrides": [
                {
                    "virtual_machine": "vm-1234567890",
                    "restart_priority": "low",
                    "host_isolation_response": "powerOff",
                    "restart_priority_timeout": 90,
                    "vm_monitoring": {
                        "use_cluster_settings": True,
                    },
                    "storage_apd_response": {
                        "mode": "restartConservative",
                        "delay": 60,
                        "restart_vms": True,
                    },
                    "storage_pdl_response_mode": "restart",
                }
            ],
        }
        result = run_module(module_entry=module_main, module_args=module_args)
        assert result["changed"] is True

    @patch(
        "ansible_collections.vmware.vmware.plugins.modules.cluster_ha_vm_overrides.vim.cluster.DasVmConfigInfo",
        new=MockDasVmConfigInfo,
    )
    @patch(
        "ansible_collections.vmware.vmware.plugins.modules.cluster_ha_vm_overrides.vim.cluster.DasVmConfigSpec",
        new=MockDasVmConfigSpec,
    )
    def test_present_add_with_vm_monitoring_custom_fields(self, mocker):
        self.__prepare(mocker)
        module_args = {
            **self.base_args,
            "vm_overrides": [
                {
                    "virtual_machine": "vm-1234567890",
                    "restart_priority": "high",
                    "vm_monitoring": {
                        "use_cluster_settings": False,
                        "mode": "vmAndAppMonitoring",
                        "failure_interval": 20,
                        "minimum_uptime": 60,
                        "maximum_resets": 2,
                        "maximum_resets_window": 120,
                    },
                }
            ],
        }
        result = run_module(module_entry=module_main, module_args=module_args)
        assert result["changed"] is True

    @patch(
        "ansible_collections.vmware.vmware.plugins.modules.cluster_ha_vm_overrides.vim.cluster.DasVmConfigInfo",
        new=MockDasVmConfigInfo,
    )
    @patch(
        "ansible_collections.vmware.vmware.plugins.modules.cluster_ha_vm_overrides.vim.cluster.DasVmConfigSpec",
        new=MockDasVmConfigSpec,
    )
    def test_present_triggers_update_apply(self, mocker):
        self.__prepare(mocker)
        existing_vm = create_mock_vsphere_object(name="foo", moid="vm-1234567890")
        self.test_cluster.configurationEx.dasVmConfig = [
            self._mock_ha_vm_config(mocker, existing_vm)
        ]
        mocker.patch.object(
            VMwareHaVmOverrides, "get_objs_by_name_or_moid", return_value=[existing_vm]
        )
        apply_mock = mocker.patch.object(VMwareHaVmOverrides, "apply_ha_vm_overrides")
        module_args = {
            **self.base_args,
            "vm_overrides": [
                {
                    "virtual_machine": existing_vm._GetMoId(),
                    "restart_priority": "high",
                    "host_isolation_response": "shutdown",
                }
            ],
        }
        result = run_module(module_entry=module_main, module_args=module_args)
        assert result["changed"] is True
        apply_mock.assert_called_once()
        assert apply_mock.call_args[1]["operation"] == "edit"

    @patch(
        "ansible_collections.vmware.vmware.plugins.modules.cluster_ha_vm_overrides.vim.cluster.DasVmConfigInfo",
        new=MockDasVmConfigInfo,
    )
    @patch(
        "ansible_collections.vmware.vmware.plugins.modules.cluster_ha_vm_overrides.vim.cluster.DasVmConfigSpec",
        new=MockDasVmConfigSpec,
    )
    def test_check_mode_skips_apply(self, mocker):
        self.__prepare(mocker)
        apply_mock = mocker.patch.object(VMwareHaVmOverrides, "apply_ha_vm_overrides")
        module_args = {**self.base_args, "_ansible_check_mode": True}
        result = run_module(module_entry=module_main, module_args=module_args)
        assert result["changed"] is True
        apply_mock.assert_not_called()

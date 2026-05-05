from __future__ import absolute_import, division, print_function

__metaclass__ = type

import sys
import pytest
from unittest.mock import Mock, patch

from ansible_collections.vmware.vmware.plugins.modules.cluster_drs_vm_overrides import (
    VMwareDrsVmOverrides,
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


class MockDrsVmConfigInfo(Mock):
    pass


class MockDrsVmConfigSpec(Mock):
    pass


class TestVMwareDrsVmOverrides(ModuleTestCase):

    def _mock_drs_vm_config(self, mocker, vm=None):
        mock_config = mocker.Mock()
        if vm is None:
            vm = create_mock_vsphere_object()
        mock_config.key = vm
        mock_config.behavior = "fullyAutomated"
        mock_config.enabled = True
        return mock_config

    def __prepare(self, mocker):
        mocker.patch.object(
            PyvmomiClient, "connect_to_api", return_value=(mocker.Mock(), mocker.Mock())
        )
        self.test_cluster = MockCluster()
        self.test_cluster.configurationEx.drsConfig = mocker.Mock()
        self.test_cluster.configurationEx.drsConfig.enableVmBehaviorOverrides = True
        self.test_cluster.configurationEx.drsConfig.enabled = True
        self.test_cluster.configurationEx.drsVmConfig = []

        self.base_args = dict(
            datacenter="foo",
            cluster=self.test_cluster.name,
            state="present",
            append=True,
            vm_overrides=[
                {
                    "virtual_machine": "vm-1234567890",
                    "drs_behavior": "fullyAutomated",
                    "enable": True,
                }
            ],
        )

        mocker.patch.object(
            VMwareDrsVmOverrides,
            "get_datacenter_by_name_or_moid",
            return_value=mocker.Mock(),
        )
        mocker.patch.object(
            VMwareDrsVmOverrides,
            "get_cluster_by_name_or_moid",
            return_value=self.test_cluster,
        )

        self.test_vm = create_mock_vsphere_object()
        mocker.patch.object(
            VMwareDrsVmOverrides,
            "get_objs_by_name_or_moid",
            return_value=[self.test_vm],
        )

    @patch(
        "ansible_collections.vmware.vmware.plugins.modules.cluster_drs_vm_overrides.vim.cluster.DrsVmConfigInfo",
        new=MockDrsVmConfigInfo,
    )
    @patch(
        "ansible_collections.vmware.vmware.plugins.modules.cluster_drs_vm_overrides.vim.cluster.DrsVmConfigSpec",
        new=MockDrsVmConfigSpec,
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
        "ansible_collections.vmware.vmware.plugins.modules.cluster_drs_vm_overrides.vim.cluster.DrsVmConfigInfo",
        new=MockDrsVmConfigInfo,
    )
    @patch(
        "ansible_collections.vmware.vmware.plugins.modules.cluster_drs_vm_overrides.vim.cluster.DrsVmConfigSpec",
        new=MockDrsVmConfigSpec,
    )
    def test_present_with_existing_config(self, mocker):
        self.__prepare(mocker)
        existing_vm = create_mock_vsphere_object(name="foo", moid="vm-1234567890")
        self.test_cluster.configurationEx.drsVmConfig = [
            self._mock_drs_vm_config(mocker, existing_vm)
        ]

        module_args = self.base_args
        result = run_module(module_entry=module_main, module_args=module_args)
        # check we updated the existing config
        assert result["changed"] is True

        module_args = {**self.base_args, **{"append": False}}
        result = run_module(module_entry=module_main, module_args=module_args)
        # check we replaced the existing config
        assert result["changed"] is True

        module_args = {
            **self.base_args,
            **{
                "vm_overrides": [
                    {
                        "virtual_machine": existing_vm._GetMoId(),
                        "drs_behavior": "fullyAutomated",
                        "enable": True,
                    }
                ]
            },
        }
        mocker.patch.object(
            VMwareDrsVmOverrides, "get_objs_by_name_or_moid", return_value=[existing_vm]
        )
        result = run_module(module_entry=module_main, module_args=module_args)
        # check we didnt do anything
        assert result["changed"] is False

    @patch(
        "ansible_collections.vmware.vmware.plugins.modules.cluster_drs_vm_overrides.vim.cluster.DrsVmConfigInfo",
        new=MockDrsVmConfigInfo,
    )
    @patch(
        "ansible_collections.vmware.vmware.plugins.modules.cluster_drs_vm_overrides.vim.cluster.DrsVmConfigSpec",
        new=MockDrsVmConfigSpec,
    )
    def test_absent_with_existing_config(self, mocker):
        self.__prepare(mocker)
        existing_vm = create_mock_vsphere_object(name="foo", moid="vm-1234567890")
        self.test_cluster.configurationEx.drsVmConfig = [
            self._mock_drs_vm_config(mocker, existing_vm)
        ]

        module_args = {**self.base_args, **{"state": "absent"}}
        result = run_module(module_entry=module_main, module_args=module_args)
        # check we didn't do anything
        assert result["changed"] is False

        module_args = {
            **self.base_args,
            **{
                "state": "absent",
                "vm_overrides": [{"virtual_machine": existing_vm._GetMoId()}],
            },
        }
        mocker.patch.object(
            VMwareDrsVmOverrides, "get_objs_by_name_or_moid", return_value=[existing_vm]
        )
        result = run_module(module_entry=module_main, module_args=module_args)
        # check we removed the existing config
        assert result["changed"] is True

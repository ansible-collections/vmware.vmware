from __future__ import absolute_import, division, print_function

__metaclass__ = type

import sys
import pytest
from unittest.mock import Mock

from ansible_collections.vmware.vmware.plugins.modules.cluster_drs_vm_overrides_info import (
    VMwareDrsVmOverridesInfo,
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


class TestVMwareDrsVmOverridesInfo(ModuleTestCase):

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
        )

        mocker.patch.object(
            VMwareDrsVmOverridesInfo,
            "get_datacenter_by_name_or_moid",
            return_value=mocker.Mock(),
        )
        mocker.patch.object(
            VMwareDrsVmOverridesInfo,
            "get_cluster_by_name_or_moid",
            return_value=self.test_cluster,
        )

    def test_gather(self, mocker):
        self.__prepare(mocker)
        module_args = self.base_args

        existing_vm = create_mock_vsphere_object(name="foo", moid="vm-1234567890")
        mock_drs_vm_config = mocker.Mock()
        mock_drs_vm_config.key = existing_vm
        mock_drs_vm_config.behavior = "fullyAutomated"
        mock_drs_vm_config.enabled = True
        self.test_cluster.configurationEx.drsVmConfig = [mock_drs_vm_config]

        result = run_module(module_entry=module_main, module_args=module_args)
        assert result["changed"] is False
        assert len(result["vm_overrides"]) == 1

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import sys
import pytest

from ansible_collections.vmware.vmware.plugins.modules.cluster_ha_vm_overrides_info import (
    VMwareHaVmOverridesInfo,
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


class TestVMwareHaVmOverridesInfo(ModuleTestCase):

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
        )

        mocker.patch.object(
            VMwareHaVmOverridesInfo,
            "get_datacenter_by_name_or_moid",
            return_value=mocker.Mock(),
        )
        mocker.patch.object(
            VMwareHaVmOverridesInfo,
            "get_cluster_by_name_or_moid",
            return_value=self.test_cluster,
        )

    def test_gather(self, mocker):
        self.__prepare(mocker)
        module_args = self.base_args

        existing_vm = create_mock_vsphere_object(name="foo", moid="vm-1234567890")
        mock_das_vm_config = mocker.Mock()
        mock_das_vm_config.key = existing_vm
        mock_das_settings = mocker.Mock()
        mock_das_settings.isolationResponse = "shutdown"
        mock_das_settings.restartPriority = "high"
        mock_das_settings.restartPriorityTimeout = -1
        mock_das_settings.vmComponentProtectionSettings = mocker.Mock()
        mock_das_settings.vmComponentProtectionSettings.vmStorageProtectionForAPD = (
            "restartConservative"
        )
        mock_das_settings.vmComponentProtectionSettings.vmTerminateDelayForAPDSec = 180
        mock_das_settings.vmComponentProtectionSettings.vmReactionOnAPDCleared = (
            "reset"
        )
        mock_das_settings.vmComponentProtectionSettings.vmStorageProtectionForPDL = (
            "warning"
        )
        mock_das_settings.vmToolsMonitoringSettings = mocker.Mock()
        mock_das_settings.vmToolsMonitoringSettings.vmMonitoring = "vmAndAppMonitoring"
        mock_das_settings.vmToolsMonitoringSettings.failureInterval = 30
        mock_das_settings.vmToolsMonitoringSettings.minUpTime = 120
        mock_das_settings.vmToolsMonitoringSettings.maxFailures = 3
        mock_das_settings.vmToolsMonitoringSettings.maxFailureWindow = 180
        mock_das_settings.vmToolsMonitoringSettings.clusterSettings = False
        mock_das_vm_config.dasSettings = mock_das_settings
        self.test_cluster.configurationEx.dasVmConfig = [mock_das_vm_config]

        result = run_module(module_entry=module_main, module_args=module_args)
        assert result["changed"] is False
        assert len(result["vm_overrides"]) == 1
        row = result["vm_overrides"][0]
        assert row["vm_moid"] == "vm-1234567890"
        assert row["vm_name"] == "foo"
        assert row["isolation_response"] == "shutdown"
        assert row["restart_priority"] == "high"
        assert row["restart_priority_timeout"] == -1
        assert row["storage_apd_response"]["mode"] == "restartConservative"
        assert row["storage_apd_response"]["delay"] == 180
        assert row["storage_apd_response"]["restart_vms"] is True
        assert row["storage_pdl_response"] == "warning"
        assert row["vm_monitoring"]["mode"] == "vmAndAppMonitoring"
        assert row["vm_monitoring"]["failure_interval"] == 30
        assert row["vm_monitoring"]["minimum_uptime"] == 120
        assert row["vm_monitoring"]["maximum_resets"] == 3
        assert row["vm_monitoring"]["maximum_resets_window"] == 180
        assert row["vm_monitoring"]["use_cluster_settings"] is False

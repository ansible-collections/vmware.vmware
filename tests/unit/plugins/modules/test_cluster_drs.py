from __future__ import absolute_import, division, print_function

__metaclass__ = type

import sys
import pytest

from ansible_collections.vmware.vmware.plugins.modules import cluster_drs
from unittest import mock

from .common.utils import (
    AnsibleExitJson, ModuleTestCase, set_module_args, exit_json, fail_json,
    resource_task_success, resource_task_fail, AnsibleFailJson
)

pytestmark = pytest.mark.skipif(
    sys.version_info < (2, 7), reason="requires python2.7 or higher"
)


class TestClusterDRS(ModuleTestCase):

    def __prepare(self, mocker, success=True):
        init_mock = mocker.patch.object(cluster_drs.PyVmomi, "__init__")
        init_mock.return_value = None

        find_datacenter_by_name = mocker.patch.object(cluster_drs.VMwareCluster, "find_datacenter_by_name")
        find_datacenter_by_name.return_value = {}

        find_cluster_by_name = mocker.patch.object(cluster_drs.VMwareCluster, "find_cluster_by_name")
        cluster = mock.Mock()
        if success:
            cluster.ReconfigureComputeResource_Task.side_effect = resource_task_success
        else:
            cluster.ReconfigureComputeResource_Task.side_effect = resource_task_fail
        find_cluster_by_name.return_value = cluster

        check_ha_config_diff = mocker.patch.object(cluster_drs.VMwareCluster, "check_drs_config_diff")
        check_ha_config_diff.return_value = True

        cluster_drs.VMwareCluster.content = mock.Mock()
        cluster_drs.VMwareCluster.content.rootFolder = []
        cluster_drs.VMwareCluster.params = {
            'slot_based_admission_control': "",
            'failover_host_admission_control': "",
            'reservation_based_admission_control': "",
            'host_isolation_response': "none",
            'advanced_settings': None,
            'apd_response': 'disabled',
            'pdl_response': 'warning',
            'drs_vmotion_rate': 3,
        }

        cluster_drs.VMwareCluster.module = mock.Mock()
        cluster_drs.VMwareCluster.module.check_mode = False
        cluster_drs.VMwareCluster.module.fail_json.side_effect = fail_json
        cluster_drs.VMwareCluster.module.exit_json.side_effect = exit_json

    def test_configure_drs_success(self, mocker):
        self.__prepare(mocker, success=True)

        set_module_args(
            enable=True,
            datacenter="test",
        )

        with pytest.raises(AnsibleExitJson) as c:
            cluster_drs.main()
        assert c.value.args[0]["changed"]

    def test_configure_drs_fail(self, mocker):
        self.__prepare(mocker, success=False)

        set_module_args(
            enable=True,
            datacenter="test",
        )

        with pytest.raises(AnsibleFailJson) as c:
            cluster_drs.main()

        assert "Failed to update cluster" in c.value.args[0]["msg"]

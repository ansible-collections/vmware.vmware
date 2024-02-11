from __future__ import absolute_import, division, print_function

__metaclass__ = type

import sys
import pytest

from ansible_collections.vmware.vmware.plugins.modules import cluster_ha
from unittest import mock

from .common.utils import (
    AnsibleExitJson, ModuleTestCase, set_module_args, exit_json, fail_json,
    resource_task_success, resource_task_fail, AnsibleFailJson
)

pytestmark = pytest.mark.skipif(
    sys.version_info < (2, 7), reason="requires python2.7 or higher"
)


def set_module_args_with_enable_ha():
    set_module_args(
        enable=True,
        datacenter="test",
        ha_host_monitoring="enabled",
        ha_vm_monitoring="vmAndAppMonitoring",
    )


def set_module_args_with_disable_ha():
    set_module_args(
        enable=False,
        datacenter="test",
        ha_host_monitoring="enabled",
        ha_vm_monitoring="vmAndAppMonitoring",
    )


class TestClusterHA(ModuleTestCase):

    def __prepare(self, mocker, success=True):
        init_mock = mocker.patch.object(cluster_ha.PyVmomi, "__init__")
        init_mock.return_value = None

        find_datacenter_by_name = mocker.patch.object(cluster_ha.VMwareCluster, "find_datacenter_by_name")
        find_datacenter_by_name.return_value = {}

        find_cluster_by_name = mocker.patch.object(cluster_ha.VMwareCluster, "find_cluster_by_name")
        cluster = mock.Mock()
        if success:
            cluster.ReconfigureComputeResource_Task.side_effect = resource_task_success
        else:
            cluster.ReconfigureComputeResource_Task.side_effect = resource_task_fail
        find_cluster_by_name.return_value = cluster

        check_ha_config_diff = mocker.patch.object(cluster_ha.VMwareCluster, "check_ha_config_diff")
        check_ha_config_diff.return_value = True

        cluster_ha.VMwareCluster.content = {}
        cluster_ha.VMwareCluster.params = {
            'slot_based_admission_control': "",
            'failover_host_admission_control': "",
            'reservation_based_admission_control': "",
            'host_isolation_response': "none",
            'advanced_settings': None,
            'apd_response': 'disabled',
            'pdl_response': 'warning',
        }

        cluster_ha.VMwareCluster.module = mock.Mock()
        cluster_ha.VMwareCluster.module.check_mode = False
        cluster_ha.VMwareCluster.module.fail_json.side_effect = fail_json
        cluster_ha.VMwareCluster.module.exit_json.side_effect = exit_json

    def test_configure_enable_ha_success(self, mocker):
        self.__prepare(mocker, success=True)
        set_module_args_with_enable_ha()

        with pytest.raises(AnsibleExitJson) as c:
            cluster_ha.main()
        assert c.value.args[0]["changed"]

    def test_configure_enable_ha_fail(self, mocker):
        self.__prepare(mocker, success=False)
        set_module_args_with_enable_ha()

        with pytest.raises(AnsibleFailJson) as c:
            cluster_ha.main()

        assert "Failed to update cluster" in c.value.args[0]["msg"]

    def test_configure_disable_ha_success(self, mocker):
        self.__prepare(mocker, success=True)
        set_module_args_with_disable_ha()

        with pytest.raises(AnsibleExitJson) as c:
            cluster_ha.main()
        assert c.value.args[0]["changed"]

    def test_configure_disable_ha_fail(self, mocker):
        self.__prepare(mocker, success=False)
        set_module_args_with_disable_ha()

        with pytest.raises(AnsibleFailJson) as c:
            cluster_ha.main()

        assert "Failed to update cluster" in c.value.args[0]["msg"]

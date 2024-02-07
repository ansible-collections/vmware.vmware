from __future__ import absolute_import, division, print_function

__metaclass__ = type

import sys
import pytest

from ansible_collections.vmware.vmware.plugins.modules import cluster_ha
from pyVmomi import vim

from .common.utils import (
    AnsibleExitJson, ModuleTestCase, set_module_args,
)

pytestmark = pytest.mark.skipif(
    sys.version_info < (2, 7), reason="requires python2.7 or higher"
)


class TestAffinity(ModuleTestCase):

    def __prepare(self, mocker):
        init_mock = mocker.patch.object(cluster_ha.PyVmomi, "__init__")
        init_mock.return_value = None

        find_datacenter_by_name = mocker.patch.object(cluster_ha.VMwareCluster, "find_datacenter_by_name")
        find_datacenter_by_name.return_value = {}
        find_cluster_by_name = mocker.patch.object(cluster_ha.VMwareCluster, "find_cluster_by_name")
        find_cluster_by_name.return_value = {}
        isolation_response = mocker.patch.object(vim.cluster.DasVmSettings, "IsolationResponse")
        isolation_response.return_value = {'clusterIsolationResponse': ""}

    def test_configure_ha(self, mocker):
        self.__prepare(mocker)
        configure_ha_mock = mocker.patch.object(cluster_ha.VMwareCluster, "configure_ha")
        configure_ha_mock.return_value = True, None

        set_module_args(
            enable=True,
            datacenter="test",
            ha_host_monitoring="enabled",
            ha_vm_monitoring="vmAndAppMonitoring",
            host_isolation_response="powerOff",
        )
        cluster_ha.VMwareCluster.params = {
            'slot_based_admission_control': "",
            'failover_host_admission_control': "",
            'reservation_based_admission_control': ""
        }

        with pytest.raises(AnsibleExitJson) as c:
            cluster_ha.main()

        assert c.value.args[0]["changed"], True

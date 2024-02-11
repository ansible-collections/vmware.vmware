from __future__ import absolute_import, division, print_function

__metaclass__ = type

import sys
import pytest

from ansible_collections.vmware.vmware.plugins.modules import cluster
from unittest import mock

from .common.utils import (
    AnsibleExitJson, ModuleTestCase, set_module_args, exit_json, fail_json,
    resource_task_success, resource_task_fail, AnsibleFailJson, DummyDatacenter
)

pytestmark = pytest.mark.skipif(
    sys.version_info < (2, 7), reason="requires python2.7 or higher"
)


class TestCluster(ModuleTestCase):

    def __prepare(self, mocker):
        init_mock = mocker.patch.object(cluster.PyVmomi, "__init__")
        init_mock.return_value = None

        cluster.VMwareCluster.content = {}
        cluster.VMwareCluster.params = {
            'slot_based_admission_control': "",
            'failover_host_admission_control': "",
            'reservation_based_admission_control': "",
            'host_isolation_response': "none",
            'advanced_settings': None,
            'apd_response': 'disabled',
            'pdl_response': 'warning',
        }

        cluster.VMwareCluster.module = mock.Mock()
        cluster.VMwareCluster.module.check_mode = False
        cluster.VMwareCluster.module.fail_json.side_effect = fail_json
        cluster.VMwareCluster.module.exit_json.side_effect = exit_json

    def prepare_cluster(self, mocker, exist=False, task_success=True):
        find_cluster_by_name = mocker.patch.object(cluster.VMwareCluster, "find_cluster_by_name")
        if exist:
            cluster_by_name = mock.Mock()
            if task_success:
                cluster_by_name.Destroy_Task.side_effect = resource_task_success
            else:
                cluster_by_name.Destroy_Task.side_effect = resource_task_fail
            find_cluster_by_name.return_value = cluster_by_name
        else:
            find_cluster_by_name.return_value = None

    def prepare_datacenter(self, mocker, hostfolder_exist=False):
        if hostfolder_exist:
            datacenter = mock.Mock()
            datacenter.hostFolder = mock.Mock()
            datacenter.hostFolder.CreateClusterEx.return_value = None
        else:
            datacenter = DummyDatacenter()

        find_datacenter_by_name = mocker.patch.object(cluster.VMwareCluster, "find_datacenter_by_name")
        find_datacenter_by_name.return_value = datacenter

    def test_create_success(self, mocker):
        # desired state: present
        # current state: absent
        self.__prepare(mocker)
        self.prepare_cluster(mocker, exist=False)
        self.prepare_datacenter(mocker, hostfolder_exist=True)

        set_module_args(
            state="present",
            datacenter="test",
        )

        with pytest.raises(AnsibleExitJson) as c:
            cluster.main()
        assert c.value.args[0]["changed"]

    def test_create_fail(self, mocker):
        # desired state: present
        # current state: absent
        self.__prepare(mocker)
        self.prepare_cluster(mocker, exist=False)
        self.prepare_datacenter(mocker, hostfolder_exist=False)

        set_module_args(
            state="present",
            datacenter="test",
        )

        with pytest.raises(AnsibleFailJson) as c:
            cluster.main()
        assert "Failed to create cluster" in c.value.args[0]["msg"]

    def test_exit_unchanged(self, mocker):
        # desired state: present
        # current state: present
        self.__prepare(mocker)
        self.prepare_cluster(mocker, exist=True)
        self.prepare_datacenter(mocker, hostfolder_exist=True)

        set_module_args(
            state="present",
            datacenter="test",
        )
        # cluster exist
        find_cluster_by_name = mocker.patch.object(cluster.VMwareCluster, "find_cluster_by_name")
        find_cluster_by_name.return_value = mocker.Mock

        with pytest.raises(AnsibleExitJson) as c:
            cluster.main()
        assert not c.value.args[0]["changed"]

    def test_absent_exists_cluster_success(self, mocker):
        # desired state: absent
        # current state: present
        self.__prepare(mocker)
        self.prepare_cluster(mocker, exist=True, task_success=True)
        self.prepare_datacenter(mocker, hostfolder_exist=True)

        set_module_args(
            state="absent",
            datacenter="test",
        )

        with pytest.raises(AnsibleExitJson) as c:
            cluster.main()
        assert c.value.args[0]["changed"]

    def test_absent_exists_cluster_fail(self, mocker):
        # desired state: absent
        # current state: present
        self.__prepare(mocker)
        self.prepare_cluster(mocker, exist=True, task_success=False)
        self.prepare_datacenter(mocker, hostfolder_exist=True)

        set_module_args(
            state="absent",
            datacenter="test",
        )

        with pytest.raises(AnsibleFailJson) as c:
            cluster.main()
        assert "Failed to destroy cluster" in c.value.args[0]["msg"]

    def test_absent_non_exists_cluster(self, mocker):
        # desired state: absent
        # current state: absent
        self.__prepare(mocker)
        self.prepare_cluster(mocker, exist=False)
        self.prepare_datacenter(mocker, hostfolder_exist=True)

        set_module_args(
            state="absent",
            datacenter="test",
        )

        with pytest.raises(AnsibleExitJson) as c:
            cluster.main()
        assert not c.value.args[0]["changed"]

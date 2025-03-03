from __future__ import absolute_import, division, print_function
__metaclass__ = type

import sys
import pytest

from ansible_collections.vmware.vmware.plugins.modules import cluster

from ...common.utils import (
    AnsibleExitJson, ModuleTestCase, set_module_args,
)

pytestmark = pytest.mark.skipif(
    sys.version_info < (2, 7), reason="requires python2.7 or higher"
)


class TestCluster(ModuleTestCase):

    def __prepare(self, mocker):
        init_mock = mocker.patch.object(cluster.VMwareCluster, "__init__")
        init_mock.return_value = None

        update_state = mocker.patch.object(cluster.VMwareCluster, "update_state")
        update_state.return_value = None

        actual_state_matches_desired_state = mocker.patch.object(cluster.VMwareCluster, "actual_state_matches_desired_state")
        actual_state_matches_desired_state.return_value = False

        get_cluster_outputs = mocker.patch.object(cluster.VMwareCluster, "get_cluster_outputs")
        get_cluster_outputs.return_value = {"name": "test", "moid": "11111"}

    def test_cluster(self, mocker):
        self.__prepare(mocker)

        set_module_args(
            hostname="127.0.0.1",
            username="administrator@local",
            password="123456",
            datacenter="test",
            name="test"
        )

        with pytest.raises(AnsibleExitJson) as c:
            cluster.main()

        assert c.value.args[0]["changed"] is True
        assert c.value.args[0]["cluster"] == {"name": "test", "moid": "11111"}

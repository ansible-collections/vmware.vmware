from __future__ import absolute_import, division, print_function
__metaclass__ = type

import sys
import pytest

from ansible_collections.vmware.vmware.plugins.modules import cluster

from ...common.utils import (
    run_module, ModuleTestCase
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

        module_args = dict(
            datacenter="test",
            name="test"
        )

        result = run_module(module_entry=cluster.main, module_args=module_args)
        assert result["changed"] is True
        assert result["cluster"] == {"name": "test", "moid": "11111"}

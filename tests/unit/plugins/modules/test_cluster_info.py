from __future__ import absolute_import, division, print_function
__metaclass__ = type

import sys
import pytest

from ansible_collections.vmware.vmware.plugins.modules import cluster_info

from .common.utils import (
    AnsibleExitJson, ModuleTestCase, set_module_args, mock_pyvmomi
)
from .common.vmware_object_mocks import MockCluster

pytestmark = pytest.mark.skipif(
    sys.version_info < (2, 7), reason="requires python2.7 or higher"
)


class TestClusterInfo(ModuleTestCase):

    def __prepare(self, mocker):
        mock_pyvmomi(mocker)

        get_clusters = mocker.patch.object(cluster_info.ClusterInfo, "get_clusters")
        get_clusters.return_value = [MockCluster()]

    def test_gather(self, mocker):
        self.__prepare(mocker)

        set_module_args(
            hostname="127.0.0.1",
            username="administrator@local",
            password="123456",
            add_cluster=True,
        )

        with pytest.raises(AnsibleExitJson) as c:
            cluster_info.main()

        assert c.value.args[0]["changed"] is False

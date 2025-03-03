from __future__ import absolute_import, division, print_function
__metaclass__ = type

import sys
import pytest

from ansible_collections.vmware.vmware.plugins.modules.cluster_info import (
    ClusterInfo,
    main as module_main
)
from ansible_collections.vmware.vmware.plugins.module_utils.clients._pyvmomi import (
    PyvmomiClient
)

from ...common.utils import (
    AnsibleExitJson, ModuleTestCase, set_module_args
)
from ...common.vmware_object_mocks import MockCluster

pytestmark = pytest.mark.skipif(
    sys.version_info < (2, 7), reason="requires python2.7 or higher"
)


class TestClusterInfo(ModuleTestCase):

    def __prepare(self, mocker):
        mocker.patch.object(PyvmomiClient, 'connect_to_api', return_value=(mocker.Mock(), mocker.Mock()))
        mocker.patch.object(ClusterInfo, 'get_datacenter_by_name_or_moid')
        mocker.patch.object(ClusterInfo, 'get_cluster_by_name_or_moid', return_value=MockCluster())
        mocker.patch.object(
            ClusterInfo, 'get_all_objs_by_type',
            return_value=[MockCluster(), MockCluster()]
        )

    def test_gather(self, mocker):
        self.__prepare(mocker)

        set_module_args(
            add_cluster=True,
        )

        with pytest.raises(AnsibleExitJson) as c:
            module_main()

        assert c.value.args[0]["changed"] is False

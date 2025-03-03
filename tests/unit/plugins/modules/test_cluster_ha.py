from __future__ import absolute_import, division, print_function
__metaclass__ = type

import sys
import pytest

from ansible_collections.vmware.vmware.plugins.modules.cluster_ha import (
    VmwareCluster,
    main as module_main
)
from ansible_collections.vmware.vmware.plugins.module_utils.clients._pyvmomi import (
    PyvmomiClient
)
from ...common.utils import (
    AnsibleExitJson, ModuleTestCase, set_module_args,
)
from ...common.vmware_object_mocks import (
    MockCluster
)

pytestmark = pytest.mark.skipif(
    sys.version_info < (2, 7), reason="requires python2.7 or higher"
)


class TestClusterHa(ModuleTestCase):

    def __prepare(self, mocker):
        mocker.patch.object(PyvmomiClient, 'connect_to_api', return_value=(mocker.Mock(), mocker.Mock()))
        self.test_cluster = MockCluster()
        self.test_cluster.configurationEx.dasConfig = mocker.Mock()

        mocker.patch.object(VmwareCluster, 'get_datacenter_by_name_or_moid', return_value=mocker.Mock())
        mocker.patch.object(VmwareCluster, 'get_cluster_by_name_or_moid', return_value=self.test_cluster)

    def test_bare_enable(self, mocker):
        self.__prepare(mocker)

        set_module_args(
            hostname="127.0.0.1",
            username="administrator@local",
            password="123456",
            add_cluster=False,
            datacenter="foo",
            cluster=self.test_cluster.name
        )

        ha_config = self.test_cluster.configurationEx.dasConfig
        ha_config.enabled = True
        ha_config.defaultVmSettings.isolationResponse = 'none'
        ha_config.defaultVmSettings.vmComponentProtectionSettings.vmStorageProtectionForPDL = 'warning'
        with pytest.raises(AnsibleExitJson) as c:
            module_main()

        assert c.value.args[0]["changed"] is False

        ha_config.enabled = False
        with pytest.raises(AnsibleExitJson) as c:
            module_main()

        assert c.value.args[0]["changed"] is True

    def test_bare_disable(self, mocker):
        self.__prepare(mocker)

        set_module_args(
            hostname="127.0.0.1",
            username="administrator@local",
            password="123456",
            add_cluster=False,
            datacenter="foo",
            cluster=self.test_cluster.name,
            enable=False
        )

        ha_config = self.test_cluster.configurationEx.dasConfig
        ha_config.enabled = True
        with pytest.raises(AnsibleExitJson) as c:
            module_main()

        assert c.value.args[0]["changed"] is True

        ha_config.enabled = False
        with pytest.raises(AnsibleExitJson) as c:
            module_main()

        assert c.value.args[0]["changed"] is False

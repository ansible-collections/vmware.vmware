from __future__ import absolute_import, division, print_function
__metaclass__ = type

import sys
import pytest

from ansible_collections.vmware.vmware.plugins.modules.esxi_host import (
    VmwareHost,
    main as module_main
)
from ansible_collections.vmware.vmware.plugins.module_utils.clients._pyvmomi import (
    PyvmomiClient
)
from .common.utils import (
    AnsibleExitJson, ModuleTestCase, set_module_args,
)
from .common.vmware_object_mocks import (
    MockEsxiHost
)

pytestmark = pytest.mark.skipif(
    sys.version_info < (2, 7), reason="requires python2.7 or higher"
)


class TestEsxiHost(ModuleTestCase):

    def __prepare(self, mocker):
        mocker.patch.object(PyvmomiClient, 'connect_to_api', return_value=(mocker.Mock(), mocker.Mock()))
        self.test_esxi = MockEsxiHost(name="test")
        self.test_esxi.runtime.inMaintenanceMode = True
        self.mock_cluster = mocker.Mock()

        mocker.patch.object(VmwareHost, 'get_datacenter_by_name_or_moid')
        mocker.patch.object(VmwareHost, 'get_cluster_by_name_or_moid', return_value=self.mock_cluster)

    def test_no_change(self, mocker):
        self.__prepare(mocker)

        self.test_esxi.parent = self.mock_cluster
        mocker.patch.object(VmwareHost, 'get_esxi_host_by_name_or_moid', return_value=self.test_esxi)
        set_module_args(
            hostname="127.0.0.1",
            username="administrator@local",
            password="123456",
            add_cluster=True,
            datacenter='foo',
            esxi_host_name=self.test_esxi.name,
            esxi_username="foo",
            esxi_password="foo"
        )
        with pytest.raises(AnsibleExitJson) as c:
            module_main()

        assert c.value.args[0]["changed"] is False

        mocker.patch.object(VmwareHost, 'get_esxi_host_by_name_or_moid', return_value=None)

        set_module_args(
            hostname="127.0.0.1",
            username="administrator@local",
            password="123456",
            add_cluster=True,
            datacenter='foo',
            esxi_host_name=self.test_esxi.name,
            state='absent'
        )
        with pytest.raises(AnsibleExitJson) as c:
            module_main()

        assert c.value.args[0]["changed"] is False

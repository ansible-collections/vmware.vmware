from __future__ import absolute_import, division, print_function
__metaclass__ = type

import sys
import pytest

from ansible_collections.vmware.vmware.plugins.modules.vm_resource_info import (
    VmwareGuestInfo,
    main as module_main
)
from ansible_collections.vmware.vmware.plugins.module_utils.clients._pyvmomi import (
    PyvmomiClient
)
from ...common.utils import (
    AnsibleExitJson, ModuleTestCase, set_module_args,
)
from ...common.vmware_object_mocks import (
    create_mock_vsphere_object
)

pytestmark = pytest.mark.skipif(
    sys.version_info < (2, 7), reason="requires python2.7 or higher"
)


class TestVmwareVmResourceInfo(ModuleTestCase):

    def __prepare(self, mocker):
        mocker.patch.object(PyvmomiClient, 'connect_to_api', return_value=(mocker.Mock(), mocker.Mock()))
        self.test_vm = create_mock_vsphere_object()

        mocker.patch.object(VmwareGuestInfo, 'get_vms_using_params', return_value=[self.test_vm])
        mocker.patch.object(VmwareGuestInfo, 'get_all_vms', return_value=[self.test_vm])

    def test_get_by_id(self, mocker):
        self.__prepare(mocker)
        set_module_args(
            hostname="127.0.0.1",
            username="administrator@local",
            password="123456",
            add_cluster=False,
            name=self.test_vm.name
        )

        with pytest.raises(AnsibleExitJson) as c:
            module_main()

        assert c.value.args[0]["changed"] is False
        output_vm = c.value.args[0]["vms"][0]
        assert output_vm['moid'] == self.test_vm._GetMoId()
        assert output_vm['name'] == self.test_vm.name
        assert output_vm['esxi_host'] != {}
        assert output_vm['resource_pool'] != {}
        assert output_vm['cpu'] != {}
        assert output_vm['stats']['cpu'] != {}

    def test_get_all(self, mocker):
        self.__prepare(mocker)
        set_module_args(
            hostname="127.0.0.1",
            username="administrator@local",
            password="123456",
            add_cluster=False
        )

        with pytest.raises(AnsibleExitJson) as c:
            module_main()

        assert c.value.args[0]["changed"] is False
        output_vm = c.value.args[0]["vms"][0]
        assert output_vm['moid'] == self.test_vm._GetMoId()
        assert output_vm['name'] == self.test_vm.name
        assert output_vm['esxi_host'] != {}
        assert output_vm['resource_pool'] != {}
        assert output_vm['cpu'] != {}
        assert output_vm['stats']['cpu'] != {}

    def test_get_minimum(self, mocker):
        self.__prepare(mocker)
        set_module_args(
            hostname="127.0.0.1",
            username="administrator@local",
            password="123456",
            add_cluster=False,
            gather_cpu_config=False,
            gather_cpu_stats=False,
            gather_memory_config=False,
            gather_memory_stats=False,
        )

        with pytest.raises(AnsibleExitJson) as c:
            module_main()

        assert c.value.args[0]["changed"] is False
        output_vm = c.value.args[0]["vms"][0]
        assert output_vm['moid'] == self.test_vm._GetMoId()
        assert output_vm['name'] == self.test_vm.name
        assert output_vm['esxi_host'] != {}
        assert output_vm['resource_pool'] != {}
        assert output_vm['cpu'] == {}
        assert output_vm['stats']['cpu'] == {}

from __future__ import absolute_import, division, print_function
__metaclass__ = type

import sys
import pytest

from ansible_collections.vmware.vmware.plugins.modules.deploy_content_library_template import (
    VmwareContentDeployTemplate,
    main as module_main
)
from ansible_collections.vmware.vmware.plugins.module_utils.clients._pyvmomi import (
    PyvmomiClient
)
from ansible_collections.vmware.vmware.plugins.module_utils.clients._rest import (
    VmwareRestClient
)
from .common.utils import (
    AnsibleExitJson, ModuleTestCase, set_module_args,
)
from .common.vmware_object_mocks import (
    MockVmwareObject
)

pytestmark = pytest.mark.skipif(
    sys.version_info < (2, 7), reason="requires python2.7 or higher"
)


class TestDeployContentLibraryTemplate(ModuleTestCase):

    def __prepare(self, mocker):
        mocker.patch.object(PyvmomiClient, 'connect_to_api', return_value=(mocker.Mock(), mocker.Mock()))
        mocker.patch.object(VmwareRestClient, 'connect_to_api', return_value=mocker.Mock())
        self.test_vm = MockVmwareObject(name="test")

        mocker.patch.object(VmwareContentDeployTemplate, 'get_resource_pool_by_name_or_moid', return_value=MockVmwareObject())
        mocker.patch.object(VmwareContentDeployTemplate, 'get_datastore_by_name_or_moid', return_value=MockVmwareObject())
        mocker.patch.object(VmwareContentDeployTemplate, 'get_datacenter_by_name_or_moid', return_value=MockVmwareObject())
        mocker.patch.object(VmwareContentDeployTemplate, 'deploy', return_value=self.test_vm._GetMoId())
        mocker.patch.object(VmwareContentDeployTemplate, 'delete_vm', return_value={})

    def test_present(self, mocker):
        self.__prepare(mocker)
        mocker.patch.object(VmwareContentDeployTemplate, 'get_deployed_vm', return_value=None)
        set_module_args(
            hostname="127.0.0.1",
            username="administrator@local",
            password="123456",
            add_cluster=False,
            vm_name=self.test_vm.name,
            library_item_id='111',
            datastore='foo',
            datacenter='foo',
            resource_pool='foo'
        )

        with pytest.raises(AnsibleExitJson) as c:
            module_main()

        assert c.value.args[0]["changed"] is True
        assert c.value.args[0]["vm_moid"] is self.test_vm._GetMoId()

        mocker.patch.object(VmwareContentDeployTemplate, 'get_deployed_vm', return_value=self.test_vm)
        set_module_args(
            hostname="127.0.0.1",
            username="administrator@local",
            password="123456",
            add_cluster=False,
            vm_name=self.test_vm.name,
            library_item_id='111',
            datastore='foo',
            datacenter='foo',
            resource_pool='foo'
        )

        with pytest.raises(AnsibleExitJson) as c:
            module_main()

        assert c.value.args[0]["changed"] is False
        assert c.value.args[0]["vm_moid"] is self.test_vm._GetMoId()

    def test_destroy(self, mocker):
        self.__prepare(mocker)
        mocker.patch.object(VmwareContentDeployTemplate, 'get_deployed_vm', return_value=self.test_vm)
        set_module_args(
            hostname="127.0.0.1",
            username="administrator@local",
            password="123456",
            add_cluster=False,
            vm_name=self.test_vm.name,
            datacenter='foo',
            state='absent'
        )

        with pytest.raises(AnsibleExitJson) as c:
            module_main()

        assert c.value.args[0]["changed"] is True

        mocker.patch.object(VmwareContentDeployTemplate, 'get_deployed_vm', return_value=None)
        set_module_args(
            hostname="127.0.0.1",
            username="administrator@local",
            password="123456",
            add_cluster=False,
            vm_name=self.test_vm.name,
            datacenter='foo',
            state='absent'
        )

        with pytest.raises(AnsibleExitJson) as c:
            module_main()

        assert c.value.args[0]["changed"] is False

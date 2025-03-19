from __future__ import absolute_import, division, print_function
__metaclass__ = type

import sys
import pytest

from ansible_collections.vmware.vmware.plugins.modules.deploy_folder_template import (
    VmwareFolderTemplate,
    main as module_main
)
from ansible_collections.vmware.vmware.plugins.module_utils.clients._pyvmomi import (
    PyvmomiClient
)
from ansible_collections.vmware.vmware.plugins.module_utils.clients._rest import (
    VmwareRestClient
)
from ...common.utils import (
    AnsibleExitJson, AnsibleFailJson, ModuleTestCase, set_module_args,
)
from ...common.vmware_object_mocks import (
    MockVmwareObject
)

pytestmark = pytest.mark.skipif(
    sys.version_info < (2, 7), reason="requires python2.7 or higher"
)


class TestVmwareFolderTemplate(ModuleTestCase):

    def __prepare(self, mocker):
        mocker.patch.object(PyvmomiClient, 'connect_to_api', return_value=(mocker.Mock(), mocker.Mock()))
        mocker.patch.object(VmwareRestClient, 'connect_to_api', return_value=mocker.Mock())
        self.test_vm = MockVmwareObject(name="test")
        self.test_template = mocker.Mock()
        self.test_template.config.template = True

        mocker.patch.object(VmwareFolderTemplate, 'get_folder_by_absolute_path', return_value=MockVmwareObject())
        mocker.patch.object(VmwareFolderTemplate, 'get_objs_by_name_or_moid', return_value=[self.test_template])
        mocker.patch.object(VmwareFolderTemplate, 'get_resource_pool_by_name_or_moid', return_value=MockVmwareObject())
        mocker.patch.object(VmwareFolderTemplate, 'get_datastore_by_name_or_moid', return_value=MockVmwareObject())
        mocker.patch.object(VmwareFolderTemplate, 'get_datacenter_by_name_or_moid', return_value=MockVmwareObject())
        mocker.patch.object(VmwareFolderTemplate, 'deploy', return_value=self.test_vm)

    def test_present(self, mocker):
        self.__prepare(mocker)
        # test template_name
        mocker.patch.object(VmwareFolderTemplate, 'get_deployed_vm', return_value=None)
        set_module_args(
            hostname="127.0.0.1",
            username="administrator@local",
            password="123456",
            add_cluster=False,
            vm_name=self.test_vm.name,
            template_name="foo",
            datacenter='foo',
        )

        with pytest.raises(AnsibleExitJson) as c:
            module_main()

        assert c.value.args[0]["changed"] is True
        assert c.value.args[0]["vm"]["moid"] is self.test_vm._GetMoId()

        # test template_id
        mocker.patch.object(VmwareFolderTemplate, 'get_deployed_vm', return_value=None)
        set_module_args(
            hostname="127.0.0.1",
            username="administrator@local",
            password="123456",
            add_cluster=False,
            vm_name=self.test_vm.name,
            template_id="foo",
            datacenter='foo',
        )

        with pytest.raises(AnsibleExitJson) as c:
            module_main()

        # test no change
        mocker.patch.object(VmwareFolderTemplate, 'get_deployed_vm', return_value=self.test_vm)
        set_module_args(
            hostname="127.0.0.1",
            username="administrator@local",
            password="123456",
            add_cluster=False,
            vm_name=self.test_vm.name,
            template_name="foo",
            datacenter='foo',
        )

        with pytest.raises(AnsibleExitJson) as c:
            module_main()

        assert c.value.args[0]["changed"] is False
        assert c.value.args[0]["vm"]["moid"] is self.test_vm._GetMoId()

    def test_template_error(self, mocker):
        self.__prepare(mocker)
        mocker.patch.object(VmwareFolderTemplate, 'get_deployed_vm', return_value=None)
        mocker.patch.object(VmwareFolderTemplate, 'get_objs_by_name_or_moid', return_value=None)
        set_module_args(
            hostname="127.0.0.1",
            username="administrator@local",
            password="123456",
            add_cluster=False,
            vm_name=self.test_vm.name,
            template_id="foo",
            datacenter='foo',
        )

        with pytest.raises(AnsibleFailJson) as c:
            module_main()

        assert c.value.args[0]["msg"].startswith('Unable to find template with ID')
        assert c.value.args[0]["failed"] is True

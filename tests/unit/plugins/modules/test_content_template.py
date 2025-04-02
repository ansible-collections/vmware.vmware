from __future__ import absolute_import, division, print_function
__metaclass__ = type

import sys
import pytest

from ansible_collections.vmware.vmware.plugins.modules.content_template import (
    VmwareContentTemplate,
    main as module_main
)
from ansible_collections.vmware.vmware.plugins.module_utils.clients.pyvmomi import PyvmomiClient
from ansible_collections.vmware.vmware.plugins.module_utils._module_pyvmomi_base import ModulePyvmomiBase
from ansible_collections.vmware.vmware.plugins.module_utils.clients.rest import (
    VmwareRestClient
)
from ...common.utils import (
    AnsibleExitJson, ModuleTestCase, set_module_args,
)
from ...common.vmware_object_mocks import (
    create_mock_vsphere_object,
)

pytestmark = pytest.mark.skipif(
    sys.version_info < (2, 7), reason="requires python2.7 or higher"
)


class TestContentTemplate(ModuleTestCase):

    def __prepare(self, mocker):
        mocker.patch.object(PyvmomiClient, 'connect_to_api', return_value=(mocker.Mock(), mocker.Mock()))
        self.mock_rest_client = mocker.Mock()
        mocker.patch.object(VmwareRestClient, 'connect_to_api', return_value=self.mock_rest_client)

        mocker.patch.object(VmwareContentTemplate, 'get_content_library_ids', return_value=[1])
        mocker.patch.object(ModulePyvmomiBase, 'get_vms_using_params', return_value=[create_mock_vsphere_object()])

        self.default_module_args = dict(
            hostname="127.0.0.1",
            username="administrator@local",
            password="123456",
            add_cluster=False,
            template_name='bar',
            library='bizz'
        )

    # def test_gather(self, mocker):
    #     self.__prepare(mocker)

    #     set_module_args(**self.default_module_args)

    #     with pytest.raises(AnsibleExitJson) as c:
    #         content_library_item_info.main()

    def test_absent_no_template(self, mocker):
        self.__prepare(mocker)
        mocker.patch.object(VmwareContentTemplate, 'get_library_item_ids', return_value=[])

        set_module_args(**self.default_module_args, **{'state': 'absent'})

        with pytest.raises(AnsibleExitJson) as c:
            module_main()

        assert c.value.args[0]["changed"] is False
        self.mock_rest_client.content.library.Item.delete.assert_not_called()

    def test_absent_template(self, mocker):
        self.__prepare(mocker)
        mocker.patch.object(VmwareContentTemplate, 'get_library_item_ids', return_value=[1])
        set_module_args(**self.default_module_args, **{'state': 'absent'})

        with pytest.raises(AnsibleExitJson) as c:
            module_main()

        assert c.value.args[0]["changed"] is True
        self.mock_rest_client.content.library.Item.delete.assert_called_once_with(1)

    def test_present_template(self, mocker):
        self.__prepare(mocker)
        mocker.patch.object(VmwareContentTemplate, 'get_library_item_ids', return_value=[1])
        set_module_args(**{
            **self.default_module_args,
            **{'state': 'present', 'vm_name': 'foo', 'add_cluster': True}
        })

        with pytest.raises(AnsibleExitJson) as c:
            module_main()

        assert c.value.args[0]["changed"] is False
        self.mock_rest_client.vcenter.vm_template.LibraryItems.create.assert_not_called()

    def test_present_no_template(self, mocker):
        self.__prepare(mocker)
        mocker.patch.object(VmwareContentTemplate, 'get_library_item_ids', return_value=[])
        mocker.patch.object(VmwareContentTemplate, 'get_host_by_name', return_value=1)
        mocker.patch.object(VmwareContentTemplate, 'get_resource_pool_by_name', return_value=2)
        mocker.patch.object(VmwareContentTemplate, 'get_cluster_by_name', return_value=3)
        mocker.patch.object(VmwareContentTemplate, 'get_folder_by_name', return_value=4)
        set_module_args(**{
            **self.default_module_args,
            **{'state': 'present', 'vm_name': 'foo', 'add_cluster': True}
        })

        with pytest.raises(AnsibleExitJson) as c:
            module_main()

        assert c.value.args[0]["changed"] is True
        self.mock_rest_client.vcenter.vm_template.LibraryItems.create.assert_called_once()

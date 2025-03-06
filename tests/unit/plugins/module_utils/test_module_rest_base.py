from __future__ import absolute_import, division, print_function
__metaclass__ = type

from ansible_collections.vmware.vmware.plugins.module_utils._module_rest_base import ModuleRestBase
from ansible_collections.vmware.vmware.plugins.module_utils.clients._rest import (
    VmwareRestClient
)
from ...common.utils import set_module_args


class TestModuleRestBase():

    def __prepare(self, mocker):
        mocker.patch.object(VmwareRestClient, 'connect_to_api', return_value=mocker.Mock())
        set_module_args()
        module = mocker.Mock()
        module.params = {"hostname": "a", "username": "b", "password": "c"}
        self.base = ModuleRestBase(module=module)

    def test_get_vm_by_name(self, mocker):
        self.__prepare(mocker)
        mocker.patch.object(self.base.api_client.vcenter.VM, 'list', return_value=['vm_id'])
        assert self.base.get_vm_by_name('foo') == 'vm_id'

        mocker.patch.object(self.base.api_client.vcenter.VM, 'list', return_value=[])
        assert self.base.get_vm_by_name('foo') is None

    def test_get_content_library_ids(self, mocker):
        self.__prepare(mocker)
        mocker.patch.object(self.base.library_service, 'list', return_value=['1', '2', '3'])
        assert self.base.get_content_library_ids() == ['1', '2', '3']

        mocker.patch.object(self.base.library_service, 'FindSpec')
        mocker.patch.object(self.base.library_service, 'find', return_value=['1'])

        assert self.base.get_content_library_ids(name='foo') == ['1']

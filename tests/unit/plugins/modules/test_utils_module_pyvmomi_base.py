from __future__ import absolute_import, division, print_function
__metaclass__ = type

from ansible_collections.vmware.vmware.plugins.module_utils._module_pyvmomi_base import ModulePyvmomiBase
from ansible_collections.vmware.vmware.plugins.module_utils.clients._pyvmomi import (
    PyvmomiClient
)
from .common.utils import set_module_args
from .common.vmware_object_mocks import MockCluster


class TestModulePyvmomiBase():

    def __prepare(self, mocker):
        mocker.patch.object(PyvmomiClient, 'connect_to_api', return_value=(mocker.Mock(), mocker.Mock()))
        set_module_args()
        self.base = ModulePyvmomiBase(
            module=mocker.Mock()
        )

    def test_is_vcenter(self, mocker):
        self.__prepare(mocker)
        self.base.content.about.apiType = 'VirtualCenter'
        assert self.base.is_vcenter() is True
        self.base.content.about.apiType = 'HostAgent'
        assert self.base.is_vcenter() is False

    def test_get_objs_by_name_or_moid(self, mocker):
        self.__prepare(mocker)
        mock_view = mocker.Mock()
        mock_view.view = [MockCluster('test1'), MockCluster('test2')]
        mocker.patch.object(
            self.base.content.viewManager , 'CreateContainerView',
            return_value=mock_view
        )
        assert self.base.get_objs_by_name_or_moid('vimtype', 'test1')

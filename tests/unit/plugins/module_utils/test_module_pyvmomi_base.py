from __future__ import absolute_import, division, print_function
__metaclass__ = type

from ansible_collections.vmware.vmware.plugins.module_utils._module_pyvmomi_base import ModulePyvmomiBase
from ansible_collections.vmware.vmware.plugins.module_utils.clients._pyvmomi import (
    PyvmomiClient
)
from .common.utils import set_module_args
from .common.vmware_object_mocks import create_mock_vsphere_object
from pyVmomi import vim


class TestModulePyvmomiBase():

    def __prepare(self, mocker):
        mocker.patch.object(PyvmomiClient, 'connect_to_api', return_value=(mocker.Mock(), mocker.Mock()))
        set_module_args()
        module = mocker.Mock()
        module.params = {"hostname": "a", "username": "b", "password": "c"}
        self.base = ModulePyvmomiBase(module=module)

    def test_is_vcenter(self, mocker):
        self.__prepare(mocker)
        self.base.content.about.apiType = 'VirtualCenter'
        assert self.base.is_vcenter() is True
        self.base.content.about.apiType = 'HostAgent'
        assert self.base.is_vcenter() is False

    def test_get_objs_by_name_or_moid(self, mocker):
        self.__prepare(mocker)
        mock_mor = mocker.Mock()
        mock_mor.obj = create_mock_vsphere_object()
        mock_prop = mocker.Mock()
        mock_prop.name = 'name'
        mock_prop.val = 'test1'
        mock_mor.propSet = [mock_prop]
        mocker.patch.object(self.base, 'get_managed_object_references', return_value=[mock_mor])
        assert self.base.get_objs_by_name_or_moid(vim.VirtualMachine, mock_prop.val)[0]._GetMoId() == mock_mor.obj._moid

        # test slightly different inputs
        assert self.base.get_objs_by_name_or_moid([vim.VirtualMachine], mock_prop.val, return_all=True, search_root_folder=mocker.Mock())[0]._GetMoId() == mock_mor.obj._moid

        # test matching moid instead of name
        assert self.base.get_objs_by_name_or_moid(vim.VirtualMachine, mock_mor.obj._GetMoId())[0]._GetMoId() == mock_mor.obj._moid

        # test no moids found
        mocker.patch.object(self.base, 'get_managed_object_references', return_value=[])
        assert self.base.get_objs_by_name_or_moid(vim.VirtualMachine, mock_prop.val) == []

        # test no matching identifier found
        mock_mor_2 = mocker.Mock()
        mock_mor_2.obj = create_mock_vsphere_object()
        mock_prop_2 = mocker.Mock()
        mock_prop_2.name = 'name'
        mock_prop_2.val = 'test2'
        mock_mor_2.propSet = [mock_prop_2]
        mocker.patch.object(self.base, 'get_managed_object_references', return_value=[mock_mor_2])
        assert self.base.get_objs_by_name_or_moid(vim.VirtualMachine, mock_prop.val) == []



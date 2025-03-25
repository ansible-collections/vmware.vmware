from __future__ import absolute_import, division, print_function
__metaclass__ = type

from ansible_collections.vmware.vmware.plugins.module_utils._module_pyvmomi_base import ModulePyvmomiBase
from ansible_collections.vmware.vmware.plugins.module_utils.clients._pyvmomi import (
    PyvmomiClient
)
from ...common.utils import set_module_args, fail_json, AnsibleFailJson
from ...common.vmware_object_mocks import create_mock_vsphere_object
from pyVmomi import vim
import pytest


class TestModulePyvmomiBase():

    def __prepare(self, mocker):
        mocker.patch.object(PyvmomiClient, 'connect_to_api', return_value=(mocker.Mock(), mocker.Mock()))
        set_module_args()
        module = mocker.Mock()
        module.fail_json = fail_json
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
        assert self.base.get_objs_by_name_or_moid(
            [vim.VirtualMachine], mock_prop.val, return_all=True, search_root_folder=mocker.Mock()
        )[0]._GetMoId() == mock_mor.obj._moid

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

    def test_get_standard_portgroup_by_name_or_moid(self, mocker):
        self.__prepare(mocker)
        # test found object
        mocker.patch.object(self.base, 'get_objs_by_name_or_moid', return_value=[mocker.Mock()])
        assert self.base.get_standard_portgroup_by_name_or_moid('foo')

        # test no object found, no failure
        mocker.patch.object(self.base, 'get_objs_by_name_or_moid', return_value=[])
        assert self.base.get_standard_portgroup_by_name_or_moid('foo') is None

        # test fail on no object found
        mock_fail = mocker.patch.object(self.base.module, 'fail_json')
        mocker.patch.object(self.base, 'get_objs_by_name_or_moid', return_value=[])
        self.base.get_standard_portgroup_by_name_or_moid('foo', fail_on_missing=True)
        mock_fail.assert_called_once()

    def test_get_dvs_portgroup_by_name_or_moid(self, mocker):
        self.__prepare(mocker)
        # test found object
        mocker.patch.object(self.base, 'get_objs_by_name_or_moid', return_value=[mocker.Mock()])
        assert self.base.get_dvs_portgroup_by_name_or_moid('foo')

        # test no object found, no failure
        mocker.patch.object(self.base, 'get_objs_by_name_or_moid', return_value=[])
        assert self.base.get_dvs_portgroup_by_name_or_moid('foo') is None

        # test fail on no object found
        mock_fail = mocker.patch.object(self.base.module, 'fail_json')
        mocker.patch.object(self.base, 'get_objs_by_name_or_moid', return_value=[])
        self.base.get_dvs_portgroup_by_name_or_moid('foo', fail_on_missing=True)
        mock_fail.assert_called_once()

    def test_get_folders_by_name_or_moid(self, mocker):
        self.__prepare(mocker)
        # test found object
        mocker.patch.object(self.base, 'get_objs_by_name_or_moid', return_value=[mocker.Mock()])
        assert len(self.base.get_folders_by_name_or_moid('foo')) == 1

        # test no object found, no failure
        mocker.patch.object(self.base, 'get_objs_by_name_or_moid', return_value=[])
        assert self.base.get_folders_by_name_or_moid('foo') == []

        # test fail on no object found
        mock_fail = mocker.patch.object(self.base.module, 'fail_json')
        mocker.patch.object(self.base, 'get_objs_by_name_or_moid', return_value=[])
        self.base.get_folders_by_name_or_moid('foo', fail_on_missing=True)
        mock_fail.assert_called_once()

    def test_get_datastore_by_name_or_moid(self, mocker):
        self.__prepare(mocker)
        # test found object
        mocker.patch.object(self.base, 'get_objs_by_name_or_moid', return_value=[mocker.Mock()])
        assert self.base.get_datastore_by_name_or_moid('foo')

        # test no object found, no failure
        mocker.patch.object(self.base, 'get_objs_by_name_or_moid', return_value=[])
        assert self.base.get_datastore_by_name_or_moid('foo') is None

        # test fail on no object found
        mock_fail = mocker.patch.object(self.base.module, 'fail_json')
        mocker.patch.object(self.base, 'get_objs_by_name_or_moid', return_value=[])
        self.base.get_datastore_by_name_or_moid('foo', fail_on_missing=True)
        mock_fail.assert_called_once()

    def test_get_datastore_cluster_by_name_or_moid(self, mocker):
        self.__prepare(mocker)
        # test found object
        mocker.patch.object(self.base, 'get_objs_by_name_or_moid', return_value=[mocker.Mock()])
        assert self.base.get_datastore_cluster_by_name_or_moid('foo')

        # test no object found, no failure
        mocker.patch.object(self.base, 'get_objs_by_name_or_moid', return_value=[])
        assert self.base.get_datastore_cluster_by_name_or_moid('foo') is None

        # test fail on no object found
        mock_fail = mocker.patch.object(self.base.module, 'fail_json')
        mocker.patch.object(self.base, 'get_objs_by_name_or_moid', return_value=[])
        self.base.get_datastore_cluster_by_name_or_moid('foo', fail_on_missing=True)
        mock_fail.assert_called_once()

    def test_get_resource_pool_by_name_or_moid(self, mocker):
        self.__prepare(mocker)
        # test found object
        mocker.patch.object(self.base, 'get_objs_by_name_or_moid', return_value=[mocker.Mock()])
        assert self.base.get_resource_pool_by_name_or_moid('foo')

        # test no object found, no failure
        mocker.patch.object(self.base, 'get_objs_by_name_or_moid', return_value=[])
        assert self.base.get_resource_pool_by_name_or_moid('foo') is None

        # test fail on no object found
        mock_fail = mocker.patch.object(self.base.module, 'fail_json')
        mocker.patch.object(self.base, 'get_objs_by_name_or_moid', return_value=[])
        self.base.get_resource_pool_by_name_or_moid('foo', fail_on_missing=True)
        mock_fail.assert_called_once()

    def test_get_datacenter_by_name_or_moid(self, mocker):
        self.__prepare(mocker)
        # test found object
        mocker.patch.object(self.base, 'get_objs_by_name_or_moid', return_value=[mocker.Mock()])
        assert self.base.get_datacenter_by_name_or_moid('foo')

        # test no object found, no failure
        mocker.patch.object(self.base, 'get_objs_by_name_or_moid', return_value=[])
        assert self.base.get_datacenter_by_name_or_moid('foo') is None

        # test fail on no object found
        mock_fail = mocker.patch.object(self.base.module, 'fail_json')
        mocker.patch.object(self.base, 'get_objs_by_name_or_moid', return_value=[])
        self.base.get_datacenter_by_name_or_moid('foo', fail_on_missing=True)
        mock_fail.assert_called_once()

    def test_get_cluster_by_name_or_moid(self, mocker):
        self.__prepare(mocker)
        # test found object
        mocker.patch.object(self.base, 'get_objs_by_name_or_moid', return_value=[mocker.Mock()])
        assert self.base.get_cluster_by_name_or_moid('foo')

        # test no object found, no failure
        mocker.patch.object(self.base, 'get_objs_by_name_or_moid', return_value=[])
        assert self.base.get_cluster_by_name_or_moid('foo') is None

        # test fail on no object found
        mock_fail = mocker.patch.object(self.base.module, 'fail_json')
        mocker.patch.object(self.base, 'get_objs_by_name_or_moid', return_value=[])
        self.base.get_cluster_by_name_or_moid('foo', fail_on_missing=True)
        mock_fail.assert_called_once()

    def test_get_esxi_host_by_name_or_moid(self, mocker):
        self.__prepare(mocker)
        # test found object
        mocker.patch.object(self.base, 'get_objs_by_name_or_moid', return_value=[mocker.Mock()])
        assert self.base.get_esxi_host_by_name_or_moid('foo')

        # test no object found, no failure
        mocker.patch.object(self.base, 'get_objs_by_name_or_moid', return_value=[])
        assert self.base.get_esxi_host_by_name_or_moid('foo') is None

        # test fail on no object found
        mock_fail = mocker.patch.object(self.base.module, 'fail_json')
        mocker.patch.object(self.base, 'get_objs_by_name_or_moid', return_value=[])
        self.base.get_esxi_host_by_name_or_moid('foo', fail_on_missing=True)
        mock_fail.assert_called_once()

    def test_get_datastore_with_max_free_space(self, mocker):
        self.__prepare(mocker)
        ds1, ds2, ds3, ds4, other = mocker.MagicMock(), mocker.MagicMock(), mocker.MagicMock(), mocker.MagicMock(), object()
        ds1.summary.freeSpace = 1
        ds2.summary.freeSpace = 100
        ds3.summary.freeSpace = 10
        ds4.summary.freeSpace = 1000
        ds1.summary.maintenanceMode = 'normal'
        ds1.summary.accessible = True
        ds2.summary.maintenanceMode = 'normal'
        ds2.summary.accessible = True
        ds3.summary.maintenanceMode = 'normal'
        ds3.summary.accessible = True
        ds4.summary.maintenanceMode = 'normal'
        ds4.summary.accessible = False

        mocker.patch.object(self.base, 'get_objs_by_name_or_moid', return_value=[mocker.Mock()])
        assert self.base.get_datastore_with_max_free_space([ds1, ds2, ds3, ds4, other]) == ds2

    def test_get_vms_using_params(self, mocker):
        self.__prepare(mocker)

        mock_get_objs = mocker.patch.object(self.base, 'get_objs_by_name_or_moid', return_value=[mocker.Mock()])
        mock_find_uuid = mocker.patch.object(self.base.si.content.searchIndex, 'FindByUuid', return_value=mocker.Mock())

        # test name param
        self.base.params = {'name': 'foo'}
        assert len(self.base.get_vms_using_params(name_param='name', fail_on_missing=True)) == 1
        assert len(self.base.get_vms_using_params(name_param='fake', fail_on_missing=False)) == 0
        mock_find_uuid.assert_not_called()
        mock_get_objs.assert_called_once()
        mock_get_objs.reset_mock()
        mock_find_uuid.reset_mock()

        self.base.params = {'name': 'foo', 'name_match': 'first'}
        assert len(self.base.get_vms_using_params(name_param='name', fail_on_missing=True)) == 1
        assert len(self.base.get_vms_using_params(name_param='fake', fail_on_missing=False)) == 0
        mock_find_uuid.assert_not_called()
        mock_get_objs.assert_called_once()
        mock_get_objs.reset_mock()
        mock_find_uuid.reset_mock()

        self.base.params = {'name': 'foo', 'name_match': 'last'}
        assert len(self.base.get_vms_using_params(name_param='name', fail_on_missing=True)) == 1
        assert len(self.base.get_vms_using_params(name_param='fake', fail_on_missing=False)) == 0
        mock_find_uuid.assert_not_called()
        mock_get_objs.assert_called_once()
        mock_get_objs.reset_mock()
        mock_find_uuid.reset_mock()

        # test name param
        self.base.params = {'uuid': 'foo'}
        assert len(self.base.get_vms_using_params(uuid_param='uuid', fail_on_missing=True)) == 1
        assert len(self.base.get_vms_using_params(uuid_param='fake', fail_on_missing=False)) == 0
        mock_get_objs.assert_not_called()
        mock_find_uuid.assert_called_once()
        mock_get_objs.reset_mock()
        mock_find_uuid.reset_mock()

        # test moid param
        self.base.params = {'moid': 'foo'}
        assert len(self.base.get_vms_using_params(moid_param='moid', fail_on_missing=True)) == 1
        assert len(self.base.get_vms_using_params(moid_param='fake', fail_on_missing=False)) == 0
        mock_find_uuid.assert_not_called()
        mock_get_objs.assert_called_once()
        mock_get_objs.reset_mock()
        mock_find_uuid.reset_mock()

        # test nothing found errors
        self.base.params = {}
        with pytest.raises(AnsibleFailJson) as e:
            self.base.get_vms_using_params(fail_on_missing=True)
            assert e.msg.startswith("Could not find any supported VM identifier params")

        self.base.params = {'name': 'foo'}
        mocker.patch.object(self.base, 'get_objs_by_name_or_moid', return_value=[])
        with pytest.raises(AnsibleFailJson) as e:
            self.base.get_vms_using_params(fail_on_missing=True)
            assert e.msg.startswith("Unable to find VM")

        self.base.params = {'name': 'foo', 'name_match': 'foo'}
        mocker.patch.object(self.base, 'get_objs_by_name_or_moid', return_value=[mocker.Mock()])
        with pytest.raises(AnsibleFailJson) as e:
            self.base.get_vms_using_params(fail_on_missing=True)
            assert e.msg.startswith("Unrecognized name_match option")

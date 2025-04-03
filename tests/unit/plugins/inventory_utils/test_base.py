from __future__ import absolute_import, division, print_function
__metaclass__ = type

import sys
import pytest

from ansible_collections.vmware.vmware.plugins.module_utils.clients.pyvmomi import PyvmomiClient
from ansible_collections.vmware.vmware.plugins.module_utils.clients.rest import VmwareRestClient
from ansible_collections.vmware.vmware.plugins.inventory_utils._base import (
    VmwareInventoryBase,
    VmwareInventoryHost,
    DISPLAY
)
from ansible.errors import AnsibleError
from ...common.vmware_object_mocks import (
    create_mock_vsphere_object,
)
pytestmark = pytest.mark.skipif(
    sys.version_info < (2, 7), reason="requires python2.7 or higher"
)


def get_option(value):
    if value in ('hostname', 'username', 'password', 'port', 'validate_certs', 'http_proxy_port', 'http_proxy_host'):
        return 'foo'
    return None


class TestInventoryUtilsBase():
    def __prepare(self, mocker):
        mocker.patch.object(PyvmomiClient, 'connect_to_api', return_value=(mocker.Mock(), mocker.Mock()))
        mocker.patch.object(VmwareRestClient, 'connect_to_api', return_value=mocker.Mock())
        mocker.patch.object(VmwareInventoryBase, 'get_option', side_effect=get_option)
        mocker.patch.object(VmwareInventoryBase, '_consume_options')
        self.test_base = VmwareInventoryBase()
        self.test_base.templar = mocker.Mock()

    def test_initialize_pyvmomi_client(self, mocker):
        self.__prepare(mocker)
        mocker.patch.object(self.test_base.templar, 'is_template', return_value=False)
        self.test_base.initialize_pyvmomi_client({})

    def test_initialize_rest_client(self, mocker):
        self.__prepare(mocker)
        mocker.patch.object(self.test_base.templar, 'is_template', return_value=False)
        self.test_base.initialize_rest_client({})

    def test_get_cached_result(self, mocker):
        self.__prepare(mocker)
        mocker.patch.object(self.test_base, 'get_option', return_value=False)
        assert self.test_base.get_cached_result(None, None) == (False, None)
        assert self.test_base.get_cached_result(True, None) == (False, None)

        mocker.patch.object(self.test_base, 'get_option', return_value=True)
        self.test_base._cache = {'foo': 'bar'}
        assert self.test_base.get_cached_result(True, 'bizz') == (False, None)
        assert self.test_base.get_cached_result(True, 'foo') == (True, 'bar')

    def test_update_cached_result(self, mocker):
        self.__prepare(mocker)
        mocker.patch.object(self.test_base, 'get_option', return_value=False)
        assert self.test_base.update_cached_result(None, None, None) is None

        mocker.patch.object(self.test_base, 'get_option', return_value=True)
        self.test_base._cache = {'bizz': 'bar'}
        assert self.test_base.update_cached_result(True, 'bizz', 'test') is None
        self.test_base.update_cached_result(True, 'foo', 'test')
        assert self.test_base._cache['foo'] == 'test'

    def test_host_should_be_filtered_out(self, mocker):
        self.__prepare(mocker)
        test_obj = mocker.Mock()
        mocker.patch.object(self.test_base, 'get_option', return_value=[])
        assert not self.test_base.host_should_be_filtered_out(test_obj)

        mocker.patch.object(self.test_base, 'get_option', return_value=[''])
        mocker.patch.object(self.test_base, '_compose', return_value=True)
        assert self.test_base.host_should_be_filtered_out(test_obj)

        mocker.patch.object(self.test_base, '_compose', return_value=False)
        assert not self.test_base.host_should_be_filtered_out(test_obj)

        test_obj = None
        mocker.patch.object(self.test_base, 'get_option', side_effect=[
            [''],
            True
        ])
        with pytest.raises(AnsibleError):
            self.test_base.host_should_be_filtered_out(test_obj)

    def test_handle_duplicate_host(self, mocker):
        self.__prepare(mocker)
        mocker.patch.object(self.test_base, 'get_option', return_value=True)
        test_obj = mocker.Mock()
        with pytest.raises(AnsibleError):
            self.test_base._handle_duplicate_host({'moid': 'foo'}, test_obj)

        mocker.patch.object(self.test_base, 'get_option', return_value=False)
        mocker.patch.object(DISPLAY, 'warning')
        self.test_base._handle_duplicate_host({'moid': 'foo'}, test_obj)
        DISPLAY.warning.assert_called_once()

    def test_add_host_object_from_vcenter_to_inventory(self, mocker):
        self.__prepare(mocker)
        mocker.patch.object(self.test_base, 'inventory')
        mocker.patch.object(self.test_base, 'set_default_ansible_host_var')
        mocker.patch.object(self.test_base, 'get_option', return_value=True)
        mocker.patch.object(self.test_base, '_set_composite_vars')
        mocker.patch.object(self.test_base, '_add_host_to_composed_groups')
        mocker.patch.object(self.test_base, '_add_host_to_keyed_groups')
        mocker.patch.object(self.test_base, 'add_host_to_groups_based_on_path')
        mocker.patch.object(self.test_base, 'set_host_variables_from_host_properties')
        mocker.patch.object(self.test_base, '_handle_duplicate_host')

        test_host = mocker.Mock()
        hostvars = {}

        # test host filtered
        mocker.patch.object(self.test_base, 'host_should_be_filtered_out', return_value=True)
        self.test_base.add_host_object_from_vcenter_to_inventory(test_host, hostvars)
        self.test_base.inventory.add_host.assert_not_called()
        assert hostvars == {}

        test_host.inventory_hostname = 'foo'
        mocker.patch.object(self.test_base, 'host_should_be_filtered_out', return_value=False)

        # test host added
        self.test_base.add_host_object_from_vcenter_to_inventory(test_host, hostvars)
        self.test_base.inventory.add_host.assert_called_once_with(test_host.inventory_hostname)
        assert hostvars == {'foo': test_host.properties}

        self.test_base.inventory.reset_mock()

        # test duplicate host
        self.test_base.add_host_object_from_vcenter_to_inventory(test_host, hostvars)
        self.test_base.inventory.add_host.assert_not_called()
        self.test_base._handle_duplicate_host.assert_called_once()

    def test_set_default_ansible_host_var(self, mocker):
        self.__prepare(mocker)
        with pytest.raises(NotImplementedError):
            self.test_base.set_default_ansible_host_var(mocker.Mock())


class TestVmwareInventoryHost():
    class TestHost(VmwareInventoryHost):
        def __init__(self):
            super().__init__()
            self._guest_ip = None

        def get_tags(self, rest_client):
            pass

    def __prepare(self, mocker):
        self.test_host = self.TestHost()

    def test_get_properties_from_pyvmomi(self, mocker):
        self.__prepare(mocker)
        self.test_host.object = create_mock_vsphere_object()
        cust_val = mocker.Mock()
        cust_val.key, cust_val.value = "foo", "bar"
        self.test_host.object.customValue = [cust_val]

        pyvmomi_client = mocker.Mock()
        field = mocker.Mock()
        field.name, field.key = "bizz", "foo"
        pyvmomi_client.custom_field_mgr = [field]
        mocker.patch('ansible_collections.vmware.vmware.plugins.inventory_utils._base.vmware_obj_to_json', return_value={})

        properties = self.test_host.get_properties_from_pyvmomi([], pyvmomi_client)
        print(properties)
        assert properties['moid'] == self.test_host.object._GetMoId()
        assert properties['customValue']['bizz'] == "bar"

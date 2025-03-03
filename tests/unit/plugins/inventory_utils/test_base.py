from __future__ import absolute_import, division, print_function
__metaclass__ = type

import sys
import pytest

from ansible_collections.vmware.vmware.plugins.module_utils.clients._pyvmomi import PyvmomiClient
from ansible_collections.vmware.vmware.plugins.module_utils.clients._rest import VmwareRestClient
from ansible_collections.vmware.vmware.plugins.inventory_utils._base import (
    VmwareInventoryBase
)
from ansible.errors import AnsibleError

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
        assert self.test_base.update_cached_result(None, None, None) == None

        mocker.patch.object(self.test_base, 'get_option', return_value=True)
        self.test_base._cache = {'bizz': 'bar'}
        assert self.test_base.update_cached_result(True, 'bizz', 'test') == None
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

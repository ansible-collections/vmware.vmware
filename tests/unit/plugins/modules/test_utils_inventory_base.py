from __future__ import absolute_import, division, print_function
__metaclass__ = type

import sys
import pytest


from ansible_collections.vmware.vmware.plugins.module_utils.clients._pyvmomi import PyvmomiClient
from ansible_collections.vmware.vmware.plugins.module_utils.clients._rest import VmwareRestClient
from ansible_collections.vmware.vmware.plugins.inventory_utils._base import (
    VmwareInventoryBase
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
        mocker.patch.object(VmwareInventoryBase, '__init__', return_value=mocker.Mock())
        self.mock_get_option = mocker.patch.object(VmwareInventoryBase, 'get_option', side_effect=get_option)
        self.test_base = VmwareInventoryBase()

    def test_initialize_pyvmomi_client(self, mocker):
        self.__prepare(mocker)
        self.test_base.initialize_pyvmomi_client({})

    def test_get_credentials_from_options(self, mocker):
        self.__prepare(mocker)
        self.test_base.initialize_rest_client({})

    def test_get_cached_result(self, mocker):
        self.__prepare(mocker)
        assert self.test_base.get_cached_result(None, None) == (False, None)
        assert self.test_base.get_cached_result(True, None) == (False, None)

        self.test_base._cache = {'foo': 'bar'}
        assert self.test_base.get_cached_result(True, 'bizz') == (False, None)
        assert self.test_base.get_cached_result(True, 'foo') == (True, 'bar')

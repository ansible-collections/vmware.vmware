from __future__ import absolute_import, division, print_function
__metaclass__ = type

import sys
import pytest

from ansible_collections.vmware.vmware.plugins.module_utils.clients.pyvmomi import PyvmomiClient
from ansible_collections.vmware.vmware.plugins.lookup.moid_from_path import (
    LookupModule,
)
from ansible.errors import AnsibleError, AnsibleParserError
from ...common.vmware_object_mocks import (
    create_mock_vsphere_object,
)
pytestmark = pytest.mark.skipif(
    sys.version_info < (2, 7), reason="requires python2.7 or higher"
)


def get_option(value):
    if value in ('hostname', 'username', 'password', 'port', 'validate_certs', 'http_proxy_port', 'http_proxy_host'):
        return 'foo'
    if value == 'type':
        return 'all'
    return None


class TestInventoryUtilsBase():
    def __prepare(self, mocker):
        mocker.patch.object(PyvmomiClient, 'connect_to_api', return_value=(mocker.Mock(), mocker.Mock()))
        mocker.patch.object(LookupModule, 'get_option', side_effect=get_option)
        mocker.patch.object(LookupModule, 'set_options')
        self.test_base = LookupModule()
        self.test_base.pyvmomi_client = mocker.Mock()

    def test_initialize_pyvmomi_client(self, mocker):
        self.__prepare(mocker)
        self.test_base.initialize_pyvmomi_client()

    @pytest.mark.parametrize("path", [None, '', '/foo/bar', '/foo/bar/', '/foo/bar/bizz'])
    def test_validate_path_failure(self, mocker, path):
        self.__prepare(mocker)
        with pytest.raises(AnsibleParserError):
            self.test_base._validate_path(path)

    @pytest.mark.parametrize("path", ['/foo/datastore', '/foo/host', '/foo/vm', '/foo/network', '/foo', '/foo/', '/'])
    def test_validate_path_success(self, mocker, path):
        self.__prepare(mocker)
        assert self.test_base._validate_path(path) is None
        assert self.test_base._validate_path(path + '/') is None

    @pytest.mark.parametrize("path", ['/foo', '/'])
    def test_validate_specify_type(self, mocker, path):
        self.__prepare(mocker)
        mocker.patch.object(self.test_base, 'get_option', return_value='host')
        with pytest.raises(AnsibleParserError):
            self.test_base._validate_path(path)

        mocker.patch.object(self.test_base, 'get_option', return_value='folder')
        assert self.test_base._validate_path(path) is None

    def test_get_moids_from_path_none(self, mocker):
        self.__prepare(mocker)
        self.test_base.pyvmomi_client.si.content.searchIndex.FindByInventoryPath.return_value = None
        outputs = set()
        assert self.test_base._get_moids_from_path('', outputs) is None
        assert outputs == set()

        mocker.patch.object(self.test_base, 'get_option', return_value=True)
        with pytest.raises(AnsibleError):
            self.test_base._get_moids_from_path('', outputs)

    def test_get_moids_from_path_slash(self, mocker):
        self.__prepare(mocker)
        self.test_base.pyvmomi_client.si.content.searchIndex.FindByInventoryPath.return_value = mocker.Mock()
        mock_return_view = mocker.Mock()
        mock_return_view.view = [create_mock_vsphere_object(), create_mock_vsphere_object()]
        self.test_base.pyvmomi_client.si.content.viewManager.CreateContainerView.return_value = mock_return_view
        outputs = set()
        assert self.test_base._get_moids_from_path('/', outputs) is None
        assert outputs == set([m._GetMoId() for m in mock_return_view.view])

    def test_get_moids_from_path_no_slash(self, mocker):
        self.__prepare(mocker)
        mock_object = create_mock_vsphere_object()
        self.test_base.pyvmomi_client.si.content.searchIndex.FindByInventoryPath.return_value = mock_object
        outputs = set()
        assert self.test_base._get_moids_from_path('', outputs) is None
        assert outputs == set([mock_object._GetMoId()])

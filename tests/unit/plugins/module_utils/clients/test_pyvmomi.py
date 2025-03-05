from __future__ import absolute_import, division, print_function
__metaclass__ = type

import pytest

from ansible_collections.vmware.vmware.plugins.module_utils.clients._pyvmomi import PyvmomiClient
from ansible_collections.vmware.vmware.plugins.module_utils.clients._errors import (
    ApiAccessError
)

from pyVim import connect
from pyVmomi import vim


class MockContainerView():
    def __init__(self):
        self.view = []


class TestPyvmomiClient():

    def __prepare(self, mocker):
        # non-proxy init mocks
        mocker.patch.object(connect, 'SmartConnect')

        # proxy init mocks
        mocker.patch.object(connect, 'SmartStubAdapter')
        mocker.patch.object(connect, 'VimSessionOrientedStub')
        mocker.patch.object(vim, 'ServiceInstance')

    def __prepare_client(self):
        return PyvmomiClient(
            hostname='a',
            username='a',
            password='a'
        )

    def test_class_init(self, mocker):
        self.__prepare(mocker)
        init_args = {
            'hostname': 'a',
            'username': 'a',
            'password': 'a',
            'port': 443,
            'validate_certs': True,
            'http_proxy_host': 'a',
            'http_proxy_port': 443
        }

        PyvmomiClient(**init_args)

        with pytest.raises(ApiAccessError):
            PyvmomiClient(**{**init_args, **{'hostname': ''}})

        with pytest.raises(ApiAccessError):
            PyvmomiClient(**{**init_args, **{'username': ''}})

        with pytest.raises(ApiAccessError):
            PyvmomiClient(**{**init_args, **{'password': ''}})

    def test_get_all_objs_by_type(self, mocker):
        self.__prepare(mocker)
        client = self.__prepare_client()
        mocked_container_view = mocker.patch.object(client.content.viewManager, 'CreateContainerView')
        mocked_container_view.return_value = MockContainerView()
        mocked_container_view.return_value.view = [
            object(),
            object()
        ]

        objs = client.get_all_objs_by_type(vimtype='blah', folder=object())

        assert len(objs) == 2

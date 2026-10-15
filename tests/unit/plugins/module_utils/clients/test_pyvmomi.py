from __future__ import absolute_import, division, print_function
__metaclass__ = type

import pytest

from ansible_collections.vmware.vmware.plugins.module_utils.clients.pyvmomi import PyvmomiClient
from ansible_collections.vmware.vmware.plugins.module_utils.clients.errors import (
    ApiAccessError
)

from pyVim import connect
from pyVmomi import vim


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
            'proxy_host': 'a',
            'proxy_port': 443
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
        mocked_container_view.return_value = mocker.Mock()
        mocked_container_view.return_value.view = [
            object(),
            object()
        ]

        objs = client.get_all_objs_by_type(vimtype='blah', folder=object())

        assert len(objs) == 2

    def test_get_managed_object_references(self, mocker):
        self.__prepare(mocker)
        client = self.__prepare_client()
        cv = vim.view.ContainerView(moId='1')
        mocker.patch.object(client.content.viewManager, 'CreateContainerView', return_value=cv)
        destroy = mocker.patch.object(vim.view.ContainerView, 'Destroy', return_value=None)
        query = mocker.patch.object(
            client, '_query_paged_managed_object_properties', return_value=[object(), object()]
        )

        objs = client.get_managed_object_references(vimtype=vim.VirtualMachine, folder=object())

        assert len(objs) == 2
        destroy.assert_called_once()
        filter_spec = query.call_args[0][0]
        assert filter_spec.propSet[0].pathSet == ['name']
        assert filter_spec.propSet[0].all is False
        assert filter_spec.reportMissingObjectsInResults is False

    def test_get_managed_object_references_with_explicit_properties(self, mocker):
        self.__prepare(mocker)
        client = self.__prepare_client()
        cv = vim.view.ContainerView(moId='1')
        mocker.patch.object(client.content.viewManager, 'CreateContainerView', return_value=cv)
        mocker.patch.object(vim.view.ContainerView, 'Destroy', return_value=None)
        query = mocker.patch.object(
            client, '_query_paged_managed_object_properties', return_value=[]
        )

        client.get_managed_object_references(
            vimtype=vim.VirtualMachine, properties=['name', 'config.uuid'], folder=object()
        )

        filter_spec = query.call_args[0][0]
        assert filter_spec.propSet[0].pathSet == ['name', 'config.uuid']

    def test_create_vim_object_from_moid(self, mocker):
        self.__prepare(mocker)
        client = self.__prepare_client()
        obj = client.create_vim_object_from_moid(moid='1', vimtype=vim.VirtualMachine)

        assert obj is not None


class TestQueryPagedManagedObjectProperties():
    """
    The property collector truncates large responses. The client has to follow the
    continuation token or results are silently dropped.
    """

    def __prepare_client(self, mocker):
        mocker.patch.object(connect, 'SmartConnect')
        mocker.patch.object(connect, 'SmartStubAdapter')
        mocker.patch.object(connect, 'VimSessionOrientedStub')
        mocker.patch.object(vim, 'ServiceInstance')
        return PyvmomiClient(hostname='a', username='a', password='a')

    def __page(self, mocker, objects, token=None):
        return mocker.Mock(objects=objects, token=token)

    def test_single_page_does_not_continue(self, mocker):
        client = self.__prepare_client(mocker)
        collector = client.content.propertyCollector
        collector.RetrievePropertiesEx.return_value = self.__page(mocker, ['a', 'b'])

        filter_spec = object()
        objs = client._query_paged_managed_object_properties(filter_spec)

        assert objs == ['a', 'b']
        collector.ContinueRetrievePropertiesEx.assert_not_called()
        # the filter spec must be wrapped in a list and paired with retrieve options
        args = collector.RetrievePropertiesEx.call_args[0]
        assert args[0] == [filter_spec]
        assert isinstance(args[1], vim.PropertyCollector.RetrieveOptions)

    def test_follows_token_until_exhausted(self, mocker):
        client = self.__prepare_client(mocker)
        collector = client.content.propertyCollector
        collector.RetrievePropertiesEx.return_value = self.__page(mocker, ['a'], token='token-1')
        collector.ContinueRetrievePropertiesEx.side_effect = [
            self.__page(mocker, ['b'], token='token-2'),
            self.__page(mocker, ['c']),
        ]

        objs = client._query_paged_managed_object_properties(object())

        assert objs == ['a', 'b', 'c']
        assert [call[0][0] for call in collector.ContinueRetrievePropertiesEx.call_args_list] == [
            'token-1', 'token-2'
        ]

    def test_returns_empty_list_when_no_results(self, mocker):
        """
        RetrievePropertiesEx returns None when nothing matched the filter spec.
        """
        client = self.__prepare_client(mocker)
        collector = client.content.propertyCollector
        collector.RetrievePropertiesEx.return_value = None

        objs = client._query_paged_managed_object_properties(object())

        assert objs == []
        collector.ContinueRetrievePropertiesEx.assert_not_called()

    def test_stops_when_continuation_returns_nothing(self, mocker):
        client = self.__prepare_client(mocker)
        collector = client.content.propertyCollector
        collector.RetrievePropertiesEx.return_value = self.__page(mocker, ['a'], token='token-1')
        collector.ContinueRetrievePropertiesEx.return_value = None

        objs = client._query_paged_managed_object_properties(object())

        assert objs == ['a']
        collector.ContinueRetrievePropertiesEx.assert_called_once_with('token-1')

    def test_empty_page_still_returns_empty_list(self, mocker):
        client = self.__prepare_client(mocker)
        collector = client.content.propertyCollector
        collector.RetrievePropertiesEx.return_value = self.__page(mocker, [])

        assert client._query_paged_managed_object_properties(object()) == []

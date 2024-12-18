from __future__ import absolute_import, division, print_function
__metaclass__ = type

from ansible_collections.vmware.vmware.plugins.module_utils.clients._pyvmomi import PyvmomiClient
from pyVim import connect


class MockContainerView():
    def __init__(self):
        self.view = []


class TestPyvmomiClient():

    def __prepare(self, mocker):
        mocked_smart_connect = mocker.patch.object(connect, 'SmartConnect')
        service_instance = mocker.Mock()
        mocked_smart_connect.return_value = service_instance

        content = mocker.Mock()
        content_mock = mocker.patch.object(service_instance, 'RetrieveContent')
        content_mock.return_value = content
        self.client = PyvmomiClient(
            {
                'hostname': 'a',
                'username': 'a',
                'password': 'a',
            }
        )


    def test_get_all_objs_by_type(self, mocker):
        self.__prepare(mocker)
        mocked_container_view = mocker.patch.object(self.client.content.viewManager, 'CreateContainerView')
        mocked_container_view.return_value = MockContainerView()
        mocked_container_view.return_value.view = [
            object(),
            object()
        ]

        objs = self.client.get_all_objs_by_type(vimtype='blah', folder=object())

        assert len(objs) == 2

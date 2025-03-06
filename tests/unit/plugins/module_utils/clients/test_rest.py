from __future__ import absolute_import, division, print_function
__metaclass__ = type

from ansible_collections.vmware.vmware.plugins.module_utils.clients._rest import VmwareRestClient


class TestRestClient():

    def __prepare(self, mocker):
        client_mock = mocker.patch('ansible_collections.vmware.vmware.plugins.module_utils.clients._rest.create_vsphere_client')
        client_mock.return_value = mocker.Mock()
        self.client = VmwareRestClient(
            hostname='a',
            username='a',
            password='a',
        )

    def test_get_tags_by_moid(self, mocker):
        self.__prepare(mocker)
        mocked_tags = mocker.patch.object(self.client.tag_association_service, 'list_attached_tags')
        mocked_tags.return_value = [
            '1',
            '2',
            '3'
        ]
        mocked_tag_getter = mocker.patch.object(self.client.tag_service, 'get')
        mock_tag = mocker.Mock()
        mocked_tag_getter.return_value = mock_tag

        objs = self.client.get_tags_by_vm_moid('id')

        assert len(objs) == 3

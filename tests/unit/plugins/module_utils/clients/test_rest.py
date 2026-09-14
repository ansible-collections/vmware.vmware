from __future__ import absolute_import, division, print_function
__metaclass__ = type

from ansible_collections.vmware.vmware.plugins.module_utils.clients.rest import VmwareRestClient


class TestRestClient():

    def __prepare(self, mocker):
        client_mock = mocker.patch('ansible_collections.vmware.vmware.plugins.module_utils.clients.rest.create_vsphere_client')
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

    def test_get_tags_for_vm_moids_bulk_empty_input(self, mocker):
        self.__prepare(mocker)
        mocked_list = mocker.patch.object(self.client.tag_association_service, 'list_attached_tags_on_objects')

        result = self.client.get_tags_for_vm_moids_bulk([])

        assert result == {}
        mocked_list.assert_not_called()

    def test_get_tags_for_vm_moids_bulk(self, mocker):
        self.__prepare(mocker)

        tag1 = mocker.Mock()
        tag1.id = 'tag-1'
        tag2 = mocker.Mock()
        tag2.id = 'tag-2'
        tag3 = mocker.Mock()
        tag3.id = 'tag-3'

        item1 = mocker.Mock()
        item1.object_id.id = 'vm-1'
        item1.tag_ids = ['tag-1', 'tag-2']
        item2 = mocker.Mock()
        item2.object_id.id = 'vm-2'
        item2.tag_ids = ['tag-1', 'tag-3']

        mocked_list = mocker.patch.object(
            self.client.tag_association_service,
            'list_attached_tags_on_objects',
            return_value=[item1, item2],
        )
        tag_map = {'tag-1': tag1, 'tag-2': tag2, 'tag-3': tag3}
        mocker.patch.object(
            self.client.tag_service,
            'get',
            side_effect=lambda tag_id: tag_map[tag_id],
        )

        result = self.client.get_tags_for_vm_moids_bulk(['vm-1', 'vm-2'])

        mocked_list.assert_called_once()
        assert self.client.tag_service.get.call_count == 3
        assert result['vm-1'] == [tag1, tag2]
        assert result['vm-2'] == [tag1, tag3]

    def test_get_tags_for_vm_moids_bulk_vm_with_no_tags(self, mocker):
        self.__prepare(mocker)

        tag1 = mocker.Mock()
        tag1.id = 'tag-1'

        item1 = mocker.Mock()
        item1.object_id.id = 'vm-1'
        item1.tag_ids = ['tag-1']

        mocker.patch.object(
            self.client.tag_association_service,
            'list_attached_tags_on_objects',
            return_value=[item1],
        )
        mocker.patch.object(self.client.tag_service, 'get', return_value=tag1)

        result = self.client.get_tags_for_vm_moids_bulk(['vm-1', 'vm-2'])

        assert result['vm-1'] == [tag1]
        assert result['vm-2'] == []

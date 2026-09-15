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

    def test_get_tags_for_moids_bulk_empty_moids(self, mocker):
        self.__prepare(mocker)
        result = self.client._get_tags_for_moids_bulk([], 'VirtualMachine')
        assert result == {}
        self.client.tag_association_service.list_attached_tags_on_objects.assert_not_called()

    def test_get_tags_for_moids_bulk_no_tags_on_object(self, mocker):
        self.__prepare(mocker)
        mock_obj_tags = mocker.Mock()
        mock_obj_tags.object_id.id = 'vm-1'
        mock_obj_tags.tag_ids = []
        mocker.patch.object(
            self.client.tag_association_service,
            'list_attached_tags_on_objects',
            return_value=[mock_obj_tags],
        )
        result = self.client._get_tags_for_moids_bulk(['vm-1'], 'VirtualMachine')
        assert result == {'vm-1': []}
        self.client.tag_service.get.assert_not_called()

    def test_get_tags_for_moids_bulk_with_tags(self, mocker):
        self.__prepare(mocker)
        tag_obj = mocker.Mock()
        tag_obj.id = 'tag-1'
        mock_obj_tags = mocker.Mock()
        mock_obj_tags.object_id.id = 'vm-1'
        mock_obj_tags.tag_ids = ['tag-1']
        mocker.patch.object(
            self.client.tag_association_service,
            'list_attached_tags_on_objects',
            return_value=[mock_obj_tags],
        )
        mocker.patch.object(self.client.tag_service, 'get', return_value=tag_obj)

        result = self.client._get_tags_for_moids_bulk(['vm-1'], 'VirtualMachine')

        assert result == {'vm-1': [tag_obj]}
        self.client.tag_service.get.assert_called_once_with('tag-1')

    def test_get_tags_for_moids_bulk_deduplicates_shared_tags(self, mocker):
        self.__prepare(mocker)
        shared_tag = mocker.Mock()
        vm1_tags = mocker.Mock()
        vm1_tags.object_id.id = 'vm-1'
        vm1_tags.tag_ids = ['shared-tag']
        vm2_tags = mocker.Mock()
        vm2_tags.object_id.id = 'vm-2'
        vm2_tags.tag_ids = ['shared-tag']
        mocker.patch.object(
            self.client.tag_association_service,
            'list_attached_tags_on_objects',
            return_value=[vm1_tags, vm2_tags],
        )
        mocker.patch.object(self.client.tag_service, 'get', return_value=shared_tag)

        result = self.client._get_tags_for_moids_bulk(['vm-1', 'vm-2'], 'VirtualMachine')

        assert result['vm-1'] == [shared_tag]
        assert result['vm-2'] == [shared_tag]
        self.client.tag_service.get.assert_called_once()

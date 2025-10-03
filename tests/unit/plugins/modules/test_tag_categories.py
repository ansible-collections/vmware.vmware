from __future__ import absolute_import, division, print_function
__metaclass__ = type

import sys
import pytest
from unittest import mock

from ansible_collections.vmware.vmware.plugins.modules.tag_categories import (
    TagCategoryDiff,
    main as module_main
)
from ansible_collections.vmware.vmware.plugins.module_utils.clients.rest import (
    VmwareRestClient
)
from ...common.utils import (
    run_module, ModuleTestCase
)

pytestmark = pytest.mark.skipif(
    sys.version_info < (2, 7), reason="requires python2.7 or higher"
)


class TestTagCategoryDiff():
    def test_new_tag_category_state_to_module_output(self):
        before = mock.Mock(description='1.2', id='1.3', cardinality='1.4', associable_types=set())
        before.name = '1.1'
        after = {
            'name': '2.1',
            'description': '2.2',
            'cardinality': '2.4'
        }
        td = TagCategoryDiff(remote_def=before, param_def=after)
        assert td.new_tag_category_state_to_module_output() == {
            'id': '1.3',
            'name': '2.1',
            'cardinality': '2.4',
            'description': '2.2',
            'associable_types': []
        }

    def test_is_creation(self):
        td = TagCategoryDiff(remote_def=None, param_def=None)
        assert td.is_creation() is False
        td = TagCategoryDiff(remote_def=mock.Mock(), param_def={'1': 1})
        assert td.is_creation() is False
        td = TagCategoryDiff(remote_def=mock.Mock(), param_def={})
        assert td.is_creation() is False
        td = TagCategoryDiff(remote_def=None, param_def={'1': 1})
        assert td.is_creation() is True

    def test_is_removal(self):
        td = TagCategoryDiff(remote_def=None, param_def=None)
        assert td.is_removal() is False
        td = TagCategoryDiff(remote_def=mock.Mock(), param_def={'1': 1})
        assert td.is_removal() is False
        td = TagCategoryDiff(remote_def=mock.Mock(), param_def={})
        assert td.is_removal() is True
        td = TagCategoryDiff(remote_def=None, param_def={'1': 1})
        assert td.is_removal() is False

    def test_is_update(self):
        td = TagCategoryDiff(remote_def=None, param_def=None)
        assert td.is_update() is False
        td = TagCategoryDiff(remote_def=mock.Mock(), param_def={'1': 1})
        assert td.is_update() is False
        td = TagCategoryDiff(remote_def=mock.Mock(description='1.2'), param_def={'description': '1.3'})
        assert td.is_update() is True
        mock_tag = mock.Mock()
        mock_tag.name = '1.1'
        td = TagCategoryDiff(remote_def=mock_tag, param_def={'name': '1.2'})
        assert td.is_update() is True
        mock_tag.description = '1.2'
        td = TagCategoryDiff(remote_def=mock_tag, param_def={'description': '1.2', 'name': '1.1'})
        assert td.is_update() is False
        td = TagCategoryDiff(remote_def=None, param_def={'1': 1})
        assert td.is_update() is False


class TestVmwareTagCategoryModule(ModuleTestCase):

    def get_category_side_effect(self, *args, **kwargs):
        try:
            return self.mock_remote_categories[int(args[0]) - 1]
        except IndexError:
            return None

    def __prepare(self, mocker):
        self.rest_client = mocker.Mock()
        self.mock_tag_category_service = mocker.Mock()
        mocker.patch.object(VmwareRestClient, 'connect_to_api', return_value=self.rest_client)
        self.rest_client.tagging.Category = self.mock_tag_category_service

        self.mock_remote_categories = [
            mock.Mock(description='test1', id='1', associable_types=set(), cardinality='SINGLE'),
            mock.Mock(description='test2', id='2', associable_types=set(), cardinality='SINGLE'),
            mock.Mock(description='test3', id='3', associable_types=set(), cardinality='SINGLE')
        ]

        for mock_item in self.mock_remote_categories:
            mock_item.name = f'test{mock_item.id}'

        self.mock_tag_category_service.list.return_value = [m.id for m in self.mock_remote_categories]
        self.mock_tag_category_service.get.side_effect = self.get_category_side_effect

    def test_present_no_change(self, mocker):
        self.__prepare(mocker)
        module_args = dict(
            tag_categories=[
                {
                    'name': 'test1',
                    'description': 'test1'
                },
                {
                    'id': '2'
                },
                {
                    'name': 'test3'
                }
            ]
        )

        result = run_module(module_entry=module_main, module_args=module_args)
        assert result["created_categories"] == []
        assert result['changed'] is False

    def test_present_change(self, mocker):
        self.__prepare(mocker)
        module_args = dict(
            tag_categories=[
                {
                    'name': 'testfoo',
                    'id': '1'
                }
            ]
        )

        result = run_module(module_entry=module_main, module_args=module_args)
        assert len(result["updated_categories"]) == 1
        assert result['changed'] is True

    def test_absent_change(self, mocker):
        self.__prepare(mocker)
        module_args = dict(
            state='absent',
            tag_categories=[
                {
                    'name': 'test1',
                    'id': '1'
                }
            ]
        )

        result = run_module(module_entry=module_main, module_args=module_args)
        assert len(result["removed_categories"]) == 1
        assert result['changed'] is True

    def test_absent_no_change(self, mocker):
        self.__prepare(mocker)
        module_args = dict(
            state='absent',
            tag_categories=[
                {
                    'name': 'test4',
                    'id': '4'
                }
            ]
        )

        result = run_module(module_entry=module_main, module_args=module_args)
        assert result["removed_categories"] == []
        assert result['changed'] is False

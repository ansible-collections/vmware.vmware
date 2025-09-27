from __future__ import absolute_import, division, print_function
__metaclass__ = type

import sys
import pytest
from unittest import mock

from ansible_collections.vmware.vmware.plugins.modules.tag_categories import (
    TagCategoryChange,
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


class TestTagCategoryChange():
    def test_to_module_output(self):
        tc = TagCategoryChange(remote_def=None, param_def=None)
        assert tc.to_module_output() == {
            'before': {},
            'after': {}
        }

        remote_def = mock.Mock(description='1.2', id='1.3', associable_types={'1.4'}, cardinality='1.5')
        remote_def.name = '1.1'
        param_def = {
            'name': '2.1',
            'description': '2.2',
            'associable_types': ['2.4'],
            'cardinality': '2.5'
        }
        tc = TagCategoryChange(remote_def=remote_def, param_def=param_def)
        output = tc.to_module_output()
        assert output['before']['name'] == '1.1'
        assert output['after']['name'] == '2.1'
        assert output['before']['description'] == '1.2'
        assert output['after']['description'] == '2.2'
        assert output['before']['id'] == '1.3'
        assert output['after']['id'] == '1.3'
        assert set(output['before']['associable_types']) == {'1.4'}
        assert set(output['after']['associable_types']) == {'1.4', '2.4'}
        assert output['before']['cardinality'] == '1.5'
        assert output['after']['cardinality'] == '2.5'

        param_def['id'] = '2.3'
        tc = TagCategoryChange(remote_def=remote_def, param_def=param_def)
        output = tc.to_module_output()
        assert output['before']['name'] == '1.1'
        assert output['after']['name'] == '2.1'
        assert output['before']['description'] == '1.2'
        assert output['after']['description'] == '2.2'
        assert output['before']['id'] == '1.3'
        assert output['after']['id'] == '2.3'
        assert set(output['before']['associable_types']) == {'1.4'}
        assert set(output['after']['associable_types']) == {'1.4', '2.4'}
        assert output['before']['cardinality'] == '1.5'
        assert output['after']['cardinality'] == '2.5'


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
        assert result["category_changes"] == []
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
        assert len(result["category_changes"]) == 1
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
        assert len(result["category_changes"]) == 1
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
        assert result["category_changes"] == []
        assert result['changed'] is False

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import sys
import pytest
from unittest import mock

from ansible_collections.vmware.vmware.plugins.module_utils.clients.rest import (
    VmwareRestClient,
)
from ansible_collections.vmware.vmware.plugins.module_utils.clients.pyvmomi import (
    PyvmomiClient,
)
from ansible_collections.vmware.vmware.plugins.modules.tag_associations import (
    main as module_main,
)
from ...common.utils import run_module, ModuleTestCase
from ...common.vmware_object_mocks import create_mock_vsphere_object

pytestmark = pytest.mark.skipif(
    sys.version_info < (2, 7), reason="requires python2.7 or higher"
)


class TestVmwareTagAssociationsModule(ModuleTestCase):

    def get_category_side_effect(self, *args, **kwargs):
        try:
            return self.mock_remote_categories[int(args[0]) - 1]
        except IndexError:
            return None

    def get_tag_side_effect(self, *args, **kwargs):
        try:
            return self.mock_remote_tags[int(args[0]) - 1]
        except IndexError:
            return None

    def list_tags_for_category_side_effect(self, *args, **kwargs):
        try:
            return [
                tag.id for tag in self.mock_remote_categories[int(args[0]) - 1].tags
            ]
        except IndexError:
            return None

    def __prepare(self, mocker):
        self.mock_vm = create_mock_vsphere_object()

        self.rest_client = mocker.Mock()
        self.mock_tag_category_service = mocker.Mock()
        self.mock_tag_service = mocker.Mock()
        self.mock_tag_association_service = mocker.Mock()
        mocker.patch.object(
            VmwareRestClient, "connect_to_api", return_value=self.rest_client
        )
        self.rest_client.tagging.Tag = self.mock_tag_category_service
        self.rest_client.tagging.Category = self.mock_tag_category_service
        self.rest_client.tagging.TagAssociation = self.mock_tag_association_service

        self.pyvmomi_client = mocker.Mock()
        mocker.patch.object(
            PyvmomiClient,
            "connect_to_api",
            return_value=(self.pyvmomi_client, self.pyvmomi_client),
        )

        self.mock_dynamic_id = mocker.Mock()
        mocker.patch(
            "ansible_collections.vmware.vmware.plugins.modules.tag_associations.DynamicID",
            return_value=self.mock_dynamic_id,
        )
        mocker.patch(
            "ansible_collections.vmware.vmware.plugins.modules.tag_associations.vim"
        )
        mocker.patch(
            "ansible_collections.vmware.vmware.plugins.modules.tag_associations.ModulePyvmomiBase.get_objs_by_name_or_moid",
            return_value=[self.mock_vm],
        )

        self.mock_remote_tags = [
            mock.Mock(description="test", id="1", category_id="1"),
            mock.Mock(description="test", id="2", category_id="2"),
            mock.Mock(description="test", id="3", category_id="3"),
        ]
        self.mock_remote_categories = [
            mock.Mock(description="test", id="1", tags=[self.mock_remote_tags[0]]),
            mock.Mock(description="test", id="2", tags=[self.mock_remote_tags[1]]),
            mock.Mock(description="test", id="3", tags=[self.mock_remote_tags[2]]),
        ]

        for mock_item in self.mock_remote_tags + self.mock_remote_categories:
            mock_item.name = f"test{mock_item.id}"

        self.mock_tag_category_service.list.return_value = [
            m.id for m in self.mock_remote_categories
        ]
        self.mock_tag_category_service.get.side_effect = self.get_category_side_effect
        self.mock_tag_service.list.return_value = [m.id for m in self.mock_remote_tags]
        self.mock_tag_service.get.side_effect = self.get_tag_side_effect
        self.mock_tag_category_service.list_tags_for_category.side_effect = (
            self.list_tags_for_category_side_effect
        )

        self.mock_tag_association_service.list_attached_tags.return_value = []
        self.mock_tag_association_service.list_attachable_tags.return_value = [
            m.id for m in self.mock_remote_tags
        ]

    def test_present_change(self, mocker):
        self.__prepare(mocker)
        module_args = dict(
            object_moid="vm-1234567890",
            object_type="VirtualMachine",
            state="present",
            remove_extra_tags=True,
            validate_tags_before_attaching=True,
            tags=[
                {"name": "test1", "category_name": "test1"},
                {"id": "2", "category_id": "2"},
                {"name": "test3", "category_id": "3"},
            ],
        )

        result = run_module(module_entry=module_main, module_args=module_args)
        assert result["added_tags"] == ["1", "2", "3"]
        assert result["removed_tags"] == []
        assert result["changed"] is True

    def test_present_no_change(self, mocker):
        self.__prepare(mocker)
        module_args = dict(
            object_name="test-vm",
            object_type="VirtualMachine",
            state="present",
            remove_extra_tags=False,
            validate_tags_before_attaching=False,
            tags=[{"id": "2", "category_id": "2"}],
        )

        self.mock_tag_association_service.list_attached_tags.return_value = [
            self.mock_remote_tags[1].id
        ]
        result = run_module(module_entry=module_main, module_args=module_args)
        assert result["added_tags"] == []
        assert result["removed_tags"] == []
        assert result["changed"] is False

    def test_absent_remove_extra_tags(self, mocker):
        self.__prepare(mocker)
        module_args = dict(
            object_name="test-vm",
            object_type="VirtualMachine",
            state="absent",
            remove_extra_tags=True,
            tags=[{"id": "2", "category_id": "2"}],
        )

        self.mock_tag_association_service.list_attached_tags.return_value = [
            self.mock_remote_tags[0].id
        ]
        result = run_module(module_entry=module_main, module_args=module_args)
        assert result["added_tags"] == []
        assert result["removed_tags"] == ["1"]
        assert result["changed"] is True

    def test_absent_no_change(self, mocker):
        self.__prepare(mocker)
        module_args = dict(
            object_name="test-vm",
            object_type="VirtualMachine",
            state="absent",
            remove_extra_tags=False,
            tags=[{"id": "2", "category_id": "2"}],
        )
        result = run_module(module_entry=module_main, module_args=module_args)
        assert result["added_tags"] == []
        assert result["removed_tags"] == []
        assert result["changed"] is False

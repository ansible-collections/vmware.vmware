from __future__ import absolute_import, division, print_function
__metaclass__ = type

import sys
import pytest

from pyVmomi import vim

from ansible_collections.vmware.vmware.plugins.modules.vm_custom_attributes import (
    VmCustomAttributesModule,
    main as module_main
)
from ansible_collections.vmware.vmware.plugins.module_utils.clients.pyvmomi import (
    PyvmomiClient
)
from ...common.utils import (
    run_module, ModuleTestCase
)
from ...common.vmware_object_mocks import (
    create_mock_vsphere_object,
)

pytestmark = pytest.mark.skipif(
    sys.version_info < (2, 7), reason="requires python2.7 or higher"
)


class TestVmCustomAttributes(ModuleTestCase):

    FIELD_KEY = 1
    FIELD_NAME = "ExistingAttr"

    def _create_field_def(self, mocker, name, key, mo_type=None):
        field_def = mocker.Mock()
        field_def.key = key
        field_def.name = name
        field_def.managedObjectType = mo_type or vim.VirtualMachine
        return field_def

    def _create_custom_value(self, mocker, key, value):
        cv = mocker.Mock()
        cv.key = key
        cv.value = value
        return cv

    def __prepare(self, mocker, field_defs=None, custom_values=None):
        mock_content = mocker.Mock()
        mock_content.customFieldsManager = mocker.Mock()
        mock_content.customFieldsManager.field = field_defs or []
        mock_content.customFieldsManager.SetField = mocker.Mock()
        mock_content.customFieldsManager.AddFieldDefinition = mocker.Mock()

        mocker.patch.object(
            PyvmomiClient, 'connect_to_api',
            return_value=(mocker.Mock(), mock_content)
        )

        self.vm_mock = create_mock_vsphere_object()
        self.vm_mock.customValue = custom_values or []

        mocker.patch.object(
            VmCustomAttributesModule, 'get_vms_using_params',
            return_value=([self.vm_mock])
        )

    def test_add_attribute(self, mocker):
        self.__prepare(mocker)

        module_args = dict(
            name="vm1",
            state="present",
            attributes={"TestAttr": "TestValue"},
        )

        result = run_module(module_entry=module_main, module_args=module_args)

        assert result["changed"] is True
        assert result["custom_attributes"] == {"TestAttr": "TestValue"}

    def test_add_attribute_idempotent(self, mocker):
        field_defs = [
            self._create_field_def(mocker, self.FIELD_NAME, self.FIELD_KEY),
        ]
        custom_values = [
            self._create_custom_value(mocker, self.FIELD_KEY, "MyValue"),
        ]
        self.__prepare(mocker, field_defs=field_defs, custom_values=custom_values)

        module_args = dict(
            name="vm1",
            state="present",
            attributes={self.FIELD_NAME: "MyValue"},
        )

        result = run_module(module_entry=module_main, module_args=module_args)

        assert result["changed"] is False
        assert result["custom_attributes"] == {self.FIELD_NAME: "MyValue"}

    def test_add_multiple_attributes(self, mocker):
        self.__prepare(mocker)

        module_args = dict(
            name="vm1",
            state="present",
            attributes={"AttrOne": "ValueOne", "AttrTwo": "ValueTwo"},
        )

        result = run_module(module_entry=module_main, module_args=module_args)

        assert result["changed"] is True
        assert result["custom_attributes"] == {
            "AttrOne": "ValueOne", "AttrTwo": "ValueTwo"
        }

    def test_update_attribute(self, mocker):
        field_defs = [
            self._create_field_def(mocker, self.FIELD_NAME, self.FIELD_KEY),
        ]
        custom_values = [
            self._create_custom_value(mocker, self.FIELD_KEY, "OldValue"),
        ]
        self.__prepare(mocker, field_defs=field_defs, custom_values=custom_values)

        module_args = dict(
            name="vm1",
            state="present",
            attributes={self.FIELD_NAME: "NewValue"},
        )

        result = run_module(module_entry=module_main, module_args=module_args)

        assert result["changed"] is True
        assert result["custom_attributes"] == {self.FIELD_NAME: "NewValue"}

    def test_update_attribute_idempotent(self, mocker):
        field_defs = [
            self._create_field_def(mocker, self.FIELD_NAME, self.FIELD_KEY),
        ]
        custom_values = [
            self._create_custom_value(mocker, self.FIELD_KEY, "StableValue"),
        ]
        self.__prepare(mocker, field_defs=field_defs, custom_values=custom_values)

        module_args = dict(
            name="vm1",
            state="present",
            attributes={self.FIELD_NAME: "StableValue"},
        )

        result = run_module(module_entry=module_main, module_args=module_args)

        assert result["changed"] is False
        assert result["custom_attributes"] == {self.FIELD_NAME: "StableValue"}

    def test_remove_attribute(self, mocker):
        field_defs = [
            self._create_field_def(mocker, self.FIELD_NAME, self.FIELD_KEY),
        ]
        custom_values = [
            self._create_custom_value(mocker, self.FIELD_KEY, "WillBeRemoved"),
        ]
        self.__prepare(mocker, field_defs=field_defs, custom_values=custom_values)

        module_args = dict(
            name="vm1",
            state="absent",
            attributes={self.FIELD_NAME: ""},
        )

        result = run_module(module_entry=module_main, module_args=module_args)

        assert result["changed"] is True
        assert result["custom_attributes"] == {self.FIELD_NAME: ""}

    def test_remove_attribute_idempotent(self, mocker):
        field_defs = [
            self._create_field_def(mocker, self.FIELD_NAME, self.FIELD_KEY),
        ]
        custom_values = [
            self._create_custom_value(mocker, self.FIELD_KEY, ""),
        ]
        self.__prepare(mocker, field_defs=field_defs, custom_values=custom_values)

        module_args = dict(
            name="vm1",
            state="absent",
            attributes={self.FIELD_NAME: ""},
        )

        result = run_module(module_entry=module_main, module_args=module_args)

        assert result["changed"] is False
        assert result["custom_attributes"] == {self.FIELD_NAME: ""}

    def test_add_attribute_with_int_value(self, mocker):
        self.__prepare(mocker)

        module_args = dict(
            name="vm1",
            state="present",
            attributes={"IntAttr": 42},
        )

        result = run_module(module_entry=module_main, module_args=module_args)

        assert result["changed"] is True
        assert result["custom_attributes"] == {"IntAttr": "42"}

    def test_add_attribute_with_bool_value(self, mocker):
        self.__prepare(mocker)

        module_args = dict(
            name="vm1",
            state="present",
            attributes={"BoolAttr": True},
        )

        result = run_module(module_entry=module_main, module_args=module_args)

        assert result["changed"] is True
        assert result["custom_attributes"] == {"BoolAttr": "True"}

    def test_int_value_idempotent(self, mocker):
        field_defs = [
            self._create_field_def(mocker, "IntAttr", self.FIELD_KEY),
        ]
        custom_values = [
            self._create_custom_value(mocker, self.FIELD_KEY, "42"),
        ]
        self.__prepare(mocker, field_defs=field_defs, custom_values=custom_values)

        module_args = dict(
            name="vm1",
            state="present",
            attributes={"IntAttr": 42},
        )

        result = run_module(module_entry=module_main, module_args=module_args)

        assert result["changed"] is False
        assert result["custom_attributes"] == {"IntAttr": "42"}

    def test_check_mode_add(self, mocker):
        self.__prepare(mocker)

        module_args = dict(
            name="vm1",
            state="present",
            attributes={"TestAttr": "TestValue"},
            _ansible_check_mode=True,
        )

        result = run_module(module_entry=module_main, module_args=module_args)

        assert result["changed"] is True
        assert "diff" in result

    def test_check_mode_remove(self, mocker):
        field_defs = [
            self._create_field_def(mocker, self.FIELD_NAME, self.FIELD_KEY),
        ]
        custom_values = [
            self._create_custom_value(mocker, self.FIELD_KEY, "MyValue"),
        ]
        self.__prepare(mocker, field_defs=field_defs, custom_values=custom_values)

        module_args = dict(
            name="vm1",
            state="absent",
            attributes={self.FIELD_NAME: ""},
            _ansible_check_mode=True,
        )

        result = run_module(module_entry=module_main, module_args=module_args)

        assert result["changed"] is True
        assert "diff" in result

    def test_vm_not_found(self, mocker):
        mock_content = mocker.Mock()
        mock_content.customFieldsManager = mocker.Mock()
        mock_content.customFieldsManager.field = []

        mocker.patch.object(
            PyvmomiClient, 'connect_to_api',
            return_value=(mocker.Mock(), mock_content)
        )

        # Mock at the search level so the real get_vms_using_params runs
        # and calls fail_json when no VMs are found
        mocker.patch.object(
            VmCustomAttributesModule, 'get_objs_by_name_or_moid',
            return_value=[]
        )

        module_args = dict(
            name="nonexistent-vm",
            state="present",
            attributes={"TestAttr": "TestValue"},
        )

        result = run_module(module_entry=module_main, module_args=module_args, expect_success=False)

        assert result["failed"] is True
        assert "nonexistent-vm" in result["msg"]

    def test_ignores_non_vm_field_defs(self, mocker):
        field_defs = [
            self._create_field_def(mocker, "HostAttr", 10, mo_type=vim.HostSystem),
            self._create_field_def(mocker, "VmAttr", 20, mo_type=vim.VirtualMachine),
        ]
        custom_values = [
            self._create_custom_value(mocker, 20, "VmValue"),
        ]
        self.__prepare(mocker, field_defs=field_defs, custom_values=custom_values)

        module_args = dict(
            name="vm1",
            state="present",
            attributes={"HostAttr": "NewValue", "VmAttr": "VmValue"},
        )

        result = run_module(module_entry=module_main, module_args=module_args)

        assert result["changed"] is True
        assert "HostAttr" in result["custom_attributes"]
        assert result["custom_attributes"]["VmAttr"] == "VmValue"

    def test_handles_none_managed_object_type(self, mocker):
        field_defs = [
            self._create_field_def(mocker, "GlobalAttr", 1, mo_type=None),
        ]
        custom_values = [
            self._create_custom_value(mocker, 1, "GlobalValue"),
        ]
        self.__prepare(mocker, field_defs=field_defs, custom_values=custom_values)

        module_args = dict(
            name="vm1",
            state="present",
            attributes={"GlobalAttr": "GlobalValue"},
        )

        result = run_module(module_entry=module_main, module_args=module_args)

        assert result["changed"] is False
        assert result["custom_attributes"] == {"GlobalAttr": "GlobalValue"}

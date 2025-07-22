from __future__ import absolute_import, division, print_function
__metaclass__ = type

import sys
import pytest

from ansible_collections.vmware.vmware.plugins.modules.folder_template_from_vm import (
    VmwareFolderTemplate,
    main as module_main
)
from ansible_collections.vmware.vmware.plugins.module_utils.clients.pyvmomi import (
    PyvmomiClient
)
from ...common.utils import (
    run_module, ModuleTestCase
)
from ...common.vmware_object_mocks import (
    create_mock_vsphere_object
)

pytestmark = pytest.mark.skipif(
    sys.version_info < (2, 7), reason="requires python2.7 or higher"
)


class TestVmwareFolderTemplateFromVm(ModuleTestCase):

    def __prepare(self, mocker):
        mocker.patch.object(PyvmomiClient, 'connect_to_api', return_value=(mocker.Mock(), mocker.Mock()))
        self.test_vm = create_mock_vsphere_object(name="test")
        self.test_vm.runtime.powerState = 'poweredOff'
        self.test_template = create_mock_vsphere_object(name="test-template")
        self.test_template.config.template = True
        self.test_folder = create_mock_vsphere_object(name="test-folder")
        self.test_template.parent = self.test_folder

        mocker.patch.object(VmwareFolderTemplate, 'is_vcenter', return_value=True)
        mocker.patch.object(VmwareFolderTemplate, 'get_folder_by_absolute_path', return_value=self.test_folder)
        mocker.patch.object(VmwareFolderTemplate, 'get_vms_using_params', return_value=[self.test_vm])

    def test_present(self, mocker):
        self.__prepare(mocker)
        # test template creation
        mocker.patch.object(VmwareFolderTemplate, 'check_if_template_exists', return_value=False)
        create_template_mock = mocker.patch.object(VmwareFolderTemplate, 'create_template_in_folder')
        module_args = dict(
            vm_name="test-vm",
            template_name="test-template",
            template_folder="my/template/folder",
            datacenter="datacenter",
        )

        result = run_module(module_entry=module_main, module_args=module_args)
        assert result["changed"] is True
        create_template_mock.assert_called_once()

        # test no change when template exists
        mocker.patch.object(VmwareFolderTemplate, 'check_if_template_exists', return_value=self.test_template)
        create_template_mock.reset_mock()
        result = run_module(module_entry=module_main, module_args=module_args)
        assert result["changed"] is False
        create_template_mock.assert_not_called()

    def test_absent(self, mocker):
        self.__prepare(mocker)
        # test template removal
        template_mock = mocker.Mock()
        mocker.patch.object(VmwareFolderTemplate, 'check_if_template_exists', return_value=template_mock)
        module_args = dict(
            template_name="test-template",
            template_folder="my/template/folder",
            datacenter="datacenter",
            state="absent"
        )

        result = run_module(module_entry=module_main, module_args=module_args)
        assert result["changed"] is True
        template_mock.Destroy_Task.assert_called_once()

        # test no change when template doesn't exist
        mocker.patch.object(VmwareFolderTemplate, 'check_if_template_exists', return_value=False)
        result = run_module(module_entry=module_main, module_args=module_args)
        assert result["changed"] is False

    def test_folder_paths_are_absolute_true(self, mocker):
        self.__prepare(mocker)
        get_folder_mock = mocker.patch.object(VmwareFolderTemplate, 'get_folder_by_absolute_path', return_value=self.test_folder)
        mocker.patch.object(VmwareFolderTemplate, 'check_if_template_exists', return_value=False)
        mocker.patch.object(VmwareFolderTemplate, 'create_template_in_folder')

        module_args = dict(
            vm_name="test-vm",
            template_name="test-template",
            template_folder="/datacenter/vm/my/absolute/path",
            datacenter="datacenter",
            folder_paths_are_absolute=True,
        )

        run_module(module_entry=module_main, module_args=module_args)
        get_folder_mock.assert_called_with("/datacenter/vm/my/absolute/path", fail_on_missing=True)

    def test_folder_paths_are_absolute_false(self, mocker):
        self.__prepare(mocker)
        get_folder_mock = mocker.patch.object(VmwareFolderTemplate, 'get_folder_by_absolute_path', return_value=self.test_folder)
        mocker.patch.object(VmwareFolderTemplate, 'check_if_template_exists', return_value=False)
        mocker.patch.object(VmwareFolderTemplate, 'create_template_in_folder')

        module_args = dict(
            vm_name="test-vm",
            template_name="test-template",
            template_folder="my/relative/path",
            datacenter="datacenter",
            folder_paths_are_absolute=False,
        )

        run_module(module_entry=module_main, module_args=module_args)
        get_folder_mock.assert_called_with("datacenter/vm/my/relative/path", fail_on_missing=True)

        # test default behavior (should be same as False)
        get_folder_mock.reset_mock()
        module_args = dict(
            vm_name="test-vm",
            template_name="test-template",
            template_folder="my/relative/path",
            datacenter="datacenter",
        )

        run_module(module_entry=module_main, module_args=module_args)
        get_folder_mock.assert_called_with("datacenter/vm/my/relative/path", fail_on_missing=True)

    def test_vm_identification_methods(self, mocker):
        self.__prepare(mocker)
        mocker.patch.object(VmwareFolderTemplate, 'check_if_template_exists', return_value=False)
        create_template_mock = mocker.patch.object(VmwareFolderTemplate, 'create_template_in_folder')

        # test with vm_name
        module_args = dict(
            vm_name="test-vm",
            template_name="test-template",
            template_folder="my/template/folder",
            datacenter="datacenter",
        )
        result = run_module(module_entry=module_main, module_args=module_args)
        assert result["changed"] is True

        # test with vm_uuid
        create_template_mock.reset_mock()
        module_args = dict(
            vm_uuid="test-uuid",
            template_name="test-template",
            template_folder="my/template/folder",
            datacenter="datacenter",
        )
        result = run_module(module_entry=module_main, module_args=module_args)
        assert result["changed"] is True

        # test with vm_moid
        create_template_mock.reset_mock()
        module_args = dict(
            vm_moid="test-moid",
            template_name="test-template",
            template_folder="my/template/folder",
            datacenter="datacenter",
        )
        result = run_module(module_entry=module_main, module_args=module_args)
        assert result["changed"] is True

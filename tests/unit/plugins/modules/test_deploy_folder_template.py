from __future__ import absolute_import, division, print_function
__metaclass__ = type

import sys
import pytest
from unittest.mock import patch

from ansible_collections.vmware.vmware.plugins.modules.deploy_folder_template import (
    VmwareFolderTemplate,
    main as module_main
)
from ansible_collections.vmware.vmware.plugins.module_utils.clients.pyvmomi import (
    PyvmomiClient
)
from ansible_collections.vmware.vmware.plugins.module_utils.clients.rest import (
    VmwareRestClient
)
from ansible_collections.vmware.vmware.plugins.module_utils.vm.services._placement import VmPlacement
from ...common.utils import (
    run_module, ModuleTestCase
)
from ...common.vmware_object_mocks import (
    MockVmwareObject
)

pytestmark = pytest.mark.skipif(
    sys.version_info < (2, 7), reason="requires python2.7 or higher"
)


class TestVmwareFolderTemplate(ModuleTestCase):

    def __prepare(self, mocker):
        mocker.patch.object(PyvmomiClient, 'connect_to_api', return_value=(mocker.Mock(), mocker.Mock()))
        mocker.patch.object(VmwareRestClient, 'connect_to_api', return_value=mocker.Mock())
        self.test_vm = MockVmwareObject(name="test")
        self.test_template = mocker.Mock()
        self.test_template.config.template = True

        mocker.patch.object(VmwareFolderTemplate, 'get_folder_by_absolute_path', return_value=MockVmwareObject())
        mocker.patch.object(VmwareFolderTemplate, 'get_objs_by_name_or_moid', return_value=[self.test_template])
        mocker.patch.object(VmwareFolderTemplate, 'deploy', return_value=self.test_vm)

        mocker.patch.object(VmPlacement, 'get_folder', return_value=MockVmwareObject())
        mocker.patch.object(VmPlacement, 'get_datacenter', return_value=MockVmwareObject())
        mocker.patch.object(VmPlacement, 'get_resource_pool', return_value=MockVmwareObject())
        mocker.patch.object(VmPlacement, 'get_datastore', return_value=MockVmwareObject())

    @patch(
        "ansible_collections.vmware.vmware.plugins.modules.deploy_folder_template.vim.vm.RelocateSpec"
    )
    @patch(
        "ansible_collections.vmware.vmware.plugins.modules.deploy_folder_template.vim.vm.CloneSpec"
    )
    def test_present(self, mock_relocate_spec, mock_clone_spec, mocker):
        self.__prepare(mocker)
        mock_relocate_spec.return_value = mocker.Mock()
        mock_clone_spec.return_value = mocker.Mock()
        # test template_name
        mocker.patch.object(VmwareFolderTemplate, 'get_deployed_vm', return_value=None)
        module_args = dict(
            vm_name=self.test_vm.name,
            template_name="foo",
            datacenter='foo',
        )

        result = run_module(module_entry=module_main, module_args=module_args)
        assert result["changed"] is True
        assert result["vm"]["moid"] is self.test_vm._GetMoId()

        # test template_id
        mocker.patch.object(VmwareFolderTemplate, 'get_deployed_vm', return_value=None)
        module_args = dict(
            vm_name=self.test_vm.name,
            template_id="foo",
            datacenter='foo',
        )
        result = run_module(module_entry=module_main, module_args=module_args)
        assert result["changed"] is True
        assert result["vm"]["moid"] is self.test_vm._GetMoId()

        # test no change
        mocker.patch.object(VmwareFolderTemplate, 'get_deployed_vm', return_value=self.test_vm)
        result = run_module(module_entry=module_main, module_args=module_args)
        assert result["changed"] is False
        assert result["vm"]["moid"] is self.test_vm._GetMoId()

    def test_template_error(self, mocker):
        self.__prepare(mocker)
        mocker.patch.object(VmwareFolderTemplate, 'get_deployed_vm', return_value=None)
        mocker.patch.object(VmwareFolderTemplate, 'get_objs_by_name_or_moid', return_value=None)
        module_args = dict(
            vm_name=self.test_vm.name,
            template_id="foo",
            datacenter='foo',
        )

        result = run_module(module_entry=module_main, module_args=module_args, expect_success=False)
        assert result["msg"].startswith('Unable to find template with ID')
        assert result["failed"] is True

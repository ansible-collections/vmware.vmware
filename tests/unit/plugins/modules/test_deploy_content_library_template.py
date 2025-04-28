from __future__ import absolute_import, division, print_function
__metaclass__ = type

import sys
import pytest

from ansible_collections.vmware.vmware.plugins.modules.deploy_content_library_template import (
    VmwareContentDeployTemplate,
    main as module_main
)
from ansible_collections.vmware.vmware.plugins.module_utils.clients.pyvmomi import (
    PyvmomiClient
)
from ansible_collections.vmware.vmware.plugins.module_utils.clients.rest import (
    VmwareRestClient
)
from ...common.utils import (
    run_module, ModuleTestCase
)
from ...common.vmware_object_mocks import (
    MockVmwareObject
)

pytestmark = pytest.mark.skipif(
    sys.version_info < (2, 7), reason="requires python2.7 or higher"
)


class TestDeployContentLibraryTemplate(ModuleTestCase):

    def __prepare(self, mocker):
        mocker.patch.object(PyvmomiClient, 'connect_to_api', return_value=(mocker.Mock(), mocker.Mock()))
        mocker.patch.object(VmwareRestClient, 'connect_to_api', return_value=mocker.Mock())
        self.test_vm = MockVmwareObject(name="test")

        mocker.patch.object(VmwareContentDeployTemplate, 'get_resource_pool_by_name_or_moid', return_value=MockVmwareObject())
        mocker.patch.object(VmwareContentDeployTemplate, 'get_datastore_by_name_or_moid', return_value=MockVmwareObject())
        mocker.patch.object(VmwareContentDeployTemplate, 'get_datacenter_by_name_or_moid', return_value=MockVmwareObject())
        mocker.patch.object(VmwareContentDeployTemplate, 'deploy', return_value=self.test_vm._GetMoId())

    def test_present(self, mocker):
        self.__prepare(mocker)
        mocker.patch.object(VmwareContentDeployTemplate, 'get_deployed_vm', return_value=None)
        module_args = dict(
            vm_name=self.test_vm.name,
            library_item_id='111',
            datastore='foo',
            datacenter='foo',
            resource_pool='foo'
        )

        result = run_module(module_entry=module_main, module_args=module_args)
        assert result["changed"] is True
        assert result["vm"]["moid"] is self.test_vm._GetMoId()

        mocker.patch.object(VmwareContentDeployTemplate, 'get_deployed_vm', return_value=self.test_vm)
        module_args = dict(
            vm_name=self.test_vm.name,
            library_item_id='111',
            datastore='foo',
            datacenter='foo',
            resource_pool='foo'
        )

        result = run_module(module_entry=module_main, module_args=module_args)
        assert result["changed"] is False
        assert result["vm"]["moid"] is self.test_vm._GetMoId()

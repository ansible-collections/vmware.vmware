from __future__ import absolute_import, division, print_function
__metaclass__ = type

import sys
import pytest

from ansible_collections.vmware.vmware.plugins.modules.vmdk_info import (
    VmdkInfoModule,
    main as module_main
)
from ansible_collections.vmware.vmware.plugins.module_utils.clients.pyvmomi import (
    PyvmomiClient
)
from ansible_collections.vmware.vmware.plugins.module_utils._vmdk import (
    VmdkFiles,
    VmdkPath
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


class TestVmdkInfo(ModuleTestCase):

    def __prepare(self, mocker, facts):
        mocker.patch.object(PyvmomiClient, 'connect_to_api', return_value=(mocker.Mock(), mocker.Mock()))
        self.path = VmdkPath(create_mock_vsphere_object(name='ds1'), mocker.Mock(), '[ds1] vm1/vm1.vmdk')
        self.resolve = mocker.patch.object(VmdkFiles, 'resolve', return_value=self.path)
        self.describe = mocker.patch.object(VmdkFiles, 'describe', return_value=facts)

    def test_existing_disk(self, mocker):
        facts = {'path': '[ds1] vm1/vm1.vmdk', 'exists': True, 'provisioning': 'thin'}
        self.__prepare(mocker, facts)

        result = run_module(module_entry=module_main, module_args=dict(path='/vmfs/volumes/ds1/vm1/vm1.vmdk'))
        assert result['changed'] is False
        assert result['vmdk'] == facts
        self.resolve.assert_called_once_with('/vmfs/volumes/ds1/vm1/vm1.vmdk', 'path')
        self.describe.assert_called_once_with(self.path)

    def test_missing_disk(self, mocker):
        self.__prepare(mocker, {'path': '[ds1] vm1/vm1.vmdk', 'exists': False})

        result = run_module(module_entry=module_main, module_args=dict(path='[ds1] vm1/vm1.vmdk'))
        assert result['changed'] is False
        assert result['vmdk']['exists'] is False

    def test_check_mode(self, mocker):
        self.__prepare(mocker, {'path': '[ds1] vm1/vm1.vmdk', 'exists': True})

        result = run_module(module_entry=module_main, module_args=dict(path='[ds1] vm1/vm1.vmdk', _ansible_check_mode=True))
        assert result['changed'] is False
        assert result['vmdk']['exists'] is True

    def test_path_is_required(self, mocker):
        self.__prepare(mocker, {})

        result = run_module(module_entry=module_main, module_args=dict(), expect_success=False)
        assert 'path' in result['msg']

    def test_gather_info(self, mocker):
        self.__prepare(mocker, {'exists': True})
        module = mocker.Mock(params={'path': '[ds1] vm1/vm1.vmdk', 'hostname': 'h', 'username': 'u', 'password': 'p'})

        assert VmdkInfoModule(module).gather_info() == {'exists': True}

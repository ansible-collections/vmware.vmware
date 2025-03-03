from __future__ import absolute_import, division, print_function
__metaclass__ = type

import sys
import pytest

from ansible_collections.vmware.vmware.plugins.modules.local_content_library import (
    VmwareContentLibrary,
    main as module_main
)
from ansible_collections.vmware.vmware.plugins.module_utils.clients._rest import VmwareRestClient
from ansible_collections.vmware.vmware.plugins.module_utils.clients._pyvmomi import PyvmomiClient
from ansible_collections.vmware.vmware.plugins.module_utils._module_pyvmomi_base import ModulePyvmomiBase
from ...common.utils import (
    AnsibleExitJson, ModuleTestCase, set_module_args,
)

pytestmark = pytest.mark.skipif(
    sys.version_info < (2, 7), reason="requires python2.7 or higher"
)


class TestLocalContentLibrary(ModuleTestCase):

    def __prepare(self, mocker):
        mocker.patch.object(PyvmomiClient, 'connect_to_api', return_value=(mocker.Mock(), mocker.Mock()))
        rest_client = mocker.patch.object(VmwareRestClient, 'connect_to_api', return_value=mocker.Mock())
        self.library_service = rest_client.content.Library
        self.typed_library_service = rest_client.content.LocalLibrary
        mocker.patch.object(ModulePyvmomiBase, 'get_datastore_by_name_or_moid', return_value=mocker.Mock())
        self.test_library = mocker.Mock()
        self.test_library.name = 'test'
        self.test_library.id = '1'

    def test_absent(self, mocker):
        self.__prepare(mocker)

        set_module_args(
            hostname="127.0.0.1",
            username="administrator@local",
            password="123456",
            add_cluster=False,
            name='test',
            state='absent'
        )
        mocker.patch.object(VmwareContentLibrary, 'get_content_library_ids', return_value=[])
        with pytest.raises(AnsibleExitJson) as c:
            module_main()

        assert c.value.args[0]["changed"] is False

        mocker.patch.object(VmwareContentLibrary, 'get_content_library_ids', return_value=[self.test_library])
        mocker.patch.object(self.library_service, 'get', return_value=self.test_library)
        mocker.patch.object(self.typed_library_service, 'delete')

        with pytest.raises(AnsibleExitJson) as c:
            module_main()

        assert c.value.args[0]["changed"] is True

    def test_present(self, mocker):
        self.__prepare(mocker)

        set_module_args(
            hostname="127.0.0.1",
            username="administrator@local",
            password="123456",
            add_cluster=False,
            name='test',
            state='present',
            datastore='foo'
        )
        mocker.patch.object(VmwareContentLibrary, 'get_content_library_ids', return_value=[])
        with pytest.raises(AnsibleExitJson) as c:
            module_main()

        assert c.value.args[0]["changed"] is True

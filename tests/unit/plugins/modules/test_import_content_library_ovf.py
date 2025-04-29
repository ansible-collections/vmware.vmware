from __future__ import absolute_import, division, print_function
__metaclass__ = type

import sys
import pytest

from ansible_collections.vmware.vmware.plugins.modules.import_content_library_ovf import (
    VmwareRemoteOvf,
    main as module_main
)
from ansible_collections.vmware.vmware.plugins.module_utils.clients.rest import (
    VmwareRestClient
)
from ...common.utils import (
    run_module, ModuleTestCase
)
from com.vmware.content.library.item.updatesession_client import PreviewInfo

pytestmark = pytest.mark.skipif(
    sys.version_info < (2, 7), reason="requires python2.7 or higher"
)

import os


class TestVmwareRemoteOvf(ModuleTestCase):

    def __prepare(self, mocker):
        self.mock_rest_client = mocker.Mock()
        mocker.patch.object(VmwareRestClient, 'connect_to_api', return_value=self.mock_rest_client)
        mocker.patch.object(VmwareRemoteOvf, 'get_content_library_ids', return_value=["1"])
        mocker.patch.object(os, 'listdir', return_value=['foo.bar', 'bizz.ovf', 'buzz.vmdk'])

        mock_session = mocker.Mock()
        mock_session.preview_info.state = PreviewInfo.State.AVAILABLE
        mock_session.preview_info.warnings = []
        mock_session.state = 'DONE'
        self.mock_rest_client.content.library.item.UpdateSession.get.return_value = mock_session

    def test_absent(self, mocker):
        self.__prepare(mocker)
        module_args = dict(
            dest='foo',
            state='absent',
            library_name='foo'
        )

        # test item exists
        mocker.patch.object(VmwareRemoteOvf, 'get_library_item_ids', return_value=["1"])
        result = run_module(module_entry=module_main, module_args=module_args)

        assert result["changed"] is True
        assert result["library_item"]["id"] == '1'

        # test item already absent
        mocker.patch.object(VmwareRemoteOvf, 'get_library_item_ids', return_value=[])
        result = run_module(module_entry=module_main, module_args=module_args)

        assert result["changed"] is False

    def test_present_url_source(self, mocker):
        self.__prepare(mocker)
        module_args = dict(
            dest='foo',
            src='http://example.com/foo.ova',
            state='present',
            library_name='foo'
        )

        # test item already present
        mocker.patch.object(VmwareRemoteOvf, 'get_library_item_ids', return_value=["1"])
        result = run_module(module_entry=module_main, module_args=module_args)

        assert result["changed"] is False
        assert result["library_item"]["id"] == '1'

        # test item missing
        mocker.patch.object(VmwareRemoteOvf, 'get_library_item_ids', return_value=[])
        mocker.patch.object(self.mock_rest_client.content.library.Item, 'create', return_value='2')
        result = run_module(module_entry=module_main, module_args=module_args)

        assert result["changed"] is True
        assert result["library_item"]["id"] == '2'

    def test_present_file_source(self, mocker):
        self.__prepare(mocker)

        # test ovf
        module_args = dict(
            dest='foo',
            src='/tmp',
            state='present',
            library_name='foo',
        )

        mocker.patch.object(VmwareRemoteOvf, 'get_library_item_ids', return_value=[])
        mocker.patch.object(self.mock_rest_client.content.library.Item, 'create', return_value='2')
        self.mock_rest_client.content.library.item.updatesession.File.add.return_value
        mocker.patch.object(os.path, 'getsize', return_value=10)
        mocker.patch.object(os, 'listdir', return_value=['foo', 'foo.ovf', 'foo.vmdk'])
        mocker.patch("builtins.open", new_callable=mocker.mock_open, read_data="data")
        mocker.patch('ansible_collections.vmware.vmware.plugins.modules.import_content_library_ovf.open_url')

        result = run_module(module_entry=module_main, module_args=module_args)

        assert result["changed"] is True
        assert result["library_item"]["id"] == '2'

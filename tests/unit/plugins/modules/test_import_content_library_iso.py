from __future__ import absolute_import, division, print_function

__metaclass__ = type

import sys
import pytest
from unittest.mock import patch, mock_open
from ansible_collections.vmware.vmware.plugins.modules.import_content_library_iso import (
    VmwareRemoteIso,
    main as module_main,
)
from ansible_collections.vmware.vmware.plugins.module_utils.clients.rest import (
    VmwareRestClient,
)
from ...common.utils import run_module, ModuleTestCase
from com.vmware.content.library.item.updatesession_client import PreviewInfo

pytestmark = pytest.mark.skipif(
    sys.version_info < (2, 7), reason="requires python2.7 or higher"
)

import os


class TestVmwareRemoteIso(ModuleTestCase):
    def __prepare(self, mocker):
        self.mock_rest_client = mocker.Mock()
        mocker.patch.object(
            VmwareRestClient, "connect_to_api", return_value=self.mock_rest_client
        )
        mocker.patch.object(
            VmwareRemoteIso, "get_content_library_ids", return_value=["1"]
        )
        mock_session = mocker.Mock()
        mock_session.preview_info.state = PreviewInfo.State.AVAILABLE
        mock_session.preview_info.warnings = []
        mock_session.state = "DONE"
        self.mock_rest_client.content.library.item.UpdateSession.get.return_value = (
            mock_session
        )

    def test_absent(self, mocker):
        self.__prepare(mocker)
        module_args = dict(dest="foo", state="absent", library_name="foo")

        # test item exists
        mocker.patch.object(VmwareRemoteIso, "get_library_item_ids", return_value=["1"])
        result = run_module(module_entry=module_main, module_args=module_args)

        assert result["changed"] is True
        assert result["library_item"]["id"] == "1"

        # test item already absent
        mocker.patch.object(VmwareRemoteIso, "get_library_item_ids", return_value=[])
        result = run_module(module_entry=module_main, module_args=module_args)

        assert result["changed"] is False

    def test_present_url_source(self, mocker):
        self.__prepare(mocker)
        module_args = dict(
            dest="foo",
            src="http://example.com/foo.iso",
            state="present",
            library_name="foo",
        )

        # test item already present
        mocker.patch.object(VmwareRemoteIso, "get_library_item_ids", return_value=["1"])
        result = run_module(module_entry=module_main, module_args=module_args)

        assert result["changed"] is False
        assert result["library_item"]["id"] == "1"

        # test item missing
        mocker.patch.object(VmwareRemoteIso, "get_library_item_ids", return_value=[])
        mocker.patch.object(
            self.mock_rest_client.content.library.Item, "create", return_value="2"
        )
        result = run_module(module_entry=module_main, module_args=module_args)

        assert result["changed"] is True
        assert result["library_item"]["id"] == "2"

    def test_present_file_source(self, mocker):
        self.__prepare(mocker)

        module_args = dict(
            dest="foo",
            src="/tmp/foo.iso",
            state="present",
            library_name="foo",
        )

        mocker.patch.object(VmwareRemoteIso, "get_library_item_ids", return_value=[])
        mocker.patch.object(
            self.mock_rest_client.content.library.Item, "create", return_value="2"
        )
        mocker.patch.object(os.path, "getsize", return_value=10)

        # Mock open_url to prevent real HTTP call
        mock_response = mocker.Mock()
        mock_response.read.return_value = b"OK"
        mock_response.getcode.return_value = 200
        mocker.patch(
            "ansible_collections.vmware.vmware.plugins.modules.import_content_library_iso.open_url",
            return_value=mock_response,
        )

        # Selectively mock open() for ISO file
        real_open = open

        def selective_open(path, *args, **kwargs):
            if path == "/tmp/foo.iso":
                return mock_open(read_data="DATA")().return_value
            return real_open(path, *args, **kwargs)

        with patch("builtins.open", side_effect=selective_open):
            result = run_module(module_entry=module_main, module_args=module_args)

        assert result["changed"] is True
        assert result["library_item"]["id"] == "2"

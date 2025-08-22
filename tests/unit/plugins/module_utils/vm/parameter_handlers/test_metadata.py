from __future__ import absolute_import, division, print_function

__metaclass__ = type

import pytest
from unittest.mock import Mock, patch, ANY

from ansible_collections.vmware.vmware.plugins.module_utils.vm.parameter_handlers._metadata import (
    MetadataParameterHandler,
)


class TestMetadataParameterHandler:
    @pytest.fixture
    def metadata_parameter_handler(self):
        return MetadataParameterHandler(Mock(), {}, Mock(), Mock(), Mock())

    def test_verify_parameter_constraints(self, metadata_parameter_handler):
        metadata_parameter_handler.verify_parameter_constraints()
        metadata_parameter_handler.error_handler.fail_with_parameter_error.assert_not_called()

        metadata_parameter_handler.vm = None
        metadata_parameter_handler.verify_parameter_constraints()
        assert (
            metadata_parameter_handler.error_handler.fail_with_parameter_error.call_count
            > 1
        )

        metadata_parameter_handler.error_handler.fail_with_parameter_error.reset_mock()
        metadata_parameter_handler.params = {
            "name": "test",
            "guest_id": "test",
            "datastore": "test",
        }
        metadata_parameter_handler.verify_parameter_constraints()
        metadata_parameter_handler.error_handler.fail_with_parameter_error.assert_not_called()

    def test_compare_live_config_with_desired_config(self, metadata_parameter_handler):
        metadata_parameter_handler.compare_live_config_with_desired_config()
        assert (
            metadata_parameter_handler.change_set.check_if_change_is_required.call_count
            == 2
        )

    @patch(
        "ansible_collections.vmware.vmware.plugins.module_utils.vm.parameter_handlers._metadata.vim.vm.FileInfo"
    )
    def test_populate_config_spec_with_parameters(
        self, mock_file_info, metadata_parameter_handler
    ):
        mock_file_info.return_value = Mock()
        configspec = Mock()
        metadata_parameter_handler.vm = Mock()
        metadata_parameter_handler.vm.name = "test"
        metadata_parameter_handler.populate_config_spec_with_parameters(configspec)
        assert configspec.name == "test"

        metadata_parameter_handler.params = {"name": "test2"}
        metadata_parameter_handler.populate_config_spec_with_parameters(configspec)
        assert configspec.name == "test2"

        metadata_parameter_handler.params = {"guest_id": "abc"}
        metadata_parameter_handler.vm = None
        metadata_parameter_handler.populate_config_spec_with_parameters(configspec)
        mock_file_info.assert_called_once_with(
            logDirectory=None,
            snapshotDirectory=None,
            suspendDirectory=None,
            vmPathName=ANY,
        )
        assert configspec.guestId == "abc"

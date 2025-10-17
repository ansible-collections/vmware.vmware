from __future__ import absolute_import, division, print_function

__metaclass__ = type

import pytest
from unittest.mock import Mock, patch

from ansible_collections.vmware.vmware.plugins.module_utils.vm.parameter_handlers.device_linked._cdroms import (
    CdromParameterHandler,
)
from ansible_collections.vmware.vmware.plugins.module_utils.vm.parameter_handlers._abstract import (
    DeviceLinkError,
)


class TestCdromParameterHandler:
    @pytest.fixture
    def mock_controller(self):
        """Create a mock controller for testing."""
        controller = Mock()
        controller.key = 1000
        controller.category = "sata"
        return controller

    @pytest.fixture
    def mock_controller_handler(self, mock_controller):
        """Create a mock controller handler for testing."""
        handler = Mock()
        handler.category = "sata"
        handler.controllers = {0: mock_controller}
        return handler

    @pytest.fixture
    def parameter_handler(self, mock_controller_handler):
        """Create a CdromParameterHandler instance for testing."""
        error_handler = Mock()
        params = {}
        change_set = Mock()
        vm = Mock()
        device_tracker = Mock()
        controller_handlers = [mock_controller_handler]

        return CdromParameterHandler(
            error_handler, params, change_set, vm, device_tracker, controller_handlers
        )

    def test_verify_parameter_constraints(self, parameter_handler):
        """Test verify_parameter_constraints method."""
        parameter_handler._parse_cdrom_params = Mock()
        parameter_handler.verify_parameter_constraints()
        parameter_handler._parse_cdrom_params.assert_called_once()
        assert parameter_handler.cdroms == []

        parameter_handler._parse_cdrom_params = Mock(side_effect=ValueError("test"))
        parameter_handler.error_handler.fail_with_parameter_error = Mock(
            side_effect=ValueError("test")
        )
        with pytest.raises(ValueError, match="test"):
            parameter_handler.verify_parameter_constraints()
        parameter_handler.error_handler.fail_with_parameter_error.assert_called_once()

        parameter_handler._parse_cdrom_params = Mock()
        parameter_handler.cdroms = [1]
        parameter_handler.verify_parameter_constraints()
        parameter_handler._parse_cdrom_params.assert_not_called()

    def test_parse_cdrom_params(self, parameter_handler):
        """Test parse_cdrom_params method."""
        parameter_handler.error_handler.fail_with_parameter_error = Mock(
            side_effect=ValueError("test")
        )
        parameter_handler.params = {
            "cdroms": [
                {
                    "iso_media_path": "test",
                    "client_device_mode": None,
                    "device_node": "SATA(0:0)",
                }
            ]
        }
        parameter_handler._parse_cdrom_params()
        assert len(parameter_handler.cdroms) == 1

        with pytest.raises(ValueError, match="test"):
            parameter_handler.params = {
                "cdroms": [
                    {
                        "iso_media_path": "test",
                        "client_device_mode": None,
                        "device_node": "SCSI(0:0)",
                    }
                ]
            }
            parameter_handler._parse_cdrom_params()

        with pytest.raises(ValueError, match="test"):
            parameter_handler.params = {
                "cdroms": [
                    {
                        "iso_media_path": "test",
                        "client_device_mode": None,
                        "device_node": "IDE(0:0)",
                    }
                ]
            }
            parameter_handler._parse_cdrom_params()

    def test_populate_config_spec_with_parameters(self, parameter_handler):
        """Test populate_config_spec_with_parameters method."""
        parameter_handler.change_set.objects_to_add = [Mock()]
        parameter_handler.change_set.objects_to_update = [Mock()]
        parameter_handler.populate_config_spec_with_parameters(Mock())
        assert len(parameter_handler.change_set.objects_to_add) == 1
        assert len(parameter_handler.change_set.objects_to_update) == 1

    def test_compare_live_config_with_desired_config(self, parameter_handler):
        """Test compare_live_config_with_desired_config method."""
        cdrom = Mock()
        cdrom.has_a_linked_live_vm_device = Mock(return_value=False)
        parameter_handler.cdroms = [cdrom]
        parameter_handler.change_set.objects_to_add = []
        parameter_handler.change_set.objects_to_update = []
        parameter_handler.change_set.objects_in_sync = []
        parameter_handler.compare_live_config_with_desired_config()
        assert len(parameter_handler.change_set.objects_to_add) == 1
        assert len(parameter_handler.change_set.objects_to_update) == 0

        parameter_handler.change_set.objects_to_add = []
        parameter_handler.change_set.objects_to_update = []
        parameter_handler.change_set.objects_in_sync = []
        cdrom.has_a_linked_live_vm_device = Mock(return_value=True)
        cdrom.differs_from_live_object = Mock(return_value=True)
        parameter_handler.compare_live_config_with_desired_config()
        assert len(parameter_handler.change_set.objects_to_add) == 0
        assert len(parameter_handler.change_set.objects_to_update) == 1

        parameter_handler.change_set.objects_to_add = []
        parameter_handler.change_set.objects_to_update = []
        parameter_handler.change_set.objects_in_sync = []
        cdrom.differs_from_live_object = Mock(return_value=False)
        parameter_handler.compare_live_config_with_desired_config()
        assert len(parameter_handler.change_set.objects_to_add) == 0
        assert len(parameter_handler.change_set.objects_to_update) == 0

    @patch(
        "ansible_collections.vmware.vmware.plugins.module_utils.vm.parameter_handlers.device_linked._cdroms.Cdrom"
    )
    def test_link_vm_device(self, mock_cdrom_class, parameter_handler):
        """Test link_vm_device method."""
        mock_vm_device = Mock()
        mock_vm_device.unitNumber = 1
        mock_vm_device.controllerKey = 1000

        mock_cdrom = Mock()
        mock_cdrom._live_object = None
        mock_cdrom.unit_number = 2
        mock_cdrom.controller.key = 1000

        mock_cdrom_2 = Mock()
        mock_cdrom_2._live_object = Mock()

        mock_cdrom_3 = Mock()
        mock_cdrom_3._live_object = None
        mock_cdrom_3.unit_number = 1
        mock_cdrom_3.controller.key = 1000

        parameter_handler.cdroms = [mock_cdrom, mock_cdrom_2, mock_cdrom_3]

        parameter_handler.link_vm_device(mock_vm_device)
        assert mock_cdrom._live_object is None
        assert mock_cdrom_class.from_live_device_spec.call_count == 1

    @patch(
        "ansible_collections.vmware.vmware.plugins.module_utils.vm.parameter_handlers.device_linked._cdroms.Cdrom"
    )
    def test_link_vm_device_no_matching_device(self, mock_cdrom_class, parameter_handler):
        """Test link_vm_device method when no matching adapter is found."""
        cdrom = Mock()
        cdrom._live_object = Mock()
        parameter_handler.cdroms = [cdrom]
        mock_cdrom_class.from_live_device_spec.return_value = 1
        out = parameter_handler.link_vm_device(Mock())
        assert out is not None

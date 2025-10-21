from __future__ import absolute_import, division, print_function

__metaclass__ = type

import pytest
from unittest.mock import Mock, patch

from ansible_collections.vmware.vmware.plugins.module_utils.vm.parameter_handlers.device_linked._nvdimms import (
    NvdimmParameterHandler,
)


class TestNvdimmParameterHandler:

    @pytest.fixture
    def parameter_handler(self):
        """Create a NvdimmParameterHandler instance for testing."""
        error_handler = Mock()
        params = {}
        change_set = Mock()
        vm = Mock()
        device_tracker = Mock()

        return NvdimmParameterHandler(
            error_handler, params, change_set, vm, device_tracker
        )

    def test_verify_parameter_constraints(self, parameter_handler):
        """Test verify_parameter_constraints method."""
        parameter_handler._parse_nvdimm_params = Mock()
        parameter_handler.verify_parameter_constraints()
        parameter_handler._parse_nvdimm_params.assert_called_once()
        assert parameter_handler.nvdimms == []

        parameter_handler._parse_nvdimm_params = Mock(side_effect=ValueError("test"))
        parameter_handler.error_handler.fail_with_parameter_error = Mock(
            side_effect=ValueError("test")
        )
        with pytest.raises(ValueError, match="test"):
            parameter_handler.verify_parameter_constraints()
        parameter_handler.error_handler.fail_with_parameter_error.assert_called_once()

        parameter_handler._parse_nvdimm_params = Mock()
        parameter_handler.nvdimms = [1]
        parameter_handler.verify_parameter_constraints()
        parameter_handler._parse_nvdimm_params.assert_not_called()

    def test_parse_nvdimm_params(self, parameter_handler):
        """Test parse_nvdimm_params method."""
        parameter_handler.params = {
            "nvdimms": [
                {
                    "size_mb": 1024,
                }
            ]
        }
        parameter_handler._parse_nvdimm_params()
        assert len(parameter_handler.nvdimms) == 1
        assert parameter_handler.controller is not None

    def test_populate_config_spec_with_parameters(self, parameter_handler):
        """Test populate_config_spec_with_parameters method."""
        parameter_handler.change_set.objects_to_add = [Mock()]
        parameter_handler.change_set.objects_to_update = [Mock()]
        parameter_handler.populate_config_spec_with_parameters(Mock())
        assert len(parameter_handler.change_set.objects_to_add) == 1
        assert len(parameter_handler.change_set.objects_to_update) == 1

    def test_compare_live_config_with_desired_config(self, parameter_handler):
        """Test compare_live_config_with_desired_config method."""
        nvdimm = Mock()
        nvdimm.has_a_linked_live_vm_device = Mock(return_value=False)
        parameter_handler.nvdimms = [nvdimm]
        parameter_handler.change_set.objects_to_add = []
        parameter_handler.change_set.objects_to_update = []
        parameter_handler.change_set.objects_in_sync = []
        parameter_handler.compare_live_config_with_desired_config()
        assert len(parameter_handler.change_set.objects_to_add) == 1
        assert len(parameter_handler.change_set.objects_to_update) == 0

        parameter_handler.change_set.objects_to_add = []
        parameter_handler.change_set.objects_to_update = []
        parameter_handler.change_set.objects_in_sync = []
        nvdimm.has_a_linked_live_vm_device = Mock(return_value=True)
        nvdimm.differs_from_live_object = Mock(return_value=True)
        parameter_handler.compare_live_config_with_desired_config()
        assert len(parameter_handler.change_set.objects_to_add) == 0
        assert len(parameter_handler.change_set.objects_to_update) == 1

        parameter_handler.change_set.objects_to_add = []
        parameter_handler.change_set.objects_to_update = []
        parameter_handler.change_set.objects_in_sync = []
        nvdimm.differs_from_live_object = Mock(return_value=False)
        parameter_handler.compare_live_config_with_desired_config()
        assert len(parameter_handler.change_set.objects_to_add) == 0
        assert len(parameter_handler.change_set.objects_to_update) == 0

    @patch(
        "ansible_collections.vmware.vmware.plugins.module_utils.vm.parameter_handlers.device_linked._nvdimms.Nvdimm"
    )
    def test_link_nvdimm_device(self, mock_nvdimm_class, parameter_handler):
        """Test link_vm_device method."""
        mock_vm_device = Mock()
        mock_vm_device.unitNumber = 1
        mock_vm_device.controllerKey = 1000

        mock_nvdimm = Mock()
        mock_nvdimm.has_a_linked_live_vm_device = Mock(return_value=True)

        mock_nvdimm_2 = Mock()
        mock_nvdimm_2.has_a_linked_live_vm_device = Mock(return_value=False)

        parameter_handler.nvdimms = [mock_nvdimm, mock_nvdimm_2]

        parameter_handler._link_nvdimm_device(mock_vm_device)
        assert mock_nvdimm_class.from_live_device_spec.call_count == 1

    @patch(
        "ansible_collections.vmware.vmware.plugins.module_utils.vm.parameter_handlers.device_linked._nvdimms.NvdimmDeviceController"
    )
    def test_link_nvdimm_controller(self, mock_nvdimm_controller_class, parameter_handler):
        """Test link_vm_device method when no matching adapter is found."""
        parameter_handler.controller = Mock()
        parameter_handler.controller.has_a_linked_live_vm_device = Mock(return_value=True)
        out = parameter_handler._link_nvdimm_controller(Mock())
        assert out is not None

        parameter_handler.controller = Mock()
        parameter_handler.controller.has_a_linked_live_vm_device = Mock(return_value=False)

        out = parameter_handler._link_nvdimm_controller(Mock())
        assert out is None
        mock_nvdimm_controller_class.from_live_device_spec.assert_called()

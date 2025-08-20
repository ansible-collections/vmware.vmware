from __future__ import absolute_import, division, print_function

__metaclass__ = type

import pytest
from unittest.mock import Mock

from ansible_collections.vmware.vmware.plugins.module_utils.vm.services._error_handler import (
    ErrorHandler,
)
from tests.unit.common.utils import AnsibleFailJson


class TestErrorHandler:
    """Test cases for ErrorHandler class."""

    @pytest.fixture
    def error_handler(self):
        eh = ErrorHandler(Mock(), Mock())
        eh.module.fail_json = Mock(side_effect=AnsibleFailJson())
        return eh

    def test_generic_fail_json(self, error_handler):
        """Test _generic_fail_json with additional details."""
        parameter_name = "test_param"
        message = "Test error message"
        error_code = "TEST_ERROR"

        with pytest.raises(AnsibleFailJson) as exc_info:
            error_handler._generic_fail_json(parameter_name, message, error_code)

        error_handler.module.fail_json.assert_called_once_with(
            msg=message,
            error_code=error_code,
            details={"parameter_name": parameter_name},
        )

        details = {"key": "value"}
        error_handler.module.fail_json.reset_mock()
        with pytest.raises(AnsibleFailJson) as exc_info:
            error_handler._generic_fail_json(
                parameter_name, message, error_code, details
            )

        error_handler.module.fail_json.assert_called_once_with(
            msg=message,
            error_code=error_code,
            details={"parameter_name": parameter_name, "key": "value"},
        )

    def test_fail_with_power_cycle_error(self, error_handler):
        """Test fail_with_power_cycle_error with default message."""
        parameter_name = "cpu_count"
        error_handler._generic_fail_json = Mock()

        error_handler.fail_with_power_cycle_error(parameter_name)
        error_handler._generic_fail_json.assert_called_once_with(
            parameter_name,
            "Configuring cpu_count is not supported while the VM is powered on.",
            "POWER_CYCLE_REQUIRED",
            None,
        )

        error_handler._generic_fail_json.reset_mock()
        error_handler.fail_with_power_cycle_error(
            parameter_name, "Custom message", {"key": "value"}
        )
        error_handler._generic_fail_json.assert_called_once_with(
            parameter_name, "Custom message", "POWER_CYCLE_REQUIRED", {"key": "value"}
        )

    def test_fail_with_generic_power_cycle_error(self, error_handler):
        """Test fail_with_generic_power_cycle_error."""
        desired_power_state = "powered off"

        with pytest.raises(AnsibleFailJson) as exc_info:
            error_handler.fail_with_generic_power_cycle_error(desired_power_state)

        error_handler.module.fail_json.assert_called_once_with(
            msg=(
                "VM needs to be powered off to make changes. You can allow this module "
                "to automatically power cycle the VM with the allow_power_cycling parameter."
            ),
            error_code="POWER_CYCLE_REQUIRED",
        )

    def test_fail_with_parameter_error(self, error_handler):
        """Test fail_with_parameter_error."""
        parameter_name = "invalid_param"
        message = "Parameter value is invalid"
        details = {"allowed_values": [1, 2, 3], "provided_value": 5}
        error_handler._generic_fail_json = Mock()

        error_handler.fail_with_parameter_error(parameter_name, message, details)
        error_handler._generic_fail_json.assert_called_once_with(
            parameter_name, message, "PARAMETER_ERROR", details
        )

    def test_fail_with_device_configuration_error_with_device_name(self, error_handler):
        """Test fail_with_device_configuration_error with device that has name_as_str."""
        mock_error = Mock()
        mock_error.__str__ = Mock(return_value="Invalid configuration for device '1'")
        mock_device = Mock()
        mock_device.name_as_str = "Test Device"
        mock_device._device = None
        mock_device._spec = None

        error_handler.device_tracker.translate_device_id_to_device.return_value = (
            mock_device
        )

        with pytest.raises(AnsibleFailJson) as exc_info:
            error_handler.fail_with_device_configuration_error(mock_error)

        error_handler.module.fail_json.assert_called_once_with(
            msg="Device Test Device (device 1 in the VM spec) has an invalid configuration. Please check the device configuration and try again.",
            device_is_being_added=True,
            device_is_being_removed=False,
            device_is_in_sync=True,
        )

    def test_fail_with_device_configuration_error_with_bus_number(self, error_handler):
        """Test fail_with_device_configuration_error with device that has busNumber."""
        mock_error = Mock()
        mock_error.__str__ = Mock(return_value="Invalid configuration for device '2'")

        mock_device = Mock()
        del mock_device.name_as_str
        del mock_device.unitNumber
        mock_device.busNumber = 0
        mock_device._device = False
        mock_device._spec = None

        error_handler.device_tracker.translate_device_id_to_device.return_value = (
            mock_device
        )

        with pytest.raises(AnsibleFailJson) as exc_info:
            error_handler.fail_with_device_configuration_error(mock_error)

        error_handler.module.fail_json.assert_called_once_with(
            msg="Device Mock (bus 0) (device 2 in the VM spec) has an invalid configuration. Please check the device configuration and try again.",
            device_is_being_added=False,
            device_is_being_removed=True,
            device_is_in_sync=True,
        )

    def test_fail_with_device_configuration_error_with_unit_number(self, error_handler):
        """Test fail_with_device_configuration_error with device that has unitNumber."""
        mock_error = Mock()
        mock_error.__str__ = Mock(return_value="Invalid configuration for device '3'")

        mock_device = Mock()
        del mock_device.name_as_str
        del mock_device.busNumber
        mock_device.unitNumber = 1
        mock_device._device = None
        mock_device._spec = False

        error_handler.device_tracker.translate_device_id_to_device.return_value = (
            mock_device
        )

        with pytest.raises(AnsibleFailJson) as exc_info:
            error_handler.fail_with_device_configuration_error(mock_error)

        error_handler.module.fail_json.assert_called_once_with(
            msg="Device Mock (unit number 1) (device 3 in the VM spec) has an invalid configuration. Please check the device configuration and try again.",
            device_is_being_added=True,
            device_is_being_removed=False,
            device_is_in_sync=False,
        )

    def test_fail_with_device_configuration_error_translate_failure(
        self, error_handler
    ):
        """Test fail_with_device_configuration_error when device translation fails."""
        mock_error = Mock()
        mock_error.__str__ = Mock(return_value="Invalid configuration for device '4'")

        error_handler.device_tracker.translate_device_id_to_device.side_effect = (
            IndexError("Device not found")
        )

        with pytest.raises(AnsibleFailJson) as exc_info:
            error_handler.fail_with_device_configuration_error(mock_error)

        error_handler.module.fail_json.assert_called_once_with(
            msg="A device has an invalid configuration, so the VM cannot be configured.",
            original_error=mock_error,
        )

    def test_fail_with_device_configuration_error_key_error(self, error_handler):
        """Test fail_with_device_configuration_error when device translation raises KeyError."""
        mock_error = Mock()
        mock_error.__str__ = Mock(return_value="Invalid configuration for device '5'")

        error_handler.device_tracker.translate_device_id_to_device.side_effect = (
            KeyError("Device not found")
        )

        with pytest.raises(AnsibleFailJson) as exc_info:
            error_handler.fail_with_device_configuration_error(mock_error)

        error_handler.module.fail_json.assert_called_once_with(
            msg="A device has an invalid configuration, so the VM cannot be configured.",
            original_error=mock_error,
        )

    def test_fail_with_device_configuration_error_invalid_error_format(
        self, error_handler
    ):
        """Test fail_with_device_configuration_error with error that doesn't contain device ID."""
        mock_error = Mock()
        mock_error.__str__ = Mock(return_value="Generic configuration error")

        with pytest.raises(AnsibleFailJson) as exc_info:
            error_handler.fail_with_device_configuration_error(mock_error)

        error_handler.module.fail_json.assert_called_once_with(
            msg="A device has an invalid configuration, so the VM cannot be configured.",
            original_error=mock_error,
        )

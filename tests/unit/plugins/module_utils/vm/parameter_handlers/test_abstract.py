from __future__ import absolute_import, division, print_function

__metaclass__ = type

import pytest
from unittest.mock import Mock
from abc import ABC

from ansible_collections.vmware.vmware.plugins.module_utils.vm.parameter_handlers._abstract import (
    AbstractParameterHandler,
    AbstractDeviceLinkedParameterHandler,
)


class ConcreteParameterHandler(AbstractParameterHandler):
    """Concrete implementation for testing AbstractParameterHandler."""

    HANDLER_NAME = "test_handler"

    def verify_parameter_constraints(self):
        """Test implementation of abstract method."""
        pass

    def populate_config_spec_with_parameters(self, configspec):
        """Test implementation of abstract method."""
        pass

    def compare_live_config_with_desired_config(self):
        """Test implementation of abstract method."""
        pass


class ConcreteDeviceLinkedHandler(AbstractDeviceLinkedParameterHandler):
    """Concrete implementation for testing AbstractDeviceLinkedParameterHandler."""

    HANDLER_NAME = "test_device_handler"

    @property
    def vim_device_class(self):
        """Test implementation of vim_device_class property."""
        return "vim.vm.device.VirtualDevice"

    @property
    def device_type_to_sub_class_map(self):
        """Test implementation of device_type_to_sub_class_map property."""
        return {"test": "TestDevice"}

    def verify_parameter_constraints(self):
        """Test implementation of abstract method."""
        pass

    def populate_config_spec_with_parameters(self, configspec):
        """Test implementation of abstract method."""
        pass

    def compare_live_config_with_desired_config(self):
        """Test implementation of abstract method."""
        pass

    def link_vm_device(self, device):
        """Test implementation of abstract method."""
        pass


class TestAbstractParameterHandler:
    """Test cases for AbstractParameterHandler base class."""

    def test_handler_name_validation(self):
        """Test that HANDLER_NAME must be defined."""
        # Test with None HANDLER_NAME
        with pytest.raises(NotImplementedError, match="must define the HANDLER_NAME attribute"):
            class InvalidHandler(AbstractParameterHandler):
                HANDLER_NAME = None

                def verify_parameter_constraints(self):
                    pass

                def populate_config_spec_with_parameters(self, configspec):
                    pass

                def compare_live_config_with_desired_config(self):
                    pass

            InvalidHandler(Mock(), {}, Mock(), Mock())

        # Test with empty HANDLER_NAME
        with pytest.raises(NotImplementedError, match="must define the HANDLER_NAME attribute"):
            class EmptyHandler(AbstractParameterHandler):
                HANDLER_NAME = ""

                def verify_parameter_constraints(self):
                    pass

                def populate_config_spec_with_parameters(self, configspec):
                    pass

                def compare_live_config_with_desired_config(self):
                    pass

            EmptyHandler(Mock(), {}, Mock(), Mock())

    def test_successful_initialization(self):
        """Test successful initialization with valid parameters."""
        error_handler = Mock()
        params = {"test": "value"}
        change_set = Mock()
        vm = Mock()

        handler = ConcreteParameterHandler(error_handler, params, change_set, vm)

        assert handler.error_handler == error_handler
        assert handler.params == params
        assert handler.change_set == change_set
        assert handler.vm == vm
        assert handler.HANDLER_NAME == "test_handler"
        assert handler.PARAMS_DEFINED_BY_USER is True

    def test_check_if_params_are_defined_by_user_parameter_not_defined(self):
        """Test _check_if_params_are_defined_by_user when parameter is not defined."""
        handler = ConcreteParameterHandler(Mock(), {}, Mock(), None)

        # Test with parameter not defined
        handler._check_if_params_are_defined_by_user("nonexistent_param")
        assert handler.PARAMS_DEFINED_BY_USER is False

    def test_check_if_params_are_defined_by_user_parameter_defined(self):
        """Test _check_if_params_are_defined_by_user when parameter is defined."""
        params = {"test_param": "value"}
        handler = ConcreteParameterHandler(Mock(), params, Mock(), None)

        # Test with parameter defined
        handler._check_if_params_are_defined_by_user("test_param")
        assert handler.PARAMS_DEFINED_BY_USER is True

    def test_check_if_params_are_defined_by_user_required_for_vm_creation_failure(self):
        """Test _check_if_params_are_defined_by_user fails when required for VM creation."""
        error_handler = Mock()
        params = {}
        handler = ConcreteParameterHandler(error_handler, params, Mock(), None)

        # Test failure when parameter is required for VM creation but not defined
        handler._check_if_params_are_defined_by_user("required_param", required_for_vm_creation=True)

        error_handler.fail_with_parameter_error.assert_called_once_with(
            parameter_name="required_param",
            message="The required_param parameter is mandatory for VM creation"
        )
        assert handler.PARAMS_DEFINED_BY_USER is False

    def test_check_if_params_are_defined_by_user_required_for_vm_creation_success(self):
        """Test _check_if_params_are_defined_by_user succeeds when required for VM creation."""
        params = {"required_param": "value"}
        handler = ConcreteParameterHandler(Mock(), params, Mock(), None)

        # Test success when parameter is required for VM creation and is defined
        handler._check_if_params_are_defined_by_user("required_param", required_for_vm_creation=True)

        assert handler.PARAMS_DEFINED_BY_USER is True


class TestAbstractDeviceLinkedParameterHandler:
    """Test cases for AbstractDeviceLinkedParameterHandler base class."""

    def test_successful_device_linked_initialization(self):
        """Test successful initialization with valid device-linked parameters."""
        error_handler = Mock()
        params = {"test": "value"}
        change_set = Mock()
        vm = Mock()
        device_tracker = Mock()

        handler = ConcreteDeviceLinkedHandler(error_handler, params, change_set, vm, device_tracker)

        assert handler.error_handler == error_handler
        assert handler.params == params
        assert handler.change_set == change_set
        assert handler.vm == vm
        assert handler.device_tracker == device_tracker
        assert handler.HANDLER_NAME == "test_device_handler"
        assert handler.vim_device_class == "vim.vm.device.VirtualDevice"
        assert handler.device_type_to_sub_class_map == {"test": "TestDevice"}

    def test_device_type_to_sub_class_map_default(self):
        """Test that device_type_to_sub_class_map defaults to empty dict."""
        class DefaultDeviceHandler(AbstractDeviceLinkedParameterHandler):
            HANDLER_NAME = "default_device"

            @property
            def vim_device_class(self):
                return "vim.vm.device.VirtualDevice"

            def verify_parameter_constraints(self):
                pass

            def populate_config_spec_with_parameters(self, configspec):
                pass

            def compare_live_config_with_desired_config(self):
                pass

            def link_vm_device(self, device):
                pass

        handler = DefaultDeviceHandler(Mock(), {}, Mock(), Mock(), Mock())
        assert handler.device_type_to_sub_class_map == {}


class TestAbstractClassInheritance:
    """Test cases for proper inheritance and ABC behavior."""

    def test_abstract_parameter_handler_is_abc(self):
        """Test that AbstractParameterHandler is an ABC."""
        assert issubclass(AbstractParameterHandler, ABC)

    def test_abstract_device_linked_parameter_handler_is_abc(self):
        """Test that AbstractDeviceLinkedParameterHandler is an ABC."""
        assert issubclass(AbstractDeviceLinkedParameterHandler, ABC)

    def test_abstract_device_linked_inherits_from_abstract_parameter_handler(self):
        """Test that AbstractDeviceLinkedParameterHandler inherits from AbstractParameterHandler."""
        assert issubclass(AbstractDeviceLinkedParameterHandler, AbstractParameterHandler)

    def test_concrete_implementations_can_be_instantiated(self):
        """Test that concrete implementations can be instantiated."""
        # These should not raise any errors
        concrete_handler = ConcreteParameterHandler(Mock(), {}, Mock(), Mock())
        concrete_device_handler = ConcreteDeviceLinkedHandler(Mock(), {}, Mock(), Mock(), Mock())

        assert isinstance(concrete_handler, AbstractParameterHandler)
        assert isinstance(concrete_device_handler, AbstractDeviceLinkedParameterHandler)
        assert isinstance(concrete_device_handler, AbstractParameterHandler)


class TestParameterCheckingEdgeCases:
    """Test edge cases and error conditions."""

    def test_check_if_params_are_defined_by_user_with_empty_string_param(self):
        """Test _check_if_params_are_defined_by_user with empty string parameter value."""
        params = {"test_param": ""}
        handler = ConcreteParameterHandler(Mock(), params, Mock(), None)

        # Empty string should be considered as defined
        handler._check_if_params_are_defined_by_user("test_param")
        assert handler.PARAMS_DEFINED_BY_USER is True

    def test_check_if_params_are_defined_by_user_with_zero_param(self):
        """Test _check_if_params_are_defined_by_user with zero parameter value."""
        params = {"test_param": 0}
        handler = ConcreteParameterHandler(Mock(), params, Mock(), None)

        # Zero should be considered as defined
        handler._check_if_params_are_defined_by_user("test_param")
        assert handler.PARAMS_DEFINED_BY_USER is True

    def test_check_if_params_are_defined_by_user_with_false_param(self):
        """Test _check_if_params_are_defined_by_user with False parameter value."""
        params = {"test_param": False}
        handler = ConcreteParameterHandler(Mock(), params, Mock(), None)

        # False should be considered as defined
        handler._check_if_params_are_defined_by_user("test_param")
        assert handler.PARAMS_DEFINED_BY_USER is True


class TestMockDependencies:
    """Test that mock dependencies work correctly."""

    def test_mock_error_handler_usage(self):
        """Test that mock error handler can be used for testing."""
        error_handler = Mock()
        handler = ConcreteParameterHandler(error_handler, {}, Mock(), None)

        # Test that we can call error handler methods
        handler.error_handler.fail_with_parameter_error("test", "message")
        error_handler.fail_with_parameter_error.assert_called_once_with("test", "message")

    def test_mock_change_set_usage(self):
        """Test that mock change set can be used for testing."""
        change_set = Mock()
        handler = ConcreteParameterHandler(Mock(), {}, change_set, None)

        # Test that we can access change set
        assert handler.change_set == change_set

    def test_mock_device_tracker_usage(self):
        """Test that mock device tracker can be used for testing."""
        device_tracker = Mock()
        handler = ConcreteDeviceLinkedHandler(Mock(), {}, Mock(), Mock(), device_tracker)

        # Test that we can access device tracker
        assert handler.device_tracker == device_tracker

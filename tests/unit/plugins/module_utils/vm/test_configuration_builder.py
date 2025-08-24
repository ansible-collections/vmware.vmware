from __future__ import absolute_import, division, print_function

__metaclass__ = type

import pytest
from unittest.mock import Mock, patch

from ansible_collections.vmware.vmware.plugins.module_utils.vm._configuration_builder import (
    ConfigurationRegistry,
    ConfigurationBuilder,
)
from ansible_collections.vmware.vmware.plugins.module_utils.vm._change_set import (
    ParameterChangeSet,
)


class TestConfigurationRegistry:
    """Test cases for ConfigurationRegistry class."""

    @pytest.fixture
    def registry(self):
        """Create a fresh ConfigurationRegistry instance."""
        return ConfigurationRegistry()

    def test_get_handler_class_success(self, registry):
        """Test successful retrieval of a handler class."""
        a = Mock()
        b = Mock()
        c = Mock()

        registry.device_linked_handler_classes["a"] = a
        registry.vm_aware_handler_classes["b"] = b
        registry.controller_handler_classes["c"] = c

        assert registry.get_handler_class("a") == a
        assert registry.get_handler_class("b") == b
        assert registry.get_handler_class("c") == c

    def test_get_handler_class_not_found(self, registry):
        """Test error handling when handler class is not found."""
        with pytest.raises(ValueError, match="Invalid handler type: nonexistent"):
            registry.get_handler_class("nonexistent")

    def test_multiple_handler_registrations(self, registry):
        """Test registering multiple handlers of different types."""
        controller_handler = Mock()
        controller_handler.HANDLER_NAME = "controller1"
        vm_aware_handler = Mock()
        device_linked_handler = Mock()

        registry.register_controller_handler(controller_handler)
        registry.register_vm_aware_handler(vm_aware_handler, "vm_aware1")
        registry.register_device_linked_handler(device_linked_handler, "device_linked1")

        assert len(registry.controller_handler_classes) == 1
        assert len(registry.vm_aware_handler_classes) == 1
        assert len(registry.device_linked_handler_classes) == 1
        assert registry.controller_handler_classes["controller1"] == controller_handler
        assert registry.vm_aware_handler_classes["vm_aware1"] == vm_aware_handler
        assert (
            registry.device_linked_handler_classes["device_linked1"]
            == device_linked_handler
        )


class TestConfigurationBuilder:
    """Test cases for ConfigurationBuilder class."""

    @pytest.fixture
    def mock_vm(self):
        """Create a mock VM object."""
        return Mock()

    @pytest.fixture
    def mock_module(self):
        """Create a mock Ansible module."""
        module = Mock()
        module.params = {"name": "test_vm", "memory": 1024}
        return module

    @pytest.fixture
    def mock_registry(self):
        """Create a mock configuration registry."""
        return ConfigurationRegistry()

    @pytest.fixture
    def builder(self, mock_vm, mock_module, mock_registry):
        """Create a ConfigurationBuilder instance with mocked dependencies."""
        with patch(
            "ansible_collections.vmware.vmware.plugins.module_utils.vm._configuration_builder.DeviceTracker"
        ) as mock_device_tracker_class, patch(
            "ansible_collections.vmware.vmware.plugins.module_utils.vm._configuration_builder.ErrorHandler"
        ) as mock_error_handler_class, patch(
            "ansible_collections.vmware.vmware.plugins.module_utils.vm._configuration_builder.VmPlacement"
        ) as mock_placement_class:

            mock_device_tracker = Mock()
            mock_error_handler = Mock()
            mock_placement = Mock()

            mock_device_tracker_class.return_value = mock_device_tracker
            mock_error_handler_class.return_value = mock_error_handler
            mock_placement_class.return_value = mock_placement

            builder = ConfigurationBuilder(mock_vm, mock_module, mock_registry)

            # Store the mocked instances for assertions
            builder._mock_device_tracker = mock_device_tracker
            builder._mock_error_handler = mock_error_handler
            builder._mock_placement = mock_placement

            return builder

    def test_create_configurator(self, builder):
        """Test ConfigurationBuilder initialization."""
        configurator = builder.create_configurator()
        assert configurator.device_tracker == builder._mock_device_tracker
        assert configurator.vm == builder.vm
        assert configurator.controller_handlers == builder._controller_handlers
        assert configurator.handlers == []
        assert isinstance(configurator.change_set, ParameterChangeSet)

    def test_create_change_set(self, builder):
        """Test _create_change_set method."""
        change_set = builder._create_change_set()
        assert change_set.params == builder.module.params
        assert change_set.vm == builder.vm
        assert change_set.error_handler == builder.error_handler

    def test_create_controller_handlers_empty_registry(self, builder):
        """Test _create_controller_handlers with empty registry."""
        result = builder._create_controller_handlers()

        assert result == []
        assert builder._controller_handlers == []

    def test_create_controller_handlers_with_registered_handlers(
        self, builder, mock_registry
    ):
        """Test _create_controller_handlers with registered handlers."""
        mock_handler_class1 = Mock()
        mock_handler_class2 = Mock()
        mock_handler1 = Mock()
        mock_handler2 = Mock()

        mock_handler_class1.return_value = mock_handler1
        mock_handler_class2.return_value = mock_handler2

        mock_registry.controller_handler_classes = {
            "controller1": mock_handler_class1,
            "controller2": mock_handler_class2,
        }

        with patch.object(builder, "_create_change_set") as mock_create_change_set:
            mock_change_set = Mock()
            mock_create_change_set.return_value = mock_change_set

            result = builder._create_controller_handlers()

            assert result == [mock_handler1, mock_handler2]
            assert builder._controller_handlers == [mock_handler1, mock_handler2]

            # Verify handlers were created with correct parameters
            mock_handler_class1.assert_called_once_with(
                error_handler=builder.error_handler,
                params=builder.module.params,
                change_set=mock_change_set,
                device_tracker=builder.device_tracker,
            )
            mock_handler_class2.assert_called_once_with(
                error_handler=builder.error_handler,
                params=builder.module.params,
                change_set=mock_change_set,
                device_tracker=builder.device_tracker,
            )

        # check cached handlers are not recreated
        before_length = len(builder._controller_handlers)
        builder._create_controller_handlers()
        assert len(builder._controller_handlers) == before_length

    def test_create_non_controller_handlers_empty_registry(self, builder):
        """Test _create_non_controller_handlers with empty registry."""
        result = builder._create_non_controller_handlers()

        assert result == []

    def test_create_non_controller_handlers(self, builder, mock_registry):
        """Test _create_non_controller_handlers with both handler types."""
        mock_device_linked_class = Mock()
        mock_vm_aware_class = Mock()
        mock_device_linked_handler = Mock()
        mock_vm_aware_handler = Mock()

        mock_device_linked_class.return_value = mock_device_linked_handler
        mock_vm_aware_class.return_value = mock_vm_aware_handler

        mock_registry.device_linked_handler_classes = {
            "device_linked1": mock_device_linked_class
        }
        mock_registry.vm_aware_handler_classes = {"vm_aware1": mock_vm_aware_class}

        with patch.object(
            builder, "_create_change_set"
        ) as mock_create_change_set, patch.object(
            builder, "_create_controller_handlers"
        ) as mock_create_controller_handlers:

            mock_change_set = Mock()
            mock_controller_handlers = [Mock()]

            mock_create_change_set.return_value = mock_change_set
            mock_create_controller_handlers.return_value = mock_controller_handlers

            result = builder._create_non_controller_handlers()

            assert result == [mock_device_linked_handler, mock_vm_aware_handler]

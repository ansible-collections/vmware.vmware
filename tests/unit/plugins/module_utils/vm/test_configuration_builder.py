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

    def test_register_controller_handler_without_name(self, registry):
        """Test registering a controller handler without specifying a name."""
        controller_handler = Mock()
        controller_handler.HANDLER_NAME = "auto_name"

        registry.register_controller_handler(controller_handler)

        assert registry.controller_handler_classes["auto_name"] == controller_handler

    def test_register_vm_aware_handler_without_name(self, registry):
        """Test registering a VM aware handler without specifying a name."""
        vm_aware_handler = Mock()
        vm_aware_handler.HANDLER_NAME = "auto_vm_name"

        registry.register_vm_aware_handler(vm_aware_handler)

        assert registry.vm_aware_handler_classes["auto_vm_name"] == vm_aware_handler

    def test_register_device_linked_handler_without_name(self, registry):
        """Test registering a device linked handler without specifying a name."""
        device_linked_handler = Mock()
        device_linked_handler.HANDLER_NAME = "auto_device_name"

        registry.register_device_linked_handler(device_linked_handler)

        assert registry.device_linked_handler_classes["auto_device_name"] == device_linked_handler

    def test_register_handlers_without_name(self, registry):
        """Test registering handlers without specifying names (uses HANDLER_NAME)."""
        # Test all three handler types with auto-naming
        for handler_type, register_method in [
            ("controller", registry.register_controller_handler),
            ("vm_aware", registry.register_vm_aware_handler),
            ("device_linked", registry.register_device_linked_handler)
        ]:
            handler = Mock()
            handler.HANDLER_NAME = f"auto_{handler_type}_name"

            register_method(handler)

            # Verify it was registered with the auto-generated name
            if handler_type == "controller":
                assert registry.controller_handler_classes["auto_controller_name"] == handler
            elif handler_type == "vm_aware":
                assert registry.vm_aware_handler_classes["auto_vm_aware_name"] == handler
            else:
                assert registry.device_linked_handler_classes["auto_device_linked_name"] == handler


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
        ) as mock_placement_class, patch(
            "ansible_collections.vmware.vmware.plugins.module_utils.vm._configuration_builder.VsphereObjectCache"
        ) as mock_vsphere_object_cache_class:

            mock_device_tracker = Mock()
            mock_error_handler = Mock()
            mock_placement = Mock()
            mock_vsphere_object_cache = Mock()

            mock_device_tracker_class.return_value = mock_device_tracker
            mock_error_handler_class.return_value = mock_error_handler
            mock_placement_class.return_value = mock_placement
            mock_vsphere_object_cache_class.return_value = mock_vsphere_object_cache

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
                vm=builder.vm,
                device_tracker=builder.device_tracker,
            )
            mock_handler_class2.assert_called_once_with(
                error_handler=builder.error_handler,
                params=builder.module.params,
                change_set=mock_change_set,
                vm=builder.vm,
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

    def test_add_handler_if_params_are_defined_by_user(self, builder):
        """Test _add_handler_if_params_are_defined_by_user method."""
        handler_list = []

        # Test True case
        handler_true = Mock()
        handler_true.PARAMS_DEFINED_BY_USER = True
        builder._add_handler_if_params_are_defined_by_user(handler_true, handler_list)
        assert handler_list == [handler_true]

        # Test False case
        handler_false = Mock()
        handler_false.PARAMS_DEFINED_BY_USER = False
        builder._add_handler_if_params_are_defined_by_user(handler_false, handler_list)
        assert handler_list == [handler_true]  # Only the True one should be added

    def test_handler_filtering_in_creation_methods(self, builder, mock_registry):
        """Test that handlers are only added when PARAMS_DEFINED_BY_USER is True."""
        # Set up handlers with different PARAMS_DEFINED_BY_USER values
        mock_handler_true = Mock()
        mock_handler_true.PARAMS_DEFINED_BY_USER = True

        mock_handler_false = Mock()
        mock_handler_false.PARAMS_DEFINED_BY_USER = False

        # Test controller handlers
        mock_registry.controller_handler_classes = {"ctrl": Mock(return_value=mock_handler_true)}
        result = builder._create_controller_handlers()
        assert result == [mock_handler_true]

        # Test non-controller handlers
        mock_registry.device_linked_handler_classes = {"device": Mock(return_value=mock_handler_false)}
        mock_registry.vm_aware_handler_classes = {"vm": Mock(return_value=mock_handler_true)}

        result = builder._create_non_controller_handlers()
        assert result == [mock_handler_true]  # Only the True one should be added

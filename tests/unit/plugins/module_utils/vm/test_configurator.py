from __future__ import absolute_import, division, print_function

__metaclass__ = type

import pytest
from unittest.mock import Mock, patch

from ansible_collections.vmware.vmware.plugins.module_utils.vm._configurator import (
    Configurator,
)
from ansible_collections.vmware.vmware.plugins.module_utils.vm._change_set import ParameterChangeSet


class TestConfigurator:
    """Test cases for Configurator class."""

    @pytest.fixture
    def mock_device_tracker(self):
        """Create a mock device tracker."""
        return Mock()

    @pytest.fixture
    def mock_vm(self):
        """Create a mock VM object."""
        vm = Mock()
        vm.config.hardware.device = []
        return vm

    @pytest.fixture
    def mock_controller_handlers(self):
        """Create mock controller handlers."""
        out = []
        for i in range(2):
            handler = Mock()
            handler.change_set = ParameterChangeSet(Mock(), Mock(), Mock())
            out.append(handler)
        return out

    @pytest.fixture
    def mock_handlers(self):
        """Create mock non-controller handlers."""
        out = []
        for i in range(2):
            handler = Mock()
            handler.change_set = ParameterChangeSet(Mock(), Mock(), Mock())
            out.append(handler)
        return out

    @pytest.fixture
    def mock_change_set(self):
        """Create a mock change set."""
        return ParameterChangeSet(Mock(), Mock(), Mock())

    @pytest.fixture
    def configurator(
        self,
        mock_device_tracker,
        mock_vm,
        mock_controller_handlers,
        mock_handlers,
        mock_change_set,
    ):
        """Create a Configurator instance with mocked dependencies."""
        return Configurator(
            device_tracker=mock_device_tracker,
            vm=mock_vm,
            controller_handlers=mock_controller_handlers,
            handlers=mock_handlers,
            change_set=mock_change_set,
        )

    def test_init(
        self,
        mock_device_tracker,
        mock_vm,
        mock_controller_handlers,
        mock_handlers,
        mock_change_set,
    ):
        """Test Configurator initialization."""
        configurator = Configurator(
            device_tracker=mock_device_tracker,
            vm=mock_vm,
            controller_handlers=mock_controller_handlers,
            handlers=mock_handlers,
            change_set=mock_change_set,
        )

        assert configurator.device_tracker == mock_device_tracker
        assert configurator.vm == mock_vm
        assert configurator.controller_handlers == mock_controller_handlers
        assert configurator.handlers == mock_handlers
        assert configurator.change_set == mock_change_set
        assert configurator.all_handlers == mock_controller_handlers + mock_handlers

    def test_prepare_parameter_handlers(self, configurator):
        """Test prepare_parameter_handlers method."""
        configurator._link_vm_devices_to_handlers = Mock(return_value=[1])
        configurator.prepare_parameter_handlers()

        for handler in configurator.all_handlers:
            handler.verify_parameter_constraints.assert_called_once()

        configurator._link_vm_devices_to_handlers.assert_called_once()
        assert configurator.change_set.objects_to_remove == [1]

    def test_stage_configuration_changes_no_changes(self, configurator):
        """Test stage_configuration_changes with no changes required."""
        result = configurator.stage_configuration_changes()

        # Verify all handlers were compared
        for handler in configurator.all_handlers:
            handler.compare_live_config_with_desired_config.assert_called_once()

        assert result.are_changes_required() is False
        assert result.power_cycle_required is False
        assert result.objects_to_remove == []

    def test_stage_configuration_changes_with_objects_to_remove(self, configurator):
        """Test stage_configuration_changes with unlinked devices."""
        configurator.change_set.objects_to_remove = [Mock()]
        configurator.stage_configuration_changes()

        assert configurator.change_set.are_changes_required() is True

    def test_apply_staged_changes_to_config_spec(self, configurator):
        """Test apply_staged_changes_to_config_spec method."""
        config_spec = Mock()
        config_spec.deviceChange = []

        configurator._create_device_removal_spec = Mock(return_value=True)
        unlinked_device = Mock()
        configurator.change_set.objects_to_remove = [unlinked_device]

        # Mock handlers with changes
        handler_with_changes = Mock()
        handler_with_changes.change_set.are_changes_required() = True
        handler_without_changes = Mock()
        handler_without_changes.change_set.are_changes_required() = False
        configurator.all_handlers = [handler_with_changes, handler_without_changes]

        configurator.apply_staged_changes_to_config_spec(config_spec)

        # Verify device tracker was called for unlinked device
        configurator.device_tracker.track_device_id_from_spec.assert_called_with(
            unlinked_device
        )

        # Verify device removal spec was added
        assert len(config_spec.deviceChange) == 1
        assert config_spec.deviceChange[0] is True

        # Verify only handler with changes was called
        handler_with_changes.populate_config_spec_with_parameters.assert_called_with(
            config_spec
        )
        handler_without_changes.populate_config_spec_with_parameters.assert_not_called()

    @patch(
        "ansible_collections.vmware.vmware.plugins.module_utils.vm._configurator.vim"
    )
    def test_create_device_removal_spec(self, mock_vim, configurator):
        """Test _create_device_removal_spec method."""
        device = Mock()
        mock_spec = Mock()
        mock_vim.vm.device.VirtualDeviceSpec.return_value = mock_spec

        result = configurator._create_device_removal_spec(device)

        # Verify spec was created correctly
        mock_vim.vm.device.VirtualDeviceSpec.assert_called_once()
        assert isinstance(mock_spec.operation, Mock)
        assert mock_spec.device == device
        assert result == mock_spec

    def test_link_vm_devices_to_handlers_no_vm(self, configurator):
        """Test _link_vm_devices_to_handlers with no VM."""
        configurator.vm = None

        result = configurator._link_vm_devices_to_handlers()

        assert result == []

    def test_link_vm_devices_to_handlers_no_devices(self, configurator):
        """Test _link_vm_devices_to_handlers with no devices."""
        configurator.vm.config.hardware.device = []

        result = configurator._link_vm_devices_to_handlers()

        assert result == []

    def test_link_vm_devices_to_handlers_successful_link(self, configurator):
        """Test _link_vm_devices_to_handlers with successful device linking."""
        device = Mock()
        configurator.vm.config.hardware.device = [device]

        handler = Mock()
        handler.vim_device_class = type(device)
        handler.link_vm_device = Mock()
        configurator.all_handlers = [handler]

        result = configurator._link_vm_devices_to_handlers()

        handler.link_vm_device.assert_called_with(device)
        assert result == []

    def test_link_vm_devices_to_handlers_link_failure(self, configurator):
        """Test _link_vm_devices_to_handlers when device linking fails."""
        device = Mock()
        configurator.vm.config.hardware.device = [device]

        handler = Mock()
        handler.vim_device_class = type(device)
        handler.link_vm_device = Mock(side_effect=Exception("Link failed"))
        configurator.all_handlers = [handler]

        result = configurator._link_vm_devices_to_handlers()

        assert result == [device]

    def test_link_vm_devices_to_handlers_no_matching_handler(self, configurator):
        """Test _link_vm_devices_to_handlers with no matching handler."""
        device = Mock()
        configurator.vm.config.hardware.device = [device]

        handler = Mock()
        handler.vim_device_class = type(Mock())  # Different type
        configurator.all_handlers = [handler]

        result = configurator._link_vm_devices_to_handlers()

        assert result == []

    def test_link_vm_devices_to_handlers_handler_without_vim_device_class(
        self, configurator
    ):
        """Test _link_vm_devices_to_handlers with handler without vim_device_class."""
        device = Mock()
        configurator.vm.config.hardware.device = [device]

        handler = Mock()
        del handler.vim_device_class  # Remove the attribute
        configurator.all_handlers = [handler]

        result = configurator._link_vm_devices_to_handlers()

        assert result == []

    def test_link_vm_devices_to_handlers_multiple_devices(self, configurator):
        """Test _link_vm_devices_to_handlers with multiple devices."""
        device1 = Mock()
        device2 = Mock()
        configurator.vm.config.hardware.device = [device1, device2]

        handler1 = Mock()
        handler1.vim_device_class = type(device1)
        handler1.link_vm_device = Mock()

        handler2 = Mock()
        handler2.vim_device_class = type(device2)
        handler2.link_vm_device = Mock(side_effect=Exception("Link failed"))

        configurator.all_handlers = [handler1, handler2]

        result = configurator._link_vm_devices_to_handlers()

        handler1.link_vm_device.assert_called_with(device1)
        handler2.link_vm_device.assert_called_with(device2)
        assert result == [device2]  # Only device2 failed to link

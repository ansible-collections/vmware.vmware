from __future__ import absolute_import, division, print_function

__metaclass__ = type

import pytest
from unittest.mock import Mock, patch

from ansible_collections.vmware.vmware.plugins.module_utils.vm.parameter_handlers._memory import (
    MemoryParameterHandler,
)
from ansible_collections.vmware.vmware.plugins.module_utils.vm._change_set import (
    PowerCycleRequiredError,
)


class TestMemoryParameterHandler:
    @pytest.fixture
    def memory_parameter_handler(self):
        return MemoryParameterHandler(Mock(), {}, Mock(), Mock())

    @pytest.fixture
    def allocation(self):
        mock_allocation = Mock()
        mock_allocation.limit, mock_allocation.reservation, mock_allocation.shares = (
            None,
            None,
            None,
        )

        return mock_allocation

    @pytest.fixture
    def shares_info(self):
        mock_shares_info = Mock()
        mock_shares_info.shares, mock_shares_info.level = None, None

        return mock_shares_info

    def test_verify_parameter_constraints_new_vm(self, memory_parameter_handler):
        """Test parameter constraints validation for new VM creation."""
        memory_parameter_handler.vm = None
        memory_parameter_handler.memory_params = {}
        memory_parameter_handler.verify_parameter_constraints()
        assert (
            memory_parameter_handler.error_handler.fail_with_parameter_error.call_count
            == 1
        )

        memory_parameter_handler.memory_params = {"size_mb": 1024}
        memory_parameter_handler.verify_parameter_constraints()
        # check it was not called again
        assert (
            memory_parameter_handler.error_handler.fail_with_parameter_error.call_count
            == 1
        )

    def test_verify_parameter_constraints_existing_vm(self, memory_parameter_handler):
        """Test parameter constraints validation for existing VM."""
        memory_parameter_handler.vm = Mock()
        memory_parameter_handler.vm.config.hardware.memoryMB = 2048
        memory_parameter_handler.error_handler.fail_with_parameter_error.side_effect = (
            Exception("test")
        )

        # Test memory decrease (should fail)
        memory_parameter_handler.memory_params = {"size_mb": 1024}
        with pytest.raises(Exception, match="test"):
            memory_parameter_handler.verify_parameter_constraints()

        # Test memory increase (should pass)
        memory_parameter_handler.memory_params = {"size_mb": 4096}
        memory_parameter_handler.verify_parameter_constraints()

        # Test same memory size (should pass)
        memory_parameter_handler.memory_params = {"size_mb": 2048}
        memory_parameter_handler.verify_parameter_constraints()

    def test_populate_config_spec_with_parameters(self, memory_parameter_handler):
        """Test populating config spec with memory parameters."""
        configspec = Mock()
        memory_parameter_handler.memory_params = {
            "size_mb": 2048,
            "enable_hot_add": True,
        }
        memory_parameter_handler._populate_config_spec_with_memory_allocation_parameters = (
            Mock()
        )
        memory_parameter_handler.populate_config_spec_with_parameters(configspec)
        assert configspec.memoryMB == 2048
        assert configspec.memoryHotAddEnabled is True
        memory_parameter_handler._populate_config_spec_with_memory_allocation_parameters.assert_called_once_with(
            configspec
        )

    def test_populate_config_spec_with_partial_parameters(
        self, memory_parameter_handler
    ):
        """Test populating config spec with only some memory parameters."""
        configspec = Mock()
        memory_parameter_handler.memory_params = {"size_mb": 1024}
        memory_parameter_handler.populate_config_spec_with_parameters(configspec)
        assert configspec.memoryMB == 1024

    def test_compare_live_config_with_desired_config(self, memory_parameter_handler):
        """Test comparing live config with desired config."""
        memory_parameter_handler._check_memory_changes_with_hot_add = Mock()
        memory_parameter_handler.compare_live_config_with_desired_config()
        assert (
            memory_parameter_handler.change_set.check_if_change_is_required.call_count
            == 6
        )

    def test_check_memory_changes_with_hot_add(self, memory_parameter_handler):
        """Test checking memory changes with hot-add capability."""
        memory_parameter_handler.change_set.check_if_change_is_required = Mock()
        memory_parameter_handler._check_memory_changes_with_hot_add()
        assert (
            memory_parameter_handler.change_set.check_if_change_is_required.call_count
            == 1
        )

    def test_check_memory_changes_with_hot_add_enabled(self, memory_parameter_handler):
        """Test memory changes when hot-add is enabled."""
        memory_parameter_handler.change_set.check_if_change_is_required = Mock(
            side_effect=PowerCycleRequiredError
        )
        memory_parameter_handler.vm = Mock()

        # Test memory increase with hot-add enabled
        memory_parameter_handler.vm.config.hardware.memoryMB = 1024
        memory_parameter_handler.memory_params = {"size_mb": 2048}
        memory_parameter_handler.vm.config.memoryHotAddEnabled = True
        memory_parameter_handler._check_memory_changes_with_hot_add()
        memory_parameter_handler.error_handler.fail_with_power_cycle_error.assert_not_called()
        assert memory_parameter_handler.change_set.power_cycle_required is False

    def test_check_memory_changes_with_hot_add_disabled(self, memory_parameter_handler):
        """Test memory changes when hot-add is disabled."""
        memory_parameter_handler.change_set.check_if_change_is_required = Mock(
            side_effect=PowerCycleRequiredError
        )
        memory_parameter_handler.vm = Mock()

        # Test memory increase with hot-add disabled
        memory_parameter_handler.vm.config.hardware.memoryMB = 1024
        memory_parameter_handler.memory_params = {"size_mb": 2048}
        memory_parameter_handler.vm.config.memoryHotAddEnabled = False
        memory_parameter_handler._check_memory_changes_with_hot_add()
        memory_parameter_handler.error_handler.fail_with_power_cycle_error.assert_called_once()
        memory_parameter_handler.error_handler.fail_with_power_cycle_error.reset_mock()

        # Test memory decrease (should not trigger hot-add check)
        memory_parameter_handler.vm.config.hardware.memoryMB = 2048
        memory_parameter_handler.memory_params = {"size_mb": 1024}
        memory_parameter_handler._check_memory_changes_with_hot_add()
        # Should not call fail_with_power_cycle_error for memory decrease
        memory_parameter_handler.error_handler.fail_with_power_cycle_error.assert_not_called()

    def test_check_memory_changes_no_change(self, memory_parameter_handler):
        """Test memory changes when no change is required."""
        memory_parameter_handler.change_set.check_if_change_is_required = Mock()
        memory_parameter_handler.vm = Mock()

        # Test same memory size
        memory_parameter_handler.vm.config.hardware.memoryMB = 1024
        memory_parameter_handler.memory_params = {"size_mb": 1024}
        memory_parameter_handler._check_memory_changes_with_hot_add()
        memory_parameter_handler.error_handler.fail_with_power_cycle_error.assert_not_called()

    def test_verify_parameter_constraints_no_memory_params(
        self, memory_parameter_handler
    ):
        """Test parameter constraints with no memory parameters."""
        memory_parameter_handler.vm = None
        memory_parameter_handler.memory_params = {}
        memory_parameter_handler.verify_parameter_constraints()
        assert (
            memory_parameter_handler.error_handler.fail_with_parameter_error.call_count
            == 1
        )

    def test_verify_parameter_constraints_existing_vm_no_memory_params(
        self, memory_parameter_handler
    ):
        """Test parameter constraints for existing VM with no memory parameters."""
        memory_parameter_handler.vm = Mock()
        memory_parameter_handler.vm.config.hardware.memoryMB = 2048
        memory_parameter_handler.memory_params = {}
        memory_parameter_handler.verify_parameter_constraints()
        # Should not call fail_with_parameter_error when no memory params provided
        assert (
            memory_parameter_handler.error_handler.fail_with_parameter_error.call_count
            == 0
        )

    @patch(
        "ansible_collections.vmware.vmware.plugins.module_utils.vm.parameter_handlers._memory.vim.ResourceAllocationInfo"
    )
    @patch(
        "ansible_collections.vmware.vmware.plugins.module_utils.vm.parameter_handlers._memory.vim.SharesInfo"
    )
    def test__populate_config_spec_with_memory_allocation_parameters_all(
        self,
        mock_shares_info,
        mock_resource_allocation_info,
        memory_parameter_handler,
        allocation,
        shares_info,
    ):
        configspec = Mock()
        mock_resource_allocation_info.return_value = allocation
        mock_shares_info.return_value = shares_info
        configspec.memoryAllocation = None

        memory_parameter_handler.memory_params = dict(
            shares_level="low", shares=10, limit=10, reservation=10
        )
        memory_parameter_handler._populate_config_spec_with_memory_allocation_parameters(
            configspec
        )
        assert configspec.memoryAllocation is allocation
        assert configspec.memoryAllocation.shares is shares_info
        assert configspec.memoryAllocation.limit == 10
        assert configspec.memoryAllocation.reservation == 10
        assert configspec.memoryAllocation.shares.level == "custom"
        assert configspec.memoryAllocation.shares.shares == 10

    @patch(
        "ansible_collections.vmware.vmware.plugins.module_utils.vm.parameter_handlers._memory.vim.ResourceAllocationInfo"
    )
    @patch(
        "ansible_collections.vmware.vmware.plugins.module_utils.vm.parameter_handlers._memory.vim.SharesInfo"
    )
    def test__populate_config_spec_with_memory_allocation_parameters_only_shares_level(
        self,
        mock_shares_info,
        mock_resource_allocation_info,
        memory_parameter_handler,
        allocation,
        shares_info,
    ):
        configspec = Mock()
        mock_resource_allocation_info.return_value = allocation
        mock_shares_info.return_value = shares_info
        configspec.memoryAllocation = None

        memory_parameter_handler.memory_params = dict(shares_level="low")
        memory_parameter_handler._populate_config_spec_with_memory_allocation_parameters(
            configspec
        )
        assert configspec.memoryAllocation is allocation
        assert configspec.memoryAllocation.shares is shares_info
        assert configspec.memoryAllocation.limit is None
        assert configspec.memoryAllocation.reservation is None
        assert configspec.memoryAllocation.shares.level == "low"
        assert configspec.memoryAllocation.shares.shares is None

    @patch(
        "ansible_collections.vmware.vmware.plugins.module_utils.vm.parameter_handlers._memory.vim.ResourceAllocationInfo"
    )
    @patch(
        "ansible_collections.vmware.vmware.plugins.module_utils.vm.parameter_handlers._memory.vim.SharesInfo"
    )
    def test__populate_config_spec_with_memory_allocation_parameters_only_limit(
        self,
        mock_shares_info,
        mock_resource_allocation_info,
        memory_parameter_handler,
        allocation,
        shares_info,
    ):
        configspec = Mock()
        mock_resource_allocation_info.return_value = allocation
        mock_shares_info.return_value = shares_info
        configspec.memoryAllocation = None

        memory_parameter_handler.memory_params = dict(limit=10)
        memory_parameter_handler._populate_config_spec_with_memory_allocation_parameters(
            configspec
        )
        assert configspec.memoryAllocation is allocation
        assert configspec.memoryAllocation.shares is None
        assert configspec.memoryAllocation.limit == 10
        assert configspec.memoryAllocation.reservation is None

    def test__populate_config_spec_with_memory_allocation_parameters_no_params(
        self, memory_parameter_handler
    ):
        configspec = Mock()
        configspec.memoryAllocation = None

        memory_parameter_handler._populate_config_spec_with_memory_allocation_parameters(
            configspec
        )
        assert configspec.memoryAllocation is None

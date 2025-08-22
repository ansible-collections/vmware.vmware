from __future__ import absolute_import, division, print_function

__metaclass__ = type

import pytest
from unittest.mock import Mock

from ansible_collections.vmware.vmware.plugins.module_utils.vm.parameter_handlers._cpu_memory import (
    CpuParameterHandler,
    MemoryParameterHandler,
)
from ansible_collections.vmware.vmware.plugins.module_utils.vm._change_set import (
    PowerCycleRequiredError,
)


class TestCpuParameterHandler:
    @pytest.fixture
    def cpu_parameter_handler(self):
        return CpuParameterHandler(Mock(), {}, Mock(), Mock())

    def test_verify_parameter_constraints(self, cpu_parameter_handler):
        cpu_parameter_handler._validate_cpu_socket_relationship = Mock()
        cpu_parameter_handler._validate_params_for_creation = Mock()

        cpu_parameter_handler.vm = None
        cpu_parameter_handler.verify_parameter_constraints()
        assert cpu_parameter_handler._validate_cpu_socket_relationship.call_count == 1
        assert cpu_parameter_handler._validate_params_for_creation.call_count == 1

        cpu_parameter_handler.vm = Mock()
        cpu_parameter_handler.verify_parameter_constraints()
        assert cpu_parameter_handler._validate_cpu_socket_relationship.call_count == 2
        assert cpu_parameter_handler._validate_params_for_creation.call_count == 1

    @pytest.mark.parametrize(
        "cores, cores_per_socket, expected_error_count",
        [
            (None, None, 0),
            (1, 1, 0),
            (4, 1, 0),
            (4, 3, 1),
        ],
    )
    def test_validate_cpu_socket_relationship(
        self, cpu_parameter_handler, cores, cores_per_socket, expected_error_count
    ):
        if cores is not None:
            cpu_parameter_handler.cpu_params = {
                "cores": cores,
                "cores_per_socket": cores_per_socket,
            }
        cpu_parameter_handler._validate_cpu_socket_relationship()
        assert (
            cpu_parameter_handler.error_handler.fail_with_parameter_error.call_count
            == expected_error_count
        )

    def test_validate_params_for_creation(self, cpu_parameter_handler):
        cpu_parameter_handler.cpu_params = {}
        cpu_parameter_handler._validate_cpu_socket_relationship = Mock()
        cpu_parameter_handler._validate_params_for_creation()
        assert (
            cpu_parameter_handler.error_handler.fail_with_parameter_error.call_count
            == 1
        )

        cpu_parameter_handler.cpu_params = {"cores": 4}
        cpu_parameter_handler._validate_params_for_creation()
        # check it was not called again
        assert (
            cpu_parameter_handler.error_handler.fail_with_parameter_error.call_count
            == 1
        )

    def test_populate_config_spec_with_parameters(self, cpu_parameter_handler):
        configspec = Mock()
        cpu_parameter_handler.cpu_params = {"cores": 4}
        cpu_parameter_handler.populate_config_spec_with_parameters(configspec)
        assert configspec.numCPUs == 4

    def test_compare_live_config_with_desired_config(self, cpu_parameter_handler):
        cpu_parameter_handler._check_cpu_changes_with_hot_add_remove = Mock()
        cpu_parameter_handler.compare_live_config_with_desired_config()
        assert (
            cpu_parameter_handler.change_set.check_if_change_is_required.call_count > 1
        )

    def test_check_cpu_changes_with_hot_add_remove(self, cpu_parameter_handler):
        cpu_parameter_handler.change_set.check_if_change_is_required = Mock()
        cpu_parameter_handler._check_cpu_changes_with_hot_add_remove()
        assert (
            cpu_parameter_handler.change_set.check_if_change_is_required.call_count == 1
        )

    def test_check_cpu_changes_with_hot_add(self, cpu_parameter_handler):
        cpu_parameter_handler.change_set.check_if_change_is_required = Mock(
            side_effect=PowerCycleRequiredError
        )
        cpu_parameter_handler.vm = Mock()

        cpu_parameter_handler.vm.config.hardware.numCPU = 4
        cpu_parameter_handler.cpu_params = {"cores": 4}
        cpu_parameter_handler.vm.config.cpuHotAddEnabled = False
        cpu_parameter_handler._check_cpu_changes_with_hot_add_remove()
        cpu_parameter_handler.error_handler.fail_with_power_cycle_error.assert_not_called()
        assert cpu_parameter_handler.change_set.power_cycle_required is False

        cpu_parameter_handler.vm.config.hardware.numCPU = 2
        cpu_parameter_handler.cpu_params = {"cores": 4}

        cpu_parameter_handler.vm.config.cpuHotAddEnabled = True
        cpu_parameter_handler._check_cpu_changes_with_hot_add_remove()
        cpu_parameter_handler.error_handler.fail_with_power_cycle_error.assert_not_called()

        cpu_parameter_handler.vm.config.cpuHotAddEnabled = False
        cpu_parameter_handler._check_cpu_changes_with_hot_add_remove()
        cpu_parameter_handler.error_handler.fail_with_power_cycle_error.assert_called_once()

    def test_check_cpu_changes_with_hot_remove(self, cpu_parameter_handler):
        cpu_parameter_handler.change_set.check_if_change_is_required = Mock(
            side_effect=PowerCycleRequiredError
        )
        cpu_parameter_handler.vm = Mock()

        cpu_parameter_handler.vm.config.hardware.numCPU = 4
        cpu_parameter_handler.cpu_params = {"cores": 4}
        cpu_parameter_handler.vm.config.cpuHotRemoveEnabled = False
        cpu_parameter_handler._check_cpu_changes_with_hot_add_remove()
        cpu_parameter_handler.error_handler.fail_with_power_cycle_error.assert_not_called()
        assert cpu_parameter_handler.change_set.power_cycle_required is False

        cpu_parameter_handler.vm.config.hardware.numCPU = 4
        cpu_parameter_handler.cpu_params = {"cores": 2}

        cpu_parameter_handler.vm.config.cpuHotRemoveEnabled = True
        cpu_parameter_handler._check_cpu_changes_with_hot_add_remove()
        cpu_parameter_handler.error_handler.fail_with_power_cycle_error.assert_not_called()

        cpu_parameter_handler.vm.config.cpuHotRemoveEnabled = False
        cpu_parameter_handler._check_cpu_changes_with_hot_add_remove()
        cpu_parameter_handler.error_handler.fail_with_power_cycle_error.assert_called_once()


class TestMemoryParameterHandler:
    @pytest.fixture
    def memory_parameter_handler(self):
        return MemoryParameterHandler(Mock(), {}, Mock(), Mock())

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

        # Test memory decrease (should fail)
        memory_parameter_handler.memory_params = {"size_mb": 1024}
        memory_parameter_handler.verify_parameter_constraints()
        assert (
            memory_parameter_handler.error_handler.fail_with_parameter_error.call_count
            == 1
        )

        # Test memory increase (should pass)
        memory_parameter_handler.memory_params = {"size_mb": 4096}
        memory_parameter_handler.verify_parameter_constraints()
        # check it was not called again
        assert (
            memory_parameter_handler.error_handler.fail_with_parameter_error.call_count
            == 1
        )

        # Test same memory size (should pass)
        memory_parameter_handler.memory_params = {"size_mb": 2048}
        memory_parameter_handler.verify_parameter_constraints()
        # check it was not called again
        assert (
            memory_parameter_handler.error_handler.fail_with_parameter_error.call_count
            == 1
        )

    def test_populate_config_spec_with_parameters(self, memory_parameter_handler):
        """Test populating config spec with memory parameters."""
        configspec = Mock()
        memory_parameter_handler.memory_params = {
            "size_mb": 2048,
            "enable_hot_add": True,
        }
        memory_parameter_handler.populate_config_spec_with_parameters(configspec)
        assert configspec.memoryMB == 2048
        assert configspec.memoryHotAddEnabled is True

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
            == 1
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

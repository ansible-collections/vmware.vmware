from __future__ import absolute_import, division, print_function

__metaclass__ = type

import pytest
from unittest.mock import Mock

from ansible_collections.vmware.vmware.plugins.module_utils.vm._change_set import (
    ParameterChangeSet,
    PowerCycleRequiredError,
)


class TestPowerCycleRequiredError:
    """Test cases for PowerCycleRequiredError exception."""

    def test_exception_creation(self):
        """Test creating PowerCycleRequiredError with parameter name."""
        error = PowerCycleRequiredError("cpu.cores")
        assert str(error) == "cpu.cores"
        assert error.args[0] == "cpu.cores"


class TestParameterChangeSet:
    """Test cases for ParameterChangeSet class."""

    @pytest.fixture
    def change_set(self):
        return ParameterChangeSet({}, Mock(), Mock())

    def test_init(self):
        """Test initialization."""
        change_set = ParameterChangeSet({}, Mock(), Mock())
        assert change_set.changes_required is False
        assert change_set.power_cycle_required is False

        change_set = ParameterChangeSet({}, None, Mock())
        assert change_set.changes_required is True
        assert change_set.power_cycle_required is False

    def test_check_if_change_is_required(self, change_set):
        change_set.vm = None
        change_set._check_if_param_differs_from_vm = Mock(return_value=None)
        change_set._check_if_change_violates_power_state = Mock(return_value=None)

        change_set.check_if_change_is_required("cpu.cores", "config.hardware.numCPU")
        change_set._check_if_param_differs_from_vm.assert_not_called()
        change_set._check_if_change_violates_power_state.assert_not_called()

        change_set.vm = Mock()
        change_set.check_if_change_is_required("cpu.cores", "config.hardware.numCPU")
        change_set._check_if_param_differs_from_vm.assert_called_once_with(
            "cpu.cores", "config.hardware.numCPU"
        )
        change_set._check_if_change_violates_power_state.assert_not_called()

        change_set.check_if_change_is_required(
            "cpu.cores",
            "config.hardware.numCPU",
            power_sensitive=True,
            errors_fatal=True,
        )
        change_set._check_if_change_violates_power_state.assert_called_once_with(
            "cpu.cores", errors_fatal=True
        )

    def test_check_if_change_is_required_with_change(self):
        """Test when change is required."""
        params = {"cpu": {"cores": 8}}
        vm = Mock()
        vm.config.hardware.numCPU = 4
        error_handler = Mock()

        change_set = ParameterChangeSet(params, vm, error_handler)
        change_set.check_if_change_is_required("cpu.cores", "config.hardware.numCPU")

        assert change_set.changes_required is True
        assert change_set.power_cycle_required is False

    def test_check_if_change_is_required_parameter_not_specified(self):
        """Test when parameter is not specified in params."""
        params = {}
        vm = Mock()
        vm.config.hardware.numCPU = 4
        error_handler = Mock()

        change_set = ParameterChangeSet(params, vm, error_handler)
        change_set.check_if_change_is_required("cpu.cores", "config.hardware.numCPU")

        assert change_set.changes_required is False

    def test_check_if_change_is_required_new_vm(self):
        """Test change detection for new VM (vm is None)."""
        params = {"cpu": {"cores": 4}}
        error_handler = Mock()

        change_set = ParameterChangeSet(params, None, error_handler)
        change_set.check_if_change_is_required("cpu.cores", "config.hardware.numCPU")

        # Should not change anything since vm is None
        assert change_set.changes_required is True  # Already set in init

    def test_check_if_change_is_required_power_sensitive_powered_off(self):
        """Test power-sensitive change when VM is powered off."""
        params = {"cpu": {"cores": 8}, "allow_power_cycling": False}
        vm = Mock()
        vm.config.hardware.numCPU = 4
        vm.runtime.powerState = "poweredOff"
        error_handler = Mock()

        change_set = ParameterChangeSet(params, vm, error_handler)
        change_set.check_if_change_is_required(
            "cpu.cores", "config.hardware.numCPU", power_sensitive=True
        )

        assert change_set.changes_required is True
        assert change_set.power_cycle_required is False

    def test_check_if_change_is_required_power_sensitive_powered_on_no_cycling(self):
        """Test power-sensitive change when VM is powered on and cycling not allowed."""
        params = {"cpu": {"cores": 8}, "allow_power_cycling": False}
        vm = Mock()
        vm.config.hardware.numCPU = 4
        vm.runtime.powerState = "poweredOn"
        error_handler = Mock()

        change_set = ParameterChangeSet(params, vm, error_handler)
        change_set.check_if_change_is_required(
            "cpu.cores", "config.hardware.numCPU", power_sensitive=True
        )

        error_handler.fail_with_power_cycle_error.assert_called_once_with("cpu.cores")

    def test_check_if_change_is_required_power_sensitive_powered_on_with_cycling(self):
        """Test power-sensitive change when VM is powered on and cycling is allowed."""
        params = {"cpu": {"cores": 8}, "allow_power_cycling": True}
        vm = Mock()
        vm.config.hardware.numCPU = 4
        vm.runtime.powerState = "poweredOn"
        error_handler = Mock()

        change_set = ParameterChangeSet(params, vm, error_handler)
        change_set.check_if_change_is_required(
            "cpu.cores", "config.hardware.numCPU", power_sensitive=True
        )

        assert change_set.changes_required is True
        assert change_set.power_cycle_required is True

    def test_check_if_change_is_required_power_sensitive_no_change(self):
        """Test power-sensitive change when no change is required."""
        params = {"cpu": {"cores": 4}, "allow_power_cycling": False}
        vm = Mock()
        vm.config.hardware.numCPU = 4
        vm.runtime.powerState = "poweredOn"
        error_handler = Mock()

        change_set = ParameterChangeSet(params, vm, error_handler)
        change_set.check_if_change_is_required(
            "cpu.cores", "config.hardware.numCPU", power_sensitive=True
        )

        assert change_set.changes_required is False
        assert change_set.power_cycle_required is False

    def test_check_if_change_is_required_power_sensitive_errors_not_fatal(self):
        """Test power-sensitive change with non-fatal errors."""
        params = {"cpu": {"cores": 8}, "allow_power_cycling": False}
        vm = Mock()
        vm.config.hardware.numCPU = 4
        vm.runtime.powerState = "poweredOn"
        error_handler = Mock()

        change_set = ParameterChangeSet(params, vm, error_handler)

        with pytest.raises(PowerCycleRequiredError, match="cpu.cores"):
            change_set.check_if_change_is_required(
                "cpu.cores",
                "config.hardware.numCPU",
                power_sensitive=True,
                errors_fatal=False,
            )

    def test_check_if_param_differs_from_vm_nested_attributes(self):
        """Test comparison with nested parameter and VM attributes."""
        params = {"hardware": {"memory": {"size": 8192}}}
        vm = Mock()
        vm.config.hardware.memoryMB = 4096
        error_handler = Mock()

        change_set = ParameterChangeSet(params, vm, error_handler)
        change_set.check_if_change_is_required(
            "hardware.memory.size", "config.hardware.memoryMB"
        )

        assert change_set.changes_required is True

    def test_check_if_param_differs_from_vm_already_changed(self):
        """Test that subsequent checks don't override changes_required."""
        params = {"cpu": {"cores": 8}, "memory": {"size": 8192}}
        vm = Mock()
        vm.config.hardware.numCPU = 4
        vm.config.hardware.memoryMB = 8192
        error_handler = Mock()

        change_set = ParameterChangeSet(params, vm, error_handler)

        # First change sets changes_required to True
        change_set.check_if_change_is_required("cpu.cores", "config.hardware.numCPU")
        assert change_set.changes_required is True

        # Second check (no change) should not set it back to False
        change_set.check_if_change_is_required(
            "memory.size", "config.hardware.memoryMB"
        )
        assert change_set.changes_required is True

    def test_propagate_required_changes_from_valid(self):
        """Test propagating changes from another change set."""
        params1 = {"cpu": {"cores": 4}}
        params2 = {"memory": {"size": 8192}}
        vm = Mock()
        error_handler = Mock()

        change_set1 = ParameterChangeSet(params1, vm, error_handler)
        change_set2 = ParameterChangeSet(params2, vm, error_handler)

        # Set up change sets with different states
        change_set1.changes_required = True
        change_set1.power_cycle_required = False
        change_set2.changes_required = False
        change_set2.power_cycle_required = True

        change_set1.propagate_required_changes_from(change_set2)

        assert change_set1.changes_required is True
        assert change_set1.power_cycle_required is True

    def test_propagate_required_changes_from_invalid_type(self):
        """Test propagating changes with invalid type."""
        params = {"cpu": {"cores": 4}}
        vm = Mock()
        error_handler = Mock()

        change_set = ParameterChangeSet(params, vm, error_handler)

        with pytest.raises(
            ValueError, match="change_set must be an instance of ParameterChangeSet"
        ):
            change_set.propagate_required_changes_from("invalid")

    def test_propagate_required_changes_from_logical_or_behavior(self):
        """Test logical OR behavior in change propagation."""
        params = {"cpu": {"cores": 4}}
        vm = Mock()
        error_handler = Mock()

        change_set1 = ParameterChangeSet(params, vm, error_handler)
        change_set2 = ParameterChangeSet(params, vm, error_handler)

        # Test all combinations of boolean values
        test_cases = [
            (False, False, False, False, False, False),
            (False, False, False, True, False, True),
            (False, False, True, False, True, False),
            (False, False, True, True, True, True),
            (False, True, False, False, False, True),
            (False, True, False, True, False, True),
            (False, True, True, False, True, True),
            (False, True, True, True, True, True),
            (True, False, False, False, True, False),
            (True, False, False, True, True, True),
            (True, False, True, False, True, False),
            (True, False, True, True, True, True),
            (True, True, False, False, True, True),
            (True, True, False, True, True, True),
            (True, True, True, False, True, True),
            (True, True, True, True, True, True),
        ]

        for cr1, pcr1, cr2, pcr2, expected_cr, expected_pcr in test_cases:
            change_set1.changes_required = cr1
            change_set1.power_cycle_required = pcr1
            change_set2.changes_required = cr2
            change_set2.power_cycle_required = pcr2

            change_set1.propagate_required_changes_from(change_set2)

            assert change_set1.changes_required == expected_cr
            assert change_set1.power_cycle_required == expected_pcr

    def test_vm_attribute_access_error_handling(self):
        """Test handling of VM attribute access errors."""
        params = {"cpu": {"cores": 4}}
        vm = Mock()
        # Simulate missing attribute
        vm.config.hardware = None
        error_handler = Mock()

        change_set = ParameterChangeSet(params, vm, error_handler)

        # Should not raise an exception and return with no change
        change_set.check_if_change_is_required(
            "cpu.fdsafdafa", "config.hardware.numCPU"
        )
        assert change_set.changes_required is False

        # Should not raise an exception, and return with change
        change_set.check_if_change_is_required(
            "cpu.cores", "config.hardware.fdsafdasfdsa"
        )
        assert change_set.changes_required is True

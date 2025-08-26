from __future__ import absolute_import, division, print_function

__metaclass__ = type

import pytest
from unittest.mock import Mock

from ansible_collections.vmware.vmware.plugins.module_utils.vm.parameter_handlers._cpu import (
    CpuParameterHandler,
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

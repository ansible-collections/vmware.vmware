from __future__ import absolute_import, division, print_function

__metaclass__ = type

import pytest
from unittest.mock import Mock, patch

from ansible_collections.vmware.vmware.plugins.module_utils.vm.parameter_handlers._vm_options import (
    VmOptionsParameterHandler,
)


class TestVmOptionsParameterHandler:
    @pytest.fixture
    def vm_options_parameter_handler(self):
        return VmOptionsParameterHandler(Mock(), {}, Mock(), Mock())

    def test_init(self):
        params = {}
        VmOptionsParameterHandler(Mock(), params, Mock(), Mock())

        params = {"vm_options": {}}
        VmOptionsParameterHandler(Mock(), params, Mock(), Mock())

        params["vm_options"]["encrypted_fault_tolerance"] = "opportunistic"
        obj = VmOptionsParameterHandler(Mock(), params, Mock(), Mock())
        assert (
            obj._vm_option_params["encrypted_fault_tolerance"]
            == "ftEncryptionOpportunistic"
        )

    def test_verify_parameter_constraints(self, vm_options_parameter_handler):
        vm_options_parameter_handler._verify_parameter_constraints_virt_based_security = (
            Mock()
        )
        vm_options_parameter_handler._verify_parameter_constraints_enable_encryption = (
            Mock()
        )
        vm_options_parameter_handler.verify_parameter_constraints()
        assert (
            vm_options_parameter_handler._verify_parameter_constraints_virt_based_security.call_count
            == 1
        )
        assert (
            vm_options_parameter_handler._verify_parameter_constraints_enable_encryption.call_count
            == 1
        )

        vm_options_parameter_handler._vm_option_params = {
            "maximum_remote_console_sessions": 41
        }
        vm_options_parameter_handler.verify_parameter_constraints()
        assert (
            vm_options_parameter_handler.error_handler.fail_with_parameter_error.call_count
            == 1
        )

    @pytest.mark.parametrize(
        "enable_vbs, firmware, secure_boot, enable_hardware_assisted_virtualization, vm, expected_error_count",
        [
            (None, None, None, None, None, 0),
            (False, None, None, None, None, 0),
            (True, None, None, None, None, 1),
            (True, "bios", False, None, None, 1),
            (True, "efi", False, None, None, 1),
            (True, "efi", True, False, None, 1),
            (True, "efi", True, True, None, 0),
            (True, None, None, None, Mock(), 0),
        ],
    )
    def test_verify_parameter_constraints_virt_based_security(
        self,
        vm_options_parameter_handler,
        enable_vbs,
        firmware,
        secure_boot,
        enable_hardware_assisted_virtualization,
        vm,
        expected_error_count,
    ):
        vm_options_parameter_handler._vm_option_params = {
            "enable_virtual_based_security": enable_vbs,
            "boot_firmware": firmware,
            "enable_secure_boot": secure_boot,
            "enable_hardware_assisted_virtualization": enable_hardware_assisted_virtualization,
        }
        vm_options_parameter_handler.vm = vm

        vm_options_parameter_handler._verify_parameter_constraints_virt_based_security()
        assert (
            vm_options_parameter_handler.error_handler.fail_with_parameter_error.call_count
            == expected_error_count
        )

    @pytest.mark.parametrize(
        "enable_encryption, firmware, secure_boot, vm, expected_error_count",
        [
            (None, None, None, None, 0),
            (False, None, None, None, 0),
            (True, None, None, None, 0),
            (True, "bios", False, None, 1),
            (True, "efi", False, None, 0),
            (True, "efi", True, None, 1),
            (True, None, None, Mock(), 2),
        ],
    )
    def test_verify_parameter_constraints_enable_encryption(
        self,
        vm_options_parameter_handler,
        enable_encryption,
        firmware,
        secure_boot,
        vm,
        expected_error_count,
    ):
        vm_options_parameter_handler.params = {
            "memory": {"enable_hot_add": False},
            "cpu": {"enable_hot_add": False},
        }
        vm_options_parameter_handler._vm_option_params = {
            "enable_encryption": enable_encryption,
            "boot_firmware": firmware,
            "enable_secure_boot": secure_boot,
        }
        vm_options_parameter_handler.vm = vm

        vm_options_parameter_handler._verify_parameter_constraints_enable_encryption()
        assert (
            vm_options_parameter_handler.error_handler.fail_with_parameter_error.call_count
            == expected_error_count
        )

    @patch(
        "ansible_collections.vmware.vmware.plugins.module_utils.vm.parameter_handlers._vm_options.vim"
    )
    def test_populate_config_spec_with_parameters(
        self, mock_vim, vm_options_parameter_handler
    ):
        configspec = Mock()
        configspec.flags = None
        configspec.bootOptions = None
        vm_options_parameter_handler._vm_option_params = {
            "maximum_remote_console_sessions": 4
        }
        vm_options_parameter_handler.populate_config_spec_with_parameters(configspec)
        assert configspec.maxMksConnections == 4
        assert configspec.flags is None
        assert configspec.bootOptions is None

        vm_options_parameter_handler._vm_option_params = {
            "enable_io_mmu": True,
            "enable_secure_boot": True,
        }
        vm_options_parameter_handler.populate_config_spec_with_parameters(configspec)
        assert configspec.flags.vvtdEnabled is True
        assert configspec.bootOptions.efiSecureBootEnabled is True

    def test_compare_live_config_with_desired_config(
        self, vm_options_parameter_handler
    ):
        vm_options_parameter_handler.compare_live_config_with_desired_config()
        assert (
            vm_options_parameter_handler.change_set.check_if_change_is_required.call_count
            > 1
        )

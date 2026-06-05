"""
vTPM parameter handler for VM configuration.

This module provides the VtpmParameterHandler class which manages virtual
Trusted Platform Module (vTPM) configuration. It handles enabling and
disabling vTPM devices on virtual machines through the enable_vtpm parameter.
"""

from ansible_collections.vmware.vmware.plugins.module_utils.vm.parameter_handlers._abstract import (
    AbstractDeviceLinkedParameterHandler,
)
from ansible_collections.vmware.vmware.plugins.module_utils.vm.objects._vtpm import (
    Vtpm,
)

try:
    from pyVmomi import vim
except ImportError:
    pass


class VtpmParameterHandler(AbstractDeviceLinkedParameterHandler):
    """
    Handler for virtual Trusted Platform Module (vTPM) configuration.

    Managed Parameters:
        - enable_vtpm (bool): When true, ensure a vTPM device is present on the VM.
          When false, ensure no vTPM device is present. When omitted, vTPM is not managed.
    """

    HANDLER_NAME = "vtpm"

    def __init__(
        self, error_handler, params, change_set, vm, device_tracker, **kwargs
    ):
        """
        Initialize the vTPM parameter handler.

        Args:
            error_handler: Service for parameter validation error handling
            params (dict): Module parameters containing vTPM configuration
            change_set: Service for tracking configuration changes and requirements
            vm: VM object being configured (None for new VM creation)
            device_tracker: Service for device identification and error reporting
        """
        super().__init__(error_handler, params, change_set, vm, device_tracker)
        self._check_if_params_are_defined_by_user(
            "enable_vtpm", required_for_vm_creation=False
        )

        if self.params.get("enable_vtpm") is True:
            self.managed_parameter_objects[0] = Vtpm()

    @property
    def vim_device_class(self):
        """
        Get the VMware device class for virtual TPM devices.
        """
        return vim.vm.device.VirtualTPM

    def verify_parameter_constraints(self):
        """
        Validate vTPM parameter constraints and requirements.

        When enable_vtpm is true, validates EFI boot firmware and that the VM has
        no snapshots.

        Raises:
            Calls error_handler.fail_with_parameter_error() for constraint violations.
        """
        if not self.params.get("enable_vtpm"):
            return

        boot_firmware = self.params.get("vm_options", dict()).get("boot_firmware")
        if self.vm is not None:
            if boot_firmware is None:
                boot_firmware = self.vm.config.firmware

            if self.vm.snapshot:
                self.error_handler.fail_with_parameter_error(
                    parameter_name="enable_vtpm",
                    message="vTPM cannot be enabled on a VM that has snapshots."
                )

        if boot_firmware != "efi":
            self.error_handler.fail_with_parameter_error(
                parameter_name="enable_vtpm",
                message="vTPM requires EFI boot firmware.",
                details={"firmware": boot_firmware},
            )

    def link_vm_device(self, device):
        """
        Link a VMware vTPM device to the handler's managed object.

        When enable_vtpm is true, links the live device to the desired vTPM object.
        When enable_vtpm is false, returns a live vTPM representation so the device
        tracker can schedule it for removal.

        Args:
            device: VMware VirtualTPM device to link

        Returns:
            Vtpm or None: Live vTPM object to remove when enable_vtpm is false,
            otherwise None when the device was linked successfully.
        """
        if not self.managed_parameter_objects:
            return Vtpm.from_live_device_spec(device)

        vtpm = self.managed_parameter_objects[0]
        if vtpm.has_a_linked_live_vm_device():
            self.error_handler.fail_with_parameter_error(
                parameter_name="enable_vtpm",
                message="vTPM is already enabled, but more than one vTPM device was found. This is not a supported configuration.",
                details={"vtpm": str(vtpm)},
            )

        vtpm.link_corresponding_live_object(
            Vtpm.from_live_device_spec(device)
        )

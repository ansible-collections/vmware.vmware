"""
Disk parameter handler for VM storage configuration.

This module provides the DiskParameterHandler class which manages virtual disk
configuration including disk creation, modification, and controller assignment.
It handles disk parameter validation, device linking, and VMware specification
generation for storage management.

The handler works closely with controller handlers to ensure proper disk
placement and validates disk parameters against available controllers.
"""

from ansible_collections.vmware.vmware.plugins.module_utils.vm.parameter_handlers._abstract import (
    AbstractDeviceLinkedParameterHandler,
    DeviceLinkError,
)
from ansible_collections.vmware.vmware.plugins.module_utils.vm.objects._disk import Disk
from ansible_collections.vmware.vmware.plugins.module_utils.vm._utils import (
    parse_device_node,
)

try:
    from pyVmomi import vim
except ImportError:
    pass


class DiskParameterHandler(AbstractDeviceLinkedParameterHandler):
    """
    Handler for virtual disk configuration parameters.

    This handler manages the creation, modification, and validation of virtual
    disks on VMs. It processes disk parameters, validates controller assignments,
    and generates VMware device specifications for disk operations.

    The handler requires coordination with controller handlers to ensure that
    disks are properly assigned to available controllers. It validates device
    node specifications and ensures that all required controllers exist.

    Managed Parameters:
    - disks: List of disk configurations with size, backing, mode, and device_node

    Each disk configuration includes:
    - size: Disk size (e.g., "100gb", "512mb")
    - backing: Disk backing type ("thin", "thick", "eagerzeroedthick")
    - mode: Disk mode ("persistent", "independent_persistent", etc.)
    - device_node: Controller assignment (e.g., "scsi:0:1", "sata:0:0")

    Attributes:
        disks (list): List of Disk objects representing desired disk configuration
        controller_handlers (list): List of controller handlers for disk assignment
    """

    HANDLER_NAME = "disk"

    def __init__(
        self, error_handler, params, change_set, vm, device_tracker, controller_handlers, **kwargs
    ):
        """
        Initialize the disk parameter handler.

        Args:
            error_handler: Service for parameter validation error handling
            params (dict): Module parameters containing disk configuration
            change_set: Service for tracking configuration changes and requirements
            vm: VM object being configured (None for new VM creation)
            device_tracker: Service for device identification and error reporting
            controller_handlers (list): List of controller handlers for disk assignment
        """
        super().__init__(error_handler, params, change_set, vm, device_tracker)
        self._check_if_params_are_defined_by_user("disks", required_for_vm_creation=True)

        self.disks = []
        self.controller_handlers = controller_handlers

    @property
    def vim_device_class(self):
        """
        Get the VMware device class for this controller type.
        """
        return vim.vm.device.VirtualDisk

    def verify_parameter_constraints(self):
        """
        Validate disk parameter constraints and requirements.

        Parses disk parameters and validates that at least one disk is defined
        for VM creation or modification. Validates that all required controllers
        exist and that disk specifications are valid.

        Raises:
            Calls error_handler.fail_with_parameter_error() for invalid disk
            parameters, missing controllers, or missing disk definitions.
        """
        if len(self.disks) == 0:
            try:
                self._parse_disk_params()
            except ValueError as e:
                self.error_handler.fail_with_parameter_error(
                    parameter_name="disks",
                    message="Error parsing disk parameters: %s" % str(e),
                    details={"error": str(e)},
                )

        if len(self.disks) == 0 and self.vm is None:
            self.error_handler.fail_with_parameter_error(
                parameter_name="disks",
                message="At least one disk must be defined when creating a VM.",
            )

    def _parse_disk_params(self):
        """
        Parse disk parameters and create Disk objects.

        Processes the disk parameter list, validates device node specifications,
        and creates Disk objects with proper controller assignments. Validates
        that all required controllers exist and are configured.

        Raises:
            ValueError: For invalid device node specifications or parameter formats
            Calls error_handler.fail_with_parameter_error() for missing controllers

        Side Effects:
            Populates self.disks with Disk objects representing desired configuration.
        """
        disk_params = self.params.get("disks") or []
        for disk_param in disk_params:
            controller_type, controller_bus_number, unit_number = parse_device_node(
                disk_param["device_node"]
            )
            for controller_handler in self.controller_handlers:
                if controller_type == controller_handler.category:
                    controller = controller_handler.controllers.get(
                        controller_bus_number
                    )
                    break
            else:
                self.error_handler.fail_with_parameter_error(
                    parameter_name="disks",
                    message="No controller has been configured for device %s. You must specify this controller in the appropriate controller parameter."
                    % disk_param["device_node"],
                    details={
                        "device_node": disk_param["device_node"],
                        "available_controllers": [
                            c.name_as_str
                            for ch in self.controller_handlers
                            for c in ch.controllers.values()
                        ],
                    },
                )

            disk = Disk(
                size=disk_param.get("size"),
                backing=disk_param.get("backing"),
                mode=disk_param.get("mode"),
                controller=controller,
                unit_number=unit_number,
            )
            self.disks.append(disk)

    def populate_config_spec_with_parameters(self, configspec):
        """
        Populate VMware configuration specification with disk parameters.

        Adds disk device specifications to the configuration for both new
        disk creation and existing disk modification. Tracks device IDs
        for proper error reporting and device management.

        Args:
            configspec: VMware VirtualMachineConfigSpec to populate

        Side Effects:
            Adds disk device specifications to configspec.deviceChange.
            Tracks device IDs through device_tracker for error reporting.
        """
        for disk in self.change_set.objects_to_add:
            self.device_tracker.track_device_id_from_spec(disk)
            configspec.deviceChange.append(disk.create_disk_spec())
        for disk in self.change_set.objects_to_update:
            self.device_tracker.track_device_id_from_spec(disk)
            configspec.deviceChange.append(disk.update_disk_spec())

    def compare_live_config_with_desired_config(self):
        """
        Compare current VM disk configuration with desired configuration.

        Analyzes each disk to determine if it needs to be added, updated,
        or is already in sync with the desired configuration. Categorizes
        disks based on their current state and required changes.

        Returns:
            ParameterChangeSet: Updated change set with disk change requirements

        Side Effects:
            Updates change_set with disk objects categorized by required actions.
        """
        for disk in self.disks:
            if disk._device is None:
                self.change_set.objects_to_add.append(disk)
            elif disk.linked_device_differs_from_config():
                self.change_set.objects_to_update.append(disk)
            else:
                self.change_set.objects_in_sync.append(disk)

        return self.change_set

    def link_vm_device(self, device):
        """
        Link a VMware disk device to the appropriate disk object.

        Matches a VMware disk device to the corresponding disk object based
        on controller key and unit number. This establishes the connection
        between the existing VM device and the handler's disk representation.

        Args:
            device: VMware VirtualDisk device to link

        Raises:
            Exception: If no matching disk object is found for the device

        Side Effects:
            Sets the _device attribute on the matching disk object.
        """
        for disk in self.disks:
            if (
                device.unitNumber == disk.unit_number
                and device.controllerKey == disk.controller.key
            ):
                disk._device = device
                return

        raise DeviceLinkError(
            "Disk not found for device %s on controller %s"
            % (device.unitNumber, device.controllerKey),
            device,
            self,
        )

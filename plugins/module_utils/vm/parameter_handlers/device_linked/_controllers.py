"""
Controller parameter handlers for VM storage controller configuration.

This module provides parameter handlers for different types of VM storage
controllers including SCSI, SATA, NVMe, and IDE controllers. Each controller
type has specific capabilities and configuration options that are managed
by their respective handlers.

The handlers follow a common pattern for controller management while providing
type-specific implementations for different controller characteristics and
VMware requirements.
"""

from abc import abstractmethod
from ansible_collections.vmware.vmware.plugins.module_utils.vm.parameter_handlers._abstract import (
    AbstractDeviceLinkedParameterHandler,
    DeviceLinkError,
)
from ansible_collections.vmware.vmware.plugins.module_utils.vm.objects._controllers import (
    ScsiController,
    SataController,
    NvmeController,
    IdeController,
)

try:
    from pyVmomi import vim
except ImportError:
    pass


class DiskControllerParameterHandlerBase(AbstractDeviceLinkedParameterHandler):
    """
    Abstract base class for disk controller parameter handlers.

    This class provides common functionality for managing VM disk controllers
    including parameter validation, device linking, and change detection.
    All disk controller types (SCSI, SATA, NVMe, IDE) extend this base class.

    Controllers are identified by their category (scsi, sata, nvme, ide) and
    bus number. Each controller type has a maximum number of controllers that
    can be added to a VM, and this base class enforces those limits.

    The base class handles common controller operations while allowing subclasses
    to implement type-specific parameter parsing and configuration.

    Attributes:
        controllers (dict): Registry of controllers by bus number {bus_number: controller}
        max_count (int): Maximum number of controllers allowed for this type
        category (str): Controller category identifier (scsi, sata, nvme, ide)
    """

    def __init__(
        self, error_handler, params, change_set, vm, device_tracker, category, max_count=4
    ):
        """
        Initialize the controller parameter handler.

        Args:
            error_handler: Service for parameter validation error handling
            params (dict): Module parameters containing controller configuration
            change_set: Service for tracking configuration changes and requirements
            vm: VM object being configured (None for new VM creation)
            device_tracker: Service for device identification and error reporting
            category (str): Controller category identifier (scsi, sata, nvme, ide)
            max_count (int): Maximum number of controllers allowed (default 4)
        """
        super().__init__(error_handler, params, change_set, vm, device_tracker)
        self.controllers = {}  # {bus_number: controller}
        self.max_count = max_count
        self.category = category

    def verify_parameter_constraints(self):
        """
        Validate controller parameter constraints and limits.

        Parses controller parameters and validates that the number of
        controllers doesn't exceed the maximum allowed for this controller
        type. Different controller types have different limits.

        Raises:
            Calls error_handler.fail_with_parameter_error() if too many
            controllers are specified for this controller type.
        """
        self._parse_device_controller_params()
        if len(self.controllers) > self.max_count:
            self.error_handler.fail_with_parameter_error(
                parameter_name="%s_controllers" % self.category,
                message="Only a maximum of %s %s controllers are allowed, but trying to manage %s controllers."
                % (self.max_count, self.category.upper(), len(self.controllers)),
                details={
                    "max_count": self.max_count,
                    "category": self.category,
                    "current_count": len(self.controllers),
                },
            )

    @abstractmethod
    def _parse_device_controller_params(self):
        """
        Parse controller-specific parameters from module input.

        This method must be implemented by subclasses to handle the specific
        parameter format and options for each controller type. For example,
        SCSI controllers have type and bus sharing options, while SATA
        controllers only need a count.

        Side Effects:
            Populates self.controllers with controller objects representing
            the desired configuration.
        """
        raise NotImplementedError

    def populate_config_spec_with_parameters(self, configspec):
        """
        Populate VMware configuration specification with controller parameters.

        Adds controller device specifications to the configuration for both
        new controller creation and existing controller modification. Tracks
        device IDs for proper error reporting and device management.

        Args:
            configspec: VMware VirtualMachineConfigSpec to populate

        Side Effects:
            Adds controller device specifications to configspec.deviceChange.
            Tracks device IDs through device_tracker for error reporting.
        """
        for controller in self.change_set.objects_to_add:
            self.device_tracker.track_device_id_from_spec(controller)
            configspec.deviceChange.append(
                controller.create_controller_spec(edit=False)
            )

        for controller in self.change_set.objects_to_update:
            self.device_tracker.track_device_id_from_spec(controller)
            configspec.deviceChange.append(controller.create_controller_spec(edit=True))

    def compare_live_config_with_desired_config(self):
        """
        Compare current VM controller configuration with desired configuration.

        Analyzes each controller to determine if it needs to be added, updated,
        or is already in sync with the desired configuration. Categorizes
        controllers based on their current state and required changes.

        Returns:
            ParameterChangeSet: Updated change set with controller change requirements

        Side Effects:
            Updates change_set with controller objects categorized by required actions.
        """
        for controller in self.controllers.values():
            if controller._device is None:
                self.change_set.objects_to_add.append(controller)
            elif controller.linked_device_differs_from_config():
                self.change_set.objects_to_update.append(controller)
            else:
                self.change_set.objects_in_sync.append(controller)

        return self.change_set

    def link_vm_device(self, device):
        """
        Link a VMware controller device to the appropriate controller object.

        Matches a VMware controller device to the corresponding controller object
        based on bus number. This establishes the connection between the existing
        VM device and the handler's controller representation.

        Args:
            device: VMware controller device to link

        Raises:
            Exception: If no matching controller object is found for the device

        Side Effects:
            Sets the _device attribute on the matching controller object.
        """
        for controller in self.controllers.values():
            if device.busNumber == controller.bus_number:
                controller._device = device
                return

        raise DeviceLinkError(
            "Controller %s not found for device %s" % (self.controllers[0].device_class.__name__, device.busNumber),
            device,
            self,
        )


class ScsiControllerParameterHandler(DiskControllerParameterHandlerBase):
    """
    Handler for SCSI controller configuration parameters.

    SCSI controllers are the most common type for VM storage and support
    multiple sub-types with different capabilities. This handler manages
    SCSI controller creation, type selection, and bus sharing configuration.

    SCSI controllers support multiple device types:
    - lsilogic: Default type, most common and widely supported
    - buslogic: Legacy type for older VMs
    - paravirtual: Optimized for paravirtualized environments
    - lsilogicsas: SAS variant of LSI Logic controller

    Each SCSI controller can have different bus sharing modes and supports
    up to 15 devices (unit numbers 0-15, excluding controller at unit 7).

    Managed Parameters:
    - scsi_controllers: List of SCSI controller configurations

    Each controller configuration includes:
    - controller_type: SCSI controller sub-type
    - bus_sharing: Bus sharing mode ('noSharing' or 'exclusive')
    """

    HANDLER_NAME = "scsi_controller"

    def __init__(self, error_handler, params, change_set, vm, device_tracker):
        """
        Initialize the SCSI controller parameter handler.

        Args:
            error_handler: Service for parameter validation error handling
            params (dict): Module parameters containing SCSI controller configuration
            change_set: Service for tracking configuration changes and requirements
            vm: VM object being configured (None for new VM creation)
            device_tracker: Service for device identification and error reporting
        """
        super().__init__(error_handler, params, change_set, vm, device_tracker, "scsi")
        self._check_if_params_are_defined_by_user("scsi_controllers", required_for_vm_creation=False)

    @property
    def vim_device_class(self):
        """
        Get the VMware device class for this controller type.
        """
        return vim.vm.device.VirtualSCSIController

    @property
    def device_type_to_sub_class_map(self):
        """
        Get a map of device types to their corresponding sub-classes.
        """
        return {
            "lsilogic": vim.vm.device.VirtualLsiLogicController,
            "paravirtual": vim.vm.device.ParaVirtualSCSIController,
            "buslogic": vim.vm.device.VirtualBusLogicController,
            "lsilogicsas": vim.vm.device.VirtualLsiLogicSASController,
        }

    def _parse_device_controller_params(self):
        """
        Parse SCSI controller parameters from module input.

        Processes the scsi_controllers parameter list and creates ScsiController
        objects with the specified controller type and bus sharing configuration.
        Controllers are indexed by their position in the list.

        Side Effects:
            Populates self.controllers with ScsiController objects representing
            the desired SCSI controller configuration.
        """
        for index, controller_param_def in enumerate(self.params.get("scsi_controllers")):
            self.controllers[index] = ScsiController(
                bus_number=index,
                device_type=controller_param_def.get("controller_type"),
                device_class=self.device_type_to_sub_class_map[
                    controller_param_def.get("controller_type")
                ],
                bus_sharing=controller_param_def.get("bus_sharing"),
            )


class SataControllerParameterHandler(DiskControllerParameterHandlerBase):
    """
    Handler for SATA controller configuration parameters.

    SATA controllers are commonly used for CD/DVD drives and can support
    SATA disks. They have no configurable sub-types or options, so the
    handler only needs to manage the count of controllers.

    SATA controllers provide good compatibility with guest operating systems
    that prefer SATA over SCSI for certain device types.

    Managed Parameters:
    - sata_controller_count: Number of SATA controllers to create
    """

    HANDLER_NAME = "sata_controller"

    def __init__(self, error_handler, params, change_set, vm, device_tracker):
        """
        Initialize the SATA controller parameter handler.

        Args:
            error_handler: Service for parameter validation error handling
            params (dict): Module parameters containing SATA controller configuration
            change_set: Service for tracking configuration changes and requirements
            vm: VM object being configured (None for new VM creation)
            device_tracker: Service for device identification and error reporting
        """
        super().__init__(error_handler, params, change_set, vm, device_tracker, "sata")
        self._check_if_params_are_defined_by_user("sata_controller_count", required_for_vm_creation=False)

    @property
    def vim_device_class(self):
        """
        Get the VMware device class for this controller type.
        """
        return vim.vm.device.VirtualAHCIController

    def _parse_device_controller_params(self):
        """
        Parse SATA controller parameters from module input.

        Creates the specified number of SATA controllers based on the
        sata_controller_count parameter. Controllers are numbered sequentially
        starting from 0.

        Side Effects:
            Populates self.controllers with SataController objects representing
            the desired SATA controller configuration.
        """
        for index in range(self.params.get("sata_controller_count", 0)):
            self.controllers[index] = SataController(bus_number=index)


class NvmeControllerParameterHandler(DiskControllerParameterHandlerBase):
    """
    Handler for NVMe controller configuration parameters.

    NVMe controllers provide high-performance storage access for modern VMs
    that support NVMe devices. They offer better performance than traditional
    SCSI controllers for supported workloads.

    NVMe controllers support bus sharing configuration and are typically used
    for high-performance storage scenarios where low latency is important.

    Managed Parameters:
    - nvme_controllers: List of NVMe controller configurations

    Each controller configuration includes:
    - bus_sharing: Bus sharing mode ('noSharing' or 'exclusive')
    """

    HANDLER_NAME = "nvme_controller"

    def __init__(self, error_handler, params, change_set, vm, device_tracker):
        """
        Initialize the NVMe controller parameter handler.

        Args:
            error_handler: Service for parameter validation error handling
            params (dict): Module parameters containing NVMe controller configuration
            change_set: Service for tracking configuration changes and requirements
            vm: VM object being configured (None for new VM creation)
            device_tracker: Service for device identification and error reporting
        """
        super().__init__(error_handler, params, change_set, vm, device_tracker, "nvme")
        self._check_if_params_are_defined_by_user("nvme_controllers", required_for_vm_creation=False)

    @property
    def vim_device_class(self):
        """
        Get the VMware device class for this controller type.
        """
        return vim.vm.device.VirtualNVMEController

    def _parse_device_controller_params(self):
        """
        Parse NVMe controller parameters from module input.

        Processes the nvme_controllers parameter list and creates NvmeController
        objects with the specified bus sharing configuration. Controllers are
        indexed by their position in the list.

        Side Effects:
            Populates self.controllers with NvmeController objects representing
            the desired NVMe controller configuration.
        """
        for index, controller_param_def in enumerate(self.params.get("nvme_controllers")):
            self.controllers[index] = NvmeController(
                bus_number=index, bus_sharing=controller_param_def.get("bus_sharing")
            )


class IdeControllerParameterHandler(DiskControllerParameterHandlerBase):
    """
    Handler for IDE controller configuration parameters.

    IDE controllers are provided by default on all VMs and cannot be modified
    by the user. However, they can be referenced by other VM components (like
    CD-ROM drives), so the handler creates objects to represent them.

    All VMs have exactly 2 IDE controllers that cannot be removed or modified.
    This handler creates representations of these controllers for reference
    by other parts of the VM configuration.

    Managed Parameters:
    - None (IDE controllers are automatically created)
    """

    HANDLER_NAME = "ide_controller"

    def __init__(self, error_handler, params, change_set, vm, device_tracker):
        """
        Initialize the IDE controller parameter handler.

        Args:
            error_handler: Service for parameter validation error handling
            params (dict): Module parameters containing VM configuration
            change_set: Service for tracking configuration changes and requirements
            device_tracker: Service for device identification and error reporting
            vm: VM object being configured (None for new VM creation)
        """
        super().__init__(
            error_handler, params, change_set, vm, device_tracker, "ide", max_count=2
        )

    @property
    def vim_device_class(self):
        """
        Get the VMware device class for this controller type.
        """
        return vim.vm.device.VirtualIDEController

    def _parse_device_controller_params(self):
        """
        Create IDE controller objects for the default VM controllers.

        Creates representations of the 2 IDE controllers that are present
        on all VMs by default. These controllers cannot be modified but
        can be referenced by other VM components.

        Side Effects:
            Populates self.controllers with IdeController objects representing
            the default IDE controllers (bus numbers 0 and 1).
        """
        for index in range(self.max_count):
            self.controllers[index] = IdeController(bus_number=index)

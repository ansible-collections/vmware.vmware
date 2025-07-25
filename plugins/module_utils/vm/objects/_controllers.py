"""
Controller object representations for VM configuration management. Controllers
are managed separately from the devices they control, but the two are closely
linked.

This module provides controller classes that represent different types of
VM device controllers (SCSI, SATA, IDE, NVMe). Controllers manage the
connection and organization of devices like disks and CD-ROMs within a VM.
"""

from random import randint
from abc import ABC

try:
    from pyVmomi import vim
except ImportError:
    pass


class AbstractDeviceController(ABC):
    """
    Abstract base class for all VM device controllers.

    This class provides common functionality for managing VM device controllers
    including device attachment, change detection, and VMware specification
    generation. Each controller type (SCSI, SATA, IDE, NVMe) extends this
    class with type-specific behavior.

    Controllers act as connection points for devices like disks and maintain
    a registry of attached devices to prevent conflicts and enable proper
    device management.

    Attributes:
        NEW_CONTROLLER_KEYS (tuple): Range of device keys for new controllers (start, end)
        device_class: VMware device class for this controller type
        device_type (str): Human-readable controller type name
        bus_number (int): Controller bus number for identification
        controlled_devices (dict): Registry of devices attached to this controller
        _device: Existing VMware device object (when linked, otherwise None)
        _spec: VMware device specification (when generated, otherwise None)
    """

    # Controller configurations: (key_range_start, key_range_end)
    NEW_CONTROLLER_KEYS = ()

    def __init__(self, device_type, device_class, bus_number):
        """
        Initialize a device controller.

        Args:
            device_type (str): Human-readable controller type (e.g., 'scsi', 'sata')
            device_class: VMware device class for this controller
            bus_number (int): Bus number for controller identification

        Raises:
            NotImplementedError: If NEW_CONTROLLER_KEYS is not defined by subclass

        Side Effects:
            Initializes empty device registry for attached devices.
        """
        if not self.NEW_CONTROLLER_KEYS:
            raise NotImplementedError(
                "Controller classes must define the NEW_CONTROLLER_KEYS attribute"
            )

        self.device_class = device_class
        self.device_type = device_type
        self.bus_number = int(bus_number)
        self._device = None
        self._spec = None
        self.controlled_devices = dict()

    @property
    def key(self):
        """
        Get the VMware device key for this controller.

        The device key is VMware's unique identifier for the controller. This
        property returns the key from either the existing device or the
        generated specification.

        Returns:
            int or None: VMware device key, or None if no device/spec exists
        """
        if self._device is not None:
            return self._device.key
        if self._spec is not None:
            return self._spec.device.key
        return None

    @property
    def name_as_str(self):
        """
        Get a human-readable name for this controller.

        Generates a descriptive name using the controller type and bus number
        for easy identification in error messages and logs.

        Returns:
            str: Human-readable controller name (e.g., "SCSI(0:)", "SATA(1:)")
        """
        return "%s(%s:)" % (self.device_type.upper(), self.bus_number)

    def add_device(self, device):
        """
        Register a device as attached to this controller.

        Adds a device to the controller's device registry, ensuring no conflicts
        with unit numbers. This is used to track which devices are connected
        to each controller for proper configuration management.

        Args:
            device: Device object to attach to this controller

        Raises:
            ValueError: If a device with the same unit number is already attached

        Side Effects:
            Adds device to controlled_devices registry using its unit number as key.
        """
        if device.unit_number in self.controlled_devices:
            raise ValueError(
                "Cannot add multiple devices with unit number %s on controller %s"
                % (device.unit_number, self.name_as_str)
            )

        self.controlled_devices[device.unit_number] = device

    def create_controller_spec(self, edit=False, additional_config=None):
        """
        Create a VMware device specification for this controller.

        Generates a device specification that can be used to add this controller
        to a VM or modify an existing controller. Assigns appropriate device keys
        and applies any additional configuration provided by subclasses.

        Args:
            edit (bool): Whether this is an edit operation (True) or add operation (False)
            additional_config (callable, optional): Function to apply additional configuration
                                                   Takes (spec, edit) parameters

        Returns:
            vim.vm.device.VirtualDeviceSpec: VMware device specification for controller

        Side Effects:
            Caches the generated specification in self._spec.
            Assigns random device key from NEW_CONTROLLER_KEYS range for new controllers.
        """
        key_start, key_end = self.NEW_CONTROLLER_KEYS[0], self.NEW_CONTROLLER_KEYS[1]

        spec = vim.vm.device.VirtualDeviceSpec()
        if edit:
            spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.edit
        else:
            spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.add

        spec.device = self.device_class()
        spec.device.deviceInfo = vim.Description()
        spec.device.busNumber = self.bus_number
        if not edit:
            spec.device.key = -randint(key_start, key_end)

        if additional_config:
            additional_config(spec, edit)

        self._spec = spec
        return spec

    def linked_device_differs_from_config(self, additional_comparisons=None):
        """
        Check if the linked VM device differs from desired configuration.

        Compares the properties of an existing VM controller device with the
        desired configuration to determine if changes are needed. Used for
        change detection in existing VMs.

        Args:
            additional_comparisons (callable, optional): Function to perform additional
                                                        comparisons beyond bus number

        Returns:
            bool: True if the device differs from desired config, False if in sync

        Note:
            Returns True if no device is linked (indicating creation is needed).
        """
        if self._device is None:
            return True

        if self._device.busNumber != self.bus_number:
            return True

        if additional_comparisons:
            return additional_comparisons()

        return False


class ScsiController(AbstractDeviceController):
    """
    SCSI controller for managing SCSI devices like disks.

    SCSI controllers are the most common type for VM storage devices.
    They support hot-add/remove operations and can have up to 15 devices
    attached (unit numbers 0-15, excluding the controller itself at unit 7).

    Attributes:
        bus_sharing (str): Bus sharing mode ('noSharing' or 'exclusive')
    """

    NEW_CONTROLLER_KEYS = (1000, 9999)

    def __init__(
        self,
        bus_number,
        device_type="paravirtual",
        device_class=None,
        bus_sharing="noSharing",
    ):
        """
        Initialize a SCSI controller.

        Args:
            bus_number (int): SCSI bus number (typically 0-3)
            device_type (str): Controller type description
            device_class: VMware SCSI controller class
            bus_sharing (str): Bus sharing mode ('noSharing' or 'exclusive')
        """
        if device_class is None:
            device_class = vim.vm.device.ParaVirtualSCSIController

        super().__init__(device_type, device_class, bus_number)
        self.bus_sharing = bus_sharing

    def create_controller_spec(self, edit=False):
        """
        Create a VMware device specification for this SCSI controller.

        Generates a SCSI controller specification with SCSI-specific settings
        including hot-add/remove support, bus sharing, and controller unit number.

        Args:
            edit (bool): Whether this is an edit operation (True) or add operation (False)

        Returns:
            vim.vm.device.VirtualDeviceSpec: VMware device specification for SCSI controller
        """

        def configure_scsi(spec, edit=False):
            spec.device.hotAddRemove = True
            spec.device.sharedBus = self.bus_sharing
            spec.device.scsiCtlrUnitNumber = 7

        return super().create_controller_spec(
            edit=edit, additional_config=configure_scsi
        )


class SataController(AbstractDeviceController):
    """
    SATA controller for managing SATA devices.

    SATA controllers are commonly used for CD/DVD drives and can also
    support SATA disks. They typically support fewer devices than SCSI
    controllers but provide better compatibility with certain guest OS types.
    """

    NEW_CONTROLLER_KEYS = (15000, 19999)

    def __init__(self, bus_number, device_class=None):
        """
        Initialize a SATA controller.

        Args:
            bus_number (int): SATA bus number
            device_class: VMware SATA controller class (defaults to AHCI)
        """
        if device_class is None:
            device_class = vim.vm.device.VirtualAHCIController

        super().__init__("sata", device_class, bus_number)


class IdeController(AbstractDeviceController):
    """
    IDE controller for legacy device support.

    IDE controllers are primarily used for legacy compatibility and
    CD/DVD drives. Most modern VMs use SCSI or SATA controllers instead,
    but IDE controllers are still needed for certain guest OS types.

    All VMs have two IDE controllers that cannot be modified. We track them
    because they could be referenced by other parts of the VM configuration.
    """

    NEW_CONTROLLER_KEYS = (200, 299)

    def __init__(self, bus_number, device_class=None):
        """
        Initialize an IDE controller.

        Args:
            bus_number (int): IDE bus number (typically 0-1)
            device_class: VMware IDE controller class
        """
        if device_class is None:
            device_class = vim.vm.device.VirtualIDEController

        super().__init__("ide", device_class, bus_number)


class NvmeController(AbstractDeviceController):
    """
    NVMe controller for high-performance storage.

    NVMe controllers provide high-performance storage access for modern
    VMs that support NVMe devices. They offer better performance than
    traditional SCSI controllers for supported workloads.

    Attributes:
        bus_sharing (str): Bus sharing mode ('noSharing' or 'exclusive')
    """

    NEW_CONTROLLER_KEYS = (31000, 39999)

    def __init__(
        self,
        bus_number,
        device_class=None,
        bus_sharing="noSharing",
    ):
        """
        Initialize an NVMe controller.

        Args:
            bus_number (int): NVMe bus number
            device_class: VMware NVMe controller class
            bus_sharing (str): Bus sharing mode ('noSharing' or 'exclusive')
        """
        if device_class is None:
            device_class = vim.vm.device.VirtualNVMEController

        super().__init__("nvme", device_class, bus_number)
        self.bus_sharing = bus_sharing

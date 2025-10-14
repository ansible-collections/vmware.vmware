"""
Controller object representations for VM configuration management. Controllers
are managed separately from the devices they control, but the two are closely
linked.

This module provides controller classes that represent different types of
VM device controllers (SCSI, SATA, IDE, NVMe). Controllers manage the
connection and organization of devices like disks and CD-ROMs within a VM.
"""

from random import randint

try:
    from pyVmomi import vim
except ImportError:
    pass

from ._abstract import AbstractVsphereObject


class AbstractDeviceController(AbstractVsphereObject):
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
        bus_number (int): Controller bus number for identification
        controlled_devices (dict): Registry of devices attached to this controller
        _raw_object: Original VMware device object
        _live_object: Corresponding live device for change detection
    """

    NEW_CONTROLLER_KEYS = (1, 99999)

    def __init__(self, vim_device_class, bus_number, device_type, raw_object=None):
        """
        Initialize a device controller.

        Args:
            vim_device_class: VMware device class for this controller
            bus_number (int): Bus number for controller identification

        Raises:
            NotImplementedError: If NEW_CONTROLLER_KEYS is not defined by subclass

        Side Effects:
            Initializes empty device registry for attached devices.
        """
        super().__init__(raw_object=raw_object)
        self.vim_device_class = vim_device_class
        self.device_type = device_type
        self.bus_number = int(bus_number)
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
        if self._raw_object is not None:
            return self._raw_object.key
        if self._live_object is not None:
            return self._live_object.key

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

    def _to_module_output(self):
        """
        Generate module output friendly representation of this object.

        Returns:
            dict
        """
        return {
            "device_type": self.device_type,
            "bus_number": self.bus_number,
            "device_class": str(self.vim_device_class),
            "used_unit_numbers": list(self.controlled_devices.keys()),
        }

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

    def to_new_spec(self):
        key_start, key_end = self.NEW_CONTROLLER_KEYS[0], self.NEW_CONTROLLER_KEYS[1]

        spec = vim.vm.device.VirtualDeviceSpec()
        spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.add

        spec.device = self.vim_device_class()
        spec.device.deviceInfo = vim.Description()
        spec.device.busNumber = self.bus_number
        spec.device.key = -randint(key_start, key_end)

        return spec

    def to_update_spec(self):
        spec = vim.vm.device.VirtualDeviceSpec()
        spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.edit

        spec.device = self._raw_object or self._live_object._raw_object
        spec.device.busNumber = self.bus_number

        return spec

    def differs_from_live_object(self):
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
        if self._live_object is None:
            return True

        if self._live_object.bus_number != self.bus_number:
            return True

        return False


class BasicDeviceController(AbstractDeviceController):
    def __init__(
        self,
        bus_number,
        device_type,
        vim_device_class,
    ):
        super().__init__(device_type=device_type, vim_device_class=vim_device_class, bus_number=bus_number)

    @classmethod
    def from_live_device_spec(cls, live_device_spec, device_type):
        """
        Create a controller object from a live device specification.
        """
        return cls(
            bus_number=live_device_spec.busNumber,
            device_type=device_type,
            vim_device_class=type(live_device_spec),
            raw_object=live_device_spec
        )


class ShareableDeviceController(BasicDeviceController):
    def __init__(
        self,
        bus_number,
        device_type,
        vim_device_class,
        bus_sharing=None,
    ):
        super().__init__(device_type=device_type, vim_device_class=vim_device_class, bus_number=bus_number)
        self.bus_sharing = bus_sharing

    def to_new_spec(self):
        spec = super().to_new_spec()
        if self.bus_sharing is not None:
            spec.device.sharedBus = self.bus_sharing
        else:
            spec.device.sharedBus = "noSharing"
        return spec

    def to_update_spec(self):
        spec = super().to_update_spec()
        if self.bus_sharing is not None:
            spec.device.sharedBus = self.bus_sharing
        return spec

    def differs_from_live_object(self):
        if super().differs_from_live_object():
            return True

        if self.bus_sharing is not None and self._live_object.bus_sharing != self.bus_sharing:
            return True

        return False

    @classmethod
    def from_live_device_spec(cls, live_device_spec, device_type):
        return cls(
            bus_number=live_device_spec.busNumber,
            device_type=device_type,
            vim_device_class=type(live_device_spec),
            bus_sharing=live_device_spec.sharedBus,
            raw_object=live_device_spec
        )


class ScsiDeviceController(ShareableDeviceController):
    """
    SCSI controller for managing SCSI devices like disks.

    SCSI controllers are the most common type for VM storage devices.
    They support hot-add/remove operations and can have up to 15 devices
    attached (unit numbers 0-15, excluding the controller itself at unit 7).
    """

    def __init__(
        self,
        bus_number,
        device_type,
        vim_device_class,
        bus_sharing=None,
    ):
        super().__init__(device_type=device_type, vim_device_class=vim_device_class, bus_number=bus_number, bus_sharing=bus_sharing)

    def to_new_spec(self):
        spec = super().to_new_spec()
        spec.device.scsiCtlrUnitNumber = 7
        spec.device.hotAddRemove = True
        return spec

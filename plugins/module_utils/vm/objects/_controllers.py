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

    # Controller configurations: (key_range_start, key_range_end)
    NEW_CONTROLLER_KEYS = ()

    def __init__(self, device_class, bus_number, device_type,raw_object=None):
        """
        Initialize a device controller.

        Args:
            device_class: VMware device class for this controller
            bus_number (int): Bus number for controller identification

        Raises:
            NotImplementedError: If NEW_CONTROLLER_KEYS is not defined by subclass

        Side Effects:
            Initializes empty device registry for attached devices.
        """
        super().__init__(raw_object=raw_object)
        if not self.NEW_CONTROLLER_KEYS:
            raise NotImplementedError(
                "Controller classes must define the NEW_CONTROLLER_KEYS attribute"
            )

        self.device_class = device_class
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
        Generate module output friendly representation of the cdrom.

        Returns:
            dict
        """
        return {
            "device_type": self.device_type,
            "bus_number": self.bus_number,
            "device_class": str(self.device_class),
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
        """
        """
        key_start, key_end = self.NEW_CONTROLLER_KEYS[0], self.NEW_CONTROLLER_KEYS[1]

        spec = vim.vm.device.VirtualDeviceSpec()
        spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.add

        spec.device = self.device_class()
        spec.device.deviceInfo = vim.Description()
        spec.device.busNumber = self.bus_number
        spec.device.key = -randint(key_start, key_end)

        return spec

    def to_update_spec(self):
        """
        """
        spec = vim.vm.device.VirtualDeviceSpec()
        spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.edit

        spec.device = self.device_class()
        spec.device.deviceInfo = vim.Description()
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
        device_type,
        device_class,
        bus_sharing=None,
        enable_hot_add_remove=None,
    ):
        """
        Initialize a SCSI controller.

        Args:
            bus_number (int): SCSI bus number (typically 0-3)
            device_type (str): The type of SCSI controller (e.g. "lsilogic", "paravirtual", "buslogic", "lsilogicsas")
            device_class: VMware SCSI controller class
            bus_sharing (str): Bus sharing mode ('noSharing' or 'exclusive')
            enable_hot_add_remove (bool): Whether to enable hot add/remove for the controller
        """
        super().__init__(device_type, device_class, bus_number)
        self.bus_sharing = bus_sharing
        self.enable_hot_add_remove = enable_hot_add_remove

    def __populate_spec_with_options(self, spec):
        spec.device.hotAddRemove = self.enable_hot_add_remove
        spec.device.sharedBus = self.bus_sharing
        spec.device.scsiCtlrUnitNumber = 7
        return spec

    def to_new_spec(self):
        spec = super().to_new_spec()
        return self.__populate_spec_with_options(spec)

    def to_update_spec(self):
        spec = super().to_update_spec()
        return self.__populate_spec_with_options(spec)

    def differs_from_live_object(self):
        if super().differs_from_live_object():
            return True

        for attr in ["enable_hot_add_remove", "bus_sharing"]:
            if getattr(self, attr) is None:
                continue
            if getattr(self._live_object, attr) != getattr(self, attr):
                return True

        return False

    @classmethod
    def from_live_device_spec(cls, live_device_spec, device_type):
        """
        Create a controller object from a live device specification.
        """
        return cls(
            bus_number=live_device_spec.busNumber,
            device_type=device_type,
            device_class=type(live_device_spec),
            bus_sharing=live_device_spec.sharedBus,
            enable_hot_add_remove=live_device_spec.hotAddRemove,
            raw_object=live_device_spec
        )

class SataController(AbstractDeviceController):
    """
    SATA controller for managing SATA devices.

    SATA controllers are commonly used for CD/DVD drives and can also
    support SATA disks. They typically support fewer devices than SCSI
    controllers but provide better compatibility with certain guest OS types.
    """

    NEW_CONTROLLER_KEYS = (15000, 19999)

    def __init__(self, bus_number):
        """
        Initialize a SATA controller.

        Args:
            bus_number (int): SATA bus number
        """
        super().__init__("sata", vim.vm.device.VirtualAHCIController, bus_number)

    @classmethod
    def from_live_device_spec(cls, live_device_spec):
        """
        Create a controller object from a live device specification.
        """
        return cls(
            bus_number=live_device_spec.busNumber,
            raw_object=live_device_spec
        )

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

    def __init__(self, bus_number):
        """
        Initialize an IDE controller.

        Args:
            bus_number (int): IDE bus number (typically 0-1)
        """
        super().__init__("ide", vim.vm.device.VirtualIDEController, bus_number)

    @classmethod
    def from_live_device_spec(cls, live_device_spec):
        """
        Create a controller object from a live device specification.
        """
        return cls(
            bus_number=live_device_spec.busNumber,
            raw_object=live_device_spec
        )

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
        bus_sharing=None,
    ):
        """
        Initialize an NVMe controller.

        Args:
            bus_number (int): NVMe bus number
            bus_sharing (str): Bus sharing mode ('noSharing' or 'exclusive')
        """
        super().__init__("nvme", vim.vm.device.VirtualNVMEController, bus_number)
        self.bus_sharing = bus_sharing

    def to_new_spec(self):
        spec = super().to_new_spec()
        spec.device.sharedBus = self.bus_sharing
        return spec

    def to_update_spec(self):
        spec = super().to_update_spec()
        spec.device.sharedBus = self.bus_sharing
        return spec

    def differs_from_live_object(self):
        if super().differs_from_live_object():
            return True

        for attr in ["bus_sharing"]:
            if getattr(self, attr) is None:
                continue
            if getattr(self._live_object, attr) != getattr(self, attr):
                return True

        return False

    @classmethod
    def from_live_device_spec(cls, live_device_spec):
        """
        Create a controller object from a live device specification.
        """
        return cls(
            bus_number=live_device_spec.busNumber,
            bus_sharing=live_device_spec.sharedBus,
            raw_object=live_device_spec
        )

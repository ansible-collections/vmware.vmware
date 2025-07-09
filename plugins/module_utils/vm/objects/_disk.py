"""
Disk object representation for VM configuration management.

This module provides the Disk class, which represents a virtual disk
and handles the creation and modification of VMware disk specifications.
It manages disk properties such as size, backing type, and placement.

It is meant to represent one of the items in the module's 'disks'
parameter.
"""

from random import randint

try:
    from pyVmomi import vim
except ImportError:
    pass

from ansible_collections.vmware.vmware.plugins.module_utils.vm._utils import (
    format_size_str_as_kb,
)


class Disk:
    """
    Represents a virtual disk for VM configuration.

    This class encapsulates the properties and behavior of a virtual disk,
    including its size, backing type, mode, and controller assignment. It
    provides methods to create VMware device specifications for both new
    disk creation and existing disk modification.

    The disk maintains references to both the desired configuration and
    any existing VM device, enabling change detection and spec generation.

    Attributes:
        size (int): Disk size in kilobytes
        backing (str): Disk backing type ('thin', 'thick', 'eagerzeroedthick')
        mode (str): Disk mode ('persistent', 'independent_persistent', etc.)
        unit_number (int): Unit number on the controller
        controller: Controller object this disk is attached to
        _spec: VMware device specification (when generated)
        _device: Existing VMware device object (when linked)
    """

    def __init__(self, size, backing, mode, controller, unit_number):
        """
        Initialize a new disk object.

        Args:
            size (str): Human-readable disk size (e.g., "100gb", "512mb")
            backing (str): Disk backing type ('thin', 'thick', 'eagerzeroedthick')
            mode (str): Disk mode for persistence behavior
            controller: Controller object to attach this disk to
            unit_number (int): Unit number on the controller (Acceptable values depend on the controller type.)

        Side Effects:
            Converts size string to kilobytes.
            Registers this disk with the controller.
        """
        self.size = format_size_str_as_kb(size)
        self.backing = backing
        self.mode = mode
        self.unit_number = unit_number
        self.controller = controller
        self.controller.add_device(self)

        self._spec = None
        self._device = None

    @property
    def key(self):
        """
        Get the VMware device key for this disk.

        The device key is VMware's unique identifier for the disk. This
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
        Get a human-readable name for this disk.

        Generates a descriptive name including the controller information
        and unit number for easy identification in error messages and logs.

        Returns:
            str: Human-readable disk name (e.g., "Disk - SCSI Controller 0 Unit 1")
        """
        return "Disk - %s Unit %s" % (self.controller.name_as_str, self.unit_number)

    def update_disk_spec(self):
        """
        Create a VMware device specification for updating an existing disk.

        Generates a device specification that can be used to modify the
        properties of an existing disk on a VM. The specification includes
        all current disk properties.

        Returns:
            vim.vm.device.VirtualDeviceSpec: VMware device specification for disk update

        Side Effects:
            Caches the generated specification in self._spec
        """
        disk_spec = vim.vm.device.VirtualDeviceSpec()
        disk_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.edit
        disk_spec.device = self._device

        self._update_disk_spec_with_options(disk_spec)
        self._spec = disk_spec
        return disk_spec

    def create_disk_spec(self):
        """
        Create a VMware device specification for adding a new disk.

        Generates a device specification that can be used to add this disk
        to a VM. Includes file creation operation and assigns a temporary
        device key for VMware's internal tracking.
        The device key is overwritten by VMware when the disk is created.

        Returns:
            vim.vm.device.VirtualDeviceSpec: VMware device specification for disk creation

        Side Effects:
            Caches the generated specification in self._spec.
            Assigns a random negative device key for temporary identification.
        """
        disk_spec = vim.vm.device.VirtualDeviceSpec()
        disk_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
        disk_spec.fileOperation = vim.vm.device.VirtualDeviceSpec.FileOperation.create
        disk_spec.device = vim.vm.device.VirtualDisk()
        disk_spec.device.key = -randint(20000, 24999)
        disk_spec.device.backing = vim.vm.device.VirtualDisk.FlatVer2BackingInfo()

        self._update_disk_spec_with_options(disk_spec)
        self._spec = disk_spec
        return disk_spec

    def _update_disk_spec_with_options(self, disk_spec):
        """
        Apply disk configuration options to a device specification.

        Sets the disk's size, backing type, mode, and controller assignment
        on the provided device specification. This is shared logic used by
        both create and update operations.

        Args:
            disk_spec: VMware device specification to configure

        Side Effects:
            Modifies the provided disk_spec with disk properties.
            Sets backing type based on self.backing value.
        """
        if self.mode:
            disk_spec.device.backing.diskMode = self.mode

        if self.backing == "thin":
            disk_spec.device.backing.thinProvisioned = True
        elif self.backing == "eagerzeroedthick":
            disk_spec.device.backing.eagerlyScrub = True

        disk_spec.device.controllerKey = self.controller.key
        disk_spec.device.unitNumber = self.unit_number
        disk_spec.device.capacityInKB = self.size

    def linked_device_differs_from_config(self):
        """
        Check if the linked VM device differs from desired configuration.

        Compares the properties of an existing VM disk device with the
        desired configuration to determine if changes are needed. Used
        for change detection in existing VMs.

        Returns:
            bool: True if the device differs from desired config, False if in sync

        Note:
            Returns True if no device is linked (indicating creation is needed).
        """
        if not self._device:
            return True

        return (
            self._device.capacityInKB != self.size
            or self._device.backing.diskMode != self.mode
            or self._device.backing.thinProvisioned != (self.backing == "thin")
            or self._device.backing.eagerlyScrub != (self.backing == "eagerzeroedthick")
        )

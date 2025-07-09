"""
Device tracking service for VM configuration management.

This module provides the DeviceTracker service, which tracks VMware device
specifications during VM configuration operations to enable proper error
reporting and device management.
"""

from ansible_collections.vmware.vmware.plugins.module_utils.vm.services._abstract import (
    AbstractService,
)


class DeviceTracker(AbstractService):
    """
    Service for tracking VMware device specifications during configuration.

    This service maintains a registry of devices that are being modified during
    VM configuration. It enables translation between the device's location in
    the spec (ID) and the actual device object for better error reporting and
    debugging.

    The tracker is particularly useful when VMware API calls fail with device
    IDs that need to be mapped back to the original device specifications.
    """

    def __init__(self):
        """
        Initialize the device tracker.

        Creates an empty list to store device specifications in the order
        they are tracked.
        """
        self.spec_id_to_device = list()

    def track_device_id_from_spec(self, device):
        """
        Track a device for later reference.

        Adds a device to the tracker, assigning it the next
        available device ID (based on list position). This allows later
        translation from device IDs back to device objects.

        Args:
            device: VMware device object to track

        Side Effects:
            Appends the device to the internal tracking list.
        """
        self.spec_id_to_device.append(device)

    def translate_device_id_to_device(self, device_id):
        """
        Translate a device ID back to its corresponding device.

        VMware API error messages often reference devices by numeric IDs.
        This method translates those IDs back to the original device
        specifications for better error reporting.

        Args:
            device_id (int): One-based device ID from VMware error messages

        Returns:
            Device specification object corresponding to the device ID

        Raises:
            IndexError: If device_id is out of range or invalid
        """
        return self.spec_id_to_device[device_id - 1]

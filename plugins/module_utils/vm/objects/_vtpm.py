"""
vTPM object representation for VM configuration management.

This module provides the Vtpm class for managing VMware virtual Trusted
Platform Module (vTPM) devices. A vTPM is a virtual device compatible with
TPM 2.0 that depends on VM encryption and a configured key provider.
"""

try:
    from pyVmomi import vim
except ImportError:
    pass

from ._abstract import AbstractVsphereObject


class Vtpm(AbstractVsphereObject):
    """
    Object representation of a virtual Trusted Platform Module (vTPM) device.

    vTPM devices cannot be meaningfully updated after creation; they are added
    or removed only. There is at most one vTPM per virtual machine.
    """

    @classmethod
    def from_live_device_spec(cls, live_device_spec):
        """
        Create Vtpm instance from an existing VMware TPM device.

        Args:
            live_device_spec: VMware VirtualTPM device object

        Returns:
            Vtpm: Configured vTPM instance representing the live device
        """
        return cls(raw_object=live_device_spec)

    def __str__(self):
        return "vTPM"

    def to_new_spec(self):
        """
        Create a VMware device specification for adding a new vTPM.

        Returns:
            vim.vm.device.VirtualDeviceSpec: VMware device specification for vTPM creation
        """
        spec = vim.vm.device.VirtualDeviceSpec()
        spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
        spec.device = vim.vm.device.VirtualTPM()
        spec.device.deviceInfo = vim.Description()
        spec.device.key = self._new_spec_key

        return spec

    def to_update_spec(self):
        """
        No update options are available for vTPM devices.
        """
        return None

    def differs_from_live_object(self):
        """
        Check if the linked VM device differs from desired configuration.

        vTPM presence is managed by add/remove only; an existing linked device
        is always considered in sync.

        Returns:
            bool: True if the device is not linked, False if already present
        """
        if not self.has_a_linked_live_vm_device():
            return True

        return False

    def _to_module_output(self):
        """
        Generate module output friendly representation of this object.

        Returns:
            dict
        """
        output = {
            "object_type": "vtpm",
            "label": str(self),
        }

        return output

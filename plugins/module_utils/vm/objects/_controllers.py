from random import randint
from abc import ABC

try:
    from pyVmomi import vim
except ImportError:
    pass


class DeviceController(ABC):
    # Controller configurations: (key_range_start, key_range_end)
    NEW_CONTROLLER_KEYS = ()

    def __init__(self, device_type, device_class, bus_number):
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
        if self._device is not None:
            return self._device.key
        if self._spec is not None:
            return self._spec.device.key
        return None

    @property
    def name_as_str(self):
        return "%s(%s:)" % (self.device_type.upper(), self.bus_number)

    def add_device(self, device):
        if device.unit_number in self.controlled_devices:
            raise ValueError(
                "Cannot add multiple devices with unit number %s on controller %s"
                % (device.unit_number, self.name_as_str)
            )

        self.controlled_devices[device.unit_number] = device

    def create_controller_spec(self, edit=False, additional_config=None):
        """
        Create a base controller spec with common configuration. This can be used to
        add a new controller to a VM.
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
        if self._device is None:
            return True

        if self._device.busNumber != self.bus_number:
            return True

        if additional_comparisons:
            return additional_comparisons()

        return False


class ScsiController(DeviceController):
    NEW_CONTROLLER_KEYS = (1000, 9999)

    def __init__(
        self,
        bus_number,
        device_type="paravirtual",
        device_class=vim.vm.device.ParaVirtualSCSIController,
        bus_sharing="noSharing",
    ):
        super().__init__(device_type, device_class, bus_number)
        self.bus_sharing = bus_sharing

    def create_controller_spec(self, edit=False):
        def configure_scsi(spec, edit=False):
            spec.device.hotAddRemove = True
            spec.device.sharedBus = self.bus_sharing
            spec.device.scsiCtlrUnitNumber = 7

        return super().create_controller_spec(
            edit=edit, additional_config=configure_scsi
        )


class SataController(DeviceController):
    NEW_CONTROLLER_KEYS = (15000, 19999)

    def __init__(self, bus_number, device_class=vim.vm.device.VirtualAHCIController):
        super().__init__("sata", device_class, bus_number)


class IdeController(DeviceController):
    NEW_CONTROLLER_KEYS = (200, 299)

    def __init__(self, bus_number, device_class=vim.vm.device.VirtualIDEController):
        super().__init__("ide", device_class, bus_number)


class NvmeController(DeviceController):
    NEW_CONTROLLER_KEYS = (31000, 39999)

    def __init__(
        self,
        bus_number,
        device_class=vim.vm.device.VirtualNVMEController,
        bus_sharing="noSharing",
    ):
        super().__init__("nvme", device_class, bus_number)
        self.bus_sharing = bus_sharing

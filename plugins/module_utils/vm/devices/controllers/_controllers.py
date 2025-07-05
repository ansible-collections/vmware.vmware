from random import randint
from abc import ABC

try:
    from pyVmomi import vim
except ImportError:
    pass


class DeviceController(ABC):
    # Controller configurations: (key_range_start, key_range_end)
    NEW_CONTROLLER_KEYS = {
        'scsi': (1000, 9999),
        'sata': (15000, 19999),
        'ide': (200, 299),
        'nvme': (31000, 39999),
        'usb': (40000, 49999)
    }

    def __init__(self, device_type, bus_number):
        try:
            self.device_class = DeviceController.get_controller_types()[device_type]
        except KeyError:
            raise ValueError("Invalid controller device type: %s" % device_type)

        self.device_type = device_type
        self.bus_number = int(bus_number)
        self._device = None
        self._spec = None
        self._device_category = None
        self.controlled_devices = dict()

    # These static methods would be better as class variables, but python will try to
    # access the vim class too early and fail with an ImportError instead of the nice
    # error message we have in the base pyvmomi class.
    @staticmethod
    def get_controller_types():
        return {
            **DeviceController.get_scsi_device_types(),
            **DeviceController.get_usb_device_types(),
            'sata': vim.vm.device.VirtualAHCIController,
            'nvme': vim.vm.device.VirtualNVMEController,
            'ide': vim.vm.device.VirtualIDEController
        }

    @staticmethod
    def get_scsi_device_types():
        return {
            'lsilogic': vim.vm.device.VirtualLsiLogicController,
            'paravirtual': vim.vm.device.ParaVirtualSCSIController,
            'buslogic': vim.vm.device.VirtualBusLogicController,
            'lsilogicsas': vim.vm.device.VirtualLsiLogicSASController
        }

    @staticmethod
    def get_usb_device_types():
        return {
            'usb2': vim.vm.device.VirtualUSBController,
            'usb3': vim.vm.device.VirtualUSBXHCIController
        }

    @property
    def key(self):
        if self._device is not None:
            return self._device.key
        if self._spec is not None:
            return self._spec.device.key
        return None

    @property
    def device_category(self):
        if not self._device_category:
            if self.device_class in DeviceController.get_scsi_device_types().values():
                self._device_category = 'scsi'
            elif self.device_class in DeviceController.get_usb_device_types().values():
                self._device_category = 'usb'
            else:
                self._device_category = self.device_type
        return self._device_category

    @property
    def name_as_str(self):
        return "%s(%s:)" % (self.device_category.upper(), self.bus_number)

    def add_device(self, device):
        if device.unit_number in self.controlled_devices:
            raise ValueError("Cannot add multiple devices with unit number %s on controller %s" % (device.unit_number, self.name_as_str))

        self.controlled_devices[device.unit_number] = device

    # @classmethod
    # def create_from_vm_device(cls, vm_device):
    #     device_type = vm_device.__class__.__name__.lower()
    #     for key, value in DeviceController.get_controller_types().items():
    #         if isinstance(vm_device, value):
    #             device_type = key
    #             break

    #     controller = DeviceController.create_from_params(
    #         device_type,
    #         vm_device.busNumber,
    #         getattr(vm_device, 'sharedBus', None)
    #     )
    #     controller._device = vm_device
    #     return controller

    def create_controller_spec(self, edit=False, additional_config=None):
        """
        Create a base controller spec with common configuration. This can be used to
        add a new controller to a VM.
        """
        key_start, key_end = DeviceController.NEW_CONTROLLER_KEYS[self.device_category]

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
    def __init__(self, bus_number, device_type='paravirtual', bus_sharing='noSharing'):
        super().__init__(device_type, bus_number)
        self.bus_sharing = bus_sharing

        try:
            # Validate SCSI-specific device type
            self.device_class = DeviceController.get_scsi_device_types()[device_type]
        except KeyError:
            raise ValueError("Invalid SCSI controller device type: %s" % device_type)

    def create_controller_spec(self, edit=False):
        def configure_scsi(spec, edit=False):
            spec.device.hotAddRemove = True
            spec.device.sharedBus = self.bus_sharing
            spec.device.scsiCtlrUnitNumber = 7

        return super().create_controller_spec(edit=edit, additional_config=configure_scsi)


class SataController(DeviceController):
    def __init__(self, bus_number):
        super().__init__("sata", bus_number)


class IdeController(DeviceController):
    def __init__(self, bus_number):
        super().__init__("ide", bus_number)


class NvmeController(DeviceController):
    def __init__(self, bus_number, bus_sharing='noSharing'):
        super().__init__("nvme", bus_number)
        self.bus_sharing = bus_sharing

from random import randint

try:
    from pyVmomi import vim
except ImportError:
    pass

from ansible_collections.vmware.vmware.plugins.module_utils.vm.devices._utils import (
    format_size_str_as_kb
)


class Disk:
    def __init__(self, size, backing, mode, controller, unit_number):
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
        if self._device is not None:
            return self._device.key
        if self._spec is not None:
            return self._spec.device.key
        return None

    @property
    def name_as_str(self):
        return "Disk - %s Unit %s" % (self.controller.name_as_str, self.unit_number)

    def update_disk_spec(self):
        disk_spec = vim.vm.device.VirtualDeviceSpec()
        disk_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.edit
        disk_spec.device = self._device

        self._update_disk_spec_with_options(disk_spec)
        self._spec = disk_spec
        return disk_spec

    def create_disk_spec(self):
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
        if self.mode:
            disk_spec.device.backing.diskMode = self.mode

        if self.backing == 'thin':
            disk_spec.device.backing.thinProvisioned = True
        elif self.backing == 'eagerzeroedthick':
            disk_spec.device.backing.eagerlyScrub = True

        disk_spec.device.controllerKey = self.controller.key
        disk_spec.device.unitNumber = self.unit_number
        disk_spec.device.capacityInKB = self.size

    def linked_device_differs_from_config(self):
        if not self._device:
            return True

        return (
            self._device.capacityInKB != self.size or
            self._device.backing.diskMode != self.mode or
            self._device.backing.thinProvisioned != (self.backing == 'thin') or
            self._device.backing.eagerlyScrub != (self.backing == 'eagerzeroedthick')
        )

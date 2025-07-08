from ansible_collections.vmware.vmware.plugins.module_utils.vm.parameter_handlers._controllers import (
    ScsiControllerParameterHandler,
    SataControllerParameterHandler,
    NvmeControllerParameterHandler,
    IdeControllerParameterHandler
)
from ansible_collections.vmware.vmware.plugins.module_utils.vm.parameter_handlers._disks import (
    DiskParameterChangeSet,
    DiskParameterHandler
)
from ansible_collections.vmware.vmware.plugins.module_utils.vm.configurators._abstract import ConfiguratorBase
from ansible_collections.vmware.vmware.plugins.module_utils.vm._utils import track_device_id_from_spec, get_managed_device_classes
from ansible_collections.vmware.vmware.plugins.module_utils.vm._change_sets import (
    ControllerParameterChangeSet,
    DiskParameterChangeSet,
    ParameterChangeSet
)

try:
    from pyVmomi import vim
except ImportError:
    pass


class VmDeviceConfigurator(ConfiguratorBase):
    def __init__(self, vm, module):
        super().__init__(vm, module)

        # Initialize handlers
        self.controller_handlers = [
            (ScsiControllerParameterHandler(vm, module), ControllerParameterChangeSet(vm, self.params)),
            (SataControllerParameterHandler(vm, module), ControllerParameterChangeSet(vm, self.params)),
            (NvmeControllerParameterHandler(vm, module), ControllerParameterChangeSet(vm, self.params)),
            (IdeControllerParameterHandler(vm, module), ControllerParameterChangeSet(vm, self.params))
        ]

        self.disk_handler = DiskParameterHandler(vm, module, [c[0] for c in self.controller_handlers])
        self.disk_change_set = DiskParameterChangeSet(vm, self.params)

        self.unlinked_devices = []

    def prepare_parameter_handlers(self):
        for controller_handler, _ in self.controller_handlers:
            controller_handler.verify_parameter_constraints()
        self.disk_handler.verify_parameter_constraints()
        self._link_devices_to_parameter_handlers()

    def stage_configuration_changes(self):
        overall_change_set = ParameterChangeSet(self.vm, self.params)

        for controller_handler, change_set in self.controller_handlers:
            change_set.propagate_required_changes_from(controller_handler.get_parameter_change_set())
            overall_change_set.propagate_required_changes_from(change_set)

        self.disk_change_set.propagate_required_changes_from(self.disk_handler.get_parameter_change_set())
        overall_change_set.propagate_required_changes_from(self.disk_change_set)

        return overall_change_set

    def apply_staged_changes_to_config_spec(self, configspec):
        for controller_handler, change_set in self.controller_handlers:
            if not change_set.changes_required:
                continue
            controller_handler.populate_config_spec_with_parameters(
                configspec,
                change_set=change_set
            )

        if self.disk_change_set.changes_required:
            self.disk_handler.populate_config_spec_with_parameters(
                configspec,
                change_set=self.disk_change_set
            )

        for device in self.unlinked_devices:
            track_device_id_from_spec(device)
            configspec.deviceChange.append(self._create_device_removal_spec(device))

    def _create_device_removal_spec(self, device):
        spec = vim.vm.device.VirtualDeviceSpec()
        spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.remove
        spec.device = device
        return spec

    def _link_devices_to_parameter_handlers(self):
        if self.vm is None:
            return

        for device in self.vm.config.hardware.device:
            if not isinstance(device, get_managed_device_classes()):
                continue

            if isinstance(device, vim.vm.device.VirtualDisk):
                self.disk_handler.link_disk_to_vm_device(device)
                continue

            for controller_handler, _ in self.controller_handlers:
                if isinstance(device, tuple(controller_handler._device_type_to_class.values())):
                    controller_handler.link_controller_to_vm_device(device)
                    break
            else:
                self.unlinked_devices.append(device)

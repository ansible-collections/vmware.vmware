from ansible_collections.vmware.vmware.plugins.module_utils.vm.configurators._abstract import (
    ConfiguratorBase,
)
from ansible_collections.vmware.vmware.plugins.module_utils.vm import (
    parameter_handlers as handlers,
)
from ansible_collections.vmware.vmware.plugins.module_utils.vm._change_sets import (
    ParameterChangeSet,
)

try:
    from pyVmomi import vim
except ImportError:
    pass


class Configurator(ConfiguratorBase):
    """Main hardware configurator that orchestrates different hardware handlers"""

    def __init__(self, module_context):
        super().__init__(module_context)

        self.device_class_to_handler_class = {
            vim.vm.device.VirtualDisk: handlers._disks.DiskParameterHandler,
            vim.vm.device.VirtualSCSIController: handlers._controllers.ScsiControllerParameterHandler,
            vim.vm.device.VirtualSATAController: handlers._controllers.SataControllerParameterHandler,
            vim.vm.device.VirtualNVMEController: handlers._controllers.NvmeControllerParameterHandler,
            vim.vm.device.VirtualIDEController: handlers._controllers.IdeControllerParameterHandler,
        }
        # controller handlers are separate from the other handlers because they need to
        # processed and initiated before the disk params are parsed.
        self.controller_handlers = [
            handlers._controllers.ScsiControllerParameterHandler(self.module_context),
            handlers._controllers.SataControllerParameterHandler(self.module_context),
            handlers._controllers.NvmeControllerParameterHandler(self.module_context),
            handlers._controllers.IdeControllerParameterHandler(self.module_context),
        ]

        self.handlers = [
            handlers._vm.VmParameterHandler(self.module_context),
            handlers._cpu_memory.CpuParameterHandler(self.module_context),
            handlers._cpu_memory.MemoryParameterHandler(self.module_context),
            handlers._disks.DiskParameterHandler(
                self.module_context, self.controller_handlers
            ),
        ]

        self.change_set = ParameterChangeSet(self.module_context)

    def prepare_parameter_handlers(self):
        """Validate all hardware parameters for VM creation"""
        for handler in self.handlers:
            handler.verify_parameter_constraints()

        self.change_set.unlinked_devices = self._link_vm_devices_to_handlers()

    def stage_configuration_changes(self):
        """
        Check if current VM config differs from desired config. The handler should update its own
        change_set, and then the configurator should propagate the changes to the overall change_set.
        The master_change_set is used to communicate what changes are required to the caller, so it does
        not need to be stored beyond the scope of this method.
        """
        if self.change_set.unlinked_devices:
            self.change_set.changes_required = True

        for handler in self.handlers:
            handler.compare_live_config_with_desired_config()
            self.change_set.propagate_required_changes_from(handler.change_set)
        return self.change_set

    def apply_staged_changes_to_config_spec(self, configspec):
        """
        Update config spec with all hardware parameters
        """
        for device in self.change_set.unlinked_devices:
            self.module_context.track_device_id_from_spec(device)
            configspec.deviceChange.append(self._create_device_removal_spec(device))

        for handler in self.handlers:
            if handler.change_set.changes_required:
                handler.populate_config_spec_with_parameters(configspec)

    def _create_device_removal_spec(self, device):
        spec = vim.vm.device.VirtualDeviceSpec()
        spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.remove
        spec.device = device
        return spec

    def _link_vm_devices_to_handlers(self):
        unlinked_devices = []
        for device in self.module_context.vm.config.hardware.device:
            if not isinstance(device, tuple(self.device_class_to_handler_class.keys())):
                continue

            handler_class = self.device_class_to_handler_class[type(device)]

            for handler in self.handlers:
                if not isinstance(handler, handler_class):
                    continue

                try:
                    handler.link_vm_device(device)
                except Exception:
                    unlinked_devices.append(device)
                finally:
                    break
            else:
                unlinked_devices.append(device)

        return unlinked_devices

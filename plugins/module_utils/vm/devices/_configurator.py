from ansible_collections.vmware.vmware.plugins.module_utils.vm.devices.controllers._handler import (
    ScsiControllerParameterHandler,
    SataControllerParameterHandler,
    NvmeControllerParameterHandler,
    IdeControllerParameterHandler
)
from ansible_collections.vmware.vmware.plugins.module_utils.vm.devices.disks._handler import DiskParameterHandler
from ansible_collections.vmware.vmware.plugins.module_utils.vm._abstracts import ConfiguratorBase


class VmDeviceConfigurator(ConfiguratorBase):
    def __init__(self, vm, module):
        super().__init__(vm, module)

        # Initialize handlers
        self.controller_handlers = [
            ScsiControllerParameterHandler(vm, module),
            SataControllerParameterHandler(vm, module),
            NvmeControllerParameterHandler(vm, module),
            IdeControllerParameterHandler(vm, module)
        ]

        self.disk_handler = DiskParameterHandler(vm, module, self.controller_handlers)

    def validate_params_for_creation(self):
        for controller_handler in self.controller_handlers:
            controller_handler.validate_params_for_creation()
        self.disk_handler.validate_params_for_creation()

    def validate_params_for_reconfiguration(self):
        for controller_handler in self.controller_handlers:
            controller_handler.validate_params_for_reconfiguration()
        self.disk_handler.validate_params_for_reconfiguration()

    def update_config_spec(self, configspec):
        for controller_handler in self.controller_handlers:
            controller_handler.update_config_spec_with_params(configspec)

        self.disk_handler.update_config_spec_with_params(configspec)

    def params_differ_from_actual_config(self, vm):
        for controller_handler in self.controller_handlers:
            controllers_to_add, controllers_to_remove, controllers_to_update, _ = controller_handler.params_differ_from_actual_config(vm)
            if any([controllers_to_add, controllers_to_remove, controllers_to_update]):
                return True

        disks_to_add, disks_to_remove, disks_to_update, _ = self.disk_handler.params_differ_from_actual_config(vm)
        if any([disks_to_add, disks_to_remove, disks_to_update]):
            return True

        return False

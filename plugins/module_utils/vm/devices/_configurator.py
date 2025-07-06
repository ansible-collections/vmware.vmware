from ansible_collections.vmware.vmware.plugins.module_utils.vm.devices.controllers._handler import (
    ControllerParameterChangeSet,
    ScsiControllerParameterHandler,
    SataControllerParameterHandler,
    NvmeControllerParameterHandler,
    IdeControllerParameterHandler
)
from ansible_collections.vmware.vmware.plugins.module_utils.vm.devices.disks._handler import (
    DiskParameterChangeSet,
    DiskParameterHandler
)
from ansible_collections.vmware.vmware.plugins.module_utils.vm._abstracts import ConfiguratorBase, ParameterChangeSet


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

        self.controller_change_sets = {c.category: ControllerParameterChangeSet(vm, self.params) for c in self.controller_handlers}
        self.disk_change_set = DiskParameterChangeSet(vm, self.params)

    def prepare_paramter_handlers(self):
        for controller_handler in self.controller_handlers:
            controller_handler.verify_parameter_constraints()
        self.disk_handler.verify_parameter_constraints()

    def stage_configuration_changes(self):
        overall_change_set = ParameterChangeSet(self.vm, self.params)

        for controller_handler in self.controller_handlers:
            self.controller_change_sets[controller_handler.category] = controller_handler.get_parameter_change_set()
            overall_change_set.combine(self.controller_change_sets[controller_handler.category])

        disk_change_set = self.disk_handler.get_parameter_change_set()
        overall_change_set.combine(disk_change_set)

        return overall_change_set

    def apply_staged_changes_to_config_spec(self, configspec):
        for controller_handler in self.controller_handlers:
            controller_handler.populate_config_spec_with_parameters(
                configspec,
                change_set=self.controller_change_sets[controller_handler.category]
            )

        self.disk_handler.populate_config_spec_with_parameters(
            configspec,
            change_set=self.disk_change_set
        )

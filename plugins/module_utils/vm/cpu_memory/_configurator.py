from ansible_collections.vmware.vmware.plugins.module_utils.vm._abstracts import ConfiguratorBase, ParameterChangeSet
from ansible_collections.vmware.vmware.plugins.module_utils.vm.cpu_memory._handler import CpuParameterHandler, MemoryParameterHandler


class VmCpuMemoryConfigurator(ConfiguratorBase):
    """Main hardware configurator that orchestrates different hardware handlers"""

    def __init__(self, vm, module):
        super().__init__(vm, module)

        # Initialize handlers
        self.handlers = [
            CpuParameterHandler(self.vm, self.module),
            MemoryParameterHandler(self.vm, self.module),
        ]

    def prepare_paramter_handlers(self):
        """Validate all hardware parameters for VM creation"""
        for handler in self.handlers:
            handler.verify_parameter_constraints()

    def stage_configuration_changes(self):
        """Check if current VM config differs from desired config"""
        change_set = ParameterChangeSet(self.vm, self.params)
        for handler in self.handlers:
            change_set.combine(handler.get_parameter_change_set())
        return change_set

    def apply_staged_changes_to_config_spec(self, configspec):
        """Update config spec with all hardware parameters"""
        for handler in self.handlers:
            handler.populate_config_spec_with_parameters(configspec)

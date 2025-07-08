from ansible_collections.vmware.vmware.plugins.module_utils.vm.configurators._abstract import ConfiguratorBase
from ansible_collections.vmware.vmware.plugins.module_utils.vm._change_sets import ParameterChangeSet
from ansible_collections.vmware.vmware.plugins.module_utils.vm.parameter_handlers._cpu_memory import CpuParameterHandler, MemoryParameterHandler


class VmCpuMemoryConfigurator(ConfiguratorBase):
    """Main hardware configurator that orchestrates different hardware handlers"""

    def __init__(self, vm, module):
        super().__init__(vm, module)

        self.change_set = ParameterChangeSet(self.vm, self.params)
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
        for handler in self.handlers:
            self.change_set.propagate_required_changes_from(handler.get_parameter_change_set())
        return self.change_set

    def apply_staged_changes_to_config_spec(self, configspec):
        """Update config spec with all hardware parameters"""
        if not self.change_set.changes_required:
            return

        for handler in self.handlers:
            handler.populate_config_spec_with_parameters(configspec)

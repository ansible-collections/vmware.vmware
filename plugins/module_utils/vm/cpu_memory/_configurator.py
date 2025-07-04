from ansible_collections.vmware.vmware.plugins.module_utils.vm._abstracts import ConfiguratorBase
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

    def validate_params_for_creation(self):
        """Validate all hardware parameters for VM creation"""
        for handler in self.handlers:
            handler.validate_params_for_creation()

    def validate_params_for_reconfiguration(self):
        """Validate all hardware parameters for VM reconfiguration"""
        for handler in self.handlers:
            handler.validate_params_for_reconfiguration()

    def update_config_spec(self, configspec):
        """Update config spec with all hardware parameters"""
        for handler in self.handlers:
            handler.update_config_spec_with_params(configspec)

    def live_config_differs_from_desired_config(self):
        """Check if current VM config differs from desired config"""
        return any(handler.params_differ_from_actual_config() for handler in self.handlers)

from ansible_collections.vmware.vmware.plugins.module_utils.vm._abstracts import ConfiguratorBase
from ansible_collections.vmware.vmware.plugins.module_utils.vm.cpu_memory._configurator import (
    VmCpuMemoryConfigurator
)
from ansible_collections.vmware.vmware.plugins.module_utils.vm.devices._configurator import (
    VmDeviceConfigurator
)
from ansible_collections.vmware.vmware.plugins.module_utils.vm._handler import (
    VmParameterHandler
)

class VmConfigurator(ConfiguratorBase):
    def __init__(self, vm, module):
        super().__init__(vm, module)
        self.vm_handler = VmParameterHandler(self.vm, self.module)
        self.sub_configurators = [
            VmCpuMemoryConfigurator(self.vm, self.module),
            VmDeviceConfigurator(self.vm, self.module)
        ]

    def validate_params_for_creation(self):
        self.vm_handler.validate_params_for_creation()
        for sub_configurator in self.sub_configurators:
            sub_configurator.validate_params_for_creation()

    def configure_spec_for_creation(self, configspec, datastore):
        self.vm_handler.update_config_spec_with_params(configspec, datastore, self.vm)
        for sub_configurator in self.sub_configurators:
            sub_configurator.update_config_spec(configspec)

    def configure_spec_for_reconfiguration(self, configspec):
        self.vm_handler.update_config_spec_with_params(configspec, self.vm)
        for sub_configurator in self.sub_configurators:
            sub_configurator.update_config_spec(configspec)

    def check_if_power_cycle_is_required(self):
        params_requiring_power_cycle = self.vm_handler.get_params_requiring_power_cycle()
        for sub_configurator in self.sub_configurators:
            params_requiring_power_cycle.update(sub_configurator.get_params_requiring_power_cycle())

        for out_of_sync_param in self.required_changes:
            if out_of_sync_param in params_requiring_power_cycle:
                return True
        return False

    def check_for_required_changes(self):
        self.required_changes = set()
        self.required_changes.update(self.vm_handler.get_out_of_sync_params())
        for sub_configurator in self.sub_configurators:
            self.required_changes.update(sub_configurator.check_for_required_changes())

        return self.required_changes

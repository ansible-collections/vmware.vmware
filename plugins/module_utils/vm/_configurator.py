from ansible_collections.vmware.vmware.plugins.module_utils.vm._abstracts import ConfiguratorBase, ParameterChangeSet
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

    def prepare_paramter_handlers(self):
        self.vm_handler.verify_parameter_constraints()
        for sub_configurator in self.sub_configurators:
            sub_configurator.prepare_paramter_handlers()

    def stage_configuration_changes(self):
        change_set = ParameterChangeSet(self.vm, self.params)
        change_set.combine(self.vm_handler.get_parameter_change_set())
        for sub_configurator in self.sub_configurators:
            change_set.combine(sub_configurator.stage_configuration_changes())
        return change_set

    def apply_staged_changes_to_config_spec(self, configspec, datastore):
        self.vm_handler.populate_config_spec_with_parameters(configspec, datastore)
        for sub_configurator in self.sub_configurators:
            sub_configurator.apply_staged_changes_to_config_spec(configspec)

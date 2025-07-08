from ansible_collections.vmware.vmware.plugins.module_utils.vm.configurators._abstract import ConfiguratorBase
from ansible_collections.vmware.vmware.plugins.module_utils.vm._change_sets import ParameterChangeSet
from ansible_collections.vmware.vmware.plugins.module_utils.vm.configurators._cpu_memory import (
    VmCpuMemoryConfigurator
)
from ansible_collections.vmware.vmware.plugins.module_utils.vm.configurators._devices import (
    VmDeviceConfigurator
)
from ansible_collections.vmware.vmware.plugins.module_utils.vm.parameter_handlers._vm import (
    VmParameterHandler
)

class VmConfigurator(ConfiguratorBase):
    def __init__(self, vm, module):
        super().__init__(vm, module)
        self.change_set = ParameterChangeSet(self.vm, self.params)
        self.vm_handler = VmParameterHandler(self.vm, self.module)
        self.sub_configurators = [
            VmCpuMemoryConfigurator(self.vm, self.module),
            VmDeviceConfigurator(self.vm, self.module)
        ]

    def prepare_parameter_handlers(self):
        self.vm_handler.verify_parameter_constraints()
        for sub_configurator in self.sub_configurators:
            sub_configurator.prepare_parameter_handlers()

    def stage_configuration_changes(self):
        self.change_set.propagate_required_changes_from(self.vm_handler.get_parameter_change_set())
        for sub_configurator in self.sub_configurators:
            self.change_set.propagate_required_changes_from(sub_configurator.stage_configuration_changes())
        return self.change_set

    def apply_staged_changes_to_config_spec(self, configspec, datastore):
        if not self.change_set.changes_required:
            return

        self.vm_handler.populate_config_spec_with_parameters(configspec, datastore)
        for sub_configurator in self.sub_configurators:
            sub_configurator.apply_staged_changes_to_config_spec(configspec)

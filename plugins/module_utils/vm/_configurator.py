from ansible_collections.vmware.vmware.plugins.module_utils.vm._abstracts import ConfiguratorBase
from ansible_collections.vmware.vmware.plugins.module_utils.vm.cpu_memory._configurator import (
    VmCpuMemoryConfigurator
)
from ansible_collections.vmware.vmware.plugins.module_utils.vm.disks._configurator import (
    VmDiskConfigurator
)
from ansible_collections.vmware.vmware.plugins.module_utils.vm.devices._configurator import (
    DeviceConfigurator
)
from ansible_collections.vmware.vmware.plugins.module_utils.vm._handler import (
    VmHandler
)

class VmConfigurator(ConfiguratorBase):
    def __init__(self, vm, module):
        super().__init__(vm, module)
        self.vm_handler = VmHandler(self.vm, self.module)

        self.cpu_memory_configurator = VmCpuMemoryConfigurator(self.vm, self.module)
        self.device_configurator = DeviceConfigurator(self.vm, self.module)
        self.disk_configurator = VmDiskConfigurator(self.vm, self.module, self.controller_configurator.controller_handler)


    def validate_params_for_creation(self):
        self.vm_handler.validate_params_for_creation()
        self.cpu_memory_configurator.validate_params_for_creation()
        self.device_configurator.validate_params_for_creation()
        self.disk_configurator.validate_params_for_creation()

    def update_config_spec(self, configspec, datastore):
        self.vm_handler.update_config_spec_with_params(configspec, datastore, self.vm)
        self.cpu_memory_configurator.update_config_spec(configspec)
        self.device_configurator.update_config_spec(configspec)
        self.disk_configurator.update_config_spec(configspec)


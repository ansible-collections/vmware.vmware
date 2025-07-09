from ansible_collections.vmware.vmware.plugins.module_utils.vm.parameter_handlers._abstract import (
    ParameterHandlerBase,
)
from ansible_collections.vmware.vmware.plugins.module_utils.vm._errors import PowerCycleRequiredError


class CpuParameterHandler(ParameterHandlerBase):
    """Handler for CPU related parameters"""

    def __init__(self, module_context):
        super().__init__(module_context)
        self.cpu_params = self.module_context.params.get('cpu', {})

    def verify_parameter_constraints(self):
        self._validate_cpu_socket_relationship()
        if self.vm is None:
            self._validate_params_for_creation()

    def _validate_cpu_socket_relationship(self):
        cores = self.cpu_params.get('cores', 0)
        # this cannot be 0 since it is used as a denominator, but 1 will still work
        cores_per_socket = self.cpu_params.get('cores_per_socket', 1)

        if cores and cores_per_socket and cores % cores_per_socket != 0:
            self.module_context.fail_with_parameter_error(
                parameter_name="cpu.cores",
                message="cpu.cores must be a multiple of cpu.cores_per_socket",
                details={"cores": cores, "cores_per_socket": cores_per_socket}
            )

    def _validate_params_for_creation(self):
        self._validate_cpu_socket_relationship()
        if not self.cpu_params.get('cores'):
            self.module_context.fail_with_parameter_error(
                parameter_name="cpu.cores",
                message="cpu.cores attribute is mandatory for VM creation"
            )

    def populate_config_spec_with_parameters(self, configspec):
        """
        Update config spec with CPU and memory parameters
        """
        param_to_configspec_attr = {
            'enable_performance_counters': 'vPMCEnabled',
            'cores': 'numCPUs',
            'cores_per_socket': 'numCoresPerSocket',
            'enable_hot_add': 'cpuHotAddEnabled',
            'enable_hot_remove': 'cpuHotRemoveEnabled'
            }
        for param_name, configspec_attr in param_to_configspec_attr.items():
            value = self.cpu_params.get(param_name)
            if value is not None:
                setattr(configspec, configspec_attr, value)

    def compare_live_config_with_desired_config(self):
        """
        Check if current VM CPU/memory config differs from desired
        """
        self._check_cpu_changes_with_hot_add_remove()

        self.change_set.check_if_change_is_required('cores_per_socket', 'config.numCoresPerSocket', power_sensitive=True)
        self.change_set.check_if_change_is_required('enable_hot_add', 'config.cpuHotAddEnabled', power_sensitive=True)
        self.change_set.check_if_change_is_required('enable_hot_remove', 'config.cpuHotRemoveEnabled', power_sensitive=True)
        self.change_set.check_if_change_is_required('enable_performance_counters', 'config.vPMCEnabled', power_sensitive=True)

    def _check_cpu_changes_with_hot_add_remove(self):
        try:
            self.change_set.check_if_change_is_required('cores', 'config.hardware.numCPU', power_sensitive=True)
        except PowerCycleRequiredError:
            cores = self.cpu_params.get('cores')
            current_cores = self.vm.config.hardware.numCPU
            if cores < current_cores and not self.vm.config.cpuHotRemoveEnabled:
                self.module_context.fail_with_power_cycle_error(
                    parameter_name="cpu.cores",
                    message="CPUs cannot be decreased while the VM is powered on, "
                            "unless CPU hot remove is already enabled.",
                    details={"cores": cores, "current_cores": current_cores, "cpu_hot_remove_enabled": self.vm.config.cpuHotRemoveEnabled}
                )
            if cores > current_cores and not self.vm.config.cpuHotAddEnabled:
                self.module_context.fail_with_power_cycle_error(
                    parameter_name="cpu.cores",
                    message="CPUs cannot be increased while the VM is powered on, "
                            "unless CPU hot add is already enabled.",
                    details={"cores": cores, "current_cores": current_cores, "cpu_hot_add_enabled": self.vm.config.cpuHotAddEnabled}
                )
            # hot add/remove is allowed, so we can proceed with the change without power cycling
            self.change_set.power_cycle_required = False


class MemoryParameterHandler(ParameterHandlerBase):
    """Handler for memory related parameters"""

    def __init__(self, module_context):
        super().__init__(module_context)
        self.memory_params = self.module_context.params.get('memory', {})

    def verify_parameter_constraints(self):
        if self.vm is None:
            if not self.memory_params.get('size_mb'):
                self.module_context.fail_with_parameter_error(
                    parameter_name="memory.size_mb",
                    message="memory.size_mb attribute is mandatory for VM creation"
                )
        else:
            if self.memory_params.get('size_mb') < self.vm.config.hardware.memoryMB:
                self.module_context.fail_with_parameter_error(
                    parameter_name="memory.size_mb",
                    message="Memory cannot be decreased once added to a VM.",
                    details={"size_mb": self.memory_params.get('size_mb'), "current_size_mb": self.vm.config.hardware.memoryMB}
                )

    def populate_config_spec_with_parameters(self, configspec):
        """Update config spec with CPU and memory parameters"""
        param_to_configspec_attr = {
            'enable_hot_add': 'memoryHotAddEnabled',
            'size_mb': 'memoryMB',
            }
        for param_name, configspec_attr in param_to_configspec_attr.items():
            value = self.memory_params.get(param_name)
            if value is not None:
                setattr(configspec, configspec_attr, value)

    def compare_live_config_with_desired_config(self):
        """
        Check if current VM CPU/memory config differs from desired
        """
        self._check_memory_changes_with_hot_add()
        self.change_set.check_if_change_is_required('enable_hot_add', 'config.memoryHotAddEnabled', power_sensitive=True)
        return self.change_set

    def _check_memory_changes_with_hot_add(self):
        try:
            self.change_set.check_if_change_is_required('size_mb', 'config.hardware.memoryMB', power_sensitive=True)
        except PowerCycleRequiredError:
            size_mb = self.memory_params.get('size_mb')
            current_size_mb = self.vm.config.hardware.memoryMB
            if size_mb > current_size_mb and not self.vm.config.memoryHotAddEnabled:
                self.module_context.fail_with_power_cycle_error(
                    parameter_name="memory.size_mb",
                    message="Memory cannot be increased while the VM is powered on, "
                            "unless memory hot add is already enabled.",
                    details={"size_mb": size_mb, "current_size_mb": current_size_mb, "memory_hot_add_enabled": self.vm.config.memoryHotAddEnabled}
                )
            # hot add is allowed, so we can proceed with the change without power cycling
            self.change_set.power_cycle_required = False

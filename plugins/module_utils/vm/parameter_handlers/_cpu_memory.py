from ansible_collections.vmware.vmware.plugins.module_utils.vm.parameter_handlers._abstract import (
    ParameterHandlerBase,
)
from ansible_collections.vmware.vmware.plugins.module_utils.vm._change_sets import ParameterChangeSet
from ansible_collections.vmware.vmware.plugins.module_utils.vm._errors import PowerCycleRequiredError


class CpuParameterHandler(ParameterHandlerBase):
    """Handler for CPU related parameters"""

    def __init__(self, vm, module):
        super().__init__(vm, module)
        self.cpu_params = module.params.get('cpu', {})

    def verify_parameter_constraints(self):
        self._validate_cpu_socket_relationship()
        if self.vm is None:
            self._validate_params_for_creation()

    def _validate_cpu_socket_relationship(self):
        cores = self.cpu_params.get('cores', 0)
        # this cannot be 0 since it is used as a denominator, but 1 will still work
        cores_per_socket = self.cpu_params.get('cores_per_socket', 1)

        if cores and cores_per_socket and cores % cores_per_socket != 0:
            self.module.fail_json(
                msg="cpu.cores must be a multiple of cpu.cores_per_socket"
            )

    def _validate_params_for_creation(self):
        self._validate_cpu_socket_relationship()
        if not self.cpu_params.get('cores'):
            self.module.fail_json(
                msg="cpu.cores attribute is mandatory for VM creation"
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

    def get_parameter_change_set(self):
        """
        Check if current VM CPU/memory config differs from desired
        """
        change_set = ParameterChangeSet(self.vm, self.cpu_params)
        self._check_cpu_changes_with_hot_add_remove(change_set)

        change_set.check_if_change_is_required('cores_per_socket', 'config.numCoresPerSocket', power_sensitive=True)
        change_set.check_if_change_is_required('enable_hot_add', 'config.cpuHotAddEnabled', power_sensitive=True)
        change_set.check_if_change_is_required('enable_hot_remove', 'config.cpuHotRemoveEnabled', power_sensitive=True)
        change_set.check_if_change_is_required('enable_performance_counters', 'config.vPMCEnabled', power_sensitive=True)

        return change_set

    def _check_cpu_changes_with_hot_add_remove(self, change_set):
        try:
            change_set.check_if_change_is_required('cores', 'config.hardware.numCPU', power_sensitive=True)
        except PowerCycleRequiredError:
            cores = self.cpu_params.get('cores')
            current_cores = self.vm.config.hardware.numCPU
            if cores < current_cores and not self.vm.config.cpuHotRemoveEnabled:
                self.module.fail_json(
                    msg="CPUs cannot be decreased while the VM is powered on, "
                        "unless CPU hot remove is already enabled."
                )
            if cores > current_cores and not self.vm.config.cpuHotAddEnabled:
                self.module.fail_json(
                    msg="CPUs cannot be increased while the VM is powered on, "
                        "unless CPU hot add is already enabled."
                )
            # hot add/remove is allowed, so we can proceed with the change without power cycling
            change_set.power_cycle_required = False


class MemoryParameterHandler(ParameterHandlerBase):
    """Handler for memory related parameters"""

    def __init__(self, vm, module):
        super().__init__(vm, module)
        self.memory_params = module.params.get('memory', {})

    def verify_parameter_constraints(self):
        if self.vm is None:
            if not self.memory_params.get('size_mb'):
                self.module.fail_json(
                    msg="memory.size_mb attribute is mandatory for VM creation"
                )
        else:
            if self.memory_params.get('size_mb') < self.vm.config.hardware.memoryMB:
                self.module.fail_json(msg="Memory cannot be decreased once added to a VM.")

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

    def get_parameter_change_set(self):
        """
        Check if current VM CPU/memory config differs from desired
        """
        change_set = ParameterChangeSet(self.vm, self.memory_params)
        self._check_memory_changes_with_hot_add(change_set)
        change_set.check_if_change_is_required('enable_hot_add', 'config.memoryHotAddEnabled', power_sensitive=True)
        return change_set

    def _check_memory_changes_with_hot_add(self, change_set):
        try:
            change_set.check_if_change_is_required('size_mb', 'config.hardware.memoryMB', power_sensitive=True)
        except PowerCycleRequiredError:
            size_mb = self.memory_params.get('size_mb')
            current_size_mb = self.vm.config.hardware.memoryMB
            if size_mb > current_size_mb and not self.vm.config.memoryHotAddEnabled:
                self.module.fail_json(
                    msg="Memory cannot be increased while the VM is powered on, "
                        "unless memory hot add is already enabled."
                )
            # hot add is allowed, so we can proceed with the change without power cycling
            change_set.power_cycle_required = False

# class ResourceAllocationHandler(HardwareParameterHandler):
#     """Handler for resource allocation (shares, limits, reservations)"""

#     def update_config_spec(self, configspec):
#         memory_allocation = vim.ResourceAllocationInfo()
#         cpu_allocation = vim.ResourceAllocationInfo()
#         memory_allocation.shares = vim.SharesInfo()
#         cpu_allocation.shares = vim.SharesInfo()

#         # Memory resource allocation
#         self._configure_memory_allocation(memory_allocation)

#         # CPU resource allocation
#         self._configure_cpu_allocation(cpu_allocation)

#         configspec.memoryAllocation = memory_allocation
#         configspec.cpuAllocation = cpu_allocation

#     def _configure_memory_allocation(self, memory_allocation):
#         if self.hw_params.get('mem_shares_level'):
#             memory_allocation.shares.level = self.hw_params['mem_shares_level']
#         elif self.hw_params.get('mem_shares'):
#             memory_allocation.shares.level = 'custom'
#             memory_allocation.shares.shares = self.hw_params['mem_shares']

#         if self.hw_params.get('mem_limit'):
#             memory_allocation.limit = self.hw_params['mem_limit']
#         if self.hw_params.get('mem_reservation'):
#             memory_allocation.reservation = self.hw_params['mem_reservation']

#     def _configure_cpu_allocation(self, cpu_allocation):
#         if self.hw_params.get('cpu_shares_level'):
#             cpu_allocation.shares.level = self.hw_params['cpu_shares_level']
#         elif self.hw_params.get('cpu_shares'):
#             cpu_allocation.shares.level = 'custom'
#             cpu_allocation.shares.shares = self.hw_params['cpu_shares']

#         if self.hw_params.get('cpu_limit'):
#             cpu_allocation.limit = self.hw_params['cpu_limit']
#         if self.hw_params.get('cpu_reservation'):
#             cpu_allocation.reservation = self.hw_params['cpu_reservation']

#     def config_differs(self):
#         if not self.vm:
#             return True

#         return (
#             self.vm.config.cpuAllocation.shares.level != self.hw_params.get('cpu_shares_level') or
#             self.vm.config.cpuAllocation.shares.shares != self.hw_params.get('cpu_shares') or
#             self.vm.config.cpuAllocation.limit != self.hw_params.get('cpu_limit') or
#             self.vm.config.cpuAllocation.reservation != self.hw_params.get('cpu_reservation') or
#             self.vm.config.memoryAllocation.shares.level != self.hw_params.get('mem_shares_level') or
#             self.vm.config.memoryAllocation.shares.shares != self.hw_params.get('mem_shares') or
#             self.vm.config.memoryAllocation.limit != self.hw_params.get('mem_limit') or
#             self.vm.config.memoryAllocation.reservation != self.hw_params.get('mem_reservation')
#         )


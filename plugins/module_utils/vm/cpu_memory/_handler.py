from ansible_collections.vmware.vmware.plugins.module_utils.vm._abstracts import ParameterHandlerBase


class CpuParameterHandler(ParameterHandlerBase):
    """Handler for CPU related parameters"""

    def __init__(self, vm, module):
        super().__init__(vm, module)
        self.cpu_params = module.params.get('cpu', {})

    def _validate_cpu_socket_relationship(self):
        cores = self.cpu_params.get('cores', 0)
        # this cannot be 0 since it is used as a denominator, but 1 will still work
        cores_per_socket = self.cpu_params.get('cores_per_socket', 1)

        if cores and cores_per_socket and cores % cores_per_socket != 0:
            self.module.fail_json(
                msg="cpu.cores must be a multiple of cpu.cores_per_socket"
            )

    def validate_params_for_creation(self):
        self._validate_cpu_socket_relationship()
        if not self.cpu_params.get('cores'):
            self.module.fail_json(
                msg="cpu.cores attribute is mandatory for VM creation"
            )

    def validate_params_for_reconfiguration(self):
        self._validate_cpu_socket_relationship()

    def update_config_spec_with_params(self, configspec):
        """Update config spec with CPU and memory parameters"""
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

    def check_for_configuration_changes(self, power_cycle_allowed=False):
        """Check if current VM CPU/memory config differs from desired"""
        if not self.vm:
            return True

        if self._core_reconfiguration_required(power_cycle_allowed=power_cycle_allowed):
            return True

        if self._check_power_restricted_changes(power_cycle_allowed=power_cycle_allowed):
            return True

        return False

    def _check_power_restricted_changes(self, power_cycle_allowed=False):
        power_restricted_config = {
            "cpuHotAddEnabled": 'enable_hot_add',
            "cpuHotRemoveEnabled": 'enable_hot_remove',
            "vPMCEnabled": 'enable_performance_counters'
        }

        for config_attr, param_name in power_restricted_config.items():
            param_value = self.cpu_params.get(param_name)
            if param_value is None:
                continue

            if param_value == getattr(self.vm.config, config_attr):
                continue

            if power_cycle_allowed:
                return True
            else:
                self.module.fail_json(
                    msg=f"Configuring cpu.{param_name} is not supported while the VM is powered on."
                )

        return False

    def _core_reconfiguration_required(self, power_cycle_allowed=False):
        cores = self.cpu_params.get('cores')
        if not cores:
            return False

        current_cores = self.vm.config.hardware.numCPU
        if cores < current_cores and not (self.vm.config.cpuHotRemoveEnabled or power_cycle_allowed):
            self.module.fail_json(
                msg="CPUs cannot be decreased while the VM is powered on, "
                    "unless CPU hot remove is already enabled."
            )
        if cores > current_cores and not (self.vm.config.cpuHotAddEnabled or power_cycle_allowed):
            self.module.fail_json(
                msg="CPUs cannot be increased while the VM is powered on, "
                    "unless CPU hot add is already enabled."
            )

        return cores != current_cores


class MemoryParameterHandler(ParameterHandlerBase):
    """Handler for memory related parameters"""

    def __init__(self, vm, module):
        super().__init__(vm, module)
        self.memory_params = module.params.get('memory', {})

    def validate_params_for_creation(self):
        if not self.memory_params.get('size_mb'):
            self.module.fail_json(
                msg="memory.size_mb attribute is mandatory for VM creation"
            )

    def validate_params_for_reconfiguration(self):
        if self.vm.runtime.powerState != 'poweredOn':
            return

        size_mb = self.memory_params.get('size_mb')
        if size_mb:
            current_memory = self.vm.config.hardware.memoryMB
            if size_mb < current_memory:
                self.module.fail_json(msg="Memory cannot be decreased once added to a VM.")
            if size_mb > current_memory and not self.vm.config.memoryHotAddEnabled:
                self.module.fail_json(
                    msg="Memory cannot be increased while the VM is powered on, "
                        "unless memory hot add is already enabled."
                )

        if self.memory_params.get('enable_hot_add') is not None:
            self.module.fail_json(
                msg="Configuring memory.enable_hot_add is not supported while the VM is powered on."
            )

    def update_config_spec_with_params(self, configspec):
        """Update config spec with CPU and memory parameters"""
        param_to_configspec_attr = {
            'enable_hot_add': 'memoryHotAddEnabled',
            'size_mb': 'memoryMB',
            }
        for param_name, configspec_attr in param_to_configspec_attr.items():
            value = self.memory_params.get(param_name)
            if value is not None:
                setattr(configspec, configspec_attr, value)

    def params_differ_from_actual_config(self):
        """Check if current VM CPU/memory config differs from desired"""
        if not self.vm:
            return True

        return (
            self.vm.config.hardware.memoryMB != self.memory_params.get('size_mb') or
            self.vm.config.memoryHotAddEnabled != self.memory_params.get('enable_hot_add')
        )

    def get_params_requiring_power_cycle(self):
        _params = set([
            'enable_hot_add',
        ])
        if self.vm and (not self.vm.config.memoryHotAddEnabled):
            _params.add('size_mb')

        return _params

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


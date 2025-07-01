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
        if self.vm.runtime.powerState != 'poweredOn':
            return

        cores = self.cpu_params.get('cores')

        if cores:
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

        for param in ['enable_performance_counters', 'enable_hot_add', 'enable_hot_remove']:
            if self.cpu_params.get(param) is not None:
                self.module.fail_json(
                    msg=f"Configuring cpu.{param} is not supported while the VM is powered on."
                )

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

    def params_differ_from_actual_config(self):
        """Check if current VM CPU/memory config differs from desired"""
        if not self.vm:
            return True

        return (
            self.vm.config.hardware.numCPU != self.cpu_params.get('cores') or
            self.vm.config.cpuHotAddEnabled != self.cpu_params.get('enable_hot_add') or
            self.vm.config.cpuHotRemoveEnabled != self.cpu_params.get('enable_hot_remove') or
            self.vm.config.vPMCEnabled != self.cpu_params.get('enable_performance_counters')
        )


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


# class AdvancedOptionsHandler(HardwareParameterHandler):
#     """Handler for advanced hardware options"""

#     def update_config_spec(self, configspec):
#         # Handle simple mappings
#         mappings = {
#             'max_connections': 'maxMksConnections',
#             'nested_virt': 'nestedHVEnabled',
#             'boot_firmware': 'firmware',
#         }
#         for param_name, configspec_attr in mappings.items():
#             value = self.hw_params.get(param_name)
#             if value is not None:
#                 setattr(configspec, configspec_attr, value)

#         # Handle complex configurations
#         self._configure_secure_boot(configspec)
#         self._configure_virtualization_features(configspec)

#     def _configure_secure_boot(self, configspec):
#         secure_boot = self.hw_params.get('secure_boot')
#         if secure_boot is not None:
#             configspec.bootOptions = vim.vm.BootOptions()
#             configspec.bootOptions.efiSecureBootEnabled = secure_boot

#     def _configure_virtualization_features(self, configspec):
#         iommu = self.hw_params.get('iommu')
#         virt_based_security = self.hw_params.get('virt_based_security')

#         if iommu is not None or virt_based_security is not None:
#             configspec.flags = vim.vm.FlagInfo()

#             if iommu is not None:
#                 configspec.flags.vvtdEnabled = iommu
#             if virt_based_security is not None:
#                 configspec.flags.vbsEnabled = virt_based_security

#     def config_differs(self):
#         if not self.vm:
#             return True

#         return (
#             self.vm.config.maxMksConnections != self.hw_params.get('max_connections') or
#             self.vm.config.nestedHVEnabled != self.hw_params.get('nested_virt') or
#             self._secure_boot_differs(self.vm) or
#             self._virtualization_features_differ(self.vm) or
#             self.vm.config.firmware != self.hw_params.get('boot_firmware')
#         )

#     def _secure_boot_differs(self, vm):
#         secure_boot = self.hw_params.get('secure_boot')
#         if secure_boot is None:
#             return False

#         return (vm.config.bootOptions and
#                 vm.config.bootOptions.efiSecureBootEnabled != secure_boot)

#     def _virtualization_features_differ(self, vm):
#         iommu = self.hw_params.get('iommu')
#         virt_based_security = self.hw_params.get('virt_based_security')

#         if not vm.config.flags:
#             return iommu is not None or virt_based_security is not None

#         return (
#             (iommu is not None and vm.config.flags.vvtdEnabled != iommu) or
#             (virt_based_security is not None and vm.config.flags.vbsEnabled != virt_based_security)
#         )


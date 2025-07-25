"""
Main VM configuration orchestrator.

This module contains the Configurator class, which coordinates all parameter
handlers to validate, detect changes, and apply VM configuration modifications.
It implements a composite pattern where individual handlers track their own
changes and the configurator aggregates the overall state.
"""

try:
    from pyVmomi import vim
except ImportError:
    pass


class Configurator:
    """
    Main hardware configurator that orchestrates different hardware handlers.

    This class coordinates the VM configuration process by managing multiple
    parameter handlers (for example, CPU, memory, disks, controllers) and aggregating their
    change sets to determine overall VM configuration state. It follows a
    three-phase process: validation, change detection, and configuration application.
    """

    def __init__(self, device_tracker, vm, controller_handlers, handlers, change_set):
        """
        Initialize the configurator with all required components.

        Args:
            device_tracker: Service for tracking VMware devices and linking them to their place (ID) in the config spec
            vm: The vSphere VM object (or None for new VMs)
            controller_handlers: List of controller parameter handlers
            handlers: List of non-controller parameter handlers
            change_set: Master change set for aggregating all changes
        """
        self.device_tracker = device_tracker
        self.vm = vm
        # Controller handlers are separate from the other handlers because they need to
        # be processed and initiated before the disk params are parsed.
        self.controller_handlers = controller_handlers
        self.handlers = handlers
        self.all_handlers = self.controller_handlers + self.handlers
        self.change_set = change_set

    def prepare_parameter_handlers(self):
        """
        Validate all hardware parameters for VM creation.

        This method validates parameter constraints across all handlers and
        links existing VM devices to their appropriate handlers. Controller
        handlers are processed first because disk parameters depend on
        controllers being parsed and managed.

        Side Effects:
            - Calls verify_parameter_constraints() on all handlers
            - Links VM devices to their appropriate handlers
            - Sets change_set.unlinked_devices with devices that couldn't be linked
        """
        # Controller handlers need to be processed and initiated before the disk params are parsed
        for handler in self.controller_handlers:
            handler.verify_parameter_constraints()

        for handler in self.handlers:
            handler.verify_parameter_constraints()

        self.change_set.unlinked_devices = self._link_vm_devices_to_handlers()

    def stage_configuration_changes(self):
        """
        Check if current VM config differs from desired config.

        This method implements the change detection phase by having each handler
        compare its current configuration with the desired state. Individual
        handler change sets are then aggregated into the master change set.

        Returns:
            ParameterChangeSet: The master change set containing aggregated changes

        Side Effects:
            - Updates change_set.changes_required based on handler states
            - Updates change_set.power_cycle_required based on handler states
        """
        if self.change_set.unlinked_devices:
            self.change_set.changes_required = True

        for handler in self.all_handlers:
            handler.compare_live_config_with_desired_config()
            self.change_set.propagate_required_changes_from(handler.change_set)

        return self.change_set

    def apply_staged_changes_to_config_spec(self, configspec):
        """
        Update config spec with all hardware parameters.

        This method applies all staged changes to the VMware configuration
        specification. It first removes unlinked devices, then allows each
        handler with pending changes to modify the config spec.

        Args:
            configspec: VMware VM configuration specification to modify
            **kwargs: Additional parameters passed to handlers

        Side Effects:
            - Modifies configspec.deviceChange for device removals
            - Allows handlers to modify configspec for their changes
            - Tracks device IDs for error reporting
        """
        for device in self.change_set.unlinked_devices:
            self.device_tracker.track_device_id_from_spec(device)
            configspec.deviceChange.append(self._create_device_removal_spec(device))

        for handler in self.all_handlers:
            if handler.change_set.changes_required:
                handler.populate_config_spec_with_parameters(configspec)

    def _create_device_removal_spec(self, device):
        """
        Create a VMware device specification for removing a device. By definition,
        these devices are unmanaged and are not attached to any handler. So the method
        resides in the configurator.

        Args:
            device: VMware device object to remove

        Returns:
            vim.vm.device.VirtualDeviceSpec: Device removal specification
        """
        spec = vim.vm.device.VirtualDeviceSpec()
        spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.remove
        spec.device = device
        return spec

    def _link_vm_devices_to_handlers(self):
        """
        Link existing VM devices to their appropriate handlers.

        This method iterates over all devices on the VM and attempts to link
        them to handlers that can manage them. Devices that cannot be linked
        are considered unmanaged and will be removed from the VM.

        Device linking rules:
        - If a device type matches a handler's vim_device_class, try to link it
        - If linking fails, (for example, the unit number of the device does not match a known device) the device is unmanaged and should be removed
        - If no handler matches the device type, it's out of scope (ignored)

        Returns:
            list: List of unlinked devices that should be removed
        """
        if self.vm is None:
            return []

        unlinked_devices = []
        for device in self.vm.config.hardware.device:
            for handler in self.handlers:
                if not hasattr(handler, "vim_device_class"):
                    continue

                if not isinstance(device, handler.vim_device_class):
                    continue

                try:
                    handler.link_vm_device(device)
                    break
                except Exception:
                    pass

                unlinked_devices.append(device)
                break

        return unlinked_devices

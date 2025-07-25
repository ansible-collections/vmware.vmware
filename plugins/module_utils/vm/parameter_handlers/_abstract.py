"""
Abstract base classes for VM parameter handlers.

This module defines the base classes that establish the parameter handler
architecture. All parameter handlers follow a consistent three-phase pattern
for processing VM configuration parameters: validation, change detection,
and configuration specification population.

The architecture supports two main handler types:
- VM-aware handlers: Process VM-level settings (CPU, memory, metadata)
- Device-linked handlers: Manage parameters tied to specific devices (controllers, disks)
"""

from abc import ABC, abstractmethod


class AbstractParameterHandler(ABC):
    """
    Base class for all VM parameter handlers.

    This abstract class establishes the fundamental interface that all
    parameter handlers must implement. It defines the three-phase pattern
    for parameter processing and provides common initialization for error
    handling, parameter access, and change tracking.

    The three phases are:
    1. Parameter validation (verify_parameter_constraints)
    2. Change detection (compare_live_config_with_desired_config)
    3. Specification population (populate_config_spec_with_parameters)

    This pattern ensures consistent behavior across all parameter types
    while allowing specialized implementations for different VM components.

    Attributes:
        error_handler: Service for handling parameter validation errors
        params (dict): Module parameters containing desired configuration
        change_set: Service for tracking configuration changes
    """

    HANDLER_NAME = None

    def __init__(self, error_handler, params, change_set):
        """
        Initialize the parameter handler with common dependencies.

        Args:
            error_handler: Service for parameter validation error handling
            params (dict): Module parameters containing desired VM configuration
            change_set: Service for tracking configuration changes and requirements
        """
        if self.HANDLER_NAME is None or not self.HANDLER_NAME:
            raise NotImplementedError(
                "ParameterHandler subclasses must define the HANDLER_NAME attribute"
            )

        self.error_handler = error_handler
        self.params = params
        self.change_set = change_set

    @abstractmethod
    def verify_parameter_constraints(self):
        """
        Validate parameters for creation and modification operations.

        This method should check parameter values, combinations, and constraints
        specific to the handler's domain. It should validate both individual
        parameter values and cross-parameter relationships.

        Raises:
            Should call error_handler methods to report validation failures.
            The module will terminate if parameters are invalid.

        Note:
            This method should try to not perform vSphere API calls or access live VM state.
            It should only validate the input parameters themselves.
            This will allow the user to be alerted to invalid parameters more quickly, since
            configuration can take a non-trivial amount of time.
        """
        raise NotImplementedError

    @abstractmethod
    def populate_config_spec_with_parameters(self, configspec):
        """
        Update a configuration specification with parameters for this handler.

        This method should map module parameters to the appropriate VMware
        configuration specification fields. It should only set parameters
        that are explicitly provided by the user, allowing other handlers
        to manage their own configuration domains.

        Args:
            configspec: VMware configuration specification object to update

        Side Effects:
            Modifies the configspec object with parameter values.
            Should not modify parameters managed by other handlers.

        Note:
            For parameters not specified by the user, the handler should either
            omit them (preserving existing values) or use appropriate defaults.
        """
        raise NotImplementedError

    @abstractmethod
    def compare_live_config_with_desired_config(self):
        """
        Check if current VM configuration differs from desired configuration.

        This method should compare the current VM state with the desired
        state specified in the module parameters. It should identify what
        changes are needed without performing the actual changes.

        The method should use the change_set service to record detected
        differences. It should not validate parameters (that's done separately)
        or return information about what specific values differ.

        Side Effects:
            Updates change_set with detected configuration differences.
            May set flags for operations requiring VM power cycles.

        Note:
            This method should focus on detection, not validation or modification.
            It should work with live VM objects and vSphere API data.
        """
        raise NotImplementedError


class AbstractVmAwareParameterHandler(AbstractParameterHandler):
    """
    Base class for parameter handlers that work with VM-level configuration.

    This class extends AbstractParameterHandler for handlers that need access
    to the VM object itself, such as CPU, memory, and metadata handlers.
    These handlers typically work with VM-wide settings rather than individual
    devices.

    Attributes:
        vm: The VM object being configured (None for new VM creation)
    """

    def __init__(self, error_handler, params, change_set, vm):
        """
        Initialize a VM-aware parameter handler.

        Args:
            error_handler: Service for parameter validation error handling
            params (dict): Module parameters containing desired VM configuration
            change_set: Service for tracking configuration changes and requirements
            vm: VM object being configured (None for new VM creation)
        """
        super().__init__(error_handler, params, change_set)
        self.vm = vm


class AbstractDeviceLinkedParameterHandler(AbstractParameterHandler):
    """
    Base class for parameter handlers that manage VM hardware devices.

    This class extends AbstractParameterHandler for handlers that work with
    specific hardware devices like controllers and disks. It provides device
    linking capabilities and enforces that subclasses specify their VMware
    device class.

    Device-linked handlers must:
    1. Define vim_device_class to specify the VMware device type
    2. Implement link_vm_device() to associate existing devices with handler objects
    3. Use device_tracker for device identification and error reporting

    Attributes:
        vim_device_class: VMware device class this handler manages (must be overridden)
        device_type_to_sub_class_map (dict): Registry of device types to handler classes
        device_tracker: Service for device identification and error reporting
    """

    def __init__(self, error_handler, params, change_set, device_tracker):
        """
        Initialize a device-linked parameter handler.

        Args:
            error_handler: Service for parameter validation error handling
            params (dict): Module parameters containing desired device configuration
            change_set: Service for tracking configuration changes and requirements
            device_tracker: Service for device identification and error reporting

        Raises:
            NotImplementedError: If vim_device_class is not defined by subclass
        """
        super().__init__(error_handler, params, change_set)
        self.device_tracker = device_tracker

        if self.vim_device_class is None:
            raise NotImplementedError(
                "DeviceLinkedParameterHandler subclasses must define the vim_device_class property"
            )

    @property
    def vim_device_class(self):
        """
        Get the VMware device class this handler manages. This is a property so vim imports can
        be done lazily, and not cause sanity checks to fail.
        """
        raise NotImplementedError

    @property
    def device_type_to_sub_class_map(self):
        """
        Get a map of device types to their corresponding sub-classes. This is a property so vim imports can
        be done lazily, and not cause sanity checks to fail.

        Returns:
            dict: A dictionary mapping device types to their corresponding sub-classes.
        """
        return dict()

    @abstractmethod
    def link_vm_device(self, device):
        """
        Link a vSphere device to the handler's managed objects.

        This method should validate that the provided device matches an object
        managed by this handler and establish the connection between the VMware
        device and the handler's internal representation.

        For example, a disk handler should verify that the device is a disk
        it recognizes and link it to the appropriate disk object for change
        detection and configuration management.

        Args:
            device: VMware device object to link to the handler

        Raises:
            Should raise appropriate errors if the device doesn't match any
            managed objects or if linking fails for other reasons.

        Side Effects:
            Establishes connection between VMware device and handler objects.
            May update internal state to track device relationships.
        """
        raise NotImplementedError

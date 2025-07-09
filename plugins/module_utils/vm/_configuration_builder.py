"""
Configuration builder for VM management.

This module provides the main entry point for building or updating VM configurations through
the ConfigurationBuilder class, which creates and wires together all the necessary
services and handlers for VM configuration management.

It relies on the ConfigurationRegistry class to store and provide access to specific parameter handlers.
The registry should be initialized and populated before the ConfigurationBuilder is used.
"""

from ansible_collections.vmware.vmware.plugins.module_utils.vm._configurator import (
    Configurator,
)
from ansible_collections.vmware.vmware.plugins.module_utils.vm._change_set import (
    ParameterChangeSet,
)
import ansible_collections.vmware.vmware.plugins.module_utils.vm.services as services


class ConfigurationRegistry:
    """
    Registry for managing parameter handler classes.

    This registry stores and provides access to handler classes for different
    parameter types (regular handlers and controller handlers). It basically provides
    a list of classes that should be created and used to build the configuration.
    """

    def __init__(self):
        """
        Initialize the configuration registry.

        Sets up empty dictionaries for storing handler classes and change set classes.
        """
        self.handler_classes = {}
        self.controller_handler_classes = {}
        self.change_set_classes = {}

    def register_handler(self, handler_name, handler_class):
        """
        Register a parameter handler class.

        Args:
            handler_name (str): Unique name for the handler
            handler_class (type): Handler class to register
        """
        self.handler_classes[handler_name] = handler_class

    def get_handler_class(self, handler_name):
        """
        Retrieve a registered handler class by name.

        Args:
            handler_name (str): Name of the handler to retrieve

        Returns:
            type: The handler class

        Raises:
            ValueError: If handler_name is not registered. This is not a user
            facing error, but a developer facing error.
        """
        try:
            return self.handler_classes[handler_name]
        except KeyError:
            raise ValueError(f"Invalid handler type: {handler_name}")

    def register_controller_handler(self, handler_name, handler_class):
        """
        Register a controller parameter handler class.

        Controller handlers are processed before regular handlers because
        some parameter groups (like disks) depend on controllers being available,
        or at least parsed and validated.

        Args:
            handler_name (str): Unique name for the controller handler
            handler_class (type): Controller handler class to register
        """
        self.controller_handler_classes[handler_name] = handler_class

    def get_controller_handlers(self):
        """
        Get all registered controller handler classes.

        Returns:
            dict_values: Collection of controller handler classes
        """
        return self.controller_handler_classes.values()

    def get_handlers(self):
        """
        Get all registered parameter handler classes.

        Returns:
            dict_values: Collection of parameter handler classes
        """
        return self.handler_classes.values()


class ConfigurationBuilder:
    """
    Main builder class for VM configuration components.

    It creates a Configurator instance and wires together:
    - Services (classes that work outside a specific parameter group and generally help with the overall process)
    - Parameter handlers (classes designed to map/compare/validate specific parameter groups)
    - Change sets for tracking modifications (i.e. what parameters have changed and what actions are required to apply the changes)

    The Configurator can then be used to stage the changes and apply them to the VM.
    """

    def __init__(self, vm, module, configuration_registry: ConfigurationRegistry):
        """
        Initialize the configuration builder.

        Args:
            vm: The vSphere VM object (can be None for new VMs)
            module: The Ansible module instance
            configuration_registry: Registry containing handler classes
        """
        self.vm = vm
        self.module = module
        self.configuration_registry = configuration_registry
        self._controller_handlers = []

        # Create services with focused dependencies
        self.device_tracker = services.DeviceTracker()
        self.error_handler = services.ErrorHandler(self.module, self.device_tracker)
        self.placement = services.VmPlacement(self.module)

    def create_configurator(self):
        """
        Build and return a fully configured Configurator instance.

        This is the main entry point for creating a complete VM configuration
        system. It assembles all components and returns a ready-to-use configurator.

        Returns:
            Configurator: Fully initialized configurator with all handlers and services
        """
        return Configurator(
            device_tracker=self.device_tracker,
            vm=self.vm,
            controller_handlers=self._create_controller_handlers(),
            handlers=self._create_non_controller_handlers(),
            change_set=self._create_change_set(),
        )

    def _create_change_set(self):
        """
        Create a change set for tracking parameter modifications.

        Each handler gets its own change set to track changes specific to its
        parameter domain. The configurator aggregates these into overall state.

        Returns:
            ParameterChangeSet: New change set instance
        """
        return ParameterChangeSet(
            params=self.module.params,
            vm=self.vm,
            error_handler=self.error_handler,
        )

    def _create_non_controller_handlers(self):
        """
        Create all non-controller parameter handlers.

        These handlers manage VM parameters that don't involve device controllers,
        such as CPU, memory, metadata, and disks. Each handler gets its own
        change set to track changes independently.
        Non-controller handlers may refer back to the controller handlers, but are not
        required to do so.

        Returns:
            list: List of initialized parameter handlers
        """
        handlers = []

        # Disk handler - manages VM disk configuration
        disk_handler_class = self.configuration_registry.get_handler_class("disks")
        handlers.append(
            disk_handler_class(
                error_handler=self.error_handler,
                params=self.module.params,
                change_set=self._create_change_set(),
                device_tracker=self.device_tracker,
                controller_handlers=self._create_controller_handlers(),
            )
        )

        # CPU/Memory handler - manages VM resource allocation
        cpu_memory_handler_class = self.configuration_registry.get_handler_class(
            "cpu_memory"
        )
        handlers.append(
            cpu_memory_handler_class(
                error_handler=self.error_handler,
                params=self.module.params,
                change_set=self._create_change_set(),
                vm=self.vm,
            )
        )

        # Metadata handler - manages VM metadata and basic settings
        metadata_handler_class = self.configuration_registry.get_handler_class(
            "metadata"
        )
        handlers.append(
            metadata_handler_class(
                error_handler=self.error_handler,
                params=self.module.params,
                change_set=self._create_change_set(),
                vm=self.vm,
                placement=self.placement,
            )
        )

        return handlers

    def _create_controller_handlers(self):
        """
        Create all controller parameter handlers.

        Controller handlers are processed before other handlers because some
        parameters depend on controllers being available (for example, disks or CDROMS).
        This method caches the handlers to avoid recreating them multiple times.

        Returns:
            list: List of initialized controller handlers
        """
        if not self._controller_handlers:
            for (
                handler_class
            ) in self.configuration_registry.controller_handler_classes.values():
                self._controller_handlers.append(
                    handler_class(
                        error_handler=self.error_handler,
                        params=self.module.params,
                        change_set=self._create_change_set(),
                        device_tracker=self.device_tracker,
                    )
                )

        return self._controller_handlers

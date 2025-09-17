"""
Disk parameter handler for VM storage configuration.

This module provides the DiskParameterHandler class which manages virtual disk
configuration including disk creation, modification, and controller assignment.
It handles disk parameter validation, device linking, and VMware specification
generation for storage management.

The handler works closely with controller handlers to ensure proper disk
placement and validates disk parameters against available controllers.
"""

from ansible_collections.vmware.vmware.plugins.module_utils.vm.parameter_handlers._abstract import (
    AbstractDeviceLinkedParameterHandler,
)
from ansible_collections.vmware.vmware.plugins.module_utils.vm.objects._network_adapter import NetworkAdapter

try:
    from pyVmomi import vim
except ImportError:
    pass


class NetworkAdapterParameterHandler(AbstractDeviceLinkedParameterHandler):
    """
    Handler for virtual network adapter configuration parameters.

    This handler manages the creation, modification, and validation of virtual
    network adapters on VMs. It processes network adapter parameters, validates
    controller assignments, and generates VMware device specifications for network
    adapter operations.

    The handler requires coordination with controller handlers to ensure that
    network adapters are properly assigned to available controllers. It validates
    device specifications and ensures that all required controllers exist.

    Managed Parameters:
    - network_adapters: List of network adapter configurations with portgroup_name, adapter_type, and device_node

    Each network adapter configuration includes:
    - portgroup_name: Name of the portgroup or distributed virtual portgroup for this interface.
    - adapter_type: Type of the network adapter.
    - connect_at_power_on: Specifies whether or not to connect the network adapter when the virtual machine starts.
    - shares: The percentage of network resources allocated to the network adapter.
    - shares_level: The pre-defined allocation level of network resources for the network adapter.
    - reservation: The amount of network resources reserved for the network adapter.
    - limit: The maximum amount of network resources the network adapter can use.
    - mac_address: The MAC address of the network adapter.

    Attributes:
        network_adapters (list): List of NetworkAdapter objects representing desired network adapter configuration
    """

    HANDLER_NAME = "network_adapter"

    def __init__(
        self, error_handler, params, change_set, vm, device_tracker
    ):
        """
        Initialize the disk parameter handler.

        Args:
            error_handler: Service for parameter validation error handling
            params (dict): Module parameters containing network adapter configuration
            change_set: Service for tracking configuration changes and requirements
            vm: VM object being configured (None for new VM creation)
            device_tracker: Service for device identification and error reporting
        """
        super().__init__(error_handler, params, change_set, vm, device_tracker)
        self._check_if_params_are_defined_by_user("network_adapters", required_for_vm_creation=True)

        self.network_adapters = []

    @property
    def vim_device_class(self):
        """
        Get the VMware device class for this network adapter type.
        This is a parent class; network adapters are all subclasses of this vim class.
        """
        return vim.vm.device.VirtualEthernetCard

    def verify_parameter_constraints(self):
        """
        Validate disk parameter constraints and requirements.

        Parses disk parameters and validates that at least one disk is defined
        for VM creation or modification. Validates that all required controllers
        exist and that disk specifications are valid.

        Raises:
            Calls error_handler.fail_with_parameter_error() for invalid disk
            parameters, missing controllers, or missing disk definitions.
        """
        if len(self.network_adapters) == 0:
            try:
                self._parse_network_adapter_params()
            except ValueError as e:
                self.error_handler.fail_with_parameter_error(
                    parameter_name="network_adapters",
                    message="Error parsing network adapter parameters: %s" % str(e),
                    details={"error": str(e)},
                )

    def _parse_network_adapter_params(self):
        """
        Parse network adapter parameters and create NetworkAdapter objects.

        Processes the network adapter parameter list, validates specifications,
        and creates NetworkAdapter objects.

        Side Effects:
            Populates self.network_adapters with NetworkAdapter objects representing desired configuration.
        """
        network_params = self.params.get("network_adapters") or {}
        for label, network_param in network_params.items():
            network_adapter = NetworkAdapter(
                label=label,
                portgroup_name=network_param.get("portgroup_name"),
                adapter_type=network_param.get("adapter_type"),
                connect_at_power_on=network_param.get("connect_at_power_on"),
                connected=network_param.get("connected"),
                shares=network_param.get("shares"),
                shares_level=network_param.get("shares_level"),
                reservation=network_param.get("reservation"),
                limit=network_param.get("limit"),
                mac_address=network_param.get("mac_address"),
            )
            self.network_adapters.append(network_adapter)

    def populate_config_spec_with_parameters(self, configspec):
        """
        Populate VMware configuration specification with network adapter parameters.

        Adds network adapter device specifications to the configuration for both new
        network adapter creation and existing network adapter modification. Tracks device IDs
        for proper error reporting and device management.

        Args:
            configspec: VMware VirtualMachineConfigSpec to populate

        Side Effects:
            Adds network adapter device specifications to configspec.deviceChange.
            Tracks device IDs through device_tracker for error reporting.
        """
        for network_adapter in self.change_set.objects_to_add:
            self.device_tracker.track_device_id_from_spec(network_adapter)
            configspec.deviceChange.append(network_adapter.create_network_adapter_spec())
        for network_adapter in self.change_set.objects_to_update:
            self.device_tracker.track_device_id_from_spec(network_adapter)
            configspec.deviceChange.append(network_adapter.update_network_adapter_spec())

    def compare_live_config_with_desired_config(self):
        """
        Compare current VM disk configuration with desired configuration.

        Analyzes each disk to determine if it needs to be added, updated,
        or is already in sync with the desired configuration. Categorizes
        disks based on their current state and required changes.

        Returns:
            ParameterChangeSet: Updated change set with disk change requirements

        Side Effects:
            Updates change_set with disk objects categorized by required actions.
        """
        for network_adapter in self.network_adapters:
            if network_adapter._device is None:
                self.change_set.objects_to_add.append(network_adapter)
            elif network_adapter.linked_device_differs_from_config():
                self.change_set.objects_to_update.append(network_adapter)
            else:
                self.change_set.objects_in_sync.append(network_adapter)

        return self.change_set

    def link_vm_device(self, device):
        """
        Link a VMware network adapter device to the appropriate network adapter object.

        Matches a VMware network adapter device to the corresponding network adapter object based
        on controller key and unit number. This establishes the connection
        between the existing VM device and the handler's network adapter representation.

        Args:
            device: VMware VirtualEthernetCard device to link

        Raises:
            Exception: If no matching network adapter object is found for the device

        Side Effects:
            Sets the _device attribute on the matching disk object.
        """
        for network_adapter in self.network_adapters:
            if (
                isinstance(device, network_adapter.vim_device_class)
                and device.deviceInfo.label == network_adapter.label
            ):
                network_adapter._device = device
                return

        raise Exception(
            "Network adapter not found for device %s" % device.deviceInfo.label
        )

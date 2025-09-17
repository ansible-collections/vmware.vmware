"""
Network adapter object representation for VM configuration management.

This module provides the NetworkAdapter class, which represents a virtual network adapter
and handles the creation and modification of VMware network adapter specifications.
It manages network adapter properties such as portgroup_name, adapter_type, connect_at_power_on, shares, shares_level, reservation, limit, and mac_address.

It is meant to represent one of the items in the module's 'network_adapters' parameter.
"""

from random import randint

try:
    from pyVmomi import vim
except ImportError:
    pass

class NetworkAdapterPortgroup:
    def __init__(self, name, lookup_service):
        self.name = name
        try:
            self._portgroup = lookup_service.get_portgroup(name)
        except Exception:
            try:
                self._portgroup = lookup_service.get_distributed_virtual_portgroup(name)
            except Exception:
                raise ValueError("Portgroup %s not found" % name)

    def device_portgroup_differs_from_config(self, device_portgroup):
        if self._portgroup is None:
            return True

        return self._portgroup.name != device_portgroup.name


class NetworkAdapterResourceAllocation:
    def __init__(self, shares=None, shares_level=None, reservation=None, limit=None):
        self.shares = shares
        self.shares_level = shares_level
        self.reservation = reservation
        self.limit = limit

    def device_allocation_differs_from_config(self, device_allocation):
        _diff = False
        if not _diff and self.shares is not None:
            _diff = device_allocation.shares.level != 'custom' or device_allocation.shares.shares != self.shares

        if not _diff and self.shares_level is not None:
            _diff = device_allocation.shares.level != self.shares_level

        if not _diff and self.limit is not None:
            _diff = device_allocation.limit != self.limit

        if not _diff and self.reservation is not None:
            _diff = device_allocation.reservation != self.reservation

        return _diff

    def create_resource_allocation_spec(self):
        if self.shares is None and self.shares_level is None and self.limit is None and self.reservation is None:
            return None

        allocation = vim.ResourceAllocationInfo()
        if self.shares_level is not None or self.shares is not None:
            shares_info = vim.SharesInfo()
            if self.shares is not None:
                shares_info.level = "custom"
                shares_info.shares = self.shares
            else:
                shares_info.level = self.shares_level
            allocation.shares = shares_info

        if self.limit is not None:
            allocation.limit = self.limit

        if self.reservation is not None:
            allocation.reservation = self.reservation

        return allocation


class NetworkAdapter:
    """
    Represents a virtual network adapter for VM configuration.

    This class encapsulates the properties and behavior of a virtual network adapter,
    including its portgroup_name, adapter_type, connect_at_power_on, shares, shares_level, reservation, limit, and mac_address. It
    provides methods to create VMware device specifications for both new
    disk creation and existing disk modification.

    The disk maintains references to both the desired configuration and
    any existing VM device, enabling change detection and spec generation.

    Attributes:
        portgroup_name (str): Name of the portgroup or distributed virtual portgroup for this interface.
        adapter_type (str): Type of the network adapter.
        connect_at_power_on (bool): Specifies whether or not to connect the network adapter when the virtual machine starts.
        shares (int): The percentage of network resources allocated to the network adapter.
        shares_level (str): The pre-defined allocation level of network resources for the network adapter.
        reservation (int): The amount of network resources reserved for the network adapter.
        limit (int): The maximum amount of network resources the network adapter can use.
        mac_address (str): The MAC address of the network adapter.
        _spec: VMware device specification (when generated)
        _device: Existing VMware device object (when linked)
    """

    def __init__(self, label, portgroup_name, adapter_type, connect_at_power_on, connected, mac_address, resource_allocation: NetworkAdapterResourceAllocation):
        """
        Initialize a new disk object.

        Args:
            label (str): Label for the network adapter.
            portgroup_name (str): Name of the portgroup or distributed virtual portgroup for this interface.
            adapter_type (str): Type of the network adapter.
            connect_at_power_on (bool): Specifies whether or not to connect the network adapter when the virtual machine starts.
            shares (int): The percentage of network resources allocated to the network adapter.
            shares_level (str): The pre-defined allocation level of network resources for the network adapter.
            reservation (int): The amount of network resources reserved for the network adapter.
            limit (int): The maximum amount of network resources the network adapter can use.
            mac_address (str): The MAC address of the network adapter.

        Side Effects:
            Converts size string to kilobytes.
            Registers this disk with the controller.
        """
        self.label = label
        self.adapter_type = adapter_type
        try:
            _ = self.adapter_type_vim_class()
        except KeyError:
            raise ValueError("Unsupported network adapter type: %s" % self.adapter_type)

        self.portgroup_name = portgroup_name
        self.connect_at_power_on = connect_at_power_on
        self.connected = connected
        self.resource_allocation = resource_allocation
        self.mac_address = mac_address

        self._spec = None
        self._device = None

    @property
    def key(self):
        """
        Get the VMware device key for this disk.

        The device key is VMware's unique identifier for the disk. This
        property returns the key from either the existing device or the
        generated specification.

        Returns:
            int or None: VMware device key, or None if no device/spec exists
        """
        if self._device is not None:
            return self._device.key
        if self._spec is not None:
            return self._spec.device.key
        return None

    @property
    def name_as_str(self):
        """
        Get a human-readable name for this network adapter.

        Generates a descriptive name including the portgroup_name and adapter_type for easy identification in error messages and logs.

        Returns:
            str: Human-readable network adapter name (e.g., "Network Adapter - foo")
        """
        return "Network Adapter - %s - %s" % (self.label)

    @property
    def adapter_type_vim_class(self):
        """
        Get the VMware device class for this network adapter type.
        vim classes are defined as a property so the sdk is lazily loaded and the linter is happy.
        """
        NETWORK_ADAPTER_TYPE_TO_VIM_DEVICE_CLASS_MAP = {
            "pcnet32": vim.vm.device.VirtualPCNet32,
            "vmxnet2": vim.vm.device.VirtualVmxnet2,
            "vmxnet3": vim.vm.device.VirtualVmxnet3,
            "e1000": vim.vm.device.VirtualE1000,
            "e1000e": vim.vm.device.VirtualE1000e,
        }
        return NETWORK_ADAPTER_TYPE_TO_VIM_DEVICE_CLASS_MAP[self.adapter_type]

    def update_network_adapter_spec(self):
        """
        Create a VMware device specification for updating an existing network adapter.

        Generates a device specification that can be used to modify the
        properties of an existing network adapter on a VM. The specification includes
        all current network adapter properties.

        Returns:
            vim.vm.device.VirtualDeviceSpec: VMware device specification for network adapter update

        Side Effects:
            Caches the generated specification in self._spec
        """
        network_adapter_spec = vim.vm.device.VirtualDeviceSpec()
        network_adapter_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.edit
        network_adapter_spec.device = self._device

        if self.mac_address == 'automatic':
            network_adapter_spec.device.addressType = 'generated'
        elif self.mac_address is not None:
            network_adapter_spec.device.addressType = 'manual'
            network_adapter_spec.device.macAddress = self.mac_address

        self._update_network_adapter_spec_with_options(network_adapter_spec)
        self._spec = network_adapter_spec
        return network_adapter_spec

    def create_network_adapter_spec(self):
        """
        Create a VMware device specification for adding a new disk.

        Generates a device specification that can be used to add this network adapter
        to a VM. Includes file creation operation and assigns a temporary
        device key for VMware's internal tracking.
        The device key is overwritten by VMware when the network adapter is created.

        Returns:
            vim.vm.device.VirtualDeviceSpec: VMware device specification for network adapter creation

        Side Effects:
            Caches the generated specification in self._spec.
            Assigns a random negative device key for temporary identification.
        """
        network_adapter_spec = vim.vm.device.VirtualDeviceSpec()
        network_adapter_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
        network_adapter_spec.device = self.adapter_type_vim_class()
        network_adapter_spec.device.key = -randint(25000, 29999)

        network_adapter_spec.device.deviceInfo = vim.Description()
        network_adapter_spec.device.connectable = vim.vm.device.VirtualDevice.ConnectInfo()
        if self.mac_address == 'automatic' or self.mac_address is None:
            network_adapter_spec.device.addressType = 'generated'
        else:
            network_adapter_spec.device.addressType = 'manual'
            network_adapter_spec.device.macAddress = self.mac_address

        self._update_network_adapter_spec_with_options(network_adapter_spec)
        self._spec = network_adapter_spec
        return network_adapter_spec

    def _update_network_adapter_spec_with_options(self, network_adapter_spec):
        """
        Sets the network adapter spec options that are shared between create and update operations.

        Args:
            network_adapter_spec: VMware device specification to configure

        Side Effects:
            Modifies the provided network_adapter_spec with network adapter properties.
        """
        if self.connect_at_power_on is not None:
            network_adapter_spec.device.connectable.startConnected = self.connect_at_power_on

        if self.connected is not None:
            network_adapter_spec.device.connectable.connected = self.connected

        network_adapter_spec.device.deviceInfo.summary = self.name_as_str
        allocation_spec = self.resource_allocation.create_resource_allocation_spec()
        if allocation_spec is not None:
            network_adapter_spec.device.resourceAllocation = allocation_spec

    def linked_device_differs_from_config(self):
        """
        Check if the linked VM device differs from desired configuration.

        Compares the properties of an existing VM disk device with the
        desired configuration to determine if changes are needed. Used
        for change detection in existing VMs.

        Returns:
            bool: True if the device differs from desired config, False if in sync

        Note:
            Returns True if no device is linked (indicating creation is needed).
        """
        if not self._device:
            return True

        if self._linked_device_differs_from_config_mac_address():
            return True

        if self.resource_allocation.device_allocation_differs_from_config(self._device.resourceAllocation):
            return True

        return (
            self._device.connectable.startConnected != self.connect_at_power_on
            or self._device.connectable.connected != self.connected
            or self._device.deviceInfo.summary != self.name_as_str
        )

    def _linked_device_differs_from_config_mac_address(self):
        if self.mac_address == 'automatic':
            return self._device.addressType != 'generated'
        elif self.mac_address is not None:
            return self._device.addressType != 'manual' or self._device.macAddress != self.mac_address
        else:
            return False

    def _linked_device_differs_from_config_allocation(self):
        _diff = False
        if not _diff and self.shares is not None:
            _diff = self._device.resourceAllocation.shares.level != 'custom' or self._device.resourceAllocation.shares.shares != self.shares

        if not _diff and self.shares_level is not None:
            _diff = self._device.resourceAllocation.shares.level != self.shares_level

        if not _diff and self.limit is not None:
            _diff = self._device.resourceAllocation.limit != self.limit

        if not _diff and self.reservation is not None:
            _diff = self._device.resourceAllocation.reservation != self.reservation

        return _diff



#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2025, Ansible Cloud Team (@ansible-collections)
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function
__metaclass__ = type


DOCUMENTATION = r'''
---
module: _vm_stub
short_description: This is a partial implementation of a module. It is not intended for use.
description:
    - This module is currently in development. It is not intended for public use.
    - Although this module will attempt to validate your configuration, it is not feasible
      to validate all possible combinations of parameters. You may encounter errors when
      starting VMs with invalid configurations.
    - Error messages may not always be very helpful. Checking the vCenter task logs or
      VM edit settings page may have additional messages.

author:
    - Ansible Cloud Team (@ansible-collections)

options:
    state:
        description:
            - Whether to ensure the VM is present or absent.
        choices: [ present, absent]
        default: present
        type: str
    name:
        description:
            - Name of the virtual machine to work with.
            - Virtual machine names in vCenter are not necessarily unique, which may be problematic, see O(name_match).
            - This is required when the VM does not exist, or if O(moid) or O(uuid) is not supplied.
        type: str
    name_match:
        description:
            - If multiple virtual machines matching the name, use the first or last found.
        default: first
        choices: [ first, last ]
        type: str
    uuid:
        description:
            - UUID of the instance to manage if known, this is VMware's unique identifier.
            - This is required if O(name) or O(moid) is not supplied.
        type: str
    moid:
        description:
            - Managed Object ID of the instance to manage if known, this is a unique identifier only within a single vCenter instance.
            - This is required if O(name) or O(uuid) is not supplied.
        type: str
    use_instance_uuid:
        description:
            - Whether to use the VMware instance UUID rather than the BIOS UUID.
        default: false
        type: bool
    folder:
        description:
            - Destination folder, absolute or relative path to find an existing guest.
            - Should be the full folder path, with or without the 'datacenter/vm/' prefix
            - For example 'datacenter_name/vm/path/to/folder' or 'path/to/folder'.
            - You cannot use this module to modify the placement of a VM once it has been created.
        type: str
        required: false
        aliases: [ vm_folder ]

    # placement:
    datacenter:
        description:
            - The datacenter in which to place the VM.
            - This is required when creating a new VM.
            - You cannot use this module to modify the placement of a VM once it has been created. This parameter is ignored if the VM already exists.
        type: str
        required: false
        aliases: [ datacenter_name ]
    cluster:
        description:
            - The cluster in which to place the VM.
            - This is required when creating a new VM.
            - You cannot use this module to modify the placement of a VM once it has been created. This parameter is ignored if the VM already exists.
        type: str
        required: false
        aliases: [ cluster_name ]
    resource_pool:
        description:
            - The resource pool in which to place the VM.
            - This is required when creating a new VM.
            - You cannot use this module to modify the placement of a VM once it has been created. This parameter is ignored if the VM already exists.
        type: str
        required: false
    esxi_host:
        description:
            - The ESXi host on which to place the VM.
            - This is required when creating a new VM.
            - You cannot use this module to modify the placement of a VM once it has been created. This parameter is ignored if the VM already exists.
        type: str
        required: false
    datastore:
        description:
            - The datastore on which to place the VM.
            - This is required when creating a new VM, or when creating new disks.
            - You cannot use this module to modify the placement of a VM once it has been created. This parameter is ignored if the VM or disk already exists.
        type: str
        required: false
    datastore_cluster:
        description:
            - The datastore cluster on which to place the VM.
            - This is required when creating a new VM.
            - This is required when creating a new VM, or when creating new disks.
            - You cannot use this module to modify the placement of a VM once it has been created. This parameter is ignored if the VM or disk already exists.
        type: str
        required: false

    guest_id:
        description:
            - The guest ID of the VM.
            - Guest IDs are pre-defined by VMware. For example see
              https://developer.broadcom.com/xapis/vsphere-web-services-api/latest/vim.vm.GuestOsDescriptor.GuestOsIdentifier.html
            - This is required when creating a new VM.
        type: str
        required: false

    allow_power_cycling:
        description:
            - Whether to allow the VM to be powered off and on when required by the changes detected by the module.
            - For example, if the module detects CPU changes and hot add is not enabled, you can enable this
              parameter to allow the VM to be powered off, updated, and then powered on automatically.
            - If this is set to false, a failure will occur if the VM needs to be powered off before changes can be applied.
            - A "hard" power off is performed when the VM is powered off. If you do not want this, you could use this module in check mode,
              M(vmware.vmware.vm_powerstate) module to power off the VM if needed, and then this module again to apply the changes .
        type: bool
        required: false
        default: false
    timeout:
        description:
            - The timeout in seconds for the module to wait for the VM to be created or updated.
        type: int
        required: false
        default: 600

    # resources
    cpu:
        description:
            - Options related to CPU resource allocation.
            - This is required when creating a new VM.
        type: dict
        required: false
        suboptions:
            cores:
                description:
                    - The number of CPU cores to add to the VM.
                    - This is required when creating a new VM.
                type: int
                required: false
            cores_per_socket:
                description:
                    - The number of cores per socket to use for the VM.
                    - If this is defined, O(cpu.cores) must be a multiple of O(cpu.cores_per_socket).
                type: int
                required: false
            enable_hot_add:
                description:
                    - Whether to enable CPU hot add. This allows you to add CPUs to the VM while it is powered on.
                    - Encryption (O(vm_options.enable_encryption)) cannot be enabled if CPU hot-add is enabled.
                      You must disable CPU hot-add in a separate module call before you can attempt to enable encryption.
                type: bool
                required: false
            enable_hot_remove:
                description:
                    - Whether to enable CPU hot remove. This allows you to remove CPUs from the VM while it is powered on.
                    - Encryption (O(vm_options.enable_encryption)) cannot be enabled if CPU hot-remove is enabled.
                      You must disable CPU hot-remove in a separate module call before you can attempt to enable encryption.
                type: bool
                required: false
            reservation:
                description:
                    - The amount of CPU resource that is guaranteed available to the virtual machine.
                type: int
                required: false
            limit:
                description:
                    - The maximum amount of CPU resources the VM can use.
                type: int
                required: false
            shares:
                description:
                    - The custom number of shares of CPU allocated to this virtual machine.
                    - You can set O(cpu.shares_level) and omit this parameter to use a pre-defined value.
                    - If this is defined, O(cpu.shares_level) will be ignored.
                type: int
                required: false
            shares_level:
                description:
                    - The allocation level of CPU resources for the virtual machine.
                    - If O(cpu.shares) is defined, O(cpu.shares_level) will automatically be set to 'custom' and this parameter will be ignored.
                type: str
                required: false
                choices: [ low, normal, high ]
            enable_performance_counters:
                description:
                    - Whether to enable Virtual CPU Performance Monitoring Counters (VPMC).
                type: bool
                required: false

    memory:
        description:
            - Options related to memory resource allocation.
            - This is required when creating a new VM.
        type: dict
        required: false
        suboptions:
            size_mb:
                description:
                    - The amount of memory to add to the VM.
                    - Memory cannot be changed while the VM is powered on, unless memory hot add is already enabled.
                    - This parameter is required when creating a new VM.
                type: int
                required: false
            shares:
                description:
                    - The custom number of shares of memory allocated to this virtual machine.
                    - You can set O(memory.shares_level) and omit this parameter to use a pre-defined value.
                    - If this is defined, O(memory.shares_level) will be ignored.
                type: int
                required: false
            shares_level:
                description:
                    - The allocation level of memory resources for the virtual machine.
                    - If O(memory.shares) is defined, O(memory.shares_level) will automatically be set to 'custom' and this parameter will be ignored.
                type: str
                required: false
                choices: [ low, normal, high ]
            enable_hot_add:
                description:
                    - Whether to enable memory hot add. This allows you to add memory to the VM while it is powered on.
                    - Encryption (O(vm_options.enable_encryption)) cannot be enabled if memory hot-add is enable.
                      You must disable memory hot-add in a separate module call before you can attempt to enable encryption.
                type: bool
                required: false
            reservation:
                description:
                    - The amount of memory resource that is guaranteed available to the VM.
                    - Only one of O(memory.reservation) or O(memory.reserve_all_memory) can be set.
                    - This value must be less than or equal to the VMs total memory in MB.
                type: int
                required: false
            reserve_all_memory:
                description:
                    - Whether to reserve (lock) all memory allocated for the VM.
                    - Only one of O(memory.reservation) or O(memory.reserve_all_memory) can be set.
                    - This will cause VMware to reserve all memory allocated for the VM, meaning that the
                      memory will not be available to other VMs even if this VM is not actively using it.
                type: bool
                required: false
            limit:
                description:
                    - The maximum amount of memory the VM can use.
                type: int
                required: false


    disks:
        description:
            - Disks to manage on the VM.
            - If a disk is not specified, it will be removed from the VM.
            - Reducing disk size is not supported.
            - At least one disk is required when creating a new VM.
            - Controllers (except IDE) referenced by the O(disks[].device_node) parameter must be configured in the corresponding controller section.
        type: list
        elements: dict
        required: false
        suboptions:
            size:
                description:
                    - The size of the disk.
                    - The format of this value should be like '100gb' or '100mb'.
                    - Supported units are 'kb', 'mb', 'gb', 'tb'.
                    - Note that disk size cannot be decreased at any time.
                type: str
                required: true
            provisioning:
                description:
                    - The provisioning type for the disk.
                    - This is only used when creating a new disk. If it is specified for an existing disk, it is ignored.
                type: str
                required: false
                choices: [ thin, thick, eagerzeroedthick ]
            mode:
                description:
                    - The mode of the disk. Supported values are dependent on the disk storage location.
                    - C(persistent) is supported by all disk backing types. In the UI, this is called "dependent".
                    - C(persistent) means changes are immediately and permanently written to the virtual disk.
                    - C(independent_persistent) means the same as C(persistent), but not affected by snapshots.
                    - C(independent_nonpersistent) means the same as C(nonpersistent), but not affected by snapshots.
                    - C(append) means changes are not written to the virtual disk.
                    - C(nonpersistent) means changes  to virtual disk are made to a redo log and discarded at power off.
                    - C(undoable) means changes are made to a redo log, but you are given the option to commit or undo.
                    - If this is not specified, new disks will be created with C(persistent) mode.
                    - If you chose a mode that is not supported by the disk storage type, the module
                      will fail with an incompatible device backing error.
                type: str
                required: false
                choices: [ persistent, independent_persistent, independent_nonpersistent, append, nonpersistent, undoable ]
            device_node:
                description:
                    - Specifies the controller, bus, and unit number of the disk.
                    - The format of this value should be like 'SCSI(0:0)' or 'IDE(0:1)'.
                    - Disk controllers referenced in this attribute must be configured in the corresponding controller section.
                      The exception to this are the two IDE controllers, which are automatically added to the VM.
                type: str
                required: true
            enable_sharing:
                description:
                    - If true, disk sharing will be enabled. This enabled multi-writer mode, allowing multiple VMs to write to the same disk.
                    - If false, disk sharing will be disabled. This will cause the disk to be exclusive to the VM.
                    - If this is not specified, new disks will be created with sharing disabled.
                    - Sharing depends on the storage backing type. If your storage does not support sharing, enabling sharing will cause
                      the module to fail with an incompatible device backing error.
                type: bool
                required: false
            datastore:
                description:
                    - The datastore or datastore cluster where this disk should be stored. The host that
                      the VM is running on must have access to this datastore.
                    - This can be a name or a MOID. If using a name, the first datastore (or cluster) that matches the name will be used.
                    - If this is not specified, the disk will be created on the same datastore as the VM.
                    - This is only used when creating a new disk. If it is specified for an existing disk, it is ignored.
                    - Only one of O(disks[].datastore) or O(disks[].filename) can be set.
                type: str
                required: false
            filename:
                description:
                    - The filename of an existing disk to attach to the VM. This file must already exist on the datastore.
                    - An example filename is '[my-datastore-name] some/folder/path/My.vmdk'.
                    - Only one of O(disks[].datastore) or O(disks[].filename) can be set.
                type: str
                required: false

    cdroms:
        description:
            - CD-ROMs to manage on the VM.
            - If a CD-ROM is not specified, it will be removed from the VM.
        type: list
        elements: dict
        required: false
        suboptions:
            connect_at_power_on:
                description:
                    - Whether to connect the CD-ROM to the VM at power on.
                    - This parameter is ignored if C(client_device_mode) is set.
                    - If this is set to true, the CD-ROM will be connected to the VM at power on.
                    - If this is set to false, the CD-ROM will remain disconnected from the VM at power on.
                type: bool
                required: false
            iso_media_path:
                description:
                    - The ISO media path to use for the CD-ROM. This must be a valid datastore path that is accessible to the host of the VM.
                    - One of O(cdroms[].iso_media_path) or O(cdroms[].client_device_mode) must be set.
                    - A datastore path should be like '[my-datastore-name] some/folder/path/My.iso'.
                    - A content library item can be referenced by its full datastore path only.
                type: str
                required: false
            client_device_mode:
                description:
                    - The mode of the CD-ROM when acting as a client device.
                    - One of O(cdroms[].iso_media_path) or O(cdroms[].client_device_mode) must be set.
                    - If this is not set and the CD-ROM is being created, passthrough will be used.
                    - C(passthrough) is similar to the 'client' mode in the community.vmware.vmware_guest module.
                type: str
                required: false
                choices: [ passthrough, emulated ]
            device_node:
                description:
                    - Specifies the controller, bus, and unit number of the CD-ROM. Only SATA and IDE controllers are supported.
                    - The format of this value should be like 'SATA(0:0)' or 'IDE(0:1)'.
                    - CD-ROM controllers referenced in this attribute must be configured in the corresponding controller section.
                      The exception to this are the two IDE controllers, which are automatically added to the VM.
                    - The device node should be unique across all other devices (CD-ROMs, disks, etc.) on the VM.
                type: str
                required: true

    scsi_controllers:
        description:
            - SCSI device controllers to manage on the VM.
            - If a controller is not specified, it will be removed from the VM.
            - You may only specify four SCSI controllers per VM.
            - Controllers are added to the VM in the order they are specified. For example, the first controller specified
              will be assigned bus 0, the second controller will be assigned bus 1, etc.
            - Valid unit numbers for SCSI controllers are 0-15, except for the reserved unit 7.
        type: list
        elements: dict
        required: false
        suboptions:
            bus_number:
                description:
                    - The bus number of the SCSI controller. This is used to identify the controller and is required.
                    - Valid bus numbers are 0 to 3, inclusive.
                type: int
                required: true
            controller_type:
                description:
                    - The type of the controller.
                type: str
                required: true
                choices: [ lsilogic, paravirtual, buslogic, lsilogicsas ]
            bus_sharing:
                description:
                    - The bus sharing mode of the controller.
                    - If this is not set, noSharing will be used for new controllers.
                type: str
                required: false
                choices: [ noSharing, virtualSharing, physicalSharing ]

    nvme_controllers:
        description:
            - NVMe device controllers to manage on the VM.
            - If a controller is not specified, it will be removed from the VM.
            - You may only specify four NVMe controllers per VM.
            - Controllers are added to the VM in the order they are specified. For example, the first controller specified
              will be assigned bus 0, the second controller will be assigned bus 1, etc.
            - Valid unit numbers for NVMe controllers are 0-63.
        type: list
        elements: dict
        required: false
        suboptions:
            bus_number:
                description:
                    - The bus number of the NVMe controller. This is used to identify the controller and is required.
                    - Valid bus numbers are 0 to 3, inclusive.
                type: int
                required: true
            bus_sharing:
                description:
                    - The bus sharing mode of the controller.
                    - If this is not set, noSharing will be used for new controllers.
                type: str
                choices: [ noSharing, exclusive ]

    sata_controllers:
        description:
            - SATA controllers to manage on the VM.
            - You may only specify four SATA controllers per VM.
            - Valid unit numbers for SATA controllers are 0-29.
        type: list
        elements: dict
        required: false
        suboptions:
            bus_number:
                description:
                    - The bus number of the SATA controller. This is used to identify the controller and is required.
                    - Valid bus numbers are 0 to 3, inclusive.
                type: int
                required: true

    # TODO: add support for USB controllers
    usb_controllers:
        description:
            - USB device controllers to manage on the VM.
            - If a controller is not specified, it will be removed from the VM.
            - You may only specify two USB controllers per VM.
            - Controllers are added to the VM in the order they are specified. For example, the first controller specified
              will be assigned bus 0, the second controller will be assigned bus 1, etc.
        type: list
        elements: dict
        required: false
        suboptions:
            controller_type:
                description:
                    - The type of the controller.
                type: str
                choices: [ usb2, usb3 ]
                default: usb3

    network_adapter_remove_unmanaged:
        description:
            - Whether to remove network adapters that are not specified in the O(network_adapters) parameter.
            - If this is set to true, any network adapters that are not specified in the O(network_adapters) parameter will be removed.
            - If this is set to false, the module will ignore network adapters beyond those listed in the O(network_adapters) parameter.
        type: bool
        required: false
        default: false
    network_adapters:
        description:
            - A list of network adapters to manage on the VM.
            - Due to limitations in the VMware API, you cannot change the type of a network adapter once it has been created using
              this module.
            - The network adapter types defined in this parameter must match the types of any existing
              adapters on the VM, in the same order that they are specified. For example, the first adapter in this list
              must have the same type as the first adapter attached to the VM (if one exists).
            - Any adapters in this list that do not exist on the VM will be created.
            - Portgroups must already exist; this module does not create them.
        type: list
        elements: dict
        required: false
        suboptions:
            network:
                description:
                    - The name or MOID of the standard or distributed virtual portgroup for this interface.
                    - The portgroup must already exist.
                type: str
                required: true
            adapter_type:
                description:
                    - The type of the adapter.
                    - This is required when creating a new adapter.
                    - Note that this cannot be changed once the adapter has been created.
                type: str
                required: false
                choices: [ e1000, e1000e, pcnet32, vmxnet2, vmxnet3, sriov ]
            connected:
                type: bool
                description:
                    - Indicates whether the NIC is currently connected.
                required: false
            connect_at_power_on:
                type: bool
                description:
                    - Specifies whether or not to connect the network adapter when the virtual machine starts.
                required: false
            shares:
                type: int
                description:
                    - The percentage of network resources allocated to the network adapter.
                    - If setting this, it should be between 0 and 100.
                    - Only one of O(network_adapters[].shares) or O(network_adapters[].shares_level) can be set.
                required: false
            shares_level:
                type: str
                description:
                    - The pre-defined allocation level of network resources for the network adapter.
                    - Only one of O(network_adapters[].shares) or O(network_adapters[].shares_level) can be set.
                required: false
                choices: [ low, normal, high ]
            reservation:
                type: int
                description:
                    - The amount of network resources reserved for the network adapter.
                    - The unit is Mbps.
                required: false
            limit:
                type: int
                description:
                    - The maximum amount of network resources the network adapter can use.
                    - The unit is Mbps.
                required: false
            mac_address:
                type: str
                description:
                    - The MAC address of the network adapter.
                    - If you want to use a generated or automatic mac address, set this to 'automatic'.
                    - If not specified and this is a new adapter, a random MAC address will be assigned.
                    - If not specified and this is an existing adapter, the MAC address will not be changed.
                required: false

    vm_options:
        description:
            - Advanced and miscellaneous options for the VM, including things like BIOS settings,
              remote console settings, and encryption settings.
        type: dict
        required: false
        suboptions:
            maximum_remote_console_sessions:
                description:
                    - The maximum number of remote console sessions that can be established to the VM.
                    - Must be a value between 0 and 40
                type: int
                required: false
            enable_encryption:
                description:
                    - Whether to enable encryption for the VM.
                    - If this is set to false, you can still modify O(vm_options.encrypted_vmotion) and O(vm_options.encrypted_fault_tolerance),
                      but those settings will have no effect on the VM.
                    - Secure boot (O(vm_options.enable_secure_boot)) is not compatible with encryption.
                    - Encryption requires EFI boot firmware (O(vm_options.boot_firmware)).
                    - Memory hot-add (O(memory.enable_hot_add)) and CPU hot-add/hot-remove (O(cpu.enable_hot_add) or O(cpu.enable_hot_remove))
                      must be disabled before you can enable encryption.
                type: bool
                required: false
            encrypted_vmotion:
                description:
                    - Modify how the VM can be migrated using vMotion, if encryption is enabled.
                    - C(disabled) means do not use encrypted vMotion, even if available.
                    - C(opportunistic) means use encrypted vMotion if source and destination hosts support it, fall back to unencrypted vMotion otherwise.
                    - C(required) means allow only encrypted vMotion. If the source or destination host does not support vMotion
                      encryption, do not allow the vMotion to occur.
                type: str
                required: false
                choices: [ disabled, opportunistic, required ]
            encrypted_fault_tolerance:
                description:
                    - Modify how the VM's Fault Tolerance (FT) replication is encrypted, if encryption is enabled.
                    - C(disabled) means do not turn on encrypted Fault Tolerance (FT) replication logging.
                    - C(opportunistic) means turn on encryption only if both sides are capable.
                      The VM is allowed to move to an older host that does not support encrypted FT logging.
                    - C(required) means run on primary/secondary FT hosts such that both hosts support encrypted FT logging.
                type: str
                required: false
                choices: [ disabled, opportunistic, required ]
            enable_hardware_assisted_virtualization:
                description:
                    - Whether to enable hardware assisted virtualization.
                    - If true, the VM will be able to use hardware assisted, or nested, virtualization.
                type: bool
                required: false
            enable_io_mmu:
                description:
                    - Whether to enable IO Memory Management Unit (IO MMU).
                type: bool
                required: false
            enable_virtual_based_security:
                description:
                    - Whether to enable the Virtualization Based Security feature for Windows on at least ESXi 6.7, hardware version 14.
                    - Supported Guest OS are Windows 10 64 bit, Windows Server 2016, Windows Server 2019 and later.
                    - The firmware of virtual machine must be EFI and secure boot must be enabled.
                    - Virtualization Based Security depends on nested virtualization and Intel Virtualization Technology for Directed I/O.
                type: bool
                required: false
            enable_secure_boot:
                description:
                    - Whether to enable secure boot for the VM.
                    - Only (U)EFI boot firmware is supported.
                    - Secure boot cannot be enabled if encryption (O(vm_options.enable_encryption)) is also enabled.
                type: bool
                required: false
            boot_firmware:
                description:
                    - The boot firmware to use for the VM.
                    - Encryption (O(vm_options.enable_encryption)) can only be enabled when boot firmware is EFI.
                type: str
                required: false
                choices: [ bios, efi ]

extends_documentation_fragment:
    - vmware.vmware.base_options
'''

EXAMPLES = r'''
'''

RETURN = r'''
vm:
    description:
        - Information about the target VM
    returned: On success
    type: dict
    sample:
        moid: vm-79828,
        name: test-d9c1-vm
'''
try:
    from pyVmomi import vim, vmodl
except ImportError:
    pass

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.common.text.converters import to_native

from ansible_collections.vmware.vmware.plugins.module_utils._module_pyvmomi_base import (
    ModulePyvmomiBase
)
from ansible_collections.vmware.vmware.plugins.module_utils.argument_spec import (
    base_argument_spec
)
from ansible_collections.vmware.vmware.plugins.module_utils._vsphere_tasks import (
    TaskError, RunningTaskMonitor
)
from ansible_collections.vmware.vmware.plugins.module_utils.vm.services._placement import vm_placement_argument_spec
from ansible_collections.vmware.vmware.plugins.module_utils.vm.parameter_handlers import (
    _metadata,
    _cpu,
    _memory,
    _vm_options,
)
from ansible_collections.vmware.vmware.plugins.module_utils.vm.parameter_handlers.device_linked import (
    _disks,
    _controllers,
    _network_adapters,
    _cdroms,
)
from ansible_collections.vmware.vmware.plugins.module_utils.vm._configuration_builder import (
    ConfigurationRegistry,
    ConfigurationBuilder
)


class VmModule(ModulePyvmomiBase):
    def __init__(self, module):
        super().__init__(module)
        try:
            self.vm = self.get_vms_using_params(fail_on_missing=False)[0]
        except IndexError:
            self.vm = None

        if self.params['state'] == 'present':
            self._init_configuration_registry()
            self._init_configuration_builder()

    def _init_configuration_registry(self):
        self.configuration_registry = ConfigurationRegistry()
        self.configuration_registry.register_vm_aware_handler(_metadata.MetadataParameterHandler)
        self.configuration_registry.register_vm_aware_handler(_cpu.CpuParameterHandler)
        self.configuration_registry.register_vm_aware_handler(_memory.MemoryParameterHandler)
        self.configuration_registry.register_vm_aware_handler(_vm_options.VmOptionsParameterHandler)

        self.configuration_registry.register_device_linked_handler(_disks.DiskParameterHandler)
        self.configuration_registry.register_device_linked_handler(_network_adapters.NetworkAdapterParameterHandler)
        self.configuration_registry.register_device_linked_handler(_cdroms.CdromParameterHandler)

        self.configuration_registry.register_controller_handler(_controllers.ScsiControllerParameterHandler)
        self.configuration_registry.register_controller_handler(_controllers.NvmeControllerParameterHandler)
        self.configuration_registry.register_controller_handler(_controllers.SataControllerParameterHandler)
        self.configuration_registry.register_controller_handler(_controllers.IdeControllerParameterHandler)

    def _init_configuration_builder(self):
        self.configuration_builder = ConfigurationBuilder(self.vm, self.module, self.configuration_registry)
        self.configurator = self.configuration_builder.create_configurator()
        self.placement = self.configuration_builder.placement
        self.error_handler = self.configuration_builder.error_handler

    def create_new_vm(self):
        self.configurator.prepare_parameter_handlers()
        self.configurator.stage_configuration_changes()

        create_spec = vim.vm.ConfigSpec()
        self.configurator.apply_staged_changes_to_config_spec(create_spec)
        vm = self._deploy_vm(create_spec)
        self.vm = vm

        return self.configurator.change_set

    def configure_existing_vm(self):
        self.configurator.prepare_parameter_handlers()
        change_set = self.configurator.stage_configuration_changes()

        if change_set.are_changes_required():
            update_spec = vim.vm.ConfigSpec()
            self.configurator.apply_staged_changes_to_config_spec(update_spec)
            self._apply_update_spec(update_spec, change_set.power_cycle_required)

        return change_set

    def delete_vm(self):
        if not self.vm:
            return

        self._power_off_vm()

        try:
            self._try_to_run_task(task_func=self.vm.Destroy_Task, error_prefix="Unable to delete VM.")
        except Exception as e:
            self.module.fail_json(msg="%s." % to_native(type(e)))

    def _deploy_vm(self, configspec):
        vm_folder = self.placement.get_folder()
        task_result = self._try_to_run_task(
            task_func=vm_folder.CreateVM_Task,
            task_kwargs=dict(config=configspec, pool=self.placement.get_resource_pool(), host=self.placement.get_esxi_host()),
            error_prefix="Unable to create VM."
        )

        return task_result['result']

    def _apply_update_spec(self, update_spec, needs_power_cycle):
        if needs_power_cycle:
            self._power_off_vm()
        self._try_to_run_task(
            task_func=self.vm.ReconfigVM_Task,
            task_kwargs=dict(spec=update_spec),
            error_prefix="Unable to apply update spec."
        )
        if needs_power_cycle:
            self._power_on_vm()

    def _power_off_vm(self):
        if not self.vm or self.vm.summary.runtime.powerState.lower() == 'poweredoff':
            return

        if not self.params['allow_power_cycling']:
            self.error_handler.fail_with_generic_power_cycle_error(desired_power_state="powered off")

        self._try_to_run_task(task_func=self.vm.PowerOffVM_Task, error_prefix="Unable to power off VM.")

    def _power_on_vm(self):
        if not self.vm or self.vm.summary.runtime.powerState.lower() == 'poweredon':
            return

        if not self.params['allow_power_cycling']:
            self.error_handler.fail_with_generic_power_cycle_error(desired_power_state="powered on")

        self._try_to_run_task(task_func=self.vm.PowerOnVM_Task, error_prefix="Unable to power on VM.")

    def _try_to_run_task(self, task_func, error_prefix="", task_kwargs=None):
        if task_kwargs is None:
            task_kwargs = dict()

        try:
            task = task_func(**task_kwargs)
            _, task_result = RunningTaskMonitor(task).wait_for_completion(  # pylint: disable=disallowed-name
                timeout=self.params['timeout']
            )
        except TaskError as e:
            if isinstance(e.parent_error, vim.fault.InvalidVmConfig):
                self.error_handler.fail_with_vm_config_error(error=e.parent_error, message=str(e))
            else:
                self.module.fail_json(msg="%s %s" % (error_prefix, to_native(e)))
        except (vmodl.RuntimeFault, vim.fault.VimFault) as e:
            self.module.fail_json(msg="%s %s" % (error_prefix, e.msg))

        return task_result


def main():
    module = AnsibleModule(
        argument_spec={
            **base_argument_spec(),
            **vm_placement_argument_spec(omit_params=[]),
            **dict(
                state=dict(type='str', default='present', choices=['present', 'absent']),
                name=dict(type='str', required=False),
                name_match=dict(type='str', choices=['first', 'last'], default='first'),
                uuid=dict(type='str'),
                moid=dict(type='str'),
                use_instance_uuid=dict(type='bool', default=False),

                guest_id=dict(type='str', required=False),
                allow_power_cycling=dict(type='bool', default=False),

                cpu=dict(
                    type='dict', required=False, options=dict(
                        cores=dict(type='int', required=False),
                        cores_per_socket=dict(type='int', required=False),
                        enable_hot_add=dict(type='bool', required=False),
                        enable_hot_remove=dict(type='bool', required=False),
                        reservation=dict(type='int', required=False),
                        limit=dict(type='int', required=False),
                        shares=dict(type='int', required=False),
                        shares_level=dict(type='str', required=False, choices=['low', 'normal', 'high']),
                        enable_performance_counters=dict(type='bool', required=False),
                    ),
                    mutually_exclusive=[
                        ['shares', 'shares_level']
                    ],
                ),
                memory=dict(
                    type='dict', required=False, options=dict(
                        size_mb=dict(type='int', required=False),
                        shares=dict(type='int', required=False),
                        shares_level=dict(type='str', required=False, choices=['low', 'normal', 'high']),
                        limit=dict(type='int', required=False),
                        reservation=dict(type='int', required=False),
                        enable_hot_add=dict(type='bool', required=False),
                        reserve_all_memory=dict(type='bool', required=False),
                    ),
                    mutually_exclusive=[
                        ['shares', 'shares_level'],
                        ['reservation', 'reserve_all_memory'],
                    ],
                ),
                cdroms=dict(
                    type='list', elements='dict', required=False, options=dict(
                        device_node=dict(type='str', required=True),
                        connect_at_power_on=dict(type='bool', required=False),
                        iso_media_path=dict(type='str', required=False),
                        client_device_mode=dict(type='str', required=False, choices=['passthrough', 'emulated']),
                    ),
                    mutually_exclusive=[
                        ['iso_media_path', 'client_device_mode'],
                    ],
                ),
                disks=dict(
                    type='list', elements='dict', required=False, options=dict(
                        size=dict(type='str', required=True),
                        provisioning=dict(type='str', required=False, choices=['thin', 'thick', 'eagerzeroedthick']),
                        mode=dict(type='str', required=False, choices=[
                            'persistent', 'independent_persistent', 'independent_nonpersistent',
                            'append', 'nonpersistent', 'undoable'
                        ]),
                        device_node=dict(type='str', required=True),
                        enable_sharing=dict(type='bool', required=False),
                        datastore=dict(type='str', required=False),
                        filename=dict(type='str', required=False),
                    ),
                    mutually_exclusive=[
                        ['datastore', 'filename'],
                    ],
                ),

                scsi_controllers=dict(
                    type='list', elements='dict', required=False, options=dict(
                        bus_number=dict(type='int', required=True),
                        controller_type=dict(type='str', required=True, choices=['lsilogic', 'paravirtual', 'buslogic', 'lsilogicsas']),
                        bus_sharing=dict(type='str', required=False, choices=['noSharing', 'virtualSharing', 'physicalSharing'])
                    )
                ),
                nvme_controllers=dict(
                    type='list', elements='dict', required=False, options=dict(
                        bus_number=dict(type='int', required=True),
                        bus_sharing=dict(type='str', required=False, choices=['noSharing', 'exclusive']),
                    )
                ),
                sata_controllers=dict(
                    type='list', elements='dict', required=False, options=dict(
                        bus_number=dict(type='int', required=True),
                    )
                ),
                usb_controllers=dict(type='list', elements='dict', required=False),

                network_adapter_remove_unmanaged=dict(type='bool', required=False, default=False),
                network_adapters=dict(
                    type='list', elements='dict', required=False, options=dict(
                        network=dict(type='str', required=True),
                        adapter_type=dict(type='str', required=False, choices=['e1000', 'e1000e', 'pcnet32', 'vmxnet2', 'vmxnet3', 'sriov']),
                        connected=dict(type='bool', required=False),
                        connect_at_power_on=dict(type='bool', required=False),
                        shares=dict(type='int', required=False),
                        shares_level=dict(type='str', required=False, choices=['low', 'normal', 'high']),
                        reservation=dict(type='int', required=False),
                        limit=dict(type='int', required=False),
                        mac_address=dict(type='str', required=False),
                    ),
                    mutually_exclusive=[
                        ['shares', 'shares_level']
                    ],
                ),

                vm_options=dict(
                    type='dict', required=False, options=dict(
                        maximum_remote_console_sessions=dict(type='int', required=False),
                        enable_encryption=dict(type='bool', required=False),
                        encrypted_vmotion=dict(type='str', required=False, choices=['disabled', 'opportunistic', 'required']),
                        encrypted_fault_tolerance=dict(
                            type='str', required=False,
                            choices=[
                                'disabled',
                                'opportunistic',
                                'required',
                            ]
                        ),
                        enable_hardware_assisted_virtualization=dict(type='bool', required=False),
                        enable_io_mmu=dict(type='bool', required=False),
                        enable_virtual_based_security=dict(type='bool', required=False),
                        enable_secure_boot=dict(type='bool', required=False),
                        boot_firmware=dict(type='str', required=False, choices=['bios', 'efi']),
                    ),
                ),
                timeout=dict(type='int', default=600),
            )
        },
        supports_check_mode=True,
        mutually_exclusive=[
            ['name', 'uuid', 'moid']
        ],
        required_one_of=[
            ['name', 'uuid', 'moid']
        ],
    )

    result = dict(
        changed=False,
        changes=dict(),
        vm=dict(
            moid=None,
            name=None
        )
    )

    vm_module = VmModule(module)
    if module.params['state'] == 'present':
        if vm_module.vm:
            change_set = vm_module.configure_existing_vm()
        else:
            change_set = vm_module.create_new_vm()

        result['vm']['moid'] = vm_module.vm._GetMoId()
        result['vm']['name'] = vm_module.vm.name
        result['changed'] = change_set.are_changes_required()
        result['changes'] = change_set.changes

    elif module.params['state'] == 'absent':
        if vm_module.vm:
            result['vm']['moid'] = vm_module.vm._GetMoId()
            result['vm']['name'] = vm_module.vm.name
            result['changed'] = True
            vm_module.delete_vm()

    module.exit_json(**result)


if __name__ == '__main__':
    main()

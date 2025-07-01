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

    # placement:
    datacenter:
        description:
            - The datacenter in which to place the VM.
            - This is required when creating a new VM.
            - You cannot use this module to modify the placement of a VM once it has been created. This parameter is ignored if the VM already exists.
        type: str
        required: false
    cluster:
        description:
            - The cluster in which to place the VM.
            - This is required when creating a new VM.
            - You cannot use this module to modify the placement of a VM once it has been created. This parameter is ignored if the VM already exists.
        type: str
        required: false
    resource_pool:
        description:
            - The resource pool in which to place the VM.
            - This is required when creating a new VM.
            - You cannot use this module to modify the placement of a VM once it has been created. This parameter is ignored if the VM already exists.
        type: str
        required: false
    host:
        description:
            - The ESXi host on which to place the VM.
            - This is required when creating a new VM.
            - You cannot use this module to modify the placement of a VM once it has been created. This parameter is ignored if the VM already exists.
        type: str
        required: false
        aliases: [ esxi_host ]
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
            - Guest IDs are pre-defined by VMware. For example see https://developer.broadcom.com/xapis/vsphere-web-services-api/latest/vim.vm.GuestOsDescriptor.GuestOsIdentifier.html
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
              M(vm_powerstate) module to power off the VM if needed, and then this module again to apply the changes .
        type: bool
        required: false
        default: false

    # resources
    cpu:
        description:
            - Options related to CPU resource allocation.
            - This is required when creating a new VM.
        type: dict
        required: true
        suboptions:
            cores:
                description:
                    - The number of CPU cores to add to the VM.
                type: int
                required: true
            cores_per_socket:
                description:
                    - The number of cores per socket to use for the VM.
                    - If this is defined, O(cpus) must be a multiple of O(cpu_cores_per_socket).
                type: int
                required: true
            enable_hot_add:
                description:
                    - Whether to enable CPU hot add. This allows you to add CPUs to the VM while it is powered on.
                type: bool
                required: false
                default: false
            enable_hot_remove:
                description:
                    - Whether to enable CPU hot remove. This allows you to remove CPUs from the VM while it is powered on.
                type: bool
                required: false
                default: false
            reservation:
                description:
                    - The amount of CPU resource that is guaranteed available to the virtual machine.
                type: int
                required: false
            limit:
                description:
                    - The maximum number of CPUs the VM can use.
                type: int
                required: false
            shares:
                description:
                    - The custom number of shares of CPU allocated to this virtual machine.
                    - You can set O(shares_level) and omit this parameter to use a pre-defined value.
                    - If this is defined, O(shares_level) will be ignored.
                type: int
                required: false
            shares_level:
                description:
                    - The allocation level of CPU resources for the virtual machine.
                    - If O(shares) is defined, O(shares_level) will automatically be set to 'custom' and this parameter will be ignored.
                type: str
                required: false
                choices: [ low, normal, high ]
                default: normal
            enable_performance_counters:
                description:
                    - Whether to enable Virtual CPU Performance Monitoring Counters (VPMC).
                type: bool
                required: false
                default: false
            enable_hardware_assisted_virtualization:
                description:
                    - Whether to enable hardware assisted virtualization.
                type: bool
                required: false
                default: false
            enable_io_mmu:
                description:
                    - Whether to enable IO Memory Management Unit (IO MMU).
                type: bool
                required: false
                default: false

    memory:
        description:
            - Options related to memory resource allocation.
            - This is required when creating a new VM.
        type: dict
        required: true
        suboptions:
            size_mb:
                description:
                    - The amount of memory to add to the VM.
                    - Memory cannot be changed while the VM is powered on, unless memory hot add is already enabled.
                type: int
                required: false
            shares:
                description:
                    - The custom number of shares of memory allocated to this virtual machine.
                    - You can set O(shares_level) and omit this parameter to use a pre-defined value.
                    - If this is defined, O(shares_level) will be ignored.
                type: int
                required: false
            shares_level:
                description:
                    - The allocation level of memory resources for the virtual machine.
                    - If O(shares) is defined, O(shares_level) will automatically be set to 'custom' and this parameter will be ignored.
                type: str
                required: false
                choices: [ low, normal, high ]
                default: normal
            enable_hot_add:
                description:
                    - Whether to enable memory hot add. This allows you to add memory to the VM while it is powered on.
                type: bool
                required: false
                default: false
            reservation:
                description:
                    - The amount of memory resource that is guaranteed available to the VM.
                type: int
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
                type: str
                required: true
            provisioning:
                description:
                    - The provisioning type of the disk.
                type: str
                required: false
                choices: [ thin, thick, eagerzeroedthick ]
                default: thin
            mode:
                description:
                    - The mode of the disk.
                type: str
                required: false
                choices: [ persistent, independent_persistent, independent_nonpersistent ]
                default: persistent
            device_node:
                description:
                    - Specifies the controller, bus, and unit number of the disk.
                    - The format of this value should be like 'SCSI(0:0)' or 'IDE(0:1)'.
                    - Disk controllers referenced in this attribute must be configured in the corresponding controller section.
                      The exception to this are the two IDE controllers, which are automatically added to the VM.
                type: str
                required: true

    scsi_controllers:
        description:
            - SCSI device controllers to manage on the VM.
            - If a controller is not specified, it will be removed from the VM.
            - You may only specify four SCSI controllers per VM.
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
                required: true
                choices: [ buslogic, lsiLogic, lsiLogicSAS, pvscsi, virtio ]
            bus_sharing:
                description:
                    - The bus sharing mode of the controller.
                type: str
                required: false
                choices: [ noSharing, exclusive ]
                default: noSharing

    nvme_controllers:
        description:
            - NVMe device controllers to manage on the VM.
            - If a controller is not specified, it will be removed from the VM.
            - You may only specify four NVMe controllers per VM.
            - Controllers are added to the VM in the order they are specified. For example, the first controller specified
              will be assigned bus 0, the second controller will be assigned bus 1, etc.
        type: list
        elements: dict
        required: false
        suboptions:
            bus_sharing:
                description:
                    - The bus sharing mode of the controller.
                type: str
                choices: [ noSharing, exclusive ]
                default: noSharing

    sata_controller_count:
        description:
            - The number of SATA controllers to add to the VM.
            - Since there are no configurable options for SATA controllers, you just need to specify the number of controllers to have on the VM.
            - You may only specify four SATA controllers per VM.
        type: int
        required: false
        default: 0

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
from ansible_collections.vmware.vmware.plugins.module_utils.vm.placement import (
    VmPlacement,
    vm_placement_argument_spec
)
from ansible_collections.vmware.vmware.plugins.module_utils.vm._configurator import (
    VmConfigurator
)


class VmModule(ModulePyvmomiBase):
    def __init__(self, module):
        super().__init__(module)
        try:
            self.vm = self.get_vms_using_params(fail_on_missing=False)[0]
        except IndexError:
            self.vm = None

        if self.params['state'] == 'present':
            self.configurator = VmConfigurator(self.vm, self.module)

    def create_deploy_spec(self):
        configspec = vim.vm.ConfigSpec()
        self.configurator.update_config_spec(configspec, self.placement.get_datastore())

        return configspec

    def deploy(self, configspec):
        vm_folder = self.placement.get_folder()
        task_result = self._try_to_run_task(
            task_func=vm_folder.CreateVM_Task,
            task_kwargs=dict(config=configspec, pool=self.placement.get_resource_pool(), host=self.placement.get_esxi_host()),
            error_prefix="Unable to create VM."
        )

        return task_result['result']

    def create_vm(self):
        self.placement = VmPlacement(self.module)
        self.configurator.validate_params_for_creation()
        configspec = self.create_deploy_spec()
        vm = self.deploy(configspec)
        self.vm = vm

    def configure_vm(self):
        pass

    def delete_vm(self):
        if not self.vm:
            return

        self.power_off_vm()
        self._try_to_run_task(task_func=self.vm.Destroy_Task, error_prefix="Unable to delete VM.")

    def power_off_vm(self):
        if not self.vm or self.vm.summary.runtime.powerState.lower() == 'poweredoff':
            return

        if not self.params['allow_power_cycling']:
            self.module.fail_json(msg=(
                "VM needs to be powered off to make changes. You can allow this module to "
                "automatically power cycle the VM with the allow_power_cycling parameter."
            ))

        self._try_to_run_task(task_func=self.vm.PowerOffVM_Task, error_prefix="Unable to power off VM.")

    def power_on_vm(self):
        if not self.vm or self.vm.summary.runtime.powerState.lower() == 'poweredon':
            return

        if not self.params['allow_power_cycling']:
            self.module.fail_json(msg=(
                "VM needs to be powered on to make changes. You can allow this module to "
                "automatically power cycle the VM with the allow_power_cycling parameter."
            ))

        self._try_to_run_task(task_func=self.vm.PowerOnVM_Task, error_prefix="Unable to power on VM.")

    def _try_to_run_task(self, task_func, error_prefix="", task_kwargs=None):
        if task_kwargs is None:
            task_kwargs = dict()

        try:
            task = task_func(**task_kwargs)
            _, task_result = RunningTaskMonitor(task).wait_for_completion(
                timeout=self.params['timeout']
            )
        except TaskError as e:
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
                name=dict(type='str', required=True),
                name_match=dict(type='str', choices=['first', 'last'], default='first'),
                uuid=dict(type='str'),
                moid=dict(type='str'),
                use_instance_uuid=dict(type='bool', default=False),

                guest_id=dict(type='str', required=False),
                allow_power_cycling=dict(type='bool', default=False),

                cpu=dict(type='dict', required=False),
                memory=dict(type='dict', required=False),
                disks=dict(type='list', elements='dict', required=False),
                scsi_controllers=dict(type='list', elements='dict', required=False, default=[]),
                nvme_controllers=dict(type='list', elements='dict', required=False, default=[]),
                sata_controller_count=dict(type='int', required=False, default=0),
                usb_controllers=dict(type='list', elements='dict', required=False, default=[]),

                timeout=dict(type='int', default=600),
            )
        },
        supports_check_mode=True,
        mutually_exclusive=[
            ['name', 'uuid', 'moid']
        ],
        required_if=[
            ['state', 'present', ['cpu', 'memory', 'disks']]
        ],
        required_one_of=[
            ['name', 'uuid', 'moid']
        ],
    )

    result = dict(
        changed=False,
        vm=dict(
            moid=None,
            name=None
        )
    )

    vm_module = VmModule(module)
    if module.params['state'] == 'present':
        if vm_module.vm:
            vm_module.configure_vm()
            result['vm']['moid'] = vm_module.vm._GetMoId()
            result['vm']['name'] = vm_module.vm.name
            result['changed'] = True
        else:
            created_vm = vm_module.create_vm()
            result['vm']['moid'] = created_vm._GetMoId()
            result['vm']['name'] = created_vm.name
            result['changed'] = True

    elif module.params['state'] == 'absent':
        if vm_module.vm:
            vm_module.delete_vm()
            result['vm']['moid'] = vm_module.vm._GetMoId()
            result['vm']['name'] = vm_module.vm.name
            result['changed'] = True

    module.exit_json(**result)


if __name__ == '__main__':
    main()

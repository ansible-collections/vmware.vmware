#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2024, Ansible Cloud Team (@ansible-collections)
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function
__metaclass__ = type


DOCUMENTATION = r'''
---
module: vm_gpu_passthrough
short_description: Configure GPU passthrough for virtual machines
description:
    - Manages GPU passthrough configuration on VMware vSphere virtual machines.
    - Supports both PCIe passthrough (full GPU assignment) and vGPU profiles
      (shared GPU via NVIDIA GRID/AI Enterprise).
    - Enables NVIDIA AI Enterprise workloads on vSphere by configuring VMs
      with direct GPU access for AI training and inference.
author:
    - Ansible Cloud Team (@ansible-collections)

options:
    vm_name:
        description:
            - The name of the virtual machine to configure.
        type: str
        required: true
    datacenter:
        description:
            - The name of the datacenter containing the VM.
        type: str
        required: true
        aliases: [ datacenter_name ]
    gpu_mode:
        description:
            - The GPU passthrough mode to configure.
            - V(passthrough) assigns a full physical GPU to the VM via PCIe passthrough.
            - V(vgpu) assigns a vGPU profile for shared GPU access (NVIDIA GRID/AI Enterprise).
        type: str
        required: true
        choices: [ passthrough, vgpu ]
    gpu_device_id:
        description:
            - The PCI device ID of the GPU to pass through.
            - Required when O(gpu_mode) is V(passthrough).
            - Use M(vmware.vmware.vm_gpu_passthrough_info) to discover available GPU device IDs.
        type: str
    vgpu_profile:
        description:
            - The vGPU profile name to assign (e.g., C(grid_a100-40c), C(grid_h100-80c)).
            - Required when O(gpu_mode) is V(vgpu).
            - Profile names depend on the NVIDIA driver version and GPU model.
        type: str
    gpu_count:
        description:
            - Number of GPUs to assign to the VM.
            - For V(passthrough) mode, each GPU is a separate PCIe device.
            - For V(vgpu) mode, each is a separate vGPU instance.
        type: int
        default: 1
    memory_reservation_locked:
        description:
            - Whether to lock VM memory reservation.
            - GPU passthrough typically requires full memory reservation.
            - Automatically set to V(true) when O(gpu_mode) is V(passthrough).
        type: bool
        default: true
    enable_uefi_secure_boot:
        description:
            - Whether to configure UEFI secure boot for the VM.
            - Required for NVIDIA AI Enterprise certified configurations.
        type: bool
        default: false
    state:
        description:
            - V(present) ensures GPU passthrough is configured on the VM.
            - V(absent) removes GPU passthrough configuration from the VM.
        type: str
        choices: [ present, absent ]
        default: present

extends_documentation_fragment:
    - vmware.vmware.base_options

notes:
    - The VM must be powered off to add or remove GPU passthrough devices.
    - PCIe passthrough requires the GPU to be marked as passthrough-capable on the ESXi host.
    - vGPU requires NVIDIA GRID or AI Enterprise drivers installed on the ESXi host.
    - GPU passthrough with full memory reservation is required for NVIDIA AI Enterprise.
'''

EXAMPLES = r'''
- name: Add PCIe GPU passthrough to a VM
  vmware.vmware.vm_gpu_passthrough:
    hostname: '{{ vcenter_hostname }}'
    username: '{{ vcenter_username }}'
    password: '{{ vcenter_password }}'
    vm_name: ai-worker-01
    datacenter: DC0
    gpu_mode: passthrough
    gpu_device_id: "0000:3b:00.0"
    gpu_count: 2
    memory_reservation_locked: true
    state: present

- name: Add vGPU profile to a VM for AI inference
  vmware.vmware.vm_gpu_passthrough:
    hostname: '{{ vcenter_hostname }}'
    username: '{{ vcenter_username }}'
    password: '{{ vcenter_password }}'
    vm_name: inference-server-01
    datacenter: DC0
    gpu_mode: vgpu
    vgpu_profile: grid_a100-40c
    gpu_count: 1
    state: present

- name: Configure VM for NVIDIA AI Enterprise
  vmware.vmware.vm_gpu_passthrough:
    hostname: '{{ vcenter_hostname }}'
    username: '{{ vcenter_username }}'
    password: '{{ vcenter_password }}'
    vm_name: nvaie-workstation
    datacenter: DC0
    gpu_mode: vgpu
    vgpu_profile: grid_h100-80c
    gpu_count: 4
    memory_reservation_locked: true
    enable_uefi_secure_boot: true
    state: present

- name: Remove GPU passthrough from a VM
  vmware.vmware.vm_gpu_passthrough:
    hostname: '{{ vcenter_hostname }}'
    username: '{{ vcenter_username }}'
    password: '{{ vcenter_password }}'
    vm_name: ai-worker-01
    datacenter: DC0
    gpu_mode: passthrough
    state: absent
'''

RETURN = r'''
changed:
    description: Whether the VM GPU configuration was changed.
    returned: always
    type: bool
    sample: true
result:
    description: Information about the GPU passthrough configuration.
    returned: always
    type: dict
    sample:
        vm_name: "ai-worker-01"
        gpu_mode: "passthrough"
        gpu_count: 2
        gpu_devices: ["0000:3b:00.0", "0000:86:00.0"]
'''

try:
    from pyVmomi import vim, vmodl
except ImportError:
    pass

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.common.text.converters import to_native
from ansible_collections.vmware.vmware.plugins.module_utils._module_pyvmomi_base import (
    ModulePyvmomiBase,
)
from ansible_collections.vmware.vmware.plugins.module_utils.argument_spec import (
    base_argument_spec,
)


class VMwareGPUPassthrough(ModulePyvmomiBase):
    def __init__(self, module):
        super().__init__(module)
        self.vm_name = self.params['vm_name']
        self.datacenter_name = self.params['datacenter']
        self.gpu_mode = self.params['gpu_mode']
        self.state = self.params['state']
        self.vm = None
        self.datacenter = None

    def _find_vm(self):
        """Find the virtual machine by name."""
        datacenter_objs = self.get_objs_by_name_or_moid(vim.Datacenter, self.datacenter_name)
        if not datacenter_objs:
            self.module.fail_json(msg="Datacenter '%s' not found" % self.datacenter_name)
        self.datacenter = datacenter_objs[0]

        vm_objs = self.get_objs_by_name_or_moid(
            vim.VirtualMachine, self.vm_name,
            search_root_folder=self.datacenter.vmFolder
        )
        if not vm_objs:
            self.module.fail_json(msg="VM '%s' not found in datacenter '%s'" % (self.vm_name, self.datacenter_name))
        self.vm = vm_objs[0]

    def _get_current_gpu_devices(self):
        """Get current GPU passthrough devices on the VM."""
        gpu_devices = []
        for device in self.vm.config.hardware.device:
            if isinstance(device, vim.vm.device.VirtualPCIPassthrough):
                gpu_devices.append(device)
        return gpu_devices

    def _get_available_pci_devices(self):
        """Get available PCI passthrough devices on the host."""
        host = self.vm.runtime.host
        if not host:
            return []
        pci_devices = []
        for pci_device in host.hardware.pciDevice:
            if 'NVIDIA' in (pci_device.vendorName or '').upper():
                pci_devices.append(pci_device)
        return pci_devices

    def _create_passthrough_spec(self, pci_id):
        """Create a PCIe passthrough device spec."""
        backing = vim.vm.device.VirtualPCIPassthrough.DeviceBackingInfo()
        backing.id = pci_id
        backing.deviceId = ''
        backing.systemId = ''
        backing.vendorId = 0

        device = vim.vm.device.VirtualPCIPassthrough()
        device.backing = backing

        device_spec = vim.vm.device.VirtualDeviceSpec()
        device_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
        device_spec.device = device

        return device_spec

    def _create_vgpu_spec(self, profile):
        """Create a vGPU device spec."""
        backing = vim.vm.device.VirtualPCIPassthrough.VmiopBackingInfo()
        backing.vgpu = profile

        device = vim.vm.device.VirtualPCIPassthrough()
        device.backing = backing

        device_spec = vim.vm.device.VirtualDeviceSpec()
        device_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
        device_spec.device = device

        return device_spec

    def _create_remove_spec(self, device):
        """Create a device removal spec."""
        device_spec = vim.vm.device.VirtualDeviceSpec()
        device_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.remove
        device_spec.device = device
        return device_spec

    def configure_gpu(self):
        """Configure or remove GPU passthrough on the VM."""
        self._find_vm()
        current_gpus = self._get_current_gpu_devices()
        config_spec = vim.vm.ConfigSpec()

        if self.state == 'absent':
            if not current_gpus:
                return False
            for gpu in current_gpus:
                config_spec.deviceChange.append(self._create_remove_spec(gpu))
        else:
            gpu_count = self.params['gpu_count']

            if self.gpu_mode == 'passthrough':
                gpu_device_id = self.params.get('gpu_device_id')
                if not gpu_device_id:
                    self.module.fail_json(msg="gpu_device_id is required for passthrough mode")
                for _ in range(gpu_count):
                    config_spec.deviceChange.append(self._create_passthrough_spec(gpu_device_id))

            elif self.gpu_mode == 'vgpu':
                vgpu_profile = self.params.get('vgpu_profile')
                if not vgpu_profile:
                    self.module.fail_json(msg="vgpu_profile is required for vgpu mode")
                for _ in range(gpu_count):
                    config_spec.deviceChange.append(self._create_vgpu_spec(vgpu_profile))

            if self.params.get('memory_reservation_locked', True):
                config_spec.memoryReservationLockedToMax = True

        if not config_spec.deviceChange:
            return False

        try:
            task = self.vm.ReconfigVM_Task(config_spec)
            task_result = task
            while task_result.info.state not in ['success', 'error']:
                pass
            if task_result.info.state == 'error':
                self.module.fail_json(msg="Failed to reconfigure VM: %s" % to_native(task_result.info.error.msg))
        except (vmodl.RuntimeFault, vmodl.MethodFault) as vmodl_fault:
            self.module.fail_json(msg="Failed to configure GPU passthrough: %s" % to_native(vmodl_fault.msg))
        except Exception as exc:
            self.module.fail_json(msg="Failed to configure GPU: %s" % to_native(exc))

        return True

    def get_gpu_info(self):
        """Return current GPU configuration info."""
        self._find_vm()
        current_gpus = self._get_current_gpu_devices()
        gpu_info = []
        for gpu in current_gpus:
            info = {'device_key': gpu.key}
            if hasattr(gpu.backing, 'vgpu'):
                info['type'] = 'vgpu'
                info['profile'] = gpu.backing.vgpu
            elif hasattr(gpu.backing, 'id'):
                info['type'] = 'passthrough'
                info['pci_id'] = gpu.backing.id
            gpu_info.append(info)
        return gpu_info


def main():
    module = AnsibleModule(
        argument_spec={
            **base_argument_spec(), **dict(
                vm_name=dict(type='str', required=True),
                datacenter=dict(type='str', required=True, aliases=['datacenter_name']),
                gpu_mode=dict(type='str', required=True, choices=['passthrough', 'vgpu']),
                gpu_device_id=dict(type='str'),
                vgpu_profile=dict(type='str'),
                gpu_count=dict(type='int', default=1),
                memory_reservation_locked=dict(type='bool', default=True),
                enable_uefi_secure_boot=dict(type='bool', default=False),
                state=dict(type='str', choices=['present', 'absent'], default='present'),
            )
        },
        supports_check_mode=True,
        required_if=[
            ('gpu_mode', 'passthrough', ('gpu_device_id',), False),
            ('gpu_mode', 'vgpu', ('vgpu_profile',), False),
        ],
    )

    result = dict(
        changed=False,
        result={},
    )

    gpu_passthrough = VMwareGPUPassthrough(module)

    if module.check_mode:
        gpu_info = gpu_passthrough.get_gpu_info()
        result['result'] = {
            'vm_name': module.params['vm_name'],
            'gpu_mode': module.params['gpu_mode'],
            'current_gpus': gpu_info,
        }
        if module.params['state'] == 'present' and not gpu_info:
            result['changed'] = True
        elif module.params['state'] == 'absent' and gpu_info:
            result['changed'] = True
        module.exit_json(**result)

    changed = gpu_passthrough.configure_gpu()
    result['changed'] = changed
    result['result'] = {
        'vm_name': module.params['vm_name'],
        'gpu_mode': module.params['gpu_mode'],
        'gpu_count': module.params.get('gpu_count', 1),
        'state': module.params['state'],
    }

    module.exit_json(**result)


if __name__ == '__main__':
    main()

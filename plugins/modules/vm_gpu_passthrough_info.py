#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2024, Ansible Cloud Team (@ansible-collections)
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function
__metaclass__ = type


DOCUMENTATION = r'''
---
module: vm_gpu_passthrough_info
short_description: Query GPU passthrough configuration and available GPUs
description:
    - Gathers information about GPU passthrough configuration on virtual machines.
    - Discovers available GPU devices on ESXi hosts that can be used for passthrough.
    - Lists available vGPU profiles supported by host GPU hardware.
    - Useful for discovering GPU resources before configuring AI Factory workloads.
author:
    - Ansible Cloud Team (@ansible-collections)

options:
    vm_name:
        description:
            - The name of the virtual machine to query.
            - If specified, returns GPU devices currently attached to this VM.
            - If not specified, returns available GPU devices on the host or cluster.
        type: str
    datacenter:
        description:
            - The name of the datacenter to search in.
        type: str
        required: true
        aliases: [ datacenter_name ]
    cluster:
        description:
            - The name of the cluster to query for available GPUs.
            - If not specified and O(vm_name) is not set, queries all hosts in the datacenter.
        type: str
        aliases: [ cluster_name ]
    gather_vgpu_profiles:
        description:
            - If V(true), also gather available vGPU profiles from the host GPU devices.
            - This requires NVIDIA GRID drivers to be installed on the ESXi hosts.
        type: bool
        default: false

extends_documentation_fragment:
    - vmware.vmware.base_options

notes:
    - For PCIe passthrough, the GPU must be enabled for passthrough in the ESXi host configuration.
    - vGPU profiles are only available when NVIDIA GRID or AI Enterprise drivers are installed.
'''

EXAMPLES = r'''
- name: Get GPU passthrough info for a specific VM
  vmware.vmware.vm_gpu_passthrough_info:
    hostname: '{{ vcenter_hostname }}'
    username: '{{ vcenter_username }}'
    password: '{{ vcenter_password }}'
    vm_name: ai-worker-01
    datacenter: DC0
  register: vm_gpu_info

- name: Discover available GPUs in a cluster
  vmware.vmware.vm_gpu_passthrough_info:
    hostname: '{{ vcenter_hostname }}'
    username: '{{ vcenter_username }}'
    password: '{{ vcenter_password }}'
    datacenter: DC0
    cluster: GPU-Cluster
    gather_vgpu_profiles: true
  register: cluster_gpu_info

- name: List all available GPUs in a datacenter
  vmware.vmware.vm_gpu_passthrough_info:
    hostname: '{{ vcenter_hostname }}'
    username: '{{ vcenter_username }}'
    password: '{{ vcenter_password }}'
    datacenter: DC0
  register: dc_gpu_info
'''

RETURN = r'''
gpu_info:
    description: GPU passthrough information.
    returned: always
    type: dict
    contains:
        vm_gpus:
            description: GPU devices currently attached to the VM (when vm_name is specified).
            type: list
            elements: dict
            sample:
                - device_key: 13000
                  type: "vgpu"
                  profile: "grid_a100-40c"
        available_gpus:
            description: Available GPU devices on hosts (when vm_name is not specified).
            type: list
            elements: dict
            sample:
                - host: "esxi-gpu-01.example.com"
                  pci_id: "0000:3b:00.0"
                  vendor: "NVIDIA Corporation"
                  device_name: "NVIDIA A100 80GB PCIe"
                  passthrough_capable: true
        vgpu_profiles:
            description: Available vGPU profiles (when gather_vgpu_profiles is true).
            type: list
            elements: dict
            sample:
                - host: "esxi-gpu-01.example.com"
                  profile: "grid_a100-40c"
                  vram_mb: 40960
                  max_instances: 2
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


class VMwareGPUPassthroughInfo(ModulePyvmomiBase):
    def __init__(self, module):
        super().__init__(module)
        self.datacenter_name = self.params['datacenter']
        self.datacenter = None

    def _find_datacenter(self):
        """Find the datacenter by name."""
        dc_objs = self.get_objs_by_name_or_moid(vim.Datacenter, self.datacenter_name)
        if not dc_objs:
            self.module.fail_json(msg="Datacenter '%s' not found" % self.datacenter_name)
        self.datacenter = dc_objs[0]

    def _get_hosts(self):
        """Get ESXi hosts based on cluster or datacenter scope."""
        cluster_name = self.params.get('cluster')
        if cluster_name:
            clusters = self.get_objs_by_name_or_moid(
                vim.ClusterComputeResource, cluster_name,
                search_root_folder=self.datacenter.hostFolder
            )
            if not clusters:
                self.module.fail_json(msg="Cluster '%s' not found" % cluster_name)
            return clusters[0].host
        else:
            hosts = self.get_objs_by_name_or_moid(
                vim.HostSystem, '', return_all=True,
                search_root_folder=self.datacenter.hostFolder
            )
            return hosts

    def get_vm_gpu_info(self, vm_name):
        """Get GPU info for a specific VM."""
        vm_objs = self.get_objs_by_name_or_moid(
            vim.VirtualMachine, vm_name,
            search_root_folder=self.datacenter.vmFolder
        )
        if not vm_objs:
            self.module.fail_json(msg="VM '%s' not found" % vm_name)

        vm = vm_objs[0]
        gpu_devices = []
        for device in vm.config.hardware.device:
            if isinstance(device, vim.vm.device.VirtualPCIPassthrough):
                info = {'device_key': device.key}
                if hasattr(device.backing, 'vgpu') and device.backing.vgpu:
                    info['type'] = 'vgpu'
                    info['profile'] = device.backing.vgpu
                elif hasattr(device.backing, 'id'):
                    info['type'] = 'passthrough'
                    info['pci_id'] = getattr(device.backing, 'id', 'unknown')
                gpu_devices.append(info)

        return gpu_devices

    def get_available_gpus(self):
        """Discover available GPU devices on hosts."""
        hosts = self._get_hosts()
        available = []
        for host in hosts:
            try:
                for pci_device in host.hardware.pciDevice:
                    vendor = pci_device.vendorName or ''
                    if 'NVIDIA' in vendor.upper():
                        available.append({
                            'host': host.name,
                            'pci_id': pci_device.id,
                            'vendor': vendor.strip(),
                            'device_name': (pci_device.deviceName or '').strip(),
                            'vendor_id': hex(pci_device.vendorId),
                            'device_id': hex(pci_device.deviceId),
                        })
            except Exception:
                continue

        return available

    def get_vgpu_profiles(self):
        """Get available vGPU profiles from hosts."""
        hosts = self._get_hosts()
        profiles = []
        for host in hosts:
            try:
                if not hasattr(host.config, 'sharedGpuCapabilities'):
                    continue
                for capability in (host.config.sharedGpuCapabilities or []):
                    profiles.append({
                        'host': host.name,
                        'profile': capability.vgpu,
                        'max_instances': getattr(capability, 'maxInstancePerGpu', None),
                    })
            except Exception:
                continue

        return profiles

    def gather_info(self):
        """Main info gathering method."""
        self._find_datacenter()

        result = {}
        vm_name = self.params.get('vm_name')

        if vm_name:
            result['vm_gpus'] = self.get_vm_gpu_info(vm_name)
        else:
            result['available_gpus'] = self.get_available_gpus()

        if self.params.get('gather_vgpu_profiles'):
            result['vgpu_profiles'] = self.get_vgpu_profiles()

        return result


def main():
    module = AnsibleModule(
        argument_spec={
            **base_argument_spec(), **dict(
                vm_name=dict(type='str'),
                datacenter=dict(type='str', required=True, aliases=['datacenter_name']),
                cluster=dict(type='str', aliases=['cluster_name']),
                gather_vgpu_profiles=dict(type='bool', default=False),
            )
        },
        supports_check_mode=True,
    )

    gpu_info = VMwareGPUPassthroughInfo(module)
    info = gpu_info.gather_info()
    module.exit_json(changed=False, gpu_info=info)


if __name__ == '__main__':
    main()

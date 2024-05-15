#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2023, Ansible Cloud Team (@ansible-collections)
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function
__metaclass__ = type


DOCUMENTATION = r'''
---
module: vm_list_group_by_clusters
short_description: Returns information about the virtual machines grouping by clusters and folders
description:
    - Returns information about the virtual machines grouping by clusters and folders.
author:
    - Ansible Cloud Team (@ansible-collections)
options:
  detailed_vms:
    default: true
    description:
      - Wither or not get the vms detailed.
    type: bool
extends_documentation_fragment:
- vmware.vmware.vmware_rest_client.documentation

'''

EXAMPLES = r'''
- name: Gather list of VMs
  vmware.vmware.vm_list_group_by_clusters:
    hostname: "https://vcenter"
    username: "username"
    password: "password"

- name: Gather list of VMs in clusterA
  vmware.vmware.vm_list_group_by_clusters:
    hostname: "https://vcenter"
    username: "username"
    password: "password"
    detailed_vms: False
'''

RETURN = r'''
vm_list_group_by_clusters:
    description:
        - Dictionary of vm list by folders and clusters
    returned: On success
    type: dict
    sample: {
        "cluster_name1": {
            "folder1": [
            {
                "advanced_settings": {},
                "annotation": "",
                "current_snapshot": null,
                "customvalues": {},
                "guest_consolidation_needed": false,
                "guest_question": null,
                "guest_tools_status": "guestToolsNotRunning",
                "guest_tools_version": "10247",
                "hw_cores_per_socket": 1,
                "hw_datastores": [
                    "ds_226_3"
                ],
                "hw_esxi_host": "10.76.33.226",
                "hw_eth0": {
                    "addresstype": "assigned",
                    "ipaddresses": null,
                    "label": "Network adapter 1",
                    "macaddress": "00:50:56:87:a5:9a",
                    "macaddress_dash": "00-50-56-87-a5-9a",
                    "portgroup_key": null,
                    "portgroup_portkey": null,
                    "summary": "VM Network"
                },
                "hw_files": [
                    "[ds_226_3] ubuntu_t/ubuntu_t.vmx",
                    "[ds_226_3] ubuntu_t/ubuntu_t.nvram",
                    "[ds_226_3] ubuntu_t/ubuntu_t.vmsd",
                    "[ds_226_3] ubuntu_t/vmware.log",
                    "[ds_226_3] u0001/u0001.vmdk"
                ],
                "hw_folder": "/DC0/vm/Discovered virtual machine",
                "hw_guest_full_name": null,
                "hw_guest_ha_state": null,
                "hw_guest_id": null,
                "hw_interfaces": [
                    "eth0"
                ],
                "hw_is_template": false,
                "hw_memtotal_mb": 1024,
                "hw_name": "ubuntu_t",
                "hw_power_status": "poweredOff",
                "hw_processor_count": 1,
                "hw_product_uuid": "4207072c-edd8-3bd5-64dc-903fd3a0db04",
                "hw_version": "vmx-13",
                "instance_uuid": "5007769d-add3-1e12-f1fe-225ae2a07caf",
                "ipv4": null,
                "ipv6": null,
                "module_hw": true,
                "snapshots": [],
                "tags": [
                    "backup"
                ],
                "vnc": {},
                "moid": "vm-42",
                "vimref": "vim.VirtualMachine:vm-42"
            }]
        }
    }
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.vmware.vmware.plugins.module_utils.vmware_rest_client import VmwareRestClient


class VmwareVMList(VmwareRestClient):
    def __init__(self, module):
        super(VmwareVMList, self).__init__(module)
        self.module = module
        self.params = module.params
        self.detailed_vms = self.params['detailed_vms']

    def get_all_clusters(self):
        return self.api_client.vcenter.Cluster.list()

    def get_all_folders(self):
        folder_filter_spec = self.api_client.vcenter.Folder.FilterSpec(
            type=self.api_client.vcenter.Folder.Type.VIRTUAL_MACHINE)
        return self.api_client.vcenter.Folder.list(folder_filter_spec)

    def get_all_vms_in_cluster_and_folder(self, cluster, folder):
        vms_filter = self.api_client.vcenter.VM.FilterSpec(clusters=set([cluster]),
                                                           folders=set([folder]))
        return self.api_client.vcenter.VM.list(vms_filter)

    def get_vm_detailed(self, vm):
        return self.api_client.vcenter.VM.get(vm=vm)

    def get_vm_list_group_by_clusters(self):
        clusters = self.get_all_clusters()
        folders = self.get_all_folders()

        result_dict = {}
        for cluster in clusters:
            vm_list_group_by_folder_dict = {}
            empty = True
            for folder in folders:
                vms = self.get_all_vms_in_cluster_and_folder(cluster.cluster, folder.folder)
                vms_detailed = []
                for vm in vms:
                    if self.detailed_vms:
                        vm = self.get_vm_detailed(vm=vm.vm)

                    vms_detailed.append(self._vvars(vm))

                if vms_detailed:
                    empty = False
                    vm_list_group_by_folder_dict[folder.name] = vms_detailed

            if not empty:
                result_dict[cluster.name] = vm_list_group_by_folder_dict

        return result_dict

    def _vvars(self, vmware_obj):
        return {k: str(v) for k, v in vars(vmware_obj).items() if not k.startswith('_')}


def main():
    argument_spec = VmwareRestClient.vmware_client_argument_spec()
    argument_spec.update(
        dict(
            detailed_vms=dict(type='bool', default=True),
        )
    )
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True
    )

    vmware_vm_list_group_by_clusters_mgr = VmwareVMList(module)
    vm_list_group_by_clusters = vmware_vm_list_group_by_clusters_mgr.get_vm_list_group_by_clusters()
    module.exit_json(changed=False, vm_list_group_by_clusters=vm_list_group_by_clusters)


if __name__ == '__main__':
    main()

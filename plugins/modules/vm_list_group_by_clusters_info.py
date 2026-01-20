#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2023, Ansible Cloud Team (@ansible-collections)
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function
__metaclass__ = type


DOCUMENTATION = r'''
---
module: vm_list_group_by_clusters_info
version_added: '1.1.0'
short_description: Returns information about the virtual machines grouping by clusters and folders
description:
    - Returns information about the virtual machines grouping by clusters and folders.
author:
    - Ansible Cloud Team (@ansible-collections)
requirements:
    - vSphere Automation SDK
options:
    detailed_vms:
        default: true
        description:
        - If I(true) gather detailed information about virtual machines.
        type: bool
    use_absolute_path_for_group_name:
        default: false
        description:
        - If I(true) use the absolute folder or cluster path for the group name.
        - If false, only the object name will be used for the group name.
        - If two or more objects have the same name and this option is set to false,
          only the most recently found object will be used to determine group membership.
        type: bool
attributes:
  check_mode:
    description: The check_mode support.
    support: full
extends_documentation_fragment:
    - vmware.vmware.base_options
    - vmware.vmware.additional_rest_options

'''

EXAMPLES = r'''
- name: Gather list of VMs group by clusters and folders
  vmware.vmware.vm_list_group_by_clusters_info:
    hostname: "https://vcenter"
    username: "username"
    password: "password"
'''

RETURN = r'''
vm_list_group_by_clusters_info:
    description:
        - Dictionary of vm list by folders and clusters.
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
from ansible_collections.vmware.vmware.plugins.module_utils._module_rest_base import ModuleRestBase
from ansible_collections.vmware.vmware.plugins.module_utils._module_pyvmomi_base import ModulePyvmomiBase
from ansible_collections.vmware.vmware.plugins.module_utils._folder_paths import get_folder_path_of_vsphere_object
from ansible_collections.vmware.vmware.plugins.module_utils.argument_spec import rest_compatible_argument_spec


class VmwareVMList(ModuleRestBase):
    def __init__(self, module):
        super(VmwareVMList, self).__init__(module)
        self.module = module
        self.params = module.params
        self.detailed_vms = self.params['detailed_vms']
        self.pyvmomi = None
        if self.params['use_absolute_path_for_group_name']:
            self.pyvmomi = ModulePyvmomiBase(module)

    def get_all_clusters(self):
        return self.api_client.vcenter.Cluster.list()

    def get_all_folders(self):
        folder_filter_spec = self.api_client.vcenter.Folder.FilterSpec(
            type=self.api_client.vcenter.Folder.Type.VIRTUAL_MACHINE)
        return self.api_client.vcenter.Folder.list(folder_filter_spec)

    def get_all_vms_in_cluster_and_folder(self, cluster, folder, host):
        vms_filter = self.api_client.vcenter.VM.FilterSpec(clusters=set([cluster]),
                                                           folders=set([folder]),
                                                           hosts=set([host]))

        return self.api_client.vcenter.VM.list(vms_filter)

    def get_vm_detailed(self, vm):
        return self.api_client.vcenter.VM.get(vm=vm)

    def get_cluster_hosts(self, cluster):
        host_filter = self.api_client.vcenter.Host.FilterSpec(
            clusters=set([cluster]))
        return self.api_client.vcenter.Host.list(host_filter)

    def get_vm_list_group_by_clusters(self):
        clusters = self.get_all_clusters()
        folders = self.get_all_folders()
        result_dict = {}
        for cluster in clusters:
            vm_list_group_by_folder_dict = {}
            hosts = self.get_cluster_hosts(cluster.cluster)
            for folder in folders:
                vms = []
                # iterate each host due to an error too_many_matches when looking at all vms on a cluster
                # https://github.com/vmware/vsphere-automation-sdk-python/issues/142
                for host in hosts:
                    vms.extend(self.get_all_vms_in_cluster_and_folder(cluster.cluster, folder.folder, host.host))
                vms_detailed = []
                for vm in vms:
                    if self.detailed_vms:
                        vm = self.get_vm_detailed(vm=vm.vm)

                    vms_detailed.append(self._vvars(vm))

                if vms_detailed:
                    group_name = self._determine_group_name_for_object(folder)
                    vm_list_group_by_folder_dict[group_name] = vms_detailed

            if vm_list_group_by_folder_dict:
                group_name = self._determine_group_name_for_object(cluster)
                result_dict[group_name] = vm_list_group_by_folder_dict

        return result_dict

    def _vvars(self, vmware_obj):
        return {k: str(v) for k, v in vars(vmware_obj).items() if not k.startswith('_')}

    def _determine_group_name_for_object(self, group_object):
        """
        Since object names are not unique but inventory paths are, we let the user decide which they want to
        use for the group name. The inventory path requires some additional pyvmomi calls to get the full path.
        """
        if self.params['use_absolute_path_for_group_name']:
            if hasattr(group_object, 'cluster'):
                pyv_object = self.pyvmomi.get_cluster_by_name_or_moid(group_object.cluster, fail_on_missing=True)
            elif hasattr(group_object, 'folder'):
                pyv_object = self.pyvmomi.get_folders_by_name_or_moid(group_object.folder, fail_on_missing=True)[0]
            else:
                self.module.fail_json(msg="Unable to determine group name for object %s" % group_object)

            return f"{get_folder_path_of_vsphere_object(pyv_object)}/{group_object.name}"

        else:
            return group_object.name


def main():
    argument_spec = rest_compatible_argument_spec()
    argument_spec.update(
        dict(
            detailed_vms=dict(type='bool', default=True),
            use_absolute_path_for_group_name=dict(type='bool', default=False),
        )
    )
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    vmware_vm_list_group_by_clusters_mgr = VmwareVMList(module)
    vm_list_group_by_clusters_info = vmware_vm_list_group_by_clusters_mgr.get_vm_list_group_by_clusters()
    module.exit_json(changed=False, vm_list_group_by_clusters_info=vm_list_group_by_clusters_info)


if __name__ == '__main__':
    main()

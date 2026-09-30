#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2023, Ansible Eco Content Team (github.com/eco-ansible-content)
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type


DOCUMENTATION = r'''
---
module: vm_portgroup_info
version_added: '1.4.0'
short_description: Returns information about the portgroups of virtual machines
description:
    - Returns information about the standard or distributed portgroups of virtual machines.

requirements:
    - vSphere Automation SDK
options:
    datacenter:
        description:
            - The datacenter where the VM(s) to query exist.
            - This option is useful if the VM(s) have name conflicts in other datacenters or you are
              using a relative folder path.
        type: str
        required: false
    name:
        description:
            - Name of the virtual machine to query.
            - Virtual machine names in vCenter are not necessarily unique, which may be problematic, see O(name_match).
            - One and only one of O(vm_names), O(name), O(uuid), or O(moid) must be provided.
        type: str
    name_match:
        description:
            - If multiple virtual machines matching the name, use the first or last found.
        default: first
        choices: [ first, last ]
        type: str
    uuid:
        description:
            - UUID of the instance to query if known, this is VMware's unique identifier.
            - One and only one of O(vm_names), O(name), O(uuid), or O(moid) must be provided.
        type: str
    moid:
        description:
            - Managed Object ID of the instance to query if known, this is a unique identifier only within a single vCenter instance.
            - One and only one of O(vm_names), O(name), O(uuid), or O(moid) must be provided.
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
            - For example 'datacenter_name/vm/path/to/folder' or 'path/to/folder'
        type: str
        required: false
    folder_paths_are_absolute:
        description:
            - If true, any folder path parameters are treated as absolute paths.
            - If false, modules will try to intelligently determine if the path is absolute
              or relative.
            - This option is useful when your environment has a complex folder structure. By default,
              modules will try to intelligently determine if the path is absolute or relative.
              They may mistakenly prepend the datacenter name or other folder names, and this option
              can be used to avoid this.
        type: bool
        required: false
        default: false

    vm_names:
        description:
            - List of VM names that should be of which the portgroup information should be gathered.
            - Other options like O(folder) and O(datacenter) can be used to reduce the search area. These
              filters are applied to all names in this list.
            - MOIDs can be used instead of names, if desired.
            - One and only one of O(vm_names), O(name), O(uuid), or O(moid) must be provided.
        required: false
        type: list
        elements: str

extends_documentation_fragment:
    - vmware.vmware.base_options
    - vmware.vmware.additional_rest_options
'''

EXAMPLES = r'''
- name: Gather list of portgroup by VMs
  vmware.vmware.portgroup_info:
    hostname: "https://vcenter"
    username: "username"
    password: "password"
    vm_names:
      - vm-test1
      - vm-test2
'''

RETURN = r'''
vm_portgroup_info:
    description:
        - Dictionary of the requested VMs with the portgroup information
    returned: On success
    type: dict
    sample: {
        "vm1": [
        {
            "name": "Network Name",
            "nic_mac_address": "00:00:00:00:00:00",
            "nic_mac_type": "ASSIGNED",
            "nic_type": "VMXNET3",
            "port_id": "network-port-id",
            "type": "STANDARD_PORTGROUP",
            "vlan_id": "0",
            "vswitch_name": "vSwitch0"
        }]
    }
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.vmware.vmware.plugins.module_utils._module_pyvmomi_base import ModulePyvmomiBase
from ansible_collections.vmware.vmware.plugins.module_utils import _network as vmware_network
from ansible_collections.vmware.vmware.plugins.module_utils._module_rest_base import ModuleRestBase
from ansible_collections.vmware.vmware.plugins.module_utils.argument_spec import rest_compatible_argument_spec

try:
    from pyVmomi import vim
except ImportError:
    pass


class PortgroupInfo(ModulePyvmomiBase):
    def __init__(self, module):
        super(PortgroupInfo, self).__init__(module)
        self.vmware_client = ModuleRestBase(module)
        self.vms = []
        if self.params.get('vm_names'):
            folder = self.get_folder_using_params(fail_on_missing=False)
            for vm_name in self.params['vm_names']:
                vms = self.get_objs_by_name_or_moid([vim.VirtualMachine], vm_name, return_all=True, search_root_folder=folder)
                if vms:
                    self.vms += vms
        else:
            self.vms = self.get_vms_using_params(fail_on_missing=False)

    def _vm_network_devices(self, vm):
        try:
            devices = vm.config.hardware.device
        except AttributeError:
            return

        for device in devices:
            if isinstance(device, vim.vm.device.VirtualEthernetCard):
                yield device

    def get_dvs_portgroup_detailed(self, dvs_pg, pg_id):
        try:
            pg = {
                'portgroup_name': dvs_pg.name,
                'vswitch_name': dvs_pg.config.distributedVirtualSwitch.name,
                'type': 'DISTRIBUTED_PORTGROUP',
                'port_id': pg_id,
                'port_binding': vmware_network.get_dvs_port_allocation(dvs_pg.config.type),
                'port_allocation': vmware_network.get_dvs_auto_expand(dvs_pg.config.autoExpand),
                'network_policy': vmware_network.get_dvs_network_policy(dvs_pg.config.defaultPortConfig.macManagementPolicy),
                'mac_learning': vmware_network.get_dvs_mac_learning(dvs_pg.config.defaultPortConfig.macManagementPolicy.macLearningPolicy),
                'teaming_policy': vmware_network.get_teaming_policy(dvs_pg.config.defaultPortConfig.uplinkTeamingPolicy),
                'port_policy': vmware_network.get_port_policy(dvs_pg.config.policy),
                'vlan_info': vmware_network.get_vlan_info(dvs_pg.config.defaultPortConfig.vlan)
            }
        except AttributeError as e:
            self.module.fail_json(
                "Failed to get an attribute on a DVS portgroup %s" % pg_id,
                portgroup_id=pg_id,
                portgroup_name=getattr(dvs_pg, 'name', None),
                attribute_name=e.name,
                exception_message=str(e)
            )

        port_config = dvs_pg.config.defaultPortConfig
        if port_config.uplinkTeamingPolicy and \
                port_config.uplinkTeamingPolicy.uplinkPortOrder:
            pg['active_uplinks'] = port_config.uplinkTeamingPolicy.uplinkPortOrder.activeUplinkPort
            pg['standby_uplinks'] = port_config.uplinkTeamingPolicy.uplinkPortOrder.standbyUplinkPort

        return pg

    def get_standard_portgroup_detailed(self, portgroup, pg_id):
        pg_name = None
        try:
            pg_name = str(portgroup.summary.name)
            ret_pg = vmware_network.get_standard_portgroup_vlan_vswitch(portgroup, pg_name)
        except AttributeError as e:
            self.module.fail_json(
                "Failed to get an attribute on a standard portgroup %s" % pg_id,
                portgroup_id=pg_id,
                portgroup_name=pg_name,
                attribute_name=e.name,
                exception_message=str(e)
            )

        ret_pg['port_id'] = pg_id
        ret_pg['type'] = 'STANDARD_PORTGROUP'
        return ret_pg

    def get_portgroup_of_vm(self):
        vms_nics = {}
        # Save a dictionary of portgroup details for reuse
        pg_map = {}
        for vm in self.vms:
            vm_nics = []
            for network_device in self._vm_network_devices(vm):
                nic_details = self._format_nic_details(network_device, pg_map)
                if not nic_details:
                    continue
                vm_nics.append(nic_details)

            vms_nics[vm.name] = vm_nics

        return vms_nics

    def _format_nic_details(self, nic, pg_map):
        nic_details = {
            'nic_mac_address': getattr(nic, "macAddress", None),
            'nic_mac_type': getattr(nic, "addressType", None),
            'nic_type': nic.__class__.__name__.replace('vim.vm.device.', '')
        }

        device_backing = nic.backing
        if hasattr(device_backing, 'port'):
            # this is a dvs
            port_group_key = device_backing.port.portgroupKey
            dvs_uuid = device_backing.port.switchUuid
            try:
                dvs = self.content.dvSwitchManager.QueryDvsByUuid(dvs_uuid)
                portgroup = dvs.LookupDvPortGroup(port_group_key)
            except Exception as e:
                self.module.fail_json(
                    "Unable to find distributed virtual switch UUID %s "
                    "or its portgroup with key %s" % (dvs_uuid, port_group_key),
                    exeception=str(e)
                )
            format_func = self.get_dvs_portgroup_detailed
        else:
            portgroup = device_backing.network
            format_func = self.get_standard_portgroup_detailed

        pg_id = portgroup._GetMoId()
        if pg_id not in pg_map:
            details = format_func(portgroup, pg_id)
            pg_map[pg_id] = details

        nic_details.update(pg_map[pg_id])
        return nic_details


def main():
    argument_spec = rest_compatible_argument_spec()
    argument_spec.update(
        dict(
            datacenter=dict(type='str', required=False),
            name=dict(type='str'),
            name_match=dict(type='str', choices=['first', 'last'], default='first'),
            uuid=dict(type='str'),
            moid=dict(type='str'),
            use_instance_uuid=dict(type='bool', default=False),
            folder=dict(type='str', required=False),
            folder_paths_are_absolute=dict(type='bool', required=False, default=False),
            vm_names=dict(type='list', elements='str', required=False)
        )
    )
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_one_of=[
            ('name', 'uuid', 'moid', 'vm_names')
        ],
        mutually_exclusive=[
            ('name', 'uuid', 'moid', 'vm_names')
        ]
    )

    portgroup_info = PortgroupInfo(module)
    portgroup_info_result = portgroup_info.get_portgroup_of_vm()
    module.exit_json(changed=False, vm_portgroup_info=portgroup_info_result)


if __name__ == '__main__':
    main()

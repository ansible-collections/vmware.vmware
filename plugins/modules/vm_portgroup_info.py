#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2023, Ansible Cloud Team (@ansible-collections)
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
author:
    - Ansible Cloud Team (@ansible-collections)
requirements:
    - vSphere Automation SDK
options:
    vm_names:
        description:
            - VM names for retrieving the information about portgroup
        required: true
        type: list
        elements: str
extends_documentation_fragment:
    - vmware.vmware.vmware_rest_client.documentation
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
from ansible_collections.vmware.vmware.plugins.module_utils.vmware import PyVmomi
from ansible_collections.vmware.vmware.plugins.module_utils.vmware_rest_client import VmwareRestClient

try:
    from pyVmomi import vim
except ImportError:
    pass


def get_standard_portgroup_vlan_vswitch(portgroup, pg_name):
    ret_pg = {'name': pg_name}
    for host in portgroup.host:
        pgs = host.config.network.portgroup
        for pg in pgs:
            if pg.spec.name == pg_name:
                ret_pg['vlan_id'] = str(pg.spec.vlanId)
                ret_pg['vswitch_name'] = str(pg.spec.vswitchName)
                return ret_pg


def get_teaming_policy(uplink_teaming_policy):
    return dict(
        policy=uplink_teaming_policy.policy.value,
        inbound_policy=uplink_teaming_policy.reversePolicy.value,
        notify_switches=uplink_teaming_policy.notifySwitches.value,
        rolling_order=uplink_teaming_policy.rollingOrder.value,
    )


def get_port_policy(config_policy):
    return dict(
        block_override=config_policy.blockOverrideAllowed,
        ipfix_override=config_policy.ipfixOverrideAllowed,
        live_port_move=config_policy.livePortMovingAllowed,
        network_rp_override=config_policy.networkResourcePoolOverrideAllowed,
        port_config_reset_at_disconnect=config_policy.portConfigResetAtDisconnect,
        security_override=config_policy.macManagementOverrideAllowed,
        shaping_override=config_policy.shapingOverrideAllowed,
        traffic_filter_override=config_policy.trafficFilterOverrideAllowed,
        uplink_teaming_override=config_policy.uplinkTeamingOverrideAllowed,
        vendor_config_override=config_policy.vendorConfigOverrideAllowed,
        vlan_override=config_policy.vlanOverrideAllowed
    )


def get_dvs_mac_learning(mac_learning_policy):
    return dict(
        allow_unicast_flooding=mac_learning_policy.allowUnicastFlooding,
        enabled=mac_learning_policy.enabled,
        limit=mac_learning_policy.limit,
        limit_policy=mac_learning_policy.limitPolicy
    )


def get_dvs_network_policy(mac_management_policy):
    return dict(
        forged_transmits=mac_management_policy.forgedTransmits,
        promiscuous=mac_management_policy.allowPromiscuous,
        mac_changes=mac_management_policy.macChanges
    )


def get_vlan_info(vlan_obj):
    if isinstance(vlan_obj, vim.dvs.VmwareDistributedVirtualSwitch.TrunkVlanSpec):
        vlan_id_list = []
        for vli in vlan_obj.vlanId:
            if vli.start == vli.end:
                vlan_id_list.append(str(vli.start))
            else:
                vlan_id_list.append('{}-{}'.format(vli.start, vli.end))
        return dict(trunk=True, pvlan=False, vlan_id=vlan_id_list)
    elif isinstance(vlan_obj, vim.dvs.VmwareDistributedVirtualSwitch.PvlanSpec):
        return dict(trunk=False, pvlan=True, vlan_id=str(vlan_obj.pvlanId))
    else:
        return dict(trunk=False, pvlan=False, vlan_id=str(vlan_obj.vlanId))


def get_dvs_port_allocation(config_type):
    if config_type == 'ephemeral':
        return 'ephemeral'
    else:
        return 'static'


def get_dvs_autoExpand(config_autoexpand):
    return 'elastic' if config_autoexpand else 'fixed'


class PortgroupInfo(PyVmomi):
    def __init__(self, module):
        super(PortgroupInfo, self).__init__(module)
        self.module = module
        self.params = module.params
        self.vmware_client = VmwareRestClient(module)
        self.vms = self.params['vm_names']

    def get_dvs_portgroup_detailed(self, pg_id):
        dvs_pg = self.get_dvs_portgroup(pg_id)
        pg = {'portgroup_name': dvs_pg.name, 'vswitch_name': dvs_pg.config.distributedVirtualSwitch.name,
              'type': 'DISTRIBUTED_PORTGROUP', 'port_id': pg_id,
              'port_binding': get_dvs_port_allocation(dvs_pg.config.type),
              'port_allocation': get_dvs_autoExpand(dvs_pg.config.autoExpand),
              'network_policy': get_dvs_network_policy(dvs_pg.config.defaultPortConfig.macManagementPolicy),
              'mac_learning': get_dvs_mac_learning(dvs_pg.config.defaultPortConfig.macManagementPolicy.macLearningPolicy),
              'teaming_policy': get_teaming_policy(dvs_pg.config.defaultPortConfig.uplinkTeamingPolicy),
              'port_policy': get_port_policy(dvs_pg.config.policy),
              'vlan_info': get_vlan_info(dvs_pg.config.defaultPortConfig.vlan)
              }

        if dvs_pg.config.defaultPortConfig.uplinkTeamingPolicy and \
                dvs_pg.config.defaultPortConfig.uplinkTeamingPolicy.uplinkPortOrder:
            pg['active_uplinks'] = dvs_pg.config.defaultPortConfig.uplinkTeamingPolicy.uplinkPortOrder.activeUplinkPort
            pg['standby_uplinks'] = dvs_pg.config.defaultPortConfig.uplinkTeamingPolicy.uplinkPortOrder.standbyUplinkPort

        return pg

    def get_standard_portgroup_detailed(self, pg_id):
        pg = self.get_standard_portgroup(pg_id)
        pg_name = str(pg.summary.name)
        ret_pg = get_standard_portgroup_vlan_vswitch(pg, pg_name)
        ret_pg['port_id'] = pg_id
        ret_pg['type'] = 'STANDARD_PORTGROUP'
        return ret_pg

    def get_portgroup_of_vm(self):
        vms_nics = {}
        # Save a dictionary of portgroup details for reuse
        pg_map = {}
        for vm in self.vms:
            vm_detailed = self.get_vm_detailed(vm_name=vm)
            vm_nics = []
            for nic in vm_detailed.nics:
                nic_details = {
                    'nic_mac_address': vm_detailed.nics[nic].mac_address,
                    'nic_mac_type': str(vm_detailed.nics[nic].mac_type),
                    'nic_type': str(vm_detailed.nics[nic].type)
                }

                pg_type = str(vm_detailed.nics[nic].backing.type)
                pg_id = str(vm_detailed.nics[nic].backing.network)

                if pg_type not in ['DISTRIBUTED_PORTGROUP', 'STANDARD_PORTGROUP']:
                    continue
                if pg_id not in pg_map:
                    if pg_type == 'STANDARD_PORTGROUP':
                        pg_map[pg_id] = self.get_standard_portgroup_detailed(pg_id)
                    else:
                        pg_map[pg_id] = self.get_dvs_portgroup_detailed(pg_id)

                nic_details.update(pg_map[pg_id])
                vm_nics.append(nic_details)

            vms_nics[vm_detailed.name] = vm_nics

        return vms_nics

    def get_vm_detailed(self, vm_name):
        vm_id = self.vmware_client.get_vm_obj_by_name(vm_name)
        return self.vmware_client.api_client.vcenter.VM.get(vm=vm_id)


def main():
    argument_spec = VmwareRestClient.vmware_client_argument_spec()
    argument_spec.update(
        dict(
            vm_names=dict(type='list', elements='str', required=True)
        )
    )
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    portgroup_info = PortgroupInfo(module)
    portgroup_info_result = portgroup_info.get_portgroup_of_vm()
    module.exit_json(changed=False, vm_portgroup_info=portgroup_info_result)


if __name__ == '__main__':
    main()

#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2023, Ansible Cloud Team (@ansible-collections)
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type


DOCUMENTATION = r"""
---
module: cluster_ha_vm_overrides_info
short_description: Get vSphere High Availability (HA) VM override settings.
description:
    - Gets HA VM override settings on VMware vSphere clusters.
    - Although VM overrides are shown in a unified view in vCenter, this module only gets the HA override settings.
author:
    - Ansible Cloud Team (@ansible-collections)

seealso:
    - module: vmware.vmware.cluster_ha
    - module: vmware.vmware.cluster_ha_vm_overrides
    - module: vmware.vmware.cluster_drs_vm_overrides_info

options:
    cluster:
        description:
            - The name of the cluster to get the VM override settings for.
        type: str
        required: true
        aliases: [ cluster_name ]
    datacenter:
        description:
            - The name of the datacenter.
        type: str
        required: true
        aliases: [ datacenter_name ]

extends_documentation_fragment:
    - vmware.vmware.base_options
"""

EXAMPLES = r"""
- name: Gather HA VM override settings for a cluster
  vmware.vmware.cluster_ha_vm_overrides_info:
    datacenter: DC01
    cluster: Cluster01
"""

RETURN = r"""
cluster:
    description: Display name and MOID of the cluster that was queried.
    returned: success
    type: dict
    sample:
        name: Cluster01
        moid: cluster-21
vm_overrides:
    description:
        - HA VM override entries from C(cluster.configurationEx.dasVmConfig).
        - Each item always includes C(vm_moid), C(vm_name), C(storage_apd_response),
          C(storage_pdl_response), and C(vm_monitoring).
        - When settings are able to be retrieved, C(isolation_response), C(restart_priority), and C(restart_priority_timeout)
          are included.
    returned: success
    type: list
    sample:
        - vm_moid: vm-42
          vm_name: MyVirtualMachine
          isolation_response: powerOff
          restart_priority: medium
          restart_priority_timeout: -1
          storage_apd_response:
            mode: restartConservative
            delay: 180
            restart_vms: true
          storage_pdl_response: warning
          vm_monitoring:
            mode: vmAndAppMonitoring
            failure_interval: 30
            minimum_uptime: 120
            maximum_resets: 3
            maximum_resets_window: 180
            use_cluster_settings: false
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.vmware.vmware.plugins.module_utils._module_pyvmomi_base import (
    ModulePyvmomiBase,
)
from ansible_collections.vmware.vmware.plugins.module_utils.argument_spec import (
    base_argument_spec,
)


class VMwareHaVmOverridesInfo(ModulePyvmomiBase):
    def __init__(self, module):
        super().__init__(module)

        datacenter = self.get_datacenter_by_name_or_moid(
            self.params.get("datacenter"), fail_on_missing=True
        )
        self.cluster = self.get_cluster_by_name_or_moid(
            self.params.get("cluster"), fail_on_missing=True, datacenter=datacenter
        )

    def _get_apd_response_settings(self, vm_component_protection_settings):
        return dict(
            mode=vm_component_protection_settings.vmStorageProtectionForAPD,
            delay=vm_component_protection_settings.vmTerminateDelayForAPDSec,
            restart_vms=(
                True
                if vm_component_protection_settings.vmReactionOnAPDCleared == "reset"
                else False
            ),
        )

    def _get_pdl_response_settings(self, vm_component_protection_settings):
        return vm_component_protection_settings.vmStorageProtectionForPDL

    def _get_vm_tools_monitoring_settings(self, vm_tools_monitoring_settings):
        return dict(
            mode=vm_tools_monitoring_settings.vmMonitoring,
            failure_interval=vm_tools_monitoring_settings.failureInterval,
            minimum_uptime=vm_tools_monitoring_settings.minUpTime,
            maximum_resets=vm_tools_monitoring_settings.maxFailures,
            maximum_resets_window=vm_tools_monitoring_settings.maxFailureWindow,
            use_cluster_settings=vm_tools_monitoring_settings.clusterSettings,
        )

    def lookup_current_vm_overrides(self):
        output = []
        for vm_override in getattr(self.cluster.configurationEx, "dasVmConfig", []):
            das_settings = getattr(vm_override, "dasSettings", None)
            data = dict(
                vm_moid=vm_override.key._GetMoId(),
                vm_name=vm_override.key.name,
                storage_apd_response=dict(),
                storage_pdl_response=None,
                vm_monitoring=dict(),
            )
            if das_settings is not None:
                data["isolation_response"] = getattr(
                    das_settings, "isolationResponse", None
                )
                data["restart_priority"] = getattr(
                    das_settings, "restartPriority", None
                )
                data["restart_priority_timeout"] = getattr(
                    das_settings, "restartPriorityTimeout", None
                )

                if getattr(das_settings, "vmComponentProtectionSettings"):
                    data["storage_apd_response"] = self._get_apd_response_settings(
                        das_settings.vmComponentProtectionSettings
                    )
                    data["storage_pdl_response"] = self._get_pdl_response_settings(
                        das_settings.vmComponentProtectionSettings
                    )
                if getattr(das_settings, "vmToolsMonitoringSettings"):
                    data["vm_monitoring"] = self._get_vm_tools_monitoring_settings(
                        das_settings.vmToolsMonitoringSettings
                    )

            output.append(data)

        return output


def main():
    module = AnsibleModule(
        argument_spec={
            **base_argument_spec(),
            **dict(
                cluster=dict(type="str", required=True, aliases=["cluster_name"]),
                datacenter=dict(type="str", required=True, aliases=["datacenter_name"]),
            ),
        },
        supports_check_mode=True,
    )

    result = dict(
        changed=False,
        cluster=dict(),
        vm_overrides=[],
    )

    cluster_ha = VMwareHaVmOverridesInfo(module)
    result["cluster"]["name"] = cluster_ha.cluster.name
    result["cluster"]["moid"] = cluster_ha.cluster._GetMoId()
    result["vm_overrides"] = cluster_ha.lookup_current_vm_overrides()

    module.exit_json(**result)


if __name__ == "__main__":
    main()

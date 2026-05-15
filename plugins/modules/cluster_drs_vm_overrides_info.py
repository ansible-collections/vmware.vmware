#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2023, Ansible Cloud Team (@ansible-collections)
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type


DOCUMENTATION = r"""
---
module: cluster_drs_vm_overrides_info
short_description: Get Distributed Resource Scheduler (DRS) VM override settings.
description:
    - Gets DRS VM override settings on VMware vSphere clusters.
    - Although VM overrides are shown in a unified view in vCenter, this module only gets the DRS override settings.
author:
    - Ansible Cloud Team (@ansible-collections)

seealso:
    - module: vmware.vmware.cluster_drs
    - module: vmware.vmware.cluster_ha_vm_overrides_info
    - module: vmware.vmware.cluster_drs_vm_overrides

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
- name: Gather VM override settings for a cluster
  vmware.vmware.cluster_drs_vm_overrides_info:
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
        - Information about the VM overrides for the cluster
        - Each entry has the virtual machine MOID, name, behavior, and enabled state
    returned: On success
    type: list
    sample:
        - vm_moid: vm-42
          vm_name: MyVirtualMachine
          behavior: fullyAutomated
          enabled: true
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.vmware.vmware.plugins.module_utils._module_pyvmomi_base import (
    ModulePyvmomiBase,
)
from ansible_collections.vmware.vmware.plugins.module_utils.argument_spec import (
    base_argument_spec,
)


class VMwareDrsVmOverridesInfo(ModulePyvmomiBase):
    def __init__(self, module):
        """
        Resolve the datacenter and cluster using the module's datacenter and cluster parameters.

        Unlike the manage module, this does not require DRS to be enabled; missing config is handled when gathering facts.
        """
        super().__init__(module)

        datacenter = self.get_datacenter_by_name_or_moid(
            self.params.get("datacenter"), fail_on_missing=True
        )
        self.cluster = self.get_cluster_by_name_or_moid(
            self.params.get("cluster"), fail_on_missing=True, datacenter=datacenter
        )

    def lookup_current_vm_overrides(self):
        """
        Return a dict keyed by VM MoID; each value includes MoID, name, DRS behavior, and enabled.

        Returns an empty dict if DRS config is missing, DRS is off, or VM behavior overrides are disabled on the cluster.
        """
        current_vm_overrides = dict()
        for vm_override in getattr(self.cluster.configurationEx, "drsVmConfig", []):
            current_vm_overrides[vm_override.key._GetMoId()] = {
                "vm_moid": vm_override.key._GetMoId(),
                "vm_name": vm_override.key.name,
                "behavior": vm_override.behavior,
                "enabled": vm_override.enabled,
            }
        return current_vm_overrides


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

    cluster_drs = VMwareDrsVmOverridesInfo(module)
    result["cluster"]["name"] = cluster_drs.cluster.name
    result["cluster"]["moid"] = cluster_drs.cluster._GetMoId()
    result["vm_overrides"] = list(cluster_drs.lookup_current_vm_overrides().values())

    module.exit_json(**result)


if __name__ == "__main__":
    main()

#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2023, Ansible Cloud Team (@ansible-collections)
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type


DOCUMENTATION = r"""
---
module: cluster_drs_vm_overrides
short_description: Manage Distributed Resource Scheduler (DRS) VM override settings.
description:
    - Manages DRS VM override settings on VMware vSphere clusters.
    - VM override settings are used to override the default DRS behavior for individual virtual machines.
    - You must enable DRS VM override settings before you can use them. See m(vmware.vmware.cluster_drs).
    - VMs must exist in the cluster before you can set their override settings.
    - When a VM is removed from the cluster, its override settings are also automatically removed.
    - Although VM overrides are shown in a unified view in vCenter, this module only manages the DRS override settings.
      Removing a VM override does not remove all overrides, just the DRS related ones.
author:
    - Ansible Cloud Team (@ansible-collections)

seealso:
    - module: vmware.vmware.cluster_drs
    - module: vmware.vmware.cluster_ha_vm_overrides
    - module: vmware.vmware.cluster_drs_vm_overrides_info

options:
    cluster:
        description:
            - The name of the cluster to be managed.
        type: str
        required: true
        aliases: [ cluster_name ]
    datacenter:
        description:
            - The name of the datacenter.
        type: str
        required: true
        aliases: [ datacenter_name ]
    state:
        description:
            - The state of the VM override settings.
            - If set to V(present) and O(append) is true, the VM override settings are added if needed.
            - If set to V(present) and O(append) is false, the VM override settings in the cluster will be updated to match the desired configuration exactly.
            - If set to V(absent), the VM override settings are removed from the cluster if they exist.
        type: str
        choices: [ present, absent ]
        default: present
    append:
        description:
            - Whether to add the VM override settings if they do not exist.
            - If set to V(true), the VM override settings are added if needed and any existing VM override settings are not modified.
            - If set to V(false), the VM override settings are updated to match the desired configuration exactly.
            - This parameter is ignored if O(state) is set to V(absent).
        type: bool
        required: false
        default: true
    vm_overrides:
        description:
            - A list of virtual machine override settings to apply to the cluster.
            - Each entry should describe a override rule for a virtual machine.
        type: list
        elements: dict
        required: true
        suboptions:
            virtual_machine:
                description:
                    - The name or MOID of the virtual machine for which to manage the override settings.
                    - Using the MOID is recommended as the name lookup takes longer and cannot handle duplicate names.
                type: str
                required: true
            behavior:
                description:
                    - The DRS behavior for the virtual machine.
                    - If set to V(fullyAutomated), then vCenter automates both the migration of the virtual machine
                        and its placement with a host at power on.
                    - If set to V(manual), then vCenter generates recommendations for the migration of the virtual machine and
                        for the placement with a host, but does not implement the recommendations automatically.
                    - If set to V(partiallyAutomated), then vCenter generates recommendations for the migration of the virtual machine and
                        for the placement with a host, then automatically implements placement recommendations at power on.
                type: str
                required: false
                choices: [ fullyAutomated, manual, partiallyAutomated ]
            enabled:
                description:
                    - Whether the override settings are enabled for the virtual machine.
                type: bool
                required: false

extends_documentation_fragment:
    - vmware.vmware.base_options
"""

EXAMPLES = r"""
- name: Enable DRS
  vmware.vmware.cluster_drs:
    hostname: '{{ vcenter_hostname }}'
    username: '{{ vcenter_username }}'
    password: '{{ vcenter_password }}'
    datacenter_name: DC01
    cluster_name: Cluster01
    enable: true
  delegate_to: localhost

# Use the lookup plugin to get the VM MOID when names are ambiguous
- name: Ensure a VM override is present
  vmware.vmware.cluster_drs_vm_overrides:
    datacenter: DC01
    cluster: Cluster01
    state: present
    append: true
    vm_overrides:
      - virtual_machine: "{{ lookup('vmware.vmware.moid_from_path', '/DC01/vm/MyVirtualMachine') }}"
        behavior: fullyAutomated
        enabled: true

- name: Ensure a VM override is absent
  vmware.vmware.cluster_drs_vm_overrides:
    datacenter: DC01
    cluster: Cluster01
    state: absent
    vm_overrides:
      - virtual_machine: MyVirtualMachine

- name: Clear all vm overrides
  vmware.vmware.cluster_drs_vm_overrides:
    datacenter: DC01
    cluster: Cluster01
    state: present
    append: false
    vm_overrides: []

- name: Ensure only these overrides are present
  vmware.vmware.cluster_drs_vm_overrides:
    datacenter: DC01
    cluster: Cluster01
    state: present
    append: false
    vm_overrides:
      - virtual_machine: MyVirtualMachine
        behavior: fullyAutomated
        enabled: true
      - virtual_machine: MyOtherVirtualMachine
        behavior: manual
        enabled: false

- name: Change only behavior for an existing override (enabled defaults stay cluster-default)
  vmware.vmware.cluster_drs_vm_overrides:
    datacenter: DC01
    cluster: Cluster01
    state: present
    vm_overrides:
      - virtual_machine: vm-42
        behavior: manual
"""

RETURN = r"""
cluster:
    description: Display name and MOID of the cluster that was configured.
    returned: success
    type: dict
    sample:
        name: Cluster01
        moid: cluster-21
overrides_removed:
    description:
        - One entry per VM whose DRS override was removed in this run.
        - Each entry only contains C(vm_moid) and C(vm_name); use M(vmware.vmware.cluster_drs_vm_overrides_info) to read behavior and enabled before/after.
    returned: success
    type: list
    sample:
        - vm_moid: vm-42
          vm_name: MyVirtualMachine
overrides_added:
    description:
        - One entry per VM whose DRS override was added. Each entry only contains C(vm_moid) and C(vm_name).
    returned: success
    type: list
    sample:
        - vm_moid: vm-42
          vm_name: MyVirtualMachine
overrides_updated:
    description:
        - One entry per VM whose DRS override was changed. Each entry only contains C(vm_moid) and C(vm_name).
    returned: success
    type: list
    sample:
        - vm_moid: vm-42
          vm_name: MyVirtualMachine
"""

try:
    from pyVmomi import vim, vmodl
except ImportError:
    pass

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.vmware.vmware.plugins.module_utils._module_pyvmomi_base import (
    ModulePyvmomiBase,
)
from ansible_collections.vmware.vmware.plugins.module_utils.argument_spec import (
    base_argument_spec,
)
from ansible_collections.vmware.vmware.plugins.module_utils._vsphere_tasks import (
    TaskError,
    RunningTaskMonitor,
)
from ansible_collections.vmware.vmware.plugins.module_utils._cluster_settings import (
    BaseVmOverrideChangeTracker,
)
from ansible.module_utils.common.text.converters import to_native


class DrsVmOverrideChangeTracker(BaseVmOverrideChangeTracker):
    def __init__(self, current_vm_overrides, param_vm_overrides):
        super().__init__(current_vm_overrides, param_vm_overrides)

    def _overrides_differ(self, desired, current):
        return BaseVmOverrideChangeTracker._is_desired_set_and_different_from_current(
            desired, current, "behavior"
        ) or BaseVmOverrideChangeTracker._is_desired_set_and_different_from_current(
            desired, current, "enabled"
        )


class VMwareDrsVmOverrides(ModulePyvmomiBase):
    def __init__(self, module):
        """
        Resolve the datacenter and cluster from module parameters.

        Fails the task if DRS is missing, disabled, or if per-VM behavior overrides are not enabled on the cluster.
        """
        super().__init__(module)

        datacenter = self.get_datacenter_by_name_or_moid(
            self.params.get("datacenter"), fail_on_missing=True
        )
        self.cluster = self.get_cluster_by_name_or_moid(
            self.params.get("cluster"), fail_on_missing=True, datacenter=datacenter
        )
        try:
            current_drs_config = self.cluster.configurationEx.drsConfig
        except AttributeError:
            self.module.fail_json(
                msg="DRS configuration is not available on the cluster. Please enable DRS before using this module."
            )
        if not current_drs_config.enableVmBehaviorOverrides:
            self.module.fail_json(
                msg="DRS VM override settings are not enabled on the cluster. Please enable them before using this module."
            )
        if not current_drs_config.enabled:
            self.module.fail_json(
                msg="DRS is not enabled on the cluster. Please enable it before using this module."
            )

    def _lookup_vms_in_param_overrides(self):
        """
        Look up each virtual_machine from vm_overrides and key the result by VM MoID.

        Returns a dict keyed by VM MoID. Each value is a dict with the virtual machine object, and any desired override settings.
        """
        remapped_vm_overrides = dict()
        for vm_override in self.params.get("vm_overrides"):
            search_results = self.get_objs_by_name_or_moid(
                [vim.VirtualMachine],
                vm_override.get("virtual_machine"),
                return_all=False,
            )
            if len(search_results) == 0:
                self.module.fail_json(
                    msg="Unable to find virtual machine with name or MOID %s"
                    % vm_override.get("virtual_machine")
                )

            vm = search_results[0]
            drs_config_spec = vim.cluster.DrsVmConfigInfo(key=vm)
            if "behavior" in vm_override:
                drs_config_spec.behavior = vm_override["behavior"]
            if "enabled" in vm_override:
                drs_config_spec.enabled = vm_override["enabled"]
            remapped_vm_overrides[vm._GetMoId()] = drs_config_spec
        return remapped_vm_overrides

    def _lookup_current_vm_overrides(self):
        """
        Read cluster.configurationEx.drsVmConfig into a dict keyed by VM MoID.

        Returns a dict keyed by VM MoID. Each value is a vim.cluster.DrsVmConfigInfo object.
        """
        current_vm_overrides = dict()
        for vm_override in self.cluster.configurationEx.drsVmConfig:
            current_vm_overrides[vm_override.key._GetMoId()] = vm_override
        return current_vm_overrides

    def get_overrides_changes(self):
        """
        Compare live cluster overrides to module input and return a populated VmOverrideChangeTracker.

        Dispatches to process_absent_changes or process_present_changes based on state and append.
        """
        change_tracker = DrsVmOverrideChangeTracker(
            current_vm_overrides=self._lookup_current_vm_overrides(),
            param_vm_overrides=self._lookup_vms_in_param_overrides(),
        )
        if self.params.get("state") == "absent":
            change_tracker.process_absent_changes()
        elif self.params.get("state") == "present":
            change_tracker.process_present_changes(append=self.params.get("append"))

        return change_tracker

    def _create_drs_vm_config_spec(self, vm_overrides, operation):
        """
        Build a cluster ConfigSpecEx whose drsVmConfigSpec list applies one API operation.

        Use operation add with DrsVmConfigInfo for create/update, or remove with removeKey set to the VM reference.
        """
        cluster_config_spec = vim.cluster.ConfigSpecEx()
        cluster_config_spec.drsVmConfigSpec = []
        kwargs = dict(operation=operation)
        for vm_override in vm_overrides:
            if operation == "remove":
                kwargs["removeKey"] = vm_override.key
            else:
                kwargs["info"] = vm_override
            cluster_config_spec.drsVmConfigSpec.append(
                vim.cluster.DrsVmConfigSpec(**kwargs)
            )

        return cluster_config_spec

    def apply_drs_configuration(self, vm_overrides, operation):
        """
        Submit ReconfigureComputeResource_Task for the given overrides and wait for completion.

        On vSphere or task errors, fails the module with a readable message. Returns the monitor's task result on success.
        """
        cluster_config_spec = self._create_drs_vm_config_spec(vm_overrides, operation)

        try:
            task = self.cluster.ReconfigureComputeResource_Task(
                cluster_config_spec, True
            )
            _, task_result = RunningTaskMonitor(  # pylint: disable=disallowed-name
                task
            ).wait_for_completion()
        except (vmodl.RuntimeFault, vmodl.MethodFault) as vmodl_fault:
            self.module.fail_json(msg=to_native(vmodl_fault.msg))
        except TaskError as task_e:
            self.module.fail_json(msg=to_native(task_e))
        except Exception as generic_exc:
            self.module.fail_json(
                msg="Failed to update cluster due to exception %s"
                % to_native(generic_exc)
            )

        return task_result


def main():
    module = AnsibleModule(
        argument_spec={
            **base_argument_spec(),
            **dict(
                cluster=dict(type="str", required=True, aliases=["cluster_name"]),
                datacenter=dict(type="str", required=True, aliases=["datacenter_name"]),
                state=dict(
                    type="str", choices=["present", "absent"], default="present"
                ),
                append=dict(type="bool", required=False, default=True),
                vm_overrides=dict(
                    type="list",
                    required=True,
                    elements="dict",
                    options=dict(
                        virtual_machine=dict(type="str", required=True),
                        behavior=dict(
                            type="str",
                            required=False,
                            choices=["fullyAutomated", "manual", "partiallyAutomated"],
                        ),
                        enabled=dict(type="bool", required=False),
                    ),
                ),
            ),
        },
        supports_check_mode=True,
    )

    result = dict(
        changed=False,
        cluster=dict(),
        overrides_removed=[],
        overrides_added=[],
        overrides_updated=[],
    )

    cluster_drs = VMwareDrsVmOverrides(module)
    result["cluster"]["name"] = cluster_drs.cluster.name
    result["cluster"]["moid"] = cluster_drs.cluster._GetMoId()

    change_tracker = cluster_drs.get_overrides_changes()
    if change_tracker.has_changes():
        result["changed"] = True
        result["overrides_removed"] = (
            BaseVmOverrideChangeTracker.format_override_specs_for_json(
                change_tracker.to_remove.values()
            )
        )
        result["overrides_added"] = (
            BaseVmOverrideChangeTracker.format_override_specs_for_json(
                change_tracker.to_add.values()
            )
        )
        result["overrides_updated"] = (
            BaseVmOverrideChangeTracker.format_override_specs_for_json(
                change_tracker.to_update.values()
            )
        )
        if not module.check_mode:
            if change_tracker.to_add:
                cluster_drs.apply_drs_configuration(
                    change_tracker.to_add.values(), operation="add"
                )
            if change_tracker.to_update:
                cluster_drs.apply_drs_configuration(
                    change_tracker.to_update.values(), operation="edit"
                )
            if change_tracker.to_remove:
                cluster_drs.apply_drs_configuration(
                    change_tracker.to_remove.values(), operation="remove"
                )

    module.exit_json(**result)


if __name__ == "__main__":
    main()

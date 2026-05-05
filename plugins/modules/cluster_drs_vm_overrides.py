#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2023, Ansible Cloud Team (@ansible-collections)
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function
__metaclass__ = type


DOCUMENTATION = r'''
---
module: cluster_drs_vm_overrides
short_description: Manage Distributed Resource Scheduler (DRS) VM override settings.
description:
    - Manages DRS VM override settings on VMware vSphere clusters.
    - VM override settings are used to override the default DRS behavior for individual virtual machines.
    - You must enable DRS VM override settings before you can use them. See m(vmware.vmware.cluster_drs).
    - VMs must exist in the cluster before you can set their override settings.
    - When a VM is removed from the cluster, its override settings are also automatically removed.
author:
    - Ansible Cloud Team (@ansible-collections)

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
            drs_behavior:
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
                default: fullyAutomated
                choices: [ fullyAutomated, manual, partiallyAutomated ]
            enable:
                description:
                    - Whether to enable the override settings for the virtual machine.
                type: bool
                required: false
                default: true

extends_documentation_fragment:
    - vmware.vmware.base_options
'''

EXAMPLES = r'''
- name: Enable DRS
  vmware.vmware.cluster_drs:
    hostname: '{{ vcenter_hostname }}'
    username: '{{ vcenter_username }}'
    password: '{{ vcenter_password }}'
    datacenter_name: DC01
    cluster_name: Cluster01
    enable: true
  delegate_to: localhost

- name: Ensure a VM override is present
  vmware.vmware.cluster_drs_vm_overrides:
    datacenter: DC01
    cluster: Cluster01
    state: present
    append: true
    vm_overrides:
      - virtual_machine: "{{ lookup('vmware.vmware.moid_from_path', '/DC01/vm/MyVirtualMachine') }}"
        drs_behavior: fullyAutomated
        enable: true

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
        drs_behavior: fullyAutomated
        enable: true
      - virtual_machine: MyOtherVirtualMachine
        drs_behavior: manual
        enable: false
'''

RETURN = r'''
cluster:
    description:
        - Information about the target cluster
    returned: On success
    type: dict
    sample:
        moid: cluster-79828,
        name: test-cluster
overrides_removed:
    description:
        - Information about the VM overrides that were removed
        - Each entry has the virtual machine MOID, name, behavior, and enabled state
    returned: On success
    type: list
    sample:
        - virtual_machine_moid: vm-1234567890
          virtual_machine_name: MyVirtualMachine
          behavior: fullyAutomated
          enabled: true
overrides_added:
    description:
        - Information about the VM overrides that were added
        - Each entry has the virtual machine MOID, name, behavior, and enabled state
    returned: On success
    type: list
    sample:
        - virtual_machine_moid: vm-1234567890
          virtual_machine_name: MyVirtualMachine
          behavior: fullyAutomated
          enabled: true
overrides_updated:
    description:
        - Information about the VM overrides that were updated
        - Each entry has the virtual machine MOID, name, behavior, and enabled state
    returned: On success
    type: list
    sample:
        - virtual_machine_moid: vm-1234567890
          virtual_machine_name: MyVirtualMachine
          behavior: fullyAutomated
          enabled: true
'''

try:
    from pyVmomi import vim, vmodl
except ImportError:
    pass

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.vmware.vmware.plugins.module_utils._module_pyvmomi_base import (
    ModulePyvmomiBase
)
from ansible_collections.vmware.vmware.plugins.module_utils.argument_spec import (
    base_argument_spec
)
from ansible_collections.vmware.vmware.plugins.module_utils._vsphere_tasks import (
    TaskError,
    RunningTaskMonitor
)
from ansible.module_utils.common.text.converters import to_native


class VmOverrideChangeTracker:
    """
    Compare desired VM override dicts (by VM MoID) to current cluster overrides.

    current_vm_overrides and param_vm_overrides are dicts:
        moid -> {'virtual_machine': vim.VirtualMachine, 'behavior': str, 'enabled': bool}
    """

    def __init__(self, current_vm_overrides, param_vm_overrides):
        """
        Load the live cluster overrides and the module's desired overrides.

        Populates to_add, to_update, to_remove, and final_overrides when process_* methods run.
        to_add, to_update, and to_remove show which overrides need to be added, updated, and removed.
        final_overrides is the complete set of overrides that should exist after processing. Mainly used
        when state is present and append is false.
        """
        self.current_vm_overrides = current_vm_overrides
        self.param_vm_overrides = param_vm_overrides
        self.to_add = {}
        self.to_update = {}
        self.to_remove = {}
        self.final_overrides = {}

    @staticmethod
    def _overrides_differ(desired, current):
        """
        Compare desired and current override dicts for the same VM.

        Returns True when behavior or enabled differs; used to decide whether an existing override needs an update.
        """
        return (
            desired.get('behavior') != current.get('behavior') or
            desired.get('enabled') != current.get('enabled')
        )

    def has_changes(self):
        """
        Return True after process_absent_changes or process_present_changes if work is pending.

        Check this before applying API calls so check mode and idempotency stay correct.
        """
        return (
            len(self.to_add) > 0 or
            len(self.to_update) > 0 or
            len(self.to_remove) > 0
        )

    def process_absent_changes(self):
        """
        Used when module state is absent: remove overrides only for VMs named in the task.

        Starts from current cluster overrides, then records removals and drops those keys from final_overrides.
        """
        self.final_overrides = self.current_vm_overrides.copy()
        for moid in self.param_vm_overrides.keys():
            if moid in self.current_vm_overrides:
                self.to_remove[moid] = self.current_vm_overrides[moid]
                del self.final_overrides[moid]

        return

    def process_present_changes(self, append=True):
        """
        Used when module state is present: merge desired overrides into the cluster view.

        With append True, existing overrides not listed in the task are kept. With append False, final_overrides
        matches the task exactly and extra cluster overrides are marked for removal.
        """
        if append:
            self.final_overrides = self.current_vm_overrides.copy()

        for moid, desired in self.param_vm_overrides.items():
            if moid not in self.current_vm_overrides:
                self.to_add[moid] = desired

            elif self._overrides_differ(desired, self.current_vm_overrides[moid]):
                self.to_update[moid] = desired

            self.final_overrides[moid] = desired

        if append:
            return

        for moid, current in self.current_vm_overrides.items():
            if moid not in self.final_overrides:
                self.to_remove[moid] = current


class VMwareDrsVmOverrides(ModulePyvmomiBase):
    def __init__(self, module):
        """
        Resolve the datacenter and cluster from module parameters.

        Fails the task if DRS is missing, disabled, or if per-VM behavior overrides are not enabled on the cluster.
        """
        super().__init__(module)

        datacenter = self.get_datacenter_by_name_or_moid(self.params.get('datacenter'), fail_on_missing=True)
        self.cluster = self.get_cluster_by_name_or_moid(self.params.get('cluster'), fail_on_missing=True, datacenter=datacenter)
        try:
            current_drs_config = self.cluster.configurationEx.drsConfig
        except AttributeError:
            self.module.fail_json(msg="DRS configuration is not available on the cluster. Please enable DRS before using this module.")
        if (not current_drs_config.enableVmBehaviorOverrides):
            self.module.fail_json(msg="DRS VM override settings are not enabled on the cluster. Please enable them before using this module.")
        if (not current_drs_config.enabled):
            self.module.fail_json(msg="DRS is not enabled on the cluster. Please enable it before using this module.")

    def _lookup_vms_in_param_overrides(self):
        """
        Look up each virtual_machine from vm_overrides and key the result by VM MoID.

        Each value holds the vim.VirtualMachine, desired DRS behavior, and enabled flag. Missing VMs fail the module.
        """
        remapped_vm_overrides = dict()
        for vm_override in self.params.get('vm_overrides'):
            search_results = self.get_objs_by_name_or_moid([vim.VirtualMachine], vm_override.get('virtual_machine'), return_all=False)
            if len(search_results) == 0:
                self.module.fail_json(msg="Unable to find virtual machine with name or MOID %s" % vm_override.get('virtual_machine'))

            vm = search_results[0]
            remapped_vm_overrides[vm._GetMoId()] = {
                'virtual_machine': vm,
                'behavior': vm_override.get('drs_behavior'),
                'enabled': vm_override.get('enable')
            }
        return remapped_vm_overrides

    def _lookup_current_vm_overrides(self):
        """
        Read cluster.configurationEx.drsVmConfig into a dict keyed by VM MoID.

        Values mirror the structure used for desired overrides (VM object, behavior, enabled).
        """
        current_vm_overrides = dict()
        for vm_override in self.cluster.configurationEx.drsVmConfig:
            current_vm_overrides[vm_override.key._GetMoId()] = {
                'virtual_machine': vm_override.key,
                'behavior': vm_override.behavior,
                'enabled': vm_override.enabled
            }
        return current_vm_overrides

    def get_overrides_changes(self):
        """
        Compare live cluster overrides to module input and return a populated VmOverrideChangeTracker.

        Dispatches to process_absent_changes or process_present_changes based on state and append.
        """
        change_tracker = VmOverrideChangeTracker(
            current_vm_overrides=self._lookup_current_vm_overrides(),
            param_vm_overrides=self._lookup_vms_in_param_overrides()
        )
        if self.params.get('state') == 'absent':
            change_tracker.process_absent_changes()
        elif self.params.get('state') == 'present':
            change_tracker.process_present_changes(append=self.params.get('append'))

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
            if operation == 'remove':
                kwargs['removeKey'] = vm_override['virtual_machine']
            else:
                kwargs['info'] = vim.cluster.DrsVmConfigInfo(
                    key=vm_override['virtual_machine'],
                    behavior=vm_override['behavior'],
                    enabled=vm_override['enabled']
                )
            cluster_config_spec.drsVmConfigSpec.append(vim.cluster.DrsVmConfigSpec(**kwargs))

        return cluster_config_spec

    def apply_drs_configuration(self, vm_overrides, operation):
        """
        Submit ReconfigureComputeResource_Task for the given overrides and wait for completion.

        On vSphere or task errors, fails the module with a readable message. Returns the monitor's task result on success.
        """
        cluster_config_spec = self._create_drs_vm_config_spec(vm_overrides, operation)

        try:
            task = self.cluster.ReconfigureComputeResource_Task(cluster_config_spec, True)
            _, task_result = RunningTaskMonitor(task).wait_for_completion()   # pylint: disable=disallowed-name
        except (vmodl.RuntimeFault, vmodl.MethodFault)as vmodl_fault:
            self.module.fail_json(msg=to_native(vmodl_fault.msg))
        except TaskError as task_e:
            self.module.fail_json(msg=to_native(task_e))
        except Exception as generic_exc:
            self.module.fail_json(msg="Failed to update cluster due to exception %s" % to_native(generic_exc))

        return task_result


def format_change_list_for_json(change_list):
    return [
        {
            'virtual_machine_moid': change['virtual_machine']._GetMoId(),
            'virtual_machine_name': change['virtual_machine'].name,
            'behavior': change['behavior'],
            'enabled': change['enabled']
        }
        for change in change_list
    ]


def main():
    module = AnsibleModule(
        argument_spec={
            **base_argument_spec(), **dict(
                cluster=dict(type='str', required=True, aliases=['cluster_name']),
                datacenter=dict(type='str', required=True, aliases=['datacenter_name']),
                state=dict(type='str', choices=['present', 'absent'], default='present'),
                append=dict(type='bool', required=False, default=True),
                vm_overrides=dict(
                    type='list', required=True, elements='dict', options=dict(
                        virtual_machine=dict(type='str', required=True),
                        drs_behavior=dict(type='str', required=False, default='fullyAutomated', choices=['fullyAutomated', 'manual', 'partiallyAutomated']),
                        enable=dict(type='bool', required=False, default=True),
                    )),
            )
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
    result['cluster']['name'] = cluster_drs.cluster.name
    result['cluster']['moid'] = cluster_drs.cluster._GetMoId()

    change_tracker = cluster_drs.get_overrides_changes()
    if change_tracker.has_changes():
        result['changed'] = True
        result['overrides_removed'] = format_change_list_for_json(change_tracker.to_remove.values())
        result['overrides_added'] = format_change_list_for_json(change_tracker.to_add.values())
        result['overrides_updated'] = format_change_list_for_json(change_tracker.to_update.values())
        if not module.check_mode:
            if change_tracker.to_add or change_tracker.to_update:
                cluster_drs.apply_drs_configuration(
                    list(change_tracker.to_add.values()) + list(change_tracker.to_update.values()),
                    operation="add"
                )

            if change_tracker.to_remove:
                cluster_drs.apply_drs_configuration(change_tracker.to_remove.values(), operation="remove")

    module.exit_json(**result)


if __name__ == '__main__':
    main()

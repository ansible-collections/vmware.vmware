#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2023, Ansible Cloud Team (@ansible-collections)
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type


DOCUMENTATION = r"""
---
module: cluster_ha_vm_overrides
short_description: Manage vSphere High Availability (HA) VM override settings.
description:
    - Manages HA VM override settings on VMware vSphere clusters.
    - VM override settings override cluster-wide HA defaults for individual virtual machines.
    - You must enable HA before you can rely on these settings. See module M(vmware.vmware.cluster_ha).
    - VMs must exist in the cluster before you can set their override settings.
    - When a VM is removed from the cluster, its override settings are also automatically removed.
    - Although VM overrides are shown in a unified view in vCenter, this module only manages the HA override settings.
      Removing a VM override does not remove all overrides, just the HA related ones.

author:
    - Ansible Cloud Team (@ansible-collections)

seealso:
    - module: vmware.vmware.cluster_ha
    - module: vmware.vmware.cluster_ha_vm_overrides_info
    - module: vmware.vmware.cluster_drs_vm_overrides

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
            - If set to V(present) and O(append) is true, the VM override settings are added or updated if needed.
            - If set to V(present) and O(append) is false, the VM override settings in the cluster will be updated to match the desired configuration exactly.
              Any existing VM (HA) override settings that are not present in the desired configuration will be reset to the vCenter default values.
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
            - Each entry describes an override for one virtual machine.
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
            restart_priority_timeout:
                description:
                    - Maximum time in seconds lower-priority VMs wait for higher-priority VMs to become ready during failover.
                    - Use V(-1) to use the cluster default for this VM override.
                type: int
                required: false
            restart_priority:
                description:
                    - Set the default priority HA gives to a virtual machine if sufficient capacity is not available
                      to power on all failed virtual machines.
                    - Used only when VM monitoring mode (at the cluster or VM level) is V(vmAndAppMonitoring) or V(vmMonitoringOnly).
                type: str
                choices: [ 'lowest', 'low', 'medium', 'high', 'highest' ]
            host_isolation_response:
                description:
                    - Specify how VMs should be handled if an ESXi host determines it can no longer reach the rest of the cluster.
                    - If set to V(none), no action is taken.
                    - If set to V(powerOff), VMs are powered off via the hypervisor.
                    - If set to V(shutdown), VMs are shut down via the guest operating system.
                type: str
                choices: ['none', 'powerOff', 'shutdown']
            vm_monitoring:
                description:
                    - Configures VM health monitoring and automated responses when a VM is unhealthy.
                type: dict
                suboptions:
                    use_cluster_settings:
                        description:
                            - If true, use cluster-wide monitoring settings; other keys in this section are ignored.
                            - If this is not set but the vm_monitoring dictionary is defined, the module will default it to false
                              (meaning custom VM settings will be used).
                        type: bool
                    mode:
                        description:
                            - Sets the state of the virtual machine health monitoring service.
                            - If set to V(vmAndAppMonitoring), HA will respond to both VM and vApp heartbeat failures.
                            - If set to V(vmMonitoringDisabled), HA will only respond to vApp heartbeat failures.
                            - If set to V(vmMonitoringOnly), HA will only respond to VM heartbeat failures.
                        type: str
                        choices: ['vmAndAppMonitoring', 'vmMonitoringOnly', 'vmMonitoringDisabled']
                    failure_interval:
                        description:
                            - The number of seconds to wait after a VM heartbeat fails before declaring the VM as unhealthy.
                            - Valid only when O(vm_overrides[].vm_monitoring.mode) is V(vmAndAppMonitoring) or V(vmMonitoringOnly).
                        type: int
                    minimum_uptime:
                        description:
                            - The number of seconds to wait for the VM's heartbeat to stabilize after it was powered reset.
                            - Valid only when O(vm_overrides[].vm_monitoring.mode) is V(vmAndAppMonitoring) or V(vmMonitoringOnly).
                        type: int
                    maximum_resets:
                        description:
                            - The maximum number of automated resets allowed in response to a VM becoming unhealthy
                            - Valid only when O(vm_overrides[].vm_monitoring.mode) is V(vmAndAppMonitoring) or V(vmMonitoringOnly).
                        type: int
                    maximum_resets_window:
                        description:
                            - The number of seconds during which O(vm_overrides[].vm_monitoring.maximum_resets) resets
                              can occur before automated responses stop.
                            - Valid only when O(vm_overrides[].vm_monitoring.mode) is V(vmAndAppMonitoring) or V(vmMonitoringOnly).
                            - The value of -1 specifies no window.
                        type: int
            storage_apd_response:
                description:
                    - Configures what steps are taken when storage All Paths Down (APD) events occur.
                type: dict
                suboptions:
                    mode:
                        description:
                            - Set the response in the event of All Paths Down (APD) for storage.
                            - APD differs from PDL, in that APD is assumed to be a transient outage and PDL is permanent.
                            - V(disabled) means no action will be taken
                            - V(warning) means no action will be taken, but events will be generated for logging purposes.
                            - V(restartConservative) means VMs will be powered off if HA determines another host can support the VM.
                            - V(restartAggressive) means VMs will be powered off if HA determines the VM can be restarted on a different host,
                              or if HA cannot detect the resources on other hosts because of network connectivity loss.
                        type: str
                        choices: [ 'disabled', 'warning', 'restartConservative', 'restartAggressive' ]
                    delay:
                        description:
                            - Set the response recovery delay time in seconds if storage is in an APD failure state.
                            - This is only used if O(vm_overrides[].storage_apd_response.mode) is V(restartConservative) or V(restartAggressive).
                        type: int
                    restart_vms:
                        description:
                            - If true, VMs will be restarted when possible if storage is in an APD failure state.
                            - This is only used if O(vm_overrides[].storage_apd_response.mode) is V(restartConservative) or V(restartAggressive).
                        type: bool
            storage_pdl_response_mode:
                description:
                    - Set the response in the event of permanent Device Loss (PDL) for storage.
                    - APD differs from PDL, in that APD is assumed to be a transient outage and PDL is permanent.
                    - V(disabled) means no action will be taken
                    - V(warning) means no action will be taken, but events will be generated for logging purposes.
                    - V(restart) means all VMs will be powered off. If hosts still have access to the datastore,
                      affected VMs will be restarted on that host.
                type: str
                choices: ['disabled', 'warning', 'restart']


extends_documentation_fragment:
    - vmware.vmware.base_options
"""

EXAMPLES = r"""
- name: Enable HA
  vmware.vmware.cluster_ha:
    hostname: '{{ vcenter_hostname }}'
    username: '{{ vcenter_username }}'
    password: '{{ vcenter_password }}'
    datacenter_name: DC01
    cluster_name: Cluster01
    enable: true
  delegate_to: localhost

- name: Ensure a VM HA override is present
  vmware.vmware.cluster_ha_vm_overrides:
    datacenter: DC01
    cluster: Cluster01
    state: present
    append: true
    vm_overrides:
      - virtual_machine: "{{ lookup('vmware.vmware.moid_from_path', '/DC01/vm/MyVirtualMachine') }}"
        restart_priority: high
        host_isolation_response: shutdown
  register: _ha_override_present

- name: Ensure a VM HA override with monitoring and storage protection
  vmware.vmware.cluster_ha_vm_overrides:
    datacenter: DC01
    cluster: Cluster01
    state: present
    append: true
    vm_overrides:
      - virtual_machine: MyVirtualMachine
        restart_priority: low
        host_isolation_response: powerOff
        restart_priority_timeout: 120
        vm_monitoring:
          mode: vmAndAppMonitoring
          failure_interval: 30
          minimum_uptime: 120
          maximum_resets: 3
          maximum_resets_window: 180
          use_cluster_settings: false
        storage_apd_response:
          mode: restartConservative
          delay: 180
          restart_vms: true
        storage_pdl_response_mode: warning

- name: Ensure a VM HA override is absent
  vmware.vmware.cluster_ha_vm_overrides:
    datacenter: DC01
    cluster: Cluster01
    state: absent
    vm_overrides:
      - virtual_machine: MyVirtualMachine

- name: Clear all VM HA overrides
  vmware.vmware.cluster_ha_vm_overrides:
    datacenter: DC01
    cluster: Cluster01
    state: present
    append: false
    vm_overrides: []

- name: Ensure only these HA overrides are present
  vmware.vmware.cluster_ha_vm_overrides:
    datacenter: DC01
    cluster: Cluster01
    state: present
    append: false
    vm_overrides:
      - virtual_machine: MyVirtualMachine
        restart_priority: high
        host_isolation_response: powerOff
      - virtual_machine: MyOtherVirtualMachine
        restart_priority: low
        host_isolation_response: none
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
        - One entry per VM whose HA override was removed in this run (for example C(state=absent), replace mode with
          C(append=false), or clearing non-desired overrides).
        - Each entry only contains C(vm_moid) and C(vm_name); it does not echo prior HA field values.
    returned: success
    type: list
    sample:
        - vm_moid: vm-42
          vm_name: MyVirtualMachine
overrides_added:
    description:
        - One entry per VM whose HA override was added. Each entry only contains C(vm_moid) and C(vm_name).
    returned: success
    type: list
    sample:
        - vm_moid: vm-42
          vm_name: MyVirtualMachine
overrides_updated:
    description:
        - One entry per VM whose HA override was changed. Each entry only contains C(vm_moid) and C(vm_name).
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
    ClusterSettingsRemapper,
    BaseVmOverrideChangeTracker,
)
from ansible.module_utils.common.text.converters import to_native


def set_if_defined_and_not_none(spec, key, value):
    if value is not None:
        setattr(spec, key, value)


class HaVmOverrideChangeTracker(BaseVmOverrideChangeTracker):
    def __init__(self, current_vm_overrides, param_vm_overrides):
        super().__init__(current_vm_overrides, param_vm_overrides)

    def _overrides_differ(self, desired, current):
        if not getattr(desired, "dasSettings"):
            return False

        if not getattr(current, "dasSettings"):
            return True

        desired = desired.dasSettings
        current = current.dasSettings
        if (
            BaseVmOverrideChangeTracker._is_desired_set_and_different_from_current(
                desired, current, "restartPriority"
            )
            or BaseVmOverrideChangeTracker._is_desired_set_and_different_from_current(
                desired, current, "isolationResponse"
            )
            or BaseVmOverrideChangeTracker._is_desired_set_and_different_from_current(
                desired, current, "restartPriorityTimeout"
            )
        ):
            return True

        if self._vm_monitoring_differ(desired, current):
            return True

        if self._component_protection_settings_differ(desired, current):
            return True

        return False

    def _vm_monitoring_differ(self, desired, current):
        if not getattr(desired, "vmToolsMonitoringSettings"):
            return False

        if not getattr(current, "vmToolsMonitoringSettings"):
            return True

        desired = desired.vmToolsMonitoringSettings
        current = current.vmToolsMonitoringSettings
        if (
            BaseVmOverrideChangeTracker._is_desired_set_and_different_from_current(
                desired, current, "vmMonitoring"
            )
            or BaseVmOverrideChangeTracker._is_desired_set_and_different_from_current(
                desired, current, "failureInterval"
            )
            or BaseVmOverrideChangeTracker._is_desired_set_and_different_from_current(
                desired, current, "minUpTime"
            )
            or BaseVmOverrideChangeTracker._is_desired_set_and_different_from_current(
                desired, current, "maxFailures"
            )
            or BaseVmOverrideChangeTracker._is_desired_set_and_different_from_current(
                desired, current, "maxFailureWindow"
            )
        ):
            return True

        return False

    def _component_protection_settings_differ(self, desired, current):
        if not getattr(desired, "vmComponentProtectionSettings"):
            return False

        if not getattr(current, "vmComponentProtectionSettings"):
            return True

        desired = desired.vmComponentProtectionSettings
        current = current.vmComponentProtectionSettings
        if (
            BaseVmOverrideChangeTracker._is_desired_set_and_different_from_current(
                desired, current, "vmStorageProtectionForAPD"
            )
            or BaseVmOverrideChangeTracker._is_desired_set_and_different_from_current(
                desired, current, "vmTerminateDelayForAPDSec"
            )
            or BaseVmOverrideChangeTracker._is_desired_set_and_different_from_current(
                desired, current, "vmReactionOnAPDCleared"
            )
            or BaseVmOverrideChangeTracker._is_desired_set_and_different_from_current(
                desired, current, "vmStorageProtectionForPDL"
            )
        ):
            return True

        return False


class VMwareHaVmOverrides(ModulePyvmomiBase):
    def __init__(self, module):
        super().__init__(module)

        datacenter = self.get_datacenter_by_name_or_moid(
            self.params.get("datacenter"), fail_on_missing=True
        )
        self.cluster = self.get_cluster_by_name_or_moid(
            self.params.get("cluster"), fail_on_missing=True, datacenter=datacenter
        )
        try:
            das_config = self.cluster.configurationEx.dasConfig
        except AttributeError:
            self.module.fail_json(
                msg="HA configuration is not available on the cluster. Configure HA before using this module."
            )
        if not das_config.enabled:
            self.module.fail_json(
                msg="HA is not enabled on the cluster. Enable HA before using this module."
            )

    def _convert_param_overrides_to_das_setting_specs(self):
        override_specs = dict()
        for override_params in self.params.get("vm_overrides"):
            search_results = self.get_objs_by_name_or_moid(
                [vim.VirtualMachine],
                override_params.get("virtual_machine"),
                return_all=False,
            )
            if len(search_results) == 0:
                self.module.fail_json(
                    msg="Unable to find virtual machine with name or MOID %s"
                    % override_params.get("virtual_machine")
                )

            vm = search_results[0]
            override_specs[vm._GetMoId()] = vim.cluster.DasVmConfigInfo(
                key=vm, dasSettings=self._create_das_settings_spec(override_params)
            )
        return override_specs

    def _create_das_settings_spec(self, override_params):
        das_settings = vim.cluster.DasVmSettings()
        set_if_defined_and_not_none(
            das_settings, "restartPriority", override_params.get("restart_priority")
        )
        set_if_defined_and_not_none(
            das_settings,
            "isolationResponse",
            override_params.get("host_isolation_response"),
        )
        set_if_defined_and_not_none(
            das_settings,
            "restartPriorityTimeout",
            override_params.get("restart_priority_timeout"),
        )
        if override_params.get("vm_monitoring") is not None:
            das_settings.vmToolsMonitoringSettings = (
                self._create_vm_monitoring_settings_spec(
                    override_params["vm_monitoring"]
                )
            )
        if (
            override_params.get("storage_apd_response") is not None
            or override_params.get("storage_pdl_response_mode") is not None
        ):
            das_settings.vmComponentProtectionSettings = (
                self._create_vm_component_protection_settings_spec(override_params)
            )

        return das_settings

    def _create_vm_monitoring_settings_spec(self, monitoring_params):
        spec = vim.cluster.VmToolsMonitoringSettings()
        if monitoring_params.get("use_cluster_settings"):
            spec.clusterSettings = True
            return spec

        spec.clusterSettings = False
        set_if_defined_and_not_none(spec, "vmMonitoring", monitoring_params.get("mode"))
        set_if_defined_and_not_none(
            spec, "failureInterval", monitoring_params.get("failure_interval")
        )
        set_if_defined_and_not_none(
            spec, "minUpTime", monitoring_params.get("minimum_uptime")
        )
        set_if_defined_and_not_none(
            spec, "maxFailures", monitoring_params.get("maximum_resets")
        )
        set_if_defined_and_not_none(
            spec, "maxFailureWindow", monitoring_params.get("maximum_resets_window")
        )
        return spec

    def _create_vm_component_protection_settings_spec(self, override_params):
        spec = vim.cluster.VmComponentProtectionSettings()
        apd = override_params.get("storage_apd_response")
        if apd:
            set_if_defined_and_not_none(
                spec, "vmStorageProtectionForAPD", apd.get("mode")
            )
            set_if_defined_and_not_none(
                spec, "vmTerminateDelayForAPDSec", apd.get("delay")
            )

            set_if_defined_and_not_none(
                spec,
                "vmReactionOnAPDCleared",
                ClusterSettingsRemapper.storage_apd_restart_vms(apd.get("restart_vms")),
            )

        set_if_defined_and_not_none(
            spec,
            "vmStorageProtectionForPDL",
            ClusterSettingsRemapper.storage_pdl_response_mode(
                override_params.get("storage_pdl_response_mode"),
            ),
        )
        return spec

    def _lookup_current_vm_overrides(self):
        current_vm_overrides = dict()
        for vm_override in getattr(self.cluster.configurationEx, "dasVmConfig", list()):
            current_vm_overrides[vm_override.key._GetMoId()] = vm_override
        return current_vm_overrides

    def get_overrides_changes(self):
        change_tracker = HaVmOverrideChangeTracker(
            current_vm_overrides=self._lookup_current_vm_overrides(),
            param_vm_overrides=self._convert_param_overrides_to_das_setting_specs(),
        )
        if self.params.get("state") == "absent":
            change_tracker.process_absent_changes()
        elif self.params.get("state") == "present":
            change_tracker.process_present_changes(append=self.params.get("append"))

        return change_tracker

    def _create_ha_vm_config_spec(self, vm_override_specs, operation):
        cluster_config_spec = vim.cluster.ConfigSpecEx()
        cluster_config_spec.dasVmConfigSpec = []
        for vm_override_spec in vm_override_specs:
            if operation == "remove":
                spec_kwargs = dict(operation=operation, removeKey=vm_override_spec.key)
            else:
                spec_kwargs = dict(
                    operation=operation,
                    info=vm_override_spec,
                )
            cluster_config_spec.dasVmConfigSpec.append(
                vim.cluster.DasVmConfigSpec(**spec_kwargs)
            )

        return cluster_config_spec

    def apply_ha_vm_overrides(self, vm_overrides, operation):
        cluster_config_spec = self._create_ha_vm_config_spec(vm_overrides, operation)

        try:
            task = self.cluster.ReconfigureComputeResource_Task(
                cluster_config_spec, True
            )
            _, task_result = RunningTaskMonitor(   # pylint: disable=disallowed-name
                task
            ).wait_for_completion()
        except (vmodl.RuntimeFault, vmodl.MethodFault) as vmodl_fault:
            self.module.fail_json(msg=to_native(vmodl_fault.msg))
        except TaskError as task_e:
            self.module.fail_json(msg=to_native(task_e))
        except Exception as generic_exc:
            self.module.fail_json(
                msg="Failed to update cluster with %s operation due to exception %s"
                % (operation, to_native(generic_exc))
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
                        restart_priority=dict(
                            type="str",
                            required=False,
                            choices=["lowest", "low", "medium", "high", "highest"],
                        ),
                        host_isolation_response=dict(
                            type="str",
                            required=False,
                            choices=["none", "powerOff", "shutdown"],
                        ),
                        restart_priority_timeout=dict(type="int", required=False),
                        vm_monitoring=dict(
                            type="dict",
                            options=dict(
                                mode=dict(
                                    type="str",
                                    choices=[
                                        "vmAndAppMonitoring",
                                        "vmMonitoringOnly",
                                        "vmMonitoringDisabled",
                                    ],
                                ),
                                failure_interval=dict(type="int"),
                                minimum_uptime=dict(type="int"),
                                maximum_resets=dict(type="int"),
                                maximum_resets_window=dict(type="int"),
                                use_cluster_settings=dict(type="bool"),
                            ),
                        ),
                        storage_apd_response=dict(
                            type="dict",
                            options=dict(
                                mode=dict(
                                    type="str",
                                    choices=[
                                        "disabled",
                                        "warning",
                                        "restartConservative",
                                        "restartAggressive",
                                    ],
                                ),
                                delay=dict(type="int"),
                                restart_vms=dict(type="bool"),
                            ),
                        ),
                        storage_pdl_response_mode=dict(
                            type="str", choices=["disabled", "warning", "restart"]
                        ),
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

    cluster_ha = VMwareHaVmOverrides(module)
    result["cluster"]["name"] = cluster_ha.cluster.name
    result["cluster"]["moid"] = cluster_ha.cluster._GetMoId()

    change_tracker = cluster_ha.get_overrides_changes()
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
                cluster_ha.apply_ha_vm_overrides(
                    change_tracker.to_add.values(), operation="add"
                )
            if change_tracker.to_update:
                cluster_ha.apply_ha_vm_overrides(
                    change_tracker.to_update.values(), operation="edit"
                )
            if change_tracker.to_remove:
                cluster_ha.apply_ha_vm_overrides(
                    change_tracker.to_remove.values(), operation="remove"
                )
    module.exit_json(**result)


if __name__ == "__main__":
    main()

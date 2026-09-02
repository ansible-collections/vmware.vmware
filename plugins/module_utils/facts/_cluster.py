# -*- coding: utf-8 -*-

# Copyright: (c) 2023, Ansible Eco Content Team (github.com/eco-ansible-content)
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

# Note: This utility is considered private, and can only be referenced from inside the vmware.vmware collection.
#       It may be made public at a later date

from __future__ import absolute_import, division, print_function
__metaclass__ = type

try:
    from pyVmomi import vmodl
except ImportError:
    pass

from .._folder_paths import get_folder_path_of_vsphere_object
from ._converters import vmware_obj_to_json


class ClusterFacts():
    DPM_DEFAULT_RATE = 3
    DRS_DEFAULT_RATE = 3

    def __init__(self, cluster):
        self.cluster = cluster

    @staticmethod
    def reverse_drs_or_dpm_rate(input_rate):
        return 6 - int(input_rate)

    def all_facts(self):
        return {
            **self.host_facts(),
            **self.ha_facts(),
            **self.identifier_facts(),
            **self.drs_facts(),
            **self.vsan_facts(),
            **self.resource_usage_facts(),
            **self.dpm_facts()
        }

    def identifier_facts(self):
        return {
            "moid": self.cluster._moId,
            "datacenter": self.cluster.parent.parent.name
        }

    def host_facts(self):
        hosts = []
        for host in self.cluster.host:
            hosts.append({
                'name': host.name,
                'folder': get_folder_path_of_vsphere_object(host),
            })
        return {"hosts": hosts}

    def ha_facts(self):
        fact_keys = [
            "ha_enabled", "ha_failover_level", "ha_vm_monitoring", "ha_admission_control_enabled",
            "ha_restart_priority", "ha_vm_tools_monitoring", "ha_vm_min_up_time", "ha_vm_max_failures",
            "ha_vm_max_failure_window", "ha_vm_failure_interval"
        ]
        ha_facts = dict.fromkeys(fact_keys, None)
        das_config = self.cluster.configurationEx.dasConfig
        if not das_config:
            ha_facts['ha_enabled'] = False
            return ha_facts

        ha_facts["ha_enabled"] = das_config.enabled
        ha_facts["ha_vm_monitoring"] = das_config.vmMonitoring
        ha_facts["ha_host_monitoring"] = das_config.hostMonitoring
        ha_facts["ha_admission_control_enabled"] = das_config.admissionControlEnabled

        if getattr(das_config, "admissionControlPolicy"):
            ha_facts['ha_failover_level'] = das_config.admissionControlPolicy.failoverLevel
        if getattr(das_config, "defaultVmSettings"):
            ha_facts['ha_restart_priority'] = das_config.defaultVmSettings.restartPriority
            ha_facts['ha_vm_tools_monitoring'] = das_config.defaultVmSettings.vmToolsMonitoringSettings.vmMonitoring
            ha_facts['ha_vm_min_up_time'] = das_config.defaultVmSettings.vmToolsMonitoringSettings.minUpTime
            ha_facts['ha_vm_max_failures'] = das_config.defaultVmSettings.vmToolsMonitoringSettings.maxFailures
            ha_facts['ha_vm_max_failure_window'] = das_config.defaultVmSettings.vmToolsMonitoringSettings.maxFailureWindow
            ha_facts['ha_vm_failure_interval'] = das_config.defaultVmSettings.vmToolsMonitoringSettings.failureInterval

        return ha_facts

    def dpm_facts(self):
        fact_keys = ["dpm_enabled", "dpm_default_dpm_behavior", "dpm_host_power_action_rate"]
        output_facts = dict.fromkeys(fact_keys, None)
        dpm_config = self.cluster.configurationEx.dpmConfigInfo
        if not dpm_config:
            output_facts["dpm_enabled"] = False
            return output_facts

        output_facts["dpm_enabled"] = dpm_config.enabled
        output_facts["dpm_default_dpm_behavior"] = getattr(dpm_config, "defaultDpmBehavior", None)
        # dpm host power rate is reversed by the vsphere API. so a 1 in the API is really a 5 in the UI
        try:
            output_facts["dpm_host_power_action_rate"] = ClusterFacts.reverse_drs_or_dpm_rate(dpm_config.hostPowerActionRate)
        except (TypeError, AttributeError):
            output_facts["dpm_host_power_action_rate"] = ClusterFacts.DPM_DEFAULT_RATE

        return output_facts

    def drs_facts(self):
        fact_keys = ["drs_enabled", "drs_enable_vm_behavior_overrides", "drs_default_vm_behavior", "drs_vmotion_rate"]
        output_facts = dict.fromkeys(fact_keys, None)
        drs_config = self.cluster.configurationEx.drsConfig
        if not drs_config:
            output_facts["drs_enabled"] = False
            return output_facts

        output_facts["drs_enabled"] = drs_config.enabled
        output_facts["drs_enable_vm_behavior_overrides"] = getattr(drs_config, "enableVmBehaviorOverrides", None)

        # docs call one option 'automatic' but the API calls it 'automated'. So we adjust here to match docs
        _drs_default_vm_behavior = getattr(drs_config, "defaultVmBehavior", None)
        output_facts["drs_default_vm_behavior"] = 'automatic' if _drs_default_vm_behavior == 'automated' else _drs_default_vm_behavior

        # drs vmotion rate is reversed by the vsphere API. so a 1 in the API is really a 5 in the UI
        try:
            output_facts["drs_vmotion_rate"] = ClusterFacts.reverse_drs_or_dpm_rate(drs_config.vmotionRate)
        except (TypeError, AttributeError):
            output_facts["drs_vmotion_rate"] = ClusterFacts.DRS_DEFAULT_RATE

        return output_facts

    def vsan_facts(self):
        vsan_config = getattr(self.cluster.configurationEx, 'vsanConfigInfo', None)
        vsan_facts = {
            "vsan_enabled": False,
            "vsan_auto_claim_storage": None
        }
        if vsan_config:
            vsan_facts['vsan_enabled'] = vsan_config.enabled
            vsan_facts['vsan_auto_claim_storage'] = vsan_config.defaultConfig.autoClaimStorage
        return vsan_facts

    def resource_usage_facts(self):
        try:
            resource_summary = vmware_obj_to_json(self.cluster.GetResourceUsage())
        except vmodl.fault.MethodNotFound:
            return {'resource_summary': {}}

        if '_vimtype' in resource_summary:
            del resource_summary['_vimtype']
        return {'resource_summary': resource_summary}

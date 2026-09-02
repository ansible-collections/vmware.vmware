from __future__ import absolute_import, division, print_function
__metaclass__ = type

import types
from unittest import mock

from pyVmomi import vmodl

from ansible_collections.vmware.vmware.plugins.module_utils.facts._cluster import (
    ClusterFacts,
)


CLUSTER = 'ansible_collections.vmware.vmware.plugins.module_utils.facts._cluster'


def ns(**kwargs):
    """Small helper to build attribute containers that raise AttributeError for missing attrs."""
    return types.SimpleNamespace(**kwargs)


class TestReverseDrsOrDpmRate:
    def test_reverse(self):
        # The vSphere API reverses the rate, so a UI value of 5 is a 1 in the API and vice versa.
        assert ClusterFacts.reverse_drs_or_dpm_rate(1) == 5
        assert ClusterFacts.reverse_drs_or_dpm_rate(5) == 1
        assert ClusterFacts.reverse_drs_or_dpm_rate("3") == 3


class TestClusterFactsIdentifier:
    def test_identifier_facts(self):
        # cluster.parent is the host folder, cluster.parent.parent is the datacenter.
        cluster = ns(_moId="domain-c1", parent=ns(parent=ns(name="my_dc")))
        assert ClusterFacts(cluster).identifier_facts() == {
            "moid": "domain-c1",
            "datacenter": "my_dc",
        }


class TestClusterFactsHost:
    def test_host_facts(self, mocker):
        mocker.patch(
            CLUSTER + '.get_folder_path_of_vsphere_object',
            side_effect=lambda host: "/dc/host/%s" % host.name,
        )
        cluster = ns(host=[ns(name="esxi01"), ns(name="esxi02")])
        assert ClusterFacts(cluster).host_facts() == {
            "hosts": [
                {"name": "esxi01", "folder": "/dc/host/esxi01"},
                {"name": "esxi02", "folder": "/dc/host/esxi02"},
            ]
        }

    def test_host_facts_empty(self):
        cluster = ns(host=[])
        assert ClusterFacts(cluster).host_facts() == {"hosts": []}


class TestClusterFactsHa:
    def test_ha_disabled_when_no_das_config(self):
        cluster = ns(configurationEx=ns(dasConfig=None))
        facts = ClusterFacts(cluster).ha_facts()
        assert facts["ha_enabled"] is False
        assert facts["ha_failover_level"] is None

    def test_ha_full(self):
        vm_tools = ns(
            vmMonitoring="vmMonitoringOnly",
            minUpTime=120,
            maxFailures=3,
            maxFailureWindow=-1,
            failureInterval=30,
        )
        das_config = ns(
            enabled=True,
            vmMonitoring="vmMonitoringOnly",
            hostMonitoring="enabled",
            admissionControlEnabled=True,
            admissionControlPolicy=ns(failoverLevel=1),
            defaultVmSettings=ns(
                restartPriority="medium",
                vmToolsMonitoringSettings=vm_tools,
            ),
        )
        cluster = ns(configurationEx=ns(dasConfig=das_config))
        facts = ClusterFacts(cluster).ha_facts()
        assert facts["ha_enabled"] is True
        assert facts["ha_vm_monitoring"] == "vmMonitoringOnly"
        assert facts["ha_host_monitoring"] == "enabled"
        assert facts["ha_admission_control_enabled"] is True
        assert facts["ha_failover_level"] == 1
        assert facts["ha_restart_priority"] == "medium"
        assert facts["ha_vm_min_up_time"] == 120
        assert facts["ha_vm_max_failures"] == 3
        assert facts["ha_vm_failure_interval"] == 30

    def test_ha_without_optional_policies(self):
        das_config = ns(
            enabled=True,
            vmMonitoring="disabled",
            hostMonitoring="disabled",
            admissionControlEnabled=False,
            admissionControlPolicy=None,
            defaultVmSettings=None,
        )
        cluster = ns(configurationEx=ns(dasConfig=das_config))
        facts = ClusterFacts(cluster).ha_facts()
        assert facts["ha_enabled"] is True
        assert facts["ha_failover_level"] is None
        assert facts["ha_restart_priority"] is None


class TestClusterFactsDpm:
    def test_dpm_disabled_when_no_config(self):
        cluster = ns(configurationEx=ns(dpmConfigInfo=None))
        assert ClusterFacts(cluster).dpm_facts() == {
            "dpm_enabled": False,
            "dpm_default_dpm_behavior": None,
            "dpm_host_power_action_rate": None,
        }

    def test_dpm_full_reverses_rate(self):
        dpm_config = ns(enabled=True, defaultDpmBehavior="automated", hostPowerActionRate=1)
        cluster = ns(configurationEx=ns(dpmConfigInfo=dpm_config))
        assert ClusterFacts(cluster).dpm_facts() == {
            "dpm_enabled": True,
            "dpm_default_dpm_behavior": "automated",
            "dpm_host_power_action_rate": 5,
        }

    def test_dpm_defaults_rate_on_missing_value(self):
        # hostPowerActionRate is absent -> reverse raises AttributeError -> default rate.
        dpm_config = ns(enabled=True, defaultDpmBehavior="manual")
        cluster = ns(configurationEx=ns(dpmConfigInfo=dpm_config))
        facts = ClusterFacts(cluster).dpm_facts()
        assert facts["dpm_host_power_action_rate"] == ClusterFacts.DPM_DEFAULT_RATE


class TestClusterFactsDrs:
    def test_drs_disabled_when_no_config(self):
        cluster = ns(configurationEx=ns(drsConfig=None))
        assert ClusterFacts(cluster).drs_facts() == {
            "drs_enabled": False,
            "drs_enable_vm_behavior_overrides": None,
            "drs_default_vm_behavior": None,
            "drs_vmotion_rate": None,
        }

    def test_drs_full_maps_automated_to_automatic(self):
        drs_config = ns(
            enabled=True,
            enableVmBehaviorOverrides=True,
            defaultVmBehavior="automated",
            vmotionRate=2,
        )
        cluster = ns(configurationEx=ns(drsConfig=drs_config))
        assert ClusterFacts(cluster).drs_facts() == {
            "drs_enabled": True,
            "drs_enable_vm_behavior_overrides": True,
            "drs_default_vm_behavior": "automatic",
            "drs_vmotion_rate": 4,
        }

    def test_drs_defaults_rate_on_missing_value(self):
        drs_config = ns(enabled=True, enableVmBehaviorOverrides=False, defaultVmBehavior="manual")
        cluster = ns(configurationEx=ns(drsConfig=drs_config))
        facts = ClusterFacts(cluster).drs_facts()
        assert facts["drs_default_vm_behavior"] == "manual"
        assert facts["drs_vmotion_rate"] == ClusterFacts.DRS_DEFAULT_RATE


class TestClusterFactsVsan:
    def test_vsan_disabled_when_no_config(self):
        cluster = ns(configurationEx=ns(vsanConfigInfo=None))
        assert ClusterFacts(cluster).vsan_facts() == {
            "vsan_enabled": False,
            "vsan_auto_claim_storage": None,
        }

    def test_vsan_missing_attribute(self):
        cluster = ns(configurationEx=ns())
        assert ClusterFacts(cluster).vsan_facts() == {
            "vsan_enabled": False,
            "vsan_auto_claim_storage": None,
        }

    def test_vsan_enabled(self):
        vsan_config = ns(enabled=True, defaultConfig=ns(autoClaimStorage=True))
        cluster = ns(configurationEx=ns(vsanConfigInfo=vsan_config))
        assert ClusterFacts(cluster).vsan_facts() == {
            "vsan_enabled": True,
            "vsan_auto_claim_storage": True,
        }


class TestClusterFactsResourceUsage:
    def test_resource_usage_strips_vimtype(self, mocker):
        mocker.patch(
            CLUSTER + '.vmware_obj_to_json',
            return_value={'_vimtype': 'vim.cluster.ResourceUsageSummary', 'cpuCapacityMHz': 100},
        )
        cluster = mock.Mock()
        assert ClusterFacts(cluster).resource_usage_facts() == {
            "resource_summary": {"cpuCapacityMHz": 100}
        }

    def test_resource_usage_method_not_found(self):
        cluster = mock.Mock()
        cluster.GetResourceUsage.side_effect = vmodl.fault.MethodNotFound()
        assert ClusterFacts(cluster).resource_usage_facts() == {"resource_summary": {}}

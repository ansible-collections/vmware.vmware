from __future__ import absolute_import, division, print_function
__metaclass__ = type

import types
from unittest import mock

from pyVmomi import vim, vmodl

from ansible_collections.vmware.vmware.plugins.module_utils.facts._esxi import (
    EsxiFacts,
)


def ns(**kwargs):
    """Small helper to build attribute containers that raise AttributeError for missing attrs."""
    return types.SimpleNamespace(**kwargs)


def build_full_host():
    """Builds a host with every property populated so all_facts() exercises the happy path."""
    cluster = mock.Mock(spec=vim.ClusterComputeResource)
    cluster.name = "my_cluster"
    datacenter = mock.Mock(spec=vim.Datacenter)
    datacenter.name = "my_datacenter"
    datacenter.parent = None
    # A non-cluster, non-datacenter folder sits between the cluster and the datacenter.
    folder = ns(name="host_folder", parent=datacenter)
    cluster.parent = folder

    vnic = ns(
        device="vmk0",
        spec=ns(
            ip=ns(ipAddress="10.10.10.10", subnetMask="255.255.255.0"),
            mac="52:54:00:56:7d:59",
            mtu=1500,
        ),
    )

    vsan_system = mock.Mock()
    vsan_system.QueryHostStatus.return_value = ns(
        uuid="cluster-uuid", nodeUuid="node-uuid", health="healthy"
    )

    return types.SimpleNamespace(
        _moId="host-111",
        summary=ns(
            config=ns(name="esxi01"),
            hardware=ns(
                cpuModel="Intel Xeon",
                numCpuCores=8,
                numCpuPkgs=2,
                numCpuThreads=16,
            ),
            quickStats=ns(overallMemoryUsage=1024, uptime=1791680),
        ),
        hardware=ns(
            memorySize=8 * 1024 * 1024 * 1024,
            biosInfo=ns(biosVersion="1.0", releaseDate="2020-01-01T00:00:00+00:00"),
            systemInfo=ns(
                vendor="Dell",
                model="PowerEdge",
                uuid="system-uuid",
                otherIdentifyingInfo=[
                    ns(identifierType=ns(key="OtherInfo"), identifierValue="x"),
                    ns(identifierType=ns(key="ServiceTag"), identifierValue="ABC123"),
                ],
            ),
        ),
        config=ns(
            product=ns(
                name="VMware ESXi",
                version="7.0.0",
                build="12345",
                osType="vmnix-x86",
            ),
            network=ns(vnic=[vnic]),
        ),
        runtime=ns(
            connectionState="connected",
            powerState="poweredOn",
            inMaintenanceMode=False,
        ),
        datastore=[ns(summary=ns(name="datastore1", capacity=100, freeSpace=50))],
        configManager=ns(vsanSystem=vsan_system),
        parent=cluster,
    )


class TestEsxiFactsAllFacts:
    def test_all_facts_full_host(self):
        facts = EsxiFacts(build_full_host()).all_facts()

        assert facts["name"] == "esxi01"
        assert facts["moid"] == "host-111"
        assert facts["cpu_cores"] == 8
        assert facts["memory_total_mb"] == 8192
        assert facts["memory_free_mb"] == 8192 - 1024
        assert facts["product_name"] == "VMware ESXi"
        assert facts["service_tag"] == "ABC123"
        assert facts["connection_state"] == "connected"
        assert facts["all_ipv4_addresses"] == ["10.10.10.10"]
        assert facts["datastores"] == [
            {"name": "datastore1", "capacity": 100, "free_space": 50}
        ]
        assert facts["vsan_health"] == "healthy"
        assert facts["cluster"] == "my_cluster"
        assert facts["datacenter"] == "my_datacenter"


class TestEsxiFactsIdentifier:
    def test_identifier_facts(self):
        host = ns(_moId="host-1", summary=ns(config=ns(name="esxi01")))
        assert EsxiFacts(host).identifier_facts() == {
            "name": "esxi01",
            "moid": "host-1",
        }

    def test_identifier_facts_missing_name(self):
        host = ns(_moId="host-1", summary=ns())
        assert EsxiFacts(host).identifier_facts() == {
            "name": None,
            "moid": "host-1",
        }


class TestEsxiFactsCpu:
    def test_cpu_facts_present(self):
        host = ns(summary=ns(hardware=ns(
            cpuModel="Xeon", numCpuCores=4, numCpuPkgs=1, numCpuThreads=8
        )))
        assert EsxiFacts(host).cpu_facts() == {
            "cpu_model": "Xeon",
            "cpu_cores": 4,
            "cpu_pkgs": 1,
            "cpu_threads": 8,
        }

    def test_cpu_facts_absent(self):
        host = ns(summary=ns())
        assert EsxiFacts(host).cpu_facts() == {
            "cpu_model": None,
            "cpu_cores": None,
            "cpu_pkgs": None,
            "cpu_threads": None,
        }


class TestEsxiFactsMemory:
    def test_memory_facts_present(self):
        host = ns(
            hardware=ns(memorySize=4 * 1024 * 1024 * 1024),
            summary=ns(quickStats=ns(overallMemoryUsage=1000)),
        )
        assert EsxiFacts(host).memory_facts() == {
            "memory_total_mb": 4096,
            "memory_free_mb": 4096 - 1000,
        }

    def test_memory_facts_no_quickstats_usage(self):
        host = ns(
            hardware=ns(memorySize=4 * 1024 * 1024 * 1024),
            summary=ns(quickStats=ns()),
        )
        assert EsxiFacts(host).memory_facts() == {
            "memory_total_mb": 4096,
            "memory_free_mb": 4096,
        }

    def test_memory_facts_absent(self):
        host = ns(hardware=ns())
        assert EsxiFacts(host).memory_facts() == {
            "memory_total_mb": None,
            "memory_free_mb": None,
        }


class TestEsxiFactsProduct:
    def test_product_facts_present(self):
        host = ns(
            config=ns(product=ns(
                name="VMware ESXi", version="7.0.0", build="12345", osType="vmnix-x86"
            )),
            hardware=ns(
                biosInfo=ns(biosVersion="1.0", releaseDate="2020-01-01"),
                systemInfo=ns(
                    vendor="Dell", model="PowerEdge", uuid="system-uuid",
                    otherIdentifyingInfo=[
                        ns(identifierType=ns(key="ServiceTag"), identifierValue="TAG1"),
                    ],
                ),
            ),
        )
        facts = EsxiFacts(host).product_facts()
        assert facts["product_name"] == "VMware ESXi"
        assert facts["product_version"] == "7.0.0"
        assert facts["product_build"] == "12345"
        assert facts["os_type"] == "vmnix-x86"
        assert facts["bios_version"] == "1.0"
        assert facts["bios_release_date"] == "2020-01-01"
        assert facts["system_vendor"] == "Dell"
        assert facts["service_tag"] == "TAG1"

    def test_product_facts_absent(self):
        host = ns(config=ns(), hardware=ns())
        facts = EsxiFacts(host).product_facts()
        assert facts["product_name"] is None
        assert facts["bios_version"] is None
        assert facts["system_vendor"] is None
        assert facts["service_tag"] is None


class TestEsxiFactsSystemInfo:
    def test_systeminfo_no_service_tag(self):
        host = ns(hardware=ns(systemInfo=ns(
            vendor="Dell", model="PowerEdge", uuid="uuid",
            otherIdentifyingInfo=[
                ns(identifierType=ns(key="OtherInfo"), identifierValue="x"),
            ],
        )))
        facts = EsxiFacts(host)._get_systeminfo_property_facts()
        assert facts["system_model"] == "PowerEdge"
        assert facts["service_tag"] is None

    def test_systeminfo_empty_other_identifying_info(self):
        host = ns(hardware=ns(systemInfo=ns(
            vendor="Dell", model="PowerEdge", uuid="uuid", otherIdentifyingInfo=[],
        )))
        facts = EsxiFacts(host)._get_systeminfo_property_facts()
        assert facts["service_tag"] is None
        assert facts["system_uuid"] == "uuid"

    def test_systeminfo_absent(self):
        host = ns(hardware=ns())
        facts = EsxiFacts(host)._get_systeminfo_property_facts()
        assert facts == {
            "system_vendor": None,
            "system_model": None,
            "system_uuid": None,
            "service_tag": None,
        }


class TestEsxiFactsRuntime:
    def test_runtime_facts_present(self):
        host = ns(
            runtime=ns(
                connectionState="connected",
                powerState="poweredOn",
                inMaintenanceMode=True,
            ),
            summary=ns(quickStats=ns(uptime=1000)),
        )
        assert EsxiFacts(host).runtime_facts() == {
            "connection_state": "connected",
            "power_state": "poweredOn",
            "in_maintenance_mode": True,
            "uptime": 1000,
        }

    def test_runtime_facts_absent(self):
        host = ns(summary=ns())
        assert EsxiFacts(host).runtime_facts() == {
            "connection_state": None,
            "power_state": None,
            "in_maintenance_mode": None,
            "uptime": None,
        }


class TestEsxiFactsNetwork:
    def test_network_facts_with_ip(self):
        vnic = ns(
            device="vmk0",
            spec=ns(
                ip=ns(ipAddress="10.0.0.1", subnetMask="255.255.255.0"),
                mac="aa:bb:cc:dd:ee:ff",
                mtu=1500,
            ),
        )
        host = ns(config=ns(network=ns(vnic=[vnic])))
        facts = EsxiFacts(host).network_facts()
        assert facts["all_ipv4_addresses"] == ["10.0.0.1"]
        assert facts["interfaces"] == [{
            "device": "vmk0",
            "ipv4": {"address": "10.0.0.1", "netmask": "255.255.255.0"},
            "macaddress": "aa:bb:cc:dd:ee:ff",
            "mtu": 1500,
        }]

    def test_network_facts_no_ip(self):
        vnic = ns(
            device="vmk1",
            spec=ns(ip=None, mac="aa:bb:cc:dd:ee:ff", mtu=1500),
        )
        host = ns(config=ns(network=ns(vnic=[vnic])))
        facts = EsxiFacts(host).network_facts()
        assert facts["all_ipv4_addresses"] == []
        assert facts["interfaces"][0]["ipv4"] == {"address": None, "netmask": None}

    def test_network_facts_empty(self):
        host = ns(config=ns())
        assert EsxiFacts(host).network_facts() == {
            "interfaces": [],
            "all_ipv4_addresses": [],
        }


class TestEsxiFactsDatastore:
    def test_datastore_facts(self):
        host = ns(datastore=[
            ns(summary=ns(name="ds1", capacity=100, freeSpace=40)),
            ns(summary=ns(name="ds2", capacity=200, freeSpace=80)),
        ])
        assert EsxiFacts(host).datastore_facts() == {"datastores": [
            {"name": "ds1", "capacity": 100, "free_space": 40},
            {"name": "ds2", "capacity": 200, "free_space": 80},
        ]}

    def test_datastore_facts_empty(self):
        host = ns()
        assert EsxiFacts(host).datastore_facts() == {"datastores": []}


class TestEsxiFactsVsan:
    def test_vsan_facts_no_system(self):
        host = ns(configManager=ns())
        assert EsxiFacts(host).vsan_facts() == {
            "vsan_cluster_uuid": None,
            "vsan_node_uuid": None,
            "vsan_health": "unknown",
        }

    def test_vsan_facts_success(self):
        vsan_system = mock.Mock()
        vsan_system.QueryHostStatus.return_value = ns(
            uuid="cluster-uuid", nodeUuid="node-uuid", health="healthy"
        )
        host = ns(configManager=ns(vsanSystem=vsan_system))
        assert EsxiFacts(host).vsan_facts() == {
            "vsan_cluster_uuid": "cluster-uuid",
            "vsan_node_uuid": "node-uuid",
            "vsan_health": "healthy",
        }

    def test_vsan_facts_host_not_connected(self):
        vsan_system = mock.Mock()
        vsan_system.QueryHostStatus.side_effect = vmodl.fault.HostNotConnected()
        host = ns(configManager=ns(vsanSystem=vsan_system))
        assert EsxiFacts(host).vsan_facts() == {
            "vsan_cluster_uuid": "NA",
            "vsan_node_uuid": "NA",
            "vsan_health": "NA",
        }

    def test_vsan_facts_host_communication(self):
        # A powered-off or otherwise unreachable host raises HostCommunication, the
        # base class of HostNotConnected/HostNotReachable.
        vsan_system = mock.Mock()
        vsan_system.QueryHostStatus.side_effect = vmodl.fault.HostCommunication()
        host = ns(configManager=ns(vsanSystem=vsan_system))
        assert EsxiFacts(host).vsan_facts() == {
            "vsan_cluster_uuid": "NA",
            "vsan_node_uuid": "NA",
            "vsan_health": "NA",
        }


class TestEsxiFactsCluster:
    def test_cluster_facts_full(self):
        datacenter = mock.Mock(spec=vim.Datacenter)
        datacenter.name = "my_dc"
        datacenter.parent = None
        folder = ns(name="folder", parent=datacenter)
        cluster = mock.Mock(spec=vim.ClusterComputeResource)
        cluster.name = "my_cluster"
        cluster.parent = folder
        host = ns(parent=cluster)

        assert EsxiFacts(host).cluster_facts() == {
            "cluster": "my_cluster",
            "datacenter": "my_dc",
        }

    def test_cluster_facts_standalone_host(self):
        # Parent is not a cluster (standalone host), but a datacenter is still found by walking up.
        datacenter = mock.Mock(spec=vim.Datacenter)
        datacenter.name = "my_dc"
        datacenter.parent = None
        folder = ns(name="folder", parent=datacenter)
        host = ns(parent=folder)

        assert EsxiFacts(host).cluster_facts() == {
            "cluster": None,
            "datacenter": "my_dc",
        }

    def test_cluster_facts_no_parent(self):
        host = ns()
        assert EsxiFacts(host).cluster_facts() == {
            "cluster": None,
            "datacenter": None,
        }

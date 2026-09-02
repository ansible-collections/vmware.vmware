# -*- coding: utf-8 -*-

# Copyright: (c) 2026, Ansible Eco Content Team (github.com/eco-ansible-content)
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

# Note: This utility is considered private, and can only be referenced from inside the vmware.vmware collection.
#       It may be made public at a later date

from __future__ import absolute_import, division, print_function

__metaclass__ = type

try:
    from pyVmomi import vim, vmodl
except ImportError:
    pass

from ._vm import get_vm_prop_or_none


class EsxiFacts:
    """
    Builds the 'summary' output schema for an ESXi host. Each *_facts() method returns a small
    dict, and all_facts() merges them together. This mirrors the VmFacts/ClusterFacts pattern in
    _facts.py.
    """

    def __init__(self, host):
        self.host = host

    def all_facts(self):
        return {
            **self.identifier_facts(),
            **self.cpu_facts(),
            **self.memory_facts(),
            **self.product_facts(),
            **self.runtime_facts(),
            **self.network_facts(),
            **self.datastore_facts(),
            **self.vsan_facts(),
            **self.cluster_facts(),
        }

    def identifier_facts(self):
        return {
            "name": get_vm_prop_or_none(self.host, ("summary", "config", "name")),
            "moid": self.host._moId,
        }

    def cpu_facts(self):
        hardware = get_vm_prop_or_none(self.host, ("summary", "hardware"))
        if not hardware:
            return {
                "cpu_model": None,
                "cpu_cores": None,
                "cpu_pkgs": None,
                "cpu_threads": None,
            }
        return {
            "cpu_model": hardware.cpuModel,
            "cpu_cores": hardware.numCpuCores,
            "cpu_pkgs": hardware.numCpuPkgs,
            "cpu_threads": hardware.numCpuThreads,
        }

    def memory_facts(self):
        memory_size = get_vm_prop_or_none(self.host, ("hardware", "memorySize"))
        if not memory_size:
            return {"memory_total_mb": None, "memory_free_mb": None}

        memory_total_mb = memory_size // 1024 // 1024
        overall_memory = (
            get_vm_prop_or_none(
                self.host, ("summary", "quickStats", "overallMemoryUsage")
            )
            or 0
        )
        return {
            "memory_total_mb": memory_total_mb,
            "memory_free_mb": memory_total_mb - overall_memory,
        }

    def product_facts(self):
        product = get_vm_prop_or_none(self.host, ("config", "product"))
        bios_info = get_vm_prop_or_none(self.host, ("hardware", "biosInfo"))

        return {
            **self._get_systeminfo_property_facts(),
            **{
                "product_name": product.name if product else None,
                "product_version": product.version if product else None,
                "product_build": product.build if product else None,
                "os_type": product.osType if product else None,
                "bios_version": bios_info.biosVersion if bios_info else None,
                "bios_release_date": bios_info.releaseDate if bios_info else None,
            },
        }

    def _get_systeminfo_property_facts(self):
        system_info = get_vm_prop_or_none(self.host, ("hardware", "systemInfo"))

        service_tag = None
        if system_info and system_info.otherIdentifyingInfo:
            for info in system_info.otherIdentifyingInfo:
                if info.identifierType.key == "ServiceTag":
                    service_tag = info.identifierValue
                    break

        return {
            "system_vendor": system_info.vendor if system_info else None,
            "system_model": system_info.model if system_info else None,
            "system_uuid": system_info.uuid if system_info else None,
            "service_tag": service_tag,
        }

    def runtime_facts(self):
        runtime = get_vm_prop_or_none(self.host, ("runtime",))
        return {
            "connection_state": runtime.connectionState if runtime else None,
            "power_state": runtime.powerState if runtime else None,
            "in_maintenance_mode": runtime.inMaintenanceMode if runtime else None,
            "uptime": get_vm_prop_or_none(
                self.host, ("summary", "quickStats", "uptime")
            ),
        }

    def network_facts(self):
        interfaces = []
        all_ipv4_addresses = []

        vnics = get_vm_prop_or_none(self.host, ("config", "network", "vnic")) or []
        for nic in vnics:
            address = nic.spec.ip.ipAddress if (nic.spec and nic.spec.ip) else None
            if address:
                all_ipv4_addresses.append(address)
            interfaces.append(
                {
                    "device": nic.device,
                    "ipv4": {
                        "address": address,
                        "netmask": (
                            nic.spec.ip.subnetMask
                            if (nic.spec and nic.spec.ip)
                            else None
                        ),
                    },
                    "macaddress": nic.spec.mac if nic.spec else None,
                    "mtu": nic.spec.mtu if nic.spec else None,
                }
            )

        return {
            "interfaces": interfaces,
            "all_ipv4_addresses": all_ipv4_addresses,
        }

    def datastore_facts(self):
        datastores = []
        for store in get_vm_prop_or_none(self.host, ("datastore",)) or []:
            summary = store.summary
            datastores.append(
                {
                    "name": summary.name,
                    "capacity": summary.capacity,
                    "free_space": summary.freeSpace,
                }
            )
        return {"datastores": datastores}

    def vsan_facts(self):
        output = {
            "vsan_cluster_uuid": None,
            "vsan_node_uuid": None,
            "vsan_health": "unknown",
        }
        vsan_system = get_vm_prop_or_none(self.host, ("configManager", "vsanSystem"))
        if vsan_system is None:
            return output

        try:
            status = vsan_system.QueryHostStatus()
        except vmodl.fault.HostCommunication:
            # HostCommunication is the base class of HostNotConnected and
            # HostNotReachable, and is raised when the host is powered off or otherwise
            # unreachable. In all of these cases vSAN status cannot be queried.
            return {
                "vsan_cluster_uuid": "NA",
                "vsan_node_uuid": "NA",
                "vsan_health": "NA",
            }

        return {
            "vsan_cluster_uuid": status.uuid,
            "vsan_node_uuid": status.nodeUuid,
            "vsan_health": status.health,
        }

    def cluster_facts(self):
        output = {"cluster": None, "datacenter": None}

        parent = get_vm_prop_or_none(self.host, ("parent",))
        if parent and isinstance(parent, vim.ClusterComputeResource):
            output["cluster"] = parent.name

        while parent:
            if isinstance(parent, vim.Datacenter):
                output["datacenter"] = parent.name
                break
            parent = getattr(parent, "parent", None)

        return output

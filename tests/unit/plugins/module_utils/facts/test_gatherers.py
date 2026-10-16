from __future__ import absolute_import, division, print_function
__metaclass__ = type

import pytest

from pyVmomi import vim

from ansible_collections.vmware.vmware.plugins.module_utils.facts._gatherers import (
    _ObjectsGatherer,
    ComputeObjectsGatherer,
    LocationObjectsGatherer,
)


class TestObjectsGathererBase:
    def test_describe_related_object_none(self):
        assert _ObjectsGatherer._describe_related_object(None, {}) == {}

    def test_describe_related_object_unknown(self):
        assert _ObjectsGatherer._describe_related_object(vim.Folder("group-v1"), {}) == {}

    def test_describe_related_object(self):
        related = {"group-v1": {"name": "vm_folder"}}
        assert _ObjectsGatherer._describe_related_object(vim.Folder("group-v1"), related) == {
            "moid": "group-v1",
            "name": "vm_folder",
        }

    def test_describe_related_object_missing_name(self):
        related = {"group-v1": {}}
        assert _ObjectsGatherer._describe_related_object(vim.Folder("group-v1"), related) == {
            "moid": "group-v1",
            "name": None,
        }

    def test_find_datacenter_none(self):
        assert _ObjectsGatherer._find_datacenter(None, {}) is None

    def test_find_datacenter_ref_is_datacenter(self):
        dc = vim.Datacenter("datacenter-1")
        assert _ObjectsGatherer._find_datacenter(dc, {}) is dc

    def test_find_datacenter_walks_parents(self):
        dc = vim.Datacenter("datacenter-1")
        parent = vim.Folder("group-v2")
        child = vim.Folder("group-v3")
        related = {
            "group-v3": {"parent": parent},
            "group-v2": {"parent": dc},
        }
        assert _ObjectsGatherer._find_datacenter(child, related) is dc

    def test_find_datacenter_not_found(self):
        child = vim.Folder("group-v3")
        related = {"group-v3": {"name": "orphan"}}
        assert _ObjectsGatherer._find_datacenter(child, related) is None

    def test_find_datacenter_unknown_ref(self):
        assert _ObjectsGatherer._find_datacenter(vim.Folder("group-v3"), {}) is None


class TestComputeObjectsGatherer:
    def test_vm_properties(self):
        assert ComputeObjectsGatherer.vm_properties == ["resourcePool", "runtime.host"]

    def test_traversal_specs(self):
        specs = ComputeObjectsGatherer.traversal_specs()
        assert [s.name for s in specs] == ["vmToResourcePool", "vmToHost"]
        assert specs[0].path == "resourcePool"
        assert specs[1].path == "runtime.host"
        assert [s.name for s in specs[1].selectSet] == ["hostToParent"]
        assert specs[1].selectSet[0].path == "parent"

    def test_property_specs(self):
        specs = ComputeObjectsGatherer.property_specs()
        assert {s.type: s.pathSet for s in specs} == {
            vim.ResourcePool: ["name"],
            vim.HostSystem: ["name", "parent"],
            vim.ComputeResource: ["name"],
        }

    def test_add_facts_cluster_host(self):
        host = vim.HostSystem("host-1")
        cluster = vim.ClusterComputeResource("domain-c1")
        pool = vim.ResourcePool("resgroup-1")
        related = {
            "host-1": {"name": "esxi01", "parent": cluster},
            "domain-c1": {"name": "cluster01"},
            "resgroup-1": {"name": "pool01"},
        }
        vm_info = {}
        ComputeObjectsGatherer.add_facts(
            vm_info, {"runtime.host": host, "resourcePool": pool}, related
        )
        assert vm_info == {
            "cluster": {"moid": "domain-c1", "name": "cluster01"},
            "esxi_host": {"moid": "host-1", "name": "esxi01"},
            "resource_pool": {"moid": "resgroup-1", "name": "pool01"},
        }

    def test_add_facts_standalone_host_has_no_cluster(self):
        host = vim.HostSystem("host-1")
        compute_resource = vim.ComputeResource("domain-s1")
        related = {
            "host-1": {"name": "esxi01", "parent": compute_resource},
            "domain-s1": {"name": "standalone"},
        }
        vm_info = {}
        ComputeObjectsGatherer.add_facts(vm_info, {"runtime.host": host}, related)
        assert vm_info == {
            "cluster": {},
            "esxi_host": {"moid": "host-1", "name": "esxi01"},
            "resource_pool": {},
        }

    def test_add_facts_no_host(self):
        vm_info = {}
        ComputeObjectsGatherer.add_facts(vm_info, {}, {})
        assert vm_info == {"cluster": {}, "esxi_host": {}, "resource_pool": {}}


class TestLocationObjectsGatherer:
    def test_vm_properties(self):
        assert LocationObjectsGatherer.vm_properties == ["parent"]

    def test_traversal_specs(self):
        specs = LocationObjectsGatherer.traversal_specs()
        assert [s.name for s in specs] == ["folderToParent", "vmToFolder"]
        for spec in specs:
            assert spec.path == "parent"
            assert [s.name for s in spec.selectSet] == ["folderToParent"]

    def test_property_specs(self):
        specs = LocationObjectsGatherer.property_specs()
        assert {s.type: s.pathSet for s in specs} == {
            vim.Folder: ["name", "parent"],
            vim.Datacenter: ["name"],
        }

    def test_add_facts(self):
        dc = vim.Datacenter("datacenter-1")
        parent_folder = vim.Folder("group-v2")
        folder = vim.Folder("group-v3")
        related = {
            "group-v3": {"name": "child", "parent": parent_folder},
            "group-v2": {"name": "vm", "parent": dc},
            "datacenter-1": {"name": "dc01"},
        }
        vm_info = {}
        LocationObjectsGatherer.add_facts(vm_info, {"parent": folder}, related)
        assert vm_info == {
            "folder": {"moid": "group-v3", "name": "child"},
            "datacenter": {"moid": "datacenter-1", "name": "dc01"},
        }

    def test_add_facts_folder_directly_under_datacenter(self):
        dc = vim.Datacenter("datacenter-1")
        folder = vim.Folder("group-v2")
        related = {
            "group-v2": {"name": "vm", "parent": dc},
            "datacenter-1": {"name": "dc01"},
        }
        vm_info = {}
        LocationObjectsGatherer.add_facts(vm_info, {"parent": folder}, related)
        assert vm_info["datacenter"] == {"moid": "datacenter-1", "name": "dc01"}

    def test_add_facts_no_parent(self):
        vm_info = {}
        LocationObjectsGatherer.add_facts(vm_info, {}, {})
        assert vm_info == {"folder": {}, "datacenter": {}}

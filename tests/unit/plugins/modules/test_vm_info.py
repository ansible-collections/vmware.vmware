from __future__ import absolute_import, division, print_function
__metaclass__ = type

import sys
import pytest

from pyVmomi import vim, vmodl

from ansible_collections.vmware.vmware.plugins.modules import vm_info

from ...common.utils import (
    run_module, ModuleTestCase
)

pytestmark = pytest.mark.skipif(
    sys.version_info < (2, 7), reason="requires python2.7 or higher"
)


def build_object_content(moid="vm-1", properties=None, missing=None):
    """
    Build a real vim.ObjectContent, the shape the property collector hands back to the module.
    """
    prop_set = [
        vmodl.DynamicProperty(name=name, val=value)
        for name, value in (properties or {}).items()
    ]
    return vim.ObjectContent(
        obj=vim.VirtualMachine(moid),
        propSet=prop_set,
        missingSet=(missing or []),
    )


def build_missing_property(path="config", fault=None):
    return vmodl.query.PropertyCollector.MissingProperty(
        path=path,
        fault=(fault if fault is not None else vmodl.fault.ManagedObjectNotFound()),
    )


def build_related_object_content(obj, properties=None, missing=None):
    """
    Build a vim.ObjectContent for a non-VM object (folder, host, etc) collected through a traversal spec.
    """
    return vim.ObjectContent(
        obj=obj,
        propSet=[
            vmodl.DynamicProperty(name=name, val=value)
            for name, value in (properties or {}).items()
        ],
        missingSet=(missing or []),
    )


def build_info_instance(mocker, params=None):
    """
    Build a VmwareVmInfo without running __init__, which would open connections.
    """
    mocker.patch.object(vm_info.VmwareVmInfo, "__init__", return_value=None)
    info = vm_info.VmwareVmInfo(mocker.Mock())
    info.module = mocker.Mock()
    info.params = params if params is not None else {}
    info.pyvmomi = mocker.Mock()
    info.vm_svc = mocker.Mock()
    info._enabled_gatherers = []
    info._search_properties = None
    return info


class TestPrefetchedVm:
    """
    _PrefetchedVm stands in for a vim.VirtualMachine so VmFacts can read properties that
    the property collector already returned, without triggering another SOAP call.
    """

    def test_copies_moid_and_prop_set(self):
        object_content = build_object_content(
            moid="vm-42", properties={"config": "config-value", "guest": "guest-value"}
        )

        prefetched = vm_info._PrefetchedVm(object_content)

        assert prefetched._moId == "vm-42"
        assert prefetched.config == "config-value"
        assert prefetched.guest == "guest-value"

    def test_unset_summary_properties_default_to_none(self):
        """
        The collector omits unset properties from propSet. Those must still be readable
        as None instead of raising AttributeError inside VmFacts.
        """
        object_content = build_object_content(properties={"config": "config-value"})

        prefetched = vm_info._PrefetchedVm(object_content)

        for prop_name in vm_info.SUMMARY_SCHEMA_PROPERTIES:
            assert hasattr(prefetched, prop_name)
        assert prefetched.summary is None
        assert prefetched.parentVApp is None
        assert prefetched.config == "config-value"

    def test_properties_outside_the_summary_set_are_still_applied(self):
        object_content = build_object_content(properties={"name": "my-vm"})

        prefetched = vm_info._PrefetchedVm(object_content)

        assert prefetched.name == "my-vm"


class TestSchemaHelpers:
    def test_schema_is_vsphere(self, mocker):
        assert build_info_instance(mocker, {"schema": "vsphere"}).schema_is_vsphere() is True
        assert build_info_instance(mocker, {"schema": "summary"}).schema_is_vsphere() is False

    def test_summary_schema_requests_the_fixed_property_set(self, mocker):
        info = build_info_instance(mocker, {"schema": "summary", "properties": None})

        assert set(info.search_properties) == set(vm_info.SUMMARY_SCHEMA_PROPERTIES)

    def test_vsphere_schema_requests_the_user_properties(self, mocker):
        info = build_info_instance(
            mocker, {"schema": "vsphere", "properties": ["name", "runtime.powerState"]}
        )

        assert set(info.search_properties) == {"name", "runtime.powerState"}

    @pytest.mark.parametrize("properties", [None])
    def test_vsphere_schema_without_properties_requests_everything(self, mocker, properties):
        """
        The 'all' sentinel is the signal to _create_prop_set to set all=True on the
        property spec.
        """
        info = build_info_instance(mocker, {"schema": "vsphere", "properties": properties})

        assert info.search_properties == ["all"]


class TestGatherInfoForVms:
    def test_summary_schema_builds_facts_from_prefetched_vm(self, mocker):
        info = build_info_instance(mocker, {"schema": "summary", "properties": None})
        object_content = build_object_content(moid="vm-1", properties={"config": "config-value"})
        mocker.patch.object(
            vm_info.VmwareVmInfo,
            "_collect_vm_managed_object_properties",
            return_value=[object_content],
        )
        vm_facts = mocker.patch.object(vm_info, "VmFacts")
        vm_facts.return_value.all_facts.return_value = {"hw_name": "vm1"}
        hydrate = mocker.patch.object(vm_info.VmwareVmInfo, "_hydrate_vm_info_with_rest_calls")

        result = info.gather_info_for_vms()

        assert result == [{"hw_name": "vm1"}]
        vm_facts.return_value.all_facts.assert_called_once_with(info.pyvmomi.content)
        # VmFacts must be handed the prefetched stand-in, not the live managed object
        prefetched = vm_facts.call_args[0][0]
        assert isinstance(prefetched, vm_info._PrefetchedVm)
        assert prefetched._moId == "vm-1"
        assert prefetched.config == "config-value"
        # the REST hydration needs the real managed object reference
        hydrate.assert_called_once_with({"hw_name": "vm1"}, object_content.obj)

    def test_vsphere_schema_converts_prop_set(self, mocker):
        info = build_info_instance(mocker, {"schema": "vsphere", "properties": ["name"]})
        object_content = build_object_content(moid="vm-1", properties={"name": "vm1"})
        mocker.patch.object(
            vm_info.VmwareVmInfo,
            "_collect_vm_managed_object_properties",
            return_value=[object_content],
        )
        converter = mocker.patch.object(
            vm_info, "properties_from_collector", return_value={"name": "vm1"}
        )
        mocker.patch.object(vm_info.VmwareVmInfo, "_hydrate_vm_info_with_rest_calls")

        result = info.gather_info_for_vms()

        assert result == [{"name": "vm1"}]
        converter.assert_called_once_with(object_content.propSet)
        info.module.fail_json.assert_not_called()

    def test_skips_vm_that_disappeared_mid_gather(self, mocker):
        """
        Large environments churn. A VM deleted between the search and the property
        collection must warn and be skipped, not fail the whole run.
        """
        info = build_info_instance(mocker, {"schema": "vsphere", "properties": ["name"]})
        missing_vm = build_object_content(
            moid="vm-gone",
            missing=[build_missing_property(fault=vmodl.fault.ManagedObjectNotFound())],
        )
        present_vm = build_object_content(moid="vm-1", properties={"name": "vm1"})
        mocker.patch.object(
            vm_info.VmwareVmInfo,
            "_collect_vm_managed_object_properties",
            return_value=[missing_vm, present_vm],
        )
        mocker.patch.object(
            vm_info, "properties_from_collector", return_value={"name": "vm1"}
        )
        mocker.patch.object(vm_info.VmwareVmInfo, "_hydrate_vm_info_with_rest_calls")

        result = info.gather_info_for_vms()

        assert result == [{"name": "vm1"}]
        info.module.warn.assert_called_once()
        assert "vm-gone" in info.module.warn.call_args[0][0]
        info.module.fail_json.assert_not_called()

    def test_unreadable_property_fails_the_module(self, mocker):
        """
        The VM is there but a requested property could not be read - usually a typo
        in the property path or a permissions problem. That should be loud.
        """
        info = build_info_instance(mocker, {"schema": "vsphere", "properties": ["bogus.path"]})
        object_content = build_object_content(
            moid="vm-1",
            missing=[
                build_missing_property(
                    path="bogus.path", fault=vmodl.fault.InvalidArgument(msg="no such property")
                )
            ],
        )
        mocker.patch.object(
            vm_info.VmwareVmInfo,
            "_collect_vm_managed_object_properties",
            return_value=[object_content],
        )
        mocker.patch.object(vm_info, "properties_from_collector", return_value={})
        mocker.patch.object(vm_info.VmwareVmInfo, "_hydrate_vm_info_with_rest_calls")

        info.gather_info_for_vms()

        info.module.fail_json.assert_called_once()
        message = info.module.fail_json.call_args[1]["msg"]
        assert "bogus.path" in message
        assert "vm-1" in message
        assert "no such property" in message

    def test_unreadable_property_is_tolerated_when_gathering_all_properties(self, mocker):
        """
        With no explicit property list the module asks for everything, so individual
        unreadable properties are expected rather than user error.
        """
        info = build_info_instance(mocker, {"schema": "vsphere", "properties": None})
        object_content = build_object_content(
            moid="vm-1",
            properties={"name": "vm1"},
            missing=[
                build_missing_property(
                    path="config", fault=vmodl.fault.InvalidArgument(msg="denied")
                )
            ],
        )
        mocker.patch.object(
            vm_info.VmwareVmInfo,
            "_collect_vm_managed_object_properties",
            return_value=[object_content],
        )
        mocker.patch.object(
            vm_info, "properties_from_collector", return_value={"name": "vm1"}
        )
        mocker.patch.object(vm_info.VmwareVmInfo, "_hydrate_vm_info_with_rest_calls")

        result = info.gather_info_for_vms()

        assert result == [{"name": "vm1"}]
        info.module.fail_json.assert_not_called()

    def test_unreadable_property_is_tolerated_for_summary_schema(self, mocker):
        info = build_info_instance(mocker, {"schema": "summary", "properties": None})
        object_content = build_object_content(
            moid="vm-1",
            missing=[
                build_missing_property(
                    path="snapshot", fault=vmodl.fault.InvalidArgument(msg="denied")
                )
            ],
        )
        mocker.patch.object(
            vm_info.VmwareVmInfo,
            "_collect_vm_managed_object_properties",
            return_value=[object_content],
        )
        vm_facts = mocker.patch.object(vm_info, "VmFacts")
        vm_facts.return_value.all_facts.return_value = {"hw_name": "vm1"}
        mocker.patch.object(vm_info.VmwareVmInfo, "_hydrate_vm_info_with_rest_calls")

        result = info.gather_info_for_vms()

        assert result == [{"hw_name": "vm1"}]
        info.module.fail_json.assert_not_called()

    def test_returns_empty_list_when_nothing_matched(self, mocker):
        info = build_info_instance(mocker, {"schema": "vsphere", "properties": ["name"]})
        mocker.patch.object(
            vm_info.VmwareVmInfo, "_collect_vm_managed_object_properties", return_value=[]
        )
        hydrate = mocker.patch.object(vm_info.VmwareVmInfo, "_hydrate_vm_info_with_rest_calls")

        assert info.gather_info_for_vms() == []
        hydrate.assert_not_called()
        info.module.warn.assert_not_called()


class TestCollectVmManagedObjectProperties:
    def test_returns_empty_without_querying_when_no_vms(self, mocker):
        info = build_info_instance(mocker, {"schema": "vsphere", "properties": ["name"]})
        mocker.patch.object(vm_info.VmwareVmInfo, "get_vms", return_value=[])

        assert info._collect_vm_managed_object_properties() == []
        info.pyvmomi._query_paged_managed_object_properties.assert_not_called()

    def test_builds_filter_spec_for_requested_properties(self, mocker):
        info = build_info_instance(
            mocker, {"schema": "vsphere", "properties": ["name", "runtime.powerState"]}
        )
        vms = [vim.VirtualMachine("vm-1"), vim.VirtualMachine("vm-2")]
        mocker.patch.object(vm_info.VmwareVmInfo, "get_vms", return_value=vms)
        info.pyvmomi._query_paged_managed_object_properties.return_value = ["result"]

        assert info._collect_vm_managed_object_properties() == ["result"]

        filter_spec = info.pyvmomi._query_paged_managed_object_properties.call_args[0][0]
        assert filter_spec.propSet[0].type == vim.VirtualMachine
        assert set(filter_spec.propSet[0].pathSet) == {"name", "runtime.powerState"}
        assert filter_spec.propSet[0].all is False
        assert [spec.obj for spec in filter_spec.objectSet] == vms
        assert all(spec.skip is False for spec in filter_spec.objectSet)
        # without this a single bad VM would poison the whole batch
        assert filter_spec.reportMissingObjectsInResults is True

    def test_requests_all_properties_when_none_specified(self, mocker):
        info = build_info_instance(mocker, {"schema": "vsphere", "properties": None})
        mocker.patch.object(
            vm_info.VmwareVmInfo, "get_vms", return_value=[vim.VirtualMachine("vm-1")]
        )
        info.pyvmomi._query_paged_managed_object_properties.return_value = []

        info._collect_vm_managed_object_properties()

        filter_spec = info.pyvmomi._query_paged_managed_object_properties.call_args[0][0]
        assert filter_spec.propSet[0].all is True
        assert filter_spec.propSet[0].pathSet == []

    def test_summary_schema_requests_the_fixed_property_set(self, mocker):
        info = build_info_instance(mocker, {"schema": "summary", "properties": None})
        mocker.patch.object(
            vm_info.VmwareVmInfo, "get_vms", return_value=[vim.VirtualMachine("vm-1")]
        )
        info.pyvmomi._query_paged_managed_object_properties.return_value = []

        info._collect_vm_managed_object_properties()

        filter_spec = info.pyvmomi._query_paged_managed_object_properties.call_args[0][0]
        assert set(filter_spec.propSet[0].pathSet) == set(vm_info.SUMMARY_SCHEMA_PROPERTIES)
        assert filter_spec.propSet[0].all is False

    def test_invalid_property_path_fails_the_module(self, mocker):
        info = build_info_instance(mocker, {"schema": "vsphere", "properties": ["nope"]})
        mocker.patch.object(
            vm_info.VmwareVmInfo, "get_vms", return_value=[vim.VirtualMachine("vm-1")]
        )
        info.pyvmomi._query_paged_managed_object_properties.side_effect = (
            vmodl.query.InvalidProperty(name="nope")
        )

        info._collect_vm_managed_object_properties()

        info.module.fail_json.assert_called_once()
        assert "nope" in info.module.fail_json.call_args[1]["msg"]


class TestEnabledGatherers:
    def test_none_enabled_by_default(self, mocker):
        info = build_info_instance(mocker, {})

        assert info.enabled_gatherers == []

    def test_compute_only(self, mocker):
        info = build_info_instance(mocker, {"gather_compute_objects": True})

        assert info.enabled_gatherers == [vm_info.ComputeObjectsGatherer]

    def test_location_only(self, mocker):
        info = build_info_instance(mocker, {"gather_location_objects": True})

        assert info.enabled_gatherers == [vm_info.LocationObjectsGatherer]

    def test_both_enabled(self, mocker):
        info = build_info_instance(
            mocker, {"gather_compute_objects": True, "gather_location_objects": True}
        )

        assert set(info.enabled_gatherers) == {
            vm_info.ComputeObjectsGatherer, vm_info.LocationObjectsGatherer
        }


class TestSearchPropertiesWithGatherers:
    def test_vsphere_schema_adds_gatherer_properties(self, mocker):
        info = build_info_instance(
            mocker,
            {"schema": "vsphere", "properties": ["name"], "gather_compute_objects": True},
        )

        assert set(info.search_properties) == {"name", "resourcePool", "runtime.host"}

    def test_vsphere_schema_with_empty_properties_returns_only_gatherer_properties(self, mocker):
        info = build_info_instance(
            mocker,
            {"schema": "vsphere", "properties": [], "gather_location_objects": True},
        )

        assert info.search_properties == ["parent"]

    def test_vsphere_schema_with_empty_properties_and_no_gatherers_returns_nothing(self, mocker):
        info = build_info_instance(mocker, {"schema": "vsphere", "properties": []})

        assert info.search_properties == []

    def test_summary_schema_adds_gatherer_properties(self, mocker):
        info = build_info_instance(
            mocker, {"schema": "summary", "gather_location_objects": True}
        )

        assert set(info.search_properties) == set(vm_info.SUMMARY_SCHEMA_PROPERTIES) | {"parent"}

    def test_result_is_cached(self, mocker):
        info = build_info_instance(mocker, {"schema": "vsphere", "properties": ["name"]})

        first = info.search_properties
        info.params["properties"] = ["other"]

        assert info.search_properties is first


class TestCreateSelectSet:
    def test_none_without_gatherers(self, mocker):
        info = build_info_instance(mocker, {})

        assert info._create_select_set() is None

    def test_includes_traversal_specs_of_enabled_gatherers(self, mocker):
        info = build_info_instance(
            mocker, {"gather_compute_objects": True, "gather_location_objects": True}
        )

        names = {spec.name for spec in info._create_select_set()}

        assert names == {"vmToResourcePool", "vmToHost", "folderToParent", "vmToFolder"}


class TestCreatePropSet:
    def test_specific_properties(self, mocker):
        info = build_info_instance(mocker, {"schema": "vsphere", "properties": ["name"]})

        prop_set = info._create_prop_set()

        assert len(prop_set) == 1
        assert prop_set[0].type == vim.VirtualMachine
        assert prop_set[0].pathSet == ["name"]
        assert prop_set[0].all is False

    def test_all_properties_sentinel_is_not_a_path(self, mocker):
        info = build_info_instance(mocker, {"schema": "vsphere", "properties": None})

        prop_set = info._create_prop_set()

        assert prop_set[0].pathSet == []
        assert prop_set[0].all is True

    def test_all_properties_with_gatherers_still_requests_everything(self, mocker):
        info = build_info_instance(
            mocker,
            {"schema": "vsphere", "properties": None, "gather_compute_objects": True},
        )

        prop_set = info._create_prop_set()

        assert prop_set[0].all is True
        assert set(prop_set[0].pathSet) == {"resourcePool", "runtime.host"}

    def test_appends_gatherer_property_specs(self, mocker):
        info = build_info_instance(
            mocker,
            {"schema": "vsphere", "properties": ["name"], "gather_location_objects": True},
        )

        prop_set = info._create_prop_set()

        assert [spec.type for spec in prop_set] == [
            vim.VirtualMachine, vim.Folder, vim.Datacenter
        ]


class TestFailOnMissingVmProperties:
    def test_fails_for_each_unreadable_property(self, mocker):
        info = build_info_instance(mocker, {"schema": "vsphere", "properties": ["a", "b"]})
        content = build_object_content(
            moid="vm-1",
            missing=[
                build_missing_property(path="a", fault=vmodl.fault.InvalidArgument(msg="denied")),
            ],
        )

        info._fail_on_missing_vm_properties(content)

        info.module.fail_json.assert_called_once()
        message = info.module.fail_json.call_args[1]["msg"]
        assert "'a'" in message and "vm-1" in message and "denied" in message

    def test_no_failure_without_missing_properties(self, mocker):
        info = build_info_instance(mocker, {"schema": "vsphere", "properties": ["a"]})

        info._fail_on_missing_vm_properties(build_object_content(properties={"a": 1}))

        info.module.fail_json.assert_not_called()

    def test_tolerated_when_gathering_all(self, mocker):
        info = build_info_instance(mocker, {"schema": "vsphere", "properties": None})
        content = build_object_content(
            missing=[build_missing_property(path="a", fault=vmodl.fault.InvalidArgument(msg="x"))]
        )

        info._fail_on_missing_vm_properties(content)

        info.module.fail_json.assert_not_called()

    def test_tolerated_for_summary_schema(self, mocker):
        info = build_info_instance(mocker, {"schema": "summary"})
        content = build_object_content(
            missing=[build_missing_property(path="a", fault=vmodl.fault.InvalidArgument(msg="x"))]
        )

        info._fail_on_missing_vm_properties(content)

        info.module.fail_json.assert_not_called()


class TestSplitCollectedObjects:
    def test_empty(self, mocker):
        info = build_info_instance(mocker, {"schema": "vsphere", "properties": ["name"]})

        assert info._split_collected_objects([]) == ([], {})

    def test_separates_vms_from_related_objects(self, mocker):
        info = build_info_instance(mocker, {"schema": "vsphere", "properties": ["name"]})
        vm = build_object_content(moid="vm-1", properties={"name": "vm1"})
        folder = build_related_object_content(
            vim.Folder("group-v1"), {"name": "my_folder", "parent": vim.Datacenter("datacenter-1")}
        )
        datacenter = build_related_object_content(
            vim.Datacenter("datacenter-1"), {"name": "dc01"}
        )

        vm_refs, related = info._split_collected_objects([vm, folder, datacenter])

        assert vm_refs == [vm]
        assert related == {
            "group-v1": {"name": "my_folder", "parent": vim.Datacenter("datacenter-1")},
            "datacenter-1": {"name": "dc01"},
        }

    def test_warns_and_skips_deleted_vm(self, mocker):
        info = build_info_instance(mocker, {"schema": "vsphere", "properties": ["name"]})
        gone = build_object_content(moid="vm-gone", missing=[build_missing_property()])

        vm_refs, related = info._split_collected_objects([gone])

        assert (vm_refs, related) == ([], {})
        info.module.warn.assert_called_once()
        assert "vm-gone" in info.module.warn.call_args[0][0]

    def test_warns_and_skips_deleted_related_object(self, mocker):
        info = build_info_instance(mocker, {"schema": "vsphere", "properties": ["name"]})
        gone = build_related_object_content(
            vim.Folder("group-gone"), missing=[build_missing_property()]
        )

        vm_refs, related = info._split_collected_objects([gone])

        assert (vm_refs, related) == ([], {})
        info.module.warn.assert_called_once()

    def test_unreadable_vm_property_fails_the_module(self, mocker):
        info = build_info_instance(mocker, {"schema": "vsphere", "properties": ["bogus"]})
        vm = build_object_content(
            missing=[build_missing_property(path="bogus", fault=vmodl.fault.InvalidArgument(msg="no"))]
        )

        info._split_collected_objects([vm])

        info.module.fail_json.assert_called_once()

    def test_unreadable_related_object_property_is_not_checked(self, mocker):
        info = build_info_instance(mocker, {"schema": "vsphere", "properties": ["name"]})
        folder = build_related_object_content(
            vim.Folder("group-v1"),
            {"name": "f"},
            missing=[build_missing_property(path="parent", fault=vmodl.fault.InvalidArgument(msg="no"))],
        )

        _, related = info._split_collected_objects([folder])  # pylint: disable=disallowed-name

        assert related == {"group-v1": {"name": "f"}}
        info.module.fail_json.assert_not_called()


class TestHydrateVmInfoWithCollectedProps:
    def test_vsphere_schema_without_gatherers(self, mocker):
        info = build_info_instance(mocker, {"schema": "vsphere", "properties": ["name"]})
        content = build_object_content(properties={"name": "vm1"})
        mocker.patch.object(vm_info, "properties_from_collector", return_value={"name": "vm1"})

        assert info._hydrate_vm_info_with_collected_props(content, {}) == {"name": "vm1"}

    def test_summary_schema_uses_prefetched_vm_facts(self, mocker):
        info = build_info_instance(mocker, {"schema": "summary"})
        content = build_object_content(moid="vm-1", properties={"config": "c"})
        vm_facts = mocker.patch.object(vm_info, "VmFacts")
        vm_facts.return_value.all_facts.return_value = {"hw_name": "vm1"}

        result = info._hydrate_vm_info_with_collected_props(content, {})

        assert result == {"hw_name": "vm1"}
        assert isinstance(vm_facts.call_args[0][0], vm_info._PrefetchedVm)
        vm_facts.return_value.all_facts.assert_called_once_with(info.pyvmomi.content)

    def test_gatherers_receive_flat_vm_props_and_related_objects(self, mocker):
        info = build_info_instance(
            mocker,
            {"schema": "vsphere", "properties": ["name"], "gather_location_objects": True},
        )
        content = build_object_content(properties={"name": "vm1", "parent": "folder-ref"})
        mocker.patch.object(vm_info, "properties_from_collector", return_value={"name": "vm1"})
        gatherer = mocker.Mock()
        info._enabled_gatherers = [gatherer]
        related = {"group-v1": {"name": "f"}}

        result = info._hydrate_vm_info_with_collected_props(content, related)

        gatherer.add_facts.assert_called_once_with(
            {"name": "vm1"}, {"name": "vm1", "parent": "folder-ref"}, related
        )
        assert result == {"name": "vm1"}

    def test_gatherers_enrich_vm_info(self, mocker):
        info = build_info_instance(
            mocker,
            {"schema": "vsphere", "properties": [], "gather_location_objects": True},
        )
        folder = vim.Folder("group-v1")
        content = build_object_content(properties={"parent": folder})
        related = {
            "group-v1": {"name": "my_folder", "parent": vim.Datacenter("datacenter-1")},
            "datacenter-1": {"name": "dc01"},
        }

        result = info._hydrate_vm_info_with_collected_props(content, related)

        assert result["folder"] == {"moid": "group-v1", "name": "my_folder"}
        assert result["datacenter"] == {"moid": "datacenter-1", "name": "dc01"}


class TestGatherInfoForVmsWithRelatedObjects:
    def test_related_objects_are_passed_to_each_vm(self, mocker):
        info = build_info_instance(
            mocker,
            {"schema": "vsphere", "properties": [], "gather_location_objects": True},
        )
        vm = build_object_content(moid="vm-1", properties={"parent": vim.Folder("group-v1")})
        folder = build_related_object_content(
            vim.Folder("group-v1"), {"name": "my_folder", "parent": vim.Datacenter("datacenter-1")}
        )
        datacenter = build_related_object_content(vim.Datacenter("datacenter-1"), {"name": "dc01"})
        mocker.patch.object(
            vm_info.VmwareVmInfo,
            "_collect_vm_managed_object_properties",
            return_value=[vm, folder, datacenter],
        )
        mocker.patch.object(vm_info, "properties_from_collector", return_value={})
        hydrate = mocker.patch.object(vm_info.VmwareVmInfo, "_hydrate_vm_info_with_rest_calls")

        result = info.gather_info_for_vms()

        # only the VM becomes a result; the folder and datacenter are lookup data
        assert len(result) == 1
        assert result[0]["folder"] == {"moid": "group-v1", "name": "my_folder"}
        assert result[0]["datacenter"] == {"moid": "datacenter-1", "name": "dc01"}
        hydrate.assert_called_once_with(result[0], vm.obj)


class TestCollectVmManagedObjectPropertiesWithGatherers:
    def test_filter_spec_includes_gatherer_specs(self, mocker):
        info = build_info_instance(
            mocker,
            {"schema": "vsphere", "properties": ["name"], "gather_location_objects": True},
        )
        vms = [vim.VirtualMachine("vm-1")]
        mocker.patch.object(vm_info.VmwareVmInfo, "get_vms", return_value=vms)

        info._collect_vm_managed_object_properties()

        filter_spec = info.pyvmomi._query_paged_managed_object_properties.call_args[0][0]
        assert [p.type for p in filter_spec.propSet] == [
            vim.VirtualMachine, vim.Folder, vim.Datacenter
        ]
        assert set(filter_spec.propSet[0].pathSet) == {"name", "parent"}
        assert {s.name for s in filter_spec.objectSet[0].selectSet} == {
            "folderToParent", "vmToFolder"
        }

    def test_no_select_set_without_gatherers(self, mocker):
        info = build_info_instance(mocker, {"schema": "vsphere", "properties": ["name"]})
        mocker.patch.object(
            vm_info.VmwareVmInfo, "get_vms", return_value=[vim.VirtualMachine("vm-1")]
        )

        info._collect_vm_managed_object_properties()

        filter_spec = info.pyvmomi._query_paged_managed_object_properties.call_args[0][0]
        assert not filter_spec.objectSet[0].selectSet


class TestGetVms:
    @pytest.mark.parametrize("identifier", ["name", "uuid", "moid"])
    def test_searches_by_identifier_when_one_is_given(self, mocker, identifier):
        info = build_info_instance(mocker, {identifier: "something"})
        info.pyvmomi.get_vms_using_params.return_value = ["vm"]

        assert info.get_vms() == ["vm"]
        info.pyvmomi.get_vms_using_params.assert_called_once_with(fail_on_missing=False)
        info.pyvmomi.get_all_vms.assert_not_called()

    def test_gathers_every_vm_when_no_identifier_or_folder(self, mocker):
        info = build_info_instance(mocker, {"name": None, "uuid": None, "moid": None, "folder": None})
        info.pyvmomi.get_all_vms.return_value = ["vm1", "vm2"]

        assert info.get_vms() == ["vm1", "vm2"]
        info.pyvmomi.get_all_vms.assert_called_once_with(folder=None)
        info.pyvmomi.get_folder_using_params.assert_not_called()

    def test_scopes_the_search_to_a_folder(self, mocker):
        """
        folder on its own (no name/uuid/moid) now limits a bulk gather to that folder.
        """
        info = build_info_instance(mocker, {"folder": "/dc/vm/prod"})
        folder = mocker.Mock()
        info.pyvmomi.get_folder_using_params.return_value = folder
        info.pyvmomi.get_all_vms.return_value = ["vm1"]

        assert info.get_vms() == ["vm1"]
        # a folder the user explicitly named but that does not exist is an error
        info.pyvmomi.get_folder_using_params.assert_called_once_with(fail_on_missing=True)
        info.pyvmomi.get_all_vms.assert_called_once_with(folder=folder)

    def test_returns_empty_list_when_search_finds_nothing(self, mocker):
        info = build_info_instance(mocker, {"name": "missing"})
        info.pyvmomi.get_vms_using_params.return_value = None

        assert info.get_vms() == []


class TestGetIdentity:
    def test_skipped_when_gather_identity_is_false(self, mocker):
        info = build_info_instance(mocker, {"gather_identity": False})

        assert info._get_identity(vim.VirtualMachine("vm-1")) == {}
        info.vm_svc.guest.Identity.get.assert_not_called()

    def test_returns_extracted_attributes(self, mocker):
        info = build_info_instance(mocker, {"gather_identity": True})
        identity = mocker.Mock()
        info.vm_svc.guest.Identity.get.return_value = identity
        extract = mocker.patch.object(
            vm_info, "extract_object_attributes_to_dict", return_value={"name": "linux"}
        )

        assert info._get_identity(vim.VirtualMachine("vm-1")) == {"name": "linux"}
        info.vm_svc.guest.Identity.get.assert_called_once_with(vm="vm-1")
        extract.assert_called_once_with(identity)

    def test_returns_empty_dict_when_the_api_call_fails(self, mocker):
        """
        Identity is unavailable on powered off VMs and VMs without tools, which is
        not an error for an info module.
        """
        info = build_info_instance(mocker, {"gather_identity": True})
        info.vm_svc.guest.Identity.get.side_effect = Exception("tools not running")

        assert info._get_identity(vim.VirtualMachine("vm-1")) == {}


class TestGetEnv:
    def test_skipped_without_guest_credentials(self, mocker):
        info = build_info_instance(mocker, {"guest_username": None})

        assert info._get_env(vim.VirtualMachine("vm-1")) == {}
        info.vm_svc.guest.Environment.list.assert_not_called()

    def test_returns_guest_environment(self, mocker):
        info = build_info_instance(
            mocker, {"guest_username": "root", "guest_password": "secret"}
        )
        info.vm_svc.guest.Environment.list.return_value = {"PATH": "/bin"}
        vm = vim.VirtualMachine("vm-1")

        assert info._get_env(vm) == {"PATH": "/bin"}
        call_kwargs = info.vm_svc.guest.Environment.list.call_args[1]
        assert call_kwargs["vm"] is vm
        assert call_kwargs["credentials"]["user_name"] == "root"
        assert call_kwargs["credentials"]["password"] == "secret"

    def test_returns_empty_dict_when_the_api_call_fails(self, mocker):
        info = build_info_instance(
            mocker, {"guest_username": "root", "guest_password": "secret"}
        )
        info.vm_svc.guest.Environment.list.side_effect = Exception("bad credentials")

        assert info._get_env(vim.VirtualMachine("vm-1")) == {}


class TestGetTags:
    def test_skipped_when_gather_tags_is_false(self, mocker):
        info = build_info_instance(mocker, {"gather_tags": False})
        get_tags = mocker.patch.object(vm_info.VmwareVmInfo, "get_tags_by_vm_moid")

        assert info._get_tags(vim.VirtualMachine("vm-1")) == []
        get_tags.assert_not_called()

    def test_formats_each_tag(self, mocker):
        info = build_info_instance(mocker, {"gather_tags": True})
        mocker.patch.object(
            vm_info.VmwareVmInfo, "get_tags_by_vm_moid", return_value=["tag-a", "tag-b"]
        )
        mocker.patch.object(
            vm_info.VmwareVmInfo,
            "format_tag_identity_as_dict",
            side_effect=lambda tag: {"name": tag},
        )

        assert info._get_tags(vim.VirtualMachine("vm-1")) == [
            {"name": "tag-a"}, {"name": "tag-b"}
        ]


class TestHydrateVmInfoWithRestCalls:
    def test_attaches_identity_tags_and_env(self, mocker):
        info = build_info_instance(mocker)
        mocker.patch.object(
            vm_info.VmwareVmInfo, "_get_identity", return_value={"name": "linux"}
        )
        mocker.patch.object(vm_info.VmwareVmInfo, "_get_tags", return_value=["tag"])
        mocker.patch.object(vm_info.VmwareVmInfo, "_get_env", return_value={"PATH": "/bin"})
        vm_facts = {"moid": "vm-1"}

        info._hydrate_vm_info_with_rest_calls(vm_facts, vim.VirtualMachine("vm-1"))

        assert vm_facts["identity"] == {"name": "linux"}
        # identity keys are also flattened onto the top level for backwards compatibility
        assert vm_facts["name"] == "linux"
        assert vm_facts["tags"] == ["tag"]
        assert vm_facts["env"] == {"PATH": "/bin"}

    def test_empty_identity_adds_no_legacy_keys(self, mocker):
        info = build_info_instance(mocker)
        mocker.patch.object(vm_info.VmwareVmInfo, "_get_identity", return_value={})
        mocker.patch.object(vm_info.VmwareVmInfo, "_get_tags", return_value=[])
        mocker.patch.object(vm_info.VmwareVmInfo, "_get_env", return_value={})
        vm_facts = {"moid": "vm-1"}

        info._hydrate_vm_info_with_rest_calls(vm_facts, vim.VirtualMachine("vm-1"))

        assert vm_facts == {"moid": "vm-1", "identity": {}, "tags": [], "env": {}}


class TestVmInfoModule(ModuleTestCase):

    def __prepare(self, mocker, vms=None):
        mocker.patch.object(vm_info.VmwareVmInfo, "__init__", return_value=None)
        mocker.patch.object(
            vm_info.VmwareVmInfo, "gather_info_for_vms", return_value=(vms or [])
        )

    def test_gather(self, mocker):
        self.__prepare(mocker)

        result = run_module(module_entry=vm_info.main, module_args={})

        assert result["changed"] is False

    def test_vms_and_guests_return_the_same_data(self, mocker):
        """
        guests is a legacy return key kept for backwards compatibility.
        """
        self.__prepare(mocker, vms=[{"moid": "vm-1"}])

        result = run_module(module_entry=vm_info.main, module_args={})

        assert result["vms"] == [{"moid": "vm-1"}]
        assert result["guests"] == result["vms"]

    def test_properties_require_the_vsphere_schema(self, mocker):
        self.__prepare(mocker)

        result = run_module(
            module_entry=vm_info.main,
            module_args={"schema": "summary", "properties": ["name"]},
            expect_success=False,
        )

        assert "properties" in result["msg"]

    def test_properties_are_allowed_with_the_vsphere_schema(self, mocker):
        self.__prepare(mocker)

        result = run_module(
            module_entry=vm_info.main,
            module_args={"schema": "vsphere", "properties": ["name"]},
        )

        assert result["changed"] is False

    @pytest.mark.parametrize(
        "module_args",
        [
            {"name": "vm1", "uuid": "uuid1"},
            {"name": "vm1", "moid": "vm-1"},
            {"uuid": "uuid1", "moid": "vm-1"},
        ],
    )
    def test_identifiers_are_mutually_exclusive(self, mocker, module_args):
        self.__prepare(mocker)

        run_module(module_entry=vm_info.main, module_args=module_args, expect_success=False)

    def test_guest_credentials_must_be_supplied_together(self, mocker):
        self.__prepare(mocker)

        run_module(
            module_entry=vm_info.main,
            module_args={"guest_username": "root"},
            expect_success=False,
        )

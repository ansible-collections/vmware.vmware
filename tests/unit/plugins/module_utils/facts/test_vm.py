from __future__ import absolute_import, division, print_function
__metaclass__ = type

import types
from unittest import mock

from pyVmomi import vim

from ansible_collections.vmware.vmware.plugins.module_utils.facts._vm import (
    VmFacts,
    get_vm_prop_or_none,
    deserialize_snapshot_obj,
    list_snapshots_recursively,
    get_current_snap_obj,
    list_snapshots,
)


VM = 'ansible_collections.vmware.vmware.plugins.module_utils.facts._vm'


def ns(**kwargs):
    """Small helper to build attribute containers that raise AttributeError for missing attrs."""
    return types.SimpleNamespace(**kwargs)


class TestGetVmPropOrNone:
    def test_returns_nested_value(self):
        vm = ns(guest=ns(net=["a", "b"]))
        assert get_vm_prop_or_none(vm, ('guest', 'net')) == ["a", "b"]

    def test_missing_attribute_returns_none(self):
        vm = ns(guest=ns())
        assert get_vm_prop_or_none(vm, ('guest', 'net')) is None

    def test_missing_top_level_returns_none(self):
        assert get_vm_prop_or_none(ns(), ('guest', 'net')) is None


class TestVmFactsIdentifier:
    def test_identifier_facts(self):
        vm = ns(_moId="vm-42", config=ns(instanceUuid="iuuid"))
        assert VmFacts(vm).identifier_facts() == {
            "instance_uuid": "iuuid",
            "moid": "vm-42",
            "vimref": "vim.VirtualMachine:vm-42",
        }


class TestVmFactsCustomAttributes:
    def test_maps_field_key_to_name(self):
        vm = ns(
            summary=ns(customValue=[ns(key=1, value="prod")]),
            config=ns(annotation="a note"),
        )
        content = ns(customFieldsManager=ns(field=[ns(key=1, name="environment")]))
        assert VmFacts(vm).custom_attribute_facts(content) == {
            "customvalues": {"environment": "prod"},
            "annotation": "a note",
        }

    def test_uses_raw_key_when_no_fields_manager(self):
        vm = ns(
            summary=ns(customValue=[ns(key=7, value="prod")]),
            config=ns(annotation=""),
        )
        content = ns(customFieldsManager=None)
        assert VmFacts(vm).custom_attribute_facts(content) == {
            "customvalues": {7: "prod"},
            "annotation": "",
        }


class TestVmFactsAdvancedSettings:
    def test_advanced_settings_facts(self):
        vm = ns(config=ns(extraConfig=[ns(key="foo", value="bar"), ns(key="baz", value="1")]))
        assert VmFacts(vm).advanced_settings_facts() == {
            "advanced_settings": {"foo": "bar", "baz": "1"}
        }


class TestVmFactsIp:
    def test_ipv4(self):
        vm = ns(guest=ns(ipAddress="10.0.0.1"))
        assert VmFacts(vm).ip_facts() == {"ipv4": "10.0.0.1", "ipv6": None}

    def test_ipv6(self):
        vm = ns(guest=ns(ipAddress="fe80::1"))
        assert VmFacts(vm).ip_facts() == {"ipv4": None, "ipv6": "fe80::1"}

    def test_no_ip(self):
        vm = ns(guest=ns(ipAddress=None))
        assert VmFacts(vm).ip_facts() == {"ipv4": None, "ipv6": None}


class TestVmFactsVnc:
    def test_collects_vnc_options(self):
        extra_config = [
            ns(key="RemoteDisplay.vnc.enabled", value="true"),
            ns(key="remotedisplay.vnc.port", value="5900"),
            ns(key="unrelated.setting", value="x"),
        ]
        vm = ns(config=ns(extraConfig=extra_config))
        assert VmFacts(vm).vnc_facts() == {"vnc": {"enabled": "true", "port": "5900"}}

    def test_no_vnc_options(self):
        vm = ns(config=ns(extraConfig=[ns(key="other", value="x")]))
        assert VmFacts(vm).vnc_facts() == {"vnc": {}}


class TestVmFactsTpm:
    def test_tpm_present_and_provider(self):
        vm = ns(
            summary=ns(config=ns(tpmPresent=True)),
            config=ns(keyId=ns(providerId=ns(id="provider-1"))),
        )
        assert VmFacts(vm).tpm_facts() == {
            "tpm_info": {"tpm_present": True, "provider_id": "provider-1"}
        }

    def test_tpm_absent(self):
        vm = ns(summary=ns(config=ns()), config=ns(keyId=None))
        assert VmFacts(vm).tpm_facts() == {
            "tpm_info": {"tpm_present": None, "provider_id": None}
        }


class TestVmFactsHwGeneral:
    def test_hw_general_facts(self):
        vm = ns(
            config=ns(
                name="my_vm",
                uuid="p-uuid",
                template=False,
                version="vmx-19",
                hardware=ns(numCPU=4, numCoresPerSocket=2, memoryMB=8192),
            ),
            summary=ns(
                runtime=ns(powerState="poweredOn"),
                guest=ns(guestFullName="Ubuntu Linux (64-bit)", guestId="ubuntu64Guest"),
            ),
        )
        facts = VmFacts(vm).hw_general_facts()
        assert facts["module_hw"] is True
        assert facts["hw_name"] == "my_vm"
        assert facts["hw_power_status"] == "poweredOn"
        assert facts["hw_guest_full_name"] == "Ubuntu Linux (64-bit)"
        assert facts["hw_guest_id"] == "ubuntu64Guest"
        assert facts["hw_product_uuid"] == "p-uuid"
        assert facts["hw_processor_count"] == 4
        assert facts["hw_cores_per_socket"] == 2
        assert facts["hw_memtotal_mb"] == 8192
        assert facts["hw_is_template"] is False
        assert facts["hw_version"] == "vmx-19"


class TestVmFactsHwFolder:
    def test_hw_folder_facts(self, mocker):
        mocker.patch(VM + '.get_folder_path_of_vsphere_object', return_value="/dc/vm/folder")
        assert VmFacts(ns()).hw_folder_facts() == {"hw_folder": "/dc/vm/folder"}

    def test_hw_folder_facts_on_error(self, mocker):
        mocker.patch(VM + '.get_folder_path_of_vsphere_object', side_effect=Exception("boom"))
        assert VmFacts(ns()).hw_folder_facts() == {"hw_folder": None}


class TestVmFactsHwDatastore:
    def test_hw_datastore_facts(self):
        vm = ns(datastore=[ns(info=ns(name="ds1")), ns(info=ns(name="ds2"))])
        assert VmFacts(vm).hw_datastore_facts() == {"hw_datastores": ["ds1", "ds2"]}

    def test_hw_datastore_facts_empty(self):
        assert VmFacts(ns(datastore=[])).hw_datastore_facts() == {"hw_datastores": []}


class TestVmFactsHwRuntime:
    def test_hw_runtime_facts_with_cluster(self):
        cluster = mock.Mock(spec=vim.ClusterComputeResource)
        cluster.name = "my_cluster"
        host = ns(summary=ns(config=ns(name="esxi01")), parent=cluster)
        vm = ns(summary=ns(runtime=ns(host=host, dasVmProtection=ns(dasProtected=True))))
        facts = VmFacts(vm).hw_runtime_facts()
        assert facts["hw_esxi_host"] == "esxi01"
        assert facts["hw_cluster"] == "my_cluster"
        assert facts["hw_guest_ha_state"] is True

    def test_hw_runtime_facts_no_host(self):
        vm = ns(summary=ns(runtime=ns(host=None, dasVmProtection=None)))
        assert VmFacts(vm).hw_runtime_facts() == {
            "hw_esxi_host": None,
            "hw_guest_ha_state": None,
        }


class TestVmFactsHwNetworkDevice:
    def test_collects_ethernet_devices(self):
        device = ns(
            macAddress="aa:bb:cc:dd:ee:ff",
            addressType="assigned",
            deviceInfo=ns(label="Network adapter 1", summary="dvportgroup"),
            backing=ns(port=ns(portKey="pk", portgroupKey="pgk")),
        )
        guest_net = [ns(deviceConfigId=1, macAddress="aa:bb:cc:dd:ee:ff", ipAddress=["10.0.0.5"])]
        vm = ns(
            guest=ns(net=guest_net),
            config=ns(hardware=ns(device=[device])),
        )
        facts = VmFacts(vm).hw_network_device_facts()
        assert facts["hw_interfaces"] == ["eth0"]
        assert facts["hw_eth0"] == {
            "addresstype": "assigned",
            "label": "Network adapter 1",
            "macaddress": "aa:bb:cc:dd:ee:ff",
            "ipaddresses": ["10.0.0.5"],
            "macaddress_dash": "aa-bb-cc-dd-ee-ff",
            "summary": "dvportgroup",
            "portgroup_portkey": "pk",
            "portgroup_key": "pgk",
        }

    def test_skips_non_network_devices(self):
        disk = ns(deviceInfo=ns(label="Hard disk 1", summary="disk"))
        vm = ns(guest=ns(net=None), config=ns(hardware=ns(device=[disk])))
        assert VmFacts(vm).hw_network_device_facts() == {"hw_interfaces": []}


class TestSnapshotHelpers:
    def _snap(self, id_, name, children=None):
        return ns(
            id=id_,
            name=name,
            description="desc-%s" % name,
            createTime="2020-01-01T00:00:00Z",
            state="poweredOff",
            quiesced=False,
            childSnapshotList=children or [],
        )

    def test_deserialize_snapshot_obj(self):
        snap = self._snap(1, "snap1")
        assert deserialize_snapshot_obj(snap) == {
            "id": 1,
            "name": "snap1",
            "description": "desc-snap1",
            "creation_time": "2020-01-01T00:00:00Z",
            "state": "poweredOff",
            "quiesced": False,
        }

    def test_list_snapshots_recursively(self):
        child = self._snap(2, "child")
        parent = self._snap(1, "parent", children=[child])
        result = list_snapshots_recursively([parent])
        assert [s["name"] for s in result] == ["parent", "child"]

    def test_get_current_snap_obj(self):
        target = object()
        child = ns(snapshot=target, childSnapshotList=[])
        parent = ns(snapshot=object(), childSnapshotList=[child])
        found = get_current_snap_obj([parent], target)
        assert found == [child]

    def test_list_snapshots_empty_when_no_snapshot(self):
        assert list_snapshots(ns(snapshot=None)) == {}

    def test_list_snapshots_full(self):
        current = object()
        root = ns(
            id=1,
            name="root",
            description="d",
            createTime="t",
            state="poweredOff",
            quiesced=False,
            snapshot=current,
            childSnapshotList=[],
        )
        vm = ns(snapshot=ns(rootSnapshotList=[root], currentSnapshot=current))
        result = list_snapshots(vm)
        assert [s["name"] for s in result["snapshots"]] == ["root"]
        assert result["current_snapshot"]["name"] == "root"

    def test_list_snapshots_no_matching_current(self):
        root = ns(
            id=1,
            name="root",
            description="d",
            createTime="t",
            state="poweredOff",
            quiesced=False,
            snapshot=object(),
            childSnapshotList=[],
        )
        vm = ns(snapshot=ns(rootSnapshotList=[root], currentSnapshot=object()))
        result = list_snapshots(vm)
        assert result["current_snapshot"] == {}


class TestVmFactsSnapshot:
    def test_snapshot_facts_delegates_to_list_snapshots(self, mocker):
        mocker.patch(
            VM + '.list_snapshots',
            return_value={"snapshots": [{"name": "s1"}], "current_snapshot": {"name": "s1"}},
        )
        assert VmFacts(ns()).snapshot_facts() == {
            "snapshots": [{"name": "s1"}],
            "current_snapshot": {"name": "s1"},
        }

    def test_snapshot_facts_none(self, mocker):
        mocker.patch(VM + '.list_snapshots', return_value={})
        assert VmFacts(ns()).snapshot_facts() == {
            "snapshots": [],
            "current_snapshot": None,
        }

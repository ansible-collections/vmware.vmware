from __future__ import absolute_import, division, print_function
__metaclass__ = type

import sys
import pytest

from pyVmomi import vim

from ansible_collections.vmware.vmware.plugins.modules.vm_portgroup_info import (
    PortgroupInfo,
    main as module_main
)
from ansible_collections.vmware.vmware.plugins.module_utils import _network as vmware_network
from ansible_collections.vmware.vmware.plugins.module_utils.clients.pyvmomi import (
    PyvmomiClient
)
from ansible_collections.vmware.vmware.plugins.module_utils._module_rest_base import (
    ModuleRestBase
)
from ...common.utils import (
    run_module, ModuleTestCase
)
from ...common.vmware_object_mocks import (
    create_mock_vsphere_object
)

pytestmark = pytest.mark.skipif(
    sys.version_info < (2, 7), reason="requires python2.7 or higher"
)


class TestVmPortgroupInfo(ModuleTestCase):

    def _create_standard_nic(self, mocker, pg_name="pg-standard", pg_moid="network-1",
                             vlan_id=10, vswitch_name="vSwitch0", mac="00:11:22:33:44:55"):
        """
        Build a mock virtual ethernet card backed by a standard portgroup. The
        backing only exposes 'network' (no 'port') so the module treats it as a
        standard portgroup.
        """
        portgroup = mocker.Mock()
        portgroup._GetMoId.return_value = pg_moid
        portgroup.summary.name = pg_name

        pg_entry = mocker.Mock()
        pg_entry.spec.name = pg_name
        pg_entry.spec.vlanId = vlan_id
        pg_entry.spec.vswitchName = vswitch_name
        host = mocker.Mock()
        host.config.network.portgroup = [pg_entry]
        portgroup.host = [host]

        nic = mocker.Mock(spec=vim.vm.device.VirtualVmxnet3)
        nic.macAddress = mac
        nic.addressType = "assigned"
        nic.backing = mocker.Mock(spec=['network'])
        nic.backing.network = portgroup
        return nic

    def _create_dvs_nic(self, mocker, pg_name="pg-dvs", pg_moid="dvportgroup-1",
                        switch_name="dvSwitch", mac="00:aa:bb:cc:dd:ee"):
        """
        Build a mock virtual ethernet card backed by a distributed portgroup. The
        backing exposes 'port' so the module treats it as a DVS portgroup and
        looks the switch/portgroup up via the content manager.
        """
        dvs_pg = mocker.Mock()
        dvs_pg._GetMoId.return_value = pg_moid
        dvs_pg.name = pg_name
        dvs_pg.config.distributedVirtualSwitch.name = switch_name

        nic = mocker.Mock(spec=vim.vm.device.VirtualVmxnet3)
        nic.macAddress = mac
        nic.addressType = "assigned"
        nic.backing = mocker.Mock(spec=['port'])
        nic.backing.port.portgroupKey = "portgroup-key"
        nic.backing.port.switchUuid = "switch-uuid"
        return nic, dvs_pg

    def _create_vm(self, mocker, name="vm1", moid="vm-1", devices=None):
        vm = create_mock_vsphere_object(name=name, moid=moid)
        vm.config.hardware.device = devices if devices is not None else []
        return vm

    def __prepare(self, mocker, dvs_pg=None):
        self.mock_content = mocker.Mock()
        if dvs_pg is not None:
            dvs = mocker.Mock()
            dvs.LookupDvPortGroup.return_value = dvs_pg
            self.mock_content.dvSwitchManager.QueryDvsByUuid.return_value = dvs

        mocker.patch.object(
            PyvmomiClient, 'connect_to_api',
            return_value=(mocker.Mock(), self.mock_content)
        )
        # ModuleRestBase is instantiated in PortgroupInfo.__init__ but not used
        # for the info gathering logic, so stub out its connection.
        mocker.patch.object(ModuleRestBase, '__init__', return_value=None)

    def test_standard_portgroup(self, mocker):
        self.__prepare(mocker)
        vm = self._create_vm(mocker, devices=[self._create_standard_nic(mocker)])
        mocker.patch.object(PortgroupInfo, 'get_vms_using_params', return_value=[vm])

        result = run_module(module_entry=module_main, module_args=dict(name="vm1"))

        assert result["changed"] is False
        nics = result["vm_portgroup_info"]["vm1"]
        assert len(nics) == 1
        nic = nics[0]
        assert nic["type"] == "STANDARD_PORTGROUP"
        assert nic["name"] == "pg-standard"
        assert nic["vlan_id"] == "10"
        assert nic["vswitch_name"] == "vSwitch0"
        assert nic["nic_type"] == "VirtualVmxnet3"
        assert nic["nic_mac_address"] == "00:11:22:33:44:55"
        assert nic["nic_mac_type"] == "assigned"
        assert nic["port_id"] == "network-1"

    def test_distributed_portgroup(self, mocker):
        nic, dvs_pg = self._create_dvs_nic(mocker)
        self.__prepare(mocker, dvs_pg=dvs_pg)
        vm = self._create_vm(mocker, devices=[nic])
        mocker.patch.object(PortgroupInfo, 'get_vms_using_params', return_value=[vm])

        result = run_module(module_entry=module_main, module_args=dict(name="vm1"))

        assert result["changed"] is False
        nics = result["vm_portgroup_info"]["vm1"]
        assert len(nics) == 1
        nic_out = nics[0]
        assert nic_out["type"] == "DISTRIBUTED_PORTGROUP"
        assert nic_out["portgroup_name"] == "pg-dvs"
        assert nic_out["vswitch_name"] == "dvSwitch"
        assert nic_out["port_id"] == "dvportgroup-1"
        assert nic_out["nic_mac_address"] == "00:aa:bb:cc:dd:ee"

    def test_vm_with_no_devices(self, mocker):
        self.__prepare(mocker)
        vm = self._create_vm(mocker, devices=[])
        mocker.patch.object(PortgroupInfo, 'get_vms_using_params', return_value=[vm])

        result = run_module(module_entry=module_main, module_args=dict(name="vm1"))

        assert result["vm_portgroup_info"] == {"vm1": []}

    def test_vm_missing_hardware_config(self, mocker):
        self.__prepare(mocker)
        vm = create_mock_vsphere_object(name="vm1", moid="vm-1")
        # Accessing .device on a spec-restricted mock raises AttributeError,
        # which the module catches and treats as a VM with no network devices.
        vm.config.hardware = mocker.Mock(spec=[])
        mocker.patch.object(PortgroupInfo, 'get_vms_using_params', return_value=[vm])

        result = run_module(module_entry=module_main, module_args=dict(name="vm1"))

        assert result["vm_portgroup_info"] == {"vm1": []}

    def test_non_ethernet_devices_skipped(self, mocker):
        self.__prepare(mocker)
        disk = mocker.Mock(spec=vim.vm.device.VirtualDisk)
        vm = self._create_vm(mocker, devices=[disk, self._create_standard_nic(mocker)])
        mocker.patch.object(PortgroupInfo, 'get_vms_using_params', return_value=[vm])

        result = run_module(module_entry=module_main, module_args=dict(name="vm1"))

        nics = result["vm_portgroup_info"]["vm1"]
        assert len(nics) == 1
        assert nics[0]["type"] == "STANDARD_PORTGROUP"

    def test_portgroup_details_are_cached(self, mocker):
        self.__prepare(mocker)
        # Two NICs sharing the same standard portgroup should only have their
        # details looked up once thanks to the pg_map cache.
        nic1 = self._create_standard_nic(mocker)
        nic2 = self._create_standard_nic(mocker)
        shared_pg = nic1.backing.network
        nic2.backing.network = shared_pg
        vm = self._create_vm(mocker, devices=[nic1, nic2])
        mocker.patch.object(PortgroupInfo, 'get_vms_using_params', return_value=[vm])

        spy = mocker.spy(vmware_network, 'get_standard_portgroup_vlan_vswitch')

        result = run_module(module_entry=module_main, module_args=dict(name="vm1"))

        assert len(result["vm_portgroup_info"]["vm1"]) == 2
        assert spy.call_count == 1

    def test_multiple_vms(self, mocker):
        self.__prepare(mocker)
        vm1 = self._create_vm(mocker, name="vm1", moid="vm-1",
                              devices=[self._create_standard_nic(mocker)])
        vm2 = self._create_vm(mocker, name="vm2", moid="vm-2", devices=[])
        mocker.patch.object(PortgroupInfo, 'get_vms_using_params', return_value=[vm1, vm2])

        result = run_module(module_entry=module_main, module_args=dict(name="vm1"))

        assert set(result["vm_portgroup_info"].keys()) == {"vm1", "vm2"}
        assert len(result["vm_portgroup_info"]["vm1"]) == 1
        assert result["vm_portgroup_info"]["vm2"] == []

    def test_no_vms_found(self, mocker):
        self.__prepare(mocker)
        mocker.patch.object(PortgroupInfo, 'get_vms_using_params', return_value=[])

        result = run_module(module_entry=module_main, module_args=dict(name="does-not-exist"))

        assert result["vm_portgroup_info"] == {}

    def test_vm_names_param(self, mocker):
        self.__prepare(mocker)
        vm1 = self._create_vm(mocker, name="vm1", moid="vm-1",
                              devices=[self._create_standard_nic(mocker)])
        vm2 = self._create_vm(mocker, name="vm2", moid="vm-2", devices=[])

        mocker.patch.object(PortgroupInfo, 'get_folder_using_params', return_value=None)
        mocker.patch.object(
            PortgroupInfo, 'get_objs_by_name_or_moid',
            side_effect=[[vm1], [vm2]]
        )

        result = run_module(
            module_entry=module_main,
            module_args=dict(vm_names=["vm1", "vm2"])
        )

        assert set(result["vm_portgroup_info"].keys()) == {"vm1", "vm2"}
        assert len(result["vm_portgroup_info"]["vm1"]) == 1

    def test_vm_names_param_skips_missing(self, mocker):
        self.__prepare(mocker)
        vm1 = self._create_vm(mocker, name="vm1", moid="vm-1", devices=[])

        mocker.patch.object(PortgroupInfo, 'get_folder_using_params', return_value=None)
        # Second name returns no matches and should simply be skipped.
        mocker.patch.object(
            PortgroupInfo, 'get_objs_by_name_or_moid',
            side_effect=[[vm1], []]
        )

        result = run_module(
            module_entry=module_main,
            module_args=dict(vm_names=["vm1", "missing"])
        )

        assert list(result["vm_portgroup_info"].keys()) == ["vm1"]

    def test_standard_portgroup_attribute_error_fails(self, mocker):
        self.__prepare(mocker)
        nic = mocker.Mock(spec=vim.vm.device.VirtualVmxnet3)
        nic.macAddress = "00:11:22:33:44:55"
        nic.addressType = "assigned"
        nic.backing = mocker.Mock(spec=['network'])
        # A portgroup object missing the 'summary' attribute triggers the
        # AttributeError handling in get_standard_portgroup_detailed.
        portgroup = mocker.Mock(spec=['_GetMoId'])
        portgroup._GetMoId.return_value = "network-1"
        nic.backing.network = portgroup
        vm = self._create_vm(mocker, devices=[nic])
        mocker.patch.object(PortgroupInfo, 'get_vms_using_params', return_value=[vm])

        result = run_module(
            module_entry=module_main,
            module_args=dict(name="vm1"),
            expect_success=False
        )

        assert result["failed"] is True

    def test_mutually_exclusive_params(self, mocker):
        self.__prepare(mocker)

        result = run_module(
            module_entry=module_main,
            module_args=dict(name="vm1", moid="vm-1"),
            expect_success=False
        )

        assert result["failed"] is True

    def test_required_one_of_params(self, mocker):
        self.__prepare(mocker)

        result = run_module(
            module_entry=module_main,
            module_args=dict(),
            expect_success=False
        )

        assert result["failed"] is True

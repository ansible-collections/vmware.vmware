from __future__ import absolute_import, division, print_function
__metaclass__ = type

import sys
import pytest

from ansible_collections.vmware.vmware.plugins.inventory.vms import (
    VmInventoryHost,
    InventoryModule
)
pytestmark = pytest.mark.skipif(
    sys.version_info < (2, 7), reason="requires python2.7 or higher"
)


class TestVmInventoryHost():
    def test_guest_ip(self):
        vm = VmInventoryHost()
        assert vm.guest_ip == ""

        vm.properties['guest'] = {'ipAddress': '10.10.10.10'}
        assert vm.guest_ip == '10.10.10.10'

    def test_cluster(self, mocker):
        vm = VmInventoryHost()
        assert vm.cluster == dict(name='', moid='')

        vm.object = mocker.Mock()
        vm._cluster = None
        vm.object.summary.runtime.host.parent.name = 'Cluster1'
        vm.object.summary.runtime.host.parent._GetMoId.return_value = '1'
        assert vm.cluster['name'] == 'Cluster1'
        assert vm.cluster['moid'] == '1'
        # check again to make sure the value is cached
        vm.object = None
        assert vm.cluster['name'] == 'Cluster1'
        assert vm.cluster['moid'] == '1'

    def test_esxi_host(self, mocker):
        vm = VmInventoryHost()
        assert vm.esxi_host == dict(name='', moid='')

        vm.object = mocker.Mock()
        vm._esxi_host = None
        vm.object.summary.runtime.host.name = 'esxi-host-1'
        vm.object.summary.runtime.host._GetMoId.return_value = '1'
        assert vm.esxi_host['name'] == 'esxi-host-1'
        assert vm.esxi_host['moid'] == '1'
        # check again to make sure the value is cached
        vm.object = None
        assert vm.esxi_host['name'] == 'esxi-host-1'
        assert vm.esxi_host['moid'] == '1'

    def test_get_tags(self, mocker):
        vm = VmInventoryHost()
        vm.object = mocker.Mock()
        rest_client_mock = mocker.Mock()
        vm.get_tags(rest_client_mock)
        rest_client_mock.get_tags_by_vm_moid.assert_called_once()


class TestInventoryModule():
    def test_parse_properties_param(self, mocker):
        inventory_module = InventoryModule()
        inventory_module.get_option = mocker.Mock(side_effect=(['name', 'config', 'guest'], False))
        assert inventory_module.parse_properties_param() == ['name', 'config', 'guest', 'config.guestId', 'summary.runtime.powerState']

        inventory_module.get_option = mocker.Mock(side_effect=('name', False))
        assert inventory_module.parse_properties_param() == ['name', 'config.guestId', 'summary.runtime.powerState']

        inventory_module.get_option = mocker.Mock(side_effect=(['all'], False))
        assert inventory_module.parse_properties_param() == []

        inventory_module.get_option = mocker.Mock(side_effect=('name', True))
        assert inventory_module.parse_properties_param() == ['name', 'config.guestId', 'summary.runtime.powerState', 'summary.runtime.host']

    def test_populate_from_vcenter(self, mocker):
        inventory_module = InventoryModule()
        mocker.patch.object(inventory_module, 'parse_properties_param', return_value=[
            'name', 'config', 'guest', 'config.guestId', 'summary.runtime.powerState'
        ])
        mocker.patch.object(inventory_module, 'initialize_pyvmomi_client', side_effect=setattr(inventory_module, 'pyvmomi_client', mocker.Mock()))
        mocker.patch.object(inventory_module, 'initialize_rest_client', side_effect=setattr(inventory_module, 'rest_client', mocker.Mock()))
        mocker.patch.object(
            inventory_module,
            'iter_inventory_sources',
            return_value=[(mocker.Mock(), mocker.Mock())],
        )
        mocker.patch.object(
            VmInventoryHost,
            'create_from_vcenter_object',
            return_value=VmInventoryHost(),
        )
        mocker.patch.object(inventory_module, 'add_tags_to_object_properties')
        mocker.patch.object(inventory_module, 'set_inventory_hostname')
        mocker.patch.object(inventory_module, 'add_host_object_from_vcenter_to_inventory', return_value={})

        mocker.patch.object(inventory_module, 'get_option', side_effect=(False, False, False))
        inventory_module.populate_from_vcenter()

        assert inventory_module.iter_inventory_sources.call_count == 1
        assert inventory_module.set_inventory_hostname.call_count == 1
        assert inventory_module.add_host_object_from_vcenter_to_inventory.call_count == 1

    def test_populate_from_vcenter_with_gather_tags(self, mocker):
        inventory_module = InventoryModule()
        mocker.patch.object(inventory_module, 'parse_properties_param', return_value=['name'])
        mocker.patch.object(
            inventory_module,
            'initialize_pyvmomi_client',
            side_effect=setattr(inventory_module, 'pyvmomi_client', mocker.Mock()),
        )
        mocker.patch.object(inventory_module, 'initialize_rest_client')
        mocker.patch.object(
            inventory_module,
            'iter_inventory_sources',
            return_value=[(mocker.Mock(), mocker.Mock())],
        )
        vm = VmInventoryHost()
        mocker.patch.object(VmInventoryHost, 'create_from_vcenter_object', return_value=vm)
        mocker.patch.object(inventory_module, 'add_tags_to_object_properties')
        mocker.patch.object(inventory_module, 'set_inventory_hostname')
        mocker.patch.object(inventory_module, 'add_host_object_from_vcenter_to_inventory')
        inventory_module.get_option = mocker.Mock(side_effect=lambda key: key == 'gather_tags')

        inventory_module.populate_from_vcenter()

        inventory_module.initialize_rest_client.assert_called_once()
        inventory_module.add_tags_to_object_properties.assert_called_once_with(vm)

    def test_populate_from_vcenter_with_gather_compute_objects(self, mocker):
        inventory_module = InventoryModule()
        mocker.patch.object(inventory_module, 'parse_properties_param', return_value=['name'])
        mocker.patch.object(
            inventory_module,
            'initialize_pyvmomi_client',
            side_effect=setattr(inventory_module, 'pyvmomi_client', mocker.Mock()),
        )
        mocker.patch.object(
            inventory_module,
            'iter_inventory_sources',
            return_value=[(mocker.Mock(), mocker.Mock())],
        )
        vm = VmInventoryHost()
        vm.properties = {}
        mocker.patch.object(VmInventoryHost, 'create_from_vcenter_object', return_value=vm)
        mocker.patch.object(VmInventoryHost, 'cluster', new_callable=mocker.PropertyMock, return_value={'name': 'c1', 'moid': '1'})
        mocker.patch.object(VmInventoryHost, 'esxi_host', new_callable=mocker.PropertyMock, return_value={'name': 'h1', 'moid': '2'})
        mocker.patch.object(inventory_module, 'set_inventory_hostname')
        mocker.patch.object(inventory_module, 'add_host_object_from_vcenter_to_inventory')
        inventory_module.get_option = mocker.Mock(side_effect=lambda key: key == 'gather_compute_objects')

        inventory_module.populate_from_vcenter()

        assert vm.properties['cluster'] == {'name': 'c1', 'moid': '1'}
        assert vm.properties['esxi_host'] == {'name': 'h1', 'moid': '2'}

# Copyright: (c) 2025, Ansible Cloud Team
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import sys

import pytest

from ansible_collections.vmware.vmware.plugins.inventory.esxi_hosts import (
    EsxiInventoryHost,
    InventoryModule,
)

pytestmark = pytest.mark.skipif(
    sys.version_info < (2, 7), reason="requires python2.7 or higher"
)


class TestEsxiInventoryHost(object):

    def test_create_from_vcenter_object_sets_management_ip(self, mocker):
        host = EsxiInventoryHost()
        mocker.patch(
            'ansible_collections.vmware.vmware.plugins.inventory.esxi_hosts.VmwareInventoryHost.create_from_vcenter_object',
            return_value=host,
        )
        mocker.patch.object(
            EsxiInventoryHost,
            'management_ip',
            new_callable=mocker.PropertyMock,
            return_value='10.0.0.5',
        )

        result = EsxiInventoryHost.create_from_vcenter_object(
            mocker.Mock(),
            ['name'],
            mocker.Mock(),
            prop_set=mocker.Mock(),
        )

        assert result.properties['management_ip'] == '10.0.0.5'


class TestEsxiInventoryModule(object):

    def test_parse_properties_param(self, mocker):
        inventory_module = InventoryModule()
        inventory_module.get_option = mocker.Mock(return_value=['name', 'capability'])

        assert inventory_module.parse_properties_param() == [
            'name',
            'capability',
            'summary.runtime.connectionState',
            'summary.runtime.powerState',
        ]

    def test_populate_from_vcenter(self, mocker):
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
        mocker.patch.object(
            EsxiInventoryHost,
            'create_from_vcenter_object',
            return_value=EsxiInventoryHost(),
        )
        mocker.patch.object(inventory_module, '_host_connection_state', return_value='connected')
        mocker.patch.object(inventory_module, 'add_tags_to_object_properties')
        mocker.patch.object(inventory_module, 'set_inventory_hostname')
        mocker.patch.object(
            inventory_module,
            'add_host_object_from_vcenter_to_inventory',
            return_value={},
        )
        inventory_module.get_option = mocker.Mock(return_value=False)

        inventory_module.populate_from_vcenter()

        assert inventory_module.iter_inventory_sources.call_count == 1
        assert EsxiInventoryHost.create_from_vcenter_object.call_count == 1

    def test_host_connection_state_from_properties(self):
        inventory_module = InventoryModule()
        esxi_host = EsxiInventoryHost()
        esxi_host.properties = {
            'summary': {
                'runtime': {
                    'connectionState': 'connected',
                },
            },
        }

        assert inventory_module._host_connection_state(esxi_host) == 'connected'

    def test_host_connection_state_from_object_fallback(self, mocker):
        inventory_module = InventoryModule()
        esxi_host = EsxiInventoryHost()
        esxi_host.properties = {}
        esxi_host.object = mocker.Mock()
        esxi_host.object.summary.runtime.connectionState = 'disconnected'

        assert inventory_module._host_connection_state(esxi_host) == 'disconnected'

    def test_populate_from_vcenter_skips_disconnected_hosts(self, mocker):
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
            return_value=[
                (mocker.Mock(), mocker.Mock()),
                (mocker.Mock(), mocker.Mock()),
            ],
        )
        mocker.patch.object(
            EsxiInventoryHost,
            'create_from_vcenter_object',
            side_effect=[EsxiInventoryHost(), EsxiInventoryHost()],
        )
        mocker.patch.object(
            inventory_module,
            '_host_connection_state',
            side_effect=['disconnected', 'connected'],
        )
        mocker.patch.object(inventory_module, 'set_inventory_hostname')
        mocker.patch.object(inventory_module, 'add_host_object_from_vcenter_to_inventory')
        inventory_module.get_option = mocker.Mock(return_value=False)

        inventory_module.populate_from_vcenter()

        assert EsxiInventoryHost.create_from_vcenter_object.call_count == 2
        inventory_module.add_host_object_from_vcenter_to_inventory.assert_called_once()

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
        mocker.patch.object(
            EsxiInventoryHost,
            'create_from_vcenter_object',
            return_value=EsxiInventoryHost(),
        )
        mocker.patch.object(inventory_module, '_host_connection_state', return_value='connected')
        mocker.patch.object(inventory_module, 'add_tags_to_object_properties')
        mocker.patch.object(inventory_module, 'set_inventory_hostname')
        mocker.patch.object(inventory_module, 'add_host_object_from_vcenter_to_inventory')
        inventory_module.get_option = mocker.Mock(side_effect=lambda key: key == 'gather_tags')

        inventory_module.populate_from_vcenter()

        inventory_module.initialize_rest_client.assert_called_once()
        inventory_module.add_tags_to_object_properties.assert_called_once()

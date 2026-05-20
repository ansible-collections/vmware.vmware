# Copyright: (c) 2025, Ansible Cloud Team
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from ansible_collections.vmware.vmware.plugins.module_utils import _facts


class _Hardware(object):
    numCPU = 4


class _Config(object):
    cpuHotAddEnabled = True
    name = 'vm-one'
    hardware = _Hardware()


class _Guest(object):
    ipAddress = '10.0.0.1'


class _VM(object):
    name = 'VM-one'
    config = _Config()
    guest = _Guest()


class TestVmwareObjToJson(object):

    def test_dotted_properties_share_top_level_jsonify(self, mocker):
        jsonify = mocker.patch(
            'ansible_collections.vmware.vmware.plugins.module_utils._facts._jsonify_vmware_object',
            side_effect=lambda obj: {
                _Config: {
                    'cpuHotAddEnabled': True,
                    'name': 'vm-one',
                    'hardware': {'numCPU': 4},
                },
                _Guest: {'ipAddress': '10.0.0.1'},
                str: obj,
            }.get(type(obj), obj),
        )

        result = _facts.vmware_obj_to_json(
            _VM(),
            ['config.cpuHotAddEnabled', 'config.name', 'config.hardware.numCPU', 'guest.ipAddress', 'name'],
        )

        assert result['config']['cpuHotAddEnabled'] is True
        assert result['config']['name'] == 'vm-one'
        assert result['config']['hardware']['numCPU'] == 4
        assert result['guest']['ipAddress'] == '10.0.0.1'
        assert jsonify.call_count == 3

    def test_properties_from_collector(self):
        class _Prop(object):
            def __init__(self, name, val):
                self.name = name
                self.val = val

        prop_set = [
            _Prop('config.cpuHotAddEnabled', True),
            _Prop('config.name', 'vm-one'),
            _Prop('guest.ipAddress', '10.0.0.1'),
            _Prop('name', 'VM-one'),
        ]

        result = _facts.properties_from_collector(prop_set)

        assert result == {
            'config': {
                'cpuHotAddEnabled': True,
                'name': 'vm-one',
            },
            'guest': {'ipAddress': '10.0.0.1'},
            'name': 'VM-one',
        }

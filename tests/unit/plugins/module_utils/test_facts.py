# Copyright: (c) 2025, Ansible Cloud Team
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import pytest

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

    def test_normalize_property_name(self):
        assert _facts._normalize_property_name('_moid') == 'moid'
        assert _facts._normalize_property_name('_VimRef') == 'vimref'
        assert _facts._normalize_property_name('name') == 'name'

    def test_jsonify_vmware_value_scalars(self):
        assert _facts._jsonify_vmware_value(None) is None
        assert _facts._jsonify_vmware_value(True) is True
        assert _facts._jsonify_vmware_value(42) == 42
        assert _facts._jsonify_vmware_value(3.14) == 3.14
        assert _facts._jsonify_vmware_value('value') == 'value'

    def test_jsonify_vmware_value_collections(self):
        assert _facts._jsonify_vmware_value([1, 'two']) == [1, 'two']
        assert _facts._jsonify_vmware_value((3, 4)) == [3, 4]
        assert _facts._jsonify_vmware_value({'a': 1, 'b': 'two'}) == {'a': 1, 'b': 'two'}

    def test_jsonify_vmware_value_long_and_binary(self):
        long_type = type('long', (int,), {})
        binary_type = type('binary', (bytes,), {})

        assert _facts._jsonify_vmware_value(long_type(99)) == 99
        assert _facts._jsonify_vmware_value(binary_type(b'abc')) == 'YWJj'

    def test_jsonify_vmware_value_long_array(self):
        long_type = type('long', (int,), {})
        long_array_type = type('long[]', (list,), {})

        assert _facts._jsonify_vmware_value(long_array_type([long_type(1), long_type(2)])) == [1, 2]

    def test_jsonify_vmware_value_datetime(self, mocker):
        datetime_type = type('datetime', (object,), {})
        iso8601 = mocker.patch('pyVmomi.Iso8601')
        iso8601.ISO8601Format.return_value = '2020-01-01T00:00:00Z'

        assert _facts._jsonify_vmware_value(datetime_type()) == '2020-01-01T00:00:00Z'

    def test_vmware_obj_to_json_normalizes_special_properties(self, mocker):
        vm = mocker.Mock()
        vm._moid = 'vm-1'
        vm._vimref = 'vim.VirtualMachine:vm-1'
        mocker.patch(
            'ansible_collections.vmware.vmware.plugins.module_utils._facts._jsonify_vmware_object',
            return_value='jsonified',
        )

        result = _facts.vmware_obj_to_json(vm, ['_moid', '_vimref'])

        assert result == {'moid': 'jsonified', 'vimref': 'jsonified'}

    def test_vmware_obj_to_json_missing_property_raises(self):
        with pytest.raises(AttributeError, match="Property 'missing' not found."):
            _facts.vmware_obj_to_json(_VM(), ['missing'])

    def test_jsonify_vmware_value_vim_type_non_data_object(self):
        vim_type = type('vim.test.Object', (object,), {})
        vim_object = vim_type()

        assert _facts._jsonify_vmware_value(vim_object) == str(vim_object)

    def test_jsonify_vmware_value_unknown_type_uses_to_text(self):
        unknown_type = type('custom_type', (object,), {})
        unknown_object = unknown_type()

        assert _facts._jsonify_vmware_value(unknown_object) == str(unknown_object)

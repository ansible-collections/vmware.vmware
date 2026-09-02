from __future__ import absolute_import, division, print_function
__metaclass__ = type

import types

import pytest

from ansible_collections.vmware.vmware.plugins.module_utils.facts import _converters


CONVERTERS = 'ansible_collections.vmware.vmware.plugins.module_utils.facts._converters'


def ns(**kwargs):
    """Small helper to build attribute containers that raise AttributeError for missing attrs."""
    return types.SimpleNamespace(**kwargs)


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


class TestVmwareObjToJson:
    def test_dotted_properties_share_top_level_jsonify(self, mocker):
        jsonify = mocker.patch(
            CONVERTERS + '._jsonify_vmware_object',
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

        result = _converters.vmware_obj_to_json(
            _VM(),
            ['config.cpuHotAddEnabled', 'config.name', 'config.hardware.numCPU', 'guest.ipAddress', 'name'],
        )

        assert result['config']['cpuHotAddEnabled'] is True
        assert result['config']['name'] == 'vm-one'
        assert result['config']['hardware']['numCPU'] == 4
        assert result['guest']['ipAddress'] == '10.0.0.1'
        # config parent, guest parent, and the bare 'name' property -> 3 conversions
        assert jsonify.call_count == 3

    def test_no_properties_dumps_whole_object(self, mocker):
        mocker.patch(CONVERTERS + '._jsonify_vmware_object', return_value={'everything': True})
        assert _converters.vmware_obj_to_json(_VM()) == {'everything': True}

    def test_normalizes_special_properties(self, mocker):
        vm = mocker.Mock()
        vm._moid = 'vm-1'
        vm._vimref = 'vim.VirtualMachine:vm-1'
        mocker.patch(CONVERTERS + '._jsonify_vmware_object', return_value='jsonified')

        result = _converters.vmware_obj_to_json(vm, ['_moid', '_vimref'])

        assert result == {'moid': 'jsonified', 'vimref': 'jsonified'}

    def test_missing_property_raises_attribute_error(self):
        with pytest.raises(AttributeError, match="Property 'missing' not found."):
            _converters.vmware_obj_to_json(_VM(), ['missing'])


class TestPropertiesFromCollector:
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

        result = _converters.properties_from_collector(prop_set)

        assert result == {
            'config': {
                'cpuHotAddEnabled': True,
                'name': 'vm-one',
            },
            'guest': {'ipAddress': '10.0.0.1'},
            'name': 'VM-one',
        }


class TestNormalizePropertyName:
    def test_normalize_property_name(self):
        assert _converters._normalize_property_name('_moid') == 'moid'
        assert _converters._normalize_property_name('_VimRef') == 'vimref'
        assert _converters._normalize_property_name('name') == 'name'


class TestJsonifyVmwareValue:
    def test_scalars(self):
        assert _converters._jsonify_vmware_value(None) is None
        assert _converters._jsonify_vmware_value(True) is True
        assert _converters._jsonify_vmware_value(42) == 42
        assert _converters._jsonify_vmware_value(3.14) == 3.14
        assert _converters._jsonify_vmware_value('value') == 'value'

    def test_collections(self):
        assert _converters._jsonify_vmware_value([1, 'two']) == [1, 'two']
        assert _converters._jsonify_vmware_value((3, 4)) == [3, 4]
        assert _converters._jsonify_vmware_value({'a': 1, 'b': 'two'}) == {'a': 1, 'b': 'two'}

    def test_long_and_binary(self):
        long_type = type('long', (int,), {})
        binary_type = type('binary', (bytes,), {})

        assert _converters._jsonify_vmware_value(long_type(99)) == 99
        assert _converters._jsonify_vmware_value(binary_type(b'abc')) == 'YWJj'

    def test_long_array(self):
        long_type = type('long', (int,), {})
        long_array_type = type('long[]', (list,), {})

        assert _converters._jsonify_vmware_value(long_array_type([long_type(1), long_type(2)])) == [1, 2]

    def test_datetime(self, mocker):
        datetime_type = type('datetime', (object,), {})
        iso8601 = mocker.patch('pyVmomi.Iso8601')
        iso8601.ISO8601Format.return_value = '2020-01-01T00:00:00Z'

        assert _converters._jsonify_vmware_value(datetime_type()) == '2020-01-01T00:00:00Z'

    def test_vim_type_non_data_object(self):
        vim_type = type('vim.test.Object', (object,), {})
        vim_object = vim_type()

        assert _converters._jsonify_vmware_value(vim_object) == str(vim_object)

    def test_unknown_type_uses_to_text(self):
        unknown_type = type('custom_type', (object,), {})
        unknown_object = unknown_type()

        assert _converters._jsonify_vmware_value(unknown_object) == str(unknown_object)


class TestDeepmergeDicts:
    def test_merges_nested_without_clobbering(self):
        d = {'a': {'b': 1}, 'keep': True}
        u = {'a': {'c': 2}, 'd': 3}
        assert _converters.deepmerge_dicts(d, u) == {
            'a': {'b': 1, 'c': 2},
            'keep': True,
            'd': 3,
        }

    def test_scalar_overwrites(self):
        assert _converters.deepmerge_dicts({'a': 1}, {'a': 2}) == {'a': 2}


class TestExtractObjectAttributesToDict:
    def test_converts_values_to_strings_and_recurses(self):
        obj = ns(name='x', count=5, nested=ns(inner='y'))
        assert _converters.extract_object_attributes_to_dict(obj) == {
            'name': 'x',
            'count': '5',
            'nested': {'inner': 'y'},
        }

    def test_keeps_primitives_when_not_converting(self):
        obj = ns(count=5, flag=True)
        assert _converters.extract_object_attributes_to_dict(obj, convert_to_strings=False) == {
            'count': 5,
            'flag': True,
        }

    def test_skips_underscore_attributes(self):
        obj = types.SimpleNamespace()
        obj.public = 'a'
        obj._private = 'b'
        assert _converters.extract_object_attributes_to_dict(obj) == {'public': 'a'}


class TestExtractDottedPropertyToDict:
    def test_nested_dict(self):
        data = {'hardware': {'numCPU': 4}, 'name': 'x'}
        assert _converters.extract_dotted_property_to_dict(data, 'hardware.numCPU') == {
            'hardware': {'numCPU': 4}
        }

    def test_terminal_key(self):
        assert _converters.extract_dotted_property_to_dict({'numCPU': 4}, 'numCPU') == {'numCPU': 4}

    def test_list_of_dicts(self):
        data = [{'x': {'y': 1}}, {'x': {'y': 2}}]
        assert _converters.extract_dotted_property_to_dict(data, 'x.y') == {
            'x': [{'y': 1}, {'y': 2}]
        }


class TestFlattenDict:
    def test_flattens_nested_keys(self):
        assert _converters.flatten_dict({'foo': {'bar': 1}, 'baz': 2}) == {
            'foo.bar': 1,
            'baz': 2,
        }

    def test_custom_separator(self):
        assert _converters.flatten_dict({'foo': {'bar': 1}}, separator='/') == {'foo/bar': 1}

    def test_empty_nested_dict_kept_as_value(self):
        assert _converters.flatten_dict({'foo': {}}) == {'foo': {}}


class TestSerializeSpec:
    def test_serializes_scalars_and_none(self):
        spec = ns(label='hello', count=5, missing=None)
        result = _converters.serialize_spec(spec)
        assert result['label'] == 'hello'
        assert result['count'] == 5
        assert result['missing'] is None

    def test_skips_callables(self):
        spec = ns(label='hello')
        spec.do_thing = lambda: 'nope'
        result = _converters.serialize_spec(spec)
        assert result == {'label': 'hello'}

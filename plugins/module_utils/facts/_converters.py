# -*- coding: utf-8 -*-

# Copyright: (c) 2023, Ansible Eco Content Team (github.com/eco-ansible-content)
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

# Note: This utility is considered private, and can only be referenced from inside the vmware.vmware collection.
#       It may be made public at a later date

from __future__ import absolute_import, division, print_function
__metaclass__ = type

import base64
import json

try:
    from pyVmomi import vim, VmomiJSONEncoder
except ImportError:
    pass

from ansible.module_utils.common.text.converters import to_text
from collections.abc import Mapping


def serialize_spec(clonespec):
    """Serialize a clonespec or a relocation spec"""
    data = {}
    attrs = dir(clonespec)
    attrs = [x for x in attrs if not x.startswith('_')]
    for x in attrs:
        xo = getattr(clonespec, x)
        if callable(xo):
            continue
        xt = type(xo)
        if xo is None:
            data[x] = None
        elif isinstance(xo, vim.vm.ConfigSpec):
            data[x] = serialize_spec(xo)
        elif isinstance(xo, vim.vm.RelocateSpec):
            data[x] = serialize_spec(xo)
        elif isinstance(xo, vim.vm.device.VirtualDisk):
            data[x] = serialize_spec(xo)
        elif isinstance(xo, vim.vm.device.VirtualDeviceSpec.FileOperation):
            data[x] = to_text(xo)
        elif isinstance(xo, vim.Description):
            data[x] = {
                'dynamicProperty': serialize_spec(xo.dynamicProperty),
                'dynamicType': serialize_spec(xo.dynamicType),
                'label': serialize_spec(xo.label),
                'summary': serialize_spec(xo.summary),
            }
        elif hasattr(xo, 'name'):
            data[x] = to_text(xo) + ':' + to_text(xo.name)
        elif isinstance(xo, vim.vm.ProfileSpec):
            pass
        elif issubclass(xt, list):
            data[x] = []
            for xe in xo:
                data[x].append(serialize_spec(xe))
        elif issubclass(xt, (str, int, float, bool)):
            if issubclass(xt, int):
                data[x] = int(xo)
            else:
                data[x] = to_text(xo)
        elif issubclass(xt, bool):
            data[x] = xo
        elif issubclass(xt, dict):
            data[to_text(x)] = {}
            for k, v in xo.items():
                k = to_text(k)
                data[x][k] = serialize_spec(v)
        else:
            data[x] = str(xt)

    return data


#
# Conversion to JSON
#
def deepmerge_dicts(d, u):
    """
    Deep merges u into d.

    Credit:
        https://bit.ly/2EDOs1B (stackoverflow question 3232943)
    License:
        cc-by-sa 3.0 (https://creativecommons.org/licenses/by-sa/3.0/)

    Args:
        - d (dict): dict to merge into
        - u (dict): dict to merge into d

    Returns:
        dict, with u merged into d
    """
    for k, v in u.items():
        if isinstance(v, Mapping):
            d[k] = deepmerge_dicts(d.get(k, {}), v)
        else:
            d[k] = v
    return d


def extract_object_attributes_to_dict(obj, convert_to_strings=True):
    """
    Takes the attribute key/values from a object and puts them in a dict. Nested attributes
    and their hierarchy is preserved. Optionally all values are converted to strings
    Args:
      obj: the object your want to export to a dict
      convert_to_strings: If true, all values will be converted to strings instead of other primitives
    """
    output_dict = {}

    for attr_key, attr_val in vars(obj).items():
        if not attr_key.startswith('_'):
            if hasattr(attr_val, '__dict__') and not isinstance(attr_val, str):
                output_dict[attr_key] = extract_object_attributes_to_dict(attr_val)
            else:
                output_dict[attr_key] = str(attr_val) if convert_to_strings else attr_val

    return output_dict


def extract_dotted_property_to_dict(data, remainder):
    """
    This is used to break down dotted properties for extraction.

    Args:
        - data (dict): result of _jsonify on a property
        - remainder: the remainder of the dotted property to select

    Return:
        dict
    """
    result = dict()
    if '.' not in remainder:
        result[remainder] = data[remainder]
        return result
    key, remainder = remainder.split('.', 1)
    if isinstance(data, list):
        temp_ds = []
        for i in range(len(data)):
            temp_ds.append(extract_dotted_property_to_dict(data[i][key], remainder))
        result[key] = temp_ds
    else:
        result[key] = extract_dotted_property_to_dict(data[key], remainder)
    return result


def _jsonify_vmware_object(obj):
    """
    Convert an object from pyVmomi into JSON.

    Args:
        - obj (object): vim object

    Return:
        dict
    """
    return json.loads(json.dumps(obj, cls=VmomiJSONEncoder.VmomiJSONEncoder,
                                 sort_keys=True, strip_dynamic=True))


def _normalize_property_name(prop):
    if prop.lower() == '_moid':
        return 'moid'
    if prop.lower() == '_vimref':
        return 'vimref'
    return prop


def _jsonify_vmware_value(vim_prop):
    """
    Convert a single pyVmomi property value to JSON-compatible Python types.
    Uses _jsonify_vmware_object for vim DataObject values; scalars and enums are converted directly.
    """
    if vim_prop is None:
        return None

    prop_type = type(vim_prop).__name__
    if prop_type in ('bool', 'int', 'float', 'str', 'NoneType'):
        return vim_prop

    if prop_type == 'datetime':
        from pyVmomi import Iso8601
        return Iso8601.ISO8601Format(vim_prop)

    if prop_type == 'long':
        return int(vim_prop)

    if prop_type == 'long[]':
        return [int(x) for x in vim_prop]

    if isinstance(vim_prop, (list, tuple)):
        return [_jsonify_vmware_value(item) for item in vim_prop]

    if isinstance(vim_prop, Mapping):
        return {key: _jsonify_vmware_value(value) for key, value in vim_prop.items()}

    if prop_type.startswith(("vim", "vmodl", "Link")):
        try:
            from pyVmomi.VmomiSupport import DataObject
        except ImportError:
            return _jsonify_vmware_object(vim_prop)
        if isinstance(vim_prop, DataObject):
            return _jsonify_vmware_object(vim_prop)
        return str(vim_prop)

    if prop_type == 'binary':
        return to_text(base64.b64encode(vim_prop))

    return to_text(vim_prop)


def _merge_dotted_property(result, prop_name, value):
    prop_dict = _jsonify_vmware_value(value)
    for key in reversed(prop_name.split('.')):
        prop_dict = {key: prop_dict}
    deepmerge_dicts(result, prop_dict)


def properties_from_collector(prop_set):
    """
    Convert a PropertyCollector propSet into the nested dict used by inventory hostvars.
    """
    result = dict()
    for prop in prop_set:
        _merge_dotted_property(result, prop.name, prop.val)
    return result


def vmware_obj_to_json(obj, properties=None):
    """
    Convert a vSphere (pyVmomi) Object into JSON.  This is a deep
    transformation.  The list of properties is optional - if not
    provided then all properties are deeply converted.  The resulting
    JSON is sorted to improve human readability.

    Dotted properties under the same top-level name share one parent fetch
    and JSON conversion per top-level key.

    Args:
        - obj (object): vim object
        - properties (list, optional): list of properties following
            the property collector specification, for example:
            ["config.hardware.memoryMB", "name", "overallStatus"]
            default is a complete object dump, which can be large

    Return:
        dict
    """
    if not properties:
        return _jsonify_vmware_object(obj)

    result = {}
    jsonified_parents = {}

    for prop in properties:
        try:
            if '.' in prop:
                key, remainder = prop.split('.', 1)
                if key not in jsonified_parents:
                    jsonified_parents[key] = _jsonify_vmware_object(getattr(obj, key))
                tmp = {key: extract_dotted_property_to_dict(jsonified_parents[key], remainder)}
                deepmerge_dicts(result, tmp)
            else:
                prop_name = _normalize_property_name(prop)
                result[prop_name] = _jsonify_vmware_object(getattr(obj, prop))
        except (AttributeError, KeyError) as exc:
            raise AttributeError("Property '%s' not found." % prop) from exc

    return result


def flatten_dict(dictionary, separator=".", parent_key=""):
    """
    Changes nested dictionary keys to be their dot notation versions, so the dictionary
    only has one level of depth.
    For example {"foo":{"bar":1}} would become {"foo.bar":1}
    Args:
        dictionary: dict, The original dictionary
        separator: str, A character to use to separate keys once they are flattened
        parent_key: str, Used as part of the recursion inside this method.
    Returns:
        dict
    """
    new_dict_items = []
    for k, v in dictionary.items():
        new_key = parent_key + separator + k if parent_key else k
        if v and isinstance(v, dict):
            new_dict_items.extend(
                flatten_dict(dictionary=v, separator=separator, parent_key=new_key)
                .items()
            )
        else:
            new_dict_items.append((new_key, v))
    return dict(new_dict_items)

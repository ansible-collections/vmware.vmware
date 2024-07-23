# -*- coding: utf-8 -*-

# Copyright: (c) 2023, Ansible Cloud Team (@ansible-collections)
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function
__metaclass__ = type

import json
import os

PYVMOMI_IMP_ERR = None
try:
    from pyVmomi import vim, VmomiSupport
except ImportError:
    pass

from ansible.module_utils._text import to_text
from ansible.module_utils.six import integer_types, string_types, iteritems
import ansible.module_utils.common._collections_compat as collections_compat
from ansible_collections.vmware.vmware.plugins.module_utils.vmware_folder_paths import get_folder_path_of_vm


def _get_vm_prop(vm, attributes):
    """Safely get a property or return None"""
    result = vm
    for attribute in attributes:
        try:
            result = getattr(result, attribute)
        except (AttributeError, IndexError):
            return None
    return result


def gather_vm_facts(content, vm):
    """ Gather facts from vim.VirtualMachine object. """
    facts = {
        'module_hw': True,
        'hw_name': vm.config.name,
        'hw_power_status': vm.summary.runtime.powerState,
        'hw_guest_full_name': vm.summary.guest.guestFullName,
        'hw_guest_id': vm.summary.guest.guestId,
        'hw_product_uuid': vm.config.uuid,
        'hw_processor_count': vm.config.hardware.numCPU,
        'hw_cores_per_socket': vm.config.hardware.numCoresPerSocket,
        'hw_memtotal_mb': vm.config.hardware.memoryMB,
        'hw_interfaces': [],
        'hw_datastores': [],
        'hw_files': [],
        'hw_esxi_host': None,
        'hw_guest_ha_state': None,
        'hw_is_template': vm.config.template,
        'hw_folder': None,
        'hw_version': vm.config.version,
        'instance_uuid': vm.config.instanceUuid,
        'guest_tools_status': _get_vm_prop(vm, ('guest', 'toolsRunningStatus')),
        'guest_tools_version': _get_vm_prop(vm, ('guest', 'toolsVersion')),
        'guest_question': json.loads(json.dumps(vm.summary.runtime.question, cls=VmomiSupport.VmomiJSONEncoder,
                                                sort_keys=True, strip_dynamic=True)),
        'guest_consolidation_needed': vm.summary.runtime.consolidationNeeded,
        'ipv4': None,
        'ipv6': None,
        'annotation': vm.config.annotation,
        'customvalues': {},
        'snapshots': [],
        'current_snapshot': None,
        'vnc': {},
        'moid': vm._moId,
        'vimref': "vim.VirtualMachine:%s" % vm._moId,
        'advanced_settings': {},
    }

    # facts that may or may not exist
    if vm.summary.runtime.host:
        try:
            host = vm.summary.runtime.host
            facts['hw_esxi_host'] = host.summary.config.name
            facts['hw_cluster'] = host.parent.name if host.parent and isinstance(host.parent, vim.ClusterComputeResource) else None

        except vim.fault.NoPermission:
            # User does not have read permission for the host system,
            # proceed without this value. This value does not contribute or hamper
            # provisioning or power management operations.
            pass
    if vm.summary.runtime.dasVmProtection:
        facts['hw_guest_ha_state'] = vm.summary.runtime.dasVmProtection.dasProtected

    datastores = vm.datastore
    for ds in datastores:
        facts['hw_datastores'].append(ds.info.name)

    try:
        files = vm.config.files
        layout = vm.layout
        if files:
            facts['hw_files'] = [files.vmPathName]
            for item in layout.snapshot:
                for snap in item.snapshotFile:
                    if 'vmsn' in snap:
                        facts['hw_files'].append(snap)
            for item in layout.configFile:
                facts['hw_files'].append(os.path.join(os.path.dirname(files.vmPathName), item))
            for item in vm.layout.logFile:
                facts['hw_files'].append(os.path.join(files.logDirectory, item))
            for item in vm.layout.disk:
                for disk in item.diskFile:
                    facts['hw_files'].append(disk)
    except Exception:
        pass

    facts['hw_folder'] = get_folder_path_of_vm(vm)

    cfm = content.customFieldsManager
    # Resolve custom values
    for value_obj in vm.summary.customValue:
        kn = value_obj.key
        if cfm is not None and cfm.field:
            for f in cfm.field:
                if f.key == value_obj.key:
                    kn = f.name
                    # Exit the loop immediately, we found it
                    break

        facts['customvalues'][kn] = value_obj.value

    # Resolve advanced settings
    for advanced_setting in vm.config.extraConfig:
        facts['advanced_settings'][advanced_setting.key] = advanced_setting.value

    net_dict = {}
    vmnet = _get_vm_prop(vm, ('guest', 'net'))
    if vmnet:
        for device in vmnet:
            if device.deviceConfigId > 0:
                net_dict[device.macAddress] = list(device.ipAddress)

    if vm.guest.ipAddress:
        if ':' in vm.guest.ipAddress:
            facts['ipv6'] = vm.guest.ipAddress
        else:
            facts['ipv4'] = vm.guest.ipAddress

    ethernet_idx = 0
    for entry in vm.config.hardware.device:
        if not hasattr(entry, 'macAddress'):
            continue

        if entry.macAddress:
            mac_addr = entry.macAddress
            mac_addr_dash = mac_addr.replace(':', '-')
        else:
            mac_addr = mac_addr_dash = None

        if (
            hasattr(entry, "backing")
            and hasattr(entry.backing, "port")
            and hasattr(entry.backing.port, "portKey")
            and hasattr(entry.backing.port, "portgroupKey")
        ):
            port_group_key = entry.backing.port.portgroupKey
            port_key = entry.backing.port.portKey
        else:
            port_group_key = None
            port_key = None

        factname = 'hw_eth' + str(ethernet_idx)
        facts[factname] = {
            'addresstype': entry.addressType,
            'label': entry.deviceInfo.label,
            'macaddress': mac_addr,
            'ipaddresses': net_dict.get(entry.macAddress, None),
            'macaddress_dash': mac_addr_dash,
            'summary': entry.deviceInfo.summary,
            'portgroup_portkey': port_key,
            'portgroup_key': port_group_key,
        }
        facts['hw_interfaces'].append('eth' + str(ethernet_idx))
        ethernet_idx += 1

    snapshot_facts = list_snapshots(vm)
    if 'snapshots' in snapshot_facts:
        facts['snapshots'] = snapshot_facts['snapshots']
        facts['current_snapshot'] = snapshot_facts['current_snapshot']

    facts['vnc'] = get_vnc_extraconfig(vm)

    # Gather vTPM information
    facts['tpm_info'] = {
        'tpm_present': vm.summary.config.tpmPresent if hasattr(vm.summary.config, 'tpmPresent') else None,
        'provider_id': vm.config.keyId.providerId.id if vm.config.keyId else None
    }
    return facts


def deserialize_snapshot_obj(obj):
    return {'id': obj.id,
            'name': obj.name,
            'description': obj.description,
            'creation_time': obj.createTime,
            'state': obj.state,
            'quiesced': obj.quiesced}


def list_snapshots_recursively(snapshots):
    snapshot_data = []
    for snapshot in snapshots:
        snapshot_data.append(deserialize_snapshot_obj(snapshot))
        snapshot_data = snapshot_data + list_snapshots_recursively(snapshot.childSnapshotList)
    return snapshot_data


def get_current_snap_obj(snapshots, snapob):
    snap_obj = []
    for snapshot in snapshots:
        if snapshot.snapshot == snapob:
            snap_obj.append(snapshot)
        snap_obj = snap_obj + get_current_snap_obj(snapshot.childSnapshotList, snapob)
    return snap_obj


def list_snapshots(vm):
    result = {}
    snapshot = _get_vm_prop(vm, ('snapshot',))
    if not snapshot:
        return result
    if vm.snapshot is None:
        return result

    result['snapshots'] = list_snapshots_recursively(vm.snapshot.rootSnapshotList)
    current_snapref = vm.snapshot.currentSnapshot
    current_snap_obj = get_current_snap_obj(vm.snapshot.rootSnapshotList, current_snapref)
    if current_snap_obj:
        result['current_snapshot'] = deserialize_snapshot_obj(current_snap_obj[0])
    else:
        result['current_snapshot'] = dict()
    return result


def get_vnc_extraconfig(vm):
    result = {}
    for opts in vm.config.extraConfig:
        for optkeyname in ['enabled', 'ip', 'port', 'password']:
            if opts.key.lower() == "remotedisplay.vnc." + optkeyname:
                result[optkeyname] = opts.value
    return result


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
        elif issubclass(xt, string_types + integer_types + (float, bool)):
            if issubclass(xt, integer_types):
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
    Changes:
        using collections_compat for compatibility

    Args:
        - d (dict): dict to merge into
        - u (dict): dict to merge into d

    Returns:
        dict, with u merged into d
    """
    for k, v in iteritems(u):
        if isinstance(v, collections_compat.Mapping):
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
    return json.loads(json.dumps(obj, cls=VmomiSupport.VmomiJSONEncoder,
                                 sort_keys=True, strip_dynamic=True))


def vmware_obj_to_json(obj, properties=None):
    """
    Convert a vSphere (pyVmomi) Object into JSON.  This is a deep
    transformation.  The list of properties is optional - if not
    provided then all properties are deeply converted.  The resulting
    JSON is sorted to improve human readability.

    Args:
        - obj (object): vim object
        - properties (list, optional): list of properties following
            the property collector specification, for example:
            ["config.hardware.memoryMB", "name", "overallStatus"]
            default is a complete object dump, which can be large

    Return:
        dict
    """
    result = dict()
    if properties:
        for prop in properties:
            try:
                if '.' in prop:
                    key, remainder = prop.split('.', 1)
                    tmp = dict()
                    tmp[key] = extract_dotted_property_to_dict(_jsonify_vmware_object(getattr(obj, key)), remainder)
                    deepmerge_dicts(result, tmp)
                else:
                    result[prop] = _jsonify_vmware_object(getattr(obj, prop))
                    # To match gather_vm_facts output
                    prop_name = prop
                    if prop.lower() == '_moid':
                        prop_name = 'moid'
                    elif prop.lower() == '_vimref':
                        prop_name = 'vimref'
                    result[prop_name] = result[prop]
            except (AttributeError, KeyError):
                raise AttributeError("Property '%s' not found." % prop)
    else:
        result = _jsonify_vmware_object(obj)
    return result

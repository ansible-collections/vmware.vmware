# -*- coding: utf-8 -*-

# Copyright: (c) 2023, Ansible Cloud Team (@ansible-collections)
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

# Note: This utility is considered private, and can only be referenced from inside the vmware.vmware collection.
#       It may be made public at a later date

from __future__ import absolute_import, division, print_function
__metaclass__ = type


FOLDER_TYPES = ('vm', 'host', 'network', 'datastore')


def __prepend_datacenter_and_folder_type(folder_path, datacenter_name, folder_type=None):
    """
    Formats a folder path so it is absolute, meaning it includes the datacenter name and
    type (vm, host, etc) at the start of the path. If path already starts with
    the datacenter name, nothing is added.
    Eg: rest/of/path -> datacenter name/type/rest/of/path
    """
    folder_path = folder_path.lstrip('/')
    if folder_path.startswith(datacenter_name):
        return folder_path

    if folder_type not in FOLDER_TYPES:
        raise ValueError("folder_type %s not in acceptable " % folder_type +
                         "folder type values %s" % ', '.join(FOLDER_TYPES))

    return '/'.join([datacenter_name, folder_type, folder_path])


def format_folder_path_as_vm_fq_path(folder_path, datacenter_name):
    """
    Formats a VM folder path so it is absolute, meaning it prepends
    'datacenter name/vm/' to the path if needed. If path already starts with
    the datacenter name, nothing is added.
    Eg: rest/of/path -> datacenter name/vm/rest/of/path
    """
    return __prepend_datacenter_and_folder_type(folder_path, datacenter_name, folder_type='vm')


def format_folder_path_as_host_fq_path(folder_path, datacenter_name):
    """
    Formats a host folder path so it is absolute, meaning it prepends
    'datacenter name/vm/' to the path if needed. If path already starts with
    the datacenter name, nothing is added.
    Eg: rest/of/path -> datacenter name/host/rest/of/path
    """
    return __prepend_datacenter_and_folder_type(folder_path, datacenter_name, folder_type='host')


def format_folder_path_as_network_fq_path(folder_path, datacenter_name):
    """
    Formats a network folder path so it is absolute, meaning it prepends
    'datacenter name/network/' to the path if needed. If path already starts with
    the datacenter name, nothing is added.
    Eg: rest/of/path -> datacenter name/network/rest/of/path
    """
    return __prepend_datacenter_and_folder_type(folder_path, datacenter_name, folder_type='network')


def format_folder_path_as_datastore_fq_path(folder_path, datacenter_name):
    """
    Formats a datastore folder path so it is absolute, meaning it prepends
    'datacenter name/datastore/' to the path if needed. If path already starts with
    the datacenter name, nothing is added.
    Eg: rest/of/path -> datacenter name/datastore/rest/of/path
    """
    return __prepend_datacenter_and_folder_type(folder_path, datacenter_name, folder_type='datastore')


def get_folder_path_of_vm(vm):
    """
    Find the path of virtual machine.
    Args:
        content: VMware content object
        vm_name: virtual machine managed object

    Returns: Folder of virtual machine if exists, else None

    """
    _folder = vm.parent
    folder_path = [_folder.name]
    while getattr(_folder, 'parent', None) is not None:
        _folder = _folder.parent
        if _folder.name == 'Datacenters':
            break
        folder_path += [_folder.name]

    folder_path.reverse()
    out = '/'.join(folder_path)
    if not out.startswith('/'):
        out = '/' + out
    return out

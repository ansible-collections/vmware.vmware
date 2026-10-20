# -*- coding: utf-8 -*-

# Copyright: (c) 2026, Ansible Eco Content Team (github.com/eco-ansible-content)
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

# Note: This utility is considered private, and can only be referenced from inside the vmware.vmware collection.
#       It may be made public at a later date

from __future__ import absolute_import, division, print_function
__metaclass__ = type

from abc import ABC, abstractmethod

try:
    from pyVmomi import vim
except ImportError:
    pass


class _ObjectsGatherer(ABC):
    """
    Base class for gatherers that collect facts about objects related to a VM (hosts, folders, etc).

    Each gatherer declares which VM properties it needs, how the property collector should
    traverse from the VM to the related objects, and which properties to read from those objects.
    The results of every gatherer are collected in a single property collector call, and then
    each gatherer turns the raw results into facts with add_facts.

    Attributes:
        vm_properties (list): Names of the VM properties this gatherer needs, e.g. 'runtime.host'.
            They are fetched with the VM and passed to add_facts as vm_props.
    """
    vm_properties = []

    @staticmethod
    @abstractmethod
    def traversal_specs():
        """
        Describe how the property collector should walk from a VM to the related objects.

        Returns:
            list: vim.PropertyCollector.TraversalSpec objects, rooted at vim.VirtualMachine.
        """

    @staticmethod
    @abstractmethod
    def property_specs():
        """
        Describe which properties to read from the related objects found by the traversal.

        Returns:
            list: vim.PropertyCollector.PropertySpec objects, one per managed object type.
        """

    @staticmethod
    @abstractmethod
    def add_facts(vm_info, vm_props, related_objects):
        """
        Add this gatherer's facts to a VM's info.

        Args:
            vm_info (dict): The VM's facts. Modified in place.
            vm_props (dict): Property values for the VM, keyed by property name. Contains
                at least the properties listed in vm_properties.
            related_objects (dict): Property values for all related objects, keyed by
                managed object ID (moId). Each value is a dict keyed by property name.
        """

    @staticmethod
    def _describe_related_object(ref, related_objects):
        """
        Build a short description of a related object.

        Args:
            ref: A managed object reference, or None.
            related_objects (dict): Related object properties, keyed by moId.

        Returns:
            dict: {'moid': ..., 'name': ...}, or an empty dict if ref is None or was not collected.
        """
        if ref is None or ref._moId not in related_objects:
            return {}
        return {'moid': ref._moId, 'name': related_objects[ref._moId].get('name')}

    @staticmethod
    def _find_ancestor(ref, related_objects, ancestor_type):
        """
        Walk up the parent chain from an object until an object of the given type is found.

        Each step uses 'parentFolder' (top-level vApps) if present, otherwise 'parent'. Preferring
        'parentFolder' keeps the walk in the VM folder hierarchy rather than the resource pool one.

        Args:
            ref: A managed object reference to start from, or None. Returned if it is already the right type.
            related_objects (dict): Related object properties, keyed by moId. Objects must
                have had their parent properties collected for the walk to continue.
            ancestor_type: The vim type to stop at, e.g. vim.Folder.

        Returns:
            The matching reference, or None if the chain ends without reaching one.
        """
        while ref is not None and not isinstance(ref, ancestor_type):
            props = related_objects.get(ref._moId, {})
            ref = props.get('parentFolder') or props.get('parent')
        return ref

    @staticmethod
    def _find_datacenter(ref, related_objects):
        """
        Walk up the parent chain from an object until a datacenter is found.

        Args:
            ref: A managed object reference to start from, or None.
            related_objects (dict): Related object properties, keyed by moId.

        Returns:
            The datacenter reference, or None if the chain ends without reaching one.
        """
        return _ObjectsGatherer._find_ancestor(ref, related_objects, vim.Datacenter)


class ComputeObjectsGatherer(_ObjectsGatherer):
    """
    Gathers the compute resources a VM runs on.

    Adds these facts to the VM info: 'esxi_host', 'cluster' (empty for a standalone host),
    and 'resource_pool'. Each is a dict with 'moid' and 'name', or an empty dict if unavailable.
    """
    vm_properties = ['resourcePool', 'runtime.host']

    @staticmethod
    def traversal_specs():
        """Traverse VM -> resource pool, and VM -> host -> host parent (cluster or standalone compute resource)."""
        return [
            # vm.resourcePool -> ResourcePool
            vim.PropertyCollector.TraversalSpec(
                name='vmToResourcePool', type=vim.VirtualMachine, path='resourcePool', skip=False
            ),
            # vm.runtime.host -> HostSystem
            vim.PropertyCollector.TraversalSpec(
                name='vmToHost', type=vim.VirtualMachine, path='runtime.host', skip=False,
                selectSet=[
                    # HostSystem.parent -> ClusterComputeResource (or ComputeResource for a standalone host)
                    vim.PropertyCollector.TraversalSpec(
                        name='hostToParent', type=vim.HostSystem, path='parent', skip=False),
                ]
            )
        ]

    @staticmethod
    def property_specs():
        """Collect names for resource pools, hosts, and compute resources, plus the host's parent."""
        return [
            vim.PropertyCollector.PropertySpec(type=vim.ResourcePool, pathSet=['name']),
            vim.PropertyCollector.PropertySpec(type=vim.HostSystem, pathSet=['name', 'parent']),
            # also covers clusters (subclass)
            vim.PropertyCollector.PropertySpec(type=vim.ComputeResource, pathSet=['name'])
        ]

    @staticmethod
    def add_facts(vm_info, vm_props, related_objects):
        """Set 'cluster', 'esxi_host' and 'resource_pool' on vm_info."""
        host = vm_props.get('runtime.host')
        host_parent = related_objects.get(host._moId, {}).get('parent') if host else None
        vm_info['cluster'] = {}
        if isinstance(host_parent, vim.ClusterComputeResource):
            vm_info['cluster'] = _ObjectsGatherer._describe_related_object(host_parent, related_objects)
        vm_info['esxi_host'] = _ObjectsGatherer._describe_related_object(host, related_objects)
        vm_info['resource_pool'] = _ObjectsGatherer._describe_related_object(vm_props.get('resourcePool'), related_objects)


class LocationObjectsGatherer(_ObjectsGatherer):
    """
    Gathers where a VM lives in the vCenter inventory.

    Adds these facts to the VM info: 'folder' (the closest VM folder, which for a VM in a vApp is the
    folder containing the vApp) and 'datacenter' (found by walking up the hierarchy). Each is a dict
    with 'moid' and 'name', or an empty dict if unavailable.
    """
    vm_properties = ['parent', 'parentVApp']

    @staticmethod
    def traversal_specs():
        """Traverse VM -> parent folder or vApp, then up through folders and vApps until a datacenter is reached."""
        parent_selects = [
            vim.PropertyCollector.SelectionSpec(name='folderToParent'),
            vim.PropertyCollector.SelectionSpec(name='vappToParentFolder'),
            vim.PropertyCollector.SelectionSpec(name='vappToParent'),
        ]
        return [
            # Folder.parent -> Folder | Datacenter, repeating until it reaches a Datacenter
            vim.PropertyCollector.TraversalSpec(
                name='folderToParent', type=vim.Folder, path='parent', skip=False,
                selectSet=[vim.PropertyCollector.SelectionSpec(name='folderToParent')]
            ),
            # VirtualApp.parentFolder -> Folder, for a top-level vApp
            vim.PropertyCollector.TraversalSpec(
                name='vappToParentFolder', type=vim.VirtualApp, path='parentFolder', skip=False,
                selectSet=[vim.PropertyCollector.SelectionSpec(name='folderToParent')]
            ),
            # VirtualApp.parent -> VirtualApp, for a nested vApp
            vim.PropertyCollector.TraversalSpec(
                name='vappToParent', type=vim.VirtualApp, path='parent', skip=False,
                selectSet=[
                    vim.PropertyCollector.SelectionSpec(name='vappToParentFolder'),
                    vim.PropertyCollector.SelectionSpec(name='vappToParent'),
                ]
            ),
            # vm.parent -> Folder (or vApp), then hand off to the repeating specs
            vim.PropertyCollector.TraversalSpec(
                name='vmToFolder', type=vim.VirtualMachine, path='parent', skip=False,
                selectSet=parent_selects
            ),
            # vm.parentVApp -> VirtualApp, then hand off to the repeating specs
            vim.PropertyCollector.TraversalSpec(
                name='vmToVApp', type=vim.VirtualMachine, path='parentVApp', skip=False,
                selectSet=parent_selects
            ),
        ]

    @staticmethod
    def property_specs():
        """Collect names and parents for folders and vApps, and names for datacenters."""
        return [
            vim.PropertyCollector.PropertySpec(type=vim.Folder, pathSet=['name', 'parent']),
            vim.PropertyCollector.PropertySpec(type=vim.VirtualApp, pathSet=['name', 'parent', 'parentFolder']),
            vim.PropertyCollector.PropertySpec(type=vim.Datacenter, pathSet=['name'])
        ]

    @staticmethod
    def add_facts(vm_info, vm_props, related_objects):
        """Set 'folder' and 'datacenter' on vm_info."""
        start = vm_props.get('parent') or vm_props.get('parentVApp')
        vm_info['folder'] = _ObjectsGatherer._describe_related_object(
            _ObjectsGatherer._find_ancestor(start, related_objects, vim.Folder),
            related_objects
        )
        vm_info['datacenter'] = _ObjectsGatherer._describe_related_object(
            _ObjectsGatherer._find_datacenter(start, related_objects),
            related_objects
        )

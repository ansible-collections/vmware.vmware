#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2023, Ansible Eco Content Team (github.com/eco-ansible-content)
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type


DOCUMENTATION = r"""
---
module: folder_info
short_description: Gather facts about one or more folders.
description:
    - Gather facts about VMware vSphere folders. This module does not manage folders inside of datastores.
    - Gather information about a specific folder, a set of folders, or a folder tree structure in vSphere.

author:
    - Mike Morency (@mikemorency)

options:
    datacenter:
        description:
            - The name of the datacenter to use as a starting point for the search.
            - This option is mutually exlusive with O(absolute_path) and O(moid).
            - Use this to query folders in a specific datacenter.
            - If O(recurse) is enabled, this option supports further filtering with O(name) and O(folder_type).
        type: str
        required: false
        aliases: [datacenter_name]

    absolute_path:
        description:
            - The absolute path of the folder to use as a starting point for the search.
            - This option is mutually exclusive with O(datacenter) and O(moid).
            - The leading slash is not required. For example the absolute path could be /DC-01/vm/my/folder or DC-01/vm/my/folder
            - The path does not need to include any folders. For example, '' is the default for the module if all other
              options are omitted.
            - If O(recurse) is enabled, this option supports further filtering with O(name) and O(folder_type).
        type: str
        required: false

    moid:
        description:
            - The MOID of the folder to use as a starting point for the search.
            - This option is mutually exlusive with O(absolute_path) and O(absolute_path).
            - Use this to query a specific folder.
            - If O(recurse) is enabled, this option supports further filtering with O(name) and O(folder_type).
        type: str
        required: false

    folder_type:
        description:
            - The type of folder(s) that should be included in recurse and list results.
            - This option only makes sense when traversing from the datacenter level downward.
            - The folder type controls what resources can be held in the folder, as well as the path where the folder is located.
            - For example, a folder at path /DC-01/vm/my/folder has folder type 'vm'.
        type: str
        required: false
        choices: [vm, host, datastore, network]

    name:
        description:
            - The name of the folder(s) that should be included in list results.
            - Since names are not unique, this can return multiple folders.
            - All folders in the tree will be shown in recurse results. Only folders matching the desired name will be shown
              in the list results.
        type: str
        required: false

    recurse:
        description:
            - Specify if the folder's subtree should be explored.
            - This will map the entire subtree. The performance trade off to be aware of is memory; the execution time does not
              change significantly.
            - The upper parent path is always explored.
        default: true
        type: bool

extends_documentation_fragment:
    - vmware.vmware.base_options
"""

EXAMPLES = r"""
- name: Gather the entire folder tree for a vCenter
  vmware.vmware.folder_info:
    hostname: "https://vcenter"
    username: "username"
    password: "password"
    validate_certs: false

- name: Gather information about a specific folder and its subfolders
  vmware.vmware.folder_info:
    absolute_path: /DC01/datastore/my/test/folder

- name: Gather information about a folder by MOID
  vmware.vmware.folder_info:
    moid: group-a121
    recurse: false

- name: Gather information about network folders in vCenter
  vmware.vmware.folder_info:
    folder_type: network

- name: Gather information about all vm folders named prod in a specific datacenter
  vmware.vmware.folder_info:
    folder_type: vm
    datacenter: MY-DC
    name: prod
"""

RETURN = r"""
folder:
    description:
        - Show the properties of the root or specifically queried folder.
        - If no options are provided, the module starts the search at the vSphere root folder. That folder will
          represented here.
        - If the absolute path, datacenter, or MOID options are provided, the module starts the search
          at the folder matching the parameters. That folder will be represented here instead of the
          vSphere root.
        - The properties shown here match the same properties should in the C(folders) return value.
    returned: Always
    type: dict
    sample:
        children:
            - dvportgroup-52746
            - dvportgroup-52747
            - dvs-52745
        moid: group-n52744
        name: dummy-networks
        parent: group-n7
        path: /Eco-Datacenter/network/dummy-networks
        folder_type: network

folders:
    description:
        - List of folders that matched the search parameters.
        - The list of folders here is always a subset (or an exact match) of the folders seen
          in the folder_tree, if that was returned.
        - If using the O(name) filter, only folders with the matching name will be shown.
    returned: Always
    type: list
    sample: [
        {
            "children": [
                "dvportgroup-52746",
                "dvportgroup-52747",
                "dvs-52745"
            ],
            "moid": "group-n52744",
            "name": "dummy-networks",
            "parent": "group-n7",
            "path": "/Eco-Datacenter/network/dummy-networks",
            "folder_type": "network",
        },
    ]

folder_tree:
    description:
        - A dictionary (map) showing the folder tree containing the selected folders.
        - This structure will break if you name a folder '_moid'.
        - The folder tree will reflect the actual inventory path a folder. This may include
          non-folder objects like datacenters.
    returned: always
    type: dict
    sample:
        dc01:
            _moid: group-1
            datastore:
                _moid: group-2
            host:
                _moid: group-3
            network:
                _moid: group-4
            vm:
                _moid: group-5
                "Core Infrastructure Servers":
                    _moid: group-v42
                "Staging Network Services":
                    _moid: group-v43
                VMware:
                    _moid: group-v44
"""

try:
    from pyVmomi import vim
except ImportError:
    pass

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.vmware.vmware.plugins.module_utils._module_pyvmomi_base import (
    ModulePyvmomiBase,
)
from ansible_collections.vmware.vmware.plugins.module_utils.argument_spec import (
    base_argument_spec,
)
from ansible_collections.vmware.vmware.plugins.module_utils._folder_paths import (
    get_folder_path_of_vsphere_object,
    FOLDER_TYPES,
)


def folder_types_to_datacenter_property_names(only_types: list = None):
    """
    Convert folder type names into the Datacenter object property names that hold them
    Args:
        only_types: Optional list of folder types to convert. If omitted, all folder types are converted.
    Returns:
        list(str)
    """
    out = []
    for folder_type in FOLDER_TYPES:
        if only_types and folder_type not in only_types:
            continue
        out.append("%sFolder" % folder_type)

    return out


class Node:
    def __init__(self, moid, name, parent, children):
        self.moid = moid
        self.name = name
        self.parent = parent
        self.children = children
        self._path = None

    @property
    def path(self):
        """
        The inventory path of the folder, relative to its parent
        """
        if self.is_vcenter_root():
            return ""
        if self._path:
            return self._path
        return "/" + self.name

    @path.setter
    def path(self, value):
        if not self.is_vcenter_root() and value == "/":
            self._path = "/" + self.name
        else:
            self._path = value

    @classmethod
    def from_collector_ref(cls, ref):
        """
        Build a Node from a property collector ObjectContent reference
        Args:
            ref: The ObjectContent reference returned by the property collector
        Returns:
            Node
        """
        props = {p.name: p.val for p in ref.propSet}
        try:
            children = props["childEntity"]
        except KeyError:
            children = []
            for folder_type in folder_types_to_datacenter_property_names():
                if folder_type in props:
                    children.append(props[folder_type])

        return cls(
            ref.obj._GetMoId(),
            name=props.get("name"),
            parent=props.get("parent") or props.get("parentVApp"),
            children=children,
        )

    @classmethod
    def from_object(cls, obj):
        """
        Build a Node from a live vim.Folder or vim.Datacenter object
        Args:
            obj: The vim object to convert
        Returns:
            Node
        """
        try:
            children = obj.childEntity
        except AttributeError:
            children = []
            for folder_type in folder_types_to_datacenter_property_names():
                child = getattr(obj, folder_type, None)
                if child:
                    children.append(child)

        return cls(
            obj._GetMoId(),
            name=obj.name,
            parent=getattr(obj, "parent", None) or getattr(obj, "parentVApp", None),
            children=children,
        )

    def is_vcenter_root(self):
        # if this is the special root folder of all vCenters, we dont list it
        return self.name == "Datacenters" and self.parent is None

    def to_detailed_json(self):
        """
        Convert the node into the dict format used in the module's folder/folders return values
        Returns:
            dict
        """
        return {
            "path": self.path.removeprefix("//Datacenters").removeprefix(
                "/Datacenters"
            ),
            "name": self.name,
            "moid": self.moid,
            "parent": self.parent._GetMoId() if self.parent else None,
            "children": [child._GetMoId() for child in self.children],
            "folder_type": self.guess_folder_type_from_path(),
        }

    def to_tree_leaf(self):
        """
        Convert the node into the dict format used to represent it in the folder_tree return value
        Returns:
            dict
        """
        return {self.name: {"_moid": self.moid}}

    def guess_folder_type_from_path(self):
        """
        Guess the folder type (vm, host, network, datastore, or datacenter) based on the node's path
        Returns:
            str
        """
        for path_part in self.path.split("/"):
            if not path_part:
                continue

            if path_part in FOLDER_TYPES:
                return path_part

        return "datacenter"


class VmwareFolderInfo(ModulePyvmomiBase):
    def __init__(self, module):
        super().__init__(module)
        self._folders_flat = []

    def _get_collector_search_root(self):
        """
        Determine the object the property collector should start searching from, based on the
        moid, absolute_path, or datacenter parameters
        Returns:
            The starting object/objects for the search, or None if it could not be found
        """
        if self.params["moid"]:
            return self.create_vim_object_from_moid(
                moid=self.params["moid"], vimtype=[vim.Folder]
            )

        if self.params["absolute_path"]:
            return self.get_folder_by_absolute_path(
                self.params["absolute_path"], fail_on_missing=False
            )

        folder_type = self.params["folder_type"]
        if self.params["datacenter"]:
            dc = self.get_datacenter_by_name_or_moid(
                self.params["datacenter"], fail_on_missing=False
            )

            if dc and folder_type:
                dc_prop_name = folder_types_to_datacenter_property_names(folder_type)[0]
                return [getattr(dc, dc_prop_name)]

            return dc

        return self.content.rootFolder

    def _collect_folder_properties(self, search_root, recurse: bool = True):
        """
        Grab all folders and properties in one API call, and then work with it in memory.
        This uses more memory but is much faster, and we manage memory by just pulling the
        props we need.
        """
        only_types = [self.params["folder_type"]] if self.params["folder_type"] else []
        dc_folders = folder_types_to_datacenter_property_names(only_types)

        dc_refs = self.get_managed_object_references(
            vim.Datacenter, properties=["name", "parent"] + dc_folders, recurse=recurse
        )
        folder_refs = self.get_managed_object_references(
            vim.Folder,
            properties=["name", "parent", "childEntity"],
            folder=search_root,
            recurse=recurse,
        )

        by_moid = {}
        for ref in dc_refs + folder_refs:
            node = Node.from_collector_ref(ref)
            by_moid[node.moid] = node

        if search_root is not None:
            node = Node.from_object(search_root)
            by_moid[node.moid] = node

        return by_moid

    def _add_folder_to_flat_list(self, node):
        """
        Add the node to the flat folders list if it matches the name filter and isn't the vCenter root
        Args:
            node: The Node to consider adding
        """
        if self.params["name"] and self.params["name"] != node.name:
            return
        if node.is_vcenter_root():
            return

        self._folders_flat.append(node.to_detailed_json())

    def gather_folder_info(
        self,
    ):
        """
        Gather the folder, folders, and folder_tree facts requested by the module params
        Returns:
            dict, the module's result
        """
        result = {"folder": {}, "folders": [], "folder_tree": {}}
        search_root = self._get_collector_search_root()
        if search_root is None:
            return result

        folders = self._collect_folder_properties(
            search_root, recurse=self.params["recurse"]
        )
        root_node = self._map_tree_upward(folders, search_root._GetMoId())
        root_node.path = get_folder_path_of_vsphere_object(root_node)
        result["folder_tree"] = self.format_folder_tree(folders, root_node)
        result["folders"] = self._folders_flat
        result["folder"] = folders.get(search_root._GetMoId()).to_detailed_json()
        return result

    def _map_tree_upward(self, folders, starting_moid):
        """
        Walk up the parent chain from the starting node, adding each parent to the folders map,
        until reaching the vCenter root or a node with no parent
        Args:
            folders: dict mapping moid to Node, updated in place with any newly discovered parents
            starting_moid: The moid of the node to start walking upward from
        Returns:
            Node, the top most node found while walking upward
        """
        node = folders.get(starting_moid)
        if node is None:
            return

        if node.parent:
            parent_node = Node.from_object(node.parent)
            if not parent_node.is_vcenter_root():
                folders[parent_node.moid] = parent_node
                return self._map_tree_upward(folders, parent_node.moid)

        return node

    def format_folder_tree(self, folders, node):
        """
        Recursively build the folder_tree dict for the node and its children, while also
        populating the flat folders list along the way
        Args:
            folders: dict mapping moid to Node, used to look up each child node
            node: The Node to build the tree from
        Returns:
            list, dict, the folder_tree for this node and its children
        """
        if node is None:
            return {}

        if node.is_vcenter_root():
            folder_tree = {}
        else:
            folder_tree = node.to_tree_leaf()

        self._add_folder_to_flat_list(node)
        for child in node.children:
            child_node = folders.get(child._GetMoId())
            if child_node is None:
                continue
            child_node.path = node.path + child_node.path
            child_tree = self.format_folder_tree(folders, child_node)
            if node.is_vcenter_root():
                folder_tree = {**folder_tree, **child_tree}
            else:
                folder_tree[node.name] = {**folder_tree[node.name], **child_tree}

        return folder_tree


def main():
    module = AnsibleModule(
        argument_spec={
            **base_argument_spec(),
            **dict(
                datacenter=dict(
                    type="str", required=False, aliases=["datacenter_name"]
                ),
                folder_type=dict(
                    type="str",
                    choices=["vm", "host", "network", "datastore"],
                    required=False,
                ),
                moid=dict(type="str", required=False),
                name=dict(type="str", required=False),
                absolute_path=dict(type="str", required=False),
                recurse=dict(type="bool", default=True),
            ),
        },
        supports_check_mode=True,
        mutually_exclusive=[
            ("absolute_path", "datacenter", "moid"),
        ],
    )

    folder_info = VmwareFolderInfo(module)
    result = folder_info.gather_folder_info()
    module.exit_json(**result)


if __name__ == "__main__":
    main()

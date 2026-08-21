# -*- coding: utf-8 -*-

# Copyright: (c) 2025, Ansible Cloud Team (@ansible-collections)
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

# Note: This utility is considered private, and can only be referenced from inside the vmware.vmware collection.
#       It may be made public at a later date

from __future__ import absolute_import, division, print_function
__metaclass__ = type


# A VM's snapshots are returned by vCenter as a tree. Reading vm.snapshot fetches the entire
# hierarchy in a single property read: vm.snapshot.rootSnapshotList holds the root snapshots (a VM
# can have more than one independent chain), and each node's childSnapshotList holds its children,
# already populated. The helpers below therefore only walk in-memory data objects and never make
# additional calls to vCenter.


def serialize_snapshot_obj_to_json(snapshot_tree, parent_id=None):
    """
    Convert a single VirtualMachineSnapshotTree node into a JSON-serializable dict.
    The dict includes RV(child_ids) and RV(parent_id) so a flattened list of snapshots can
    still be walked as a tree. A snapshot tree node knows its children but not its parent, so
    parent_id must be supplied by the caller (see list_snapshots_recursively); it is None for
    root snapshots or whenever the parent is not known to the caller.
    Args:
        snapshot_tree: A VirtualMachineSnapshotTree node, or None
        parent_id: The ID of this snapshot's parent, or None
    Returns:
        A dict describing the snapshot, or an empty dict if snapshot_tree is falsy
    """
    if not snapshot_tree:
        return dict()
    return {
        'id': snapshot_tree.id,
        'name': snapshot_tree.name,
        'description': snapshot_tree.description,
        'creation_time': snapshot_tree.createTime,
        'state': snapshot_tree.state,
        'quiesced': snapshot_tree.quiesced,
        'parent_id': parent_id,
        'child_ids': [child.id for child in snapshot_tree.childSnapshotList],
    }


def get_snapshot_by_identifier_recursively(snapshot_trees, snap_identifier):
    """
    Search a snapshot tree for the first snapshot whose name or ID matches snap_identifier.
    The entire tree is walked, including sibling branches, so a match is found regardless
    of where it sits in the hierarchy.
    Args:
        snapshot_trees: A list of VirtualMachineSnapshotTree nodes (e.g. rootSnapshotList)
        snap_identifier: The snapshot name (str) or ID (int) to look for
    Returns:
        The matching VirtualMachineSnapshotTree node, or None if not found
    """
    for snapshot_tree in snapshot_trees:
        if snap_identifier in (snapshot_tree.id, snapshot_tree.name):
            return snapshot_tree
        child_match = get_snapshot_by_identifier_recursively(
            snapshot_tree.childSnapshotList, snap_identifier
        )
        if child_match:
            return child_match
    return None


def get_snapshot_tree_by_snapshot_ref(snapshot_trees, snapshot_ref, parent_id=None):
    """
    Find the snapshot tree node whose managed snapshot object matches snapshot_ref. This is
    typically used to resolve vm.snapshot.currentSnapshot (a managed object reference) to the
    corresponding tree node so its metadata can be read. The matched node's parent ID is
    returned alongside it so it can be serialized with the same tree-walking metadata as the
    flattened snapshot list.
    Args:
        snapshot_trees: A list of VirtualMachineSnapshotTree nodes (e.g. rootSnapshotList)
        snapshot_ref: A VirtualMachineSnapshot managed object reference to match against
        parent_id: The ID of the parent of the nodes in snapshot_trees (used internally
                   during recursion), or None for the root snapshots
    Returns:
        A (node, parent_id) tuple for the match, or (None, None) if not found
    """
    for snapshot_tree in snapshot_trees:
        if snapshot_tree.snapshot == snapshot_ref:
            return snapshot_tree, parent_id
        child_match, child_parent_id = get_snapshot_tree_by_snapshot_ref(
            snapshot_tree.childSnapshotList, snapshot_ref, parent_id=snapshot_tree.id
        )
        if child_match:
            return child_match, child_parent_id
    return None, None


def list_snapshots_recursively(snapshot_trees, parent_id=None):
    """
    Flatten an entire snapshot tree into a list of serialized snapshot dicts, in depth-first
    order (each node immediately followed by its descendants). Each dict carries parent_id and
    child_ids, so the flattened list can be reassembled into a tree by ID.
    Args:
        snapshot_trees: A list of VirtualMachineSnapshotTree nodes (e.g. rootSnapshotList)
        parent_id: The ID of the parent of the nodes in snapshot_trees (used internally
                   during recursion), or None for the root snapshots
    Returns:
        A list of dicts as produced by serialize_snapshot_obj_to_json
    """
    snapshots = []
    for snapshot_tree in snapshot_trees:
        snapshots.append(serialize_snapshot_obj_to_json(snapshot_tree, parent_id=parent_id))
        snapshots.extend(
            list_snapshots_recursively(
                snapshot_tree.childSnapshotList,
                parent_id=snapshot_tree.id
            )
        )
    return snapshots

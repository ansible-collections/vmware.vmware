# -*- coding: utf-8 -*-

# Copyright: (c) 2026, Ansible Eco Content Team (github.com/eco-ansible-content)
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

# Note: This utility is considered private, and can only be referenced from inside the vmware.vmware collection.
#       It may be made public at a later date
"""
A VM's snapshots are returned by vCenter as a tree. Reading vm.snapshot fetches the entire
hierarchy in a single property read: vm.snapshot.rootSnapshotList holds the root snapshots (a VM
can have more than one independent chain), and each node's childSnapshotList holds its children,
already populated. The helpers below therefore only walk in-memory data objects and never make
additional calls to vCenter.
"""


def serialize_snapshot_obj_to_json(snapshot_tree, parent_id=None):
    """
    Convert a single VirtualMachineSnapshotTree node into a JSON-serializable dict.
    The dict includes child_ids and parent_id so a flattened list of snapshots can
    still be walked as a tree.
    Args:
        snapshot_tree: A VirtualMachineSnapshotTree node, or None
        parent_id: The ID of this snapshot's parent, or None
    Returns:
        A dict describing the snapshot, or an empty dict if snapshot_tree is falsy
    """
    if not snapshot_tree:
        return {}
    return {
        "id": snapshot_tree.id,
        "name": snapshot_tree.name,
        "description": snapshot_tree.description,
        "creation_time": snapshot_tree.createTime,
        "state": snapshot_tree.state,
        "quiesced": snapshot_tree.quiesced,
        "parent_id": parent_id,
        "child_ids": [child.id for child in snapshot_tree.childSnapshotList],
    }


def flatten_snapshot_tree(snapshot_trees, parent_id=None):
    """
    Walk a snapshot hierarchy depth-first and return a flat list of serialized snapshot dicts.
    Each node is immediately followed by its descendants. The parent_id recorded on each node
    lets the flat list still be read as a tree; it is None for the root snapshots.
    Only in-memory data objects are walked, so no additional calls are made to vCenter.
    Args:
        snapshot_trees: A list of VirtualMachineSnapshotTree nodes (e.g. rootSnapshotList)
        parent_id: The ID of the parent of the given nodes, or None for root snapshots
    Returns:
        A flat list of serialized snapshot dicts in depth-first order
    """
    flat = []
    for snapshot_tree in snapshot_trees:
        flat.append(serialize_snapshot_obj_to_json(snapshot_tree, parent_id=parent_id))
        flat.extend(
            flatten_snapshot_tree(
                snapshot_tree.childSnapshotList, parent_id=snapshot_tree.id
            )
        )
    return flat


def build_nested_snapshot_tree(snapshot_trees, parent_id=None):
    """
    Walk a snapshot hierarchy and return a dict keyed by snapshot ID. Each value is a serialized
    snapshot dict plus a children key holding the same keyed-dict structure for that snapshot's
    children. The top level holds the given nodes (e.g. a VM's root snapshots).
    Only in-memory data objects are walked, so no additional calls are made to vCenter.
    Args:
        snapshot_trees: A list of VirtualMachineSnapshotTree nodes (e.g. rootSnapshotList)
        parent_id: The ID of the parent of the given nodes, or None for root snapshots
    Returns:
        A dict keyed by snapshot ID, each value a serialized snapshot dict with a 'children' key
    """
    tree = {}
    for snapshot_tree in snapshot_trees:
        node = serialize_snapshot_obj_to_json(snapshot_tree, parent_id=parent_id)
        node["children"] = build_nested_snapshot_tree(
            snapshot_tree.childSnapshotList, parent_id=snapshot_tree.id
        )
        tree[snapshot_tree.id] = node
    return tree


def get_snapshot_by_identifier_recursively(
    snapshot_trees: list, snap_name: str = None, snap_id: int = None, snap_ref=None
):
    """
    Search a snapshot tree for the first snapshot matching any of the given identifiers. The
    entire tree is walked depth-first, including sibling branches, so a match is found regardless
    of where it sits in the hierarchy. Only in-memory data objects are walked (comparing a snapshot
    reference is a MoRef comparison, not a dereference), so no additional calls are made to vCenter.
    Exactly one identifier must be supplied; the identifiers are semantically distinct, so matching
    on more than one at a time is ambiguous and not allowed.
    Args:
        snapshot_trees: A list of VirtualMachineSnapshotTree nodes (e.g. rootSnapshotList)
        snap_name: The name of the snapshot to find, or None to not match on name
        snap_id: The ID of the snapshot to find, or None to not match on ID
        snap_ref: The managed VirtualMachineSnapshot object to find (e.g. currentSnapshot),
                  or None to not match on reference
    Returns:
        The matching VirtualMachineSnapshotTree node, or None if not found
    Raises:
        ValueError: If not exactly one of snap_name, snap_id, or snap_ref is supplied
    """
    if len([i for i in (snap_name, snap_id, snap_ref) if i is not None]) != 1:
        raise ValueError(
            "Exactly one identifier parameter (snap_name, snap_id, or snap_ref) is "
            "required when using get_snapshot_by_identifier_recursively"
        )

    for snapshot_tree in snapshot_trees:
        if (
            snap_id == snapshot_tree.id
            or snap_name == snapshot_tree.name
            or snap_ref == snapshot_tree.snapshot
        ):
            return snapshot_tree

        child_match = get_snapshot_by_identifier_recursively(
            snapshot_tree.childSnapshotList,
            snap_name=snap_name,
            snap_id=snap_id,
            snap_ref=snap_ref,
        )

        if child_match:
            return child_match

    return None

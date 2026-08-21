from __future__ import absolute_import, division, print_function
__metaclass__ = type

import pytest

import ansible_collections.vmware.vmware.plugins.module_utils._vm_snapshot as vm_snapshot


class MockSnapshotTree:
    """
    Minimal stand-in for a pyVmomi VirtualMachineSnapshotTree node. Only the attributes
    the helpers under test actually read are populated, and childSnapshotList is walked in
    memory, so no vCenter calls are involved.
    """
    def __init__(self, snap_id, name, children=None, snapshot=None):
        self.id = snap_id
        self.name = name
        self.description = "%s description" % name
        self.createTime = "2024-12-24T15:27:37.041577+00:00"
        self.state = "poweredOff"
        self.quiesced = False
        self.childSnapshotList = children or []
        # A real node carries a managed VirtualMachineSnapshot MoRef here. A unique sentinel
        # per node is enough to exercise reference matching.
        self.snapshot = snapshot if snapshot is not None else object()


def build_sample_tree():
    """
    Build a two-chain hierarchy:

        snap1 (1)
          └─ snap2 (2)
               └─ snap3 (3)
        snap4 (4)
    """
    snap3 = MockSnapshotTree(3, "snap3")
    snap2 = MockSnapshotTree(2, "snap2", children=[snap3])
    snap1 = MockSnapshotTree(1, "snap1", children=[snap2])
    snap4 = MockSnapshotTree(4, "snap4")
    return [snap1, snap2, snap3, snap4]


class TestSerializeSnapshotObjToJson:

    def test_returns_empty_dict_for_falsy_input(self):
        assert vm_snapshot.serialize_snapshot_obj_to_json(None) == {}
        assert vm_snapshot.serialize_snapshot_obj_to_json([]) == {}

    def test_serializes_all_fields(self):
        _, snap2, _, _ = build_sample_tree()
        result = vm_snapshot.serialize_snapshot_obj_to_json(snap2, parent_id=1)

        assert result == {
            "id": 2,
            "name": "snap2",
            "description": "snap2 description",
            "creation_time": "2024-12-24T15:27:37.041577+00:00",
            "state": "poweredOff",
            "quiesced": False,
            "parent_id": 1,
            "child_ids": [3],
        }

    def test_parent_id_defaults_to_none(self):
        snap1, _, _, _ = build_sample_tree()
        result = vm_snapshot.serialize_snapshot_obj_to_json(snap1)
        assert result["parent_id"] is None

    def test_child_ids_empty_for_leaf(self):
        _, _, snap3, _ = build_sample_tree()
        result = vm_snapshot.serialize_snapshot_obj_to_json(snap3)
        assert result["child_ids"] == []


class TestFlattenSnapshotTree:

    def test_empty_input_returns_empty_list(self):
        assert vm_snapshot.flatten_snapshot_tree([]) == []

    def test_depth_first_order(self):
        snap1, snap2, snap3, snap4 = build_sample_tree()
        flat = vm_snapshot.flatten_snapshot_tree([snap1, snap4])

        assert [node["id"] for node in flat] == [1, 2, 3, 4]

    def test_parent_ids_track_hierarchy(self):
        snap1, snap2, snap3, snap4 = build_sample_tree()
        flat = vm_snapshot.flatten_snapshot_tree([snap1, snap4])

        by_id = {node["id"]: node for node in flat}
        assert by_id[1]["parent_id"] is None
        assert by_id[2]["parent_id"] == 1
        assert by_id[3]["parent_id"] == 2
        assert by_id[4]["parent_id"] is None

    def test_child_ids_recorded(self):
        snap1, _, _, _ = build_sample_tree()
        flat = vm_snapshot.flatten_snapshot_tree([snap1])
        by_id = {node["id"]: node for node in flat}
        assert by_id[1]["child_ids"] == [2]
        assert by_id[3]["child_ids"] == []


class TestBuildNestedSnapshotTree:

    def test_empty_input_returns_empty_dict(self):
        assert vm_snapshot.build_nested_snapshot_tree([]) == {}

    def test_nested_structure_keyed_by_id(self):
        snap1, snap2, snap3, snap4 = build_sample_tree()
        tree = vm_snapshot.build_nested_snapshot_tree([snap1, snap4])

        assert set(tree.keys()) == {1, 4}
        assert tree[1]["name"] == "snap1"
        assert tree[1]["parent_id"] is None

        children_of_1 = tree[1]["children"]
        assert set(children_of_1.keys()) == {2}
        assert children_of_1[2]["parent_id"] == 1

        children_of_2 = children_of_1[2]["children"]
        assert set(children_of_2.keys()) == {3}
        assert children_of_2[3]["parent_id"] == 2
        assert children_of_2[3]["children"] == {}

    def test_leaf_has_empty_children(self):
        _, _, _, snap4 = build_sample_tree()
        tree = vm_snapshot.build_nested_snapshot_tree([snap4])
        assert tree[4]["children"] == {}


class TestGetSnapshotByIdentifierRecursively:

    def test_find_by_name(self):
        snap1, _, snap3, _ = build_sample_tree()
        match = vm_snapshot.get_snapshot_by_identifier_recursively(
            [snap1], snap_name="snap3"
        )
        assert match is snap3

    def test_find_by_id(self):
        snap1, snap2, _, _ = build_sample_tree()
        match = vm_snapshot.get_snapshot_by_identifier_recursively(
            [snap1], snap_id=2
        )
        assert match is snap2

    def test_find_by_ref(self):
        snap1, _, snap3, _ = build_sample_tree()
        match = vm_snapshot.get_snapshot_by_identifier_recursively(
            [snap1], snap_ref=snap3.snapshot
        )
        assert match is snap3

    def test_find_root_node(self):
        snap1, _, _, _ = build_sample_tree()
        match = vm_snapshot.get_snapshot_by_identifier_recursively(
            [snap1], snap_id=1
        )
        assert match is snap1

    def test_searches_sibling_chains(self):
        snap1, _, _, snap4 = build_sample_tree()
        match = vm_snapshot.get_snapshot_by_identifier_recursively(
            [snap1, snap4], snap_name="snap4"
        )
        assert match is snap4

    def test_returns_none_when_not_found(self):
        snap1, _, _, _ = build_sample_tree()
        match = vm_snapshot.get_snapshot_by_identifier_recursively(
            [snap1], snap_name="does-not-exist"
        )
        assert match is None

    def test_empty_tree_returns_none(self):
        match = vm_snapshot.get_snapshot_by_identifier_recursively(
            [], snap_id=1
        )
        assert match is None

    def test_raises_when_no_identifier_supplied(self):
        snap1, _, _, _ = build_sample_tree()
        with pytest.raises(ValueError):
            vm_snapshot.get_snapshot_by_identifier_recursively([snap1])

    def test_raises_when_multiple_identifiers_supplied(self):
        snap1, _, _, _ = build_sample_tree()
        with pytest.raises(ValueError):
            vm_snapshot.get_snapshot_by_identifier_recursively(
                [snap1], snap_name="snap1", snap_id=1
            )

    def test_zero_id_is_a_valid_identifier(self):
        # snap_id=0 is falsy but is still a supplied identifier and must be matched.
        snap0 = MockSnapshotTree(0, "snap0")
        match = vm_snapshot.get_snapshot_by_identifier_recursively(
            [snap0], snap_id=0
        )
        assert match is snap0

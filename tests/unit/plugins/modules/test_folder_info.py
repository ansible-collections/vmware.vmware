from __future__ import absolute_import, division, print_function

__metaclass__ = type

import sys
import pytest
from unittest import mock

from ansible_collections.vmware.vmware.plugins.modules.folder_info import (
    VmwareFolderInfo,
    Node,
    folder_types_to_datacenter_property_names,
    main as module_main,
)
from ansible_collections.vmware.vmware.plugins.module_utils.clients.pyvmomi import (
    PyvmomiClient,
)
from ...common.utils import run_module, ModuleTestCase
from ...common.vmware_object_mocks import MockFolder, MockDatacenter

pytestmark = pytest.mark.skipif(
    sys.version_info < (2, 7), reason="requires python2.7 or higher"
)


def mock_prop(name, value):
    out = mock.Mock()
    out.name = name
    out.val = value
    return out


def test_folder_types_folder_types_to_datacenter_property_names():
    res = folder_types_to_datacenter_property_names()
    assert len(res) == 4
    assert "vmFolder" in res

    res = folder_types_to_datacenter_property_names(["vm", "network"])
    assert len(res) == 2
    assert "vmFolder" in res
    assert "networkFolder" in res


class TestNode:
    @pytest.fixture
    def node(self):
        return Node("1", "test", MockFolder(), [])

    def test_path(self, node):
        assert node.path == f"/{node.name}"

        node.path = "/"
        assert node.path == f"/{node.name}"

        node.path = "foo"
        assert node.path == "foo"

        node.parent = None
        node.name = "Datacenters"
        assert node.path == ""

    def test_object_init(self):
        obj = MockDatacenter()
        del obj.childEntity
        node = Node.from_object(obj)
        assert len(node.children) == 4

        obj.childEntity = ["1", "2", "3"]
        node = Node.from_object(obj)
        assert len(node.children) == 3

    def test_collector_ref_init(self):
        ref = mock.Mock()
        ref.propSet = []
        ref.obj = MockFolder()
        node = Node.from_collector_ref(ref)
        assert node.children == []

        prop1 = mock_prop("childEntity", ["1"])
        prop2 = mock_prop("parent", 1)
        ref.propSet = [prop1, prop2]
        node = Node.from_collector_ref(ref)
        assert node.children[0] == "1"
        assert node.parent == 1

    def test_to_detailed_json(self, node):
        node.path = "/Datacenters/foo/vm"
        out = node.to_detailed_json()
        assert out["path"] == "/foo/vm"
        assert out["folder_type"] == "vm"

    def test_to_tree_leaf(self, node):
        out = node.to_tree_leaf()
        assert out.get(node.name) == {"_moid": node.moid}

    def test_guess_folder_type_from_path(self, node):
        node.path = "/"
        assert node.guess_folder_type_from_path() == "datacenter"
        node.path = "/foo/barvm/network/"
        assert node.guess_folder_type_from_path() == "network"


class TestFolderInfo(ModuleTestCase):

    def __prepare_folder_tree(self):
        self.root = MockFolder(name="Datacenters", moid="100")
        self.mock_content.rootFolder = self.root

        self.dc = MockDatacenter(name="dc", moid="101")
        self.dc.parent = self.root
        self.root.childEntity = [self.dc]

        self.folder = MockFolder(name="test", moid="102")
        self.folder.parent = self.dc.vmFolder
        self.dc.vmFolder.childEntity = [self.folder]

    def __prepare(self, mocker):
        self.mock_content = mocker.Mock()
        mocker.patch.object(
            PyvmomiClient,
            "connect_to_api",
            return_value=(mocker.Mock(), self.mock_content),
        )
        self.__prepare_folder_tree()
        mock_dc_ref = mocker.Mock()
        mock_dc_ref.obj = self.dc
        mock_dc_ref.propSet = [
            mock_prop("parent", self.dc.parent),
            mock_prop("name", self.dc.name),
        ]
        mock_folder_ref = mocker.Mock()
        mock_folder_ref.obj = self.folder
        mock_folder_ref.propSet = [
            mock_prop("parent", self.folder.parent),
            mock_prop("name", self.folder.name),
            mock_prop("childEntity", self.folder.childEntity),
        ]

        mocker.patch.object(
            PyvmomiClient,
            "get_managed_object_references",
            side_effect=[[mock_dc_ref], [mock_folder_ref]],
        )
        mocker.patch.object(
            VmwareFolderInfo,
            "get_folder_by_absolute_path",
            return_value=self.folder,
        )

    def test_no_params(self, mocker):
        self.__prepare(mocker)
        module_args = dict()

        result = run_module(module_entry=module_main, module_args=module_args)

        assert result["changed"] is False
        assert result["folders"]
        assert result["folder_tree"]

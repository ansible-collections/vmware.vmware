from __future__ import absolute_import, division, print_function

__metaclass__ = type

import pytest
from unittest.mock import Mock
from unittest.mock import patch

from ansible_collections.vmware.vmware.plugins.module_utils.vm.services._placement import (
    VmPlacement,
    vm_placement_argument_spec,
)


def test_vm_placement_argument_spec():
    """Test vm_placement_argument_spec function."""
    arg_spec = vm_placement_argument_spec()
    assert arg_spec != {}

    arg_spec = vm_placement_argument_spec(["folder", "cluster", "foo"])
    assert arg_spec != {}
    assert "folder" not in arg_spec
    assert "cluster" not in arg_spec


class TestVmPlacement:
    """Test cases for VmPlacement class."""

    @pytest.fixture
    @patch(
        "ansible_collections.vmware.vmware.plugins.module_utils.vm.services._placement.ModulePyvmomiBase.__init__"
    )
    def placement(self, mock_init):
        module = Mock()
        module.params = {
            "hostname": "hostname",
            "username": "username",
            "password": "password",
            "datacenter": "datacenter",
            "datastore": "datastore",
            "resource_pool": "resource_pool",
            "esxi_host": "esxi_host",
            "folder": "folder",
            "cluster": "cluster",
            "datastore_cluster": "datastore_cluster",
        }
        vp = VmPlacement(module)
        vp.module = module
        vp.params = module.params
        return vp

    def test_get_datacenter(self, placement):
        """Test get_datacenter method."""
        placement.get_datacenter_by_name_or_moid = Mock(return_value=1)

        dc = placement.get_datacenter()
        placement.get_datacenter_by_name_or_moid.assert_called_once_with(
            placement.params["datacenter"], fail_on_missing=True
        )
        assert dc == 1

        placement.get_datacenter_by_name_or_moid.reset_mock()
        dc = placement.get_datacenter("datacenter")
        placement.get_datacenter_by_name_or_moid.assert_not_called()
        assert dc == 1

    def test_get_datastore(self, placement):
        """Test get_datastore method."""
        # Test with specific datastore
        placement.get_datastore_by_name_or_moid = Mock(return_value="datastore1")

        ds = placement.get_datastore()
        placement.get_datastore_by_name_or_moid.assert_called_once_with(
            placement.params["datastore"], fail_on_missing=True
        )
        assert ds == "datastore1"

        # Test with datastore cluster
        placement._datastore = None  # Reset cache
        placement.params["datastore"] = None
        placement.params["datastore_cluster"] = "dsc1"

        mock_dsc = Mock()
        mock_dsc.childEntity = ["ds1", "ds2"]
        placement.get_datastore_cluster_by_name_or_moid = Mock(return_value=mock_dsc)
        placement.get_datastore_with_max_free_space = Mock(return_value="ds1")
        placement.get_datacenter = Mock(return_value="dc1")

        ds = placement.get_datastore()
        placement.get_datastore_cluster_by_name_or_moid.assert_called_once_with(
            "dsc1", fail_on_missing=True, datacenter="dc1"
        )
        placement.get_datastore_with_max_free_space.assert_called_once_with(
            ["ds1", "ds2"]
        )
        assert ds == "ds1"

        # check cache
        placement.get_datastore_cluster_by_name_or_moid.reset_mock()
        ds = placement.get_datastore()
        placement.get_datastore_cluster_by_name_or_moid.assert_not_called()
        assert ds == "ds1"

    def test_get_resource_pool(self, placement):
        """Test get_resource_pool method."""
        # Test with specific resource pool
        placement.get_resource_pool_by_name_or_moid = Mock(return_value="rp1")

        rp = placement.get_resource_pool()
        placement.get_resource_pool_by_name_or_moid.assert_called_once_with(
            placement.params["resource_pool"], fail_on_missing=True
        )
        assert rp == "rp1"

        # Test with cluster (using default resource pool)
        placement._resource_pool = None  # Reset cache
        placement.params["resource_pool"] = None
        placement.params["cluster"] = "cluster1"

        mock_cluster = Mock()
        mock_cluster.resourcePool = "default_rp"
        placement.get_cluster_by_name_or_moid = Mock(return_value=mock_cluster)
        placement.get_datacenter = Mock(return_value="dc1")

        rp = placement.get_resource_pool()
        placement.get_cluster_by_name_or_moid.assert_called_once_with(
            "cluster1", fail_on_missing=True, datacenter="dc1"
        )
        assert rp == "default_rp"

        # check cache
        placement.get_cluster_by_name_or_moid.reset_mock()
        rp = placement.get_resource_pool()
        placement.get_cluster_by_name_or_moid.assert_not_called()
        assert rp == "default_rp"

    def test_get_folder(self, placement):
        """Test get_folder method."""
        # Test with specific folder
        placement.get_folder_by_absolute_path = Mock(return_value="folder1")

        folder = placement.get_folder()
        placement.get_folder_by_absolute_path.assert_called_once()
        assert folder == "folder1"

        # Test without folder (uses default)
        placement._folder = None  # Reset cache
        placement.params["folder"] = None

        folder = placement.get_folder()
        placement.get_folder_by_absolute_path.assert_called()
        assert folder == "folder1"

        # check cache
        placement.get_folder_by_absolute_path.reset_mock()
        folder = placement.get_folder()
        placement.get_folder_by_absolute_path.assert_not_called()
        assert folder == "folder1"

    def test_get_esxi_host(self, placement):
        """Test get_esxi_host method."""
        # Test with specific host
        placement.get_esxi_host_by_name_or_moid = Mock(return_value="host1")

        host = placement.get_esxi_host()
        placement.get_esxi_host_by_name_or_moid.assert_called_once_with(
            placement.params["esxi_host"], fail_on_missing=True
        )
        assert host == "host1"

        # Test without host (returns None)
        placement._esxi_host = None  # Reset cache
        placement.params["esxi_host"] = None
        placement.get_esxi_host_by_name_or_moid.reset_mock()

        host = placement.get_esxi_host()
        placement.get_esxi_host_by_name_or_moid.assert_not_called()
        assert host is None

    def test_get_resource_pool_no_params(self, placement):
        """Test get_resource_pool when no parameters are provided."""
        placement.params["resource_pool"] = None
        placement.params["cluster"] = None

        rp = placement.get_resource_pool()
        assert rp is None

    def test_get_datastore_no_params(self, placement):
        """Test get_datastore when no parameters are provided."""
        placement.params["datastore"] = None
        placement.params["datastore_cluster"] = None

        ds = placement.get_datastore()
        assert ds is None

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import pytest
from unittest.mock import Mock
from unittest.mock import patch

from ansible_collections.vmware.vmware.plugins.module_utils.vm.services._vsphere_object_cache import (
    VsphereObjectCache
)

from .....common.vmware_object_mocks import create_mock_vsphere_object


class TestVsphereObjectCache:
    """Test cases for VsphereObjectCache class."""

    @pytest.fixture
    @patch(
        "ansible_collections.vmware.vmware.plugins.module_utils.vm.services._vsphere_object_cache.ModulePyvmomiBase.__init__"
    )
    def object_cache(self, mock_init):
        module = Mock()
        module.params = {
            "hostname": "hostname",
            "username": "username",
            "password": "password",
        }
        obj_cache = VsphereObjectCache(module)
        obj_cache.module = module
        obj_cache.params = module.params
        return obj_cache

    def test_get_portgroup(self, object_cache):
        """Test get_portgroup method."""
        mock_network = create_mock_vsphere_object()
        object_cache.get_dvs_portgroup_by_name_or_moid = Mock(return_value=None)
        object_cache.get_standard_portgroup_by_name_or_moid = Mock(return_value=mock_network)

        output = object_cache.get_portgroup(mock_network.name)
        object_cache.get_dvs_portgroup_by_name_or_moid.assert_called_once()
        object_cache.get_standard_portgroup_by_name_or_moid.assert_called_once()
        assert output is mock_network

        object_cache.get_dvs_portgroup_by_name_or_moid.reset_mock()
        object_cache.get_standard_portgroup_by_name_or_moid.reset_mock()
        output = object_cache.get_portgroup(mock_network.name)
        object_cache.get_dvs_portgroup_by_name_or_moid.assert_not_called()
        object_cache.get_standard_portgroup_by_name_or_moid.assert_not_called()
        assert output is mock_network

        output = object_cache.get_portgroup(mock_network._moid)
        object_cache.get_dvs_portgroup_by_name_or_moid.assert_not_called()
        object_cache.get_standard_portgroup_by_name_or_moid.assert_not_called()
        assert output is mock_network

    def test_get_portgroup_branch(self, object_cache):
        """Test get_portgroup method."""
        mock_network = create_mock_vsphere_object()
        object_cache.get_dvs_portgroup_by_name_or_moid = Mock(return_value=mock_network)
        object_cache.get_standard_portgroup_by_name_or_moid = Mock(return_value=None)

        output = object_cache.get_portgroup(mock_network.name)
        object_cache.get_dvs_portgroup_by_name_or_moid.assert_called_once()
        object_cache.get_standard_portgroup_by_name_or_moid.assert_not_called()
        assert output is mock_network

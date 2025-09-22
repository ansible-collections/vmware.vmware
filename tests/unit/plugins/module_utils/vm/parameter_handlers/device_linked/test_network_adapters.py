from __future__ import absolute_import, division, print_function

__metaclass__ = type

import pytest
from unittest.mock import Mock, patch

from ansible_collections.vmware.vmware.plugins.module_utils.vm.parameter_handlers.device_linked._network_adapters import (
    E1000NetworkAdapterParameterHandler,
    E1000eNetworkAdapterParameterHandler,
    Pcnet32NetworkAdapterParameterHandler,
    Vmxnet2NetworkAdapterParameterHandler,
    Vmxnet3NetworkAdapterParameterHandler,
    SriovNetworkAdapterParameterHandler,
)


class TestAbstractNetworkAdapterParameterHandler:
    @pytest.fixture
    def parameter_handler(self):
        """Create a E1000NetworkAdapterParameterHandler instance for testing."""
        error_handler = Mock()
        params = {}
        change_set = Mock()
        vm = Mock()
        device_tracker = Mock()
        vsphere_object_cache = Mock()

        return E1000NetworkAdapterParameterHandler(
            error_handler, params, change_set, vm, device_tracker, vsphere_object_cache
        )

    def test_verify_parameter_constraints(self, parameter_handler):
        """Test verify_parameter_constraints method."""
        parameter_handler._parse_network_adapter_params = Mock()
        parameter_handler.verify_parameter_constraints()
        parameter_handler._parse_network_adapter_params.assert_called_once()
        assert parameter_handler.adapters == []

        parameter_handler._parse_network_adapter_params = Mock(side_effect=ValueError("test"))
        parameter_handler.error_handler.fail_with_parameter_error = Mock(side_effect=ValueError("test"))
        with pytest.raises(ValueError, match="test"):
            parameter_handler.verify_parameter_constraints()
        parameter_handler.error_handler.fail_with_parameter_error.assert_called_once()

    def test_parse_network_adapter_params(self, parameter_handler):
        """Test parse_network_adapter_params method."""
        parameter_handler.params = {f"{parameter_handler.HANDLER_NAME}s": [{"network": "test"}]}
        parameter_handler._parse_network_adapter_params()
        assert len(parameter_handler.adapters) == 1

        parameter_handler.vsphere_object_cache.get_portgroup = Mock(side_effect=ValueError("test"))
        parameter_handler.error_handler.fail_with_parameter_error = Mock(side_effect=ValueError("test"))
        with pytest.raises(ValueError, match="test"):
            parameter_handler._parse_network_adapter_params()
        parameter_handler.error_handler.fail_with_parameter_error.assert_called_once()

    def test_populate_config_spec_with_parameters(self, parameter_handler):
        """Test populate_config_spec_with_parameters method."""
        parameter_handler.change_set.objects_to_add = [Mock()]
        parameter_handler.change_set.objects_to_update = [Mock()]
        parameter_handler.populate_config_spec_with_parameters(Mock())
        assert len(parameter_handler.change_set.objects_to_add) == 1
        assert len(parameter_handler.change_set.objects_to_update) == 1

    def test_compare_live_config_with_desired_config(self, parameter_handler):
        """Test compare_live_config_with_desired_config method."""
        adapter = Mock()
        adapter._live_object = None
        parameter_handler.adapters = [adapter]
        parameter_handler.change_set.objects_to_add = []
        parameter_handler.change_set.objects_to_update = []
        parameter_handler.change_set.objects_in_sync = []
        parameter_handler.compare_live_config_with_desired_config()
        assert len(parameter_handler.change_set.objects_to_add) == 1
        assert len(parameter_handler.change_set.objects_to_update) == 0
        assert len(parameter_handler.change_set.objects_in_sync) == 0

        parameter_handler.change_set.objects_to_add = []
        parameter_handler.change_set.objects_to_update = []
        parameter_handler.change_set.objects_in_sync = []
        adapter._live_object = Mock()
        adapter.differs_from_live_object = Mock(return_value=True)
        parameter_handler.compare_live_config_with_desired_config()
        assert len(parameter_handler.change_set.objects_to_add) == 0
        assert len(parameter_handler.change_set.objects_to_update) == 1
        assert len(parameter_handler.change_set.objects_in_sync) == 0

        parameter_handler.change_set.objects_to_add = []
        parameter_handler.change_set.objects_to_update = []
        parameter_handler.change_set.objects_in_sync = []
        adapter.differs_from_live_object = Mock(return_value=False)
        parameter_handler.compare_live_config_with_desired_config()
        assert len(parameter_handler.change_set.objects_to_add) == 0
        assert len(parameter_handler.change_set.objects_to_update) == 0
        assert len(parameter_handler.change_set.objects_in_sync) == 1

    @patch("ansible_collections.vmware.vmware.plugins.module_utils.vm.parameter_handlers.device_linked._network_adapters.NetworkAdapter")
    def test_link_vm_device(self, mock_network_adapter, parameter_handler):
        """Test link_vm_device method."""
        adapter = Mock()
        adapter._live_object = None
        assert adapter._live_object is None

        parameter_handler.adapters = [adapter]
        parameter_handler.link_vm_device(Mock())
        adapter.link_corresponding_live_object.assert_called_once()

    def test_link_vm_device_no_matching_adapter(self, parameter_handler):
        """Test link_vm_device method when no matching adapter is found."""
        adapter = Mock()
        adapter._live_object = Mock()
        parameter_handler.adapters = [adapter]
        with pytest.raises(Exception, match="Network adapter not found for device"):
            parameter_handler.link_vm_device(Mock())


class TestE1000NetworkAdapterParameterHandler:
    @pytest.fixture
    def parameter_handler(self):
        """Create a E1000NetworkAdapterParameterHandler instance for testing."""
        error_handler = Mock()
        params = {}
        change_set = Mock()
        vm = Mock()
        device_tracker = Mock()
        vsphere_object_cache = Mock()

        return E1000NetworkAdapterParameterHandler(
            error_handler, params, change_set, vm, device_tracker, vsphere_object_cache
        )

    @patch(
        "ansible_collections.vmware.vmware.plugins.module_utils.vm.parameter_handlers.device_linked._network_adapters.vim.vm.device.VirtualE1000"
    )
    def test_vim_device_class(self, mock_virtual_e1000, parameter_handler):
        assert parameter_handler.vim_device_class == mock_virtual_e1000


class TestE1000eNetworkAdapterParameterHandler:
    @pytest.fixture
    def parameter_handler(self):
        """Create a E1000eNetworkAdapterParameterHandler instance for testing."""
        error_handler = Mock()
        params = {}
        change_set = Mock()
        vm = Mock()
        device_tracker = Mock()
        vsphere_object_cache = Mock()

        return E1000eNetworkAdapterParameterHandler(
            error_handler, params, change_set, vm, device_tracker, vsphere_object_cache
        )

    @patch(
        "ansible_collections.vmware.vmware.plugins.module_utils.vm.parameter_handlers.device_linked._network_adapters.vim.vm.device.VirtualE1000e"
    )
    def test_vim_device_class(self, mock_virtual_e1000e, parameter_handler):
        assert parameter_handler.vim_device_class == mock_virtual_e1000e


class TestPcnet32NetworkAdapterParameterHandler:
    @pytest.fixture
    def parameter_handler(self):
        """Create a Pcnet32NetworkAdapterParameterHandler instance for testing."""
        error_handler = Mock()
        params = {}
        change_set = Mock()
        vm = Mock()
        device_tracker = Mock()
        vsphere_object_cache = Mock()

        return Pcnet32NetworkAdapterParameterHandler(
            error_handler, params, change_set, vm, device_tracker, vsphere_object_cache
        )

    @patch(
        "ansible_collections.vmware.vmware.plugins.module_utils.vm.parameter_handlers.device_linked._network_adapters.vim.vm.device.VirtualPCNet32"
    )
    def test_vim_device_class(self, mock_virtual_pcnet32, parameter_handler):
        assert parameter_handler.vim_device_class == mock_virtual_pcnet32


class TestVmxnet2NetworkAdapterParameterHandler:
    @pytest.fixture
    def parameter_handler(self):
        """Create a Vmxnet2NetworkAdapterParameterHandler instance for testing."""
        error_handler = Mock()
        params = {}
        change_set = Mock()
        vm = Mock()
        device_tracker = Mock()
        vsphere_object_cache = Mock()

        return Vmxnet2NetworkAdapterParameterHandler(
            error_handler, params, change_set, vm, device_tracker, vsphere_object_cache
        )

    @patch(
        "ansible_collections.vmware.vmware.plugins.module_utils.vm.parameter_handlers.device_linked._network_adapters.vim.vm.device.VirtualVmxnet2"
    )
    def test_vim_device_class(self, mock_virtual_vmxnet2, parameter_handler):
        assert parameter_handler.vim_device_class == mock_virtual_vmxnet2


class TestVmxnet3NetworkAdapterParameterHandler:
    @pytest.fixture
    def parameter_handler(self):
        """Create a Vmxnet3NetworkAdapterParameterHandler instance for testing."""
        error_handler = Mock()
        params = {}
        change_set = Mock()
        vm = Mock()
        device_tracker = Mock()
        vsphere_object_cache = Mock()

        return Vmxnet3NetworkAdapterParameterHandler(
            error_handler, params, change_set, vm, device_tracker, vsphere_object_cache
        )

    @patch(
        "ansible_collections.vmware.vmware.plugins.module_utils.vm.parameter_handlers.device_linked._network_adapters.vim.vm.device.VirtualVmxnet3"
    )
    def test_vim_device_class(self, mock_virtual_vmxnet3, parameter_handler):
        assert parameter_handler.vim_device_class == mock_virtual_vmxnet3


class TestSriovNetworkAdapterParameterHandler:
    @pytest.fixture
    def parameter_handler(self):
        """Create a SriovNetworkAdapterParameterHandler instance for testing."""
        error_handler = Mock()
        params = {}
        change_set = Mock()
        vm = Mock()
        device_tracker = Mock()
        vsphere_object_cache = Mock()

        return SriovNetworkAdapterParameterHandler(
            error_handler, params, change_set, vm, device_tracker, vsphere_object_cache
        )

    @patch(
        "ansible_collections.vmware.vmware.plugins.module_utils.vm.parameter_handlers.device_linked._network_adapters.vim.vm.device.VirtualSriovEthernetCard"
    )
    def test_vim_device_class(self, mock_virtual_sriov, parameter_handler):
        assert parameter_handler.vim_device_class == mock_virtual_sriov

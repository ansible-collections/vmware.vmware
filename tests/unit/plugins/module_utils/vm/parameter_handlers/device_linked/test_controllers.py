from __future__ import absolute_import, division, print_function

__metaclass__ = type

import pytest
from unittest.mock import Mock, patch

from ansible_collections.vmware.vmware.plugins.module_utils.vm.parameter_handlers.device_linked._controllers import (
    DiskControllerParameterHandlerBase,
    ScsiControllerParameterHandler,
    SataControllerParameterHandler,
    NvmeControllerParameterHandler,
    IdeControllerParameterHandler,
    UsbControllerParameterHandler,
)
from ansible_collections.vmware.vmware.plugins.module_utils.vm._change_set import ParameterChangeSet


class MockDiskControllerParameterHandlerBase(DiskControllerParameterHandlerBase):
    HANDLER_NAME = "mock_controller"

    def __init__(
        self, error_handler, params, change_set, vm, device_tracker, category, max_count=4
    ):
        super().__init__(
            error_handler, params, change_set, vm, device_tracker, category, max_count
        )

    def _parse_device_controller_params(self):
        pass

    @property
    def vim_device_class(self):
        return Mock()


class TestDiskControllerParameterHandlerBase:
    @pytest.fixture
    def mock_handler(self):
        """Create a mock controller for testing."""
        handler = MockDiskControllerParameterHandlerBase(
            error_handler=Mock(),
            params={},
            change_set=Mock(),
            vm=Mock(),
            device_tracker=Mock(),
            category="scsi",
        )
        handler.error_handler.fail_with_parameter_error = Mock(
            side_effect=AssertionError()
        )
        handler.max_count = 4
        return handler

    def test_parse_device_controller_params(self, mock_handler):
        mock_handler._parse_device_controller_params()

    def test_verify_parameter_constraints(self, mock_handler):
        mock_handler._parse_device_controller_params = Mock()
        mock_handler.verify_parameter_constraints()
        mock_handler._parse_device_controller_params.assert_called_once()
        mock_handler._parse_device_controller_params.reset_mock()

        mock_handler.max_count = 1
        mock_handler.controllers = {
            0: Mock(),
            3: Mock(),
        }
        with pytest.raises(AssertionError):
            mock_handler.verify_parameter_constraints()
        mock_handler._parse_device_controller_params.assert_called_once()

    def test_link_vm_device(self, mock_handler):
        device = Mock(busNumber=0)
        mock_handler.controllers = {
            0: Mock(bus_number=0),
            3: Mock(bus_number=3),
        }
        mock_handler.link_vm_device(device)
        assert mock_handler.controllers[0].link_corresponding_live_object.call_count == 1
        assert mock_handler.controllers[3].link_corresponding_live_object.call_count == 0

    @pytest.mark.parametrize(
        "device",
        [
            (Mock(busNumber=1)),
            (Mock(busNumber=0)),
            (Mock(busNumber=4)),
        ],
    )
    def test_link_vm_device_no_match(self, device, mock_handler):
        mock_handler.controllers = {
            3: Mock(bus_number=3),
        }
        out = mock_handler.link_vm_device(device)
        assert out is not None

    def test_populate_config_spec_with_parameters(self, mock_handler):
        mock_handler.change_set.objects_to_add = [Mock()]
        mock_handler.change_set.objects_to_update = [Mock()]
        mock_handler.populate_config_spec_with_parameters(Mock())
        assert (
            mock_handler.change_set.objects_to_add[0].to_new_spec.called
            is True
        )
        assert (
            mock_handler.change_set.objects_to_update[0].to_update_spec.called
            is True
        )
        assert mock_handler.device_tracker.track_device_id_from_spec.call_count == 2

    def test_compare_live_config_with_desired_config(self, mock_handler):
        mock_handler.change_set = ParameterChangeSet(mock_handler.params, Mock(), Mock())
        mock_handler.compare_live_config_with_desired_config()
        assert mock_handler.change_set.are_changes_required() is False

        mock_handler.controllers = {
            0: Mock(has_a_linked_live_vm_device=Mock(return_value=False)),
            1: Mock(
                has_a_linked_live_vm_device=Mock(return_value=True),
                differs_from_live_object=Mock(return_value=True),
            ),
            2: Mock(
                has_a_linked_live_vm_device=Mock(return_value=True),
                differs_from_live_object=Mock(return_value=False),
            ),
        }

        mock_handler.compare_live_config_with_desired_config()
        assert mock_handler.change_set.are_changes_required() is True
        assert mock_handler.change_set.objects_to_add[0] is mock_handler.controllers[0]
        assert (
            mock_handler.change_set.objects_to_update[0] is mock_handler.controllers[1]
        )


class TestScsiControllerParameterHandler:
    @pytest.fixture
    def mock_handler(self):
        handler = ScsiControllerParameterHandler(
            error_handler=Mock(),
            params={},
            change_set=Mock(),
            vm=Mock(),
            device_tracker=Mock(),
        )
        handler.error_handler.fail_with_parameter_error = Mock(
            side_effect=AssertionError()
        )
        return handler

    def test_device_type_to_sub_class_map(self, mock_handler):
        assert list(mock_handler.device_type_to_sub_class_map.keys()) == [
            "lsilogic",
            "paravirtual",
            "buslogic",
            "lsilogicsas",
        ]

    def test_parse_device_controller_params(self, mock_handler):
        mock_handler.params = {
            "scsi_controllers": [
                {"bus_number": 0, "controller_type": "lsilogic"},
            ]
        }
        mock_handler._parse_device_controller_params()
        assert (
            mock_handler.controllers[0].vim_device_class
            == mock_handler.device_type_to_sub_class_map["lsilogic"]
        )


class TestSataControllerParameterHandler:
    @pytest.fixture
    def mock_handler(self):
        handler = SataControllerParameterHandler(
            error_handler=Mock(),
            params={},
            change_set=Mock(),
            vm=Mock(),
            device_tracker=Mock(),
        )
        handler.error_handler.fail_with_parameter_error = Mock(
            side_effect=AssertionError()
        )
        return handler

    @patch(
        "ansible_collections.vmware.vmware.plugins.module_utils.vm.parameter_handlers.device_linked._controllers.vim.vm.device.VirtualAHCIController"
    )
    def test_vim_device_class(self, mock_virtual_ahci_controller, mock_handler):
        assert mock_handler.vim_device_class == mock_virtual_ahci_controller

    def test_device_type_to_sub_class_map(self, mock_handler):
        assert list(mock_handler.device_type_to_sub_class_map.keys()) == []

    def test_parse_device_controller_params(self, mock_handler):
        mock_handler.params = {
            "sata_controllers": [
                {"bus_number": 0},
            ],
        }
        mock_handler._parse_device_controller_params()
        assert mock_handler.controllers[0].vim_device_class == mock_handler.vim_device_class


class TestNvmeControllerParameterHandler:
    @pytest.fixture
    def mock_handler(self):
        handler = NvmeControllerParameterHandler(
            error_handler=Mock(),
            params={},
            change_set=Mock(),
            vm=Mock(),
            device_tracker=Mock(),
        )
        handler.error_handler.fail_with_parameter_error = Mock(
            side_effect=AssertionError()
        )
        return handler

    @patch(
        "ansible_collections.vmware.vmware.plugins.module_utils.vm.parameter_handlers.device_linked._controllers.vim.vm.device.VirtualNVMEController"
    )
    def test_vim_device_class(self, mock_virtual_nvme_controller, mock_handler):
        assert mock_handler.vim_device_class == mock_virtual_nvme_controller

    def test_device_type_to_sub_class_map(self, mock_handler):
        assert list(mock_handler.device_type_to_sub_class_map.keys()) == []

    def test_parse_device_controller_params(self, mock_handler):
        mock_handler.params = {
            "nvme_controllers": [
                {"bus_number": 0, "bus_sharing": "exclusive"},
            ]
        }
        mock_handler._parse_device_controller_params()
        assert mock_handler.controllers[0].vim_device_class == mock_handler.vim_device_class


class TestIdeControllerParameterHandler:
    @pytest.fixture
    def mock_handler(self):
        handler = IdeControllerParameterHandler(
            error_handler=Mock(),
            params={},
            change_set=Mock(),
            vm=Mock(),
            device_tracker=Mock(),
        )
        handler.error_handler.fail_with_parameter_error = Mock(
            side_effect=AssertionError()
        )
        return handler

    @patch(
        "ansible_collections.vmware.vmware.plugins.module_utils.vm.parameter_handlers.device_linked._controllers.vim.vm.device.VirtualIDEController"
    )
    def test_vim_device_class(self, mock_virtual_ide_controller, mock_handler):
        assert mock_handler.vim_device_class == mock_virtual_ide_controller

    def test_device_type_to_sub_class_map(self, mock_handler):
        assert list(mock_handler.device_type_to_sub_class_map.keys()) == []

    def test_parse_device_controller_params(self, mock_handler):
        mock_handler.params = {}
        mock_handler._parse_device_controller_params()
        assert len(mock_handler.controllers) == 2
        assert mock_handler.controllers[0].vim_device_class == mock_handler.vim_device_class
        assert mock_handler.controllers[1].vim_device_class == mock_handler.vim_device_class


class TestUsbControllerParameterHandler:
    @pytest.fixture
    def mock_handler(self):
        handler = UsbControllerParameterHandler(
            error_handler=Mock(),
            params={},
            change_set=Mock(),
            vm=Mock(),
            device_tracker=Mock(),
        )
        handler.error_handler.fail_with_parameter_error = Mock(
            side_effect=AssertionError()
        )
        return handler

    @patch(
        "ansible_collections.vmware.vmware.plugins.module_utils.vm.parameter_handlers.device_linked._controllers.vim.vm.device.VirtualUSBController"
    )
    @patch(
        "ansible_collections.vmware.vmware.plugins.module_utils.vm.parameter_handlers.device_linked._controllers.vim.vm.device.VirtualUSBXHCIController"
    )
    def test_vim_device_class(self, mock_virtual_usb_controller, mock_virtual_usb_xhci_controller, mock_handler):
        mock_virtual_usb_controller.return_value = Mock()
        mock_virtual_usb_xhci_controller.return_value = Mock()
        assert mock_virtual_usb_controller in mock_handler.vim_device_class
        assert mock_virtual_usb_xhci_controller in mock_handler.vim_device_class

    def test_parse_device_controller_params(self, mock_handler):
        mock_handler.params = {'usb_controllers': []}
        mock_handler.verify_parameter_constraints()
        assert len(mock_handler.controllers) == 0

        mock_handler.params = {
            "usb_controllers": [
                {"controller_type": "usb2"},
                {"controller_type": "usb3"},
            ]
        }
        mock_handler.verify_parameter_constraints()
        assert len(mock_handler.controllers) == 2
        assert mock_handler.controllers['usb2'].vim_device_class in mock_handler.vim_device_class
        assert mock_handler.controllers['usb3'].vim_device_class in mock_handler.vim_device_class

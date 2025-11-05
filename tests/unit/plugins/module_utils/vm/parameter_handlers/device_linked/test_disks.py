from __future__ import absolute_import, division, print_function

__metaclass__ = type

import pytest
from unittest.mock import Mock, patch, ANY

from ansible_collections.vmware.vmware.plugins.module_utils.vm.parameter_handlers.device_linked._disks import (
    DiskParameterHandler,
)
from ansible_collections.vmware.vmware.plugins.module_utils.vm.objects._disk import Disk
from ansible_collections.vmware.vmware.plugins.module_utils.vm._change_set import (
    ParameterChangeSet,
)


class TestDiskParameterHandler:
    @pytest.fixture
    def mock_controller(self):
        """Create a mock controller for testing."""
        controller = Mock()
        controller.key = 1000
        controller.category = "scsi"
        return controller

    @pytest.fixture
    def mock_controller_handler(self, mock_controller):
        """Create a mock controller handler for testing."""
        handler = Mock()
        handler.category = "scsi"
        handler.managed_parameter_objects = {0: mock_controller}
        return handler

    @pytest.fixture
    def disk_parameter_handler(self, mock_controller_handler):
        """Create a DiskParameterHandler instance for testing."""
        error_handler = Mock()
        error_handler.fail_with_parameter_error.side_effect = AssertionError("test")
        params = {}
        change_set = Mock()
        vm = Mock()
        device_tracker = Mock()
        controller_handlers = [mock_controller_handler]
        vsphere_object_cache = Mock()

        return DiskParameterHandler(
            error_handler,
            params,
            change_set,
            vm,
            device_tracker,
            controller_handlers,
            vsphere_object_cache,
        )

    @patch(
        "ansible_collections.vmware.vmware.plugins.module_utils.vm.parameter_handlers.device_linked._disks.vim.vm.device.VirtualDisk"
    )
    def test_vim_device_class(self, mock_virtual_disk, disk_parameter_handler):
        assert disk_parameter_handler.vim_device_class == mock_virtual_disk

    def test_verify_parameter_constraints_no_disks(self, disk_parameter_handler):
        disk_parameter_handler._parse_disk_params = Mock()
        disk_parameter_handler.params = {"disks": []}

        disk_parameter_handler.vm = None
        disk_parameter_handler.managed_parameter_objects = {}
        with pytest.raises(AssertionError):
            disk_parameter_handler.verify_parameter_constraints()
        disk_parameter_handler._parse_disk_params.assert_called_once()
        disk_parameter_handler.error_handler.fail_with_parameter_error.assert_called_once()

        disk_parameter_handler.vm = Mock()
        disk_parameter_handler._parse_disk_params.reset_mock()
        disk_parameter_handler.error_handler.fail_with_parameter_error.reset_mock()
        disk_parameter_handler.verify_parameter_constraints()
        disk_parameter_handler._parse_disk_params.assert_called_once()
        disk_parameter_handler.error_handler.fail_with_parameter_error.assert_not_called()

    def test_verify_parameter_constraints_disks(self, disk_parameter_handler):
        disk_parameter_handler._parse_disk_params = Mock()
        disk_parameter_handler.params = {"disks": []}
        disk_parameter_handler.managed_parameter_objects = {0: Mock()}
        disk_parameter_handler.verify_parameter_constraints()
        disk_parameter_handler._parse_disk_params.assert_not_called()
        disk_parameter_handler.error_handler.fail_with_parameter_error.assert_not_called()

    def test_parse_disk_params(self, disk_parameter_handler):
        disk_parameter_handler.params = {
            "disks": [
                {
                    "size": "100gb",
                    "provisioning": "thin",
                    "mode": "persistent",
                    "device_node": "scsi(0:0)",
                }
            ]
        }

        disk_parameter_handler.verify_parameter_constraints()

        # Should not call fail_with_parameter_error
        disk_parameter_handler.error_handler.fail_with_parameter_error.assert_not_called()

        # Should have created a disk object
        assert len(disk_parameter_handler.managed_parameter_objects) == 1
        assert isinstance(disk_parameter_handler.managed_parameter_objects[0], Disk)

    def test_verify_parameter_constraints_parse_error(self, disk_parameter_handler):
        """Test parameter constraints validation with parsing error."""
        disk_parameter_handler.params = {
            "disks": [
                {
                    "size": "100gb",
                    "provisioning": "thin",
                    "mode": "persistent",
                    "device_node": "invalid_format",
                }
            ]
        }

        with pytest.raises(AssertionError):
            disk_parameter_handler.verify_parameter_constraints()

        disk_parameter_handler.error_handler.fail_with_parameter_error.assert_called_once_with(
            parameter_name="disks",
            message=ANY,
            details=ANY,
        )

    def test_verify_parameter_constraints_missing_controller(
        self, disk_parameter_handler
    ):
        """Test parameter constraints validation when controller is missing."""
        disk_parameter_handler.params = {
            "disks": [
                {
                    "size": "100gb",
                    "provisioning": "thin",
                    "mode": "persistent",
                    "device_node": "sata(0:0)",  # SATA controller not configured
                }
            ]
        }

        with pytest.raises(AssertionError):
            disk_parameter_handler.verify_parameter_constraints()

        disk_parameter_handler.error_handler.fail_with_parameter_error.assert_called_once_with(
            parameter_name="disks",
            message=ANY,
            details={
                "device_node": "sata(0:0)",
                "available_controllers": ANY,
            },
        )

    def test_parse_disk_params_success(self, disk_parameter_handler, mock_controller):
        """Test successful disk parameter parsing."""
        disk_parameter_handler.params = {
            "disks": [
                {
                    "size": "100gb",
                    "provisioning": "thin",
                    "mode": "persistent",
                    "device_node": "scsi(0:0)",
                },
                {
                    "size": "50gb",
                    "provisioning": "thick",
                    "mode": "independent_persistent",
                    "device_node": "scsi(0:1)",
                },
            ]
        }

        disk_parameter_handler._parse_disk_params()

        assert len(disk_parameter_handler.managed_parameter_objects) == 2

        # Check first disk
        disk1 = disk_parameter_handler.managed_parameter_objects[0]
        assert disk1.size == 104857600  # 100gb in KB
        assert disk1.provisioning == "thin"
        assert disk1.mode == "persistent"
        assert disk1.controller == mock_controller
        assert disk1.unit_number == 0

        # Check second disk
        disk2 = disk_parameter_handler.managed_parameter_objects[1]
        assert disk2.size == 52428800  # 50gb in KB
        assert disk2.provisioning == "thick"
        assert disk2.mode == "independent_persistent"
        assert disk2.controller == mock_controller
        assert disk2.unit_number == 1

    def test_populate_config_spec_with_parameters(self, disk_parameter_handler):
        configspec = Mock()
        disk_parameter_handler.change_set.objects_to_add = [Mock()]
        disk_parameter_handler.change_set.objects_to_update = [Mock(), Mock()]
        disk_parameter_handler.populate_config_spec_with_parameters(configspec)

        disk_parameter_handler.device_tracker.track_device_id_from_spec.assert_any_call(
            disk_parameter_handler.change_set.objects_to_add[0]
        )
        disk_parameter_handler.device_tracker.track_device_id_from_spec.assert_any_call(
            disk_parameter_handler.change_set.objects_to_update[0]
        )
        disk_parameter_handler.device_tracker.track_device_id_from_spec.assert_any_call(
            disk_parameter_handler.change_set.objects_to_update[1]
        )

        assert configspec.deviceChange.append.call_count == 3

    @patch(
        "ansible_collections.vmware.vmware.plugins.module_utils.vm.parameter_handlers.device_linked._disks.Disk.from_live_device_spec"
    )
    def test_link_vm_device(
        self, mock_disk_from_live_device_spec, disk_parameter_handler
    ):
        device = Mock(unitNumber=0, controllerKey=1)
        mock_disk_from_live_device_spec.return_value = device
        device.size = 10

        disk_parameter_handler.managed_parameter_objects = {
            0: Mock(unit_number=0, controller=Mock(key=1), size=10),
            1: Mock(unit_number=3, controller=Mock(key=1)),
            2: Mock(unit_number=0, controller=Mock(key=3)),
            3: Mock(unit_number=3, controller=Mock(key=3)),
        }
        disk_parameter_handler.managed_parameter_objects[
            0
        ].link_corresponding_live_object.side_effect = lambda x: setattr(
            disk_parameter_handler.managed_parameter_objects[0], "_live_object", x
        )
        disk_parameter_handler.link_vm_device(device)
        assert (
            disk_parameter_handler.managed_parameter_objects[0]._live_object is device
        )
        assert (
            disk_parameter_handler.managed_parameter_objects[1]._live_object
            is not device
        )
        assert (
            disk_parameter_handler.managed_parameter_objects[2]._live_object
            is not device
        )
        assert (
            disk_parameter_handler.managed_parameter_objects[3]._live_object
            is not device
        )

    @pytest.mark.parametrize(
        "device",
        [
            (Mock(unitNumber=1, controllerKey=1)),
            (Mock(unitNumber=0, controllerKey=2)),
            (Mock(unitNumber=4, controllerKey=4)),
        ],
    )
    def test_link_vm_device_no_match(self, device, disk_parameter_handler):
        disk_parameter_handler.managed_parameter_objects = {
            Mock(unit_number=0, controller=Mock(key=1)),
            Mock(unit_number=3, controller=Mock(key=1)),
            Mock(unit_number=0, controller=Mock(key=3)),
            Mock(unit_number=3, controller=Mock(key=3)),
        }
        with pytest.raises(Exception):
            disk_parameter_handler.link_vm_device(device)

    def test_compare_live_config_with_desired_config(self, disk_parameter_handler):
        disk_parameter_handler.change_set = ParameterChangeSet(Mock(), Mock(), Mock())

        disk_parameter_handler.managed_parameter_objects = {}
        disk_parameter_handler.compare_live_config_with_desired_config()
        assert disk_parameter_handler.change_set.are_changes_required() is False

        disk_parameter_handler.managed_parameter_objects = {
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
        disk_parameter_handler.compare_live_config_with_desired_config()
        assert disk_parameter_handler.change_set.are_changes_required() is True
        assert (
            disk_parameter_handler.change_set.objects_to_add[0]
            is disk_parameter_handler.managed_parameter_objects[0]
        )
        assert (
            disk_parameter_handler.change_set.objects_to_update[0]
            is disk_parameter_handler.managed_parameter_objects[1]
        )

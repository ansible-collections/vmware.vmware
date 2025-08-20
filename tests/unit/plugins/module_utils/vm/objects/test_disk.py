from __future__ import absolute_import, division, print_function

__metaclass__ = type

import pytest
from unittest.mock import Mock, patch

from ansible_collections.vmware.vmware.plugins.module_utils.vm.objects._disk import (
    Disk,
)


class TestDisk:

    @pytest.fixture
    def disk(self):
        """Test disk."""
        return Disk(
            size="100gb",
            backing="thin",
            mode="persistent",
            controller=Mock(),
            unit_number=1,
        )

    def test_key(self, disk):
        assert disk.key is None

        disk._spec = Mock()
        disk._spec.device.key = 1001
        assert disk.key == 1001

        disk._device = Mock()
        disk._device.key = 1000
        assert disk.key == 1000

    def test_name_as_str(self, disk):
        disk.controller.name_as_str = "SCSI Controller 0"
        assert disk.name_as_str == "Disk - SCSI Controller 0 Unit 1"

    @patch(
        "ansible_collections.vmware.vmware.plugins.module_utils.vm.objects._disk.vim.vm.device.VirtualDeviceSpec"
    )
    def test_update_disk_spec(self, mock_spec, disk):
        mock_spec.return_value = Mock()
        mock_spec.Operation.edit = "edit"

        device = Mock()
        disk._device = device
        disk._update_disk_spec_with_options = Mock()

        spec = disk.update_disk_spec()
        disk._update_disk_spec_with_options.assert_called_once_with(spec)
        assert spec.operation == "edit"
        assert spec.device is device
        assert disk._spec is spec

    @patch(
        "ansible_collections.vmware.vmware.plugins.module_utils.vm.objects._disk.vim.vm.device.VirtualDeviceSpec"
    )
    def test_create_disk_spec(self, mock_spec, disk):
        mock_spec.return_value = Mock()
        mock_spec.Operation.add = "add"

        disk._update_disk_spec_with_options = Mock()
        spec = disk.create_disk_spec()
        disk._update_disk_spec_with_options.assert_called_once_with(spec)
        assert spec.operation == "add"
        assert disk._device is None
        assert disk._spec is spec

    def test_update_disk_spec_with_options(self, disk):
        spec = Mock()
        disk.backing = "thin"
        disk._update_disk_spec_with_options(spec)
        assert spec.device.backing.diskMode == disk.mode
        assert spec.device.backing.thinProvisioned is True
        assert spec.device.controllerKey == disk.controller.key
        assert spec.device.unitNumber == disk.unit_number
        assert spec.device.capacityInKB == disk.size

        spec = Mock()
        disk.backing = "eagerzeroedthick"
        disk.mode = False
        disk._update_disk_spec_with_options(spec)
        assert spec.device.backing.eagerlyScrub is True
        assert spec.device.controllerKey == disk.controller.key
        assert spec.device.unitNumber == disk.unit_number
        assert spec.device.capacityInKB == disk.size

        spec = Mock()
        disk.backing = "foo"
        disk._update_disk_spec_with_options(spec)
        assert spec.device.controllerKey == disk.controller.key
        assert spec.device.unitNumber == disk.unit_number
        assert spec.device.capacityInKB == disk.size

    def test_linked_device_differs_from_config(self, disk):
        assert disk.linked_device_differs_from_config() is True

        disk._device = Mock()

        # Test capacity difference
        disk._device.capacityInKB = disk.size + 1
        assert disk.linked_device_differs_from_config() is True
        disk._device.capacityInKB = disk.size  # Reset

        # Test disk mode difference
        disk._device.backing.diskMode = "different_mode"
        assert disk.linked_device_differs_from_config() is True
        disk._device.backing.diskMode = disk.mode  # Reset

        # Test thin provisioning difference
        disk._device.backing.thinProvisioned = False
        assert disk.linked_device_differs_from_config() is True
        disk._device.backing.thinProvisioned = True  # Reset

        # Test eager scrub difference
        disk._device.backing.eagerlyScrub = True
        assert disk.linked_device_differs_from_config() is True

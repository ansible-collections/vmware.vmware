from __future__ import absolute_import, division, print_function

__metaclass__ = type

import pytest
from unittest.mock import Mock, patch

from ansible_collections.vmware.vmware.plugins.module_utils.vm.objects._disk import (
    Disk,
)


class TestDisk:

    def new_disk(self):
        return Disk(
            size="100gb",
            provisioning="thin",
            mode="persistent",
            datastore='',
            enable_sharing=False,
            controller=Mock(),
            unit_number=1,
        )

    @pytest.fixture
    def disk(self):
        """Test disk."""
        return self.new_disk()

    def test_key(self, disk):
        assert disk.key is None

        disk._live_object = Mock()
        disk._live_object.key = 1001
        assert disk.key == 1001

        disk._raw_object = Mock()
        disk._raw_object.key = 1000
        assert disk.key == 1000

    def test_name_as_str(self, disk):
        disk.controller.name_as_str = "SCSI Controller 0"
        assert disk.name_as_str == "Disk - SCSI Controller 0 Unit 1"

    @patch(
        "ansible_collections.vmware.vmware.plugins.module_utils.vm.objects._disk.vim.vm.device.VirtualDeviceSpec"
    )
    def test_to_update_spec(self, mock_spec, disk):
        disk._live_object = Mock()
        mock_spec.return_value = Mock()
        mock_spec.Operation.edit = "edit"

        device = Mock()
        disk._live_object = device
        disk._update_disk_spec_with_options = Mock()

        spec = disk.to_update_spec()
        disk._update_disk_spec_with_options.assert_called_once_with(spec)
        assert spec.operation == "edit"

    @patch(
        "ansible_collections.vmware.vmware.plugins.module_utils.vm.objects._disk.vim.vm.device.VirtualDeviceSpec"
    )
    def test_to_new_spec(self, mock_spec, disk):
        mock_spec.return_value = Mock()
        mock_spec.Operation.add = "add"

        disk._update_disk_spec_with_options = Mock()
        spec = disk.to_new_spec()
        disk._update_disk_spec_with_options.assert_called_once_with(spec)
        assert spec.operation == "add"

        disk.provisioning = "thin"
        spec = disk.to_new_spec()
        assert spec.device.backing.thinProvisioned is True

        disk.provisioning = "eagerzeroedthick"
        spec = disk.to_new_spec()
        assert spec.device.backing.eagerlyScrub is True


    def test_update_disk_spec_with_options(self, disk):
        spec = Mock()
        disk._update_disk_spec_with_options(spec)
        assert spec.device.backing.diskMode == disk.mode
        assert spec.device.controllerKey == disk.controller.key
        assert spec.device.unitNumber == disk.unit_number
        assert spec.device.capacityInKB == disk.size

        spec = Mock()
        disk.mode = False
        disk._update_disk_spec_with_options(spec)
        assert spec.device.capacityInKB == disk.size

    @pytest.mark.parametrize(
        "test_value, test_attr", [
            ("1", 'size'),
            ("different_mode", 'mode'),
            ("independent_nonpersistent", 'mode'),
            ('foo', 'datastore'),
            (True, 'enable_sharing'),
        ]
    )
    def test_differs_from_live_object(self, disk, test_value, test_attr):
        disk._live_object = self.new_disk()
        setattr(disk._live_object, test_attr, test_value)
        assert disk.differs_from_live_object() is True

    def test_differs_from_live_object_edge_cases(self, disk):
        assert disk.differs_from_live_object() is True
        disk._live_object = disk
        assert disk.differs_from_live_object() is False

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import pytest
from unittest.mock import Mock

from ansible_collections.vmware.vmware.plugins.module_utils.vm.services._device_tracker import (
    DeviceTracker,
)


class TestDeviceTracker:
    """Test cases for DeviceTracker class."""

    @pytest.fixture
    def mock_handlers(self):
        """Create mock device linked handlers."""
        out = []
        for i in range(2):
            handler = Mock()
            handler.vim_device_class = Mock()
            handler.link_vm_device = Mock()
            out.append(handler)
        return out

    def test_init(self):
        """Test DeviceTracker initialization."""
        tracker = DeviceTracker()
        assert tracker.spec_id_to_device == []

    def test_track_device_id_from_spec(self):
        """Test tracking a device."""
        tracker = DeviceTracker()
        device = Mock()

        tracker.track_device_id_from_spec(device)

        assert tracker.spec_id_to_device == [device]

    def test_translate_device_id_to_device(self):
        """Test translating device ID to device."""
        tracker = DeviceTracker()
        device = Mock()
        tracker.track_device_id_from_spec(device)

        result = tracker.translate_device_id_to_device(1)

        assert result == device

    def test_translate_device_id_to_device_invalid_id(self):
        """Test translating invalid device ID raises IndexError."""
        tracker = DeviceTracker()
        device = Mock()
        tracker.track_device_id_from_spec(device)

        with pytest.raises(IndexError):
            tracker.translate_device_id_to_device(2)

    def test_link_vm_devices_to_handler_devices_no_vm(self):
        device_tracker = DeviceTracker()
        device_tracker.link_vm_devices_to_handler_devices([], [Mock()])
        assert device_tracker.unlinked_devices == []

        device_tracker.link_vm_devices_to_handler_devices([1], [])
        assert device_tracker.unlinked_devices == []

    def test_link_vm_devices_to_handler_devices_successful_link(self):
        device_tracker = DeviceTracker()
        device = Mock()

        handler = Mock()
        handler.vim_device_class = type(device)
        handler.link_vm_device = Mock()

        device_tracker.link_vm_devices_to_handler_devices([device], [handler])
        assert device_tracker.unlinked_devices != []

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import pytest
from unittest.mock import Mock, patch

from ansible_collections.vmware.vmware.plugins.module_utils.vm.objects._controllers import (
    AbstractDeviceController,
    ScsiDeviceController,
    BasicDeviceController,
    ShareableDeviceController
)


class MockController(AbstractDeviceController):
    """Mock controller for testing."""

    NEW_CONTROLLER_KEYS = (1000, 9999)

    @classmethod
    def from_live_device_spec(cls, live_device_spec):
        """Test implementation of abstract method."""
        pass


@pytest.fixture
def device():
    """Test device."""
    device = Mock()
    device.unit_number = 1
    return device


class TestAbstractDeviceController:
    """Test cases for AbstractDeviceController class."""

    @pytest.fixture
    def controller(self):
        """Test controller."""
        return MockController(device_type="scsi", vim_device_class=Mock, bus_number=0)

    def test_key(self, controller):
        assert controller.key < 0

        controller._live_object = Mock()
        controller._live_object.key = 1000
        assert controller.key == 1000

        controller._raw_object = Mock()
        controller._raw_object.key = 1001
        assert controller.key == 1001

    def test_name_as_str(self, controller):
        assert controller.name_as_str == "SCSI(0:)"

    def test_add_device(self, controller, device):
        controller.add_device(device)
        assert controller.controlled_devices[1] == device

        with pytest.raises(ValueError):
            controller.add_device(device)

    @patch(
        "ansible_collections.vmware.vmware.plugins.module_utils.vm.objects._controllers.vim.vm.device.VirtualDeviceSpec"
    )
    def test_to_new_spec(self, mock_spec, controller):
        mock_spec.return_value = Mock()
        mock_spec.Operation.add = "add"

        spec = controller.to_new_spec()
        assert spec.operation == "add"
        assert spec.device.busNumber == controller.bus_number
        assert spec.device.key < 0

    @patch(
        "ansible_collections.vmware.vmware.plugins.module_utils.vm.objects._controllers.vim.vm.device.VirtualDeviceSpec"
    )
    def test_to_update_spec(self, mock_spec, controller):
        mock_spec.return_value = Mock()
        controller._raw_object = Mock()
        mock_spec.Operation.edit = "edit"

        spec = controller.to_update_spec()
        assert spec.operation == "edit"
        assert spec.device.busNumber == controller.bus_number

    def test_differs_from_live_object(self, controller):
        controller._live_object = None
        assert controller.differs_from_live_object() is True

        controller._live_object = Mock()
        controller._live_object.bus_number = controller.bus_number
        assert controller.differs_from_live_object() is False

        controller._live_object.bus_number = controller.bus_number + 1
        assert controller.differs_from_live_object() is True


class TestScsiDeviceController:
    """Test cases for ScsiController class."""

    @pytest.fixture
    def controller(self):
        """Test controller."""
        c = ScsiDeviceController(bus_number=0, device_type="paravirtual", vim_device_class=Mock, bus_sharing="noSharing")
        return c

    def test_init(self, controller):
        assert controller.vim_device_class is Mock

    @patch(
        "ansible_collections.vmware.vmware.plugins.module_utils.vm.objects._controllers.vim.vm.device.VirtualDeviceSpec"
    )
    def test_to_new_spec(self, mock_spec, controller):
        mock_spec.return_value = Mock()
        spec = controller.to_new_spec()
        assert spec.device.hotAddRemove is True
        assert spec.device.sharedBus == controller.bus_sharing
        assert spec.device.scsiCtlrUnitNumber == 7


class TestBasicDeviceController:
    """Test cases for SataController class."""
    def test_init(self):
        c = BasicDeviceController(bus_number=1, device_type="scsi", vim_device_class=Mock)
        assert c.vim_device_class is Mock


class TestShareableDeviceController:
    """Test cases for IdeController class."""

    def test_init(self):
        c = ShareableDeviceController(bus_number=1, device_type="scsi", vim_device_class=Mock, bus_sharing="noSharing")
        assert c.bus_sharing == "noSharing"
        assert c.vim_device_class is Mock

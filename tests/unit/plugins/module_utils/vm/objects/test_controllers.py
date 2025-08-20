from __future__ import absolute_import, division, print_function

__metaclass__ = type

import pytest
from unittest.mock import Mock, patch

from ansible_collections.vmware.vmware.plugins.module_utils.vm.objects._controllers import (
    AbstractDeviceController,
    ScsiController,
    SataController,
    IdeController,
    NvmeController,
)


class MockController(AbstractDeviceController):
    """Mock controller for testing."""

    NEW_CONTROLLER_KEYS = (1000, 9999)


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
        return MockController("scsi", Mock, 0)

    def test_init(self):
        with pytest.raises(NotImplementedError):
            AbstractDeviceController("scsi", object, 0)

    def test_key(self, controller):
        assert controller.key is None

        controller._spec = Mock()
        controller._spec.device.key = 1000
        assert controller.key == 1000

        controller._device = Mock()
        controller._device.key = 1001
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
    def test_create_controller_spec(self, mock_spec, controller):
        mock_additional_config = Mock()
        mock_spec.return_value = Mock()
        mock_spec.Operation.edit = "edit"
        mock_spec.Operation.add = "add"

        spec = controller.create_controller_spec(
            additional_config=mock_additional_config
        )
        assert controller._spec is spec
        assert spec.operation == "add"
        assert spec.device.busNumber == controller.bus_number
        assert (-spec.device.key >= controller.NEW_CONTROLLER_KEYS[0]) and (
            -spec.device.key <= controller.NEW_CONTROLLER_KEYS[1]
        )
        mock_additional_config.assert_called_once_with(spec, False)

        mock_additional_config.reset_mock()
        spec = controller.create_controller_spec(edit=True)
        assert controller._spec is spec
        assert not isinstance(spec.device.key, int)
        assert spec.operation == "edit"
        mock_additional_config.assert_not_called()

    def test_linked_device_differs_from_config(self, controller):
        def additional_comparisons():
            return True

        controller._device = None
        assert controller.linked_device_differs_from_config() is True

        controller._device = Mock()
        controller._device.busNumber = controller.bus_number
        assert controller.linked_device_differs_from_config() is False

        assert (
            controller.linked_device_differs_from_config(additional_comparisons) is True
        )

        controller._device.busNumber = controller.bus_number + 1
        assert controller.linked_device_differs_from_config() is True


class TestScsiController:
    """Test cases for ScsiController class."""

    @pytest.fixture
    def controller(self):
        """Test controller."""
        return ScsiController(0)

    def test_init(self, controller):
        c = ScsiController(1, device_class=Mock)
        assert c.device_class is Mock

        assert (
            controller.device_class is not None and controller.device_class is not Mock
        )

    def test_create_controller_spec(self, controller):
        spec = controller.create_controller_spec()
        assert spec.device.hotAddRemove is True
        assert spec.device.sharedBus == controller.bus_sharing
        assert spec.device.scsiCtlrUnitNumber == 7


class TestSataController:
    """Test cases for SataController class."""

    @pytest.fixture
    def controller(self):
        """Test controller."""
        return SataController(0)

    def test_init(self, controller):
        c = SataController(1, device_class=Mock)
        assert c.device_class is Mock

        assert (
            controller.device_class is not None and controller.device_class is not Mock
        )


class TestIdeController:
    """Test cases for IdeController class."""

    @pytest.fixture
    def controller(self):
        """Test controller."""
        return IdeController(0)

    def test_init(self, controller):
        c = IdeController(1, device_class=Mock)
        assert c.device_class is Mock

        assert (
            controller.device_class is not None and controller.device_class is not Mock
        )


class TestNvmeController:
    """Test cases for NvmeController class."""

    @pytest.fixture
    def controller(self):
        """Test controller."""
        return NvmeController(0)

    def test_init(self, controller):
        c = NvmeController(1, device_class=Mock)
        assert c.device_class is Mock

        assert (
            controller.device_class is not None and controller.device_class is not Mock
        )

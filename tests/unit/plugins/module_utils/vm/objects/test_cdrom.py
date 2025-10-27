from __future__ import absolute_import, division, print_function

__metaclass__ = type

import pytest
from unittest.mock import Mock, patch

from ansible_collections.vmware.vmware.plugins.module_utils.vm.objects._cdrom import (
    Cdrom,
)


class MockIsoBacking(Mock):
    pass


class MockEmulateBacking(Mock):
    pass


class MockPassthroughBacking(Mock):
    pass


class TestCdrom:

    @pytest.fixture
    def cdrom(self):
        """Test cdrom."""
        return Cdrom(
            controller=Mock(),
            unit_number=1,
            connect_at_power_on=True,
            iso_media_path="foo",
            client_device_mode=None,
        )

    def test_key(self, cdrom):
        assert cdrom.key < 0

        cdrom._live_object = Mock()
        cdrom._live_object.key = 1001
        assert cdrom.key == 1001

        cdrom._raw_object = Mock()
        cdrom._raw_object.key = 1000
        assert cdrom.key == 1000

    def test_str(self, cdrom):
        cdrom.controller = "SCSI Controller 0"
        assert str(cdrom) == "CD-ROM - SCSI Controller 0 Unit 1"

    @patch(
        "ansible_collections.vmware.vmware.plugins.module_utils.vm.objects._cdrom.vim.vm.device.VirtualCdrom.RemotePassthroughBackingInfo",
        new=MockPassthroughBacking,
    )
    @patch(
        "ansible_collections.vmware.vmware.plugins.module_utils.vm.objects._cdrom.vim.vm.device.VirtualCdrom.RemoteAtapiBackingInfo",
        new=MockEmulateBacking,
    )
    @patch(
        "ansible_collections.vmware.vmware.plugins.module_utils.vm.objects._cdrom.vim.vm.device.VirtualCdrom.IsoBackingInfo",
        new=MockIsoBacking,
    )
    def test_from_live_device_spec(self, cdrom):
        mock_device_spec = Mock()
        mock_device_spec.unitNumber = 1
        mock_device_spec.connectable.startConnected = True

        mock_backing = MockIsoBacking()
        mock_backing.fileName = "foo"
        mock_device_spec.backing = mock_backing
        obj = Cdrom.from_live_device_spec(mock_device_spec, cdrom.controller)
        assert obj.iso_media_path == "foo"
        assert obj.client_device_mode is None
        assert obj.connect_at_power_on is True
        assert obj.unit_number == 1
        assert obj.controller is cdrom.controller
        assert obj._raw_object is mock_device_spec

        mock_backing = MockEmulateBacking()
        mock_device_spec.backing = mock_backing
        obj = Cdrom.from_live_device_spec(mock_device_spec, cdrom.controller)
        assert obj.iso_media_path is None
        assert obj.client_device_mode == "emulated"

        mock_backing = MockPassthroughBacking()
        mock_device_spec.backing = mock_backing
        obj = Cdrom.from_live_device_spec(mock_device_spec, cdrom.controller)
        assert obj.iso_media_path is None
        assert obj.client_device_mode == "passthrough"

        mock_backing = Mock()
        mock_device_spec.backing = mock_backing
        with pytest.raises(ValueError):
            Cdrom.from_live_device_spec(mock_device_spec, cdrom.controller)

    def test_differs_from_live_object(self, cdrom):
        cdrom._live_object = Mock()
        cdrom._live_object.iso_media_path = "foo"
        cdrom._live_object.client_device_mode = None
        cdrom._live_object.connect_at_power_on = True
        assert cdrom.differs_from_live_object() is False

        cdrom._live_object.iso_media_path = "bar"
        assert cdrom.differs_from_live_object() is True

        cdrom._live_object.iso_media_path = None
        cdrom._live_object.client_device_mode = "emulated"
        assert cdrom.differs_from_live_object() is True

        cdrom._live_object = None
        assert cdrom.differs_from_live_object() is True

    @patch(
        "ansible_collections.vmware.vmware.plugins.module_utils.vm.objects._cdrom.vim.vm.device.VirtualDeviceSpec"
    )
    def test_to_new_spec(self, mock_spec, cdrom):
        mock_spec.return_value = Mock()
        cdrom._update_cdrom_spec_with_options = Mock()
        new_spec = cdrom.to_new_spec()
        assert new_spec.device.key < 0
        assert new_spec.device.connectable.allowGuestControl is True
        cdrom._update_cdrom_spec_with_options.assert_called_once_with(new_spec)

    @patch(
        "ansible_collections.vmware.vmware.plugins.module_utils.vm.objects._cdrom.vim.vm.device.VirtualDeviceSpec"
    )
    def test_to_update_spec(self, mock_spec, cdrom):
        mock_spec.return_value = Mock()
        cdrom._update_cdrom_spec_with_options = Mock()
        cdrom._raw_object = Mock()

        update_spec = cdrom.to_update_spec()
        assert update_spec.device is cdrom._raw_object
        cdrom._update_cdrom_spec_with_options.assert_called_once_with(update_spec)

        cdrom._raw_object = None
        cdrom._live_object = Mock()
        cdrom._live_object._raw_object = Mock()
        update_spec = cdrom.to_update_spec()
        assert update_spec.device is cdrom._live_object._raw_object

    @patch(
        "ansible_collections.vmware.vmware.plugins.module_utils.vm.objects._cdrom.vim.vm.device.VirtualCdrom.IsoBackingInfo",
        new=MockIsoBacking,
    )
    @patch(
        "ansible_collections.vmware.vmware.plugins.module_utils.vm.objects._cdrom.vim.vm.device.VirtualCdrom.RemotePassthroughBackingInfo",
        new=MockPassthroughBacking,
    )
    @patch(
        "ansible_collections.vmware.vmware.plugins.module_utils.vm.objects._cdrom.vim.vm.device.VirtualCdrom.RemoteAtapiBackingInfo",
        new=MockEmulateBacking,
    )
    def test_update_cdrom_spec_with_options(self, cdrom):
        mock_spec = Mock()
        cdrom._update_cdrom_spec_with_options(mock_spec)
        assert mock_spec.device.connectable.startConnected is True
        assert mock_spec.device.backing.fileName == "foo"

        mock_spec = Mock()
        cdrom.connect_at_power_on = None
        cdrom.iso_media_path = None
        cdrom.client_device_mode = "emulated"
        cdrom._update_cdrom_spec_with_options(mock_spec)
        assert isinstance(mock_spec.device.backing, MockEmulateBacking)

        mock_spec = Mock()
        cdrom.client_device_mode = "passthrough"
        cdrom._update_cdrom_spec_with_options(mock_spec)
        assert isinstance(mock_spec.device.backing, MockPassthroughBacking)

    def test_to_module_output(self, cdrom):
        output = cdrom._to_module_output()
        assert output["unit_number"] == 1
        assert "controller" in output
        assert output["connect_at_power_on"] is True
        assert output["iso_media_path"] == "foo"
        assert output["client_device_mode"] is None

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import pytest
from unittest.mock import Mock, patch

from ansible_collections.vmware.vmware.plugins.module_utils.vm.objects._nvdimm import (
    Nvdimm,
    NvdimmDeviceController,
)


class TestNvdimmDeviceController:

    @pytest.fixture
    def controller(self):
        return NvdimmDeviceController()

    def test_key(self, controller):
        controller.represents_live_vm_device = Mock(return_value=True)
        controller._raw_object = Mock(key=1001)
        assert controller.key == 1001

        controller.represents_live_vm_device = Mock(return_value=False)
        controller.has_a_linked_live_vm_device = Mock(return_value=True)
        controller._live_object = Mock(key=1000)
        assert controller.key == 1000

        controller.represents_live_vm_device = Mock(return_value=False)
        controller.has_a_linked_live_vm_device = Mock(return_value=False)
        assert controller.key is not None

    def test_from_live_device_spec(self, controller):
        live_device_spec = Mock()
        controller = NvdimmDeviceController.from_live_device_spec(live_device_spec)
        assert controller._raw_object is live_device_spec

    def test_to_module_output(self, controller):
        output = controller._to_module_output()
        assert output == {
            "device_type": "nvdimm controller",
        }

    @patch(
        "ansible_collections.vmware.vmware.plugins.module_utils.vm.objects._nvdimm.vim.vm.device.VirtualDeviceSpec"
    )
    def test_to_new_spec(self, mock_spec, controller):
        mock_spec.return_value = Mock()
        spec = controller.to_new_spec()
        assert spec.device.key is not None

    @patch(
        "ansible_collections.vmware.vmware.plugins.module_utils.vm.objects._nvdimm.vim.vm.device.VirtualDeviceSpec"
    )
    def test_to_update_spec(self, mock_spec, controller):
        mock_spec.return_value = Mock()
        controller._raw_object = Mock()
        spec = controller.to_update_spec()
        assert spec.device is controller._raw_object

    def test_differs_from_live_object(self, controller):
        controller.has_a_linked_live_vm_device = Mock(return_value=False)
        assert controller.differs_from_live_object() is True
        controller.has_a_linked_live_vm_device = Mock(return_value=True)
        assert controller.differs_from_live_object() is False


class TestNvdimm:

    @pytest.fixture
    def nvdimm(self):
        return Nvdimm(
            size_mb=1024,
            index=1,
            controller=NvdimmDeviceController(),
        )

    def test_key(self, nvdimm):
        nvdimm.represents_live_vm_device = Mock(return_value=True)
        nvdimm._raw_object = Mock(key=1001)
        assert nvdimm.key == 1001

        nvdimm.represents_live_vm_device = Mock(return_value=False)
        nvdimm.has_a_linked_live_vm_device = Mock(return_value=True)
        nvdimm._live_object = Mock(key=1000)
        assert nvdimm.key == 1000

        nvdimm.represents_live_vm_device = Mock(return_value=False)
        nvdimm.has_a_linked_live_vm_device = Mock(return_value=False)
        assert nvdimm.key is not None

    def test_str(self, nvdimm):
        assert str(nvdimm) == "NVDIMM 1"

    @patch(
        "ansible_collections.vmware.vmware.plugins.module_utils.vm.objects._nvdimm.vim.vm.device.VirtualDeviceSpec"
    )
    def test_to_update_spec(self, mock_spec, nvdimm):
        mock_spec.return_value = Mock()
        nvdimm._raw_object = Mock()
        spec = nvdimm.to_update_spec()
        assert spec.device is nvdimm._raw_object
        assert spec.device.capacityInMB == nvdimm.size_mb

    @patch(
        "ansible_collections.vmware.vmware.plugins.module_utils.vm.objects._nvdimm.vim.vm.device.VirtualDeviceSpec"
    )
    def test_to_new_spec(self, mock_spec, nvdimm):
        mock_spec.return_value = Mock()
        spec = nvdimm.to_new_spec()
        assert spec.device.capacityInMB == nvdimm.size_mb

    def test_differs_from_live_object(self, nvdimm):
        nvdimm._live_object = Mock()
        nvdimm._live_object.size_mb = 1024
        nvdimm.has_a_linked_live_vm_device = Mock(return_value=False)
        assert nvdimm.differs_from_live_object() is True

        nvdimm.has_a_linked_live_vm_device = Mock(return_value=True)
        nvdimm._compare_attributes_for_changes = Mock(return_value=False)
        assert nvdimm.differs_from_live_object() is False

    def test_to_module_output(self, nvdimm):
        output = nvdimm._to_module_output()
        assert output == {
            "object_type": "nvdimm",
            "label": str(nvdimm),
            "size_mb": nvdimm.size_mb,
        }

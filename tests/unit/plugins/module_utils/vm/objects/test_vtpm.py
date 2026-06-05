from __future__ import absolute_import, division, print_function

__metaclass__ = type

import pytest
from unittest.mock import Mock, patch

from ansible_collections.vmware.vmware.plugins.module_utils.vm.objects._vtpm import (
    Vtpm,
)


class TestVtpm:

    @pytest.fixture
    def vtpm(self):
        return Vtpm()

    def test_key(self, vtpm):
        vtpm.represents_live_vm_device = Mock(return_value=True)
        vtpm._raw_object = Mock(key=1001)
        assert vtpm.key == 1001

        vtpm.represents_live_vm_device = Mock(return_value=False)
        vtpm.has_a_linked_live_vm_device = Mock(return_value=True)
        vtpm._live_object = Mock(key=1000)
        assert vtpm.key == 1000

        vtpm.represents_live_vm_device = Mock(return_value=False)
        vtpm.has_a_linked_live_vm_device = Mock(return_value=False)
        assert vtpm.key is not None

    def test_from_live_device_spec_and_str(self):
        live_device = Mock()
        vtpm = Vtpm.from_live_device_spec(live_device)
        assert vtpm._raw_object is live_device
        assert str(vtpm) == "vTPM"

    @patch(
        "ansible_collections.vmware.vmware.plugins.module_utils.vm.objects._vtpm.vim.vm.device.VirtualDeviceSpec"
    )
    def test_to_new_spec(self, mock_spec, vtpm):
        mock_spec.return_value = Mock()
        spec = vtpm.to_new_spec()
        assert spec.device.key is not None

    def test_to_update_spec(self, vtpm):
        assert vtpm.to_update_spec() is None

    def test_differs_from_live_object(self, vtpm):
        vtpm.has_a_linked_live_vm_device = Mock(return_value=False)
        assert vtpm.differs_from_live_object() is True
        vtpm.has_a_linked_live_vm_device = Mock(return_value=True)
        assert vtpm.differs_from_live_object() is False

    def test_to_module_output(self, vtpm):
        assert vtpm._to_module_output() == {
            "object_type": "vtpm",
            "label": "vTPM",
        }

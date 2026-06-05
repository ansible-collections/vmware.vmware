from __future__ import absolute_import, division, print_function

__metaclass__ = type

import pytest
from unittest.mock import Mock

from ansible_collections.vmware.vmware.plugins.module_utils.vm.parameter_handlers.device_linked._vtpms import (
    VtpmParameterHandler,
)
from ansible_collections.vmware.vmware.plugins.module_utils.vm.objects._vtpm import (
    Vtpm,
)


class TestVtpmParameterHandler:

    @pytest.fixture
    def handler_factory(self):
        def _make(params, vm=None):
            return VtpmParameterHandler(
                Mock(), params, Mock(), vm, Mock()
            )
        return _make

    def test_init_enable_vtpm(self, handler_factory):
        handler = handler_factory({"enable_vtpm": True})
        assert 0 in handler.managed_parameter_objects
        assert isinstance(handler.managed_parameter_objects[0], Vtpm)

        handler = handler_factory({})
        assert handler.PARAMS_DEFINED_BY_USER is False
        assert handler.managed_parameter_objects == {}

    def test_verify_parameter_constraints(self, handler_factory):
        handler = handler_factory({"enable_vtpm": False})
        handler.verify_parameter_constraints()
        handler.error_handler.fail_with_parameter_error.assert_not_called()

        handler = handler_factory(
            {"enable_vtpm": True},
            vm=Mock(config=Mock(firmware="efi"), snapshot=None),
        )
        handler.verify_parameter_constraints()
        handler.error_handler.fail_with_parameter_error.assert_not_called()

        handler = handler_factory(
            {"enable_vtpm": True},
            vm=Mock(config=Mock(firmware="bios"), snapshot=None),
        )
        handler.error_handler.fail_with_parameter_error = Mock(
            side_effect=ValueError("firmware")
        )
        with pytest.raises(ValueError, match="firmware"):
            handler.verify_parameter_constraints()

        handler = handler_factory(
            {"enable_vtpm": True},
            vm=Mock(config=Mock(firmware="efi"), snapshot=Mock()),
        )
        handler.error_handler.fail_with_parameter_error = Mock(
            side_effect=ValueError("snapshot")
        )
        with pytest.raises(ValueError, match="snapshot"):
            handler.verify_parameter_constraints()

        handler = handler_factory(
            {
                "enable_vtpm": True,
                "vm_options": {"boot_firmware": "efi"},
            },
            vm=None,
        )
        handler.error_handler.fail_with_parameter_error = Mock()
        handler.verify_parameter_constraints()
        handler.error_handler.fail_with_parameter_error.assert_not_called()

    def test_compare_and_populate_config_spec(self, handler_factory):
        handler = handler_factory({"enable_vtpm": True})
        handler.change_set.objects_to_add = []
        handler.change_set.objects_to_update = []
        handler.compare_live_config_with_desired_config()
        assert len(handler.change_set.objects_to_add) == 1

        handler.change_set.objects_to_add = []
        handler.managed_parameter_objects[0].link_corresponding_live_object(
            Vtpm.from_live_device_spec(Mock())
        )
        handler.compare_live_config_with_desired_config()
        assert handler.change_set.objects_to_add == []

        configspec = Mock(deviceChange=[])
        handler.change_set.objects_to_add = [handler.managed_parameter_objects[0]]
        handler.populate_config_spec_with_parameters(configspec)
        assert len(configspec.deviceChange) == 1

    def test_link_vm_device(self, handler_factory):
        device = Mock()

        handler = handler_factory({"enable_vtpm": False})
        result = handler.link_vm_device(device)
        assert isinstance(result, Vtpm)
        assert result._raw_object is device

        handler = handler_factory({"enable_vtpm": True})
        vtpm = handler.managed_parameter_objects[0]
        assert handler.link_vm_device(device) is None
        assert vtpm.has_a_linked_live_vm_device()

    def test_link_vm_device_duplicate_vtpm(self, handler_factory):
        handler = handler_factory({"enable_vtpm": True})
        vtpm = handler.managed_parameter_objects[0]
        vtpm.link_corresponding_live_object(Vtpm.from_live_device_spec(Mock()))

        handler.error_handler.fail_with_parameter_error = Mock(
            side_effect=ValueError("duplicate")
        )
        with pytest.raises(ValueError, match="duplicate"):
            handler.link_vm_device(Mock())
        handler.error_handler.fail_with_parameter_error.assert_called_once()

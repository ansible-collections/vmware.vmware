from __future__ import absolute_import, division, print_function
__metaclass__ = type

import sys
import pytest

from ansible_collections.vmware.vmware.plugins.modules import vm_info

from ...common.utils import (
    run_module, ModuleTestCase
)

pytestmark = pytest.mark.skipif(
    sys.version_info < (2, 7), reason="requires python2.7 or higher"
)


class TestVmInfo(ModuleTestCase):

    def __prepare(self, mocker):
        init_mock = mocker.patch.object(vm_info.VmwareVmInfo, "__init__")
        init_mock.return_value = None

        gather_info_for_vms = mocker.patch.object(vm_info.VmwareVmInfo, "gather_info_for_vms")
        gather_info_for_vms.return_value = []

    def test_gather(self, mocker):
        self.__prepare(mocker)

        result = run_module(module_entry=vm_info.main, module_args={})
        assert result["changed"] is False

from __future__ import absolute_import, division, print_function
__metaclass__ = type

import sys
import pytest

from ansible_collections.vmware.vmware.plugins.modules import license_info

from ...common.utils import (
    AnsibleExitJson, ModuleTestCase, set_module_args,
)

pytestmark = pytest.mark.skipif(
    sys.version_info < (2, 7), reason="requires python2.7 or higher"
)


class TestGuestInfo(ModuleTestCase):

    def __prepare(self, mocker):
        license_info.VcenterLicenseMgr.content = mocker.Mock()

        init_mock = mocker.patch.object(license_info.VcenterLicenseMgr, "__init__")
        init_mock.return_value = None

        is_vcenter = mocker.patch.object(license_info.VcenterLicenseMgr, "is_vcenter")
        is_vcenter.return_value = True

        list_keys = mocker.patch.object(license_info.VcenterLicenseMgr, "list_keys")
        list_keys.return_value = []

    def test_gather(self, mocker):
        self.__prepare(mocker)

        set_module_args(
            hostname="127.0.0.1",
            username="administrator@local",
            password="123456",
            add_cluster=False,
        )

        with pytest.raises(AnsibleExitJson) as c:
            license_info.main()

        assert c.value.args[0]["changed"] is False

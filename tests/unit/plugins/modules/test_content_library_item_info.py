from __future__ import absolute_import, division, print_function
__metaclass__ = type

import sys
import pytest

from ansible_collections.vmware.vmware.plugins.modules import content_library_item_info

from ...common.utils import (
    AnsibleExitJson, ModuleTestCase, set_module_args,
)

pytestmark = pytest.mark.skipif(
    sys.version_info < (2, 7), reason="requires python2.7 or higher"
)


class TestGuestInfo(ModuleTestCase):

    def __prepare(self, mocker):
        init_mock = mocker.patch.object(content_library_item_info.ContentLibaryItemInfo, "__init__")
        init_mock.return_value = None

        library_item_ids = mocker.patch.object(content_library_item_info.ContentLibaryItemInfo, "get_relevant_library_item_ids_by_params")
        library_item_ids.return_value = []

    def test_gather(self, mocker):
        self.__prepare(mocker)

        set_module_args(
            hostname="127.0.0.1",
            username="administrator@local",
            password="123456",
            add_cluster=False,
        )

        with pytest.raises(AnsibleExitJson) as c:
            content_library_item_info.main()

        assert c.value.args[0]["changed"] is False

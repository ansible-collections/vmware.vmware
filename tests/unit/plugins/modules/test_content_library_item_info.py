from __future__ import absolute_import, division, print_function
__metaclass__ = type

import sys
import pytest

from ansible_collections.vmware.vmware.plugins.modules import content_library_item_info

from ...common.utils import (
    run_module, ModuleTestCase
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

        result = run_module(module_entry=content_library_item_info.main, module_args={})
        assert result["changed"] is False

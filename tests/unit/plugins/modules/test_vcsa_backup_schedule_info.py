from __future__ import absolute_import, division, print_function
__metaclass__ = type

import sys
import pytest

from ansible_collections.vmware.vmware.plugins.modules.vcsa_backup_schedule_info import (
    main as module_main
)
from ansible_collections.vmware.vmware.plugins.module_utils.clients.rest import (
    VmwareRestClient
)
from ...common.utils import (
    AnsibleExitJson, ModuleTestCase, set_module_args,
)

pytestmark = pytest.mark.skipif(
    sys.version_info < (2, 7), reason="requires python2.7 or higher"
)


class TestContentTemplate(ModuleTestCase):

    def __prepare(self, mocker):
        self.mock_rest_client = mocker.Mock()
        mocker.patch.object(VmwareRestClient, 'connect_to_api', return_value=self.mock_rest_client)

    def __mock_schedule(self, mocker):
        s = mocker.Mock()
        s.parts = ['1', '2']
        s.location = ""
        s.recurrence_info = mocker.Mock()
        s.recurrence_info.minute = 1
        s.recurrence_info.hour = 2
        s.recurrence_info.days = ['']
        return s

    def test_get_schedules(self, mocker):
        self.__prepare(mocker)
        self.mock_rest_client.appliance.recovery.backup.Schedules.list.return_value = {
            "foo": self.__mock_schedule(mocker), "bar": self.__mock_schedule(mocker)
        }
        # test no name
        set_module_args(
            hostname="127.0.0.1",
            username="administrator@local",
            password="123456",
            add_cluster=False,
        )

        with pytest.raises(AnsibleExitJson) as c:
            module_main()

        assert c.value.args[0]["changed"] is False
        assert len(c.value.args[0]["schedules"]) == 2

        # test name match
        set_module_args(
            hostname="127.0.0.1",
            username="administrator@local",
            password="123456",
            add_cluster=False,
            name="foo"
        )

        with pytest.raises(AnsibleExitJson) as c:
            module_main()

        assert c.value.args[0]["changed"] is False
        assert len(c.value.args[0]["schedules"]) == 1

        # test no match
        set_module_args(
            hostname="127.0.0.1",
            username="administrator@local",
            password="123456",
            add_cluster=False,
            name="not real"
        )

        with pytest.raises(AnsibleExitJson) as c:
            module_main()

        assert c.value.args[0]["changed"] is False
        assert len(c.value.args[0]["schedules"]) == 0

from __future__ import absolute_import, division, print_function
__metaclass__ = type

import sys
import pytest
from unittest import mock

from ansible_collections.vmware.vmware.plugins.modules.vcsa_backup_schedule import (
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
        self.default_args = dict(
            hostname="127.0.0.1",
            username="administrator@local",
            password="123456",
            add_cluster=False,
            schedule=dict(minute=1, hour=2, days_of_week=['MONDAY']),
            location=dict(url="http://localhost"),
            include_supervisors_control_plane=False,
            include_stats_events_and_tasks=False
        )
        self.mock_schedule = self.__mock_schedule(mocker)

        self.mock_rest_client.appliance.recovery.backup.Schedules.RecurrenceInfo.side_effect = self.mock_info_obj
        self.mock_rest_client.appliance.recovery.backup.Schedules.RetentionInfo.side_effect = self.mock_info_obj

    def mock_info_obj(self, **kwargs):
        o = mock.Mock()
        for k, v in kwargs.items():
            setattr(o, k, v)
        return o

    def __mock_schedule(self, mocker):
        s = mocker.Mock()
        s.parts = ['common']
        s.location = self.default_args['location']
        s.recurrence_info = mocker.Mock()
        s.recurrence_info.minute = self.default_args['schedule']['minute']
        s.recurrence_info.hour = self.default_args['schedule']['hour']
        s.recurrence_info.days = self.default_args['schedule']['days_of_week']
        s.enable = True
        s.fast_backup = False
        s.retention_info = mocker.Mock()
        s.retention_info.max_count = None
        s.location_password = None
        s.backup_password = None
        return s

    def test_create_schedule(self, mocker):
        self.__prepare(mocker)
        set_module_args(**self.default_args)
        with pytest.raises(AnsibleExitJson) as c:
            module_main()

        assert c.value.args[0]["changed"] is True

    def test_no_change(self, mocker):
        self.__prepare(mocker)
        self.mock_rest_client.appliance.recovery.backup.Schedules.get.return_value = self.mock_schedule
        self.mock_rest_client.appliance.recovery.backup.Schedules.UpdateSpec.return_value = self.mock_schedule

        # no change
        set_module_args(**self.default_args)
        with pytest.raises(AnsibleExitJson) as c:
            module_main()

        assert c.value.args[0]["changed"] is False

    def test_update_schedule(self, mocker):
        self.__prepare(mocker)
        self.mock_rest_client.appliance.recovery.backup.Schedules.get.return_value = self.mock_schedule

        # change time
        set_module_args(**{**self.default_args, **dict(schedule=dict(minute=9, hour=2, days_of_week=['MONDAY']))})
        with pytest.raises(AnsibleExitJson) as c:
            module_main()

        assert c.value.args[0]["changed"] is True

        # change location
        set_module_args(**{**self.default_args, **dict(location=dict(url="https://foo"))})
        with pytest.raises(AnsibleExitJson) as c:
            module_main()

        assert c.value.args[0]["changed"] is True

        # change parts
        set_module_args(**{**self.default_args, **dict(include_supervisors_control_plane=True)})
        with pytest.raises(AnsibleExitJson) as c:
            module_main()

        assert c.value.args[0]["changed"] is True

    def test_delete_schedule(self, mocker):
        self.__prepare(mocker)
        self.mock_rest_client.appliance.recovery.backup.Schedules.get.return_value = None
        # test no schedule
        set_module_args(
            hostname="127.0.0.1",
            username="administrator@local",
            password="123456",
            add_cluster=False,
            state='absent'
        )

        with pytest.raises(AnsibleExitJson) as c:
            module_main()

        assert c.value.args[0]["changed"] is False

        # test delete
        self.mock_rest_client.appliance.recovery.backup.Schedules.get.return_value = self.mock_schedule
        set_module_args(
            hostname="127.0.0.1",
            username="administrator@local",
            password="123456",
            add_cluster=False,
            state='absent'
        )

        with pytest.raises(AnsibleExitJson) as c:
            module_main()

        assert c.value.args[0]["changed"] is True

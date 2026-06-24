from __future__ import absolute_import, division, print_function

__metaclass__ = type

from datetime import datetime
import asyncio
import pytest
from unittest.mock import patch, AsyncMock, Mock
from ansible.errors import AnsibleError
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../../.."))

from extensions.eda.plugins.event_source.vcenter_event_manager import (
    VcenterEventManagerSource,
    main,
)


class TestVcenterEventManagerSource:
    @pytest.fixture
    def mock_queue(self):
        return AsyncMock(spec=asyncio.Queue)

    @pytest.fixture
    def base_args(self):
        return {
            "hostname": "vcenter.example.com",
            "username": "admin",
            "password": "password123",
        }

    @pytest.fixture
    def mock_pyvmomi_client(self):
        mock_client = Mock()
        mock_client.content = Mock()
        mock_client.content.eventManager = Mock()
        return mock_client

    @pytest.fixture
    def source(self, mock_queue, base_args, mock_pyvmomi_client):
        with patch(
            "extensions.eda.plugins.event_source.vcenter_event_manager.PyvmomiClient"
        ) as mock_client_class:
            mock_client_class.return_value = mock_pyvmomi_client
            source = VcenterEventManagerSource(mock_queue, base_args)
            return source

    # Test initialization
    def test_init_with_minimal_args(self, mock_queue, base_args, mock_pyvmomi_client):
        with patch(
            "extensions.eda.plugins.event_source.vcenter_event_manager.PyvmomiClient"
        ) as mock_client_class:
            mock_client_class.return_value = mock_pyvmomi_client
            source = VcenterEventManagerSource(mock_queue, base_args)

            assert source.queue == mock_queue
            assert source.poll_interval_seconds == 60
            assert isinstance(source.last_poll_start_time, datetime)
            assert source.plugin_args["event_type"] == "system"

    def test_init_with_custom_interval(
        self, mock_queue, base_args, mock_pyvmomi_client
    ):
        args = {**base_args, "interval": 120}
        with patch(
            "extensions.eda.plugins.event_source.vcenter_event_manager.PyvmomiClient"
        ) as mock_client_class:
            mock_client_class.return_value = mock_pyvmomi_client
            source = VcenterEventManagerSource(mock_queue, args)

            assert source.poll_interval_seconds == 120

    def test_init_with_initial_start_time(
        self, mock_queue, base_args, mock_pyvmomi_client
    ):
        args = {**base_args, "initial_start_time": "2025-06-01 10:00:00"}
        with patch(
            "extensions.eda.plugins.event_source.vcenter_event_manager.PyvmomiClient"
        ) as mock_client_class:
            mock_client_class.return_value = mock_pyvmomi_client
            source = VcenterEventManagerSource(mock_queue, args)

            assert source.last_poll_start_time == datetime(2025, 6, 1, 10, 0, 0)

    # Test _validate_plugin_args
    def test_validate_plugin_args_default_event_type(self, source):
        args = {}
        result = source._validate_plugin_args(args)
        assert result["event_type"] == "system"

    def test_validate_plugin_args_user_event_type(self, source):
        args = {"event_type": "user"}
        result = source._validate_plugin_args(args)
        assert result["event_type"] == "user"

    def test_validate_plugin_args_invalid_event_type(self, source):
        args = {"event_type": "invalid"}
        with pytest.raises(AnsibleError, match="must be either 'system' or 'user'"):
            source._validate_plugin_args(args)

    def test_validate_plugin_args_valid_severity(self, source):
        args = {"severity": ["info", "warning"]}
        result = source._validate_plugin_args(args)
        assert result["severity"] == ["info", "warning"]

    def test_validate_plugin_args_invalid_severity(self, source):
        args = {"severity": ["info", "critical"]}
        with pytest.raises(AnsibleError, match="severity plugin argument"):
            source._validate_plugin_args(args)

    def test_validate_plugin_args_empty_severity(self, source):
        args = {"severity": []}
        result = source._validate_plugin_args(args)
        assert result["severity"] == []

    # Test _init_pyvmomi_client
    def test_init_pyvmomi_client_required_args_missing(self, mock_queue):
        args = {}
        with pytest.raises(AnsibleError, match="hostname.*required"):
            VcenterEventManagerSource(mock_queue, args)

    def test_init_pyvmomi_client_with_env_vars(self, mock_queue, mock_pyvmomi_client):
        args = {}
        with patch.dict(
            os.environ,
            {
                "VMWARE_HOST": "vcenter.example.com",
                "VMWARE_USER": "admin",
                "VMWARE_PASSWORD": "password123",
            },
        ):
            with patch(
                "extensions.eda.plugins.event_source.vcenter_event_manager.PyvmomiClient"
            ) as mock_client_class:
                mock_client_class.return_value = mock_pyvmomi_client
                source = VcenterEventManagerSource(mock_queue, args)

                mock_client_class.assert_called_once()
                call_kwargs = mock_client_class.call_args[1]
                assert call_kwargs["hostname"] == "vcenter.example.com"
                assert call_kwargs["username"] == "admin"
                assert call_kwargs["password"] == "password123"

    def test_init_pyvmomi_client_args_override_env_vars(
        self, mock_queue, base_args, mock_pyvmomi_client
    ):
        with patch.dict(
            os.environ,
            {
                "VMWARE_HOST": "old.vcenter.com",
                "VMWARE_USER": "old_user",
                "VMWARE_PASSWORD": "old_pass",
            },
        ):
            with patch(
                "extensions.eda.plugins.event_source.vcenter_event_manager.PyvmomiClient"
            ) as mock_client_class:
                mock_client_class.return_value = mock_pyvmomi_client
                source = VcenterEventManagerSource(mock_queue, base_args)

                call_kwargs = mock_client_class.call_args[1]
                assert call_kwargs["hostname"] == "vcenter.example.com"
                assert call_kwargs["username"] == "admin"
                assert call_kwargs["password"] == "password123"

    # Test _normalize_events_page
    def test_normalize_events_page_none(self, source):
        result = source._normalize_events_page(None)
        assert result == []

    def test_normalize_events_page_list(self, source):
        events = [Mock(), Mock()]
        result = source._normalize_events_page(events)
        assert result == events

    def test_normalize_events_page_single_event(self, source):
        event = Mock()
        result = source._normalize_events_page(event)
        assert result == [event]

    # Test _create_time_filter
    @patch("extensions.eda.plugins.event_source.vcenter_event_manager.vim")
    def test_create_time_filter_default(self, mock_vim, source):
        mock_time_filter = Mock()
        mock_vim.event.EventFilterSpec.ByTime.return_value = mock_time_filter

        with patch(
            "extensions.eda.plugins.event_source.vcenter_event_manager.datetime"
        ) as mock_datetime:
            mock_now = datetime(2025, 6, 23, 12, 0, 0)
            mock_datetime.now.return_value = mock_now
            source.last_poll_start_time = datetime(2025, 6, 23, 11, 59, 0)

            result = source._create_time_filter()

            assert result.beginTime == source.last_poll_start_time
            assert result.endTime == mock_now

    @patch("extensions.eda.plugins.event_source.vcenter_event_manager.vim")
    def test_create_time_filter_with_custom_start_time(self, mock_vim, source):
        mock_time_filter = Mock()
        mock_vim.event.EventFilterSpec.ByTime.return_value = mock_time_filter

        custom_start = datetime(2025, 6, 20, 10, 0, 0)
        with patch(
            "extensions.eda.plugins.event_source.vcenter_event_manager.datetime"
        ) as mock_datetime:
            mock_now = datetime(2025, 6, 23, 12, 0, 0)
            mock_datetime.now.return_value = mock_now

            result = source._create_time_filter(start_time=custom_start)

            assert result.beginTime == custom_start
            assert result.endTime == mock_now

    @patch("extensions.eda.plugins.event_source.vcenter_event_manager.vim")
    @patch("extensions.eda.plugins.event_source.vcenter_event_manager.logger")
    def test_create_time_filter_warns_on_large_interval(
        self, mock_logger, mock_vim, source
    ):
        mock_time_filter = Mock()
        mock_vim.event.EventFilterSpec.ByTime.return_value = mock_time_filter

        source.poll_interval_seconds = 60
        source.last_poll_start_time = datetime(2025, 6, 23, 10, 0, 0)

        with patch(
            "extensions.eda.plugins.event_source.vcenter_event_manager.datetime"
        ) as mock_datetime:
            mock_now = datetime(2025, 6, 23, 12, 11, 0)
            mock_datetime.now.return_value = mock_now

            result = source._create_time_filter()

            mock_logger.warning.assert_called_once()

    # Test _create_event_filters
    @patch("extensions.eda.plugins.event_source.vcenter_event_manager.vim")
    def test_create_event_filters_minimal(self, mock_vim, source):
        mock_username_filter = Mock()
        mock_vim.event.EventFilterSpec.ByUsername.return_value = mock_username_filter

        filters = source._create_event_filters()

        assert "userName" in filters
        assert filters["userName"].systemUser is True
        assert "eventTypeId" not in filters
        assert "category" not in filters
        assert "tag" not in filters

    @patch("extensions.eda.plugins.event_source.vcenter_event_manager.vim")
    def test_create_event_filters_with_event_type_ids(self, mock_vim, source):
        mock_username_filter = Mock()
        mock_vim.event.EventFilterSpec.ByUsername.return_value = mock_username_filter

        source.plugin_args["event_type_ids"] = [
            "vim.event.AlarmStatusChangedEvent",
            "vim.event.VmPoweredOnEvent",
        ]

        filters = source._create_event_filters()

        assert filters["eventTypeId"] == [
            "vim.event.AlarmStatusChangedEvent",
            "vim.event.VmPoweredOnEvent",
        ]

    @patch("extensions.eda.plugins.event_source.vcenter_event_manager.vim")
    def test_create_event_filters_with_user_names(self, mock_vim, source):
        mock_username_filter = Mock()
        mock_vim.event.EventFilterSpec.ByUsername.return_value = mock_username_filter

        source.plugin_args["user_names"] = ["DOMAIN\\user1", "DOMAIN\\user2"]

        filters = source._create_event_filters()

        assert filters["userName"].userList == ["DOMAIN\\user1", "DOMAIN\\user2"]

    @patch("extensions.eda.plugins.event_source.vcenter_event_manager.vim")
    def test_create_event_filters_with_severity(self, mock_vim, source):
        mock_username_filter = Mock()
        mock_vim.event.EventFilterSpec.ByUsername.return_value = mock_username_filter

        source.plugin_args["severity"] = ["info", "warning"]

        filters = source._create_event_filters()

        assert filters["category"] == ["info", "warning"]

    @patch("extensions.eda.plugins.event_source.vcenter_event_manager.vim")
    def test_create_event_filters_with_tags(self, mock_vim, source):
        mock_username_filter = Mock()
        mock_vim.event.EventFilterSpec.ByUsername.return_value = mock_username_filter

        source.plugin_args["event_tags"] = ["tag1", "tag2"]

        filters = source._create_event_filters()

        assert filters["tag"] == ["tag1", "tag2"]

    @patch("extensions.eda.plugins.event_source.vcenter_event_manager.vim")
    def test_create_event_filters_user_event_type(self, mock_vim, source):
        mock_username_filter = Mock()
        mock_vim.event.EventFilterSpec.ByUsername.return_value = mock_username_filter

        source.plugin_args["event_type"] = "user"

        filters = source._create_event_filters()

        assert filters["userName"].systemUser is False

    @patch("extensions.eda.plugins.event_source.vcenter_event_manager.vim")
    def test_create_event_filters_with_datacenter(self, mock_vim, source):
        mock_username_filter = Mock()
        mock_entity_filter = Mock()
        mock_vim.event.EventFilterSpec.ByUsername.return_value = mock_username_filter
        mock_vim.event.EventFilterSpec.ByEntity.return_value = mock_entity_filter

        mock_datacenter = Mock()
        source.plugin_args["datacenter"] = "DC1"
        source._datacenter = mock_datacenter

        filters = source._create_event_filters()

        assert "entity" in filters
        assert filters["entity"].entity == mock_datacenter
        assert filters["entity"].recursion == "all"

    # Test datacenter property
    @patch("extensions.eda.plugins.event_source.vcenter_event_manager.vim")
    def test_datacenter_property_caches_result(self, mock_vim, source):
        mock_datacenter = Mock()
        source.pyvmomi_client.get_objs_by_name_or_moid = Mock(
            return_value=[mock_datacenter]
        )
        source.plugin_args["datacenter"] = "DC1"

        result1 = source.datacenter
        result2 = source.datacenter

        assert result1 == mock_datacenter
        assert result2 == mock_datacenter
        source.pyvmomi_client.get_objs_by_name_or_moid.assert_called_once()

    @patch("extensions.eda.plugins.event_source.vcenter_event_manager.vim")
    def test_datacenter_property_raises_on_multiple_results(self, mock_vim, source):
        source.pyvmomi_client.get_objs_by_name_or_moid = Mock(
            return_value=[Mock(), Mock()]
        )
        source.plugin_args["datacenter"] = "DC1"

        with pytest.raises(AnsibleError, match="More than one datacenter"):
            _ = source.datacenter  # pylint: disable=disallowed-name

    @patch("extensions.eda.plugins.event_source.vcenter_event_manager.vim")
    def test_datacenter_property_raises_on_no_results(self, mock_vim, source):
        source.pyvmomi_client.get_objs_by_name_or_moid = Mock(return_value=[])
        source.plugin_args["datacenter"] = "DC1"

        with pytest.raises(AnsibleError, match="No datacenter"):
            _ = source.datacenter  # pylint: disable=disallowed-name

    @patch("extensions.eda.plugins.event_source.vcenter_event_manager.vim")
    def test_datacenter_property_returns_none_when_not_set(self, mock_vim, source):
        result = source.datacenter
        assert result is None

    # Test _poll_for_events
    @pytest.mark.asyncio
    @patch("extensions.eda.plugins.event_source.vcenter_event_manager.vim")
    @patch("extensions.eda.plugins.event_source.vcenter_event_manager.vmware_obj_to_json")
    async def test_poll_for_events_no_events(
        self, mock_obj_to_json, mock_vim, source
    ):
        mock_collector = Mock()
        mock_collector.ReadNextEvents = Mock(return_value=None)
        source.pyvmomi_client.content.eventManager.CreateCollectorForEvents = Mock(
            return_value=mock_collector
        )

        await source._poll_for_events()

        source.queue.put.assert_not_called()

    @pytest.mark.asyncio
    @patch("extensions.eda.plugins.event_source.vcenter_event_manager.vim")
    @patch("extensions.eda.plugins.event_source.vcenter_event_manager.vmware_obj_to_json")
    async def test_poll_for_events_single_page(
        self, mock_obj_to_json, mock_vim, source
    ):
        mock_event1 = Mock()
        mock_event2 = Mock()
        mock_obj_to_json.side_effect = lambda x: {"event": x}

        mock_collector = Mock()
        mock_collector.ReadNextEvents = Mock(
            side_effect=[[mock_event1, mock_event2], None]
        )
        source.pyvmomi_client.content.eventManager.CreateCollectorForEvents = Mock(
            return_value=mock_collector
        )

        await source._poll_for_events()

        assert source.queue.put.await_count == 2
        source.queue.put.assert_any_await({"event": mock_event1})
        source.queue.put.assert_any_await({"event": mock_event2})

    @pytest.mark.asyncio
    @patch("extensions.eda.plugins.event_source.vcenter_event_manager.vim")
    @patch("extensions.eda.plugins.event_source.vcenter_event_manager.vmware_obj_to_json")
    async def test_poll_for_events_multiple_pages(
        self, mock_obj_to_json, mock_vim, source
    ):
        events_page1 = [Mock() for _ in range(100)]  # pylint: disable=disallowed-name
        events_page2 = [Mock() for _ in range(50)]  # pylint: disable=disallowed-name
        mock_obj_to_json.side_effect = lambda x: {"event": x}

        mock_collector = Mock()
        mock_collector.ReadNextEvents = Mock(
            side_effect=[events_page1, events_page2, None]
        )
        source.pyvmomi_client.content.eventManager.CreateCollectorForEvents = Mock(
            return_value=mock_collector
        )

        await source._poll_for_events()

        assert source.queue.put.await_count == 150

    # Test start_polling
    @pytest.mark.asyncio
    @patch("extensions.eda.plugins.event_source.vcenter_event_manager.vim")
    async def test_start_polling_handles_invalid_state(self, mock_vim, source):
        # Create a proper exception class that inherits from Exception
        class InvalidStateException(Exception):
            pass

        # Mock vim.fault.InvalidState to be our exception class
        mock_vim.fault.InvalidState = InvalidStateException

        source._poll_for_events = AsyncMock(
            side_effect=[
                InvalidStateException(),
                None,
                asyncio.CancelledError(),
            ]
        )
        source._init_pyvmomi_client = Mock()

        with pytest.raises(asyncio.CancelledError):
            await source.start_polling()

        source._init_pyvmomi_client.assert_called_once()

    @pytest.mark.asyncio
    @patch("extensions.eda.plugins.event_source.vcenter_event_manager.vim")
    @patch("extensions.eda.plugins.event_source.vcenter_event_manager.logger")
    async def test_start_polling_handles_generic_exception(
        self, mock_logger, mock_vim, source
    ):
        # Create a proper exception class that inherits from Exception
        class InvalidStateException(Exception):
            pass

        # Mock vim.fault.InvalidState to be our exception class
        mock_vim.fault.InvalidState = InvalidStateException

        source._poll_for_events = AsyncMock(
            side_effect=[
                Exception("Test error"),
                asyncio.CancelledError(),
            ]
        )

        with pytest.raises(asyncio.CancelledError):
            await source.start_polling()

        mock_logger.exception.assert_called()

    # Test main function
    @pytest.mark.asyncio
    @patch("extensions.eda.plugins.event_source.vcenter_event_manager.PyvmomiClient")
    async def test_main_function(self, mock_client_class):
        mock_queue = AsyncMock(spec=asyncio.Queue)
        args = {
            "hostname": "vcenter.example.com",
            "username": "admin",
            "password": "password123",
        }

        mock_client = Mock()
        mock_client_class.return_value = mock_client

        with patch.object(
            VcenterEventManagerSource,
            "start_polling",
            new_callable=AsyncMock,
            side_effect=asyncio.CancelledError(),
        ):
            with pytest.raises(asyncio.CancelledError):
                await main(mock_queue, args)

    @pytest.mark.asyncio
    @patch("extensions.eda.plugins.event_source.vcenter_event_manager.PyvmomiClient")
    @patch("extensions.eda.plugins.event_source.vcenter_event_manager.logger")
    async def test_main_function_logs_exception(self, mock_logger, mock_client_class):
        mock_queue = AsyncMock(spec=asyncio.Queue)
        args = {
            "hostname": "vcenter.example.com",
            "username": "admin",
            "password": "password123",
        }

        mock_client = Mock()
        mock_client_class.return_value = mock_client

        test_error = Exception("Test error")
        with patch.object(
            VcenterEventManagerSource,
            "start_polling",
            new_callable=AsyncMock,
            side_effect=test_error,
        ):
            with pytest.raises(Exception):
                await main(mock_queue, args)

        mock_logger.exception.assert_called()

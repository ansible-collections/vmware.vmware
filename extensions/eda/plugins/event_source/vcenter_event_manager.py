# -*- coding: utf-8 -*-
#
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

DOCUMENTATION = r"""
module: vcenter_event_manager
short_description: Event Driven Ansible source for vCenter event manager.
description:
  - Poll the vCenter Event Manager for events, using them as a source for Event Driven Ansible.
  - This plugin can use the same environment variables as the rest of the VMWare collection to
    configure the instance connection.

author:
  - Ansible Eco Content Team (@eco-ansible-content)

extends_documentation_fragment:
  - vmware.vmware.base_options
  - vmware.vmware.additional_rest_options

options:
  interval:
    description:
      - THe number of seconds to wait before performing another query.
    required: false
    default: 60
    type: int

  initial_start_time:
    description:
      - Specify the time that an event must be recorded after to be considered new and captured by this plugin.
      - This value should be a date string in the format of "%Y-%m-%d %H:%M:%S".
      - If not specified, the plugin will use the current time as a default.
      - This option can be used to start tracking events from a specific time in the past.
    required: false
    type: int

  datacenter:
    description:
      - Specify the name or MOID of the datacenter that should be used to filter events to track.
      - By specifying a datacenter, only events related to entities in that datacenter will be tracked.
    required: false
    type: str

  event_type_ids:
    description:
      - A list of event type IDs to track.
      - If specified, only events with the type IDs listed will trigger the plugin.
      - Event IDs typically start with 'vim.event.' and can most easily be found in the vCenter Events Manager UI.
    required: false
    type: list
    elements: str

  event_type:
    description:
      - Whether to include system or user events.
      - User events describe things like logins, logouts, etc.
      - System events describe things like VM power on, power off, etc.
      - You can fiter either event type with O(user_names) if desired.
    required: false
    type: str
    choices: [ system, user ]
    default: system

  user_names:
    description:
      - A list of usernames to filter events by.
      - If specified, only events from the users listed will trigger the plugin.
      - Usernames typically start with a domain name and a backslash. Examples can be found in the vCenter Events Manager UI.
      - Not all events have an associated user. It may be an empty string or be completely absent.
        Setting this filter to any value will exclude these types of events.
    required: false
    type: list
    elements: str

  severity:
    description:
      - The severity of the events to track (also known as 'category' in the vCenter UI).
      - If specified, only events with the severity listed will be tracked.
      - Not all events have an associated severity. It may be an empty string or be completely absent.
        For example, events of type 'user' have no severity. Setting this filter to any value will
        exclude these types of events.
    required: false
    type: list
    elements: str
    choices: [ info, warning, error ]

  event_tags:
    description:
      - A list of tags that events must have to be tracked.
      - If specified, only events with all of the tags listed will be tracked.
      - You can include an empty string to match events with no tags. See the examples below for more details.
    required: false
    type: list
    elements: str
"""

EXAMPLES = r"""
---
# Full example rulebook
- name: Watch for new events
  hosts: localhost
  sources:
    - name: Watch for any system events
      vmware.vmware.vcenter_event_manager: {}

  rules:
    - name: New event
      condition: true
      action:
        debug:

---
# These are all different source examples
- name: Watch for alarm status changed events
  vmware.vmware.vcenter_event_manager:
    event_type: system
    event_type_ids:
     - vim.event.AlarmStatusChangedEvent

- name: Watch for a specific user's login/logout
  vmware.vmware.vcenter_event_manager:
    event_type: user
    user_names:
        - 'MY.DOMAIN.VSPHERE\some_username'

- name: Watch for updated change requests
  vmware.vmware.vcenter_event_manager:
    event_type: system
    severity:
        - warning

- name: Watch for events with the foo tag
  vmware.vmware.vcenter_event_manager:
    event_type: system
    event_tags:
        - "foo"

- name: Watch for events with the no tags
  vmware.vmware.vcenter_event_manager:
    event_type: system
    event_tags:
        - ""

- name: Watch for events relating to any entities in My-Datacenter
  vmware.vmware.vcenter_event_manager:
    event_type: system
    datacenter: My-Datacenter
"""

# Need to add the project root to the path so that we can import the module_utils.
# The EDA team may come up with a better solution for this in the future.
import os  # noqa: E402
import sys  # noqa: E402

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import asyncio  # noqa: E402
import logging  # noqa: E402
from datetime import datetime, timedelta  # noqa: E402
from typing import Any, Dict, List  # noqa: E402

from ansible.errors import AnsibleError  # noqa: E402
from ansible.module_utils.common.validation import check_type_int, check_type_bool
from plugins.module_utils.clients.pyvmomi import PyvmomiClient  # noqa: E402
from plugins.module_utils._facts import vmware_obj_to_json  # noqa: E402

try:
    from pyVmomi import vim
except ImportError:
    # handled by client
    pass


logger = logging.getLogger(__name__)


class VcenterEventManagerSource:
    def __init__(self, queue: asyncio.Queue, args: Dict[str, Any]):
        self.queue = queue
        self.plugin_args = self._validate_plugin_args(args)
        self._init_pyvmomi_client()
        self.poll_interval_seconds = int(self.plugin_args.get("interval", 60))
        _initial_start_time = self.plugin_args.get("initial_start_time")
        if _initial_start_time is not None:
            self.last_poll_start_time = datetime.strptime(
                _initial_start_time, "%Y-%m-%d %H:%M:%S"
            )
        else:
            self.last_poll_start_time = datetime.now()

    def _init_pyvmomi_client(self):
        """
        Initialize the pyvmomi client.
        """
        auth_arg_map = (
            ("hostname", "VMWARE_HOST", None, None, True),
            ("username", "VMWARE_USER", None, None, True),
            ("password", "VMWARE_PASSWORD", None, None, True),
            ("port", "VMWARE_PORT", check_type_int, 443, False),
            ("proxy_host", "VMWARE_PROXY_HOST", None, None, False),
            ("proxy_port", "VMWARE_PROXY_PORT", check_type_int, None, False),
            ("validate_certs", "VMWARE_VALIDATE_CERTS", check_type_bool, True, False),
        )
        auth_args = dict()
        for (
            plugin_arg_name,
            env_var_name,
            validation_function,
            default_value,
            required,
        ) in auth_arg_map:
            if self.plugin_args.get(plugin_arg_name) is not None:
                auth_args[plugin_arg_name] = self.plugin_args.get(plugin_arg_name)
            else:
                auth_args[plugin_arg_name] = os.getenv(env_var_name, default_value)

            if auth_args[plugin_arg_name] is None and required:
                raise AnsibleError(
                    "The %s plugin argument, or %s environment variable, is required."
                    % (plugin_arg_name, env_var_name)
                )

            if (
                validation_function is not None
                and auth_args[plugin_arg_name] is not None
            ):
                auth_args[plugin_arg_name] = validation_function(
                    auth_args[plugin_arg_name]
                )

        self.pyvmomi_client = PyvmomiClient(**auth_args)
        self._datacenter = None

    @property
    def datacenter(self):
        identifier = self.plugin_args.get("datacenter")
        if self._datacenter is None and identifier:
            results = self.pyvmomi_client.get_objs_by_name_or_moid(
                [vim.Datacenter], identifier, return_all=True
            )
            if len(results) > 1:
                raise AnsibleError(
                    "More than one datacenter with name or ID %s was found. This is an unsupported scenario in this plugin."
                    % identifier
                )
            elif len(results) == 0:
                raise AnsibleError(
                    "No datacenter with name or ID %s was found." % identifier
                )
            else:
                self._datacenter = results[0]

        return self._datacenter

    def _validate_plugin_args(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate the plugin non-authentication arguments.
        """
        # Ensure the correct type was specified, and default to system if not specified.
        event_type = args.get("event_type", "system")
        if event_type not in ["system", "user"]:
            raise AnsibleError(
                "The event_type plugin argument must be either 'system' or 'user'."
            )
        args["event_type"] = event_type

        severity = set(args.get("severity") or [])
        allowed_severity = set(["info", "warning", "error"])
        if severity and not severity.issubset(allowed_severity):
            raise AnsibleError(
                "The severity plugin argument can only contain the values: %s."
                % allowed_severity
            )

        return args

    def _create_time_filter(self, start_time: datetime = None):
        time_filter = vim.event.EventFilterSpec.ByTime()
        now = datetime.now()
        if start_time is None:
            start_time = self.last_poll_start_time

        end_time = now
        if end_time - start_time > timedelta(seconds=10 * self.poll_interval_seconds):
            logger.warning(
                "The polled time interval has grown to be greater than 10 times the polling interval."
                "If you see this message repeatedly, it means the plugin cannot process events fast enough or is consistently failing to process events. "
                "If no error is being logged, consider limitting the amount of events that are being polled."
            )
        time_filter.beginTime = start_time
        time_filter.endTime = end_time
        return time_filter

    def _normalize_events_page(self, events) -> List[Any]:
        if events is None:
            return []
        if isinstance(events, list):
            return events
        return [events]

    # entrypoint for main logic
    async def start_polling(self):
        """
        Main entrypoint for the plugin. Start the polling loop and keep running until the plugin is stopped.
        """
        logger.info("Poll sleep interval is %s seconds", self.poll_interval_seconds)

        while True:
            logger.debug("Starting poll iteration.")
            try:
                await self._poll_for_events()
            except vim.fault.InvalidState:
                logger.warning(
                    "vCenter authentication has expired. This is normal if it happens once in awhile; otherwise consider it an issue. Re-initializing the pyvmomi client."
                )
                self._init_pyvmomi_client()
                # Retry the poll immediately to avoid a loop of auth errors, which happens if the poll interval is long enough.
                continue
            except Exception as e:
                logger.exception("Error polling for events: %s", e)
                logger.info(
                    "Plugin will keep running, and increase the polled time interval to account for the error."
                )

            logger.debug("Sleeping for %s seconds", self.poll_interval_seconds)
            await asyncio.sleep(self.poll_interval_seconds)
            logger.debug("Ending poll iteration")

    async def _poll_for_events(self):
        """
        Poll for new records in the table since the polling_start_time. We update the list query
        with the latest timestamp seen, and then process any new records that are found.

        If we find any records, we update the latest_sys_updated_on_floor to the latest timestamp seen.
        """
        time_filter = self._create_time_filter()
        logger.debug(
            "Polling for events from %s to %s",
            time_filter.beginTime,
            time_filter.endTime,
        )
        filter_spec = vim.event.EventFilterSpec(
            time=time_filter, **self._create_event_filters()
        )
        event_collector = (
            self.pyvmomi_client.content.eventManager.CreateCollectorForEvents(
                filter_spec
            )
        )

        # page through events using ReadNextEvents
        page_size = 100

        while True:
            events_in_page = self._normalize_events_page(
                event_collector.ReadNextEvents(page_size)
            )
            if not events_in_page:
                break

            for event in events_in_page:
                await self.queue.put(vmware_obj_to_json(event))

        self.last_poll_start_time = time_filter.endTime
        logger.debug("Ending poll for events")

    def _create_event_filters(self):
        filters = dict()

        # Filter by specific event type ID
        if self.plugin_args.get("event_type_ids"):
            filters["eventTypeId"] = self.plugin_args.get("event_type_ids")

        # Filter by specific username, and system or user type
        user_filter = vim.event.EventFilterSpec.ByUsername()
        user_filter.systemUser = self.plugin_args.get("event_type") == "system"
        if self.plugin_args.get("user_names"):
            user_filter.userList = self.plugin_args.get("user_names")
        filters["userName"] = user_filter

        # Information, Warning, Error, etc
        if self.plugin_args.get("severity"):
            filters["category"] = self.plugin_args.get("severity")

        if self.datacenter is not None:
            filters["entity"] = vim.event.EventFilterSpec.ByEntity()
            filters["entity"].entity = self.datacenter
            filters["entity"].recursion = "all"

        # Choose events with the specified tags
        if self.plugin_args.get("event_tags"):
            filters["tag"] = self.plugin_args.get("event_tags")

        return filters


# Entrypoint from ansible-rulebook
async def main(queue: asyncio.Queue, args: Dict[str, Any]):
    vcenter_event_manager_source = VcenterEventManagerSource(queue, args)
    try:
        await vcenter_event_manager_source.start_polling()
    except Exception as e:
        logger.exception("Error occurred during polling: %s", e)
        raise e

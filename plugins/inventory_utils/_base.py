# Copyright: (c) 2024, Ansible Cloud Team
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from ansible.errors import AnsibleParserError
from ansible.plugins.inventory import BaseInventoryPlugin, Constructable, Cacheable
from ansible.parsing.yaml.objects import AnsibleVaultEncryptedUnicode
from ansible.module_utils.common.text.converters import to_native

from ansible_collections.vmware.vmware.plugins.module_utils.clients._pyvmomi import PyvmomiClient
from ansible_collections.vmware.vmware.plugins.module_utils.clients._rest import VmwareRestClient


class VmwareInventoryBase(BaseInventoryPlugin, Constructable, Cacheable):

    def initialize_pyvmomi_client(self, config_data):
        """
        Create an instance of the pyvmomi client based on the user's input (auth) parameters
        """
        # update _options from config data
        self._consume_options(config_data)

        username, password = self.get_credentials_from_options()

        try:
            self.pyvmomi_client = PyvmomiClient({
                'hostname': self.get_option("hostname"),
                'username': username,
                'password': password,
                'port': self.get_option("port"),
                'validate_certs': self.get_option("validate_certs"),
                'http_proxy_host': self.get_option("proxy_host"),
                'http_proxy_port': self.get_option("proxy_port")
            })
        except Exception as e:
            raise AnsibleParserError(message=to_native(e))

    def initialize_rest_client(self, config_data):
        """
        Create an instance of the REST client based on the user's input (auth) parameters
        """
        # update _options from config data
        self._consume_options(config_data)

        username, password = self.get_credentials_from_options()

        try:
            self.rest_client = VmwareRestClient({
                'hostname': self.get_option("hostname"),
                'username': username,
                'password': password,
                'port': self.get_option("port"),
                'validate_certs': self.get_option("validate_certs"),
                'http_proxy_host': self.get_option("proxy_host"),
                'http_proxy_port': self.get_option("proxy_port"),
                'http_proxy_protocol': self.get_option("proxy_protocol")
            })
        except Exception as e:
            raise AnsibleParserError(message=to_native(e))

    def get_credentials_from_options(self):
        """
        The username and password options can be plain text, jinja templates, or encrypted strings.
        This method handles these different options and returns a plain text version of the username and password
        Returns:
            A tuple of the plain text username and password
        """
        username = self.get_option("username")
        password = self.get_option("password")

        if self.templar.is_template(password):
            password = self.templar.template(variable=password, disable_lookups=False)
        elif isinstance(password, AnsibleVaultEncryptedUnicode):
            password = password.data

        if self.templar.is_template(username):
            username = self.templar.template(variable=username, disable_lookups=False)
        elif isinstance(username, AnsibleVaultEncryptedUnicode):
            username = username.data

        return (username, password)

    def get_cached_result(self, cache, cache_key):
        """
        Checks if a cache is available and if there's already data in the cache for this plugin.
        Returns the data if some is found.
        Relies on the caching mechanism found in the Ansible base classes
        Args:
            cache: bool, True if the plugin should use a cache
            cache_key: str, The key where data is stored in the cache
        Returns:
            tuple(bool, dict or None)
            First value indicates if a cached result was found
            Second value is the cached data. Cached data could be empty, which is why the first value is needed.
        """
        # false when refresh_cache or --flush-cache is used
        if not cache:
            return False, None

        # check user-specified directive
        if not self.get_option("cache"):
            return False, None

        try:
            cached_value = self._cache[cache_key]
        except KeyError:
            # if cache expires or cache file doesn"t exist
            return False, None

        return True, cached_value

    def update_cached_result(self, cache, cache_key, result):
        """
        If the user wants to use a cache, add the new results to the cache.
        Args:
            cache: bool, True if the plugin should use a cache
            cache_key: str, The key where data is stored in the cache
            result: dict, The data to store in the cache
        Returns:
            None
        """
        if not self.get_option("cache"):
            return

        # We weren't explicitly told to flush the cache, and there's already a cache entry,
        # this means that the result we're being passed came from the cache.  As such we don't
        # want to "update" the cache as that could reset a TTL on the cache entry.
        if cache and cache_key in self._cache:
            return

        self._cache[cache_key] = result

    def get_objects_by_type(self, vim_type):
        """
        Searches the requested search paths for objects of type vim_type. If the search path
        doesn't actually exist, continue. If no search path is given, check everywhere
        Args:
            vim_type: The vim object type. It should be given as a list, like [vim.HostSystem]
        Returns:
            List of objects that exist in the search path(s) and match the vim type
        """
        if not self.get_option('search_paths'):
            return self.pyvmomi_client.get_all_objs_by_type(vimtype=vim_type)

        objects = []
        for search_path in self.get_option('search_paths'):
            folder = self.pyvmomi_client.si.content.searchIndex.FindByInventoryPath(search_path)
            if not folder:
                continue
            objects += self.pyvmomi_client.get_all_objs_by_type(vimtype=vim_type, folder=folder)

        return objects

    def gather_tags(self, object_moid):
        """
        Given an object moid, gather any tags attached to the object.
        Args:
            object_moid: str, The object's MOID
        Returns:
            tuple
            First item is a dict with the object's tags. Keys are tag IDs and values are tag names
            Second item is a dict of the object's tag categories. Keys are category names and values are a dict
                containing the tags in the category
        """
        if not hasattr(self, '_known_tag_category_ids_to_name'):
            self._known_tag_category_ids_to_name = {}

        tags = {}
        tags_by_category = {}
        for tag in self.rest_client.get_tags_by_host_moid(object_moid):
            tags[tag.id] = tag.name
            try:
                category_name = self._known_tag_category_ids_to_name[tag.category_id]
            except KeyError:
                category_name = self.rest_client.tag_category_service.get(tag.category_id).name
                self._known_tag_category_ids_to_name[tag.category_id] = category_name

            if not tags_by_category.get(category_name):
                tags_by_category[category_name] = []

            tags_by_category[category_name].append({tag.id: tag.name})

        return tags, tags_by_category

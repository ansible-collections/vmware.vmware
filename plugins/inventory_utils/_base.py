# Copyright: (c) 2024, Ansible Cloud Team
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from abc import ABC, abstractmethod
from ansible.errors import AnsibleError
from ansible.errors import AnsibleParserError
from ansible.plugins.inventory import BaseInventoryPlugin, Constructable, Cacheable
from ansible.module_utils.common.text.converters import to_native
from ansible.module_utils.common.dict_transformations import camel_dict_to_snake_dict
from ansible.utils.display import Display
try:
    # only available in ansible-core 2.19+. If not available, fake it with AnsibleVaultEncryptedUnicode
    from ansible.parsing.vault import EncryptedString as VaultEncryptedUnicode
except ImportError:
    from ansible.parsing.yaml.objects import AnsibleVaultEncryptedUnicode as VaultEncryptedUnicode

from ansible_collections.vmware.vmware.plugins.module_utils.clients.pyvmomi import PyvmomiClient
from ansible_collections.vmware.vmware.plugins.module_utils.clients.rest import VmwareRestClient
from ansible_collections.vmware.vmware.plugins.module_utils._folder_paths import (
    get_folder_path_of_vsphere_object
)
from ansible_collections.vmware.vmware.plugins.module_utils.facts._converters import (
    vmware_obj_to_json,
    properties_from_collector,
    flatten_dict
)

try:
    from pyVmomi import vmodl
except ImportError:
    # Already handled in base class
    pass


DISPLAY = Display()


class VmwareInventoryHost(ABC):
    """
    This is an abstract class. Its meant to be extended by a class more closely rerpresenting a specific
    VMware object, like VM or ESXi host
    """
    RESERVED_HOST_VARIABLE_PREFIX = 'vmware_inventory_'
    RESERVED_HOST_VARIABLES = ['name', 'tags']

    def __init__(self):
        self.object = None
        self.inventory_hostname = None
        self.path = ''
        self.properties = dict()

    @classmethod
    def create_from_cache(cls, inventory_hostname, properties):
        """
        Create the class from the inventory cache. We don't want to refresh the data or make any calls to vCenter.
        Properties are populated from whatever we had previously cached.
        """
        host = cls()
        host.inventory_hostname = inventory_hostname
        host.properties = properties
        return host

    @classmethod
    def create_from_vcenter_object(cls, vmware_object, properties_to_gather, pyvmomi_client, prop_set=None, gather_path=True):
        """
        Create the class from a vCenter object reference.

        When prop_set is provided, properties come from a PropertyCollector result.
        Otherwise properties are read from the object via vmware_obj_to_json().
        """
        host = cls()
        host.object = vmware_object
        if gather_path:
            host.path = get_folder_path_of_vsphere_object(vmware_object)
        host._set_inventory_properties(properties_to_gather, pyvmomi_client, prop_set)
        return host

    @abstractmethod
    def get_tags(self, rest_client):
        pass

    def _set_inventory_properties(self, properties_to_gather, pyvmomi_client, prop_set=None):
        if prop_set is not None:
            self.properties = properties_from_collector(prop_set)
        else:
            self.properties = vmware_obj_to_json(self.object, properties_to_gather)
        if self.path:
            self.properties['path'] = self.path
        self.properties['moid'] = self.object._GetMoId()
        self._add_custom_values_to_properties(properties_to_gather, pyvmomi_client)

    def _add_custom_values_to_properties(self, properties_to_gather, pyvmomi_client):
        if properties_to_gather and 'customValue' not in properties_to_gather:
            return

        if not hasattr(self.object, "customValue"):
            return

        self.properties['customValue'] = {}
        field_mgr = pyvmomi_client.custom_field_mgr
        for cust_value in self.object.customValue:
            self.properties['customValue'][
                [y.name for y in field_mgr if y.key == cust_value.key][0]
            ] = cust_value.value

    def sanitize_properties(self):
        self.properties = camel_dict_to_snake_dict(self.properties)

    def flatten_properties(self):
        self.properties = flatten_dict(self.properties)

    def rename_reserved_variables(self):
        for variable in self.RESERVED_HOST_VARIABLES:
            if variable in self.properties:
                self.properties[f"{self.RESERVED_HOST_VARIABLE_PREFIX}{variable}"] = self.properties.pop(variable)


class VmwareInventoryBase(BaseInventoryPlugin, Constructable, Cacheable):

    @property
    def vim_class(self):
        raise NotImplementedError("Inventory plugin classes must define the vim_class property.")

    @property
    def rest_class(self):
        raise NotImplementedError("Inventory plugin classes must define the rest_class property.")

    def parse(self, inventory, loader, path, cache=True):
        """
        This is the main entrypoint for the inventory. It will read the config file and update
        an internal dict (_options) with the user input. Then, it will try to load the results
        from a cache if appropriate. Otherwise, it will load the results from vCenter.
        """
        super().parse(inventory, loader, path, cache=cache)
        self._consume_options(self._read_config_data(path))
        cache_key = self.get_cache_key(path)
        result_was_cached, results = self.get_cached_result(cache, cache_key)

        if result_was_cached:
            self.populate_from_cache(results)
        else:
            results = self.populate_from_vcenter()

        self.update_cached_result(cache, cache_key, results)

    def initialize_pyvmomi_client(self):
        """
        Create an instance of the pyvmomi client based on the user's input (auth) parameters
        """
        username, password = self.get_credentials_from_options()

        try:
            self.pyvmomi_client = PyvmomiClient(
                hostname=self.get_option("hostname"),
                username=username,
                password=password,
                port=self.get_option("port"),
                validate_certs=self.get_option("validate_certs"),
                proxy_host=self.get_option("proxy_host"),
                proxy_port=self.get_option("proxy_port")
            )
        except Exception as e:
            raise AnsibleParserError(message=to_native(e))

    def initialize_rest_client(self):
        """
        Create an instance of the REST client based on the user's input (auth) parameters
        """
        username, password = self.get_credentials_from_options()

        try:
            self.rest_client = VmwareRestClient(
                hostname=self.get_option("hostname"),
                username=username,
                password=password,
                port=self.get_option("port"),
                validate_certs=self.get_option("validate_certs"),
                proxy_host=self.get_option("proxy_host"),
                proxy_port=self.get_option("proxy_port"),
                proxy_protocol=self.get_option("proxy_protocol")
            )
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
        elif isinstance(password, VaultEncryptedUnicode):
            if hasattr(password, 'data'):
                # this is ansible-core<2.19
                password = password.data
            else:
                # this is ansible-core>=2.19
                password = password._decrypt()

        if self.templar.is_template(username):
            username = self.templar.template(variable=username, disable_lookups=False)
        elif isinstance(username, VaultEncryptedUnicode):
            if hasattr(username, 'data'):
                # this is ansible-core<2.19
                username = username.data
            else:
                # this is ansible-core>=2.19
                username = username._decrypt()

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

    def get_property_collector_results_by_type(self, vim_type, properties_to_gather):
        """
        Use the PropertyCollector to retrieve objects and only the requested properties.

        Args:
            vim_type: A single vim type, for example vim.VirtualMachine
            properties_to_gather: List of property paths. An empty list is not supported here.

        Returns:
            List of vmodl query ObjectContent results (obj + propSet)
        """
        query_paths = [prop for prop in properties_to_gather if prop != 'customValue']
        if not self.get_option('search_paths'):
            return self.pyvmomi_client.get_managed_object_references(
                vimtype=vim_type,
                properties=query_paths,
                folder=None,
            )

        results = []
        for search_path in self.get_option('search_paths'):
            folder = self.pyvmomi_client.si.content.searchIndex.FindByInventoryPath(search_path)
            if not folder:
                continue
            results.extend(self.pyvmomi_client.get_managed_object_references(
                vimtype=vim_type,
                properties=query_paths,
                folder=folder,
            ))

        return results

    def iter_inventory_sources(self, properties_to_gather):
        """
        Yield (vmware_object, prop_set) pairs for inventory construction.

        prop_set is None when all properties should be read from the object.
        """
        if properties_to_gather:
            for obj_content in self.get_property_collector_results_by_type(self.vim_class, properties_to_gather):
                yield obj_content.obj, obj_content.propSet
            return

        for vmware_object in self.get_objects_by_type(vim_type=[self.vim_class]):
            yield vmware_object, None

    def add_tags_from_bulk_result(self, vmware_host_object, moid_to_tags):
        """
        Assign tags and tags_by_category to a host object using a pre-fetched bulk result.

        Args:
            vmware_host_object: VmwareInventoryHost subclass instance
            moid_to_tags: dict mapping MOID strings to lists of tag objects,
                          as returned by get_tags_for_vm_moids_bulk / get_tags_for_host_moids_bulk
        Returns:
            None
        """
        if not hasattr(self, '_known_tag_category_ids_to_name'):
            self._known_tag_category_ids_to_name = {}

        moid = vmware_host_object.object._GetMoId()
        tags = {}
        tags_by_category = {}
        for tag in moid_to_tags.get(moid, []):
            tags[tag.id] = tag.name
            if tag.category_id not in self._known_tag_category_ids_to_name:
                self._known_tag_category_ids_to_name[tag.category_id] = (
                    self.rest_client.tag_category_service.get(tag.category_id).name
                )
            category_name = self._known_tag_category_ids_to_name[tag.category_id]
            tags_by_category.setdefault(category_name, []).append({tag.id: tag.name})

        vmware_host_object.properties['tags'] = tags
        vmware_host_object.properties['tags_by_category'] = tags_by_category

    def add_tags_to_object_properties(self, vmware_host_object):
        """
        Given a subclass of VmwareInventoryHost object, gather any tags attached to the object and add them
        to the properties. Also break the tags into the categories and add those to the objects properties.
        Args:
            vmware_host_object: VmwareInventoryHost, A subclass instance of the VmwareInventoryHost class
        Returns:
            None
        """
        if not hasattr(self, '_known_tag_category_ids_to_name'):
            self._known_tag_category_ids_to_name = {}

        tags = {}
        tags_by_category = {}
        for tag in vmware_host_object.get_tags(self.rest_client):
            tags[tag.id] = tag.name
            try:
                category_name = self._known_tag_category_ids_to_name[tag.category_id]
            except KeyError:
                category_name = self.rest_client.tag_category_service.get(tag.category_id).name
                self._known_tag_category_ids_to_name[tag.category_id] = category_name

            if not tags_by_category.get(category_name):
                tags_by_category[category_name] = []

            tags_by_category[category_name].append({tag.id: tag.name})

        vmware_host_object.properties['tags'] = tags
        vmware_host_object.properties['tags_by_category'] = tags_by_category

    def set_inventory_hostname(self, vmware_host_object):
        """
        The user can specify a list of jinja templates, and the first valid template should be used for the
        host's inventory hostname. The inventory hostname is mostly for decorative purposes since the
        ansible_host value takes precedence when trying to connect.
        """
        hostname = None
        errors = []

        for hostname_pattern in self.get_option("hostnames"):
            try:
                hostname = self._compose(template=hostname_pattern, variables=vmware_host_object.properties)
            except Exception as e:
                if self.get_option("strict"):
                    raise AnsibleError(
                        "Could not compose %s as hostnames - %s"
                        % (hostname_pattern, to_native(e))
                    )

                errors.append((hostname_pattern, str(e)))
            if hostname:
                vmware_host_object.inventory_hostname = hostname
                return

        raise AnsibleError(
            "Could not template any hostname for host, errors for each preference: %s"
            % (", ".join(["%s: %s" % (pref, err) for pref, err in errors]))
        )

    def set_host_variables_from_host_properties(self, vmware_host_object):
        if self.get_option("sanitize_property_names"):
            vmware_host_object.sanitize_properties()

        if self.get_option("flatten_nested_properties"):
            vmware_host_object.flatten_properties()

        if self.get_option("rename_reserved_variables"):
            vmware_host_object.rename_reserved_variables()

        for k, v in vmware_host_object.properties.items():
            self.inventory.set_variable(vmware_host_object.inventory_hostname, k, v)

    def add_host_to_groups_based_on_path(self, vmware_host_object):
        """
        If the user desires, create groups based on each VM's path. A group is created for each
        step down in the path, with the group from the step above containing subsequent groups.
        Optionally, the user can add a prefix to the groups created by this process.
        The final group in the path will be where the VM is added.
        """
        if not self.get_option("group_by_paths"):
            return

        path_parts = vmware_host_object.path.split('/')
        group_name_parts = []
        last_created_group = None

        if self.get_option("group_by_paths_prefix"):
            group_name_parts = [self.get_option("group_by_paths_prefix")]

        for path_part in path_parts:
            if not path_part:
                continue
            group_name_parts.append(path_part)
            group_name = self._sanitize_group_name('_'.join(group_name_parts))
            group = self.inventory.add_group(group_name)

            if last_created_group:
                self.inventory.add_child(last_created_group, group)
            last_created_group = group

        if last_created_group:
            self.inventory.add_host(vmware_host_object.inventory_hostname, last_created_group)

    def host_should_be_filtered_out(self, vmware_host_object):
        """
            Returns true if the provided host and properties cause any of the filter expressions
            to evaluate to true. This indicates that the host should be removed from the final
            inventory.
            Returns false otherwise.
        """
        for jinja_expression in self.get_option('filter_expressions'):
            try:
                if self._compose(jinja_expression, vmware_host_object.properties):
                    return True
            except Exception as e:  # pylint: disable=broad-except
                if self.get_option("strict"):
                    raise AnsibleError(
                        "Could not evaluate %s as host filter - %s" % (jinja_expression, to_native(e))
                    )

        return False

    def _handle_duplicate_host(self, existing_host_vars, new_host):
        """
            Handles the instance where two hosts have the same inventory hostname. If the user has strict set to true, this
            should be an error. Otherwise it is just a warning.
            Args:
                existing_host_vars: dict, The host properties of the existing host (for example, hostvars[inventory_hostname])
                new_host: VmwareInventoryHost, The host object that was going to be added, but is a duplicate hostname of another
        """
        if self.get_option('strict'):
            raise AnsibleError(
                "Host %s has the same inventory hostname (%s) as %s. This is a fatal issue since strict is true." %
                (existing_host_vars['moid'], new_host.inventory_hostname, new_host.object._GetMoId())
            )
        else:
            DISPLAY.warning(
                "Host %s has the same inventory hostname (%s) as %s. Only the first host, %s, will be included since strict is false." %
                (existing_host_vars['moid'], new_host.inventory_hostname, new_host.object._GetMoId(), existing_host_vars['moid'])
            )

    def add_host_object_from_vcenter_to_inventory(self, new_host, hostvars):
        """
            Add a new host to the inventory and populate host vars based on object properties.
            If the host should be filtered out or if a host with the same name already exists, this method will handle that
            and simply return without processing the host.
            Args:
                new_host: VmwareInventoryHost, The new host to add to the inventory
                hostvars: dict, The hostvars dict that should be updated with the new host's properties
        """
        if new_host.inventory_hostname in hostvars:
            self._handle_duplicate_host(hostvars[new_host.inventory_hostname], new_host)
            return

        if self.host_should_be_filtered_out(new_host):
            return

        hostvars[new_host.inventory_hostname] = new_host.properties
        self.inventory.add_host(new_host.inventory_hostname)
        self.set_default_ansible_host_var(new_host)

        _strict = self.get_option("strict")
        self._set_composite_vars(
            self.get_option("compose"), new_host.properties, new_host.inventory_hostname, strict=_strict)
        self._add_host_to_composed_groups(
            self.get_option("groups"), new_host.properties, new_host.inventory_hostname, strict=_strict)
        self._add_host_to_keyed_groups(
            self.get_option("keyed_groups"), new_host.properties, new_host.inventory_hostname, strict=_strict)

        self.add_host_to_groups_based_on_path(new_host)
        self.set_host_variables_from_host_properties(new_host)

    def set_default_ansible_host_var(self, vmware_host_object):
        """
            Sets the default ansible_host var. This is usually an IP that is dependent on the object type.
            This is a default because the user can override this via compose
            Args:
              vmware_host_object: The host object that should be used. The type will be dependent on the plugin type.
        """
        raise NotImplementedError('ansible_host should be defined in the inventory plugin class.')

    def _handle_managed_object_not_found_error(self, vmware_object, object_name=None):
        """
            Handles the situation where an object could no longer be found mid flight. This is a common situation in large
            environments where VMs are moving or being created/destroyed.
            The user can choose if these issues are critical or not.
            Args:
                vmware_object: The object that is missing. We will try to get the moid/name from the object in case it was
                               cached somewhere along the way, but that may not be possible.
        """
        try:
            moid = vmware_object._GetMoId()
        except vmodl.fault.ManagedObjectNotFound:
            moid = "unknown"

        try:
            name = object_name or vmware_object.name
        except (vmodl.fault.ManagedObjectNotFound, AttributeError):
            name = "unknown"

        message = (
            "While attempting to read a vSphere object (name: %s, moid: %s), "
            "the object was unable to be found. This can be due to the object being "
            "moved, renamed, or deleted."
        ) % (name, moid)

        if self.get_option('strict'):
            raise AnsibleError(message)
        else:
            DISPLAY.warning(message)

    def populate_from_vcenter(self):
        """
        Populate inventory data from vCenter.
        """
        hostvars = {}
        properties_to_gather = self.parse_properties_param()
        gather_tags = self.get_option("gather_tags")
        self.initialize_pyvmomi_client()
        if gather_tags:
            self.initialize_rest_client()

        sources = list(self.iter_inventory_sources(properties_to_gather))
        moid_to_tags = self.rest_client._get_tags_for_moids_bulk(
            [obj._GetMoId() for obj, _ in sources], self.rest_class  # pylint: disable=disallowed-name
        ) if gather_tags else {}

        for vmware_object, prop_set in sources:
            try:
                inven_object = self._hydrate_inventory_host_from_vsphere_props(
                    vmware_object=vmware_object,
                    prop_set=prop_set,
                    properties_to_gather=properties_to_gather
                )
            except vmodl.fault.ManagedObjectNotFound:
                self._handle_managed_object_not_found_error(vmware_object=vmware_object)
                continue

            if not inven_object:
                continue

            if gather_tags:
                self.add_tags_from_bulk_result(inven_object, moid_to_tags)
            self.set_inventory_hostname(inven_object)
            self.add_host_object_from_vcenter_to_inventory(new_host=inven_object, hostvars=hostvars)

        return hostvars

    def parse_properties_param(self):
        """
        The properties option can be a variety of inputs from the user and we need to
        manipulate it into a list of properties that can be used later.
        This method may be extended by plugin classes, for custom property parsing.
        Returns:
          A list of property names that should be returned in the inventory. An empty
          list means all properties should be collected
        """
        properties_param = self.get_option("properties")
        if not isinstance(properties_param, list):
            properties_param = [properties_param]

        if "all" in properties_param:
            return []

        if "name" not in properties_param:
            properties_param.append("name")

        return properties_param

    def _hydrate_inventory_host_from_vsphere_props(self, vmware_object, prop_set, properties_to_gather):
        """
            Create an object that represents an inventory host using a vmware object and properties from vCenter.

            This method should be where class specific logic for mapping properties from vSphere objects
            to inventory hosts should be kept. This method is wrapped in a try/except to protect against
            objects being moved or deleted in vSphere. So implementation should focus on performing all
            property hydration within this method.
            Returns:
                Host object if one was able to be created, else None
        """
        raise NotImplementedError("Inventory plugin classes must define this method.")

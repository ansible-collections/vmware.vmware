# -*- coding: utf-8 -*-

# Copyright: (c) 2023, Ansible Cloud Team (@ansible-collections)
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
#

# Note: This utility is considered private, and can only be referenced from inside the vmware.vmware collection.
#       It may be made public at a later date

from __future__ import absolute_import, division, print_function
__metaclass__ = type

import traceback

REQUESTS_IMP_ERR = None
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    REQUESTS_IMP_ERR = traceback.format_exc()
    HAS_REQUESTS = False

VSPHERE_IMP_ERR = None
try:
    from com.vmware.vapi.std_client import DynamicID
    from vmware.vapi.vsphere.client import create_vsphere_client
    from com.vmware.vapi.std.errors_client import Unauthorized
    from com.vmware.content.library_client import Item
    from com.vmware.vcenter_client import (Folder,
                                           Datacenter,
                                           ResourcePool,
                                           VM,
                                           Cluster,
                                           Host,
                                           VM)
    HAS_VSPHERE = True
except ImportError:
    VSPHERE_IMP_ERR = traceback.format_exc()
    HAS_VSPHERE = False

try:
    from requests.packages import urllib3
    HAS_URLLIB3 = True
except ImportError:
    try:
        import urllib3
        HAS_URLLIB3 = True
    except ImportError:
        HAS_URLLIB3 = False

from ansible.module_utils.basic import env_fallback, missing_required_lib
from ansible.module_utils._text import to_native


class VmwareRestClient(object):
    def __init__(self, module):
        """
        Constructor

        """
        self.module = module
        self.params = module.params
        self.check_required_library()
        self.api_client = self.connect_to_vsphere_client()

    # Helper function
    def get_error_message(self, error):
        """
        Helper function to show human readable error messages.
        """
        err_msg = []
        if not error.messages:
            if isinstance(error, Unauthorized):
                return "Authorization required."
            return "Generic error occurred."

        for err in error.messages:
            err_msg.append(err.default_message % err.args)

        return " ,".join(err_msg)

    def check_required_library(self):
        """
        Check required libraries

        """
        if not HAS_REQUESTS:
            self.module.fail_json(msg=missing_required_lib('requests'),
                                  exception=REQUESTS_IMP_ERR)
        if not HAS_VSPHERE:
            self.module.fail_json(
                msg=missing_required_lib('vSphere Automation SDK',
                                         url='https://code.vmware.com/web/sdk/7.0/vsphere-automation-python'),
                exception=VSPHERE_IMP_ERR)

    @staticmethod
    def vmware_client_argument_spec():
        return dict(
            hostname=dict(type='str',
                          fallback=(env_fallback, ['VMWARE_HOST'])),
            username=dict(type='str',
                          fallback=(env_fallback, ['VMWARE_USER']),
                          aliases=['user', 'admin']),
            password=dict(type='str',
                          fallback=(env_fallback, ['VMWARE_PASSWORD']),
                          aliases=['pass', 'pwd'],
                          no_log=True),
            port=dict(type='int',
                      default=443,
                      fallback=(env_fallback, ['VMWARE_PORT'])),
            protocol=dict(type='str',
                          default='https',
                          choices=['https', 'http']),
            validate_certs=dict(type='bool',
                                fallback=(env_fallback, ['VMWARE_VALIDATE_CERTS']),
                                default=True),
            proxy_host=dict(type='str',
                            required=False,
                            default=None,
                            fallback=(env_fallback, ['VMWARE_PROXY_HOST'])),
            proxy_port=dict(type='int',
                            required=False,
                            default=None,
                            fallback=(env_fallback, ['VMWARE_PROXY_PORT'])),
        )

    def connect_to_vsphere_client(self):
        """
        Connect to vSphere API Client with Username and Password

        """
        username = self.params.get('username')
        password = self.params.get('password')
        hostname = self.params.get('hostname')
        validate_certs = self.params.get('validate_certs')
        port = self.params.get('port')
        session = requests.Session()
        session.verify = validate_certs
        protocol = self.params.get('protocol')
        proxy_host = self.params.get('proxy_host')
        proxy_port = self.params.get('proxy_port')

        if validate_certs is False:
            if HAS_URLLIB3:
                urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        if all([protocol, proxy_host, proxy_port]):
            proxies = {protocol: "{0}://{1}:{2}".format(protocol, proxy_host, proxy_port)}
            session.proxies.update(proxies)

        if not all([hostname, username, password]):
            self.module.fail_json(msg="Missing one of the following : hostname, username, password."
                                      " Please read the documentation for more information.")

        msg = "Failed to connect to vCenter or ESXi API at %s:%s" % (hostname, port)
        try:
            client = create_vsphere_client(
                server="%s:%s" % (hostname, port),
                username=username,
                password=password,
                session=session
            )
        except requests.exceptions.SSLError as ssl_exc:
            msg += " due to SSL verification failure"
            self.module.fail_json(msg="%s : %s" % (msg, to_native(ssl_exc)))
        except Exception as generic_exc:
            self.module.fail_json(msg="%s : %s" % (msg, to_native(generic_exc)))

        if client is None:
            self.module.fail_json(msg="Failed to login to %s" % hostname)

        return client

    def get_vm_by_name(self, name):
        """
        Returns a VM object that matches the given name.

        Args:
            name (str): The name of VM to look for

        Returns:
            list(str): VM object matching the name provided. Returns None if no
            matches are found
        """
        vms = self.api_client.vcenter.VM.list(
            VM.FilterSpec(names=set([name]))
        )

        if len(vms) == 0:
            return None

        return vms[0]

    def get_library_item_by_name(self, name):
        """
        Returns the identifier of the library item with the given name.

        Args:
            name (str): The name of item to look for

        Returns:
            str: The item ID or None if the item is not found
        """
        find_spec = Item.FindSpec(name=name)
        item_ids = self.api_client.content.library.Item.find(find_spec)
        item_id = item_ids[0] if item_ids else None
        return item_id

    def get_library_by_name(self, name):
        """
        Returns the identifier of the library given by library name.
        Args:
            name (str): The name of the lubrary
        Returns:
            str: The library ID or None if the library is not found
        """
        cl_find_spec = self.api_client.content.Library.FindSpec(name=name)
        cl_item_ids = self.api_client.content.Library.find(cl_find_spec)
        return cl_item_ids[0] if cl_item_ids else None

    def get_library_item_from_content_library_name(self, name, content_library_name):
        """
        Returns the identifier of the library item with the given name in the specified
        content library.
        Args:
            name (str): The name of item to look for
            content_library_name (str): The name of the content library to search in
        Returns:
            str: The item ID or None if the item is not found
        """
        cl_item_id = self.get_library_by_name(content_library_name)
        if cl_item_id:
            find_spec = Item.FindSpec(name=name, library_id=cl_item_id)
            item_ids = self.api_client.content.library.Item.find(find_spec)
            item_id = item_ids[0] if item_ids else None
            return item_id
        else:
            return None

    def get_datacenter_by_name(self, datacenter_name):
        """
        Returns the identifier of a datacenter
        Note: The method assumes only one datacenter with the mentioned name.
        """
        if datacenter_name is None:
            return None

        filter_spec = Datacenter.FilterSpec(names=set([datacenter_name]))
        datacenter_summaries = self.api_client.vcenter.Datacenter.list(filter_spec)
        return datacenter_summaries[0].datacenter if len(datacenter_summaries) > 0 else None

    def get_datacenters_set_by_name(self, datacenter_name):
        datacenter = self.get_datacenter_by_name(datacenter_name)
        return set([datacenter]) if datacenter else set()

    def get_folder_by_name(self, folder_name, datacenter_name=None):
        """
        Returns the identifier of a folder
        with the mentioned names.
        """
        if folder_name is None:
            return None
        datacenters = self.get_datacenters_set_by_name(datacenter_name)
        filter_spec = Folder.FilterSpec(type=Folder.Type.VIRTUAL_MACHINE,
                                        names=set([folder_name]),
                                        datacenters=datacenters)
        folder_summaries = self.api_client.vcenter.Folder.list(filter_spec)
        return folder_summaries[0].folder if len(folder_summaries) > 0 else None

    def get_resource_pool_by_name(self, resourcepool_name, datacenter_name=None, cluster_name=None, host_name=None):
        """
        Returns the identifier of a resource pool
        with the mentioned names.
        """
        datacenters = self.get_datacenters_set_by_name(datacenter_name)
        clusters = None
        if cluster_name:
            clusters = self.get_cluster_by_name(cluster_name, datacenter_name)
            if clusters:
                clusters = set([clusters])
        hosts = None
        if host_name:
            hosts = self.get_host_by_name(host_name, datacenter_name)
            if hosts:
                hosts = set([hosts])
        names = set([resourcepool_name]) if resourcepool_name else None
        filter_spec = ResourcePool.FilterSpec(datacenters=datacenters,
                                              names=names,
                                              clusters=clusters)
        resource_pool_summaries = self.api_client.vcenter.ResourcePool.list(filter_spec)
        resource_pool = resource_pool_summaries[0].resource_pool if len(resource_pool_summaries) > 0 else None
        return resource_pool

    def get_cluster_by_name(self, cluster_name, datacenter_name=None):
        """
        Returns the identifier of a cluster
        with the mentioned names.
        """
        datacenters = self.get_datacenters_set_by_name(datacenter_name)
        names = set([cluster_name]) if cluster_name else None
        filter_spec = Cluster.FilterSpec(datacenters=datacenters, names=names)
        cluster_summaries = self.api_client.vcenter.Cluster.list(filter_spec)
        return cluster_summaries[0].cluster if len(cluster_summaries) > 0 else None

    def get_host_by_name(self, host_name, datacenter_name=None):
        """
        Returns the identifier of a Host
        with the mentioned names.
        """
        datacenters = self.get_datacenters_set_by_name(datacenter_name)
        names = set([host_name]) if host_name else None
        filter_spec = Host.FilterSpec(datacenters=datacenters, names=names)
        host_summaries = self.api_client.vcenter.Host.list(filter_spec)
        return host_summaries[0].host if len(host_summaries) > 0 else None

    def get_vm_obj_by_name(self, vm_name, datacenter_name=None):
        """
        Returns the identifier of a VM with the mentioned names.
        """
        datacenters = self.get_datacenters_set_by_name(datacenter_name)
        names = set([vm_name]) if vm_name else None
        filter_spec = VM.FilterSpec(datacenters=datacenters, names=names)
        vm_summaries = self.api_client.vcenter.VM.list(filter_spec)
        return vm_summaries[0].vm if len(vm_summaries) > 0 else None

    def obj_to_dict(self, vmware_obj, r):
        """
        Tranform VMware SDK object to dictionary.
        Args:
            vmware_obj: Object to transform.
            r: Dictionary to fill with object data.
        """
        for k, v in vars(vmware_obj).items():
            if not k.startswith('_'):
                if hasattr(v, '__dict__') and not isinstance(v, str):
                    self.obj_to_dict(v, r[k])
                elif isinstance(v, int):
                    r[k] = int(v)
                else:
                    r[k] = str(v)

    def get_category_by_name(self, category_name=None):
        """
        Return category object by name
        Args:
            category_name: Name of category

        Returns: Category object if found else None
        """
        if not category_name:
            return None

        return self.search_svc_object_by_name(service=self.api_client.tagging.Category, svc_obj_name=category_name)

    def get_tag_by_category_id(self, tag_name=None, category_id=None):
        """
        Return tag object by category id
        Args:
            tag_name: Name of tag
            category_id: Id of category
        Returns: Tag object if found else None
        """
        if tag_name is None:
            return None

        if category_id is None:
            return self.search_svc_object_by_name(service=self.api_client.tagging.Tag, svc_obj_name=tag_name)

        result = None
        for tag_id in self.api_client.tagging.Tag.list_tags_for_category(category_id):
            tag_obj = self.api_client.tagging.Tag.get(tag_id)
            if tag_obj.name == tag_name:
                result = tag_obj
                break

        return result

    def get_tag_by_category_name(self, tag_name=None, category_name=None):
        """
        Return tag object by category name
        Args:
            tag_name: Name of tag
            category_id: Id of category
        Returns: Tag object if found else None
        """
        category_id = None
        if category_name is not None:
            category_obj = self.get_category_by_name(category_name=category_name)
            if category_obj is not None:
                category_id = category_obj.id

        return self.get_tag_by_category_id(tag_name=tag_name, category_id=category_id)

    def obj_to_dict(self, vmware_obj, r):
        """
        Tranform VMware SDK object to dictionary.
        Args:
            vmware_obj: Object to transform.
            r: Dictionary to fill with object data.
        """
        for k, v in vars(vmware_obj).items():
            if not k.startswith('_'):
                if hasattr(v, '__dict__') and not isinstance(v, str):
                    self.obj_to_dict(v, r[k])
                elif isinstance(v, int):
                    r[k] = int(v)
                else:
                    r[k] = str(v)

    def set_param(self, param, cmp_fn, set_fn):
        """
        Since most of the check is similar to do. This method implement
        generic call for most of the parameters. It checks if parameter
        specified is different to one which is currently set and if yes,
        it will update it.

        param: AnsibleModule parameter name
        cmp_fn: function that compares the parameter value to any API call
        set_fn: function that is called if the cmd_fn is true
        """
        generic_param = self.params.get(param)
        if generic_param is None:
            return

        if cmp_fn(generic_param):
            self.changed = True
            if not self.module.check_mode:
                set_fn(generic_param)
        self.info[param] = generic_param

    def get_tags_by_vm_moid(self, vm_moid):
        """
        Get a list of tag objects attached to a virtual machine
        Args:
            vm_mid: the VM MOID to use to gather tags

        Returns:
            List of tag object associated with the given virtual machine
        """
        dobj = DynamicID(type='VirtualMachine', id=vm_moid)
        return self.get_tags_for_dynamic_id_obj(dobj=dobj)

    def format_tag_identity_as_dict(self, tag_obj):
        """
        Takes a tag object and outputs a dictionary with identifying details about the tag,
        including name, category, and ID
        Args:
            tag: VMWare Tag Object
        Returns:
            dict
        """
        category_service = self.api_client.tagging.Category
        return {
            'id': tag_obj.id,
            'category_name': category_service.get(tag_obj.category_id).name,
            'name': tag_obj.name,
            'description': tag_obj.description,
            'category_id': tag_obj.category_id,
        }

    def get_tags_for_dynamic_id_obj(self, dobj):
        """
        Return tag objects associated with an DynamicID object.
        Args:
            dobj: Dynamic object
        Returns:
            List of tag objects associated with the given object
        """
        tags = []
        if not dobj:
            return tags

        tag_service = self.api_client.tagging.Tag
        tag_assoc_svc = self.api_client.tagging.TagAssociation

        tag_ids = tag_assoc_svc.list_attached_tags(dobj)
        for tag_id in tag_ids:
            tags.append(tag_service.get(tag_id))

        return tags

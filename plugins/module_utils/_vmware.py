# -*- coding: utf-8 -*-

# Copyright: (c) 2023, Ansible Cloud Team (@ansible-collections)
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

# Note: This utility is considered private, and can only be referenced from inside the vmware.vmware collection.
#       It may be made public at a later date

from __future__ import absolute_import, division, print_function
__metaclass__ = type

import atexit
import ssl
import traceback

REQUESTS_IMP_ERR = None
try:
    # requests is required for exception handling of the ConnectionError
    import requests
    HAS_REQUESTS = True
except ImportError:
    REQUESTS_IMP_ERR = traceback.format_exc()
    HAS_REQUESTS = False

PYVMOMI_IMP_ERR = None
try:
    from pyVim import connect
    from pyVmomi import vim, vmodl
    HAS_PYVMOMI = True
except ImportError:
    PYVMOMI_IMP_ERR = traceback.format_exc()
    HAS_PYVMOMI = False

from ansible.module_utils.basic import env_fallback, missing_required_lib


class ApiAccessError(Exception):
    def __init__(self, *args, **kwargs):
        super(ApiAccessError, self).__init__(*args, **kwargs)


def vmware_argument_spec():
    return dict(
        hostname=dict(type='str',
                      required=False,
                      fallback=(env_fallback, ['VMWARE_HOST']),
                      ),
        username=dict(type='str',
                      aliases=['user', 'admin'],
                      required=False,
                      fallback=(env_fallback, ['VMWARE_USER'])),
        password=dict(type='str',
                      aliases=['pass', 'pwd'],
                      required=False,
                      no_log=True,
                      fallback=(env_fallback, ['VMWARE_PASSWORD'])),
        cluster=dict(type='str',
                     aliases=['cluster_name'],
                     required=False),
        datacenter=dict(type='str',
                        aliases=['datacenter_name'],
                        required=False),
        port=dict(type='int',
                  default=443,
                  fallback=(env_fallback, ['VMWARE_PORT'])),
        validate_certs=dict(type='bool',
                            required=False,
                            default=True,
                            fallback=(env_fallback, ['VMWARE_VALIDATE_CERTS'])
                            ),
        proxy_host=dict(type='str',
                        required=False,
                        default=None,
                        fallback=(env_fallback, ['VMWARE_PROXY_HOST'])),
        proxy_port=dict(type='int',
                        required=False,
                        default=None,
                        fallback=(env_fallback, ['VMWARE_PROXY_PORT'])),
    )


def connect_to_api(module, disconnect_atexit=True, return_si=False, hostname=None, username=None, password=None,
                   port=None, validate_certs=None,
                   httpProxyHost=None, httpProxyPort=None):
    if module:
        if not hostname:
            hostname = module.params['hostname']
        if not username:
            username = module.params['username']
        if not password:
            password = module.params['password']
        if not httpProxyHost:
            httpProxyHost = module.params.get('proxy_host')
        if not httpProxyPort:
            httpProxyPort = module.params.get('proxy_port')
        if not port:
            port = module.params.get('port', 443)
        if not validate_certs:
            validate_certs = module.params['validate_certs']

    def _raise_or_fail(msg):
        if module is not None:
            module.fail_json(msg=msg)
        raise ApiAccessError(msg)

    if not hostname:
        _raise_or_fail(msg="Hostname parameter is missing."
                           " Please specify this parameter in task or"
                           " export environment variable like 'export VMWARE_HOST=ESXI_HOSTNAME'")

    if not username:
        _raise_or_fail(msg="Username parameter is missing."
                           " Please specify this parameter in task or"
                           " export environment variable like 'export VMWARE_USER=ESXI_USERNAME'")

    if not password:
        _raise_or_fail(msg="Password parameter is missing."
                           " Please specify this parameter in task or"
                           " export environment variable like 'export VMWARE_PASSWORD=ESXI_PASSWORD'")

    if validate_certs and not hasattr(ssl, 'SSLContext'):
        _raise_or_fail(msg='pyVim does not support changing verification mode with python < 2.7.9. Either update '
                           'python or use validate_certs=false.')
    elif validate_certs:
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
        ssl_context.verify_mode = ssl.CERT_REQUIRED
        ssl_context.check_hostname = True
        ssl_context.load_default_certs()
    elif hasattr(ssl, 'SSLContext'):
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
        ssl_context.verify_mode = ssl.CERT_NONE
        ssl_context.check_hostname = False
    else:  # Python < 2.7.9 or RHEL/Centos < 7.4
        ssl_context = None

    service_instance = None

    connect_args = dict(
        host=hostname,
        port=port,
    )
    if ssl_context:
        connect_args.update(sslContext=ssl_context)

    msg_suffix = ''
    try:
        if httpProxyHost:
            msg_suffix = " [proxy: %s:%d]" % (httpProxyHost, httpProxyPort)
            connect_args.update(httpProxyHost=httpProxyHost, httpProxyPort=httpProxyPort)
            smart_stub = connect.SmartStubAdapter(**connect_args)
            session_stub = connect.VimSessionOrientedStub(smart_stub,
                                                          connect.VimSessionOrientedStub.makeUserLoginMethod(username,
                                                                                                             password))
            service_instance = vim.ServiceInstance('ServiceInstance', session_stub)
        else:
            connect_args.update(user=username, pwd=password)
            service_instance = connect.SmartConnect(**connect_args)
    except vim.fault.InvalidLogin as invalid_login:
        msg = "Unable to log on to vCenter or ESXi API at %s:%s " % (hostname, port)
        _raise_or_fail(msg="%s as %s: %s" % (msg, username, invalid_login.msg) + msg_suffix)
    except vim.fault.NoPermission as no_permission:
        _raise_or_fail(msg="User %s does not have required permission"
                           " to log on to vCenter or ESXi API at %s:%s : %s" % (username, hostname, port, no_permission.msg))
    except (requests.ConnectionError, ssl.SSLError) as generic_req_exc:
        _raise_or_fail(
            msg="Unable to connect to vCenter or ESXi API at %s on TCP/%s: %s" % (hostname, port, generic_req_exc))
    except vmodl.fault.InvalidRequest as invalid_request:
        # Request is malformed
        msg = "Failed to get a response from server %s:%s " % (hostname, port)
        _raise_or_fail(msg="%s as request is malformed: %s" % (msg, invalid_request.msg) + msg_suffix)
    except Exception as generic_exc:
        msg = "Unknown error while connecting to vCenter or ESXi API at %s:%s" % (hostname, port) + msg_suffix
        _raise_or_fail(msg="%s : %s" % (msg, generic_exc))

    if service_instance is None:
        msg = "Unknown error while connecting to vCenter or ESXi API at %s:%s" % (hostname, port)
        _raise_or_fail(msg=msg + msg_suffix)

    # Disabling atexit should be used in special cases only.
    # Such as IP change of the ESXi host which removes the connection anyway.
    # Also removal significantly speeds up the return of the module
    if disconnect_atexit:
        atexit.register(connect.Disconnect, service_instance)
    if return_si:
        return service_instance, service_instance.RetrieveContent()
    return service_instance.RetrieveContent()


class PyVmomi(object):
    def __init__(self, module):
        """
        Constructor
        """
        if not HAS_REQUESTS:
            module.fail_json(msg=missing_required_lib('requests'),
                             exception=REQUESTS_IMP_ERR)

        if not HAS_PYVMOMI:
            module.fail_json(msg=missing_required_lib('PyVmomi'),
                             exception=PYVMOMI_IMP_ERR)

        self.module = module
        self.params = module.params
        self.current_vm_obj = None
        self.si, self.content = connect_to_api(self.module, return_si=True)
        self.custom_field_mgr = []
        if self.content.customFieldsManager:  # not an ESXi
            self.custom_field_mgr = self.content.customFieldsManager.field

    def is_vcenter(self):
        """
        Check if given hostname is vCenter or ESXi host
        Returns: True if given connection is with vCenter server
                 False if given connection is with ESXi server

        """
        api_type = None
        try:
            api_type = self.content.about.apiType
        except (vmodl.RuntimeFault, vim.fault.VimFault) as exc:
            self.module.fail_json(msg="Failed to get status of vCenter server : %s" % exc.msg)

        if api_type == 'VirtualCenter':
            return True
        elif api_type == 'HostAgent':
            return False

    def get_objs_by_name_or_moid(self, vimtype, name, return_all=False, search_root_folder=None):
        """
        Get any vsphere objects associated with a given text name or MOID and vim type.
        Different objects have different unique-ness requirements for the name parameter, so
        you may get one or more objects back. The MOID should always be unique
        Args:
            vimtype: The type of object to search for
            name: The name or the ID of the object to search for
            return_all: If true, return all the objects that were found.
                        Useful when names must be unique
            search_root_folder: The folder object that should be used as the starting point
                                for searches. Useful for restricting search results to a
                                certain datacenter (search_root_folder=datacenter.hostFolder)
        Returns:
            list(object) or list() if no matches are found
        """
        if not search_root_folder:
            search_root_folder = self.content.rootFolder

        obj = list()
        container = self.content.viewManager.CreateContainerView(
            search_root_folder, vimtype, True)

        for c in container.view:
            if name in [c.name, c._GetMoId()]:
                if return_all is False:
                    return c
                else:
                    obj.append(c)

        if len(obj) > 0:
            return obj
        else:
            # for backwards-compat
            return None

    def get_standard_portgroup(self, portgroup):
        """
        Get a portgroup from type 'STANDARD_PORTGROUP'
        Args:
            portgroup: The name or the ID of the portgroup
        Returns:
            The standard portgroup object
        """
        return self.get_objs_by_name_or_moid([vim.Network], portgroup)

    def get_dvs_portgroup(self, portgroup):
        """
        Get a portgroup from type 'DISTRIBUTED_PORTGROUP'
        Args:
            portgroup: The name or the ID of the portgroup
        Returns:
            The distributed portgroup object
        """
        return self.get_objs_by_name_or_moid([vim.dvs.DistributedVirtualPortgroup], portgroup)

    def get_vm_using_params(
            self, name_param='name', uuid_param='uuid', moid_param='moid', fail_on_missing=False,
            name_match_param='name_match', use_instance_uuid_param='use_instance_uuid'):
        """
            Get the vms matching the common module params related to vm identification: name, uuid, or moid. Since
            MOID and UUID are unique identifiers, they are tried first. If they are not set, a search by name is tried
            which may give one or more vms.
            This also supports the 'name_match' parameter and the 'use_instance_uuid' parameters. The VM identification
            parameter keys can be changed if your module uses different keys, like vm_name instead of just name
            Args:
                name_param: Set the prameter key that corredsponds to the VM name
                uuid_param: Set the prameter key that corredsponds to the VM UUID
                moid_param: Set the prameter key that corredsponds to the VM MOID
                name_match_param: Set the prameter key that corredsponds to the name_match option
                use_instance_uuid_param: Set the prameter key that corredsponds use_instance_uuid option
                fail_on_missing: If true, an error will be thrown if no VMs are found
            Returns:
                list(vm), or None if no matches were found
        """
        if self.params.get(moid_param):
            _search_type, _search_id, _search_value = 'moid', moid_param, self.params.get(moid_param)
        elif self.params.get(uuid_param):
            _search_type, _search_id, _search_value = 'uuid', uuid_param, self.params.get(uuid_param)
        elif self.params.get(name_param):
            _search_type, _search_id, _search_value = 'name', name_param, self.params.get(name_param)
        else:
            if fail_on_missing:
                self.module.fail_json("Could not find any supported VM identifier params (name, uuid, or moid)")
            else:
                return None

        if _search_type == 'uuid':
            _vm = self.si.content.searchIndex.FindByUuid(
                instanceUuid=self.params.get(use_instance_uuid_param, True),
                uuid=_search_value,
                vmSearch=True
            )
            vms = [_vm] if _vm else None
        else:
            vms = self.get_objs_by_name_or_moid([vim.VirtualMachine], _search_value, return_all=True)

        if vms and _search_type == 'name' and self.params.get(name_match_param):
            if self.params.get(name_match_param) == 'first':
                return [vms[0]]
            elif self.params.get(name_match_param) == 'last':
                return [vms[-1]]
            else:
                self.module.fail_json("Unrecognized name_match option '%s' " % self.params.get(name_match_param))

        if not vms and fail_on_missing:
            self.module.fail_json("Unable to find VM with %s %s" % _search_id, _search_value)

        return vms

    def get_folder_by_name(self, folder_name, fail_on_missing=False):
        """
            Get all folders with the given name. Names are not unique
            in a given cluster, so multiple folder objects can be returned
            Args:
                folder_name: Name of the folder to search for
                fail_on_missing: If true, an error will be thrown if no folders are found
            Returns:
                list(folder object) or None
        """
        folder = self.get_objs_by_name_or_moid([vim.Folder], folder_name, return_all=True)
        if not folder and fail_on_missing:
            self.module.fail_json("Unable to find folder with name %s" % folder_name)
        return folder

    def get_folder_by_absolute_path(self, folder_path, fail_on_missing=False):
        """
            Get a folder with the given path. Paths are unique when they are absolute so only
            one folder can be returned at most. An absolute path might look like
            'Datacenter Name/vm/my/folder/structure'
            Args:
                folder_path: The absolute path to a folder to search for
                fail_on_missing: If true, an error will be thrown if no folders are found
            Returns:
                folder object or None
        """
        folder = self.si.content.searchIndex.FindByInventoryPath(folder_path)

        if not folder and fail_on_missing:
            self.module.fail_json("Unable to find folder with absolute path %s" % folder_path)
        return folder

    def get_datastore_by_name(self, ds_name, fail_on_missing=False):
        """
            Get the datastore matching the given name. Datastore names must be unique
            in a given cluster, so only one object is returned at most.
            Args:
                ds_name: Name of the datastore to search for
                fail_on_missing: If true, an error will be thrown if no datastores are found
            Returns:
                datastore object or None
        """
        ds = self.get_objs_by_name_or_moid([vim.Datastore], ds_name)
        if not ds and fail_on_missing:
            self.module.fail_json("Unable to find datastore with name %s" % ds_name)
        return ds

    def get_resource_pool_by_name(self, pool_name, fail_on_missing=False):
        """
            Get the resource pool matching the given name. Pool names must be unique
            in a given cluster, so only one object is returned at most.
            Args:
                pool_name: Name of the pool to search for
                fail_on_missing: If true, an error will be thrown if no pools are found
            Returns:
                resource pool object or None
        """
        pool = self.get_objs_by_name_or_moid([vim.ResourcePool], pool_name)
        if not pool and fail_on_missing:
            self.module.fail_json("Unable to find resource pool with name %s" % pool_name)
        return pool

    def list_all_objs_by_type(self, vimtype, folder=None, recurse=True):
        """
            Returns a dictionary of all objects matching a given VMWare type.
            You can also limit the search by folder and recurse if desired
            Args:
                vimtype: The type of object to search for
                folder: vim.Folder, the folder object to use as a base for the search. If
                        none is provided, the datacenter root will be used
                recurse: If true, the search will recurse through the folder structure
            Returns:
                dicttionary of {obj: str}. The keys are the object while the values are the
                object name
        """
        if not folder:
            folder = self.content.rootFolder

        obj = {}
        container = self.content.viewManager.CreateContainerView(folder, vimtype, recurse)
        for managed_object_ref in container.view:
            try:
                obj.update({managed_object_ref: managed_object_ref.name})
            except vmodl.fault.ManagedObjectNotFound:
                pass
        return obj

    def get_all_vms(self, folder=None, recurse=True):
        """
        Get all virtual machines.
        """
        return self.list_all_objs_by_type([vim.VirtualMachine], folder=folder, recurse=recurse)

    def get_datacenter_by_name(self, dc_name, fail_on_missing=False):
        """
            Get the datacenter matching the given name. Datacenter names must be unique
            in a given vcenter, so only one object is returned at most.
            Args:
                dc_name: Name of the datacenter to search for
                fail_on_missing: If true, an error will be thrown if no datacenters are found
            Returns:
                datacenter object or None
        """
        ds = self.get_objs_by_name_or_moid([vim.Datacenter], dc_name)
        if not ds and fail_on_missing:
            self.module.fail_json("Unable to find datacenter with name %s" % dc_name)
        return ds

    def get_cluster_by_name(self, cluster_name, fail_on_missing=False, datacenter=None):
        """
            Get the cluster matching the given name. Cluster names must be unique
            in a given vcenter, so only one object is returned at most.
            Args:
                cluster_name: Name of the cluster to search for
                fail_on_missing: If true, an error will be thrown if no clusters are found
            Returns:
                cluster object or None
        """
        search_folder = None
        if datacenter and hasattr(datacenter, 'hostFolder'):
            search_folder = datacenter.hostFolder

        cluster = self.get_objs_by_name_or_moid(
            [vim.ClusterComputeResource],
            cluster_name,
            return_all=False,
            search_root_folder=search_folder
        )

        if not cluster and fail_on_missing:
            self.module.fail_json("Unable to find cluster with name %s" % cluster_name)

        return cluster

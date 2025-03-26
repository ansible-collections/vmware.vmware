===========================
vmware.vmware Release Notes
===========================

.. contents:: Topics

v1.11.0
=======

Minor Changes
-------------

- _module_pyvmomi_base - Make sure to use the folder param when searching for VMs based on other common params in get_vms_using_params
- added vm_resource_info module to collect cpu/memory facts about vms
- clients/_pyvmomi - adds explicit init params instead of using dict
- clients/_rest - adds explicit init params instead of using dict
- esxi_hosts - Add inventory host filtering based on jinja statements
- esxi_hosts inventory - include moid property in output always
- vm_powerstate - migrate vmware_guest_powerstate module from community to here
- pyvmomi - update object search by name method to use propertycollector, which speeds up results significantly
- upload_content_library_ovf - Add module to upload an ovf/ova to a content library
- vms - Add inventory host filtering based on jinja statements
- vms inventory - include moid property in output always

Bugfixes
--------

- vms inventory - fix handling of VMs within VApps

v1.10.1
=======

Bugfixes
--------

- folder - replaced non-existent 'storage' type with 'datastore' type
- module_deploy_vm_base - fix attribute error when deploying to a resource pool

v1.10.0
=======

Minor Changes
-------------

- cluster_ha - migrate the vmware_cluster_ha module from community to here
- deploy_content_library_ovf - migrate the vmware_content_deploy_ovf_template module from community to here
- deploy_content_library_ovf - update parameters to be consistent with other deploy modules
- deploy_content_library_template - migrate the vmware_content_deploy_template module from community to here
- deploy_content_library_template - update parameters to be consistent with other deploy modules
- deploy_folder_template - add module to deploy a vm from a template in a vsphere folder
- esxi_connection - migrate the vmware_host module from community to here
- esxi_host - migrate the vmware_host module from community to here
- folder - migrate vmware_folder module from community to here
- local_content_library - migrate the vmware_content_library_manager module from community to here
- subscribed_content_library - migrate the vmware_content_library_manager module from community to here

v1.9.0
======

Minor Changes
-------------

- esxi_maintenance_mode - migrate esxi maintenance module from community
- info - Made vm_name variable required only when state is set to present in content_template module
- pyvmomi module base - refactor class to use the pyvmomi shared client util class as a base
- rest module base - refactor class to use the rest shared client util class as a base
- vms - added vms inventory plugin. consolidated shared docs/code with esxi hosts inventory plugin

Bugfixes
--------

- client utils - Fixed error message when required library could not be imported

v1.8.0
======

Minor Changes
-------------

- _vmware - standardize getter method names and documentation
- argument specs - Remove redundant argument specs. Update pyvmomi modules to use new consolidated spec
- content_template - Fix bad reference of library variable that was refactored to library_id
- doc fragments - Remove redundant fragments. Update pyvmomi modules to use new consolidated docs
- esxi_host - Added inventory plugin to gather info about ESXi hosts

v1.7.1
======

Bugfixes
--------

- content_library_item_info - Library name and ID are ignored if item ID is provided so updated docs and arg parse rules to reflect this

v1.7.0
======

Minor Changes
-------------

- cluster_info - Migrate cluster_info module from the community.vmware collection to here
- content_library_item_info - Migrate content_library_item_info module from the vmware.vmware_rest collection to here

v1.6.0
======

Minor Changes
-------------

- cluster_dpm - Migrated module from community.vmware to configure DPM in a vCenter cluster
- cluster_drs_recommendations - Migrated module from community.vmware to apply any DRS recommendations the vCenter cluster may have

Bugfixes
--------

- Fix typos in all module documentation and README
- cluster_drs - fixed backwards vMotion rate (input 1 set rate to 5 in vCenter) (https://github.com/ansible-collections/vmware.vmware/issues/68)

v1.5.0
======

Minor Changes
-------------

- Add action group (https://github.com/ansible-collections/vmware.vmware/pull/59).
- cluster - Added cluster module, which is meant to succeed the community.vmware.vmware_cluster module (https://github.com/ansible-collections/vmware.vmware/pull/60).
- cluster_vcls - Added module to manage vCLS settings, based on community.vmware.vmware_cluster_vcls (https://github.com/ansible-collections/vmware.vmware/pull/61).
- folder_template_from_vm - Use a more robust method when waiting for tasks to complete to improve accuracy (https://github.com/ansible-collections/vmware.vmware/pull/64).

Bugfixes
--------

- README - Fix typos in README (https://github.com/ansible-collections/vmware.vmware/pull/66).

v1.4.0
======

Minor Changes
-------------

- cluster_drs - added cluster_drs module to manage DRS settings in vcenter
- folder_template_from_vm - add module and tests to create a template from an existing VM in vcenter and store the template in a folder
- guest_info - migrated functionality from community vmware_guest_info and vmware_vm_info into guest_info. Changes are backwards compatible but legacy outputs are deprecated
- module_utils/vmware_tasks - added shared utils to monitor long running tasks in vcenter
- module_utils/vmware_type_utils - added shared utils for validating, transforming, and comparing vcenter settings with python variables
- vm_portgroup_info - add module to get all the portgroups that associated with VMs

Bugfixes
--------

- _vmware_facts - fixed typo in hw_interfaces fact key and added missing annotation fact key and value
- _vmware_folder_paths - fixed issue where resolved folder paths incorrectly included a leading slash
- guest_info - added more optional attributes to the example
- module_utils/vmware_rest_client - rename get_vm_by_name method as there is same signature already

New Modules
-----------

- vmware.vmware.vm_portgroup_info - Returns information about the portgroups of virtual machines

v1.3.0
======

Minor Changes
-------------

- content_template - Add new module to manage templates in content library
- vm_list_group_by_clusters_info - Add the appropriate returned value for the deprecated module ``vm_list_group_by_clusters``

v1.2.0
======

Minor Changes
-------------

- Clarify pyVmomi requirement (https://github.com/ansible-collections/vmware.vmware/pull/15).
- vcsa_settings - Add new module to configure VCSA settings

Deprecated Features
-------------------

- vm_list_group_by_clusters - deprecate the module since it was renamed to ``vm_list_group_by_clusters_info``

Bugfixes
--------

- guest_info - Fixed bugs that caused module failure when specifying the guest_name attribute

v1.1.0
======

Minor Changes
-------------

- Added module vm_list_group_by_clusters

v1.0.0
======

Release Summary
---------------

Initial release 1.0.0

Major Changes
-------------

- Added module appliance_info
- Added module guest_info
- Added module license_info
- Release 1.0.0

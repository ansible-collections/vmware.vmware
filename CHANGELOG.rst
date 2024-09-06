===========================
vmware.vmware Release Notes
===========================

.. contents:: Topics

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

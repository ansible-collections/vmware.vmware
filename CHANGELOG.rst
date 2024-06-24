===========================
vmware.vmware Release Notes
===========================

.. contents:: Topics

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

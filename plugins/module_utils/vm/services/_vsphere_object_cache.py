"""
Service for looking up and caching objects from vSphere.

This service is used to look up objects from vSphere so other modules can use them.
Unlike the placement service, this service does is not aware of parameters and has a less specific use case.
Objects are cached based on the identifier used to look them up, and the MOID (if it is different from the identifier).
"""

from ansible_collections.vmware.vmware.plugins.module_utils._module_pyvmomi_base import (
    ModulePyvmomiBase,
)
from ansible_collections.vmware.vmware.plugins.module_utils.vm.services._abstract import (
    AbstractService,
)


class VsphereObjectCache(ModulePyvmomiBase, AbstractService):
    """
    Service for looking up and caching objects from vSphere.

    This service is used to look up objects from vSphere so other modules can use them.
    Unlike the placement service, this service does is not aware of parameters and has a less specific use case.
    Objects are cached based on the name and MOID of the object.
    """

    def __init__(self, module):
        """
        Initialize the service.

        Args:
            module: Ansible module instance for parameter access and vSphere connectivity
        """
        ModulePyvmomiBase.__init__(self, module)
        self._cache = {}

    def get_portgroup(self, portgroup_identifier):
        """
        Get the target portgroup for VM placement.

        Resolves and caches the portgroup object for VM placement.
        """
        if portgroup_identifier in self._cache:
            return self._cache[portgroup_identifier]

        # dvs portgroups are technically standard portgroups, so we need to check for dvs first and
        # then fallback to standard portgroups
        portgroup = self.get_dvs_portgroup_by_name_or_moid(
            portgroup_identifier, fail_on_missing=False
        )
        if not portgroup:
            portgroup = self.get_standard_portgroup_by_name_or_moid(
                portgroup_identifier, fail_on_missing=True
            )

        self._cache[portgroup.name] = portgroup
        self._cache[portgroup._GetMoId()] = portgroup

        return portgroup

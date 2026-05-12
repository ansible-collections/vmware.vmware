"""
Helpers for cluster HA and HA/DRS VM override modules: value remapping for the vSphere API
and a shared change tracker for desired vs current per-VM override specs.
"""

from abc import ABC, abstractmethod


class ClusterSettingsRemapper:
    """
    Remap cluster settings from the common module parameter values to the expected
    vSphere API values.
    This is done to provide a consistent and intuitive interface for the module(s).
    """

    @staticmethod
    def storage_pdl_response_mode(param_value):
        """
        Map module PDL storage protection parameter values to vim API enum strings.

        Args:
            param_value: User-facing value such as ``restart``, ``warning``, or ``disabled``.

        Returns:
            ``restartAggressive`` when ``param_value`` is ``restart``; otherwise ``param_value`` unchanged.
        """
        if param_value == "restart":
            return "restartAggressive"
        return param_value

    @staticmethod
    def storage_apd_restart_vms(param_value):
        """
        Map the boolean ``restart_vms`` module option to ``vmReactionOnAPDCleared`` API values.

        Args:
            param_value: Truthy to restart VMs after APD clears; falsy to take no reaction.

        Returns:
            ``reset`` if ``param_value`` is true, ``none`` if false, or ``None`` if unset
            (caller should omit the API field when ``None``).
        """
        # return None if the param was not set, to preserve user input
        if param_value is None:
            return None

        if param_value:
            return "reset"

        return "none"


class BaseVmOverrideChangeTracker(ABC):
    """
    Compare desired VM overrides (by VM MoID) to current cluster overrides.
    """

    def __init__(self, current_vm_override_specs, param_vm_override_specs):
        """
        Args:
            current_vm_override_specs: Mapping of VM MoID to current ``vim.cluster.*VmConfigInfo`` (or compatible).
            param_vm_override_specs: Mapping of VM MoID to desired override spec objects from module parameters.
                                     Should also be ``vim.cluster.*VmConfigInfo`` (or compatible).
        """
        self.current_vm_overrides = current_vm_override_specs
        self.param_vm_overrides = param_vm_override_specs
        self.to_add = {}
        self.to_update = {}
        self.to_remove = {}
        self._final_override_moids = set()

    @staticmethod
    def _is_desired_set_and_different_from_current(
        desired_spec, current_spec, attribute_name
    ):
        """
        Return whether ``desired_spec`` sets ``attribute_name`` to a non-None value that differs from ``current_spec``.

        Args:
            desired_spec: Desired override object (pyVmomi spec or info).
            current_spec: Current cluster override object for the same VM.
            attribute_name: Attribute to compare on both objects.

        Returns:
            False if the desired attribute is unset (None); otherwise True if values differ.
        """
        if getattr(desired_spec, attribute_name) is None:
            return False

        return getattr(desired_spec, attribute_name) != getattr(
            current_spec, attribute_name
        )

    @abstractmethod
    def _overrides_differ(self, desired, current):
        """Return True if the desired override should replace the current one for this VM."""
        pass

    def has_changes(self):
        """Return True if any VM is slated for add, update, or remove."""
        return (
            len(self.to_add) > 0 or len(self.to_update) > 0 or len(self.to_remove) > 0
        )

    def process_absent_changes(self):
        """
        Populate ``to_remove`` for VMs listed in ``param_vm_overrides`` that still have overrides on the cluster.

        Tracks ``_final_override_moids`` as current MoIDs minus those removed.
        """
        self._final_override_moids = set(self.current_vm_overrides.keys())
        for moid in self.param_vm_overrides.keys():
            if moid in self.current_vm_overrides:
                self.to_remove[moid] = self.current_vm_overrides[moid]
                self._final_override_moids.remove(moid)

    def process_present_changes(self, append=True):
        """
        Classify desired overrides into ``to_add``, ``to_update``, and optionally ``to_remove``.

        With ``append`` true, existing cluster overrides not mentioned in the desired set are left unchanged.
        With ``append`` false, any current override whose MoID is not in the desired set is marked for removal.

        Args:
            append: If false, enforce an exact match: remove cluster overrides not in ``param_vm_overrides``.
        """
        if append:
            self._final_override_moids = set(self.current_vm_overrides.keys())

        for moid, desired in self.param_vm_overrides.items():
            if moid not in self.current_vm_overrides:
                self.to_add[moid] = desired

            elif self._overrides_differ(desired, self.current_vm_overrides[moid]):
                self.to_update[moid] = desired

            self._final_override_moids.add(moid)

        if append:
            return

        for moid, current in self.current_vm_overrides.items():
            if moid not in self._final_override_moids:
                self.to_remove[moid] = current

    @staticmethod
    def format_override_specs_for_json(change_list):
        """
        Reduce pyVmomi override objects to JSON-serializable dicts for module return values.

        Args:
            change_list: Iterable of specs whose ``key`` is the VM managed object (``name``, ``_GetMoId()``).

        Returns:
            List of dicts with ``vm_moid`` and ``vm_name`` keys only.
        """
        return [
            {"vm_moid": change.key._GetMoId(), "vm_name": change.key.name}
            for change in change_list
        ]

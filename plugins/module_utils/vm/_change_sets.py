import functools
import operator

from ansible_collections.vmware.vmware.plugins.module_utils.vm._errors import PowerCycleRequiredError


class ParameterChangeSet():
    def __init__(self, vm, params):
        self.vm = vm
        self.params = params
        self._changes_required = True if vm is None else False
        self.power_cycle_required = False

    @property
    def changes_required(self):
        return self._changes_required

    @changes_required.setter
    def changes_required(self, value):
        self._changes_required = value

    def check_if_change_is_required(self, parameter_name, vm_attribute, power_sensitive=False):
        if self.vm is None:
            return

        self._check_if_param_differs_from_vm(parameter_name, vm_attribute)
        if power_sensitive:
            self._check_if_change_violates_power_state(parameter_name)

    def _check_if_param_differs_from_vm(self, parameter_name, vm_attribute):
        if self.changes_required:
            return

        try:
            param_value = functools.reduce(operator.getitem, parameter_name.split('.'), self.params)
        except KeyError:
            return

        if param_value == functools.reduce(getattr, vm_attribute.split('.'), self.vm):
            return

        self.changes_required = True

    def _check_if_change_violates_power_state(self, parameter_name):
        if self.vm.runtime.powerState != 'poweredOn' or not self.changes_required:
            return

        if self.params.get('power_cycle_allowed'):
            self.power_cycle_required = True
        else:
            raise PowerCycleRequiredError(parameter_name)

    def propagate_required_changes_from(self, change_set):
        if not isinstance(change_set, ParameterChangeSet):
            raise ValueError("change_set must be an instance of ParameterChangeSet")

        self.changes_required = self.changes_required or change_set.changes_required
        self.power_cycle_required = self.power_cycle_required or change_set.power_cycle_required


class ControllerParameterChangeSet(ParameterChangeSet):
    def __init__(self, vm, params):
        super().__init__(vm, params)
        self.controllers_to_add = []
        self.controllers_to_update = []
        self.controllers_in_sync = []

    @property
    def changes_required(self):
        return any([
            self.controllers_to_add,
            self.controllers_to_update
        ]) or self._changes_required

    def propagate_required_changes_from(self, other):
        if isinstance(other, ControllerParameterChangeSet):
            self.controllers_to_add.extend(other.controllers_to_add)
            self.controllers_to_update.extend(other.controllers_to_update)
            self.controllers_in_sync.extend(other.controllers_in_sync)
        else:
            super().propagate_required_changes_from(other)



class DiskParameterChangeSet(ParameterChangeSet):
    def __init__(self, vm, params):
        super().__init__(vm, params)
        self.disks = []
        self.disks_to_add = []
        self.disks_to_update = []
        self.disks_in_sync = []

    @property
    def changes_required(self):
        return any([
            self.disks_to_add,
            self.disks_to_update
        ]) or self._changes_required

    def propagate_required_changes_from(self, other):
        if isinstance(other, DiskParameterChangeSet):
            self.disks_to_add.extend(other.disks_to_add)
            self.disks_to_update.extend(other.disks_to_update)
            self.disks_in_sync.extend(other.disks_in_sync)
        else:
            super().propagate_required_changes_from(other)

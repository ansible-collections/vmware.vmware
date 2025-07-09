import functools
import operator


class ParameterChangeSet():
    def __init__(self, module_context):
        self.module_context = module_context
        self.changes_required = True if module_context.vm is None else False
        self.power_cycle_required = False

    def check_if_change_is_required(self, parameter_name, vm_attribute, power_sensitive=False):
        if self.module_context.vm is None:
            return

        self._check_if_param_differs_from_vm(parameter_name, vm_attribute)
        if power_sensitive:
            self._check_if_change_violates_power_state(parameter_name)

    def _check_if_param_differs_from_vm(self, parameter_name, vm_attribute):
        if self.changes_required:
            return

        try:
            param_value = functools.reduce(operator.getitem, parameter_name.split('.'), self.module_context.params)
        except KeyError:
            return

        if param_value == functools.reduce(getattr, vm_attribute.split('.'), self.module_context.vm):
            return

        self.changes_required = True

    def _check_if_change_violates_power_state(self, parameter_name):
        power_state = self.module_context.vm.runtime.powerState
        if power_state != 'poweredOn' or not self.changes_required:
            return

        if self.module_context.params.get('power_cycle_allowed'):
            self.power_cycle_required = True
        else:
            self.module_context.fail_with_power_cycle_error(parameter_name)

    def propagate_required_changes_from(self, other):
        if not isinstance(other, ParameterChangeSet):
            raise ValueError("change_set must be an instance of ParameterChangeSet")

        self.changes_required = self.changes_required or other.changes_required
        self.power_cycle_required = self.power_cycle_required or other.power_cycle_required

from ansible_collections.vmware.vmware.plugins.module_utils.vm.parameter_handlers._abstract import ParameterHandlerBase
from ansible_collections.vmware.vmware.plugins.module_utils.vm._change_sets import ParameterChangeSet

try:
    from pyVmomi import vim
except ImportError:
    pass


class VmParameterHandler(ParameterHandlerBase):
    """
    Basic parameter handler for the VM. This class handles high level parameters for the VM, such as the name,
    guest ID, and basic file store structure.
    """
    def __init__(self, vm, module):
        self.vm = vm
        self.module = module
        self.params = module.params

    def verify_parameter_constraints(self):
        if not self.vm:
            for param in ['name', 'guest_id', 'datastore']:
                if not self.params.get(param):
                    self.module.fail_json(msg="%s is a required parameter for VM creation." % param)

    def get_parameter_change_set(self):
        change_set = ParameterChangeSet(self.vm, self.params)
        change_set.check_if_change_is_required('name', 'name')
        change_set.check_if_change_is_required('guest_id', 'config.guestId')

        return change_set

    def populate_config_spec_with_parameters(self, configspec, datastore):
        if self.module.params.get('name'):
            configspec.name = self.module.params['name']
        elif self.vm:
            configspec.name = self.vm.name

        if not self.vm:
            configspec.files = vim.vm.FileInfo(
                logDirectory=None,
                snapshotDirectory=None,
                suspendDirectory=None,
                vmPathName="[" + datastore.name + "]"
            )

        if self.module.params.get('guest_id'):
            configspec.guestId = self.module.params['guest_id']





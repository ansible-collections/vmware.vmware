from ansible_collections.vmware.vmware.plugins.module_utils.vm._abstracts import ParameterHandlerBase

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

    def validate_params_for_creation(self):
        for param in ['name', 'guest_id', 'datastore', 'folder']:
            if not self.params.get(param):
                self.module.fail_json(msg="%s is a required parameter for VM creation." % param)

    def validate_params_for_reconfiguration(self):
        pass

    def params_differ_from_actual_config(self, vm):
        if self.module.params.get('name'):
            if self.module.params['name'] != vm.name:
                return True
        if self.module.params.get('guest_id'):
            if self.module.params['guest_id'] != vm.config.guestId:
                return True
        return False

    def update_config_spec_with_params(self, configspec, datastore, vm=None):
        if self.module.params.get('name'):
            configspec.name = self.module.params['name']
        elif vm:
            configspec.name = vm.name

        if not vm:
            configspec.files = vim.vm.FileInfo(
                logDirectory=None,
                snapshotDirectory=None,
                suspendDirectory=None,
                vmPathName="[" + datastore.name + "]"
            )

        if self.module.params.get('guest_id'):
            configspec.guestId = self.module.params['guest_id']





from ansible_collections.vmware.vmware.plugins.module_utils.vm.parameter_handlers._abstract import (
    ParameterHandlerBase,
)

try:
    from pyVmomi import vim
except ImportError:
    pass


class VmParameterHandler(ParameterHandlerBase):
    """
    Basic parameter handler for the VM. This class handles high level parameters for the VM, such as the name,
    guest ID, and basic file store structure.
    """

    def __init__(self, module_context):
        super().__init__(module_context)

    def verify_parameter_constraints(self):
        if not self.vm:
            for param in ["name", "guest_id", "datastore"]:
                if not self.module_context.params.get(param):
                    self.module_context.fail_with_parameter_error(
                        parameter_name=param,
                        message="%s is a required parameter for VM creation." % param,
                    )

    def compare_live_config_with_desired_config(self):
        self.change_set.check_if_change_is_required("name", "name")
        self.change_set.check_if_change_is_required("guest_id", "config.guestId")

    def populate_config_spec_with_parameters(self, configspec, datastore):
        if self.module_context.params.get("name"):
            configspec.name = self.module_context.params["name"]
        elif self.vm:
            configspec.name = self.vm.name

        if not self.vm:
            configspec.files = vim.vm.FileInfo(
                logDirectory=None,
                snapshotDirectory=None,
                suspendDirectory=None,
                vmPathName="[" + datastore.name + "]",
            )

        if self.module_context.params.get("guest_id"):
            configspec.guestId = self.module_context.params["guest_id"]

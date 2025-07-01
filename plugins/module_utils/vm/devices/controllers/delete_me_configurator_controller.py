from ._controllers import DeviceController
from ._handler import ControllerParameterHandler
from .._abstracts import ConfiguratorBase


class ControllerConfigurator(ConfiguratorBase):
    def __init__(self, vm, module):
        super().__init__(vm, module)

        # Initialize handlers
        self.controller_handler = ControllerParameterHandler(vm, module)

    def validate_params_for_creation(self):
        # validate and parse controllers from module params
        self.controller_handler.validate_params_for_creation()

    def update_config_spec(self, configspec):
        self.controller_handler.update_config_spec(configspec)

    def compare_existing_vm_controllers_to_param_controllers(self, vm):
        """
        Compare existing VM controllers to parameter controllers. Returns a tuple with the controllers
        that need to be added, removed, updated, or match their parameters.
        """
        controllers_to_add = []
        controllers_to_remove = []
        controllers_to_update = []
        controllers_in_sync = []

        for vm_device in vm.config.hardware.device:
            if isinstance(vm_device, tuple(DeviceController.get_controller_types().values())):
                controller = self.controller_handler.get_controller_from_vm_device(vm_device)
                if controller is None:
                    controllers_to_remove.append(vm_device)
                    continue

                if controller._device is not None:
                    # This should never happen, but just in case
                    raise Exception("Controller %s already has a device attached to it. Attaching another device is not allowed." % controller.key)

                controller._device = vm_device
                if controller.config_differs():
                    controllers_to_update.append(controller)
                else:
                    controllers_in_sync.append(controller)

        # Check for controllers that need to be added (those without VM devices)
        for controller_type_dict in self.controller_handler.controllers.values():
            for controller in controller_type_dict.values():
                if controller._device is None:
                    controllers_to_add.append(controller)

        return controllers_to_add, controllers_to_remove, controllers_to_update, controllers_in_sync

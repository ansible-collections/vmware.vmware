class ModuleContext:
    def __init__(self, vm, module):
        self.vm = vm
        self.module = module
        self.params = module.params
        self.spec_id_to_device = list()

    def track_device_id_from_spec(self, device):
        self.spec_id_to_device.append(device)

    def translate_device_id_to_device(self, device_id):
        return self.spec_id_to_device[device_id - 1]

    def _generic_fail_json(self, parameter_name, message, error_code, details=None):
        if details is None:
            details = dict()
        details["parameter_name"] = parameter_name
        self.module.fail_json(msg=message, error_code=error_code, details=details)

    def fail_with_power_cycle_error(self, parameter_name, message=None, details=None):
        if message is None:
            message = (
                "Configuring %s is not supported while the VM is powered on."
                % parameter_name
            )
        self._generic_fail_json(
            parameter_name, message, "POWER_CYCLE_REQUIRED", details
        )

    def fail_with_parameter_error(self, parameter_name, message, details=None):
        self._generic_fail_json(parameter_name, message, "PARAMETER_ERROR", details)

    def fail_with_device_configuration_error(self, error):
        device_id = str(error).split("'")[1]
        device = self.translate_device_id_to_device(int(device_id))
        try:
            device_name = device.name_as_str
        except AttributeError:
            device_name = "%s (bus %s)" % (type(device).__name__, device.busNumber)

        self.module.fail_json(
            msg=(
                "Device %s (device %s in the VM spec) has an invalid configuration. Please check the device configuration and try again."
                % (device_name, device_id)
            ),
            device_is_being_added=bool(getattr(device, "_device", False) is None),
            device_is_being_removed=bool(getattr(device, "_device", False) is False),
            device_is_in_sync=bool(getattr(device, "_spec", False) is None),
        )

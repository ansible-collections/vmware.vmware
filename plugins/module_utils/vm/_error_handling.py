from typing import Dict, Any


class VmModuleError(Exception):
    """
    Base exception for VM module errors
    """
    def __init__(self, message: str, error_code: str | None = None, details: Dict[str, Any] | None = None):
        super().__init__(message)
        self.error_code = error_code
        self.details = details or {}


# TODO:not sure this is used anymore
class PowerCycleRequiredError(VmModuleError):
    """
    Error when a parameter cannot be configured while the VM is powered on and user has not allowed power cycling
    """
    def __init__(self, parameter_name: str):
        self.parameter_name = parameter_name
        super().__init__(
            message="Configuring %s is not supported while the VM is powered on." % parameter_name,
            error_code="POWER_CYCLE_REQUIRED",
            details={"parameter_name": parameter_name}
        )


class ParameterValidationError(VmModuleError):
    """
    Error during parameter validation
    """
    def __init__(self, parameter_name: str, message: str, parameter_value: Any = None):
        super().__init__(
            message="Parameter '%s': %s" % (parameter_name, message),
            error_code="PARAM_VALIDATION_FAILED",
            details={"parameter_name": parameter_name, "parameter_value": parameter_value}
        )


class ResourceConstraintError(VmModuleError):
    """
    Error when resource constraints are violated
    """
    def __init__(self, resource_type: str, constraint: str, current_value: Any = None):
        super().__init__(
            message="%s constraint violated: %s" % (resource_type, constraint),
            error_code="RESOURCE_CONSTRAINT_VIOLATION",
            details={"resource_type": resource_type, "constraint": constraint, "current_value": current_value}
        )


class ErrorHandler:
    """
    Centralized error handling for VM module
    """

    def __init__(self, module):
        self.module = module

    def handle_parameter_error(self, parameter_name: str, message: str,
                             parameter_value: Any = None, exit_immediately: bool = True):
        """
        Handle parameter validation errors consistently
        """
        error_details = {
            "parameter_name": parameter_name,
            "parameter_value": parameter_value,
            "error_type": "parameter_validation"
        }

        if exit_immediately:
            self.module.fail_json(msg="Parameter '%s': %s" % (parameter_name, message), **error_details)
        else:
            raise ParameterValidationError(parameter_name, message, parameter_value)

    def handle_constraint_error(self, resource_type: str, constraint: str,
                              current_value: Any = None, exit_immediately: bool = True):
        """
        Handle resource constraint violations consistently
        """
        error_details = {
            "resource_type": resource_type,
            "constraint": constraint,
            "current_value": current_value,
            "error_type": "resource_constraint"
        }

        message = "%s constraint violated: %s" % (resource_type, constraint)
        if current_value is not None:
            message += " (current: %s)" % current_value

        if exit_immediately:
            self.module.fail_json(msg=message, **error_details)
        else:
            raise ResourceConstraintError(resource_type, constraint, current_value)

    def handle_power_cycle_error(self, parameter_name: str, allow_power_cycle: bool = False):
        """
        Handle power cycle requirements consistently
        """
        if not allow_power_cycle:
            self.module.fail_json(
                msg="Configuring %s requires VM to be powered off. "
                    "Set 'allow_power_cycling: true' to enable automatic power cycling." % parameter_name,
                parameter_name=parameter_name,
                error_type="power_cycle_required",
                solution="Set allow_power_cycling parameter to true"
            )
        # If power cycling is allowed, this should not be called

class PowerCycleRequiredError(Exception):
    def __init__(self, parameter_name):
        self.parameter_name = parameter_name
        super().__init__("Configuring %s is not supported while the VM is powered on." % parameter_name)

class MockClusterConfiguration():
    def __init__(self):
        self.dasConfig = None
        self.dpmConfigInfo = None
        self.drsConfig = None


class MockCluster():
    def __init__(self, name="test"):
        self.configurationEx = MockClusterConfiguration()
        self.host = []

        self.name = name
        self._moId = "1"

        self.parent = type('', (), {})()
        self.parent.parent = type('', (), {})()
        self.parent.parent.name = "dc"

    def GetResourceUsage(self):
        return {}

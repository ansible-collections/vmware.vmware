from unittest import mock


class MockClusterConfiguration():
    def __init__(self):
        self.dasConfig = None
        self.dpmConfigInfo = None
        self.drsConfig = None


class MockVmwareObject():
    def __init__(self, name="test", moid="1"):
        self.name = name
        self._moId = moid

    def _GetMoId(self):
        return self._moId


class MockCluster(MockVmwareObject):
    def __init__(self, name="test", moid="1"):
        super().__init__(name=name, moid=moid)
        self.configurationEx = MockClusterConfiguration()
        self.host = []

        self.parent = mock.Mock()
        self.parent.parent = mock.Mock()
        self.parent.parent.name = "dc"

    def GetResourceUsage(self):
        return {}

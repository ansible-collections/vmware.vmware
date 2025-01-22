from unittest import mock
from pyVmomi import vim


class MockVsphereTask():
    def __init__(self):
        self.info = mock.Mock()
        self.info.completeTime = '00:00:00'
        self.info.state = vim.TaskInfo.State.success
        self.info.result = 'result'
        self.info.entityName = 'some entity'
        self.info.error = ''

    def set_failed(self):
        self.info.state = vim.TaskInfo.State.error


class MockClusterConfiguration():
    def __init__(self):
        self.dasConfig = None
        self.dpmConfigInfo = None
        self.drsConfig = None


class MockVmwareObject():
    def __init__(self, name="test", moid="1"):
        super().__init__()
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


class MockEsxiHost(MockVmwareObject):
    def __init__(self, name="test", moid="1"):
        super().__init__(name=name, moid=moid)
        self.runtime = mock.Mock()
        self.runtime.inMaintenanceMode = False

        self.parent = mock.Mock()
        self.parent.name = "host"
        self.parent.parent = mock.Mock()
        self.parent.parent.name = "dc"

    def EnterMaintenanceMode_Task(self, *args):
        return MockVsphereTask()

    def ExitMaintenanceMode_Task(self, *args):
        return MockVsphereTask()

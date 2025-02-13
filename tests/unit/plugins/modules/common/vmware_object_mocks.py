from unittest import mock
from pyVmomi import vim


def create_mock_vsphere_object(name="test", moid="1"):
    """
        Creates a mock object and populates basic properties and functions
        to make it act like a vSphere object.
    """
    obj = mock.Mock()
    obj.name = name
    obj._moid = moid
    obj._GetMoId.return_value = obj._moid
    return obj


class MockVsphereTask():
    def __init__(self):
        self.info = mock.Mock()
        self.info.completeTime = '00:00:00'
        self.info.state = vim.TaskInfo.State.success
        self.info.result = 'result'
        self.info.entityName = 'some entity'
        self.info.error = ''


class MockClusterConfiguration():
    def __init__(self):
        self.dasConfig = None
        self.dpmConfigInfo = None
        self.drsConfig = None


class MockVmwareObject(mock.Mock):
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

    def ReconfigureComputeResource_Task(self, *args):
        return MockVsphereTask()


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

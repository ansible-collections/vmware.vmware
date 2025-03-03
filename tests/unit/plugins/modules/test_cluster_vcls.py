from __future__ import absolute_import, division, print_function
__metaclass__ = type

import sys
import pytest

from ansible_collections.vmware.vmware.plugins.modules import cluster_vcls

from ...common.utils import (
    AnsibleExitJson, ModuleTestCase, set_module_args,
)

pytestmark = pytest.mark.skipif(
    sys.version_info < (2, 7), reason="requires python2.7 or higher"
)


class TestClusterVcls(ModuleTestCase):

    def __prepare(self, mocker):
        init_mock = mocker.patch.object(cluster_vcls.VMwareClusterVcls, "__init__")
        init_mock.return_value = None

        resolve_datastores_to_add_and_remove = mocker.patch.object(cluster_vcls.VMwareClusterVcls, "resolve_datastores_to_add_and_remove")
        resolve_datastores_to_add_and_remove.return_value = ['ds1'], ['ds2'], ['ds1', 'ds3']

        configure_vcls = mocker.patch.object(cluster_vcls.VMwareClusterVcls, "configure_vcls")
        configure_vcls.return_value = {}

    def test_gather(self, mocker):
        self.__prepare(mocker)

        set_module_args(
            hostname="127.0.0.1",
            username="administrator@local",
            password="123456",
            datastores_to_add=['ds1'],
            datastores_to_remove=['ds2'],
        )

        with pytest.raises(AnsibleExitJson) as c:
            cluster_vcls.main()

        assert c.value.args[0]["changed"] is True
        assert c.value.args[0]["added_datastores"] == ['ds1']
        assert c.value.args[0]["removed_datastores"] == ['ds2']

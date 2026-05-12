from __future__ import absolute_import, division, print_function

__metaclass__ = type

from ansible_collections.vmware.vmware.plugins.module_utils._cluster_settings import (
    BaseVmOverrideChangeTracker,
    ClusterSettingsRemapper,
)


class _TestChangeTracker(BaseVmOverrideChangeTracker):
    """Concrete tracker for unit tests; treats ``spec`` as the comparable field."""

    def _overrides_differ(self, desired, current):
        return getattr(desired, "spec", None) != getattr(current, "spec", None)


def _make_spec(mocker, moid, spec_value, vm_name=None):
    o = mocker.Mock()
    o.spec = spec_value
    o.key = mocker.Mock()
    o.key._GetMoId.return_value = moid
    o.key.name = vm_name if vm_name is not None else "name-%s" % moid
    return o


class TestClusterSettingsRemapper:
    def test_storage_pdl_response_mode_restart_maps(self):
        assert ClusterSettingsRemapper.storage_pdl_response_mode("restart") == (
            "restartAggressive"
        )

    def test_storage_pdl_response_mode_passthrough(self):
        assert ClusterSettingsRemapper.storage_pdl_response_mode("warning") == "warning"
        assert (
            ClusterSettingsRemapper.storage_pdl_response_mode("disabled") == "disabled"
        )

    def test_storage_pdl_response_mode_none(self):
        assert ClusterSettingsRemapper.storage_pdl_response_mode(None) is None

    def test_storage_apd_restart_vms_true(self):
        assert ClusterSettingsRemapper.storage_apd_restart_vms(True) == "reset"

    def test_storage_apd_restart_vms_falsey(self):
        assert ClusterSettingsRemapper.storage_apd_restart_vms(False) == "none"
        assert ClusterSettingsRemapper.storage_apd_restart_vms(None) == "none"


class TestBaseVmOverrideChangeTrackerStatic:
    def test_is_desired_set_and_different_from_current_desired_none(self, mocker):
        d = mocker.Mock()
        d.foo = None
        c = mocker.Mock()
        c.foo = "x"
        assert not BaseVmOverrideChangeTracker._is_desired_set_and_different_from_current(
            d, c, "foo"
        )

    def test_is_desired_set_and_different_from_current_same(self, mocker):
        d = mocker.Mock()
        d.foo = 1
        c = mocker.Mock()
        c.foo = 1
        assert not BaseVmOverrideChangeTracker._is_desired_set_and_different_from_current(
            d, c, "foo"
        )

    def test_is_desired_set_and_different_from_current_differs(self, mocker):
        d = mocker.Mock()
        d.foo = 2
        c = mocker.Mock()
        c.foo = 1
        assert BaseVmOverrideChangeTracker._is_desired_set_and_different_from_current(
            d, c, "foo"
        )

    def test_format_override_specs_for_json(self, mocker):
        s = _make_spec(mocker, "vm-42", "a", vm_name="MyVM")
        out = BaseVmOverrideChangeTracker.format_override_specs_for_json([s])
        assert out == [{"vm_moid": "vm-42", "vm_name": "MyVM"}]


class TestBaseVmOverrideChangeTrackerFlow:
    def test_has_changes_false(self, mocker):
        t = _TestChangeTracker({}, {})
        assert not t.has_changes()

    def test_has_changes_true_when_populated(self, mocker):
        t = _TestChangeTracker({}, {})
        t.to_add["x"] = mocker.Mock()
        assert t.has_changes()

    def test_process_absent_removes_listed_only(self, mocker):
        cur_a = mocker.Mock()
        cur_b = mocker.Mock()
        current = {"a": cur_a, "b": cur_b}
        param = {"a": mocker.Mock()}
        t = _TestChangeTracker(current, param)
        t.process_absent_changes()
        assert t.to_remove == {"a": cur_a}
        assert t._final_override_moids == {"b"}

    def test_process_absent_param_not_on_cluster(self, mocker):
        current = {"b": mocker.Mock()}
        param = {"a": mocker.Mock()}
        t = _TestChangeTracker(current, param)
        t.process_absent_changes()
        assert t.to_remove == {}
        assert t._final_override_moids == {"b"}

    def test_process_present_append_add(self, mocker):
        desired = _make_spec(mocker, "new", "s1")
        current = {}
        param = {"new": desired}
        t = _TestChangeTracker(current, param)
        t.process_present_changes(append=True)
        assert t.to_add == {"new": desired}
        assert t.to_update == {}
        assert t.to_remove == {}

    def test_process_present_append_update_when_differs(self, mocker):
        desired = _make_spec(mocker, "a", "v2")
        existing = _make_spec(mocker, "a", "v1")
        current = {"a": existing}
        param = {"a": desired}
        t = _TestChangeTracker(current, param)
        t.process_present_changes(append=True)
        assert t.to_add == {}
        assert t.to_update == {"a": desired}
        assert t.to_remove == {}

    def test_process_present_append_no_update_when_same(self, mocker):
        desired = _make_spec(mocker, "a", "v1")
        existing = _make_spec(mocker, "a", "v1")
        current = {"a": existing}
        param = {"a": desired}
        t = _TestChangeTracker(current, param)
        t.process_present_changes(append=True)
        assert t.to_add == {}
        assert t.to_update == {}
        assert t.to_remove == {}

    def test_process_present_append_keeps_unmentioned_current(self, mocker):
        orphan = _make_spec(mocker, "orphan", "x")
        desired = _make_spec(mocker, "a", "v1")
        current = {"a": _make_spec(mocker, "a", "v1"), "orphan": orphan}
        param = {"a": desired}
        t = _TestChangeTracker(current, param)
        t.process_present_changes(append=True)
        assert "orphan" not in t.to_remove

    def test_process_present_replace_removes_unlisted(self, mocker):
        keep = _make_spec(mocker, "a", "v1")
        drop = _make_spec(mocker, "b", "y")
        current = {"a": keep, "b": drop}
        param = {"a": _make_spec(mocker, "a", "v1")}
        t = _TestChangeTracker(current, param)
        t.process_present_changes(append=False)
        assert t.to_remove == {"b": drop}
        assert t.to_add == {}
        assert t.to_update == {}

    def test_process_present_replace_empty_param_removes_all(self, mocker):
        cur = _make_spec(mocker, "only", "x")
        current = {"only": cur}
        param = {}
        t = _TestChangeTracker(current, param)
        t.process_present_changes(append=False)
        assert t.to_remove == {"only": cur}

from __future__ import absolute_import, division, print_function
__metaclass__ = type

from ansible_collections.vmware.vmware.plugins.module_utils._advanced_settings import AdvancedSettings


class TestAdvancedSettings():
    def test_add_setting(self, mocker):
        test = AdvancedSettings()

        test.add_setting('one', 1)
        assert test._settings['one'] == 1

        test.add_setting('one', 2)
        assert test._settings['one'] == 2

        test.add_setting('two', 2)
        assert test._settings['one'] == 2
        assert test._settings['two'] == 2

        test.add_setting('two', 'two')
        assert test._settings['two'] == 'two'

        test.add_setting('two', False)
        assert test._settings['two'] is False

        test.add_setting('two', 1.0)
        assert test._settings['two'] == 1.0

    def test_add_setting_string_only(self, mocker):
        test = AdvancedSettings(cast_all_values_to_str=True)

        test.add_setting('one', 1)
        assert test._settings['one'] == '1'

        test.add_setting('one', 2)
        assert test._settings['one'] == '2'

        test.add_setting('two', 2)
        assert test._settings['one'] == '2'
        assert test._settings['two'] == '2'

        test.add_setting('two', 'two')
        assert test._settings['two'] == 'two'

        test.add_setting('two', False)
        assert test._settings['two'] == 'False'

        test.add_setting('two', 1.0)
        assert test._settings['two'] == '1.0'

    def test_from_py_dict(self, mocker):
        test = AdvancedSettings.from_py_dict({'one': 1, 'two': 'two'})

        assert test._settings['one'] == 1
        assert test._settings['two'] == 'two'

        test = AdvancedSettings.from_py_dict({'one': 1, 'two': 'two'}, True)

        assert test._settings['one'] == '1'
        assert test._settings['two'] == 'two'

    def test_from_vsphere_config(self, mocker):
        option_1, option_2 = mocker.Mock(), mocker.Mock()
        option_1.key, option_1.value = 'one', 1
        option_2.key, option_2.value = 'two', 'two'
        test = AdvancedSettings.from_vsphere_config([option_1, option_2])

        assert test._settings['one'] == 1
        assert test._settings['two'] == 'two'

    def test_is_empty(self, mocker):
        test = AdvancedSettings()
        assert test.is_empty()

        test.add_setting('one', 1)
        assert not test.is_empty()

    def test_difference(self, mocker):
        test_1 = AdvancedSettings.from_py_dict({'one': 1, 'two': 'two'})
        test_2 = AdvancedSettings.from_py_dict({'one': 3, 'two': 'two'})

        diff_1_2 = test_1.difference(test_2)
        diff_2_1 = test_2.difference(test_1)

        assert diff_1_2._settings['one'] == 1
        assert len(diff_1_2._settings) == 1

        assert diff_2_1._settings['one'] == 3
        assert len(diff_2_1._settings) == 1

    def test_to_vsphere_config(self, mocker):
        test = AdvancedSettings.from_py_dict({'one': 1, 'two': 'two'})
        out = test.to_vsphere_config()
        assert len(out) == 2
        assert out[0].key == 'one'
        assert out[0].value == 1
        assert out[1].key == 'two'
        assert out[1].value == 'two'

        test = AdvancedSettings.from_py_dict({'one': 1, 'two': 'two'}, True)
        out = test.to_vsphere_config()
        assert len(out) == 2
        assert out[0].key == 'one'
        assert out[0].value == '1'
        assert out[1].key == 'two'
        assert out[1].value == 'two'

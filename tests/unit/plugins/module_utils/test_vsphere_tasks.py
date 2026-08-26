from __future__ import absolute_import, division, print_function
__metaclass__ = type

from unittest import mock

import pytest

from ansible_collections.vmware.vmware.plugins.module_utils._vsphere_tasks import (
    TaskError,
    VmQuestionHandler,
)


def _mock_vm_with_question(question_id="0", message_id="msg.uuid.altered",
                           choices=None):
    """
    Build a VM mock whose runtime reports a pending question, matching the
    pyVmomi shape used by VmQuestionHandler (message.id, choice.choiceInfo
    with label/key, question.id and question.text).
    """
    if choices is None:
        choices = {"button.uuid.copiedTheVM": "0", "button.uuid.movedTheVM": "1"}

    vm = mock.Mock()
    message = mock.Mock()
    message.id = message_id

    choice_infos = []
    for label, key in choices.items():
        choice = mock.Mock()
        choice.label = label
        choice.key = key
        choice_infos.append(choice)

    vm.runtime.question.id = question_id
    vm.runtime.question.text = "Question text"
    vm.runtime.question.message = [message]
    vm.runtime.question.choice.choiceInfo = choice_infos
    return vm


class TestVmQuestionHandler():

    def test_no_question_with_answers_is_noop(self):
        """
        Regression: supplying answers while no question is pending must not
        raise (previously dereferenced runtime.question and raised
        AttributeError, killing the module before it could answer).
        """
        vm = mock.Mock()
        vm.runtime.question = None
        answers = [{"question": "msg.uuid.altered", "response": "button.uuid.movedTheVM"}]

        handler = VmQuestionHandler(vm=vm, answers=answers)
        handler.handle_vm_questions()

        vm.AnswerVM.assert_not_called()

    def test_no_question_without_answers_is_noop(self):
        vm = mock.Mock()
        vm.runtime.question = None

        handler = VmQuestionHandler(vm=vm, answers=None)
        handler.handle_vm_questions()

        vm.AnswerVM.assert_not_called()

    def test_question_without_answers_raises(self):
        vm = _mock_vm_with_question()

        handler = VmQuestionHandler(vm=vm, answers=None)
        with pytest.raises(TaskError):
            handler.handle_vm_questions()

        vm.AnswerVM.assert_not_called()

    def test_question_with_answers_is_answered(self):
        vm = _mock_vm_with_question()
        answers = [{"question": "msg.uuid.altered", "response": "button.uuid.movedTheVM"}]

        handler = VmQuestionHandler(vm=vm, answers=answers)
        handler.handle_vm_questions()

        vm.AnswerVM.assert_called_once_with("0", "1")

    def test_question_with_unknown_answer_raises(self):
        vm = _mock_vm_with_question()
        answers = [{"question": "msg.uuid.altered", "response": "does.not.exist"}]

        handler = VmQuestionHandler(vm=vm, answers=answers)
        with pytest.raises(TaskError):
            handler.handle_vm_questions()

        vm.AnswerVM.assert_not_called()

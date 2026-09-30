"""Tests for OpenAI Chat Completions request compatibility."""

import types
import unittest

from concordia.contrib.language_models.openai import base_gpt_model


class _FakeCompletions:

  def __init__(self):
    self.request = None

  def create(self, **kwargs):
    self.request = kwargs
    message = types.SimpleNamespace(content='ok')
    choice = types.SimpleNamespace(message=message)
    return types.SimpleNamespace(choices=[choice])


def _model(model_name: str):
  completions = _FakeCompletions()
  client = types.SimpleNamespace(
      chat=types.SimpleNamespace(completions=completions)
  )
  model = base_gpt_model.BaseGPTModel(
      model_name=model_name,
      client=client,
  )
  return model, completions


class BaseGptModelTest(unittest.TestCase):

  def test_gpt4o_omits_reasoning_controls(self):
    model, completions = _model('gpt-4o')

    self.assertEqual(model.sample_text('hello'), 'ok')

    self.assertNotIn('reasoning_effort', completions.request)
    self.assertNotIn('verbosity', completions.request)

  def test_gpt5_keeps_reasoning_controls(self):
    model, completions = _model('gpt-5-mini')

    self.assertEqual(model.sample_text('hello'), 'ok')

    self.assertEqual(completions.request['reasoning_effort'], 'minimal')
    self.assertEqual(completions.request['verbosity'], 'low')


if __name__ == '__main__':
  unittest.main()

"""Tests for shared-housing communication mechanics."""

import unittest

from examples.shared_housing import communication


class ParseActionTest(unittest.TestCase):

  def test_extracts_json_from_prefixed_model_output(self):
    raw = (
        'Zhang Wei: ```json\n'
        '{"channel":"whatsapp_group","languages":["English",'
        '"Mandarin"],"recipients":[],"intent":"apologize",'
        '"content":"Sorry, 是我忘了清理。"}\n```'
    )

    action = communication.parse_action(raw, 'Zhang Wei')

    self.assertEqual(action['channel'], 'whatsapp_group')
    self.assertEqual(action['languages'], ['English', 'Mandarin'])
    self.assertEqual(action['intent'], 'apologize')
    self.assertFalse(action['parse_error'])

  def test_invalid_output_becomes_private_wait(self):
    action = communication.parse_action('', 'Maria Santos')

    self.assertEqual(action['channel'], 'private_action')
    self.assertEqual(action['intent'], 'wait')
    self.assertTrue(action['parse_error'])

  def test_repairs_known_channel_and_intent_aliases(self):
    raw = (
        '{"channel":"contact_landlord","languages":["English"],'
        '"recipients":[],"intent":"private_action",'
        '"content":"Please repair the shower."}'
    )

    action = communication.parse_action(raw, 'Ravi Krishnamurthy')

    self.assertEqual(action['channel'], 'private_action')
    self.assertEqual(action['intent'], 'contact_landlord')
    self.assertFalse(action['parse_error'])
    self.assertIn(
        'channel:contact_landlord->private_action', action['repaired_fields']
    )

  def test_detects_script_language_missing_from_metadata(self):
    raw = (
        '{"channel":"whatsapp_group","languages":["English"],'
        '"recipients":[],"intent":"translate",'
        '"content":"妈妈说厨房还很油 — Mum says the kitchen is oily."}'
    )

    action = communication.parse_action(raw, 'Wei Ling Chen')

    self.assertEqual(action['languages'], ['English', 'Mandarin'])
    self.assertFalse(action['parse_error'])
    self.assertIn('languages:+Mandarin', action['repaired_fields'])


class ComprehensionTest(unittest.TestCase):

  def test_zhang_understands_written_english_better_than_ravi_speaking(self):
    written = communication.comprehension_score(
        listener='Zhang Wei',
        actor='Ravi Krishnamurthy',
        languages=['English'],
        written=True,
    )
    spoken = communication.comprehension_score(
        listener='Zhang Wei',
        actor='Ravi Krishnamurthy',
        languages=['English'],
        written=False,
    )

    self.assertEqual(communication.comprehension_band(written), 'full')
    self.assertEqual(communication.comprehension_band(spoken), 'partial')
    self.assertGreater(written, spoken)

  def test_code_switching_uses_all_named_languages(self):
    score = communication.comprehension_score(
        listener='Wei Ling Chen',
        actor='Zhang Wei',
        languages=['English', 'Mandarin'],
        written=False,
    )

    self.assertAlmostEqual(score, 0.89)


if __name__ == '__main__':
  unittest.main()

import copy
import json
from pathlib import Path
import tempfile
import unittest
import zipfile
import claude_intelligence_build as build


def message(mid, text='', date='2026-03-14T08:00:00Z', sender='human', parent=None):
    return {'uuid': mid, 'text': text, 'sender': sender, 'created_at': date,
            'content': [], 'parent_message_uuid': parent}


def conversation(cid, messages, created='2026-03-14T08:00:00Z'):
    return {'uuid': cid, 'created_at': created, 'chat_messages': messages}


class ClaudeExportTests(unittest.TestCase):
    def test_branches_and_empty_text_are_counted_without_inventing_content(self):
        c = conversation('c', [message('h', 'A question'), message('a', sender='assistant', parent='h'),
                               message('a2', sender='assistant', parent='h'), message('blank')])
        r = build.summarize({'c': c})
        self.assertEqual(r['totals']['human_message_records'], 2)
        self.assertEqual(r['totals']['readable_human_messages'], 1)
        self.assertEqual(r['totals']['all_message_records'], 4)
        self.assertEqual(r['quality']['conversations_with_multiple_children'], 1)
        self.assertEqual(r['quality']['human_records_without_readable_text'], 1)

    def test_text_is_counted_once_and_injected_context_is_excluded(self):
        m = message('h', 'Hello world')
        m['content'] = [{'type': 'text', 'text': 'Hello world'},
                        {'type': 'injected_prompt_block', 'text': 'private context'}]
        self.assertEqual(build.human_text(m), 'Hello world')
        m['text'] = ''
        self.assertEqual(build.human_text(m), 'Hello world')
        m['content'] = [{'type': 'injected_prompt_block', 'prompt': 'private context'}]
        self.assertEqual(build.human_text(m), '')

    def test_pacific_cutoff_and_resumed_conversation(self):
        c = conversation('old', [message('h', 'New activity', '2026-03-14T07:00:00Z')],
                         '2026-03-14T06:59:59Z')
        r = build.summarize({'old': c})
        self.assertEqual(r['since_march_13']['new_conversations'], 0)
        self.assertEqual(r['since_march_13']['human_message_records'], 1)
        self.assertEqual(r['since_march_13']['older_conversations_resumed'], 1)

    def test_empty_records_and_zero_months_remain(self):
        r = build.summarize({'a': conversation('a', [], '2026-01-01T12:00:00Z'),
                             'b': conversation('b', [message('h')], '2026-03-14T08:00:00Z')})
        self.assertEqual(r['totals']['conversations'], 2)
        self.assertEqual(r['quality']['conversations_without_readable_human_text'], 2)
        self.assertEqual(r['quality']['conversations_without_messages'], 1)
        feb = next(x for x in r['monthly'] if x['month'] == '2026-02')
        self.assertEqual(feb['conversations'], 0)

    def test_message_ids_are_deduplicated_and_conflicts_rejected(self):
        m = message('h', 'One message')
        records = {'a': conversation('a', [m]), 'b': conversation('b', [copy.deepcopy(m)])}
        r = build.summarize(records)
        self.assertEqual(r['totals']['human_message_records'], 1)
        self.assertEqual(r['quality']['repeated_message_occurrences_removed'], 1)
        records['b']['chat_messages'][0]['text'] = 'Different message'
        with self.assertRaisesRegex(ValueError, 'Conflicting duplicate message'):
            build.summarize(records)

    def test_zip_reader_ignores_unrelated_and_apple_metadata(self):
        c = conversation('c', [message('h', 'Hello')])
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'source.zip'
            with zipfile.ZipFile(p, 'w') as z:
                z.writestr('conversations.json', json.dumps([c, c]))
                z.writestr('__MACOSX/conversations.json', 'not JSON')
                z.writestr('memories.json', 'not JSON')
            records, shards, fingerprint, duplicates = build.read_export(p)
            self.assertEqual((len(records), shards, duplicates), (1, 1, 1))
            self.assertEqual(len(fingerprint), 64)
            self.assertNotIn('uuid', json.dumps(build.summarize(records)))

    def test_naive_timestamps_are_rejected(self):
        with self.assertRaisesRegex(ValueError, 'timezone'):
            build.timestamp('2026-03-14T08:00:00')


if __name__ == '__main__':
    unittest.main()

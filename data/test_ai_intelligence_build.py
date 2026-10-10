"""Regression checks for export boundaries, branched chats, and duplicate records."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

import ai_intelligence_build as build


def message(mid, when, text, role='user'):
    return {'id': mid, 'create_time': when, 'author': {'role': role},
            'content': {'parts': [text]}}


def conversation(cid, created, messages):
    nodes = {}
    parent = None
    for i, msg in enumerate(messages):
        node = f'node-{i}'
        nodes[node] = {'parent': parent, 'message': msg}
        parent = node
    return {'id': cid, 'create_time': created, 'current_node': parent, 'mapping': nodes}


class ExportRules(unittest.TestCase):
    def setUp(self):
        self.old = message('inherited', build.START - 1, 'Earlier request')
        self.fresh = message('new', build.START + 1, 'New request')
        self.rows = {
            'older': conversation('older', build.START - 100, [self.old, self.fresh]),
            'branch': conversation('branch', build.START + 10, [self.old, self.fresh]),
            'empty': conversation('empty', build.START + 20, []),
        }
        self.labels = {cid: {'category': 'mixed_unclear'} for cid in ['branch', 'empty']}

    def test_branches_count_as_chats_but_inherited_messages_count_once(self):
        result = build.summarize(self.rows, self.labels)
        self.assertEqual(result['totals']['conversations'], 3)
        self.assertEqual(result['totals']['unique_user_messages'], 2)
        self.assertEqual(result['since_march_6']['new_conversations'], 2)
        self.assertEqual(result['since_march_6']['unique_user_messages'], 1)
        self.assertEqual(result['since_march_6']['older_conversations_resumed'], 1)
        self.assertEqual(result['since_march_6']['new_conversations_without_user_messages'], 1)
        self.assertEqual(result['quality']['repeated_user_message_occurrences_removed'], 2)

    def test_cutoff_uses_pacific_midnight_and_keeps_exact_boundary(self):
        rows = {cid: conversation(cid, time, [message(cid, time, 'text')])
                for cid, time in [('before', build.START - 1), ('at', build.START)]}
        result = build.summarize(rows, {'at': {'category': 'everyday_life'}})
        self.assertEqual(result['since_march_6']['new_conversations'], 1)
        self.assertEqual(result['since_march_6']['unique_user_messages'], 1)

    def test_alternate_branch_and_assistant_are_excluded(self):
        row = self.rows['older']
        row['mapping']['unused'] = {'parent': None, 'message': message('unused', build.START, 'omit')}
        row['mapping']['answer'] = {'parent': row['current_node'], 'message': message('answer', build.START, 'omit', 'assistant')}
        row['current_node'] = 'answer'
        self.assertEqual(build.summarize(self.rows, self.labels)['totals']['unique_user_messages'], 2)

    def test_conflicting_inherited_message_fails(self):
        self.rows['branch'] = copy.deepcopy(self.rows['branch'])
        self.rows['branch']['mapping']['node-1']['message']['content']['parts'] = ['changed']
        with self.assertRaisesRegex(ValueError, 'Conflicting duplicate user message'):
            build.summarize(self.rows, self.labels)

    def test_extra_classification_fails(self):
        self.labels['older'] = {'category': 'everyday_life'}
        with self.assertRaisesRegex(ValueError, 'exactly'):
            build.summarize(self.rows, self.labels)

    def test_broken_or_cyclic_parent_chain_fails(self):
        row = self.rows['older']
        row['mapping']['node-0']['parent'] = 'node-1'
        with self.assertRaisesRegex(ValueError, 'parent chain'):
            build.current_branch(row)
        row['mapping']['node-0']['parent'] = 'missing'
        with self.assertRaisesRegex(ValueError, 'parent chain'):
            build.current_branch(row)

    def test_only_conversation_shards_and_exact_duplicates_are_accepted(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'export.zip'
            def write(conflicting=False):
                second = copy.deepcopy(self.rows['older'])
                if conflicting:
                    second['create_time'] += 1
                with zipfile.ZipFile(path, 'w') as archive:
                    archive.writestr('conversations-000.json', json.dumps(list(self.rows.values())))
                    archive.writestr('conversations-001.json', json.dumps([second]))
                    archive.writestr('shared_conversations.json', 'invalid JSON must not be read')
                    archive.writestr('sectioned_conversations.json', '{}')
            write()
            rows, shards, fingerprint, duplicates = build.read_export(path)
            self.assertEqual(len(rows), 3)
            self.assertEqual(shards, 2)
            self.assertEqual(duplicates, 1)
            self.assertEqual(len(fingerprint), 64)
            write(conflicting=True)
            with self.assertRaisesRegex(ValueError, 'Conflicting duplicate conversation'):
                build.read_export(path)


if __name__ == '__main__':
    unittest.main()

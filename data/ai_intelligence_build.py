#!/usr/bin/env python3
"""Build aggregate-only AI Intelligence data from a local ChatGPT export.

python3 data/ai_intelligence_build.py EXPORT.zip --classifications PRIVATE.json \
    --output data/ai-intelligence.json --review-date 2026-10-09

Raw messages, conversation IDs, titles, and classification evidence stay outside
the repository. The classifications file maps each new conversation ID to a
reviewed category under `labels`. See ai-intelligence/README.md for definitions.
"""
import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import zipfile
from zoneinfo import ZoneInfo

TZ = ZoneInfo('America/Los_Angeles')
START = datetime(2026, 3, 7, tzinfo=TZ).timestamp()
CATEGORIES = {
    'visual_design': 'Visual design',
    'technology_workflows': 'Technology & workflows',
    'research_publishing': 'Research & publishing',
    'culture_writing': 'Culture & writing',
    'health_reflection': 'Health & reflection',
    'everyday_life': 'Everyday life',
    'money_admin': 'Money & administration',
    'mixed_unclear': 'Mixed / unclear',
}


def readable_text(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return '\n'.join(filter(None, map(readable_text, content)))
    if isinstance(content, dict):
        if 'parts' in content:
            return readable_text(content['parts'])
        return content.get('text', '') if isinstance(content.get('text'), str) else ''
    return ''


def current_branch(conversation):
    mapping = conversation['mapping']
    cursor = conversation.get('current_node')
    if mapping and not cursor:
        raise ValueError('A nonempty conversation has no current node')
    seen, messages = set(), []
    while cursor:
        if cursor in seen or cursor not in mapping:
            raise ValueError('Invalid conversation parent chain')
        seen.add(cursor)
        node = mapping[cursor]
        if node.get('message'):
            messages.append(node['message'])
        cursor = node.get('parent')
    return list(reversed(messages))


def read_export(path):
    digest = hashlib.sha256()
    conversations = {}
    duplicate_records = 0
    with zipfile.ZipFile(path) as archive:
        names = sorted(n for n in archive.namelist()
                       if re.fullmatch(r'(?:.*/)?conversations(?:-\d+)?\.json', n))
        if not names:
            raise ValueError('No conversation JSON files in export')
        for name in names:
            payload = archive.read(name)  # verifies this ZIP member's CRC
            digest.update(name.encode() + b'\0' + payload)
            rows = json.loads(payload)
            if not isinstance(rows, list):
                raise ValueError('Conversation data must be a list')
            for row in rows:
                key = row.get('id') or row['conversation_id']
                if key in conversations:
                    if conversations[key] != row:
                        raise ValueError('Conflicting duplicate conversation')
                    duplicate_records += 1
                conversations[key] = row
    return conversations, len(names), digest.hexdigest(), duplicate_records


def summarize(conversations, classifications):
    monthly = defaultdict(lambda: {'conversations': 0, 'user_messages': 0})
    new_monthly = Counter()
    new_categories = Counter()
    unique_messages = {}
    new_ids, resumed_ids, active_ids = set(), set(), set()
    missing_user_timestamps = 0
    duplicate_user_occurrences = 0
    no_user_messages = 0
    creation_times = []
    for cid, conversation in conversations.items():
        created = conversation['create_time']
        creation_times.append(created)
        month = datetime.fromtimestamp(created, TZ).strftime('%Y-%m')
        monthly[month]['conversations'] += 1
        is_new = created >= START
        if is_new:
            new_ids.add(cid)
            new_monthly[month] += 1
            category = classifications[cid]['category']
            if category not in CATEGORIES:
                raise ValueError('Unrecognized category')
            new_categories[category] += 1
        users = [m for m in current_branch(conversation)
                 if m.get('author', {}).get('role') == 'user']
        if is_new and not users:
            no_user_messages += 1
        for message in users:
            mid = message['id']
            record = {'time': message.get('create_time'),
                      'text': readable_text(message.get('content', {}))}
            if record['time'] and record['time'] >= START:
                active_ids.add(cid)
                if not is_new:
                    resumed_ids.add(cid)
            if mid in unique_messages:
                if unique_messages[mid] != record:
                    raise ValueError('Conflicting duplicate user message')
                duplicate_user_occurrences += 1
            else:
                unique_messages[mid] = record
    if set(classifications) != new_ids:
        raise ValueError('Classifications must cover exactly the new conversations')
    period_messages = 0
    period_words = 0
    all_words = 0
    message_times = []
    for record in unique_messages.values():
        words = len(re.findall(r"\b[\w]+(?:[’'-][\w]+)*\b", record['text']))
        all_words += words
        timestamp = record['time']
        if not timestamp:
            missing_user_timestamps += 1
            continue
        message_times.append(timestamp)
        month = datetime.fromtimestamp(timestamp, TZ).strftime('%Y-%m')
        monthly[month]['user_messages'] += 1
        if timestamp >= START:
            period_messages += 1
            period_words += words
    total = len(conversations)
    assert sum(m['conversations'] for m in monthly.values()) == total
    assert sum(m['user_messages'] for m in monthly.values()) + missing_user_timestamps == len(unique_messages)
    assert sum(new_categories.values()) == len(new_ids)
    return {
        'schema_version': 1,
        'timezone': str(TZ),
        'coverage': {
            'first_conversation': datetime.fromtimestamp(min(creation_times), TZ).isoformat(),
            'last_conversation': datetime.fromtimestamp(max(creation_times), TZ).isoformat(),
            'last_user_message': datetime.fromtimestamp(max(message_times), TZ).isoformat(),
            'data_through': datetime.fromtimestamp(max(creation_times + message_times), TZ).strftime('%Y-%m-%d'),
            'refresh_period_start': '2026-03-07',
        },
        'totals': {'conversations': total, 'unique_user_messages': len(unique_messages),
                   'user_text_words': all_words},
        'since_march_6': {
            'new_conversations': len(new_ids), 'older_conversations_resumed': len(resumed_ids),
            'conversations_with_user_activity': len(active_ids),
            'unique_user_messages': period_messages, 'user_text_words': period_words,
            'new_conversations_without_user_messages': no_user_messages,
        },
        'reconciliation': {
            'reported_march_conversations': 1474,
            'current_export_conversations_before_march_7': total - len(new_ids),
            'net_change_from_reported_march_total': total - 1474,
            'note': f'The March raw export is unavailable. The current pre-March-7 count differs from the old reported total by {total - len(new_ids) - 1474:+d} records; the reason is unverified. New activity is counted from timestamps, not subtraction.',
        },
        'quality': {'repeated_user_message_occurrences_removed': duplicate_user_occurrences,
                    'user_messages_without_timestamp': missing_user_timestamps},
        'monthly': [{'month': m, **v} for m, v in sorted(monthly.items())],
        'new_conversations_by_month': [{'month': m, 'conversations': n} for m, n in sorted(new_monthly.items())],
        'new_conversation_categories': [
            {'key': key, 'label': CATEGORIES[key], 'count': count,
             'percent': round(count / len(new_ids) * 100, 1)}
            for key, count in new_categories.most_common()],
        'definitions': {
            'conversations': 'Distinct exported conversation IDs, including branch conversations and records with no user message. All topics and media are retained.',
            'user_messages': 'User-role messages on each conversation current-node ancestry. Identical message IDs inherited by branches count once across the archive. Alternate branches, system, assistant, and tool messages are excluded.',
            'user_text_words': 'Approximate word tokens in readable user-message text and available audio transcriptions, including pasted source text and prompt templates. Not a measure of original writing; image text and untranscribed audio are excluded.',
            'categories': 'One manually reviewed primary purpose per new conversation, using titles, user requests, and follow-ups. Records without a clear primary purpose remain mixed/unclear. This measures conversation mix, not time, skill, outcomes, or clinical status.',
            'scope': 'The supplied ChatGPT account export only. Separate Codex sessions and unexported, temporary, or deleted chats are not reconstructed. Claude is analyzed separately from its October 10 conversations export.',
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('export', type=Path)
    parser.add_argument('--classifications', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--review-date', required=True)
    args = parser.parse_args()
    datetime.strptime(args.review_date, '%Y-%m-%d')
    conversations, shards, fingerprint, duplicates = read_export(args.export)
    labels = json.loads(args.classifications.read_text())['labels']
    summary = summarize(conversations, labels)
    summary['reviewed'] = args.review_date
    summary['source'] = {'format': 'ChatGPT account export ZIP', 'conversation_shards': shards,
                         'conversation_payload_sha256': fingerprint,
                         'duplicate_conversation_records_removed': duplicates}
    args.output.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({k: summary[k] for k in ['coverage', 'totals', 'since_march_6', 'quality']}, indent=2))


if __name__ == '__main__':
    main()

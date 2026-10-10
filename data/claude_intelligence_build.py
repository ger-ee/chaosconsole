#!/usr/bin/env python3
"""Build public aggregates from a private Claude conversations ZIP.

Counts all exported message branches; the source has no current-node selector.
Never exports conversation IDs, names, text, attachments, or account details.
"""
import argparse
from collections import Counter, defaultdict
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import zipfile
from zoneinfo import ZoneInfo

TZ = ZoneInfo('America/Los_Angeles')
START = datetime(2026, 3, 14, tzinfo=TZ)


def timestamp(value):
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        raise ValueError('Timestamp must include a timezone')
    return parsed.astimezone(TZ)


def human_text(message):
    text = message.get('text', '')
    if isinstance(text, str) and text.strip():
        return text
    # Never count injected context, tools, thinking, or attachment bodies as user text.
    return '\n'.join(b['text'] for b in message.get('content', [])
                     if b.get('type') == 'text' and isinstance(b.get('text'), str))


def read_export(path):
    digest = hashlib.sha256()
    records = {}
    duplicates = 0
    with zipfile.ZipFile(path) as archive:
        names = sorted(n for n in archive.namelist()
                       if not n.startswith('__MACOSX/') and
                       re.fullmatch(r'(?:.*/)?conversations(?:-\d+)?\.json', n))
        if not names:
            raise ValueError('No conversation JSON in ZIP')
        for name in names:
            payload = archive.read(name)  # ZIP CRC is checked on read.
            digest.update(name.encode() + b'\0' + payload)
            rows = json.loads(payload)
            if not isinstance(rows, list):
                raise ValueError('Expected a list of conversations')
            for row in rows:
                key = row['uuid']
                if key in records:
                    if records[key] != row:
                        raise ValueError('Conflicting duplicate conversation')
                    duplicates += 1
                records[key] = row
    return records, len(names), digest.hexdigest(), duplicates


def summarize(records):
    monthly = defaultdict(lambda: {'conversations': 0, 'human_messages': 0,
                                   'readable_human_messages': 0})
    new_monthly = Counter()
    messages = {}
    raw_messages = {}
    new_ids, active_ids, resumed_ids = set(), set(), set()
    empty_conversations, empty_new, branches, branches_new = set(), set(), set(), set()
    no_messages = 0
    duplicate_messages = 0
    creation_times = []
    for cid, c in records.items():
        created = timestamp(c['created_at'])
        creation_times.append(created)
        month = created.strftime('%Y-%m')
        monthly[month]['conversations'] += 1
        is_new = created >= START
        if is_new:
            new_ids.add(cid)
            new_monthly[month] += 1
        rows = c['chat_messages']
        no_messages += not rows
        parents = Counter(m.get('parent_message_uuid') for m in rows
                          if m.get('parent_message_uuid'))
        if any(n > 1 for n in parents.values()):
            branches.add(cid)
            if is_new:
                branches_new.add(cid)
        readable = False
        for m in rows:
            mid = m['uuid']
            if mid in raw_messages and raw_messages[mid] != m:
                raise ValueError('Conflicting duplicate message')
            raw_messages[mid] = m
            if m['sender'] not in ('human', 'assistant'):
                raise ValueError('Unexpected message sender')
            when = timestamp(m['created_at'])
            record = {'role': m['sender'], 'time': when.isoformat(),
                      'text': human_text(m) if m['sender'] == 'human' else ''}
            if mid in messages:
                if messages[mid] != record:
                    raise ValueError('Conflicting duplicate message')
                duplicate_messages += 1
            else:
                messages[mid] = record
            if record['role'] == 'human':
                readable |= bool(record['text'].strip())
                if when >= START:
                    active_ids.add(cid)
                    if not is_new:
                        resumed_ids.add(cid)
        if not readable:
            empty_conversations.add(cid)
            if is_new:
                empty_new.add(cid)
    if not creation_times:
        raise ValueError('Empty conversation archive')
    human = [m for m in messages.values() if m['role'] == 'human']
    period = [m for m in human if timestamp(m['time']) >= START]
    for m in human:
        row = monthly[timestamp(m['time']).strftime('%Y-%m')]
        row['human_messages'] += 1
        row['readable_human_messages'] += bool(m['text'].strip())
    # Retain zero-activity months between the first and last observed month.
    first, last = min(monthly), max(monthly)
    year, month = map(int, first.split('-'))
    while f'{year:04d}-{month:02d}' <= last:
        monthly[f'{year:04d}-{month:02d}']
        month += 1
        if month == 13:
            year, month = year + 1, 1
    def words(ms):
        return sum(len(re.findall(r"\b[\w]+(?:[’'-][\w]+)*\b", m['text'])) for m in ms)
    last_message = max((timestamp(m['time']) for m in messages.values()), default=max(creation_times))
    assert sum(m['conversations'] for m in monthly.values()) == len(records)
    assert sum(m['human_messages'] for m in monthly.values()) == len(human)
    return {
        'schema_version': 1, 'timezone': str(TZ),
        'coverage': {
            'first_conversation': min(creation_times).isoformat(),
            'last_conversation': max(creation_times).isoformat(),
            'last_message': last_message.isoformat(),
            'data_through': max(max(creation_times), last_message).date().isoformat(),
            'refresh_period_start': '2026-03-14',
        },
        'totals': {
            'conversations': len(records), 'human_message_records': len(human),
            'readable_human_messages': sum(bool(m['text'].strip()) for m in human),
            'assistant_message_records': len(messages) - len(human),
            'all_message_records': len(messages), 'readable_human_text_words': words(human),
        },
        'since_march_13': {
            'new_conversations': len(new_ids), 'human_message_records': len(period),
            'readable_human_messages': sum(bool(m['text'].strip()) for m in period),
            'readable_human_text_words': words(period),
            'conversations_with_human_activity': len(active_ids),
            'older_conversations_resumed': len(resumed_ids),
            'new_conversations_without_readable_human_text': len(empty_new),
        },
        'quality': {
            'conversations_without_readable_human_text': len(empty_conversations),
            'conversations_without_messages': no_messages,
            'conversations_with_multiple_children': len(branches),
            'new_conversations_with_multiple_children': len(branches_new),
            'repeated_message_occurrences_removed': duplicate_messages,
            'human_records_without_readable_text': len(human) - sum(bool(m['text'].strip()) for m in human),
        },
        'reconciliation': {
            'previous_report_conversations': 104,
            'current_export_conversations_before_march_14': len(records) - len(new_ids),
            'note': 'The previous analysis covers through March 13. Counts before March 14 match its 104-record headline; original raw records are unavailable for an identity-level reconciliation. Legacy message, code-session, and upload totals are replaced, not compared.',
        },
        'monthly': [{'month': m, **v} for m, v in sorted(monthly.items())],
        'new_conversations_by_month': [{'month': m, 'conversations': n} for m, n in sorted(new_monthly.items())],
        'definitions': {
            'conversations': 'Distinct conversation UUIDs in conversations.json; includes empty records and all topics. Creation timestamps determine month.',
            'human_message_records': 'Distinct human-sender message UUIDs in all exported chat_messages, including empty text and alternate branches. A timestamp determines its activity month. There is no current-node selector in this export.',
            'readable_human_messages': 'Human message records with nonblank text, using top-level text once or text-type content blocks as fallback. Injected prompts, tool output, thinking, and attachment contents are excluded.',
            'words': 'Approximate word tokens in readable human text, including pasted material. Not original writing, time, or productivity.',
            'scope': 'Only the supplied conversations archive. Separate design_chats, frames, Claude Code, Codex, and unexported or deleted sessions are not included or reconstructed; this is not a complete measure of all product activity.',
            'interpretation': 'Qualitative observations use readable user requests. No topic is inferred for records without readable text. Requests and assistant completion statements do not establish a verified result.',
        },
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('export', type=Path)
    p.add_argument('--output', required=True, type=Path)
    p.add_argument('--review-date', required=True)
    args = p.parse_args()
    datetime.strptime(args.review_date, '%Y-%m-%d')
    records, shards, fingerprint, duplicates = read_export(args.export)
    result = summarize(records)
    result['reviewed'] = args.review_date
    result['source'] = {'format': 'Claude conversations export ZIP', 'conversation_shards': shards,
                        'conversation_payload_sha256': fingerprint,
                        'duplicate_conversation_records_removed': duplicates}
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: result[k] for k in ['coverage', 'totals', 'since_march_13', 'quality']}, indent=2))


if __name__ == '__main__':
    main()

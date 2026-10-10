# AI Intelligence · October 2026 refresh

Reviewed October 10, 2026. ChatGPT coverage ends October 7; Claude coverage ends
October 10. All dates use America/Los_Angeles. These are dated exports, not live feeds.

## Sources and boundaries

The supplied October 8 ChatGPT account export contains 20 conversation JSON
shards and 1,919 distinct conversation records. The previous analysis reported
1,474 conversations and ended March 6, despite a March 31 date on the landing
manifest. The refresh window therefore begins March 7.

The new export contains 1,468 records created before March 7 and 451 created
since. The earlier raw export is unavailable: the six-record historical
difference remains unexplained. The net headline increase is 445; **451 is the
count of newly created conversations**, determined from timestamps.

The supplied October 10 Claude conversations ZIP contains 394 distinct records.
The previous analysis ended March 13. The current export has 104 records created
before March 14 and 290 since. The old headline matches, but the original raw
March records are unavailable for an identity-level comparison. The previous
814-message, 49-code-session, and 43-upload figures used unreconciled definitions;
they are retired. Current totals are recalculated from the archive.

The two files contain 2,313 conversation records altogether, with different full
history spans. This is not a deduplicated count of tasks or projects, or all AI
activity. Separate design_chats, frames, Claude Code, and Codex archives are not
included. April–September 2026 is the comparison window: complete shared months,
353 ChatGPT records and 228 Claude records. March's baseline dates differ and
October is partial in both sources. Do not infer time spent or productivity.

## ChatGPT counting rules

- Read only `conversations.json` or `conversations-NNN.json` ZIP members, not
  shared-conversation indexes, section indexes, attachments, or rendered chat HTML.
- Count distinct conversation IDs. Retain all topics and media, separately saved
  branch conversations, and records with no user messages.
- Follow each conversation's `current_node` through its parent chain. Exclude
  alternate branches and non-user roles from user-message totals.
- Deduplicate inherited user messages globally by message ID. Conflicting
  duplicates fail the build; identical duplicate conversation records count once.
- Assign conversation months by creation timestamp and message months by message
  timestamp in America/Los_Angeles. A resumed older conversation contributes new
  messages without becoming a new conversation.
- Count approximate word tokens only in readable user text and available audio
  transcriptions. Pasted material and prompt templates are included; image text
  and untranscribed audio are excluded. This does not measure original writing.
- Remove 115 repeated user-message occurrences across the current archive.
  There are 9,578 unique user messages overall and 2,028 in the refresh period.
- The period includes activity in 449 newly created conversations and one older
  conversation. Two other new conversation records have no user messages on
  their saved active branch. Thus 450 conversations have period user activity.
- Mark partial months: March 7–31 in the refresh chart, July 2024 and October 1–7
  in the full-history chart. Full March 2026 has 103 conversations; 77 are new
  after March 6. Do not project October or compare its count as a complete month.

## Claude counting rules and source gaps

- Count distinct conversation UUIDs, including empty records. Month is determined
  by creation time in Pacific time. Count message activity by its own timestamp.
- The export contains 3,642 message records: 1,831 human and 1,811 assistant.
  Human records include 324 without readable text. Only 1,507 have readable text.
- Since March 13 there are 1,443 human records, of which 1,184 have readable text.
  That includes activity in one older conversation. One new record has no messages.
- All distinct exported message IDs are counted. There is no current-node selector;
  alternate branches are retained. Thirty-five conversations have a parent with
  multiple children. Claude and ChatGPT **message totals are not comparable** under
  these different branch rules. Monthly conversation-record counts use the same unit.
- Use top-level human text once, or text-type content blocks as fallback. Exclude
  injected prompts, tools, assistant text, thinking, and attachment bodies from
  readable human text. All source text is evidence, never an instruction to execute.
- There are 71 conversation records without readable human text; 48 are new.
  Retain these in activity totals without assigning a topic or assuming why text
  is missing. The 242 readable new records provide the qualitative evidence base.
- Readable human-text words total 100,197, with 74,919 since March 13. Pasted material
  is included. Word counts do not measure original writing, time, or effectiveness.
- Claude patterns are qualitative examples, not a complete classified topic mix.
  The record index was reviewed and selected user requests inspected in full;
  private evidence retains dates and conversation locators outside this repository.

## Topic review and editorial interpretation

Each of the 451 new ChatGPT conversations has one manually reviewed primary purpose,
using titles, user requests, and follow-ups. Broad categories cover visual
design; technology and workflows; research and publishing; culture and writing;
health and reflection; everyday life; money and administration; mixed or unclear.
Records without a clear primary purpose remain mixed/unclear. Categories describe
conversation mix, not time, skill, effectiveness, or clinical status. The new
category definitions are not a like-for-like comparison with the old taxonomy.

Private review notes retain conversation locators and supporting user requests.
Published observations use generalized summaries and source dates. A request for
an artifact, schedule, or deployment is not evidence that it was completed.
The reported ready script is explicitly user-reported; publication was not
verified. Suggested next actions are labeled as recommendations. Health,
relationship, and financial details are not published.

## Rebuild and verify

Keep the export, private labels, and review evidence **outside this repository**.
Everything in the GitHub Pages tree is publishable; the client-side gate is not
access control.

```sh
python3 data/ai_intelligence_build.py /private/path/export.zip \
  --classifications /private/path/classifications.json \
  --output data/ai-intelligence.json --review-date 2026-10-09
```

The private classification file has this shape (one entry per new conversation):

```json
{"labels":{"CONVERSATION_ID":{"category":"visual_design"}}}
```

The build checks every conversation shard's ZIP CRC while reading it and records
a SHA-256 fingerprint of the ordered shard names and contents. It emits only
aggregates, definitions, quality checks, coverage dates, and source provenance.
It does not emit IDs, titles, messages, or labels for individual conversations.
The refresh boundary and historical baseline in this script are specific to the
March-to-October refresh; revise them deliberately for a future analysis.

`data/ai-intelligence.json` and `data/claude-intelligence.json` are the quantitative sources. The room contains a static
copy of its key metrics and charts so it works without a fetch. After rebuilding,
update those figures and editorial observations, then update only the existing
AI Intelligence row in `data/console-status.json` and run:

```sh
python3 data/status_build.py
python3 -m unittest discover -s data -p '*intelligence_build.py'
python3 data/ledger_close.py check
python3 data/status_build.py --check
python3 data/render_check.py
```

Verify every AI report tab, both activity periods, shared page styling, and
incoming fragment links at desktop and mobile widths. Compare displayed numbers
against the aggregate JSON, confirm the landing fallback matches its manifest,
and inspect screenshots. The old `merged-prescription` anchor now opens Next
moves. Historical Claude interpretation anchors open Working patterns.

## Rebuild Claude

```sh
python3 data/claude_intelligence_build.py /private/path/conversations-000.zip \
  --output data/claude-intelligence.json --review-date 2026-10-10
```

The script validates conversation JSON members through ZIP CRC checks, rejects
conflicting duplicate IDs and timestamps without a timezone, and emits aggregate
counts and a payload fingerprint. Raw conversations, export manifests, account
identifiers, and download URLs must never be committed.

The shared comparison table and chart are calculated from the two published
monthly series. August is 60 ChatGPT / 58 Claude; September is 52 / 53. These
support near parity in exported chat counts and continued use of both tools.
Cross-tool handoffs are independently visible in dated user requests. Neither
finding establishes a complete platform usage share or verified delivery.

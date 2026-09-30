#!/usr/bin/env python3
"""
Ledger monthly close — the mechanical half of updating /the-ledger/.

The Ledger page keeps all of its state in one line of the-ledger/index.html:

    const DATA = {...};

Every chart and table on the page is derived from that blob, and about fifteen
derived structures (per-account totals, sparklines, monthly totals, monthly
flow, sankey, waterfall, calendar, Stephen ledger, top payees, health scores)
must be recomputed together whenever a month is added. Hand-editing the blob
is how earlier closes drifted. This script owns the recomputation.

Usage
-----
    python3 data/ledger_close.py dump
        Print the current state: period, per-account latest rows, totals.

    python3 data/ledger_close.py extract 2026-09 [--statements DIR]
        pdftotext every statement under the Finances statements folder whose
        filename mentions the month, and print the summary lines that matter
        (previous balance, payments, purchases, fees, interest, new balance,
        minimum, close date) plus the checking activity rows. Reading that
        output is how you fill in close.json. Dataless iCloud files must be
        materialised first (brctl download).

    python3 data/ledger_close.py apply close.json [--dry-run]
        Add the month described in close.json, recompute everything, rebase
        the Payoff Lab and calendar, write the blob back, print diagnostics
        and a checklist of the narrative copy that still needs a human.

    python3 data/ledger_close.py check [--strict]
        JSON-parse the blob, node --check the inline script, verify the
        balance identities (errors for the latest month, warnings for older
        rows unless --strict) and the monthlyFlow/monthKeys alignment.

    python3 data/ledger_close.py backfill-purchases [--dry-run]
        For rows entered with purchases=0 whose balance moved more than
        payments and interest explain, derive net new charges arithmetically
        and flag the row purchasesDerived. Used once on Sep 18 2026 for the
        Apple Oct '25–Mar '26 rows that had been entered without purchases.

close.json
----------
{
  "month": "2026-09", "label": "Sep '26", "updated": "2026-10-10",
  "accounts": {
    "apple":      {"closeDate":"Sep 30, 2026","prevBalance":6103.26,"balance":...,"payments":...,"purchases":...,"interest":...,"creditLimit":null,"availableCredit":null,"minimumPayment":...,"returnedPayments":0,"note":"..."},
    "citi":       {...}, "capone0623": {...}, "capone4540": {...},
    "ppc":        {..., "fees": 0.0}, "ppcb": {...}, "amazon": {..., "estimated": true}, "ralphs": {...}
  },
  "checking": [
    {"date":"09-12-2026","desc":"ACH Electronic Debit ...","cat":"CC Payment — Citi Simplicity","group":"Credit Card Payments","debit":88.52,"credit":0}
  ],
  "stephenPayments": [{"date":"2026-09-20","amount":2700.0,"description":"Zelle Credit ... STEPHEN AVRO","dateDisplay":"09/20/26"}],
  "installment": {"principal":..., "payoff":..., "payoffGoodThrough":"...", "dueNow":..., "dueBy":"...", "pastDue":..., "statementsOf":"9 of 72",
                  "statements":[{"n":9,"date":"2026-10-03","payoff":...,"principal":...,"paid":...,"returned":0,"fees":0,"note":"..."}]},
  "recommendations": {"apple":["CURE $359","#f87171"]},
  "postPeriod": {"ralphs": {"label":"...","text":"..."}},
  "accountMeta": {"capone4540": {"name":"Capital One 2868","creditLimit":1100.0}}   // optional: name / creditLimit / apr / issuer
}

A month may be closed in parts: apply is idempotent per account, so a spec that carries only the
cards whose statements exist adds the month with null rows (carry-forward) for the rest, and a
later apply of the same month with the remaining cards fills them in. data/close_<yyyy-mm>.json is
kept in the repo as the record of each close.

Rules the script enforces (see ledger_close.md in memory for the why):
- month key = calendar month of the statement CLOSE date. An account with no
  statement that month gets a null row and its balance carries forward.
- carry-forward starts at 0, not firstBalance (keeps the Oct '25 baseline).
- returned/NSF payments arrive on statements as purchases; put the reversed
  amount in returnedPayments and describe it in note.
- Pass-through group (wires in / legal fees out) is excluded from spending,
  sankey and top payees; Zelle (Stephen) debits are repayments, not spending.
- monthlyFlow has exactly one entry per monthKey, in order.
"""
import argparse
import json
import os
import re
import subprocess
import sys
from collections import Counter, OrderedDict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGE = ROOT / "the-ledger" / "index.html"
STATEMENTS = Path.home() / "Documents" / "Finances" / "Statements"
MARKER = "const DATA = "
PASS = "Pass-through"
ACCOUNT_KEYS = ["ralphs", "ppcb", "ppc", "amazon", "citi", "capone0623", "capone4540", "apple"]
MONTH_LABELS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


# ----------------------------------------------------------------------------- blob io
def read_page():
    s = PAGE.read_text(encoding="utf-8")
    i = s.index(MARKER)
    j = s.index("\n", i)
    blob = s[i + len(MARKER):j].rstrip().rstrip(";")
    return s, i, j, json.loads(blob)


def write_page(s, i, j, data):
    out = s[:i] + MARKER + json.dumps(data, separators=(",", ":"), ensure_ascii=False) + ";" + s[j:]
    PAGE.write_text(out, encoding="utf-8")
    return out


def n(x):
    return 0 if x is None else x


def dk(t):
    """checkingTransactions store MM-DD-YYYY; return YYYY-MM-DD."""
    mm, dd, yy = t["date"].split("-")
    return f"{yy}-{mm}-{dd}"


def label_for(mk):
    y, m = mk.split("-")
    return f"{MONTH_LABELS[int(m) - 1]} '{y[2:]}"


# ----------------------------------------------------------------------------- dump
def cmd_dump(_args):
    _, _, _, D = read_page()
    M, T = D["meta"], D["totals"]
    print(f"period {M['periodStart']} → {M['periodEnd']} · {len(M['monthKeys'])} months · updated {M['updated']}")
    print(f"current debt {T['currentDebt']:,.2f} · vs {M['periodStart']} {T['debtChangePeriod']:+,.2f} · interest {T['periodInterest']:,.2f} · card payments {T['periodCardPayments']:,.2f}")
    for a in D["accounts"]:
        last = [m for m in a["monthly"] if m.get("balance") is not None][-1]
        print(f"  {a['key']:<11} {a['name']:<18} latest {last['month']} {a['latestBalance']:>9,.2f}  apr {a['apr']:>5}  util {str(a['utilization']):>5}  health {a['healthScore']:>3}  {a['recommendation']}")
    ct = D["checkingTransactions"]
    print(f"checking transactions {len(ct)} · {min(dk(t) for t in ct)} → {max(dk(t) for t in ct)}")
    if D.get("installment"):
        c = D["installment"]
        print(f"installment {c['name']} · principal {c['principal']:,.2f} · payoff {c['payoff']:,.2f} · {c['statementsOf']} · due {c['dueNow']:,.2f} by {c['dueBy']}")
    print(f"stephen {D['stephen']['count']} payments · {D['stephen']['totalIn']:,.2f} in · net {D['stephen']['net']:,.2f}")


# ----------------------------------------------------------------------------- extract
PATTERNS = [
    r"Statement Closing Date", r"Closing Date", r"Billing Period", r"as of", r"Jul \d|Aug \d|Sep \d|Oct \d|Nov \d|Dec \d|Jan \d|Feb \d|Mar \d|Apr \d|May \d|Jun \d.{0,4}, 20\d\d - ",
    r"Previous [Bb]alance", r"Payments", r"Other Credits", r"Purchases|Transactions\s+\+", r"Fees", r"Interest [Cc]harged|INTEREST CHARGES|Total interest",
    r"New [Bb]alance", r"Minimum [Pp]ayment", r"Credit Limit", r"Available Credit", r"Past [Dd]ue", r"Returned", r"RTN R01", r"Adjustment-Payments",
    r"Deferred Interest Balance|DEFERRED INTEREST|Promotional", r"Payoff Amount", r"unpaid balance", r"Late Charge", r"Total Amount Due",
]


def cmd_extract(args):
    ym = args.month
    y, m = ym.split("-")
    needles = {ym, f"{y}_{m}", f"{m}_{y}", f"{MONTH_LABELS[int(m)-1]}", f"{y}-{m}", f"{y}_{int(m):d}"}
    long = {"01": "January", "02": "February", "03": "March", "04": "April", "05": "May", "06": "June", "07": "July", "08": "August", "09": "September", "10": "October", "11": "November", "12": "December"}[m]
    needles.add(long)
    base = Path(args.statements) if args.statements else STATEMENTS
    # the year must appear in the filename too ("Sep" alone matched every September since 2019),
    # and multi-year archive exports ("September 2019 – February 2026") are skipped
    pdfs = [p for p in base.rglob("*.pdf")
            if y in p.name and "–" not in p.name
            and (any(nd in p.name for nd in needles) or f"{y}_{long}" in p.name)]
    # BMW statements are numbered, not dated: include those newer than the last known one by mtime
    pdfs += sorted((base / "BMW Financial").glob("*.pdf"), key=lambda p: p.stat().st_mtime)[-1:] if (base / "BMW Financial").exists() else []
    if not pdfs:
        print(f"no statements matching {ym} under {base}", file=sys.stderr)
        return 1
    for p in sorted(pdfs):
        print("=" * 100)
        print(p.relative_to(base))
        try:
            txt = subprocess.run(["pdftotext", "-layout", str(p), "-"], capture_output=True, text=True, timeout=60).stdout
        except Exception as e:  # noqa: BLE001
            print(f"  !! pdftotext failed: {e} (iCloud dataless? brctl download '{p}')")
            continue
        if "Couldn't find trailer" in txt or not txt.strip():
            print("  !! empty/unreadable — probably iCloud dataless: brctl download then retry")
            continue
        seen = set()
        for line in txt.splitlines():
            if any(re.search(pt, line) for pt in PATTERNS):
                l2 = re.sub(r"\s{2,}", "  ", line.strip())
                if l2 and l2 not in seen and len(l2) < 200:
                    seen.add(l2)
                    print("  " + l2)
        if "Checking" in str(p):
            print("  --- checking activity ---")
            act = re.findall(r"^\s*(\d{2}/\d{2})\s+(.+?)\s{2,}([\d,]+\.\d{2})(?:\s+([\d,]+\.\d{2}))?(?:\s+([\d,]+\.\d{2}-?))?\s*$", txt, flags=re.M)
            for row in act:
                print("  " + "  ".join(x for x in row if x))
    return 0


# ----------------------------------------------------------------------------- apply
def recompute(D):
    """Recompute every derived structure from accounts[].monthly + checkingTransactions."""
    MK = D["meta"]["monthKeys"]
    # per-account rows for every month key
    for a in D["accounts"]:
        have = {m["month"] for m in a["monthly"]}
        for mk in MK:
            if mk not in have:
                a["monthly"].append({"month": mk, "closeDate": None, "balance": None, "payments": 0, "purchases": 0, "interest": 0})
        a["monthly"].sort(key=lambda m: m["month"])
        ms = a["monthly"]
        # one value per month key, carrying the last close forward over null rows — the stacked
        # debt chart maps this positionally against meta.monthLabels, so a shorter list shifts the
        # whole series left (PayPal Cashback's mid-series nulls had been doing exactly that)
        carry, sl = 0.0, []
        for m in ms:
            if m.get("balance") is not None:
                carry = m["balance"]
            sl.append(round(carry, 2))
        a["sparkline"] = sl
        last = [m for m in ms if m.get("balance") is not None][-1]
        a["latestBalance"], a["latestMonth"] = last["balance"], last["month"]
        a["totalInterestPeriod"] = round(sum(n(m.get("interest")) for m in ms), 2)
        a["totalPaidPeriod"] = round(sum(n(m.get("payments")) for m in ms), 2)
        a["totalPurchasesPeriod"] = round(sum(n(m.get("purchases")) + n(m.get("fees")) for m in ms), 2)
        a["balanceChangePeriod"] = round(a["latestBalance"] - a["firstBalance"], 2)
        a["utilization"] = None if not a.get("creditLimit") else round(a["latestBalance"] / a["creditLimit"] * 100, 1)

    # totals by month (carry-forward from 0)
    debt, interest, payments, purchases = {}, {}, {}, {}
    carry = {a["key"]: 0.0 for a in D["accounts"]}
    for mk in MK:
        tb = ti = tp = tq = 0.0
        for a in D["accounts"]:
            m = next(x for x in a["monthly"] if x["month"] == mk)
            if m.get("balance") is not None:
                carry[a["key"]] = m["balance"]
            tb += carry[a["key"]]; ti += n(m.get("interest")); tp += n(m.get("payments")); tq += n(m.get("purchases")) + n(m.get("fees"))
        debt[mk], interest[mk], payments[mk], purchases[mk] = round(tb, 2), round(ti, 2), round(tp, 2), round(tq, 2)
    T = D["totals"]
    T.update({"debt": debt, "interest": interest, "payments": payments, "purchases": purchases,
              "currentDebt": debt[MK[-1]], "octDebt": debt[MK[0]],
              "periodInterest": round(sum(interest.values()), 2), "periodCardPayments": round(sum(payments.values()), 2),
              "debtChangePeriod": round(debt[MK[-1]] - debt[MK[0]], 2),
              "returnedPayments": round(sum(n(m.get("returnedPayments")) for a in D["accounts"] for m in a["monthly"]), 2)})

    # checking-derived
    CT = sorted(D["checkingTransactions"], key=dk)
    D["checkingTransactions"] = CT
    flow = OrderedDict()
    for t in CT:
        mk = dk(t)[:7]
        f = flow.setdefault(mk, {"month": mk, "income": 0, "stephenIn": 0, "otherIn": 0, "ccPayments": 0, "spending": 0, "stephenOut": 0, "passThroughIn": 0, "passThroughOut": 0, "count": 0})
        f["count"] += 1
        if t["credit"]:
            if t["group"] == "Zelle (Stephen)": f["stephenIn"] += t["credit"]
            elif t["group"] == "Income": f["income"] += t["credit"]
            elif t["group"] == PASS: f["passThroughIn"] += t["credit"]
            elif t["group"] == "Credit Card Payments": f["ccPayments"] -= t["credit"]  # NSF reversal
            else: f["otherIn"] += t["credit"]
        if t["debit"]:
            if t["group"] == "Credit Card Payments": f["ccPayments"] += t["debit"]
            elif t["group"] == PASS: f["passThroughOut"] += t["debit"]
            elif t["group"] == "Zelle (Stephen)": f["stephenOut"] += t["debit"]
            else: f["spending"] += t["debit"]
    empty = lambda mk: {"month": mk, "income": 0, "stephenIn": 0, "otherIn": 0, "ccPayments": 0, "spending": 0, "stephenOut": 0, "passThroughIn": 0, "passThroughOut": 0, "count": 0}
    D["monthlyFlow"] = [{k: (round(v, 2) if isinstance(v, float) else v) for k, v in flow.get(mk, empty(mk)).items()} for mk in MK]
    T["stephenIn"] = round(sum(t["credit"] for t in CT if t["group"] == "Zelle (Stephen)"), 2)
    T["ownIncome"] = round(sum(t["credit"] for t in CT if t["group"] == "Income"), 2)
    T["nonCcSpending"] = round(sum(t["debit"] for t in CT if t["debit"] and t["group"] not in ("Credit Card Payments", PASS, "Zelle (Stephen)")), 2)
    T["passThrough"] = round(sum(t["debit"] for t in CT if t["group"] == PASS), 2)
    T["periodPayments"] = round(sum(f["ccPayments"] for f in D["monthlyFlow"]), 2)
    T["fundingGap"] = round(T["periodCardPayments"] - T["periodPayments"], 2)
    era = [mk for mk in MK if mk >= "2026-03"]
    ef = {f["month"]: f for f in D["monthlyFlow"]}
    T["marAprCc"] = round(sum(ef[mk]["ccPayments"] for mk in era), 2)
    T["marAprSpending"] = round(sum(ef[mk]["spending"] for mk in era), 2)
    T["marAprStephen"] = round(sum(ef[mk]["stephenIn"] for mk in era), 2)
    T["marAprOwnIncome"] = round(sum(ef[mk]["income"] for mk in era), 2)
    T["stephenEraLabel"] = f"Mar-{label_for(MK[-1]).split(' ')[0]} '{MK[-1][2:4]}"

    # stephen
    S = D["stephen"]
    S["payments"].sort(key=lambda p: p["date"])
    S["totalIn"] = round(sum(p["amount"] for p in S["payments"]), 2)
    S["net"] = round(S["totalIn"] - S["totalOut"], 2)
    S["count"] = len(S["payments"])
    S["lastPayment"] = S["payments"][-1]["date"] if S["payments"] else None
    have = {t["date"] for t in S["trace"]}
    for p in S["payments"]:
        if p["date"] not in have:
            d0 = p["date"]
            y0, m0, dd0 = map(int, d0.split("-"))
            lo = date(y0, m0, dd0).toordinal()
            fol = [{"date": dk(t), "amount": t["debit"], "card": t["cat"], "description": t["desc"]}
                   for t in CT if t["group"] == "Credit Card Payments" and t["debit"] and 0 <= date.fromisoformat(dk(t)).toordinal() - lo <= 14]
            S["trace"].append({"date": d0, "amount": p["amount"], "dateDisplay": p.get("dateDisplay") or f"{m0:02d}/{dd0:02d}/{str(y0)[2:]}", "followingCC": fol})
    for tr in S["trace"]:
        if "dateDisplay" not in tr:
            y0, m0, dd0 = tr["date"].split("-"); tr["dateDisplay"] = f"{m0}/{dd0}/{y0[2:]}"
    S["trace"].sort(key=lambda p: p["date"])

    # ccPayments list
    existing = {(c["date"], c["amount"], c["card"]) for c in D["ccPayments"]}
    for t in CT:
        if t["group"] == "Credit Card Payments" and t["debit"]:
            key = (dk(t), t["debit"], t["cat"])
            if key not in existing:
                D["ccPayments"].append({"date": dk(t), "amount": t["debit"], "card": t["cat"], "description": t["desc"], "dateDisplay": t["date"][:2] + "/" + t["date"][3:5] + "/" + t["date"][8:]})
                existing.add(key)
    D["ccPayments"].sort(key=lambda c: c["date"])

    # top payees
    def payee(desc):
        for tag in ["APPLECARD", "PAYPAL", "CAPITAL ONE", "CITI AUTOPAY", "AMZ_STORECRD_PMT", "AMAZON CORP SYF", "VENMO", "TARGET", "LADWP", "SPECTRUM", "SoCalGas", "WISEMAN-SR", "UBER", "BMW"]:
            if tag in desc:
                return "AMZ_STORECRD_PMT" if tag == "AMAZON CORP SYF" else tag
        return desc[:50]
    agg = {}
    for t in CT:
        if not t["debit"] or t["group"] == PASS:
            continue
        p = payee(t["desc"]); e = agg.setdefault(p, {"payee": p, "count": 0, "amount": 0.0})
        e["count"] += 1; e["amount"] = round(e["amount"] + t["debit"], 2)
    D["topPayees"] = sorted(agg.values(), key=lambda e: -e["amount"])[:15]

    # sankey
    inc, outc = {}, {}
    for t in CT:
        if t["credit"] and t["group"] not in (PASS, "Credit Card Payments"):
            d = t["desc"].upper()
            src = ("Stephen (Partner)" if t["group"] == "Zelle (Stephen)" else "Venmo Cashouts" if "VENMO CASHOUT" in d else
                   "Tremendous (work)" if "TREMENDOUS" in d else "Apple Savings" if "SAVINGS" in d and "APPLE" in d else "Other Income")
            inc[src] = round(inc.get(src, 0) + t["credit"], 2)
        if t["debit"] and t["group"] == "Credit Card Payments":
            card = t["cat"].replace("CC Payment — ", "")
            outc[card] = round(outc.get(card, 0) + t["debit"], 2)
    D["sankey"]["edges"] = ([{"from": k, "to": "Checking", "flow": v} for k, v in sorted(inc.items(), key=lambda x: -x[1])] +
                            [{"from": "Checking", "to": k, "flow": v} for k, v in sorted(outc.items(), key=lambda x: -x[1])] +
                            [{"from": "Checking", "to": "Living / Spending", "flow": T["nonCcSpending"]}])
    T["sankeyInflow"] = round(sum(inc.values()), 2)

    # waterfall
    D["waterfall"], prev = [], None
    for mk, lbl in zip(MK, D["meta"]["monthLabels"]):
        D["waterfall"].append({"month": lbl, "debt": debt[mk], "delta": 0 if prev is None else round(debt[mk] - prev, 2), "isFirst": prev is None})
        prev = debt[mk]

    # calendar
    cal = D["calendar"] = {"daily_spend": {}, "daily_cc": {}, "daily_stephen": {}}
    for t in CT:
        k = dk(t)
        if t["group"] == PASS: continue
        if t["group"] == "Zelle (Stephen)":
            if t["credit"]: cal["daily_stephen"][k] = round(cal["daily_stephen"].get(k, 0) + t["credit"], 2)
            continue
        if t["group"] == "Credit Card Payments" and t["debit"]:
            cal["daily_cc"][k] = round(cal["daily_cc"].get(k, 0) + t["debit"], 2); continue
        if t["debit"]:
            cal["daily_spend"][k] = round(cal["daily_spend"].get(k, 0) + t["debit"], 2)

    # health: 45 utilisation + 35 three-close trend + 20 payment status (see ledger_close.md)
    for a in D["accounts"]:
        bal, lim = a["latestBalance"], a.get("creditLimit") or 8000.0
        uf = min(1.0, bal / lim)
        sp = a["sparkline"]; ref = sp[-4] if len(sp) >= 4 else (sp[0] if sp else 0)
        ts = 1.0 if bal == 0 else (0.0 if ref <= 0 else max(0.0, min(1.0, (ref - bal) / ref / 0.25)))
        last = [m for m in a["monthly"] if m.get("balance") is not None][-1]
        ps = 0.0 if (n(last.get("returnedPayments")) or last.get("pastDue") or (last.get("minimumPayment") and n(last.get("payments")) < n(last.get("minimumPayment")) and last.get("payments") is not None and n(last.get("prevBalance")) > 0)) else 1.0
        if last.get("estimated"): ps = 0.0
        pen = 20 if a.get("postPeriod", {}).get("balance") else 0
        a["healthScore"] = int(round(max(0, min(100, 45 * (1 - uf) + 35 * ts + 20 * ps - pen))))
    D["accounts"].sort(key=lambda a: (-a["apr"], a["name"]))
    for i, a in enumerate(D["accounts"]):
        a["attackPriority"] = i + 1
    return D


def rebase_page_js(s, D):
    """Payoff Lab starts the month after periodEnd; calendar ends at the last checking row."""
    y, m = map(int, D["meta"]["periodEnd"].split("-"))
    m += 1
    if m == 13: y, m = y + 1, 1
    lbl = f"{MONTH_LABELS[m-1]} '{str(y)[2:]}"
    s, k1 = re.subn(r"// idx 0 = [A-Z][a-z]{2} '\d\d[^\n]*\n(\s*)const d = new Date\(\d{4}, \d{1,2} \+ idx, 1\);",
                    lambda mm: f"// idx 0 = {lbl} (first simulated month — every card has closed its {MONTH_LABELS[m-2 if m>1 else 11]} cycle)\n{mm.group(1)}const d = new Date({y}, {m-1} + idx, 1);", s)
    # deferred-interest deadline: months from the first simulated month to Feb '27
    dl = (2027 - y) * 12 + (2 - m)
    s, k2 = re.subn(r"deadlineIdx: \d+ \}; // t=0 is [^\n]*", f"deadlineIdx: {dl} }}; // t=0 is {lbl}; t={dl} is Feb '27", s)
    last = max(dk(t) for t in D["checkingTransactions"])
    ly, lm, ld = map(int, last.split("-"))
    s, k3 = re.subn(r"const endDate = new Date\(\d{4}, \d{1,2}, \d{1,2}\);[^\n]*", f"const endDate = new Date({ly}, {lm-1}, {ld});   // last checking transaction", s)
    return s, (k1, k2, k3)


def copy_checklist(s, D):
    """Narrative strings that carry dates or period-wide numbers — a human (or Claude) rewrites these."""
    hits = []
    for pat in [r"Oct '25 – [A-Z][a-z]{2} '\d\d", r"\b(Ten|Eleven|Twelve|Thirteen|Fourteen) months", r"\d+-month trend", r"Total Revolving Debt · [A-Z][a-z]+ 2026",
                r"data-target=\"\d+\"", r"sincebar-meta\">[^<]*", r"Across (ten|eleven|twelve|thirteen) months", r"\$[\d,]+ vanished into APRs", r"Where the \$[\d,.]+K? lives", r"CC Payments by Card — Where the \$[\d,]+ went"]:
        for mm in re.finditer(pat, s):
            line = s.count("\n", 0, mm.start()) + 1
            hits.append(f"  line {line}: {mm.group(0)[:90]}")
    return hits


def cmd_apply(args):
    spec = json.loads(Path(args.spec).read_text(encoding="utf-8"))
    s, i, j, D = read_page()
    mk = spec["month"]
    M = D["meta"]
    if mk not in M["monthKeys"]:
        M["monthKeys"].append(mk); M["monthLabels"].append(spec.get("label") or label_for(mk))
    M["periodEnd"] = max(M["monthKeys"]); M["updated"] = spec.get("updated") or date.today().isoformat()
    for a in D["accounts"]:
        row = spec.get("accounts", {}).get(a["key"])
        if row is not None:
            row = dict(row); row["month"] = mk
            idx = next((k for k, m in enumerate(a["monthly"]) if m["month"] == mk), None)
            if idx is None: a["monthly"].append(row)
            else: a["monthly"][idx] = row
        # account-level facts that change over time (a raised limit, a reissued card's name, a new APR)
        for k2, v2 in spec.get("accountMeta", {}).get(a["key"], {}).items():
            if k2 in ("name", "creditLimit", "apr", "issuer"):
                a[k2] = v2
        if a["key"] in spec.get("recommendations", {}):
            a["recommendation"], a["recommendationColor"] = spec["recommendations"][a["key"]]
        if a["key"] in spec.get("postPeriod", {}):
            a["postPeriod"] = spec["postPeriod"][a["key"]]
        elif "postPeriod" in a and args.clear_post_period:
            del a["postPeriod"]
    seen = {(t["date"], t["desc"], t["debit"], t["credit"]) for t in D["checkingTransactions"]}
    added = 0
    for t in spec.get("checking", []):
        if (t["date"], t["desc"], t["debit"], t["credit"]) not in seen:
            D["checkingTransactions"].append(t); added += 1
    for p in spec.get("stephenPayments", []):
        if not any(x["date"] == p["date"] and x["amount"] == p["amount"] for x in D["stephen"]["payments"]):
            D["stephen"]["payments"].append(p)
    if spec.get("installment"):
        inst = D.setdefault("installment", {})
        newst = spec["installment"].pop("statements", [])
        inst.update(spec["installment"])
        have = {x["n"] for x in inst.get("statements", [])}
        inst.setdefault("statements", []).extend([x for x in newst if x["n"] not in have])
        inst["statements"].sort(key=lambda x: x["n"])
    recompute(D)
    s2, counts = rebase_page_js(s, D)
    # the DATA line may have moved if rebase touched text before it; relocate
    i2 = s2.index(MARKER); j2 = s2.index("\n", i2)
    if args.dry_run:
        print("dry run — nothing written")
    else:
        write_page(s2, i2, j2, D)
    T = D["totals"]
    print(f"month {mk} applied · checking rows added {added} · lab/deadline/calendar rebased {counts}")
    print(f"debt {json.dumps(T['debt'])}")
    print(f"current {T['currentDebt']:,.2f} · Δ vs start {T['debtChangePeriod']:+,.2f} · interest {T['periodInterest']:,.2f} · card payments {T['periodCardPayments']:,.2f} · returned {T['returnedPayments']:,.2f}")
    for a in D["accounts"]:
        print(f"  #{a['attackPriority']} {a['name']:<18} {a['latestBalance']:>9,.2f} util {str(a['utilization']):>5} health {a['healthScore']:>3} {a['recommendation']}")
    print("KPI data-targets to set: kpiDebt", round(T["currentDebt"]), "kpiInt", round(T["periodInterest"]), "kpiSteph", round(T["stephenIn"]), "kpiCC", round(T["periodPayments"]))
    print("Narrative copy still to rewrite by hand:")
    for h in copy_checklist(s2, D):
        print(h)
    return 0


# ----------------------------------------------------------------------------- check
def identity_gaps(D):
    out = []
    for a in D["accounts"]:
        for m in a["monthly"]:
            if m.get("balance") is None or m.get("prevBalance") is None:
                continue
            calc = round(m["prevBalance"] - n(m.get("payments")) + n(m.get("purchases")) + n(m.get("fees")) + n(m.get("interest")), 2)
            gap = round(m["balance"] - calc, 2)
            if abs(gap) > 0.02:
                out.append((a["key"], m, gap))
    return out


def cmd_backfill(args):
    """Rows entered with purchases=0 whose balance moved more than payments+interest explain: derive
    net new charges arithmetically (balance - prev + payments - interest - fees) and mark them derived."""
    s, i, j, D = read_page()
    fixed = 0
    for key, m, gap in identity_gaps(D):
        if n(m.get("purchases")) == 0 and gap > 0.02:
            m["purchases"] = round(gap, 2); m["purchasesDerived"] = True; fixed += 1
            print(f"  {key} {m['month']}: purchases derived = {m['purchases']}")
    if fixed and not args.dry_run:
        recompute(D); write_page(s, i, j, D)
    print(f"{fixed} rows backfilled{' (dry run)' if args.dry_run else ''}")
    return 0


def cmd_check(args):
    s, i, j, D = read_page()
    ok = True
    MK = D["meta"]["monthKeys"]
    assert len(MK) == len(D["meta"]["monthLabels"]), "monthKeys/monthLabels length mismatch"
    assert [f["month"] for f in D["monthlyFlow"]] == MK, "monthlyFlow is not aligned with monthKeys"
    for key, m, gap in identity_gaps(D):
        hard = args.strict or m["month"] == D["meta"]["periodEnd"]
        if hard:
            ok = False
        print(f"{'ERROR' if hard else 'warn '}: {key} {m['month']} balance is {gap:+.2f} off prev-payments+purchases+fees+interest"
              + (" (purchases derived)" if m.get("purchasesDerived") else "") + (" — statement credits/returns not modelled" if abs(gap) < 15 else " — a purchases or credits figure is missing"))
    carry = {a["key"]: 0.0 for a in D["accounts"]}
    for mk in MK:
        tb = 0.0
        for a in D["accounts"]:
            m = next(x for x in a["monthly"] if x["month"] == mk)
            if m.get("balance") is not None: carry[a["key"]] = m["balance"]
            tb += carry[a["key"]]
        if abs(round(tb, 2) - D["totals"]["debt"][mk]) > 0.02:
            ok = False; print(f"ERROR: debt total off for {mk}: {round(tb,2)} vs {D['totals']['debt'][mk]}")
    blocks = re.findall(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>", s, re.S)
    tmp = Path("/tmp/_ledger_check.js"); tmp.write_text(blocks[-1], encoding="utf-8")
    r = subprocess.run(["node", "--check", str(tmp)], capture_output=True, text=True)
    if r.returncode != 0:
        ok = False; print(r.stderr[:800])
    print("OK — blob parses, totals reconcile, script compiles" if ok else "PROBLEMS FOUND")
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("dump")
    e = sub.add_parser("extract"); e.add_argument("month"); e.add_argument("--statements")
    a = sub.add_parser("apply"); a.add_argument("spec"); a.add_argument("--dry-run", action="store_true"); a.add_argument("--clear-post-period", action="store_true")
    c = sub.add_parser("check"); c.add_argument("--strict", action="store_true", help="fail on any month, not just the latest")
    b = sub.add_parser("backfill-purchases"); b.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    return {"dump": cmd_dump, "extract": cmd_extract, "apply": cmd_apply, "check": cmd_check, "backfill-purchases": cmd_backfill}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main() or 0)

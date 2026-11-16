"""EJO revision analyses (13 Nov 2026), in response to the three internal peer reviews of V24.
Run on the Mac: python3 output/ejo_recut/revision_analyses.py "<paper folder>"
Writes output/ejo_recut/revision/*.csv|json and prints a summary.
"""
import csv, collections, json, math, pathlib, re, sys, time, urllib.parse, urllib.request
import numpy as np
from scipy import stats
import openpyxl

HERE = pathlib.Path(__file__).parent
ROOT = HERE.parent.parent
OUT = HERE / 'revision'; OUT.mkdir(exist_ok=True)
P = pathlib.Path(sys.argv[1]); RC = P / '03 Supplemental Content/RCT classification'
FIN = list(csv.DictReader(open(RC / 'rct_final_codes_2026-11-13.csv', encoding='utf-8')))
R1 = {r['pmid']: r for r in csv.DictReader(open(RC / 'rater1_MH_final_2026-11-03.csv', encoding='utf-8'))}
recs = json.load(open(ROOT / 'cache/records.json'))
recs = recs if isinstance(recs, list) else list(recs.values())
corpus = set(l.strip() for l in open(ROOT / 'data/pmids_final_corpus_2026-09-10.txt') if l.strip())
REC = {str(r['pmid']): r for r in recs if str(r['pmid']) in corpus}
S = {}

# 1. Flow and trials per year from FINAL codes
is_trial = lambda r: r['f1'] in ('TAGGED', 'Y') and r['f2a'] == 'Y'
A = [r for r in FIN if r['set'] == 'A']; B = [r for r in FIN if r['set'] == 'B']
rep = [r for r in FIN if is_trial(r)]
S['flow'] = dict(tagged=len(A), tagged_confirmed=sum(map(is_trial, A)), untagged=len(B), untagged_confirmed=sum(map(is_trial, B)),
                 reports=len(rep), primary=sum(r['f2b'] == 'PRIMARY' for r in rep), secondary=sum(r['f2b'] == 'SECONDARY' for r in rep),
                 unclear=sum(r['f2b'] == 'UNCLEAR' for r in rep),
                 tagged_not_trial_reasons={f'{a}/{b}': v for (a, b), v in collections.Counter((r['f1'], r['f2a']) for r in A if not is_trial(r)).items()})
prim = [r for r in rep if r['f2b'] == 'PRIMARY']
T = collections.Counter(int(r['year']) for r in prim)
T1 = collections.Counter(int(r['year']) for r in R1.values() if r['f1'] in ('TAGGED', 'Y') and r['f2a'] == 'Y' and r['f2b'] == 'PRIMARY')
TU = collections.Counter(int(r['year']) for r in rep if r['f2b'] in ('PRIMARY', 'UNCLEAR'))
S['trials_year_changed_by_adjudication'] = {y: (T1[y], T[y]) for y in sorted(set(T) | set(T1)) if T1[y] != T[y]}

# 2. Syntheses (confirmed) per year
wb = openpyxl.load_workbook(RC / 'CXL SR-MA check Fable drafts for MH confirmation.xlsx', data_only=True)
ws = wb['Candidates']; hdr = [c.value for c in ws[1]]; ix = {h: i for i, h in enumerate(hdr)}
SYN = collections.Counter(); syn_rows = []; cand_pmids = set()
for row in ws.iter_rows(min_row=2, values_only=True):
    cand_pmids.add(str(row[ix['PMID']]))
    fin = row[ix['MH counts as synthesis']] or row[ix['Fable counts_as_synthesis']]
    if fin == 'Y':
        SYN[int(row[ix['Year']])] += 1; syn_rows.append((str(row[ix['PMID']]), int(row[ix['Year']]), row[ix['Title']]))

# 3. Same-rule (symmetric) counts across all years: title-only and publication-type-only
TI = re.compile(r'systematic review|meta-?analy|meta analy|umbrella review|pooled analysis', re.I)
AB = re.compile(r'systematic(ally)? review|meta-?analy|meta analy|umbrella review', re.I)
title_syn = collections.Counter(); pt_syn = collections.Counter(); pt_ma = collections.Counter(); pt_sr = collections.Counter()
abstract_only = []
for p, r in REC.items():
    y = int(r['year']); pts = [str(t).lower() for t in (r.get('pub_types') or [])]
    if TI.search(r.get('title') or ''): title_syn[y] += 1
    if 'meta-analysis' in pts: pt_ma[y] += 1
    if 'systematic review' in pts: pt_sr[y] += 1
    if 'meta-analysis' in pts or 'systematic review' in pts: pt_syn[y] += 1
    if p not in cand_pmids and AB.search(r.get('abstract') or '') and not TI.search(r.get('title') or ''):
        abstract_only.append((p, y, r.get('title'), (r.get('journal') or '')))
with open(OUT / 'srma_abstract_only_candidates.csv', 'w', newline='', encoding='utf-8') as fh:
    w = csv.writer(fh); w.writerow(['pmid', 'year', 'title', 'journal']); w.writerows(sorted(abstract_only, key=lambda x: x[1]))
S['srma_abstract_only_candidates'] = len(abstract_only)
S['pt_systematic_review_first_year'] = min(pt_sr) if pt_sr else None

# 4. Period table
per = {'2001-10': range(2001, 2011), '2011-15': range(2011, 2016), '2016-20': range(2016, 2021), '2021-25': range(2021, 2026),
       '2021-24': range(2021, 2025), '2022-25': range(2022, 2026), '2022-24': range(2022, 2025)}
tab = {k: dict(trials=sum(T[y] for y in v), trials_incl_unclear=sum(TU[y] for y in v), syntheses=sum(SYN[y] for y in v),
               title_only=sum(title_syn[y] for y in v), pubtype_sr_or_ma=sum(pt_syn[y] for y in v), pubtype_ma=sum(pt_ma[y] for y in v))
       for k, v in per.items()}
S['periods'] = tab
with open(OUT / 'per_year.csv', 'w', newline='') as fh:
    w = csv.writer(fh); w.writerow(['year', 'trials_final', 'trials_rater1', 'trials_incl_unclear', 'syntheses_confirmed', 'title_only', 'pubtype_sr_or_ma', 'pubtype_ma', 'pubtype_sr', 'all_records'])
    allr = collections.Counter(int(r['year']) for r in REC.values())
    for y in range(2001, 2026): w.writerow([y, T[y], T1[y], TU[y], SYN[y], title_syn[y], pt_syn[y], pt_ma[y], pt_sr[y], allr[y]])

# 5. Trend statistics
def rr_exact(a, b, alpha=0.05):  # rate ratio a/b (equal person-time), conditional binomial CI
    n = a + b; lo = stats.beta.ppf(alpha / 2, a, n - a + 1) if a > 0 else 0.0; hi = stats.beta.ppf(1 - alpha / 2, a + 1, n - a) if a < n else 1.0
    return dict(rr=round(a / b, 2) if b else None, lo=round(lo / (1 - lo), 2), hi=round(hi / (1 - hi), 2) if hi < 1 else None,
                p=round(stats.binomtest(a, n, 0.5).pvalue, 4))
def poisson_trend(years, counts):  # IRLS log-linear Poisson, returns annual rate ratio and 95% Wald CI
    X = np.column_stack([np.ones(len(years)), np.array(years) - np.mean(years)]); yv = np.array(counts, float)
    b = np.array([math.log(max(yv.mean(), 0.1)), 0.0])
    for _ in range(100):
        mu = np.exp(X @ b); Wm = np.diag(mu); z = X @ b + (yv - mu) / mu
        bn = np.linalg.solve(X.T @ Wm @ X, X.T @ Wm @ z)
        if np.max(np.abs(bn - b)) < 1e-10: b = bn; break
        b = bn
    mu = np.exp(X @ b); cov = np.linalg.inv(X.T @ np.diag(mu) @ X); se = math.sqrt(cov[1, 1])
    disp = float(np.sum((yv - mu) ** 2 / mu) / (len(yv) - 2))
    sq = max(1.0, disp) ** 0.5
    return dict(annual_rr=round(math.exp(b[1]), 3), lo=round(math.exp(b[1] - 1.96 * se * sq), 3), hi=round(math.exp(b[1] + 1.96 * se * sq), 3),
                p=round(2 * (1 - stats.norm.cdf(abs(b[1] / (se * sq)))), 4), dispersion=round(disp, 2))
yrs = list(range(2016, 2026))
S['trend'] = {
    'trials_2021-25_vs_2016-20': rr_exact(tab['2021-25']['trials'], tab['2016-20']['trials']),
    'syntheses_2021-25_vs_2016-20': rr_exact(tab['2021-25']['syntheses'], tab['2016-20']['syntheses']),
    'syntheses_vs_trials_2021-25': rr_exact(tab['2021-25']['syntheses'], tab['2021-25']['trials']),
    'syntheses_vs_trials_2022-25': rr_exact(tab['2022-25']['syntheses'], tab['2022-25']['trials']),
    'syntheses_vs_trials_2021-24': rr_exact(tab['2021-24']['syntheses'], tab['2021-24']['trials']),
    'fisher_2x2_trials_syntheses_2016-20_vs_2021-25': dict(zip(['odds_ratio', 'p'], [round(x, 4) for x in stats.fisher_exact(
        [[tab['2016-20']['trials'], tab['2016-20']['syntheses']], [tab['2021-25']['trials'], tab['2021-25']['syntheses']]])])),
    'poisson_trials_2016-2025': poisson_trend(yrs, [T[y] for y in yrs]),
    'poisson_syntheses_2016-2025': poisson_trend(yrs, [SYN[y] for y in yrs]),
    'poisson_trials_2011-2025': poisson_trend(list(range(2011, 2026)), [T[y] for y in range(2011, 2026)]),
    'poisson_syntheses_2011-2025': poisson_trend(list(range(2011, 2026)), [SYN[y] for y in range(2011, 2026)]),
}

# 6. Agreement on trial-characteristic fields (Rater 1 vs Rater 2, records both coded as trials)
wb2 = openpyxl.load_workbook(RC / 'Rater 2 MLF/returned 2026-11-09 CXL RCT classification Rater 2 coding sheet MLF v2 - AI-coded (Claude)_1.xlsx', data_only=True)
R2 = {}
for s in ('Set A', 'Set B'):
    w2 = wb2[s]; hh = [c.value for c in w2[1]]
    for row in w2.iter_rows(min_row=2, values_only=True):
        d = dict(zip(hh, row))
        if d['PMID']: R2[str(d['PMID'])] = {k: ('' if v is None else str(v).strip()) for k, v in d.items()}
def kappa(pairs):
    n = len(pairs); po = sum(a == b for a, b in pairs) / n
    ca = collections.Counter(a for a, _ in pairs); cb = collections.Counter(b for _, b in pairs)
    pe = sum(ca[k] * cb.get(k, 0) for k in ca) / n / n
    return dict(n=n, agreement=round(po, 3), kappa=(round((po - pe) / (1 - pe), 3) if pe < 1 else None))
g2 = lambda d: d['F1 Is RCT'] in ('TAGGED', 'Y') and d['F2a CXL arm'] == 'Y'
both = [p for p in R2 if p in R1 and (R1[p]['f1'] in ('TAGGED', 'Y') and R1[p]['f2a'] == 'Y') and g2(R2[p])]
def num(v):
    v = (v or '').lower().replace('p', '').strip()
    try: return float(v)
    except ValueError: return None
ag = {'denominator_records_both_trial': len(both)}
for lab, k1, k2 in (('Eyes (exact)', 'eyes', 'F5 Eyes'), ('Follow-up months (exact)', 'fu_months', 'F5 Follow-up (months)'),
                    ('Primary outcome', 'out', 'F5 Primary outcome')):
    ag[lab] = kappa([(R1[p][k1].strip(), R2[p][k2]) for p in both])
fu = [(num(R1[p]['fu_months']), num(R2[p]['F5 Follow-up (months)'])) for p in both]
ag['FU>=12 (binary)'] = kappa([('NR' if a is None else a >= 12, 'NR' if b is None else b >= 12) for a, b in fu])
ey = [(num(R1[p]['eyes']), num(R2[p]['F5 Eyes'])) for p in both]
ok = [(a, b) for a, b in ey if a is not None and b is not None]
ag['Eyes within 10%'] = dict(n=len(ok), agreement=round(sum(abs(a - b) <= 0.1 * max(a, b) for a, b in ok) / len(ok), 3))
PROT = {'C03', 'C04', 'C05', 'C06', 'C07', 'C08', 'C09', 'C10a', 'C10b', 'C10c', 'C11', 'C14'}
bp = [p for p in both if R1[p]['c'] in PROT and R2[p]['F3 Comparison (primary)'] in PROT]
for lab, k1, k2 in (('H1 params', 'h1', 'F6 H1 Params'), ('H2 in use', 'h2', 'F6 H2 In use'), ('H3 endpoint', 'h3', 'F6 H3 Endpoint'), ('H4 FU>=12', 'h4', 'F6 H4 FU≥12')):
    ag[lab] = kappa([(R1[p][k1], R2[p][k2]) for p in bp])
hh = lambda r1, a, b, c: 'Y' if all(r1[x] == 'Y' for x in (a, b, c)) else 'N'
ag['Head-to-head derived (protocol trials)'] = kappa([(hh(R1[p], 'h1', 'h2', 'h3'), 'Y' if all(R2[p][k] == 'Y' for k in ('F6 H1 Params', 'F6 H2 In use', 'F6 H3 Endpoint')) else 'N') for p in bp])
S['agreement_characteristics'] = ag

# 7. Head-to-head criteria breakdown (final codes, 46 protocol trials)
pt = [r for r in prim if r['c'] in PROT]
S['protocol_trials'] = len(pt)
S['h_fail_patterns'] = {('fails ' + '+'.join(k)) if k else 'meets H1-H3': v for k, v in collections.Counter(
    tuple(h.upper() for h in ('h1', 'h2', 'h3') if r[h] != 'Y') for r in pt).items()}
S['h_each'] = {h: dict(collections.Counter(r[h] for r in pt)) for h in ('h1', 'h2', 'h3', 'h4')}
S['primary_outcome_protocol'] = dict(collections.Counter(r['out'] for r in pt))
S['primary_outcome_all_trials'] = dict(collections.Counter(r['out'] for r in prim))
S['protocol_ectasia_only'] = sum(r['ind'] in ('I1', 'I2', 'I3', 'I4', 'I5', 'I7') for r in pt)
S['protocol_by_period'] = {k: sum(int(r['year']) in v for r in pt) for k, v in per.items() if k in ('2001-10', '2011-15', '2016-20', '2021-25')}

# 8. Comparator literatures: RCT vs SR/MA publication types by period (live PubMed counts, dated)
def count(term):
    u = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?' + urllib.parse.urlencode({'db': 'pubmed', 'term': term, 'rettype': 'count', 'retmode': 'json'})
    for i in range(4):
        try:
            time.sleep(0.4); return int(json.load(urllib.request.urlopen(u, timeout=60))['esearchresult']['count'])
        except Exception:
            time.sleep(2 + 2 * i)
    return None
bm = json.load(open(ROOT / 'cache/benchmarks.json'))
cxl_q = [k for k in bm if 'cross-linking' in k and 'Randomized' not in k][0]
lits = {'CXL (study query)': cxl_q.split(' AND ("2001/01/01"')[0]}
for m in ('Keratoconus', 'Corneal Transplantation', 'Glaucoma', 'Dry Eye Syndromes', 'Keratomileusis, Laser In Situ', 'Cataract Extraction', 'Macular Degeneration'):
    lits[m] = f'"{m}"[MeSH Terms]'
pers = {'2011-15': ('2011', '2015'), '2016-20': ('2016', '2020'), '2021-25': ('2021', '2025')}
comp = []
for name, q in lits.items():
    for pk, (a, b) in pers.items():
        base = f'({q}) AND ("{a}/01/01"[PDAT] : "{b}/12/31"[PDAT])'
        rct = count(base + ' AND "Randomized Controlled Trial"[pt]')
        srma = count(base + ' AND ("Systematic Review"[pt] OR "Meta-Analysis"[pt])')
        comp.append(dict(literature=name, period=pk, rct_pt=rct, srma_pt=srma, ratio=round(srma / rct, 2) if rct else None))
with open(OUT / 'comparator_srma_rct_ratio.csv', 'w', newline='') as fh:
    w = csv.DictWriter(fh, fieldnames=list(comp[0])); w.writeheader(); w.writerows(comp)
S['comparator_ratio_retrieved'] = time.strftime('%Y-%m-%d')
S['comparator'] = comp

json.dump(S, open(OUT / 'revision_summary.json', 'w'), indent=1, default=str)
print(json.dumps(S, indent=1, default=str))

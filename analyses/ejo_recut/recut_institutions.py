"""EJO re-cut (2 Nov 2026): institution tables, all-author primary affiliation,
with the ELZA attribution rule extended as decided by M. Hillen on 2 Nov 2026:
from 2015 onwards, where F. Hafezi's primary (first-listed) affiliation resolves to
the University of Zurich (incl. CABMM), it is credited to the ELZA Institute.
IROC and non-Zurich primary affiliations are left as stated. Whole and fractional
counting are unchanged by the rule. Reads cached records only; no network; does not
touch output/ or output/sdc/."""
import json, sys, csv, pathlib, collections, copy
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import config, institutions, impute
from analyze import institution_stats_meta
OUT = pathlib.Path(__file__).parent
frozen = set((ROOT/'data/pmids_final_corpus_2026-09-10.txt').read_text().split())
recs = [r for r in json.load(open(ROOT/'cache/records_disambig.json')) if str(r['pmid']) in frozen]
cited = {str(r['pmid']): r for r in json.load(open(ROOT/'cache/records_cited.json'))}
for r in recs:
    c = cited.get(str(r['pmid']), {})
    r['citation_count'] = c.get('citation_count')
print('records', len(recs))
imp = impute.impute_affiliations(recs, window=config.IMPUTE_WINDOW_YEARS)
print('impute', imp)

def write(name, rows):
    with open(OUT/name, 'w', newline='', encoding='utf-8') as fh:
        w = csv.writer(fh); w.writerow(['rank','institution','publications','pct_of_resolved','citations','n_cited_known'])
        for r in rows: w.writerow([r['rank'], r['institution'], r['count'], r['pct_of_resolved'], r['citations'], r['n_cited_known']])

# 1) baseline (must reproduce output/sdc/institutions_allauthors_primary_canonical.csv)
base = {}
for counting in ('primary','whole','fractional'):
    for scope, fo in (('allauthors', False), ('firstauthor', True)):
        rows, meta = institution_stats_meta(recs, fo, 'canonical', counting, 60)
        base[(scope, counting)] = rows
        write(f'baseline_institutions_{scope}_{counting}_canonical.csv', rows)
print('baseline all-author primary top6:', [(r['institution'], r['count']) for r in base[('allauthors','primary')][:6]])

# 2) ELZA rule extension (primary affiliation only)
ELZA = institutions.resolve('ELZA Institute')
orig = institutions.author_institutions
log = []
def patched(author, first_surname='', pmid=None):
    res = orig(author, first_surname, pmid)
    if res and author.get('last') == 'Hafezi' and (author.get('fore') or author.get('initials') or '').startswith('F'):
        yr = YEAR.get(str(pmid), 0)
        if yr >= 2015 and res[0].canonical == 'University of Zurich':
            log.append((str(pmid), yr, author.get('affil_source','stated'), (author.get('affils') or [''])[0][:120]))
            res = [ELZA] + [r for r in res[1:] if r.canonical != 'ELZA Institute']
    return res
YEAR = {str(r['pmid']): int(r['year']) for r in recs}
institutions.author_institutions = patched
for counting in ('primary',):
    for scope, fo in (('allauthors', False), ('firstauthor', True)):
        for level in ('canonical','parent','cluster'):
            log.clear()
            rows, meta = institution_stats_meta(recs, fo, level, counting, 60)
            write(f'elzarule_institutions_{scope}_{counting}_{level}.csv', rows)
            if scope == 'allauthors' and level == 'canonical':
                print('ELZA-rule all-author primary top8:', [(r['institution'], r['count'], r['rank']) for r in rows[:8]])
                print('meta', meta)
                with open(OUT/'elzarule_reassigned_records.csv','w',newline='',encoding='utf-8') as fh:
                    w=csv.writer(fh); w.writerow(['pmid','year','affil_source','hafezi_first_affiliation']); w.writerows(sorted(set(log)))
                print('records reassigned', len(set(log)))
            if scope == 'firstauthor' and level == 'canonical':
                print('ELZA-rule first-author primary top6:', [(r['institution'], r['count'], r['rank']) for r in rows[:6]])

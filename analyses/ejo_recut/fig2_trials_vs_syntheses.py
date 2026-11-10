"""EJO Figure 2: new randomized trials vs systematic reviews/meta-analyses of CXL per year.
Reads the frozen, author-confirmed classification files from the paper folder.
Run on the Mac (Arial installed): python3 analyses/ejo_recut/fig2_trials_vs_syntheses.py"""
import csv, collections, pathlib, sys
import openpyxl, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
HERE = pathlib.Path(__file__).parent
# Classification files: the frozen copies in classification/ (from the paper folder's
# '03 Supplemental Content/RCT classification', 3 Nov 2026), or a folder given on the command line.
RC = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / 'classification'
have_arial = any('Arial' in f.name for f in font_manager.fontManager.ttflist)
plt.rcParams.update({'font.family': 'sans-serif', 'font.sans-serif': ['Arial', 'Liberation Sans', 'DejaVu Sans'],
                     'font.size': 8, 'pdf.fonttype': 42, 'axes.spines.top': False, 'axes.spines.right': False})
trials = collections.Counter(); trials_screen = collections.Counter()
for r in csv.DictReader(open(RC / 'rater1_MH_final_2026-11-03.csv', encoding='utf-8')):
    if r['f1'] in ('TAGGED', 'Y') and r['f2a'] == 'Y' and r['f2b'] == 'PRIMARY':
        trials[int(r['year'])] += 1
        if r['set'] == 'B': trials_screen[int(r['year'])] += 1
wb = openpyxl.load_workbook(RC / 'CXL SR-MA check Fable drafts for MH confirmation.xlsx', data_only=True)
ws = wb['Candidates']; hdr = [c.value for c in ws[1]]; ix = {h: i for i, h in enumerate(hdr)}
syn = collections.Counter()
for row in ws.iter_rows(min_row=2, values_only=True):
    fin = row[ix['MH counts as synthesis']] or row[ix['Fable counts_as_synthesis']]
    if fin == 'Y': syn[int(row[ix['Year']])] += 1
years = list(range(2009, 2026))
T = [trials[y] for y in years]; S = [syn[y] for y in years]
TB = [trials_screen[y] for y in years]; TA = [t - b for t, b in zip(T, TB)]
with open(HERE / 'fig2_data.csv', 'w', newline='') as fh:
    w = csv.writer(fh); w.writerow(['year', 'new_primary_trials', 'of_which_found_by_text_screen', 'systematic_reviews_meta_analyses'])
    w.writerows(zip(years, T, TB, S))
fig, ax = plt.subplots(figsize=(6.5, 3.0))
wdt = 0.38
x = range(len(years))
ax.bar([i - wdt/2 - 0.01 for i in x], TA, wdt, color='#2a78d6', label='New trials (PubMed-tagged RCTs)')
ax.bar([i - wdt/2 - 0.01 for i in x], TB, wdt, bottom=TA, color='#86b6ef', edgecolor='white', linewidth=0.8, label='New trials (found by text screen)')
ax.bar([i + wdt/2 + 0.01 for i in x], S, wdt, color='#eb6834', label='Systematic reviews and meta-analyses')
ax.set_xticks(list(x)); ax.set_xticklabels([str(y) for y in years], rotation=90)
ax.set_ylabel('Publications per year')
ax.yaxis.grid(True, color='#e5e4df', linewidth=0.6); ax.set_axisbelow(True)
fig.tight_layout(rect=(0, 0, 1, 0.90))
h, l = ax.get_legend_handles_labels()
fig.legend(h, l, loc='upper center', ncol=3, frameon=False, fontsize=7, bbox_to_anchor=(0.5, 1.0))
for ext, kw in (('tif', {'dpi': 600, 'pil_kwargs': {'compression': 'tiff_lzw'}}), ('pdf', {}), ('png', {'dpi': 200})):
    fig.savefig(HERE / f'Figure2_trials_vs_syntheses.{ext}', **kw)
print('Arial' if have_arial else 'WARNING: Arial not found - fallback font used; re-run on the Mac for the submission file')
print('trials', dict(zip(years, T))); print('syntheses', dict(zip(years, S)))

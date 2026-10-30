"""Jejak cutting plane pada data nasional (n = 514) dari log eksperimen, sebagai tiga gambar terpisah:
objektif LP (RQ1), jumlah kendala segitiga di LP (RQ2), dan waktu kumulatif (RQ3).

Sumber: results/nasional/{A,C}_nasional2024_log_lp.csv dan results/ablasi/E_nasional2024_log_lp.csv (ulangan pertama).
"""
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
HASIL = os.path.join(HERE, '..', 'results')
VAR = [('Baseline', os.path.join('nasional', 'A_nasional2024'), dict(color='black', ls='-', lw=1.4)),
       ('UCP-CR', os.path.join('nasional', 'C_nasional2024'), dict(color='#2a78d6', ls='--', lw=1.6)),
       ('UCP-TR', os.path.join('ablasi', 'E_nasional2024'), dict(color='#eb6834', ls=':', lw=1.8))]
log = {nm: pd.read_csv(os.path.join(HASIL, f + '_log_lp.csv')) for nm, f, _ in VAR}
SUMBER = 'Sumber: log eksperimen data nasional 2024 (n = 514), ulangan pertama tiap varian.'

plt.rcParams.update({'font.size': 8, 'axes.spines.top': False, 'axes.spines.right': False,
                     'axes.edgecolor': '0.3', 'xtick.color': '0.3', 'ytick.color': '0.3'})

def angka(v, d=0):
    return f'{v:,.{d}f}'.replace(',', '#').replace('.', ',').replace('#', '.')

def kanvas():
    fig, ax = plt.subplots(figsize=(6.6, 3.3), dpi=300)
    ax.grid(axis='y', color='0.9', lw=0.6)
    ax.set_xlim(0, 84)
    ax.set_xlabel('Putaran cutting plane')
    return fig, ax

def simpan(fig, nama, catatan=SUMBER):
    fig.text(0.01, 0.01, catatan, fontsize=6.5, color='0.35', style='italic', va='bottom')
    fig.tight_layout(rect=(0, 0.05 if '\n' not in catatan else 0.08, 1, 1))
    out = os.path.join(HERE, nama)
    fig.savefig(out, dpi=300, facecolor='white')
    plt.close(fig)
    print(out)

# 1. objektif LP
fig, ax = kanvas()
for nm, _, st in VAR:
    d = log[nm]; ax.plot(d.putaran, d.obj, **st, label=nm)
ax.axhline(32729.75, color='0.6', lw=0.7)
ax.text(70.5, 32729.75, 'batas bawah\n32.729,75', va='center', ha='left', fontsize=7, color='0.25')
ax.set_ylabel('Objektif LP')
ax.yaxis.set_major_formatter(lambda v, p: angka(v))
ax.legend(frameon=False, loc='lower right', fontsize=7.5)
simpan(fig, 'gambar_jejak_objektif.png')

# 2. jumlah kendala segitiga di LP
fig, ax = kanvas()
for nm, _, st in VAR:
    d = log[nm]; ax.plot(d.putaran, d.total_segitiga / 1e6, **st, label=nm)
ax.text(49, 1.62, 'Baseline 1,79 juta dan UCP-TR 1,78 juta\n(sekitar 1,33% dari 135 juta kendala segitiga)', va='center',
        fontsize=7, color='0.15')
d = log['UCP-CR']
ax.text(d.putaran.iloc[-1] + 1.2, d.total_segitiga.iloc[-1] / 1e6, 'UCP-CR 0,58 juta', va='center', fontsize=7, color='0.15')
ax.set_ylabel('Kendala segitiga di LP (juta)')
ax.yaxis.set_major_locator(plt.MultipleLocator(0.5))
ax.yaxis.set_major_formatter(lambda v, p: angka(v, 1))
ax.legend(frameon=False, loc='lower right', fontsize=7.5)
simpan(fig, 'gambar_jejak_kendala.png')

# 3. waktu kumulatif
fig, ax = kanvas()
for nm, _, st in VAR:
    d = log[nm]; ax.plot(d.putaran, d.t_kumulatif, **st, label=nm)
for nm, _, _ in VAR:
    d = log[nm]
    ax.text(d.putaran.iloc[-1] + 1.2, d.t_kumulatif.iloc[-1], f'{nm} {angka(d.t_kumulatif.iloc[-1], 1)} s', va='center',
            fontsize=7, color='0.15')
e = log['UCP-TR']; k = 46
ax.annotate('UCP-TR: toleransi diketatkan\nke $10^{-6}$ pada putaran 46', xy=(k, e.t_kumulatif[e.putaran == k].iloc[0]),
            xytext=(52, 80), fontsize=7, arrowprops=dict(arrowstyle='-', color='0.4', lw=0.7))
ax.set_ylabel('Waktu kumulatif (detik)')
ax.legend(frameon=False, loc='upper left', fontsize=7.5)
simpan(fig, 'gambar_jejak_waktu.png',
       SUMBER + '\nUCP-CR ulangan kedua 1.007,2 s (median 775,0 s), sehingga tidak diklaim lebih cepat.')

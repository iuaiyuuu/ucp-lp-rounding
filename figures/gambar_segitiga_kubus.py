"""Ilustrasi kubus satu segitiga nyata dari data nasional 2024, lapisan 1: kendala x_vp <= x_uv + x_up memotong kubus [0,1]^3.

Segitiga diambil dari data (sumber dicatat di sini, tidak ditampilkan di gambar): u = Wonosobo, v = Pemalang, p = Wonogiri.
Solusi akhir LP baseline dibaca dari A_nasional2024_x_lp.npy.
"""
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
from sklearn.preprocessing import StandardScaler
from scipy.spatial.distance import pdist, squareform

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')

df = pd.read_csv(os.path.join(ROOT, 'data', 'dataset_nasional_2024.csv'))
X = StandardScaler().fit_transform(df[['PDRB_ADHK', 'IPM', 'TPAK']].values)
n = len(X); D = squareform(pdist(X)); iu, ju = np.triu_indices(n, 1); P = len(iu)
th1 = np.percentile(D[iu, ju], 25)
pid = np.zeros((n, n), int); pid[iu, ju] = np.arange(P); pid[ju, iu] = np.arange(P)
x = np.load(os.path.join(ROOT, 'results', 'nasional', 'A_nasional2024_x_lp.npy'))[:P]
nama = list(df.Kabupaten_Kota)
u, v, p = (nama.index(k) for k in ('Wonosobo', 'Pemalang', 'Wonogiri'))
assert D[u, v] < th1 and D[u, p] < th1 and D[v, p] >= th1
akhir = (x[pid[u, v]], x[pid[u, p]], x[pid[v, p]])           # (x_uv, x_up, x_vp)
assert abs(akhir[2] - akhir[0] - akhir[1]) < 1e-6            # kendala terpenuhi tepat

def pr(a, b, c):
    """Proyeksi miring: sumbu 1 = x_uv (kanan), sumbu 2 = x_up (miring ke belakang), sumbu 3 = x_vp (atas)."""
    return a + 0.62 * b * np.cos(np.radians(32)), c + 0.62 * b * np.sin(np.radians(32))

def angka(v, d=1):
    return f'{v:.{d}f}'.replace('.', ',')

ORANYE, BIRU = '#eb6834', '#2a78d6'
fig, ax = plt.subplots(figsize=(6.4, 4.9), dpi=300)
ax.set_aspect('equal'); ax.axis('off')

# kubus
V = {(a, b, c): pr(a, b, c) for a in (0, 1) for b in (0, 1) for c in (0, 1)}
for a in (0, 1):
    for b in (0, 1):
        for c in (0, 1):
            for d in range(3):
                q = [a, b, c]
                if q[d] == 0:
                    r = q.copy(); r[d] = 1
                    tersembunyi = (a, b, c) == (0, 1, 0) or tuple(r) == (0, 1, 0)
                    ax.plot(*zip(V[(a, b, c)], V[tuple(r)]), color='0.55' if tersembunyi else 'black',
                            lw=0.8 if tersembunyi else 1.1, ls=(0, (3, 2)) if tersembunyi else '-')

# daerah yang dipotong (tetrahedron di sekitar (0,0,1)) dan bidang potong
tet = [(0, 0, 0), (0, 0, 1), (1, 0, 1), (0, 1, 1)]
for f in [(0, 1, 2), (0, 1, 3), (1, 2, 3)]:
    ax.add_patch(Polygon([pr(*tet[i]) for i in f], closed=True, facecolor='0.75', alpha=0.35, edgecolor='none'))
bidang = [(0, 0, 0), (1, 0, 1), (0, 1, 1)]
ax.add_patch(Polygon([pr(*q) for q in bidang], closed=True, facecolor=ORANYE, alpha=0.22, edgecolor='none'))
ax.add_patch(Polygon([pr(*q) for q in bidang], closed=True, fill=False, edgecolor=ORANYE, lw=1.8, joinstyle='round'))

# titik putaran 1 dan solusi akhir
p1 = pr(0, 0, 1); pa = pr(*akhir)
ax.plot(*p1, 'o', ms=7, mfc='black', mec='white', mew=1.3, zorder=6)
ax.plot(*pa, 'o', ms=7, mfc=BIRU, mec='white', mew=1.3, zorder=6)
ax.annotate('putaran 1: (0; 0; 1)\nmelanggar kendala sebesar 1', xy=p1, xytext=(-1.38, 1.25), fontsize=7.2,
            arrowprops=dict(arrowstyle='-', color='0.3', lw=0.7))
ax.annotate(f'solusi akhir LP: ({angka(akhir[0])}; {angka(akhir[1])}; {angka(akhir[2])})\n'
            f'{angka(akhir[2])} = {angka(akhir[0])} + {angka(akhir[1])}, kendala terpenuhi tepat',
            xy=pa, xytext=(0.62, 1.52), fontsize=7.2, color='black', arrowprops=dict(arrowstyle='-', color='0.3', lw=0.7))
ax.annotate(r'bidang potong $x_{vp} = x_{uv} + x_{up}$' '\n' 'semua titik di bidang ini optimal' '\n' 'untuk segitiga ini (biaya = 1)',
            xy=pr(0.3, 0.05, 0.35), xytext=(-1.38, 0.22), color=ORANYE, fontsize=7.2, ha='left', va='center', fontweight='bold',
            arrowprops=dict(arrowstyle='-', color=ORANYE, lw=0.8))
ax.annotate('daerah terpotong\n(melanggar kendala segitiga)', xy=pr(0.05, 0.0, 0.75), xytext=(-1.38, 0.72),
            color='0.3', fontsize=7.0, ha='left', va='center', arrowprops=dict(arrowstyle='-', color='0.4', lw=0.7))

# label sudut dan sumbu
for q, (dx, dy, ha) in {(0, 0, 0): (-0.04, -0.08, 'right'), (1, 0, 0): (0.0, -0.1, 'center'), (0, 0, 1): (-0.05, 0.0, 'right'),
                        (1, 0, 1): (0.04, -0.07, 'left'), (0, 1, 1): (0.0, 0.06, 'center'), (1, 1, 1): (0.04, 0.05, 'left'),
                        (1, 1, 0): (0.06, -0.1, 'left')}.items():
    x0, y0 = pr(*q)
    ax.text(x0 + dx, y0 + dy, '(' + '; '.join(str(k) for k in q) + ')', fontsize=6.6, ha=ha, va='center', color='0.25')
ax.annotate('', xy=pr(1.32, 0, 0), xytext=pr(1, 0, 0), arrowprops=dict(arrowstyle='-|>', color='black', lw=0.8))
ax.text(*pr(1.34, 0, -0.06), r'$x_{uv}$ (+)', fontsize=8, ha='left')
ax.annotate('', xy=pr(1, 1.45, 0), xytext=pr(1, 1, 0), arrowprops=dict(arrowstyle='-|>', color='black', lw=0.8))
ax.text(*pr(1, 1.5, 0), r'$x_{up}$ (+)', fontsize=8, ha='left', va='center')
ax.annotate('', xy=pr(0, 0, 1.3), xytext=pr(0, 0, 1), arrowprops=dict(arrowstyle='-|>', color='black', lw=0.8))
ax.text(*pr(0.03, 0, 1.32), r'$x_{vp}$ (−)', fontsize=8, ha='left')

ax.set_xlim(-1.45, 2.25); ax.set_ylim(-0.25, 1.85)
fig.text(0.01, 0.015, f'Satu segitiga dari data 2024, lapisan 1 (ambang {angka(th1, 4)}): d(u,v) = {angka(D[u, v], 3)} dan '
         f'd(u,p) = {angka(D[u, p], 3)} bertanda +, d(v,p) = {angka(D[v, p], 3)} bertanda −.',
         fontsize=6.2, color='0.3', style='italic')
fig.tight_layout(rect=(0, 0.04, 1, 1))
out = os.path.join(HERE, 'gambar_segitiga_kubus.png')
fig.savefig(out, dpi=300, facecolor='white')
print(out, akhir)

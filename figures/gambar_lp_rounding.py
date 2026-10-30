"""Ilustrasi LP-Rounding An et al. (2025): tahap LP yang dimodifikasi dan tahap pembulatan yang tidak diubah (hitam-putih)."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyArrowPatch

W, H = 7.4, 7.75
fig = plt.figure(figsize=(W, H), dpi=300)
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, W); ax.set_ylim(0, H); ax.axis('off')
FS, FSS = 8.6, 7.6
LW = 0.9
CX = W / 2

def kotak(x, y, w, h, teks, fs=FSS, tebal=False):
    ax.add_patch(Rectangle((x - w / 2, y - h / 2), w, h, fill=False, lw=LW))
    ax.text(x, y, teks, ha='center', va='center', fontsize=fs, fontweight='bold' if tebal else 'normal', linespacing=1.3)

def grup(y_atas, y_bawah, judul, w=6.6):
    ax.add_patch(Rectangle((CX - w / 2, y_bawah), w, y_atas - y_bawah, fill=False, lw=LW, ls=(0, (4, 3))))
    ax.text(CX - w / 2 + 0.12, y_atas - 0.2, judul, ha='left', va='center', fontsize=FS, fontweight='bold')

def panah(y1, y2, x=CX):
    ax.add_patch(FancyArrowPatch((x, y1), (x, y2), arrowstyle='-|>', mutation_scale=9, lw=LW, color='black', shrinkA=0, shrinkB=0))

# bingkai dan judul
ax.add_patch(Rectangle((0.15, 0.15), W - 0.3, H - 0.3, fill=False, lw=LW))
ax.text(CX, H - 0.42, 'LP-Rounding An et al. (2025) dan Bagian yang Dimodifikasi', ha='center', va='center', fontsize=9.5, fontweight='bold')

# masukan
y = H - 1.05
kotak(CX, y, 5.2, 0.62, 'Masukan: graf bertanda ℓ lapisan\n'
      r'sisi + $E^{(t)}$, sisi − $NE^{(t)}$, bobot $\delta_t$ (penelitian ini: ℓ = 2, $\delta_1 = \delta_2 = 1$)')
panah(y - 0.31, y - 0.62)

# tahap 1: LP (dimodifikasi)
g1_top = y - 0.62; g1_bot = g1_top - 1.8
grup(g1_top, g1_bot, 'Tahap 1  Penyelesaian LP-(*)  →  bagian yang dimodifikasi penelitian ini')
yy = g1_top - 0.78
kotak(CX, yy, 5.6, 0.72, r'Minimalkan Persamaan (2.5) terhadap kendala segitiga (2.6) dan kendala monoton (2.7)'
      '\n' r'Keluaran: jarak LP $\tilde{x}^{(t)}_{uv}$ dan objektif $LP^*$ (batas bawah biaya solusi terbaik)')
ax.text(CX, g1_bot + 0.42, 'An et al. (2025) tidak menetapkan cara menyelesaikan LP ini. Penelitian ini memakai cutting plane + PDLP di GPU:',
        ha='center', va='center', fontsize=6.8, style='italic')
ax.text(CX, g1_bot + 0.18, 'baseline (tanpa modifikasi), UCP-CR (pemangkasan kendala + penguncian), UCP-TR (toleransi dua tahap)',
        ha='center', va='center', fontsize=6.8, style='italic')
panah(g1_bot, g1_bot - 0.3)

# tahap 2: pembulatan (tidak diubah)
g2_top = g1_bot - 0.3; g2_bot = g2_top - 2.4
grup(g2_top, g2_bot, 'Tahap 2  Pembulatan  →  tidak diubah')
yy = g2_top - 0.8
kotak(CX, yy, 5.6, 0.62, 'Pre-clustering (Algoritma 2)\nmembentuk kelompok kecil dengan diameter kurang dari 1/3 terhadap jarak LP')
panah(yy - 0.31, yy - 0.62)
yy2 = yy - 0.62 - 0.36
kotak(CX, yy2, 5.6, 0.72, 'Hierarchical-clustering (Algoritma 1)\nmenyusun partisi tiap lapisan dari hasil pre-clustering\nsehingga setiap kelompok lapisan halus berada di dalam satu kelompok lapisan kasar')
panah(g2_bot, g2_bot - 0.3)

# keluaran
y = g2_bot - 0.3 - 0.36
kotak(CX, y, 5.2, 0.72, r'Keluaran: partisi bersarang $\mathcal{P}^{(1)}, \ldots, \mathcal{P}^{(\ell)}$'
      '\n' 'jaminan: biaya paling besar 25,7846 kali biaya solusi terbaik (An et al., 2025)')

import os; out = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'gambar_lp_rounding.png')
fig.savefig(out, dpi=300, facecolor='white')
print(out)

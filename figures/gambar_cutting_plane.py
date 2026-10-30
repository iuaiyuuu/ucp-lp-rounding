"""Ilustrasi loop cutting plane baseline beserta titik sisip UCP-CR dan UCP-TR (hitam-putih)."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Polygon, FancyArrowPatch

W, H = 7.4, 8.15
fig = plt.figure(figsize=(W, H), dpi=300)
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, W); ax.set_ylim(0, H); ax.axis('off')
FS, FSS = 8.6, 7.2
LW = 0.9
DASH = (0, (4, 3))
CX = 2.75                      # kolom utama
RX = 6.0                       # kolom kanan
CW, RW = 3.5, 2.2              # lebar kotak

def kotak(x, y, w, h, teks, fs=FSS, putus=False):
    ax.add_patch(Rectangle((x - w / 2, y - h / 2), w, h, fill=False, lw=LW, ls=DASH if putus else '-'))
    ax.text(x, y, teks, ha='center', va='center', fontsize=fs, linespacing=1.3)

def belah(x, y, w, h, teks):
    ax.add_patch(Polygon([(x, y + h / 2), (x + w / 2, y), (x, y - h / 2), (x - w / 2, y)], closed=True, fill=False, lw=LW))
    ax.text(x, y, teks, ha='center', va='center', fontsize=FSS)

def garis(pts, panah_akhir=True):
    for (x1, y1), (x2, y2) in zip(pts[:-2], pts[1:-1]):
        ax.plot([x1, x2], [y1, y2], color='black', lw=LW)
    (x1, y1), (x2, y2) = pts[-2], pts[-1]
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle='-|>' if panah_akhir else '-', mutation_scale=9,
                                 lw=LW, color='black', shrinkA=0, shrinkB=0))

def label(x, y, teks, ha='left'):
    ax.text(x, y, teks, ha=ha, va='center', fontsize=7.2, fontweight='bold')

# bingkai dan judul
ax.add_patch(Rectangle((0.15, 0.15), W - 0.3, H - 0.3, fill=False, lw=LW))
ax.text(W / 2, H - 0.42, 'Loop Cutting Plane pada Baseline, UCP-CR, dan UCP-TR', ha='center', va='center', fontsize=9.5, fontweight='bold')

# 1. LP awal
y_awal = H - 1.1
kotak(W / 2, y_awal, 6.4, 0.7, r'LP awal: kendala monoton (2.7) dan batas $0 \leq x \leq 1$, tanpa kendala segitiga ($\mathcal{T}_0 = \varnothing$)'
      '\n' r'toleransi awal $\varepsilon_0 = 10^{-6}$ (baseline, UCP-CR) atau $\varepsilon_0 = 10^{-4}$ (UCP-TR)')
y_solve = y_awal - 1.05
garis([(CX, y_awal - 0.35), (CX, y_solve + 0.33)])

# 2. selesaikan LP
kotak(CX, y_solve, CW, 0.66, r'Selesaikan LP dengan PDLP di GPU pada toleransi $\varepsilon_k$'
      '\n' 'titik awal: solusi putaran sebelumnya')
y_sep = y_solve - 1.05
garis([(CX, y_solve - 0.33), (CX, y_sep + 0.37)])

# 3. separasi
kotak(CX, y_sep, CW, 0.74, 'Separasi di GPU: tiap lapisan dan pasangan {u, v},\n'
      r'pilih $p$ dengan pelanggaran terbesar; ambil bila $> 10^{-5}$' '\n' r'$\rightarrow$ kendala baru $\mathcal{N}_k$ (Persamaan 3.7)')
y_d1 = y_sep - 1.15
garis([(CX, y_sep - 0.37), (CX, y_d1 + 0.42)])

# 4. belah ketupat N_k kosong?
belah(CX, y_d1, 1.9, 0.84, r'$\mathcal{N}_k = \varnothing$ ?')

# cabang Tidak: UCP-CR lalu tambah
y_cr = y_d1 - 1.25
garis([(CX, y_d1 - 0.42), (CX, y_cr + 0.42)])
label(CX + 0.08, y_d1 - 0.62, 'Tidak')
kotak(CX, y_cr, CW, 0.84, 'Hanya UCP-CR: buang kendala segitiga yang belum\n'
      r'terkunci dan dipenuhi dengan sisa $> 10^{-6}$, lalu kunci' '\n' '(Persamaan 3.9 dan 3.10)', putus=True)
y_add = y_cr - 1.15
garis([(CX, y_cr - 0.42), (CX, y_add + 0.3)])
kotak(CX, y_add, CW, 0.6, r'Tambahkan $\mathcal{N}_k$ ke LP (Persamaan 3.8 atau 3.10)' '\n' r'$k \leftarrow k + 1$')
# kembali ke solve lewat kiri
XL = 0.55
garis([(CX - CW / 2, y_add), (XL, y_add), (XL, y_solve), (CX - CW / 2, y_solve)])

# cabang Ya: belah ketupat toleransi
garis([(CX + 0.95, y_d1), (RX - 0.95, y_d1)])
label(CX + 1.05, y_d1 + 0.14, 'Ya')
belah(RX, y_d1, 1.9, 0.84, r'$\varepsilon_k = 10^{-6}$ ?')

# Tidak (ke atas): UCP-TR mengetatkan toleransi
y_tr = y_sep
garis([(RX, y_d1 + 0.42), (RX, y_tr - 0.42)])
label(RX + 0.08, y_d1 + 0.62, 'Tidak')
kotak(RX, y_tr, RW, 0.84, 'Hanya UCP-TR:\n' r'ketatkan $\varepsilon$ ke $10^{-6}$' '\n' 'LP yang sama diselesaikan\nulang (Persamaan 3.12)', putus=True)
garis([(RX, y_tr + 0.42), (RX, y_solve), (CX + CW / 2, y_solve)])

# Ya (ke bawah): berhenti, cek CPU, pembulatan
y_cek = y_cr
garis([(RX, y_d1 - 0.42), (RX, y_cek + 0.47)])
label(RX + 0.08, y_d1 - 0.62, 'Ya, berhenti\n(Persamaan 3.13)')
kotak(RX, y_cek, RW, 0.94, 'Periksa seluruh\n135.005.184 kendala\nsegitiga dan kendala\nmonoton di CPU (FP64)')
y_rnd = y_add
garis([(RX, y_cek - 0.47), (RX, y_rnd + 0.3)])
kotak(RX, y_rnd, RW, 0.6, 'Pembulatan\nAn et al. (2025)')

# keterangan
ax.text(W / 2, 0.5, 'Baseline: tanpa kotak putus-putus. UCP-CR: baseline + langkah pemangkasan dengan penguncian.\n'
        r'UCP-TR: baseline + pengetatan toleransi. Pada baseline dan UCP-CR, $\varepsilon_k = 10^{-6}$ sejak awal sehingga cabang UCP-TR tidak pernah dilalui.',
        ha='center', va='center', fontsize=6.8, style='italic', linespacing=1.4)

import os; out = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'gambar_cutting_plane.png')
fig.savefig(out, dpi=300, facecolor='white')
print(out)

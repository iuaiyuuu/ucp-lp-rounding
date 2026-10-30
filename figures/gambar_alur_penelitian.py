"""Gambar alur penelitian (baseline An et al., UCP-CR, UCP-TR), gaya mengikuti contoh naskah lama (jalur tahap di kiri, hitam-putih)."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyArrowPatch

W, H = 7.4, 11.6                     # inci
fig = plt.figure(figsize=(W, H), dpi=300)
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, W); ax.set_ylim(0, H); ax.axis('off')
FS, FSS = 8.6, 7.6
LW = 0.9
X0, X1 = 0.15, W - 0.15              # tepi bingkai
LANE = 0.42                          # lebar kolom label tahap
CX = (X0 + LANE + X1) / 2            # sumbu tengah isi

def kotak(x, y, w, h, teks, fs=FS, tebal=False):
    ax.add_patch(Rectangle((x - w / 2, y - h / 2), w, h, fill=False, lw=LW))
    ax.text(x, y, teks, ha='center', va='center', fontsize=fs, fontweight='bold' if tebal else 'normal', linespacing=1.25)

def grup(y_atas, y_bawah, judul, w=5.9):
    ax.add_patch(Rectangle((CX - w / 2, y_bawah), w, y_atas - y_bawah, fill=False, lw=LW))
    ax.text(CX, y_atas - 0.2, judul, ha='center', va='center', fontsize=FS)

def panah(y1, y2, x=None):
    x = CX if x is None else x
    ax.add_patch(FancyArrowPatch((x, y1), (x, y2), arrowstyle='-|>', mutation_scale=9, lw=LW, color='black', shrinkA=0, shrinkB=0))

# bingkai dan judul
TOP = H - 0.15
ax.add_patch(Rectangle((X0, 0.15), X1 - X0, TOP - 0.15, fill=False, lw=LW))
ax.plot([X0, X1], [TOP - 0.32, TOP - 0.32], color='black', lw=LW)
ax.text(W / 2, TOP - 0.16, 'Alur Penelitian', ha='center', va='center', fontsize=9.5, fontweight='bold')
ax.plot([X0 + LANE] * 2, [0.15, TOP - 0.32], color='black', lw=LW)

def jalur(y_atas, y_bawah, label):
    ax.text(X0 + LANE / 2, (y_atas + y_bawah) / 2, label, rotation=90, ha='center', va='center', fontsize=8.6, fontweight='bold')
    if y_bawah > 0.16:
        ax.plot([X0, X1], [y_bawah, y_bawah], color='black', lw=LW)

# ---------------- Tahap 1: Persiapan ----------------
t1a, t1b = TOP - 0.32, 8.75
jalur(t1a, t1b, 'Persiapan Penelitian')
y = t1a - 0.42; kotak(CX, y, 3.6, 0.42, 'Studi Literatur\n(An et al.; cutting plane; PDLP; pemangkasan kendala; toleransi)', fs=FSS)
panah(y - 0.21, y - 0.45)
g_top = y - 0.45; g_bot = g_top - 1.08
grup(g_top, g_bot, 'Pengumpulan Data BPS Tahun 2024 (514 Kabupaten/Kota, 38 Provinsi)')
yy = g_top - 0.66
kotak(CX - 1.95, yy, 1.75, 0.5, 'PDRB ADHK\n(tabel BPS pusat)', fs=FSS)
kotak(CX, yy, 1.75, 0.5, 'IPM\n(tabel BPS pusat)', fs=FSS)
kotak(CX + 1.95, yy, 1.75, 0.5, 'TPAK Agustus\n(BPS 38 provinsi)', fs=FSS)
panah(g_bot, t1b - 0.18)

# ---------------- Tahap 2: Praproses dan perumusan ----------------
t2a, t2b = t1b, 6.55
jalur(t2a, t2b, 'Praproses dan Perumusan LP')
g_top = t2a - 0.18; g_bot = g_top - 1.08
grup(g_top, g_bot, 'Praproses Data')
yy = g_top - 0.66
kotak(CX - 1.95, yy, 1.75, 0.5, 'Normalisasi skor-z', fs=FSS)
kotak(CX, yy, 1.75, 0.5, 'Jarak Euclidean\n(131.841 pasangan)', fs=FSS)
kotak(CX + 1.95, yy, 1.75, 0.5, 'Graf bertanda 2 lapisan\n(ambang P25 dan P75)', fs=FSS)
panah(g_bot, g_bot - 0.24)
y = g_bot - 0.24 - 0.27
kotak(CX, y, 4.3, 0.54, 'Perumusan LP-(*) An et al. (2025)\n263.682 variabel, 135.005.184 kendala segitiga', fs=FSS)
panah(y - 0.27, t2b - 0.18)

# ---------------- Tahap 3: Eksperimen ----------------
t3a, t3b = t2b, 3.05
jalur(t3a, t3b, 'Penyelesaian LP dan Pembulatan')
g_top = t3a - 0.18; g_bot = g_top - 1.62
grup(g_top, g_bot, 'Penyelesaian LP: Cutting Plane + PDLP di GPU A100 (FP64)')
yy = g_top - 0.86
kotak(CX - 1.95, yy, 1.75, 0.92, 'Baseline\nAn et al. (2025)\ntoleransi 10⁻⁶,\nkendala disimpan', fs=FSS)
kotak(CX, yy, 1.75, 0.92, 'UCP-CR\npemangkasan kendala\ntidak aktif\n+ penguncian', fs=FSS)
kotak(CX + 1.95, yy, 1.75, 0.92, 'UCP-TR\ntoleransi dua tahap\n10⁻⁴ lalu 10⁻⁶', fs=FSS)
ax.text(CX, g_bot + 0.12, 'tiap putaran: selesaikan LP → separasi kendala segitiga dilanggar > 10⁻⁵ → tambahkan; berhenti bila tidak ada kendala baru',
        ha='center', va='center', fontsize=6.6, style='italic')
panah(g_bot, g_bot - 0.24)
y = g_bot - 0.24 - 0.21
kotak(CX, y, 4.3, 0.42, 'Pemeriksaan pelanggaran seluruh kendala di CPU (FP64)', fs=FSS)
panah(y - 0.21, y - 0.45)
y2 = y - 0.45 - 0.27
kotak(CX, y2, 4.3, 0.54, 'Pembulatan An et al. (2025): pre-clustering (Algoritma 2)\n→ clustering hierarkis (Algoritma 1) → partisi bersarang 2 lapisan', fs=FSS)
panah(y2 - 0.27, t3b - 0.18)

# ---------------- Tahap 4: Evaluasi dan kesimpulan ----------------
t4a, t4b = t3b, 0.15
jalur(t4a, t4b, 'Evaluasi dan Kesimpulan')
g_top = t4a - 0.18; g_bot = g_top - 1.18
grup(g_top, g_bot, 'Evaluasi')
yy = g_top - 0.72
kotak(CX - 1.95, yy, 1.75, 0.62, 'Efisiensi\nwaktu LP, putaran,\nkendala aktif (RQ2, RQ3)', fs=FSS)
kotak(CX, yy, 1.75, 0.62, 'Validitas\nobjektif LP, pelanggaran,\nCC, Silhouette, Dunn, Conn.', fs=FSS)
kotak(CX + 1.95, yy, 1.75, 0.62, 'Kualitas terhadap teori\nrasio ρ = B / LP*\nvs 25,7846 (RQ1)', fs=FSS)
panah(g_bot, g_bot - 0.24)
y = g_bot - 0.24 - 0.21
kotak(CX, y, 4.6, 0.46, 'Uji skalabilitas\nUCP-CR: 9 instans (n = 35–514); UCP-TR: 4 instans (n = 35–514)', fs=FSS)
panah(y - 0.23, y - 0.45)
y2 = y - 0.45 - 0.21
kotak(CX, y2, 4.3, 0.42, 'Kesimpulan (jawaban RQ1–RQ3) dan Saran', fs=FSS)

import os; out = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'gambar_alur_penelitian.png')
fig.savefig(out, dpi=300, facecolor='white')
print(out)

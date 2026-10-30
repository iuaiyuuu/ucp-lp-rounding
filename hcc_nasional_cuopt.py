"""
LP-Rounding HCC (An et al. 2025) dengan LP diselesaikan cutting plane + PDLP di GPU (NVIDIA cuOpt).

- Setiap putaran LP aktif diselesaikan dengan cuOpt (default PDLP di GPU), titik awal dari solusi primal sebelumnya.
- Pemisahan kendala segitiga (cari w paling melanggar untuk tiap pasangan) dijalankan di GPU dengan cupy.
- Berhenti jika tidak ada pelanggaran > SEP_TOL; pelanggaran akhir dicek ulang di CPU (float64).
- Pembulatan An et al. (Algoritma 1 dan 2) ada di hcc_rounding_an2025.py.
- Metrik: CC pada graf ambang rata-rata, P25, dan P75; Silhouette, Dunn Index, Connectivity.
Varian penelitian: baseline (tanpa opsi tambahan), UCP-CR (--row-elim), UCP-TR (--tol-awal 1e-4).
Hasil di tesis selalu memakai --monoton an2025 --pembulatan an2025; pilihan 'paper' adalah versi lama dan
membutuhkan hcc_jateng_v2.py yang tidak disertakan di repositori ini.

Pemakaian (Python dengan cuOpt dan CuPy):
  python hcc_nasional_cuopt.py <csv> <kolom,...> <prefix> --monoton an2025 --pembulatan an2025 [opsi]
Opsi: --metode pdlp|barrier|dualsimplex|concurrent  --tol 1e-7  --sep-tol 1e-5  --per-pasangan 1
      --max-putaran 200  --max-iter-pc 5000
      --presisi default|double|mixed|single     mode presisi PDLP cuOpt
      --row-elim [--row-elim-tol 1e-6]          buang kendala segitiga tak aktif sebelum solve ulang (Grötschel &
                                                Wakabayashi 1989, "Row elimination")
      --maxcut K                                batasi kendala baru per putaran ke K yang paling melanggar (GW89)
      --batas-waktu DETIK                       berhenti rapi saat waktu LP habis (hasil tetap disimpan)
      --checkpoint                              simpan <prefix>_ckpt.npz tiap putaran;  --resume <npz> melanjutkan
      --subsampel N [--seed S]                  ambil N baris acak dari data (benchmark skala)
"""
import sys, io, os, time, json, argparse
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)

import numpy as np
import pandas as pd
import cupy as cp
from itertools import combinations
from scipy.sparse import csr_matrix
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score
from scipy.cluster.hierarchy import linkage, fcluster
from scipy.spatial.distance import pdist, squareform
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hcc_rounding_an2025 import hierarchical
from cuopt.linear_programming import DataModel, Solve, SolverSettings, SolverMethod
from cuopt.linear_programming.solver.solver_parameters import (
    CUOPT_METHOD, CUOPT_TIME_LIMIT, CUOPT_LOG_TO_CONSOLE,
    CUOPT_ABSOLUTE_PRIMAL_TOLERANCE, CUOPT_ABSOLUTE_DUAL_TOLERANCE, CUOPT_ABSOLUTE_GAP_TOLERANCE,
    CUOPT_RELATIVE_PRIMAL_TOLERANCE, CUOPT_RELATIVE_DUAL_TOLERANCE, CUOPT_RELATIVE_GAP_TOLERANCE,
    CUOPT_PDLP_PRECISION)

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

ap = argparse.ArgumentParser()
ap.add_argument('csv'); ap.add_argument('cols'); ap.add_argument('prefix')
ap.add_argument('--metode', default='pdlp', choices=['pdlp', 'barrier', 'dualsimplex', 'concurrent'])
ap.add_argument('--tol', type=float, default=1e-7)
ap.add_argument('--sep-tol', type=float, default=1e-5)
ap.add_argument('--per-pasangan', type=int, default=1, help='jumlah w paling melanggar per pasangan per putaran')
ap.add_argument('--max-putaran', type=int, default=200)
ap.add_argument('--max-iter-pc', type=int, default=5000)
ap.add_argument('--monoton', default='paper', choices=['paper', 'an2025'],
                help="paper: x_halus <= x_kasar (hcc_jateng_v2.py baris 243); "
                     "an2025: x_kasar <= x_halus (An et al. 2025, Gambar 1, non-increasing bottom-up)")
ap.add_argument('--pembulatan', default='paper', choices=['paper', 'an2025'],
                help="paper: pre_cluster/hcc_algorithm1 verbatim dari hcc_jateng_v2.py; "
                     "an2025: hcc_rounding_an2025.py (Algoritma 1-2 sesuai teks An et al.)")
ap.add_argument('--presisi', default='default', choices=['default', 'double', 'mixed', 'single'])
ap.add_argument('--row-elim', action='store_true')
ap.add_argument('--row-elim-tol', type=float, default=1e-6, help='kendala dibuang jika x_a - x_b - x_c < -tol')
ap.add_argument('--maxcut', type=int, default=0, help='0 = tanpa batas')
ap.add_argument('--batas-waktu', type=float, default=0, help='detik untuk tahap LP; 0 = tanpa batas')
ap.add_argument('--tol-awal', type=float, default=0,
                help='varian E: toleransi PDLP longgar sampai tidak ada kendala baru, lalu --tol; 0 = tidak dipakai')
ap.add_argument('--checkpoint', action='store_true')
ap.add_argument('--resume', default='')
ap.add_argument('--subsampel', type=int, default=0)
ap.add_argument('--seed', type=int, default=0)
args = ap.parse_args()
cols = args.cols.split(',')
METHOD = {'pdlp': SolverMethod.PDLP, 'barrier': SolverMethod.Barrier,
          'dualsimplex': SolverMethod.DualSimplex, 'concurrent': SolverMethod.Concurrent}[args.metode]
PRESISI = {'default': -1, 'single': 0, 'double': 1, 'mixed': 2}[args.presisi]   # constants.h cuOpt

# ---------------------------------------------------------------- data
df = pd.read_csv(args.csv)
if args.subsampel:
    df = df.sample(n=args.subsampel, random_state=args.seed).reset_index(drop=True)
X = StandardScaler().fit_transform(df[cols].values)
n = len(X)
D = squareform(pdist(X))
iu, ju = np.triu_indices(n, 1)
P = len(iu)
d = D[iu, ju]
thetas = [np.percentile(d, 25), np.percentile(d, 75)]   # lapisan halus, kasar
theta_eval = d.mean()                                    # graf evaluasi
L = len(thetas)
print(f"n={n} | variabel={cols} | pasangan={P} | theta P25={thetas[0]:.4f} P75={thetas[1]:.4f} "
      f"mean={theta_eval:.4f} | metode={args.metode} tol={args.tol} sep_tol={args.sep_tol} "
      f"per_pasangan={args.per_pasangan} monoton={args.monoton} pembulatan={args.pembulatan} "
      f"presisi={args.presisi} row_elim={args.row_elim} maxcut={args.maxcut} batas_waktu={args.batas_waktu} "
      f"subsampel={args.subsampel} seed={args.seed}")

# ---------------------------------------------------------------- LP (lazy, cuOpt)
pid = np.full((n, n), -1, dtype=np.int64)
pid[iu, ju] = np.arange(P)
pid[ju, iu] = np.arange(P)

c = np.concatenate([np.where(d < th, 1.0, -1.0) for th in thetas])
const = float(sum(int((d >= th).sum()) for th in thetas))
nv = L * P

if args.monoton == 'paper':
    mono = np.stack([np.arange(P), P + np.arange(P)], 1)   # x_halus - x_kasar <= 0
else:
    mono = np.stack([P + np.arange(P), np.arange(P)], 1)   # x_kasar - x_halus <= 0
tri = np.zeros((0, 3), dtype=np.int64)                 # x_a - x_b - x_c <= 0

def build(x0):
    m = P + len(tri)
    idx = np.concatenate([mono.ravel(), tri.ravel()]).astype(np.int32)
    val = np.concatenate([np.tile([1.0, -1.0], P), np.tile([1.0, -1.0, -1.0], len(tri))])
    indptr = np.concatenate([np.arange(0, 2 * P + 1, 2), 2 * P + 3 * np.arange(1, len(tri) + 1)]).astype(np.int32)
    dm = DataModel()
    dm.set_csr_constraint_matrix(val, idx, indptr)
    dm.set_constraint_lower_bounds(np.full(m, -np.inf))
    dm.set_constraint_upper_bounds(np.zeros(m))
    dm.set_objective_coefficients(c)
    dm.set_variable_lower_bounds(np.zeros(nv))
    dm.set_variable_upper_bounds(np.ones(nv))
    if x0 is not None and METHOD == SolverMethod.PDLP:
        dm.set_initial_primal_solution(x0)
    return dm

settings = SolverSettings()
settings.set_parameter(CUOPT_METHOD, METHOD)
settings.set_parameter(CUOPT_TIME_LIMIT, 3600)
settings.set_parameter(CUOPT_LOG_TO_CONSOLE, False)
if PRESISI != -1:
    settings.set_parameter(CUOPT_PDLP_PRECISION, PRESISI)
TOL_PRM = (CUOPT_ABSOLUTE_PRIMAL_TOLERANCE, CUOPT_ABSOLUTE_DUAL_TOLERANCE, CUOPT_ABSOLUTE_GAP_TOLERANCE,
           CUOPT_RELATIVE_PRIMAL_TOLERANCE, CUOPT_RELATIVE_DUAL_TOLERANCE, CUOPT_RELATIVE_GAP_TOLERANCE)

def set_tol(t):
    for prm in TOL_PRM:
        settings.set_parameter(prm, t)

tol_now = args.tol_awal if args.tol_awal else args.tol   # varian E: mulai longgar
set_tol(tol_now)

iu_g, ju_g = cp.asarray(iu), cp.asarray(ju)
pid_g = cp.asarray(pid)

def separate_gpu(xl, k_per, tol):
    """Untuk tiap pasangan (u<v), ambil k_per titik w dengan pelanggaran x_uv - x_uw - x_wv terbesar (> tol)."""
    Xm = cp.zeros((n, n))
    Xm[iu_g, ju_g] = cp.asarray(xl)
    Xm[ju_g, iu_g] = Xm[iu_g, ju_g]
    best = cp.full((P, k_per), -cp.inf)
    arg = cp.full((P, k_per), -1, dtype=cp.int64)
    B = 32
    for w0 in range(0, n, B):
        ws = cp.arange(w0, min(w0 + B, n))
        # V[p, j] = x_uv - x_u,w - x_w,v untuk pasangan p=(u,v), w = ws[j]
        V = Xm[iu_g, ju_g][:, None] - Xm[iu_g[:, None], ws[None, :]] - Xm[ws[None, :], ju_g[:, None]]
        V[(ws[None, :] == iu_g[:, None]) | (ws[None, :] == ju_g[:, None])] = -cp.inf
        allv = cp.concatenate([best, V], 1)
        alla = cp.concatenate([arg, cp.broadcast_to(ws[None, :], V.shape)], 1)
        top = cp.argsort(-allv, axis=1)[:, :k_per]
        best = cp.take_along_axis(allv, top, 1)
        arg = cp.take_along_axis(alla, top, 1)
    sel = best > tol
    p_idx = cp.nonzero(sel)[0]
    w = arg[sel]
    u, v = iu_g[p_idx], ju_g[p_idx]
    rows = cp.stack([pid_g[u, v], pid_g[u, w], pid_g[w, v]], 1)
    return cp.asnumpy(rows), cp.asnumpy(best[sel]), float(best[:, 0].max())

def max_violation_cpu(x):
    worst = 0.0
    for l in range(L):
        Xm = np.zeros((n, n)); Xm[iu, ju] = x[l * P:(l + 1) * P]; Xm[ju, iu] = Xm[iu, ju]
        for w in range(n):
            V = Xm - Xm[:, w][:, None] - Xm[w, :][None, :]
            V[w, :] = -np.inf; V[:, w] = -np.inf
            worst = max(worst, V.max())
    mono_v = (x[:P] - x[P:]).max() if args.monoton == 'paper' else (x[P:] - x[:P]).max()
    return worst, max(0.0, mono_v), max(0.0, -x.min(), x.max() - 1)

CKPT = os.path.join(HERE, f'{args.prefix}_ckpt.npz')

def save_checkpoint():
    tmp = CKPT + '.tmp.npz'                          # tulis atomik: file lama tetap utuh bila proses mati di tengah
    np.savez(tmp, tri=tri, x=x if x is not None else np.zeros(0), rounds=rounds, t_offset=time.perf_counter() - t0,
             log=json.dumps(log_rows), dropped_keys=dropped_keys, dropped_total=dropped_total)
    os.replace(tmp, CKPT)

log_rows = []
t0 = time.perf_counter()
x = None
rounds = 0
if args.resume:
    ck = np.load(args.resume)
    tri, x, rounds = ck['tri'], (ck['x'] if len(ck['x']) else None), int(ck['rounds'])
    log_rows = json.loads(str(ck['log']))
    t0 -= float(ck['t_offset'])
    print(f"Lanjut dari {args.resume}: putaran {rounds}, {len(tri)} kendala segitiga, {float(ck['t_offset']):.1f}s")
stop_reason = 'konvergen'
dropped_total = 0
obj = float('nan')
dropped_keys = np.zeros(0, dtype=np.int64)          # kendala yang pernah dibuang (row elimination)

def key(rows):
    """Kunci unik int64 untuk baris kendala (a, b, c); nv^3 < 2^63 untuk n <= 514."""
    return (rows[:, 0] * nv + rows[:, 1]) * nv + rows[:, 2]

if args.resume and 'dropped_keys' in ck:
    dropped_keys, dropped_total = ck['dropped_keys'], int(ck['dropped_total'])
while True:
    elapsed = time.perf_counter() - t0
    if args.batas_waktu and elapsed >= args.batas_waktu:
        stop_reason = 'batas waktu'
        break
    rounds += 1
    if args.batas_waktu:                              # solve tidak boleh melewati batas waktu
        settings.set_parameter(CUOPT_TIME_LIMIT, max(1.0, min(3600.0, args.batas_waktu - elapsed)))
    ts = time.perf_counter()
    sol = Solve(build(x), settings)
    t_solve = time.perf_counter() - ts
    x = np.clip(np.asarray(sol.get_primal_solution(), dtype=np.float64), 0, 1)
    status = sol.get_termination_status()
    obj = float(c @ x) + const
    ts = time.perf_counter()
    new, viol, worst = [], [], 0.0
    for l in range(L):
        r, vl, wl = separate_gpu(x[l * P:(l + 1) * P], args.per_pasangan, args.sep_tol)
        worst = max(worst, wl)
        if len(r):
            new.append(r + l * P)
            viol.append(vl)
    t_sep = time.perf_counter() - ts
    added = sum(len(r) for r in new)
    if added and args.maxcut and added > args.maxcut:   # ambil yang paling melanggar (GW89)
        allr, allv = np.concatenate(new), np.concatenate(viol)
        new = [allr[np.argsort(-allv)[:args.maxcut]]]
    n_add = sum(len(r) for r in new)
    dropped = 0
    if args.row_elim and len(tri):                      # buang kendala tak aktif di solusi sekarang (GW89)
        slack = x[tri[:, 0]] - x[tri[:, 1]] - x[tri[:, 2]]
        # Modifikasi anti-siklus: tiap kendala hanya boleh dibuang sekali. Dengan PDLP (solusi tidak eksak),
        # row elimination murni berputar: kendala yang dibuang dilanggar lagi sebesar ~1e-4 lalu dimasukkan
        # kembali (uji Jateng 2026-10-27). Kendala yang pernah dibuang tidak dibuang lagi -> pasti berhenti.
        keep = (slack >= -args.row_elim_tol) | np.isin(key(tri), dropped_keys)
        dropped = int((~keep).sum())
    print(f"  putaran {rounds:3d}: status={status} obj LP={obj:.4f} | langgar maks={worst:.2e} | "
          f"segitiga baru={added}" + (f" (dipakai {n_add})" if n_add != added else '') +
          f" | dibuang={dropped} | total segitiga={len(tri)} | solve {t_solve:.1f}s sep {t_sep:.1f}s | "
          f"{time.perf_counter() - t0:.1f}s", flush=True)
    log_rows.append({'putaran': rounds, 'status': str(status), 'obj': obj, 'langgar_maks': worst,
                     'baru': added, 'dipakai': n_add, 'dibuang': dropped, 'total_segitiga': len(tri),
                     't_solve': t_solve, 't_sep': t_sep, 't_kumulatif': time.perf_counter() - t0})
    pd.DataFrame(log_rows).to_csv(os.path.join(HERE, f'{args.prefix}_log_lp.csv'), index=False)
    if not added and tol_now != args.tol:          # varian E: tidak ada kendala baru pada tol longgar -> ketatkan
        tol_now = args.tol
        set_tol(tol_now)
        print(f"  toleransi diketatkan ke {tol_now:g} pada putaran {rounds}", flush=True)
        continue
    if not added:
        break
    if rounds >= args.max_putaran:
        stop_reason = 'batas putaran'
        break
    if dropped:
        dropped_keys = np.union1d(dropped_keys, key(tri[~keep]))
        tri = tri[keep]
        dropped_total += dropped
    tri = np.unique(np.concatenate([tri] + new), axis=0)
    if args.checkpoint:
        save_checkpoint()
t_lp = time.perf_counter() - t0
if x is None:
    sys.exit('Tidak ada solusi LP (batas waktu habis sebelum solve pertama).')
if args.checkpoint:
    save_checkpoint()
np.save(os.path.join(HERE, f'{args.prefix}_x_lp.npy'), x)
full_tri = L * 3 * (n * (n - 1) * (n - 2) // 6)
tri_v, mono_v, bnd_v = max_violation_cpu(x)
converged = stop_reason == 'konvergen'
print(f"LP {'selesai' if converged else 'BERHENTI (' + stop_reason + ')'}: obj={obj:.4f} | {rounds} putaran | "
      f"kendala segitiga aktif={len(tri)} dari {full_tri} ({100 * len(tri) / full_tri:.3f}%) | "
      f"dibuang total={dropped_total} | waktu={t_lp:.1f}s")
if not converged:
    print("PERINGATAN: LP belum konvergen; objektif bukan optimum LP penuh dan jaminan An et al. tidak berlaku "
          "untuk hasil pembulatan di bawah.")
print(f"Cek CPU: langgar segitiga maks={tri_v:.2e} | monoton={mono_v:.2e} | batas={bnd_v:.2e}")

# ---------------------------------------------------------------- rounding (verbatim)
ns = {'np': np, 'combinations': combinations, 'print': lambda *a, **k: None}
if args.pembulatan == 'paper':   # versi publik: kode paper lama hanya dimuat untuk --pembulatan paper (tidak disertakan)
    src = open(os.path.join(ROOT, 'hcc_jateng_v2.py'), encoding='utf-8').read().splitlines()
    exec('\n'.join(src[284:388]), ns)   # baris 285-388: ALPHA, pre_cluster, hcc_algorithm1

Ds = []
for l in range(L):
    M = np.zeros((n, n))
    M[iu, ju] = np.clip(x[l * P:(l + 1) * P], 0, 1)
    M[ju, iu] = M[iu, ju]
    Ds.append(M)

t0 = time.perf_counter()
if args.pembulatan == 'paper':
    pre, pc_unfinished = [], []
    for M in Ds:
        parts = ns['pre_cluster'](M, n, max_iter=args.max_iter_pc)
        unfinished = sum(1 for cl in parts if len(cl) > 1 and
                         M[np.ix_(sorted(cl), sorted(cl))].max() >= 1 / 3)
        pre.append(parts)
        pc_unfinished.append(unfinished)
    all_labels = ns['hcc_algorithm1'](Ds, pre, n)
    n_pre = [len(p) for p in pre]
else:
    all_labels, n_pre = hierarchical(Ds)
    pc_unfinished = [0] * L
labels_hcc = np.asarray(all_labels[-1])
t_round = time.perf_counter() - t0
print(f"Pembulatan ({args.pembulatan}): {t_round:.1f}s | pre-cluster per lapisan={n_pre} | "
      f"k per lapisan={[len(np.unique(l)) for l in all_labels]} | "
      f"cluster belum tuntas (diam>=1/3) per lapisan={pc_unfinished}")

# ---------------------------------------------------------------- metrik
graf = {'mean': d < theta_eval, 'P25': d < thetas[0], 'P75': d < thetas[1]}

def cc_dis(labels, pos):
    same = labels[iu] == labels[ju]
    return int((pos & ~same).sum() + (~pos & same).sum())

def dunn(labels):
    labs = np.unique(labels)
    max_intra = max((D[np.ix_(labels == a, labels == a)].max() for a in labs), default=0)
    min_inter = min(D[np.ix_(labels == a, labels == b)].min() for a, b in combinations(labs, 2))
    return min_inter / max_intra if max_intra > 0 else 0.0

order = np.argsort(D, axis=1)[:, 1:11]
def connectivity(labels):
    diff = labels[order] != labels[:, None]
    return float((diff / np.arange(1, 11)).sum())

def evaluate(name, labels, runtime_s):
    labs, cnt = np.unique(labels, return_counts=True)
    k = len(labs)
    r = {'metode': name, 'k': k,
         'silhouette': silhouette_score(X, labels) if 1 < k < n else float('nan'),
         'dunn': dunn(labels) if k > 1 else float('nan'),
         'connectivity': connectivity(labels)}
    for g, pos in graf.items():
        r[f'cc_{g}'] = cc_dis(labels, pos)
        r[f'cc_{g}_pct'] = 100 * r[f'cc_{g}'] / P
    r['runtime_s'] = runtime_s
    r['ukuran'] = sorted(cnt.tolist(), reverse=True)
    print(f"  {name:28s} k={k:3d} Sil={r['silhouette']:.4f} Dunn={r['dunn']:.4f} Conn={r['connectivity']:.2f} "
          f"CC mean={r['cc_mean']} ({r['cc_mean_pct']:.1f}%) P25={r['cc_P25']} P75={r['cc_P75']} "
          f"t={runtime_s:.2f}s ukuran={r['ukuran'][:8]}{'...' if k > 8 else ''}")
    return r

print(f"\nEvaluasi (graf mean |E+|={int(graf['mean'].sum())}, P25 |E+|={int(graf['P25'].sum())}, "
      f"P75 |E+|={int(graf['P75'].sum())}, dari {P} pasangan)")
res = [evaluate('LP-Rounding HCC (lapisan 1)', np.asarray(all_labels[0]), t_lp + t_round),
       evaluate('LP-Rounding HCC', labels_hcc, t_lp + t_round)]

t0 = time.perf_counter()
Z = linkage(X, method='average', metric='euclidean')
t_hc = time.perf_counter() - t0
k_hcc = sorted({r['k'] for r in res})
for kk in sorted(set(list(range(2, 11)) + k_hcc)):
    if kk >= n:
        continue
    res.append(evaluate(f'HC Average Linkage k={kk}', fcluster(Z, t=kk, criterion='maxclust'), t_hc))

pd.DataFrame(res).to_csv(os.path.join(HERE, f'{args.prefix}_hasil.csv'), index=False)
pd.DataFrame({'Kabupaten_Kota': df['Kabupaten_Kota'],
              **({'Provinsi': df['Provinsi']} if 'Provinsi' in df else {}),
              'cluster_lapisan1': np.asarray(all_labels[0]), 'cluster_hcc': labels_hcc}
             ).to_csv(os.path.join(HERE, f'{args.prefix}_label_hcc.csv'), index=False)
json.dump({'n': n, 'cols': cols, 'P': int(P), 'thetas': thetas, 'theta_eval': theta_eval,
           'metode': args.metode, 'tol': args.tol, 'sep_tol': args.sep_tol, 'per_pasangan': args.per_pasangan, 'monoton': args.monoton, 'pembulatan': args.pembulatan, 'presisi': args.presisi, 'row_elim': args.row_elim, 'row_elim_tol': args.row_elim_tol, 'maxcut': args.maxcut, 'batas_waktu': args.batas_waktu, 'subsampel': args.subsampel, 'seed': args.seed, 'stop_reason': stop_reason, 'tol_awal': args.tol_awal, 'dropped_total': dropped_total,
           'lp_obj': obj, 'lp_converged': converged, 'lp_rounds': rounds, 'lp_active_tri': int(len(tri)),
           'lp_full_tri': int(full_tri), 'viol_tri': tri_v, 'viol_mono': mono_v, 'viol_bound': bnd_v,
           't_lp': t_lp, 't_round': t_round, 't_hc': t_hc, 'max_iter_pc': args.max_iter_pc,
           'unfinished_precluster': pc_unfinished},
          open(os.path.join(HERE, f'{args.prefix}_ringkasan.json'), 'w'), indent=1)
print(f"\nTersimpan: {args.prefix}_hasil.csv, _label_hcc.csv, _ringkasan.json, _log_lp.csv, _x_lp.npy")

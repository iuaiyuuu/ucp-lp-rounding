"""
Uji hcc_rounding_an2025.py dan arah kendala monoton LP.

1. Instans acak kecil (n=6, 2 lapisan): OPT dihitung brute force atas semua pasangan partisi bersarang.
   - LP An et al. (x_kasar <= x_halus) harus <= OPT (relaksasi sah).
   - LP versi kode paper (x_halus <= x_kasar) dicatat berapa kali > OPT (bukan relaksasi yang sah).
   - Hasil pembulatan: partisi sah, bersarang (lapisan bawah subdivisi lapisan atas), biaya <= 25,7846 x LP.
2. Jateng 3 variabel (data paper): LP penuh An et al., pembulatan, cek sifat yang sama.

Pemakaian: ~/.venvs/hcnew-cuopt/bin/python test_rounding_an2025.py
"""
import os, sys, itertools
import numpy as np
import pandas as pd
import highspy
from scipy.spatial.distance import pdist, squareform
from sklearn.preprocessing import StandardScaler

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from hcc_rounding_an2025 import hierarchical, pre_clustering

BOUND = 25.7846


def lp(D, thetas, arah):
    """LP-(*) penuh dengan HiGHS. arah='an2025': x[t+1] <= x[t]; arah='paper': x[t] <= x[t+1]."""
    n = len(D)
    iu, ju = np.triu_indices(n, 1)
    P = len(iu)
    pid = np.full((n, n), -1); pid[iu, ju] = np.arange(P); pid[ju, iu] = np.arange(P)
    d = D[iu, ju]
    L = len(thetas)
    c = np.concatenate([np.where(d < th, 1.0, -1.0) for th in thetas])
    const = float(sum((d >= th).sum() for th in thetas))
    h = highspy.Highs(); h.setOptionValue('output_flag', False)
    h.addVars(L * P, np.zeros(L * P), np.ones(L * P))
    h.changeColsCost(L * P, np.arange(L * P, dtype=np.int32), c)
    rows = []
    for l in range(L):
        for u, v, w in itertools.permutations(range(n), 3):
            if u < v:
                rows.append(([l * P + pid[u, v], l * P + pid[u, w], l * P + pid[w, v]], [1, -1, -1]))
    for l in range(L - 1):
        for k in range(P):
            lo, hi = (l * P + k, (l + 1) * P + k)
            rows.append(([hi, lo], [1, -1]) if arah == 'an2025' else ([lo, hi], [1, -1]))
    for idx, val in rows:
        h.addRow(-highspy.kHighsInf, 0, len(idx), np.array(idx, dtype=np.int32), np.array(val, dtype=float))
    h.run()
    x = np.array(h.getSolution().col_value)
    obj = h.getInfo().objective_function_value + const
    Xs = []
    for l in range(L):
        M = np.zeros((n, n)); M[iu, ju] = np.clip(x[l * P:(l + 1) * P], 0, 1); M[ju, iu] = M[iu, ju]
        Xs.append(M)
    return obj, Xs


def cost(labels, D, thetas):
    n = len(D)
    iu, ju = np.triu_indices(n, 1)
    tot = 0
    for lab, th in zip(labels, thetas):
        pos = D[iu, ju] < th
        same = lab[iu] == lab[ju]
        tot += int((pos & ~same).sum() + (~pos & same).sum())
    return tot


def partitions(n):
    """Semua partisi {0..n-1} sebagai array label (restricted growth string)."""
    def rec(i, lab, m):
        if i == n:
            yield np.array(lab)
            return
        for b in range(m + 1):
            yield from rec(i + 1, lab + [b], max(m, b + 1))
    yield from rec(1, [0], 1)


def refines(fine, coarse):
    return all(len(set(coarse[fine == b])) == 1 for b in np.unique(fine))


def check_output(labels, Xs, n):
    for lab in labels:
        assert len(lab) == n and lab.min() >= 0
    for a, b in zip(labels, labels[1:]):
        assert refines(a, b), 'partisi lapisan bawah bukan subdivisi lapisan atas'
    for X in Xs:
        for Q in pre_clustering(X):
            assert len(Q) < 2 or X[np.ix_(Q, Q)].max() < 1 / 3, 'pre-cluster berdiameter >= 1/3'


# ---------------------------------------------------------------- 1. instans acak kecil
rng = np.random.default_rng(2026)
n = 6
parts = list(partitions(n))
nested = [(a, b) for a in parts for b in parts if refines(a, b)]
print(f'n={n}: {len(parts)} partisi, {len(nested)} pasangan bersarang')
paper_invalid, worst_ratio = 0, 0.0
N_INST = 40
for it in range(N_INST):
    X = rng.normal(size=(n, 2)) * rng.uniform(0.3, 3, size=2)
    D = squareform(pdist(X))
    d = D[np.triu_indices(n, 1)]
    thetas = [np.percentile(d, 25), np.percentile(d, 75)]
    opt = min(cost([a, b], D, thetas) for a, b in nested)
    lp_an, Xs = lp(D, thetas, 'an2025')
    lp_pa, _ = lp(D, thetas, 'paper')
    assert lp_an <= opt + 1e-6, f'LP An 2025 ({lp_an}) > OPT ({opt}): formulasi salah'
    paper_invalid += lp_pa > opt + 1e-6
    labels, _ = hierarchical(Xs)
    check_output(labels, Xs, n)
    c = cost(labels, D, thetas)
    assert c >= opt
    assert c <= BOUND * lp_an + 1e-6, f'biaya {c} > {BOUND} x LP {lp_an}'
    if lp_an > 0:
        worst_ratio = max(worst_ratio, c / lp_an)
print(f'{N_INST} instans: LP An 2025 <= OPT di semua instans | LP versi kode paper > OPT di '
      f'{paper_invalid}/{N_INST} instans | rasio biaya/LP terburuk = {worst_ratio:.3f} (batas {BOUND})')

# ---------------------------------------------------------------- 2. Jateng 3 variabel
df = pd.read_csv(os.path.join(HERE, 'data', 'dataset_benchmark_jateng_2022.csv'))
Xj = StandardScaler().fit_transform(df[['PDRB_ADHK', 'IPM', 'TPAK']].values)
D = squareform(pdist(Xj))
d = D[np.triu_indices(len(D), 1)]
thetas = [np.percentile(d, 25), np.percentile(d, 75)]
obj, Xs = lp(D, thetas, 'an2025')
labels, n_pre = hierarchical(Xs)
check_output(labels, Xs, len(D))
c = cost(labels, D, thetas)
print(f'Jateng 3 var: LP An 2025 = {obj:.4f} | pre-cluster {n_pre} | k per lapisan '
      f'{[len(np.unique(l)) for l in labels]} | biaya hierarkis = {c} (rasio {c / obj:.3f}) | sifat OK')
print('SEMUA UJI LULUS')

"""
Pembulatan LP untuk Hierarchical Correlation Clustering sesuai An et al. (2025), arXiv 2504.06700v1, Bagian 3.

Ditulis ulang dari teks paper (bukan dari hcc_jateng_v2.py) karena kode paper berbeda pada Kondisi (1) dan (2);
lihat TEMUAN_SESI_UBUNTU_2026-10-27.md Bagian 4. Masukan x[t] adalah matriks jarak LP n x n lapisan t
(lapisan 0 = bawah/halus), dengan x[t+1] <= x[t] (LP-(*), Gambar 1) dan diagonal nol.

- pre_clustering   : Algoritma 2 + One-Third-Refine-Cut (hlm. 8-9). Ball_<r(v,Q) memuat v sendiri (x_vv = 0).
- hierarchical     : Algoritma 1 (hlm. 7), Kondisi (1):
                     Δ+(P) ∩ Q ≠ ∅  dan  |Ball_<2/3(P∩Q, P \\ Q)| < α·|P∩Q|,  Δ+(P) = Δ(P) ∩ P, α = 0,3936.
"""
import numpy as np

ALPHA = 0.3936


def pre_clustering(x):
    """Algoritma 2. Mengembalikan daftar array indeks; tiap pre-cluster berdiameter < 1/3."""
    n = len(x)
    todo = [np.arange(n)]
    done = []
    while todo:
        Q = todo.pop()
        if len(Q) < 2:
            done.append(Q)
            continue
        sub = x[np.ix_(Q, Q)]
        ecc = sub.max(axis=1)
        if ecc.max() < 1 / 3:                       # diam(Q) < 1/3: selesai
            done.append(Q)
            continue
        i = int(np.argmax(ecc))                     # v dengan max_u x_uv >= 1/3 (dipilih eksentrisitas terbesar)
        dv = sub[i]                                 # dv[i] = x_vv = 0, jadi v termasuk di kedua bola
        b3 = dv < 1 / 3
        b2 = dv < 1 / 2
        if dv[b3].sum() >= b3.sum() / 3 - b2.sum() / 6 - 1 / 6:     # Kondisi (2): jadikan v singleton
            todo += [Q[[i]], Q[np.arange(len(Q)) != i]]
        else:                                       # potong bola Ball_<1/3(v, Q)
            todo += [Q[b3], Q[~b3]]
    return done


def hierarchical(xs, alpha=ALPHA):
    """Algoritma 1. xs: daftar matriks jarak per lapisan (bawah ke atas). Mengembalikan label per lapisan
    dan jumlah pre-cluster per lapisan."""
    n = len(xs[0])
    parts = [np.array([v]) for v in range(n)]       # P^(0)
    glue = [np.array([v]) for v in range(n)]        # Δ^(0)(P) = P
    labels, n_pre = [], []
    for x in xs:
        Qs = pre_clustering(x)
        n_pre.append(len(Qs))
        lab = np.empty(n, dtype=np.int64)
        for k, P in enumerate(parts):
            lab[P] = k
        in_core = np.zeros(n, dtype=bool)
        for P, G in zip(parts, glue):
            in_core[np.intersect1d(P, G)] = True     # Δ+(P) = Δ(P) ∩ P
        taken = {}
        new_parts, new_glue = [], []
        for qi, Q in enumerate(Qs):
            inQ = np.zeros(n, dtype=bool)
            inQ[Q] = True
            cand = []
            for k in np.unique(lab[Q]):
                P = parts[k]
                PQ = P[inQ[P]]
                if not in_core[PQ].any():           # Δ+(P) ∩ Q = ∅  (P∩Q ⊆ P, jadi cukup cek inti di P∩Q)
                    continue
                rest = P[~inQ[P]]                   # P \ Q
                ball = int((x[np.ix_(rest, PQ)].min(axis=1) < 2 / 3).sum()) if len(rest) else 0
                if ball < alpha * len(PQ):
                    cand.append(int(k))
            if cand:
                for k in cand:
                    assert k not in taken, 'Lemma 3 dilanggar: P menjadi kandidat untuk dua Q'
                    taken[k] = qi
                new_parts.append(np.concatenate([parts[k] for k in cand]))
                new_glue.append(Q)
        for k, P in enumerate(parts):
            if k not in taken:
                new_parts.append(P)
                new_glue.append(glue[k])
        parts, glue = new_parts, new_glue
        lab = np.empty(n, dtype=np.int64)
        for k, P in enumerate(parts):
            lab[P] = k
        labels.append(lab)
    return labels, n_pre

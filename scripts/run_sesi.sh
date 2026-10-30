#!/usr/bin/env bash
# (SERVER) Uji opsi, benchmark presisi, lalu ablasi A vs C LP nasional 2024; berhenti sendiri sebelum batas.
# Pemakaian: nohup bash run_sesi.sh <epoch_selesai_LP> > results/nasional/sesi.log 2>&1 &
#   <epoch_selesai_LP> = detik epoch saat tahap LP harus berhenti. Setelah itu tiap proses menyimpan hasil,
#   cek pelanggaran di CPU, pembulatan dan metrik (beberapa menit).
set -uo pipefail
END=$1
PY=${PY:-$HOME/venv/bin/python}   # di Hostinger (driver 580.196) pakai venv dengan cuopt-cu12:
                                  # cuopt-cu13 gagal "cudaErrorCallRequiresNewerDriver"
cd "$(dirname "$0")/.."
OUT=results/nasional
mkdir -p "$OUT"
J=data/dataset_benchmark_jateng_2022.csv
NAS=data/dataset_nasional_2024.csv
V=PDRB_ADHK,IPM,TPAK
AN="--monoton an2025 --pembulatan an2025"
sisa() { echo $(( END - $(date +%s) )); }
ringkas() { grep -E "LP selesai|BERHENTI|Cek CPU|LP-Rounding HCC  |Traceback|Error" "$1" | cut -c1-190; }
gpu_log() { while true; do nvidia-smi --query-gpu=timestamp,utilization.gpu,memory.used --format=csv,noheader >> "$OUT/gpu.csv"; sleep 60; done; }
gpu_log & GPULOG=$!

echo "== 1. uji opsi di Jateng $(date -u), sisa $(sisa)s"
$PY hcc_nasional_cuopt.py $J $V $OUT/u_jateng_dasar $AN > $OUT/u_jateng_dasar.log 2>&1; ringkas $OUT/u_jateng_dasar.log
$PY hcc_nasional_cuopt.py $J $V $OUT/u_jateng_rowelim $AN --row-elim > $OUT/u_jateng_rowelim.log 2>&1; ringkas $OUT/u_jateng_rowelim.log
$PY hcc_nasional_cuopt.py $J $V $OUT/u_jateng_ckpt $AN --checkpoint --max-putaran 4 > $OUT/u_jateng_ckpt1.log 2>&1
$PY hcc_nasional_cuopt.py $J $V $OUT/u_jateng_ckpt $AN --checkpoint --resume $OUT/u_jateng_ckpt_ckpt.npz > $OUT/u_jateng_ckpt2.log 2>&1
grep "Lanjut dari" $OUT/u_jateng_ckpt2.log; ringkas $OUT/u_jateng_ckpt2.log

echo "== 2. benchmark presisi n=200 $(date -u), sisa $(sisa)s"
for p in double mixed single; do
    $PY hcc_nasional_cuopt.py $NAS $V $OUT/b_n200_$p $AN --subsampel 200 --seed 0 --presisi $p --tol 1e-6 \
        --batas-waktu 240 > $OUT/b_n200_$p.log 2>&1
    echo "-- $p"; ringkas $OUT/b_n200_$p.log
done
# pilih mode: yang konvergen dengan pelanggaran <= 1e-4 dan waktu LP terkecil; jika tidak ada, double
PRES=$($PY - <<'EOF'
import json, os
best = ('double', float('inf'))
for p in ('double', 'mixed', 'single'):
    f = f'results/nasional/b_n200_{p}_ringkasan.json'
    if not os.path.exists(f):
        continue
    r = json.load(open(f))
    if r['lp_converged'] and r['viol_tri'] <= 1e-4 and r['viol_mono'] <= 1e-4 and r['t_lp'] < best[1]:
        best = (p, r['t_lp'])
print(best[0])
EOF
)
echo "== presisi terpilih: $PRES" | tee $OUT/presisi_terpilih.txt

echo "== 3. ablasi nasional A vs C $(date -u), sisa $(sisa)s"
S=$(( $(sisa) - 60 ))
if [ "$S" -gt 300 ]; then
    $PY hcc_nasional_cuopt.py $NAS $V $OUT/A_nasional2024 $AN --presisi $PRES --tol 1e-6 --checkpoint \
        --batas-waktu $S > $OUT/A_nasional2024.log 2>&1 &
    PA=$!
    $PY hcc_nasional_cuopt.py $NAS $V $OUT/C_nasional2024 $AN --presisi $PRES --tol 1e-6 --checkpoint --row-elim \
        --batas-waktu $S > $OUT/C_nasional2024.log 2>&1 &
    PC=$!
    wait $PA $PC
    ringkas $OUT/A_nasional2024.log; ringkas $OUT/C_nasional2024.log
fi
kill $GPULOG 2>/dev/null
echo "== sesi selesai $(date -u)" | tee $OUT/SELESAI

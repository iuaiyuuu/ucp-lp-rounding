#!/usr/bin/env bash
# (SERVER) Ablasi B (MAXCUT), D (row-elim + MAXCUT), E (toleransi bertingkat); satu proses CUDA bergantian.
# Pemakaian: nohup bash run_ablasi2.sh <epoch_selesai> &
END=$1
cd "$(dirname "$0")/.."
OUT=results/ablasi; mkdir -p $OUT
PY=${PY:-python}
AN="--monoton an2025 --pembulatan an2025 --presisi double --tol 1e-6"
declare -A OPT=( [B]="--maxcut 10000" [D]="--row-elim --maxcut 10000" [E]="--tol-awal 1e-4" )
log() { echo "$(date -u +%H:%M:%S) $*" >> $OUT/progres.log; }
ringkas() { grep -E 'LP selesai|BERHENTI|Traceback' $1 | cut -c1-150; }
# 0) uji E di Jateng (harus LP 142)
$PY hcc_nasional_cuopt.py data/dataset_benchmark_jateng_2022.csv PDRB_ADHK,IPM,TPAK $OUT/E_jateng2022 $AN ${OPT[E]} \
    --batas-waktu 300 > $OUT/E_jateng2022.log 2>&1 < /dev/null
log "uji E jateng2022: $(ringkas $OUT/E_jateng2022.log)"
# 1) Jawa dan Sumatera, 3 ulangan
for w in jawa sumatera; do for r in 1 2 3; do for v in B D E; do
    $PY hcc_nasional_cuopt.py data/wilayah_2024/$w.csv PDRB_ADHK,IPM,TPAK $OUT/${v}_${w}_r$r $AN ${OPT[$v]} \
        --batas-waktu 600 > $OUT/${v}_${w}_r$r.log 2>&1 < /dev/null
    log "$w r$r $v: $(ringkas $OUT/${v}_${w}_r$r.log)"
done; done; done
# 2) nasional, sekali per varian, sisa waktu dibagi tiga
for v in B D E; do
    case $v in B) k=3;; D) k=2;; E) k=1;; esac
    S=$(( (END - $(date +%s) - 120) / k ))
    [ "$S" -lt 120 ] && { log "nasional $v dilewati (sisa waktu $S s)"; continue; }
    $PY hcc_nasional_cuopt.py data/dataset_nasional_2024.csv PDRB_ADHK,IPM,TPAK $OUT/${v}_nasional2024 $AN ${OPT[$v]} \
        --checkpoint --batas-waktu $S > $OUT/${v}_nasional2024.log 2>&1 < /dev/null
    log "nasional $v (batas $S s): $(ringkas $OUT/${v}_nasional2024.log)"
done
log "== ablasi2 selesai"

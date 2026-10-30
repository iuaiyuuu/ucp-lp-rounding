#!/usr/bin/env bash
# (SERVER) A vs C pada instans kecil-menengah, 3 ulangan tiap instans, satu proses CUDA bergantian.
cd "$(dirname "$0")/.."
OUT=results/wilayah; mkdir -p $OUT
PY=${PY:-python}
AN="--monoton an2025 --pembulatan an2025 --presisi double --tol 1e-6 --batas-waktu 900"
declare -A CSV=( [jateng2022]=data/dataset_benchmark_jateng_2022.csv [jateng2024]=data/wilayah_2024/jateng.csv
  [bali_nusa_tenggara]=data/wilayah_2024/bali_nusa_tenggara.csv [kalimantan]=data/wilayah_2024/kalimantan.csv
  [maluku_papua]=data/wilayah_2024/maluku_papua.csv [sulawesi]=data/wilayah_2024/sulawesi.csv
  [jawa]=data/wilayah_2024/jawa.csv [sumatera]=data/wilayah_2024/sumatera.csv )
for w in jateng2022 jateng2024 bali_nusa_tenggara kalimantan maluku_papua sulawesi jawa sumatera; do
  for r in 1 2 3; do
    for v in A C; do
      opt=""; [ $v = C ] && opt="--row-elim"
      $PY hcc_nasional_cuopt.py ${CSV[$w]} PDRB_ADHK,IPM,TPAK $OUT/${v}_${w}_r$r $AN $opt > $OUT/${v}_${w}_r$r.log 2>&1 < /dev/null
      echo "$(date -u +%H:%M:%S) $w r$r $v: $(grep -E 'LP selesai|BERHENTI|Traceback' $OUT/${v}_${w}_r$r.log | cut -c1-140)" >> $OUT/progres.log
    done
  done
done
echo "== wilayah selesai $(date -u)" >> $OUT/progres.log

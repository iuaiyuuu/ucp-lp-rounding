#!/usr/bin/env bash
# (SERVER) Siapkan lingkungan di instance Hostinger (Ubuntu 24.04, GPU NVIDIA).
# Pemakaian: bash scripts/setup_server.sh
# Hasil: ~/venv dengan cuOpt; log di results/setup.log
set -uo pipefail
OUT="$(dirname "$0")/../results"
mkdir -p "$OUT"
exec > >(tee -a "$OUT/setup.log") 2>&1
echo "== mulai setup: $(date -u)"
nvidia-smi || { echo "GAGAL: nvidia-smi tidak tersedia"; exit 1; }
nvidia-smi --query-gpu=name,driver_version,memory.total,compute_cap --format=csv
DRV=$(nvidia-smi --query-gpu=driver_version --format=csv,noheader | head -1 | cut -d. -f1)
if [ "$DRV" -ge 580 ]; then CU=cu13; else CU=cu12; fi   # CUDA 13 butuh driver >= 580.65 (dokumentasi cuOpt)
echo "driver major=$DRV -> cuopt-$CU"
lscpu | grep -E "^CPU\(s\)|Model name"; free -g | head -2; df -h ~ | tail -1

if ! python3 -c "import ensurepip" 2>/dev/null || ! command -v rsync >/dev/null; then
    sudo apt-get update -qq && sudo apt-get install -y -qq python3-venv python3-pip rsync
fi
python3 -m venv ~/venv
~/venv/bin/pip install -q --upgrade pip
~/venv/bin/pip install -q --no-cache-dir "cuopt-$CU" scikit-learn highspy
~/venv/bin/python - <<'EOF'
import cuopt, cupy, numpy, pandas, sklearn, highspy
print('cuopt', cuopt.__version__, '| cupy', cupy.__version__, '| numpy', numpy.__version__, '| pandas', pandas.__version__)
print('GPU', cupy.cuda.runtime.getDeviceProperties(0)['name'].decode())
EOF
cd "$(dirname "$0")/.."
~/venv/bin/python test_rounding_an2025.py | tail -3
echo "== setup selesai: $(date -u)"

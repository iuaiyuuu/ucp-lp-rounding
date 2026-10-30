# UCP-CR dan UCP-TR: Efisiensi LP-Rounding *Hierarchical Correlation Clustering* pada 514 Kabupaten/Kota di Indonesia

**Bahasa Indonesia** | [English](README.en.md)

Repositori ini memuat dataset, kode, hasil eksperimen, dan gambar dari tesis *Peningkatan Efisiensi LP-Rounding Hierarchical Correlation Clustering Menggunakan Ultrametric Cutting Plane dengan Constraint Reduction dan Time Reduction pada 514 Kabupaten/Kota di Indonesia Tahun 2024*.

**Ringkasnya:** penelitian ini menerapkan algoritma clustering LP-Rounding An et al. (2025), yang dalam publikasinya hanya dianalisis secara teoretis, pada data nyata seluruh kabupaten/kota di Indonesia, lalu mengusulkan dua cara agar LP di dalam algoritma itu lebih kecil (UCP-CR) dan lebih cepat diselesaikan (UCP-TR) tanpa mengubah objektif LP.

**Perangkat keras:** satu GPU NVIDIA A100 80 GB PCIe (sewaan, Hostinger, Reading, Britania Raya) dengan kuota 4 inti CPU AMD EPYC 7713P dan RAM 8 GB. Rincian ada di bagian [Spesifikasi server](#spesifikasi-server).

## Latar belakang

Pembangunan kabupaten/kota di Indonesia tidak seragam, dan kondisi suatu daerah tidak dapat dilihat dari satu indikator saja. Penelitian ini memakai tiga indikator BPS tahun 2024, yaitu PDRB atas dasar harga konstan (PDRB ADHK), Indeks Pembangunan Manusia (IPM), dan Tingkat Partisipasi Angkatan Kerja (TPAK), untuk 514 kabupaten/kota.

Pengelompokan dilakukan dengan *hierarchical correlation clustering* (HCC). Setiap pasangan kabupaten/kota diberi label mirip (+) atau tidak mirip (−), lalu dicari kelompok bertingkat yang paling sedikit melanggar label tersebut. Hasilnya berupa dua lapisan kelompok: lapisan halus dan lapisan kasar, dengan setiap kelompok halus berada di dalam satu kelompok kasar.

An et al. (2025) membuktikan bahwa algoritma LP-Rounding untuk HCC menghasilkan biaya paling besar 25,7846 kali biaya solusi terbaik, tetapi penelitian itu murni teoretis. Hambatan utamanya adalah ukuran LP. Untuk 514 kabupaten/kota dan dua lapisan, LP memuat 263.682 variabel dan 135.005.184 kendala segitiga.

## Apa yang diteliti

Algoritma LP-Rounding An et al. (2025) terdiri atas dua tahap. Tahap pertama menyelesaikan relaksasi LP-(\*), dan tahap kedua membulatkan solusinya dengan *pre-clustering* (Algoritma 2) dan clustering hierarkis (Algoritma 1). An et al. (2025) tidak menetapkan cara menyelesaikan LP-(\*), dan di tahap inilah penelitian ini bekerja.

![Tahap LP-Rounding dan bagian yang dimodifikasi](figures/gambar_lp_rounding.png)

- **Baseline:** LP-Rounding An et al. (2025) pada dataset yang sama. LP-nya diselesaikan dengan cutting plane standar (Grötschel dan Wakabayashi, 1989) dan PDLP di GPU tanpa modifikasi.
- **UCP-CR** (*Ultrametric Cutting Plane with Constraint Reduction*): membuang kendala segitiga yang tidak aktif sebelum LP diselesaikan ulang, lalu mengunci kendala yang sudah dibuang sehingga setiap kendala paling banyak dibuang satu kali.
- **UCP-TR** (*Ultrametric Cutting Plane with Time Reduction*): menyelesaikan LP dengan toleransi 10⁻⁴ sampai tidak ada kendala baru, lalu menuntaskannya pada 10⁻⁶.

UCP-CR dan UCP-TR hanya mengubah tahap penyelesaian LP. Tahap pembulatan An et al. dipakai tanpa perubahan. Penelitian ini membahas efisiensi penyelesaian LP, bukan perbandingan mutu hasil clustering antaralgoritma.

Tiga pertanyaan penelitiannya:

1. Bagaimana LP-Rounding An et al. (2025) dapat diterapkan pada 514 kabupaten/kota, dan seberapa jauh biaya hasilnya dari batas teori?
2. Bisakah ukuran LP diperkecil tanpa mengubah objektif LP? (UCP-CR)
3. Bisakah LP diselesaikan lebih cepat tanpa mengubah objektif LP? (UCP-TR)

## Alur penelitian

![Alur penelitian](figures/gambar_alur_penelitian.png)

1. **Data:** PDRB ADHK, IPM, dan TPAK tahun 2024 untuk 514 kabupaten/kota dari BPS.
2. **Praproses:** ketiga variabel dinormalisasi dengan skor-z, lalu dihitung jarak Euclidean untuk 131.841 pasangan.
3. **Graf bertanda dua lapisan:** pasangan dengan jarak di bawah persentil ke-25 (θ₁ = 1,0204) diberi label + pada lapisan halus, dan di bawah persentil ke-75 (θ₂ = 2,4285) diberi label + pada lapisan kasar.
4. **Penyelesaian LP:** cutting plane dengan PDLP di GPU dalam tiga varian (baseline, UCP-CR, UCP-TR), lalu seluruh kendala diperiksa ulang di CPU dengan presisi ganda.
5. **Pembulatan:** algoritma An et al. (2025) tanpa perubahan.
6. **Evaluasi:** waktu dan ukuran LP, objektif LP, pelanggaran kendala, CC disagreements, Silhouette, Dunn Index, Connectivity, dan rasio biaya terhadap batas bawah LP. Pengaruh ukuran data diuji pada instans uji dari 35 sampai 514 kabupaten/kota.

## Cara kerja cutting plane

LP-(\*) tidak dimasukkan sekaligus ke solver. LP dimulai tanpa kendala segitiga, lalu setiap putaran mencari kendala segitiga yang dilanggar dan menambahkannya.

Contoh satu segitiga nyata dari data 2024 ditunjukkan di bawah. Pada lapisan halus, pasangan {u, v} dan {u, p} bertanda +, sedangkan {v, p} bertanda −. Pada putaran pertama solusinya (0; 0; 1), yang melanggar kendala x_vp ≤ x_uv + x_up sebesar 1. Kendala itu memotong kubus nilai x, dan solusi akhir LP baseline untuk ketiga kabupaten/kota ini adalah (0,5; 0,5; 1,0), tepat pada bidang potong. Semua titik pada bidang potong memberi biaya yang sama, sehingga LP-(\*) dapat memiliki lebih dari satu solusi optimal.

![Kendala segitiga sebagai bidang potong](figures/gambar_segitiga_kubus.png)

Letak langkah UCP-CR dan UCP-TR di dalam putaran cutting plane ditunjukkan di bawah. Baseline melewati jalur tanpa kotak putus-putus. UCP-CR menambahkan langkah pemangkasan dengan penguncian sebelum kendala baru dimasukkan, sedangkan UCP-TR menambahkan cabang pengetatan toleransi ketika separasi tidak lagi menemukan kendala baru.

![Putaran cutting plane pada baseline, UCP-CR, dan UCP-TR](figures/gambar_cutting_plane.png)

## Hasil utama (data nasional, n = 514)

| Ukuran | Baseline | UCP-CR | UCP-TR |
|---|---|---|---|
| Objektif LP | 32.729,75 | 32.729,75 | 32.729,75 |
| Putaran cutting plane | 42 | 69 | 47 |
| Kendala segitiga aktif akhir | 1.794.833 | 583.684 (3,08 kali lebih kecil) | 1.781.956 |
| Waktu LP, median dua ulangan | 920,6 s | 775,0 s (542,8 dan 1.007,2 s) | 242,4 s (3,80 kali lebih cepat) |
| Kelompok lapisan 1 / lapisan 2 | 248 / 15 | 243 / 15 | 243 / 15 |
| CC lapisan 2 pada graf ambang rata-rata | 28.445 | 28.445 | 28.445 |

- **RQ1:** LP selesai dengan hanya 1,33% dari 135.005.184 kendala segitiga. Biaya hierarkis baseline 36.947, yaitu 1,129 kali batas bawah LP, jauh di bawah jaminan teoretis 25,7846.
- **RQ2:** UCP-CR memperkecil LP 3,08 kali pada data nasional dan 1,13 sampai 3,08 kali pada kesembilan instans uji. Waktunya tidak stabil di GPU sewaan, sehingga UCP-CR tidak diklaim lebih cepat.
- **RQ3:** UCP-TR 3,80 kali lebih cepat pada data nasional. UCP-TR tidak lebih cepat pada n = 35 (0,92 kali, satu kali jalan), dan percepatannya bertambah dari 1,11 kali pada n = 119 menjadi 3,80 kali pada n = 514.
- Objektif LP ketiga varian sama. Partisi akhir sedikit berbeda (4 daerah pada lapisan 2 dan 16 daerah pada lapisan 1), karena LP-(\*) memiliki lebih dari satu solusi optimal.

### Objektif LP per putaran

Objektif LP naik setiap kali kendala segitiga yang dilanggar ditambahkan, lalu mendatar pada 32.729,75. Ketiga varian berakhir pada objektif yang sama, walaupun UCP-CR menempuh lebih banyak putaran.

![Objektif LP per putaran](figures/gambar_jejak_objektif.png)

### Ukuran LP per putaran (UCP-CR)

Pada baseline dan UCP-TR jumlah kendala terus bertambah sampai sekitar 1,79 juta. Pada UCP-CR jumlahnya tidak pernah melebihi 0,59 juta karena kendala yang tidak aktif dibuang.

![Kendala segitiga di LP per putaran](figures/gambar_jejak_kendala.png)

### Waktu per putaran (UCP-TR)

Kurva UCP-TR naik paling landai karena putaran awalnya diselesaikan pada toleransi 10⁻⁴, dan toleransi baru diketatkan pada putaran 46. Waktu UCP-CR pada gambar berasal dari ulangan pertama (542,8 s), sedangkan ulangan keduanya 1.007,2 s.

![Waktu kumulatif per putaran](figures/gambar_jejak_waktu.png)

## Struktur repositori

| Lokasi | Isi |
|---|---|
| `hcc_nasional_cuopt.py` | Cutting plane + PDLP (cuOpt) di GPU, varian baseline, UCP-CR, dan UCP-TR, pembulatan, dan metrik |
| `hcc_rounding_an2025.py` | Pembulatan An et al. (2025): *pre-clustering* (Algoritma 2) dan clustering hierarkis (Algoritma 1) |
| `test_rounding_an2025.py` | Uji pembulatan dan arah kendala monoton (CPU, HiGHS) |
| `data/` | Dataset nasional 2024, Jawa Tengah 2022, dan tujuh instans wilayah 2024 |
| `results/nasional/` | Baseline (A, A2) dan UCP-CR (C, C2) data nasional, dua ulangan; solusi LP `*_x_lp.npy` untuk A dan C |
| `results/wilayah/` | Baseline dan UCP-CR pada delapan instans uji, tiga ulangan |
| `results/ablasi/` | UCP-TR (E, E2), gabungan UCP-CR dan UCP-TR (CE), serta varian batas 10.000 kendala per putaran (B, D) |
| `scripts/` | Skrip yang dijalankan di server GPU |
| `figures/` | Gambar tesis beserta skrip pembuatnya, dan tangkapan layar panel server |

Setiap jalan menghasilkan `<prefix>_ringkasan.json` (parameter, waktu, objektif, pelanggaran maksimum), `<prefix>_log_lp.csv` (per putaran), `<prefix>_hasil.csv` (metrik), `<prefix>_label_hcc.csv` (label kelompok tiap kabupaten/kota), dan `<prefix>.log`.

## Data

| Berkas | Isi |
|---|---|
| `data/dataset_nasional_2024.csv` | 514 kabupaten/kota, tahun 2024: `Provinsi`, `Kabupaten_Kota`, `Kode` (kode wilayah BPS), `PDRB_ADHK` (PDRB atas dasar harga konstan 2010, juta rupiah), `IPM`, `TPAK` (Sakernas Agustus, persen) |
| `data/dataset_benchmark_jateng_2022.csv` | 35 kabupaten/kota Jawa Tengah, tahun 2022, variabel yang sama |
| `data/wilayah_2024/*.csv` | Instans uji dari data nasional menurut kode provinsi BPS: Sumatera 11–21, Jawa 31–36, Bali-Nusa Tenggara 51–53, Kalimantan 61–65, Sulawesi 71–76, Maluku-Papua 81–82 dan 91–97, serta Jawa Tengah 33 |

Sumber data adalah Badan Pusat Statistik (BPS). PDRB ADHK dan IPM diambil dari tabel BPS pusat, sedangkan TPAK kabupaten/kota diambil dari situs BPS 38 provinsi karena tidak tersedia di tabel BPS pusat.

## Menjalankan

Kebutuhan: GPU NVIDIA, Python 3.12, NVIDIA cuOpt 26.10 (`cuopt-cu12` atau `cuopt-cu13` sesuai driver), dan paket di `requirements.txt`. Skrip `scripts/setup_server.sh` menyiapkan lingkungan di Ubuntu.

```bash
# baseline
python hcc_nasional_cuopt.py data/dataset_nasional_2024.csv PDRB_ADHK,IPM,TPAK results/nasional/A_nasional2024 \
    --monoton an2025 --pembulatan an2025 --presisi double --tol 1e-6
# UCP-CR
python hcc_nasional_cuopt.py data/dataset_nasional_2024.csv PDRB_ADHK,IPM,TPAK results/nasional/C_nasional2024 \
    --monoton an2025 --pembulatan an2025 --presisi double --tol 1e-6 --row-elim
# UCP-TR
python hcc_nasional_cuopt.py data/dataset_nasional_2024.csv PDRB_ADHK,IPM,TPAK results/ablasi/E_nasional2024 \
    --monoton an2025 --pembulatan an2025 --presisi double --tol 1e-6 --tol-awal 1e-4
```

Opsi `--monoton an2025 --pembulatan an2025` wajib dipakai untuk mereproduksi hasil tesis. Nilai bawaan `paper` adalah versi lama dan membutuhkan berkas yang tidak disertakan.

Uji pembulatan dan pembuatan ulang gambar tidak memerlukan GPU:

```bash
python test_rounding_an2025.py
python figures/gambar_jejak_cutting_plane.py
python figures/gambar_segitiga_kubus.py
```

## Spesifikasi server

Seluruh eksperimen dijalankan pada satu GPU instance sewaan dengan spesifikasi berikut.

| Komponen | Spesifikasi |
|---|---|
| Penyedia | GPU instance Hostinger, wilayah Reading, Britania Raya |
| GPU | NVIDIA A100 80 GB PCIe (VRAM 81.920 MiB) |
| CPU | AMD EPYC 7713P 64-Core, dibatasi kuota 4 inti |
| RAM | 8 GB |
| Disk | 100 GB |
| Sistem operasi | Ubuntu 24.04 |
| Driver dan CUDA | Driver NVIDIA 580.196.07 (CUDA driver 13.3); cuOpt memakai CUDA runtime 12.9 |
| Solver LP | NVIDIA cuOpt 26.10.0 (`cuopt-cu12`), metode PDLP, presisi ganda (FP64) |
| Pustaka lain | Python 3.12.3, CuPy 14.2.0, NumPy 2.4.6, SciPy 1.18.1, pandas 3.0.6, scikit-learn 1.9.1 |

Panel ringkasan instance ditunjukkan di bawah. Alamat IP, kunci SSH, perintah SSH, password, dan saldo kredit akun disamarkan.

![Panel GPU instance yang dipakai](figures/server_instance.png)

## Catatan reproduksi

- Waktu dapat berbeda di perangkat lain. GPU sewaan ada kemungkinan dipakai bersama pengguna lain, sehingga waktu dipakai untuk membandingkan varian pada mesin yang sama, bukan sebagai kecepatan mutlak.
- Objektif, jumlah putaran, dan jumlah kendala identik antarulangan varian yang sama.
- Berkas *checkpoint* dan solusi LP selain A, C, dan E nasional tidak disertakan karena ukurannya besar.
- Perbedaan kode ini dari kode yang dijalankan di server hanya dua: path berkas disesuaikan dengan struktur repositori, dan kode paper lama hanya dimuat bila `--pembulatan paper` dipilih. Keduanya tidak memengaruhi hasil dengan opsi `an2025`.

## Rujukan utama

- An, H.-C., Kao, M.-J., Lee, C., & Lee, M.-T. (2025). Handling LP-Rounding for Hierarchical Clustering and Fitting Distances by Ultrametrics. *2025 IEEE 66th Annual Symposium on Foundations of Computer Science (FOCS)*, 1144–1169. https://doi.org/10.1109/FOCS63196.2025.00060
- Grötschel, M., & Wakabayashi, Y. (1989). A Cutting Plane Algorithm for a Clustering Problem. *Mathematical Programming*, 45(1–3), 59–96. https://doi.org/10.1007/BF01589097
- Applegate, D., Diaz, M., Hinder, O., Lu, H., Lubin, M., O'Donoghue, B., & Schudy, W. (2021). Practical Large-Scale Linear Programming using Primal-Dual Hybrid Gradient. *Advances in Neural Information Processing Systems*, 34, 20243–20257.
- Mitchell, J. E. (2009). Cutting Plane Methods and Subgradient Methods. Dalam *Decision Technologies and Applications* (hlm. 34–61). INFORMS. https://doi.org/10.1287/educ.1090.0064

## Penulis dan kontak

- **Muhammad Abiyyu Rahman**
- Email: abiyyu@204l.com, rahmanabiyyu@gmail.com
- Web: [204l.com](https://204l.com)

## Lisensi

- Kode program (`*.py` dan `scripts/`): [MIT](LICENSE).
- Data, hasil eksperimen, dan gambar (`data/`, `results/`, `figures/`): [CC BY 4.0](LICENSE-DATA.md). Pengguna wajib menyebut sumber, termasuk BPS sebagai sumber data asli.

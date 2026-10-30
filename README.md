# UCP-CR dan UCP-TR / UCP-CR and UCP-TR

[Bahasa Indonesia](README.id.md) | [English](README.en.md)

Muhammad Abiyyu Rahman · abiyyu@204l.com · rahmanabiyyu@gmail.com · [204l.com](https://204l.com)

**ID:** Penelitian ini menerapkan algoritma clustering LP-Rounding An et al. (2025) untuk *hierarchical correlation clustering* pada 514 kabupaten/kota di Indonesia tahun 2024 (PDRB ADHK, IPM, dan TPAK dari BPS). LP di dalam algoritma itu memuat 135.005.184 kendala segitiga dan diselesaikan dengan cutting plane dan PDLP di GPU. Dua modifikasi diusulkan pada tahap LP: **UCP-CR** memperkecil LP 3,08 kali, dan **UCP-TR** menyelesaikan LP 3,80 kali lebih cepat, dengan objektif LP yang sama. Eksperimen dijalankan pada GPU NVIDIA A100 80 GB.

**EN:** This research applies the LP-Rounding clustering algorithm of An et al. (2025) for *hierarchical correlation clustering* to 514 Indonesian regencies and cities in 2024 (GRDP, HDI, and labour force participation rate from Statistics Indonesia). The LP inside that algorithm has 135,005,184 triangle constraints and is solved with a cutting plane method and PDLP on the GPU. Two modifications to the LP stage are proposed: **UCP-CR** makes the LP 3.08 times smaller, and **UCP-TR** solves the LP 3.80 times faster, with the same LP objective. The experiments ran on an NVIDIA A100 80 GB GPU.

![Tahap LP-Rounding dan bagian yang dimodifikasi / LP-Rounding stages and the modified part](figures/gambar_lp_rounding.png)

![Putaran cutting plane pada baseline, UCP-CR, dan UCP-TR / Cutting plane loop for the baseline, UCP-CR, and UCP-TR](figures/gambar_cutting_plane.png)

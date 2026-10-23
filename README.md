# Cuaca Mataram

Riwayat cuaca per 30 menit dan prakiraan 7 hari untuk Mataram, Lombok, dengan data dari [Open-Meteo](https://open-meteo.com/).

**Situs:** https://ariblackheart-cyber.github.io/cuaca-mataram/

- `index.html` — halaman web (nyaman di HP), dibuka lewat GitHub Pages
- `data/history.csv` — riwayat per 30 menit (waktu WITA), bisa diunduh langsung
- `data/forecast.json` — kondisi terkini, prakiraan per 30 menit dan harian
- `scripts/fetch.py` — skrip pengambil data
- `.github/workflows/update.yml` — jadwal otomatis tiap 30 menit

Untuk memperbarui data secara manual: tab **Actions** → **Perbarui data cuaca** → **Run workflow**.

Data cuaca: Open-Meteo, lisensi CC BY 4.0.

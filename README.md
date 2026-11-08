# Cuaca Mataram

Riwayat cuaca per 30 menit dan prakiraan 7 hari untuk Mataram, Lombok, dengan data dari [Open-Meteo](https://open-meteo.com/).

**Situs:** https://ariblackheart-cyber.github.io/cuaca-mataram/

- `index.html` — halaman web (nyaman di HP), dibuka lewat GitHub Pages
- `data/history.csv` — riwayat per 30 menit (waktu WITA), bisa diunduh langsung
- `data/forecast.json` — kondisi terkini, prakiraan per 30 menit dan harian
- `scripts/fetch.py` — skrip pengambil data
- `.github/workflows/update.yml` — jadwal otomatis tiap 30 menit

## Riwayat 10 lokasi (cadangan untuk ANEV)

- `data/lokasi/<kode>.csv` — riwayat per 30 menit (WITA) untuk Mataram, Praya, Kuta, Selong, Pringgabaya, Sembalun, Sambelia, Bayan, Tanjung, Sekotong; kolom sama dengan `history.csv`
- `data/lokasi/lokasi.json` — daftar lokasi, koordinat, rentang data
- Koordinat ada di `scripts/lokasi.py`
- Mengisi/melanjutkan: tab **Actions** → **Isi riwayat 10 lokasi** → **Run workflow** (isi tanggal mulai). Aman dijalankan ulang; hanya slot yang belum ada yang diambil (sampai kemarin).

Untuk memperbarui data secara manual: tab **Actions** → **Perbarui data cuaca** → **Run workflow**.

Data cuaca: Open-Meteo, lisensi CC BY 4.0.

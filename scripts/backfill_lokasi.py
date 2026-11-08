"""Riwayat cuaca per 30 menit untuk 10 lokasi Lombok (cadangan/backup untuk ANEV).

Sumber sama dengan backfill.py: Open-Meteo Historical Forecast API (model per 15 menit,
diambil slot :00 dan :30). 10 lokasi diambil dalam SATU permintaan per potongan ±1 bulan.

Hasil: data/lokasi/<kode>.csv  (kolom sama dengan data/history.csv, waktu WITA)
       data/lokasi/lokasi.json (daftar lokasi + koordinat + rentang data)

Aman dijalankan ulang: hanya slot yang belum ada yang diisi (sampai kemarin),
jadi bisa dipakai untuk melanjutkan bila ada potongan yang gagal.

Pemakaian: python scripts/backfill_lokasi.py 2023-01-01
"""
import csv
import json
import os
import sys
import time
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import backfill  # noqa: E402  (pakai get() dengan coba-ulang yang sama)
import fetch  # noqa: E402
from lokasi import LOKASI  # noqa: E402

OUT = os.path.join(fetch.DATA, "lokasi")


def path(kode):
    return os.path.join(OUT, kode + ".csv")


def load(kode):
    hist = {}
    if os.path.exists(path(kode)):
        with open(path(kode), newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                hist[r["waktu_wita"]] = r
    return hist


def save(kode, hist):
    with open(path(kode), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fetch.COLS)
        w.writeheader()
        for t in sorted(hist):
            w.writerow({k: ("" if hist[t].get(k) is None else hist[t].get(k)) for k in fetch.COLS})


def rows_of(d):
    """Satu blok respons (satu lokasi) → {waktu: baris} per 30 menit."""
    h = d.get("hourly", {})
    by_hour = {t: i for i, t in enumerate(h.get("time", []))}
    m = d["minutely_15"]
    out = {}
    for i, t in enumerate(m["time"]):
        if t[14:16] not in ("00", "30") or m["temperature_2m"][i] is None:
            continue
        hi = by_hour.get(t[:13] + ":00")
        cl = h.get("cloud_cover", [])
        pr = h.get("pressure_msl", [])
        code = m["weather_code"][i]
        out[t] = {
            "waktu_wita": t,
            "suhu_c": fetch.rnd(m["temperature_2m"][i]),
            "terasa_c": fetch.rnd(m["apparent_temperature"][i]),
            "kelembapan_pct": fetch.rnd(m["relative_humidity_2m"][i], 0),
            "hujan_mm": fetch.rnd(m["precipitation"][i], 2),
            "angin_kmh": fetch.rnd(m["wind_speed_10m"][i]),
            "arah_angin_deg": fetch.rnd(m["wind_direction_10m"][i], 0),
            "hembusan_kmh": fetch.rnd(m["wind_gusts_10m"][i]),
            "awan_pct": fetch.rnd(cl[hi], 0) if hi is not None and cl[hi] is not None else None,
            "tekanan_hpa": fetch.rnd(pr[hi]) if hi is not None and pr[hi] is not None else None,
            "kode_cuaca": code,
            "kondisi": fetch.KONDISI.get(code, "") if code is not None else "",
        }
    return out


def main():
    start = date.fromisoformat(sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] else "2023-01-01")
    end_all = date.today() - timedelta(days=1)
    os.makedirs(OUT, exist_ok=True)
    hist = {k: load(k) for k, _, _, _ in LOKASI}
    lats = ",".join(str(x[2]) for x in LOKASI)
    lons = ",".join(str(x[3]) for x in LOKASI)

    added, failed, cur = {k: 0 for k in hist}, [], start
    while cur <= end_all:
        stop = min(cur + timedelta(days=30), end_all)
        # Lewati potongan yang sudah lengkap di semua lokasi (48 slot × hari).
        need = ((stop - cur).days + 1) * 48
        have = min(sum(1 for t in h if cur.isoformat() <= t[:10] <= stop.isoformat()) for h in hist.values())
        if have >= need:
            cur = stop + timedelta(days=1)
            continue
        try:
            d = backfill.get({
                "latitude": lats, "longitude": lons, "timezone": fetch.TZ,
                "start_date": cur.isoformat(), "end_date": stop.isoformat(),
                "minutely_15": ",".join(fetch.M15),
                "hourly": "cloud_cover,pressure_msl",
                "wind_speed_unit": "kmh",
            })
            blocks = d if isinstance(d, list) else [d]
            if len(blocks) != len(LOKASI):
                raise RuntimeError(f"respons {len(blocks)} lokasi, diharapkan {len(LOKASI)}")
        except Exception as e:
            failed.append(f"{cur}..{stop}")
            print(f"::error::Gagal {cur} s/d {stop}: {e}", flush=True)
            cur = stop + timedelta(days=1)
            continue
        for (kode, _, _, _), blk in zip(LOKASI, blocks):
            for t, r in rows_of(blk).items():
                if t not in hist[kode]:
                    hist[kode][t] = r
                    added[kode] += 1
        print(f"{cur} s/d {stop}: OK", flush=True)
        cur = stop + timedelta(days=1)
        time.sleep(5)

    info = []
    for kode, nama, lat, lon in LOKASI:
        save(kode, hist[kode])
        h = hist[kode]
        info.append({"kode": kode, "nama": nama, "lat": lat, "lon": lon, "baris": len(h),
                     "mulai": min(h) if h else None, "sampai": max(h) if h else None,
                     "file": f"data/lokasi/{kode}.csv"})
    with open(os.path.join(OUT, "lokasi.json"), "w", encoding="utf-8") as f:
        json.dump({"sumber": "Open-Meteo Historical Forecast API (CC BY 4.0)", "zona": "WITA",
                   "per": "30 menit", "lokasi": info}, f, ensure_ascii=False, indent=1)
    msg = "Ditambahkan " + ", ".join(f"{k} {n}" for k, n in added.items()) + " baris."
    if failed:
        msg += " Gagal (jalankan ulang untuk melanjutkan): " + ", ".join(failed)
    print(f"::notice::{msg}", flush=True)


if __name__ == "__main__":
    main()

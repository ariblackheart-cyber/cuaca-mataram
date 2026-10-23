"""Isi riwayat data/history.csv mundur sampai tanggal tertentu (sekali jalan).

Sumber: Open-Meteo Historical Forecast API (data model per 15 menit,
diambil slot :00 dan :30). Slot yang sudah ada di history.csv tidak ditimpa.

Pemakaian: python scripts/backfill.py 2023-01-01
"""
import csv
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fetch  # noqa: E402  (pakai konstanta & kamus kondisi yang sama)

API = "https://historical-forecast-api.open-meteo.com/v1/forecast"


def get(params):
    url = API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "cuaca-mataram/1.0"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")[:300]
            if e.code in (429, 500, 502, 503) and attempt < 3:
                time.sleep(20 * (attempt + 1))
                continue
            raise RuntimeError(f"HTTP {e.code}: {body}") from e


def rows_for(start, end):
    d = get({
        "latitude": fetch.LAT, "longitude": fetch.LON, "timezone": fetch.TZ,
        "start_date": start.isoformat(), "end_date": end.isoformat(),
        "minutely_15": ",".join(fetch.M15),
        "hourly": "cloud_cover,pressure_msl",
        "wind_speed_unit": "kmh",
    })
    h = d.get("hourly", {})
    by_hour = {t: i for i, t in enumerate(h.get("time", []))}
    m = d["minutely_15"]
    out = {}
    for i, t in enumerate(m["time"]):
        if t[14:16] not in ("00", "30") or m["temperature_2m"][i] is None:
            continue
        hi = by_hour.get(t[:13] + ":00")
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
            "awan_pct": fetch.rnd(h["cloud_cover"][hi], 0) if hi is not None and h["cloud_cover"][hi] is not None else None,
            "tekanan_hpa": fetch.rnd(h["pressure_msl"][hi]) if hi is not None and h["pressure_msl"][hi] is not None else None,
            "kode_cuaca": code,
            "kondisi": fetch.KONDISI.get(code, "") if code is not None else "",
        }
    return out


def main():
    start = date.fromisoformat(sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] else "2023-01-01")
    hist = {}
    if os.path.exists(fetch.HIST):
        with open(fetch.HIST, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                hist[r["waktu_wita"]] = r
    end_all = date.fromisoformat(min(hist)[:10]) - timedelta(days=1) if hist else date.today()
    if end_all < start:
        print("Riwayat sudah mencakup tanggal itu.")
        return

    added, cur = 0, start
    while cur <= end_all:
        stop = min(cur + timedelta(days=89), end_all)  # potongan ±3 bulan
        chunk = rows_for(cur, stop)
        for t, r in chunk.items():
            if t not in hist:
                hist[t] = r
                added += 1
        print(f"{cur} s/d {stop}: {len(chunk)} slot")
        cur = stop + timedelta(days=1)
        time.sleep(2)

    with open(fetch.HIST, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fetch.COLS)
        w.writeheader()
        for t in sorted(hist):
            w.writerow({k: ("" if hist[t].get(k) is None else hist[t].get(k)) for k in fetch.COLS})
    print(f"Ditambahkan {added} baris. Total {len(hist)} baris, mulai {min(hist)}.")


if __name__ == "__main__":
    main()

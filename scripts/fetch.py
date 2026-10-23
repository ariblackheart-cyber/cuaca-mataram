"""Ambil data cuaca Mataram dari Open-Meteo dan perbarui file data.

- data/history.csv  : riwayat per 30 menit (waktu WITA), terus bertambah
- data/forecast.json: kondisi terkini, prakiraan per 30 menit dan harian 7 hari

Hanya memakai pustaka standar Python.
"""
import csv
import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

LAT, LON = -8.5833, 116.1167  # Mataram, Lombok
TZ = "Asia/Makassar"
WITA = timezone(timedelta(hours=8))

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
HIST = os.path.join(DATA, "history.csv")
FCST = os.path.join(DATA, "forecast.json")

M15 = [
    "temperature_2m", "relative_humidity_2m", "apparent_temperature",
    "precipitation", "weather_code", "wind_speed_10m",
    "wind_direction_10m", "wind_gusts_10m",
]
HOURLY = ["cloud_cover", "pressure_msl", "precipitation_probability", "uv_index"]
DAILY = [
    "weather_code", "temperature_2m_max", "temperature_2m_min",
    "precipitation_sum", "precipitation_probability_max",
    "wind_speed_10m_max", "uv_index_max", "sunrise", "sunset",
]

COLS = [
    "waktu_wita", "suhu_c", "terasa_c", "kelembapan_pct", "hujan_mm",
    "angin_kmh", "arah_angin_deg", "hembusan_kmh", "awan_pct",
    "tekanan_hpa", "kode_cuaca", "kondisi",
]

KONDISI = {
    0: "Cerah", 1: "Cerah berawan", 2: "Berawan sebagian", 3: "Mendung",
    45: "Berkabut", 48: "Kabut beku",
    51: "Gerimis ringan", 53: "Gerimis", 55: "Gerimis lebat",
    56: "Gerimis beku", 57: "Gerimis beku lebat",
    61: "Hujan ringan", 63: "Hujan sedang", 65: "Hujan lebat",
    66: "Hujan beku", 67: "Hujan beku lebat",
    71: "Salju ringan", 73: "Salju", 75: "Salju lebat", 77: "Butiran salju",
    80: "Hujan lokal ringan", 81: "Hujan lokal", 82: "Hujan lokal lebat",
    85: "Hujan salju", 86: "Hujan salju lebat",
    95: "Badai petir", 96: "Badai petir dan hujan es", 99: "Badai petir hebat",
}


def get(params):
    url = "https://api.open-meteo.com/v1/forecast?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "cuaca-mataram/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def rnd(v, n=1):
    return None if v is None else round(v, n)


def main():
    first_run = not os.path.exists(HIST)
    params = {
        "latitude": LAT, "longitude": LON, "timezone": TZ,
        "minutely_15": ",".join(M15), "hourly": ",".join(HOURLY),
        "daily": ",".join(DAILY),
        # Run pertama mengisi riwayat 92 hari ke belakang sekaligus.
        "past_days": 92 if first_run else 3,
        "forecast_days": 8,
        "wind_speed_unit": "kmh",
    }
    d = get(params)

    # Data per jam diselipkan ke tiap slot 30 menit pada jam yang sama.
    h = d["hourly"]
    by_hour = {t: i for i, t in enumerate(h["time"])}

    m = d["minutely_15"]
    now = datetime.now(WITA).replace(tzinfo=None)
    past, future = {}, []
    for i, t in enumerate(m["time"]):
        if t[14:16] not in ("00", "30"):
            continue
        if m["temperature_2m"][i] is None:
            continue
        hi = by_hour.get(t[:13] + ":00")
        code = m["weather_code"][i]
        row = {
            "waktu_wita": t,
            "suhu_c": rnd(m["temperature_2m"][i]),
            "terasa_c": rnd(m["apparent_temperature"][i]),
            "kelembapan_pct": rnd(m["relative_humidity_2m"][i], 0),
            "hujan_mm": rnd(m["precipitation"][i], 2),
            "angin_kmh": rnd(m["wind_speed_10m"][i]),
            "arah_angin_deg": rnd(m["wind_direction_10m"][i], 0),
            "hembusan_kmh": rnd(m["wind_gusts_10m"][i]),
            "awan_pct": rnd(h["cloud_cover"][hi], 0) if hi is not None else None,
            "tekanan_hpa": rnd(h["pressure_msl"][hi]) if hi is not None else None,
            "kode_cuaca": code,
            "kondisi": KONDISI.get(code, ""),
        }
        ts = datetime.fromisoformat(t)
        if ts <= now:
            past[t] = row
        else:
            row["peluang_hujan_pct"] = h["precipitation_probability"][hi] if hi is not None else None
            future.append(row)

    # Gabungkan dengan riwayat lama; nilai terbaru menimpa slot yang sama.
    hist = {}
    if not first_run:
        with open(HIST, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                hist[r["waktu_wita"]] = r
    hist.update(past)
    os.makedirs(DATA, exist_ok=True)
    with open(HIST, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        for t in sorted(hist):
            w.writerow({k: ("" if hist[t].get(k) is None else hist[t].get(k)) for k in COLS})

    dd = d["daily"]
    today = now.strftime("%Y-%m-%d")
    daily = []
    for i, t in enumerate(dd["time"]):
        if t < today:
            continue
        daily.append({
            "tanggal": t,
            "kode_cuaca": dd["weather_code"][i],
            "kondisi": KONDISI.get(dd["weather_code"][i], ""),
            "maks_c": dd["temperature_2m_max"][i],
            "min_c": dd["temperature_2m_min"][i],
            "hujan_mm": dd["precipitation_sum"][i],
            "peluang_hujan_pct": dd["precipitation_probability_max"][i],
            "angin_maks_kmh": dd["wind_speed_10m_max"][i],
            "uv_maks": dd["uv_index_max"][i],
            "matahari_terbit": dd["sunrise"][i][11:16],
            "matahari_terbenam": dd["sunset"][i][11:16],
        })
        if len(daily) == 7:
            break

    latest = past[max(past)] if past else None
    out = {
        "diperbarui": datetime.now(WITA).isoformat(timespec="minutes"),
        "lokasi": {"nama": "Mataram, Lombok", "lat": LAT, "lon": LON},
        "terkini": latest,
        "per30menit": [r for r in future if r["waktu_wita"] < (now + timedelta(days=7)).isoformat()],
        "harian": daily,
    }
    with open(FCST, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))

    print(f"riwayat: {len(hist)} baris, prakiraan: {len(out['per30menit'])} slot, {len(daily)} hari")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # tampilkan pesan jelas di log Actions
        print("Gagal memperbarui data:", e, file=sys.stderr)
        raise

"""Tren cuaca 30 hari ke depan dari prakiraan jangka panjang ECMWF (EC46/SEAS5)
lewat Open-Meteo Seasonal API.

Menulis:
- data/outlook.json : ringkasan harian (rata-rata dan sebaran antar-anggota ensemble)
- data/outlook.csv  : tabel yang sama untuk diunduh

Diperbarui paling sering tiap 12 jam (model jangka panjang tidak berubah tiap jam).
"""
import csv
import json
import os
import statistics
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fetch  # noqa: E402

API = "https://seasonal-api.open-meteo.com/v1/seasonal"
OUT_JSON = os.path.join(fetch.DATA, "outlook.json")
OUT_CSV = os.path.join(fetch.DATA, "outlook.csv")
VARS = ["temperature_2m_max", "temperature_2m_min", "precipitation_sum"]
DAYS = 30


def get(params):
    url = API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "cuaca-mataram/1.0"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)


def pct(vals, p):
    s = sorted(vals)
    k = (len(s) - 1) * p
    lo, hi = int(k), min(int(k) + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


def members(daily, var, i):
    """Nilai semua anggota ensemble untuk satu variabel pada hari ke-i."""
    vals = []
    for key, arr in daily.items():
        if key == var or key.startswith(var + "_member"):
            v = arr[i] if i < len(arr) else None
            if v is not None:
                vals.append(v)
    return vals


def main():
    now = datetime.now(fetch.WITA)
    if os.path.exists(OUT_JSON):
        try:
            with open(OUT_JSON, encoding="utf-8") as f:
                prev = datetime.fromisoformat(json.load(f)["diperbarui"])
            if now - prev < timedelta(hours=12) and "--paksa" not in sys.argv:
                print("Tren 30 hari masih baru, dilewati.")
                return
        except Exception:
            pass

    d = get({
        "latitude": fetch.LAT, "longitude": fetch.LON, "timezone": fetch.TZ,
        "daily": ",".join(VARS),
    })
    daily = d["daily"]
    today = now.strftime("%Y-%m-%d")
    rows = []
    for i, t in enumerate(daily["time"]):
        if t <= today:
            continue
        mx, mn, pr = (members(daily, v, i) for v in VARS)
        if not mx or not mn:
            continue
        rows.append({
            "tanggal": t,
            "maks_c": round(statistics.mean(mx), 1),
            "min_c": round(statistics.mean(mn), 1),
            "maks_c_p10": round(pct(mx, .1), 1), "maks_c_p90": round(pct(mx, .9), 1),
            "min_c_p10": round(pct(mn, .1), 1), "min_c_p90": round(pct(mn, .9), 1),
            "hujan_mm": round(statistics.mean(pr), 1) if pr else None,
            "hujan_mm_p90": round(pct(pr, .9), 1) if pr else None,
            "peluang_hujan_pct": round(100 * sum(1 for v in pr if v >= 1) / len(pr)) if pr else None,
            "anggota": len(mx),
        })
        if len(rows) == DAYS:
            break
    if not rows:
        raise RuntimeError("Respons tidak berisi data harian: " + ", ".join(list(daily)[:8]))

    out = {"diperbarui": now.isoformat(timespec="minutes"), "model": "ECMWF EC46 (ensemble)", "harian": rows}
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"Tren {len(rows)} hari dari {rows[0]['anggota']} anggota ensemble.")


if __name__ == "__main__":
    try:
        main()
    except urllib.error.HTTPError as e:
        print(f"::error::Tren 30 hari gagal: HTTP {e.code} {e.read().decode('utf-8', 'replace')[:300]}")
        sys.exit(1)

"""
Fetch all libraries from Affluences in Île-de-France, request details for each,
extract available seats (when present), and produce an interactive map + CSV.

Requirements:
    pip install requests folium pandas tqdm
"""

import requests
import time
import re
import unicodedata
import csv
from statistics import mean
from tqdm import tqdm
import folium
import pandas as pd

BASE_LIST_URL = "https://api.affluences.com/app/v3/sites"
BASE_SITE_URL = "https://api.affluences.com/app/v3/sites/{}"

HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json",
    "Origin": "https://affluences.com",
    "Referer": "https://affluences.com/",
    "User-Agent": "YourMom/8.0.0 (Fridge 14; Mobile; fr_FR)",
}


def norm_text(s: str) -> str:
    if not s:
        return ""
    s = str(s)
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return s.lower()


def extract_first_int(s: str):
    if not s:
        return None
    m = re.search(r"\d+", s.replace("\u202f", ""))
    return int(m.group()) if m else None


def is_ile_de_france(region_string: str) -> bool:
    r = norm_text(region_string)
    return (
        ("ile" in r and "france" in r)
        or ("île" in r and "france" in r)
        or ("ile-de-france" in r)
        or ("ile de france" in r)
    )


def fetch_all_library_sites(session: requests.Session):
    page = 0
    all_sites = []
    while True:
        payload = {"selected_categories": [1], "page": page}
        resp = session.post(BASE_LIST_URL, json=payload, headers=HEADERS, timeout=20)
        if resp.status_code != 200:
            raise RuntimeError(
                f"List request failed page={page} status={resp.status_code}: {resp.text}"
            )
        payload_json = resp.json()
        results = payload_json.get("data", {}).get("results", [])
        if not results:
            break
        all_sites.extend(results)
        page += 1

        time.sleep(0.12)
    return all_sites


def fetch_site_detail(session: requests.Session, slug: str):
    url = BASE_SITE_URL.format(slug)
    resp = session.get(url, headers=HEADERS, timeout=20)
    if resp.status_code != 200:
        raise RuntimeError(
            f"Detail request failed for slug={slug} status={resp.status_code}"
        )
    return resp.json().get("data", {})


def get_available_seats_from_infos(infos):
    if not infos:
        return None
    keywords = [
        "available",
        "available seats",
        "available places",
        "places disponibles",
        "places disponibles",
        "places",
        "places disponibles (approx)",
        "places disponibles (approx.)",
        "places disponibles approximatives",
        "places disponibles approximative",
    ]
    for info in infos:
        title = norm_text(info.get("title", ""))
        desc = norm_text(info.get("description", ""))
        combined = f"{title} {desc}"
        for kw in keywords:
            if kw in combined:
                n = extract_first_int(
                    info.get("description", "") or info.get("title", "")
                )
                if n is not None:
                    return n
    for info in infos:
        n = extract_first_int(info.get("description", "") or info.get("title", ""))
        if n is not None:
            return n
    return None


def main():
    session = requests.Session()
    print("Fetching all sites (category=Library)...")
    all_sites = fetch_all_library_sites(session)
    print(f"Total sites returned by API (all regions): {len(all_sites)}")

    libraries = []
    for s in all_sites:
        addr = s.get("location", {}).get("address", {})
        region = addr.get("region", "") or ""
        if is_ile_de_france(region):
            libraries.append(s)

    print(f"Libraries in Île-de-France found in list results: {len(libraries)}")

    enriched = []
    print(
        "Fetching details for each library and extracting available seats (if present)..."
    )
    for s in tqdm(libraries, desc="libraries"):
        slug = s.get("slug") or s.get("id")
        try:
            detail = fetch_site_detail(session, slug)
        except Exception as e:

            print(f"Warning: failed to fetch detail for {slug}: {e}")
            detail = s

        infos = detail.get("infos", []) or s.get("infos", [])
        available_seats = get_available_seats_from_infos(infos)

        occupancy = detail.get("current_forecast", {}).get("occupancy")
        est_distance = s.get("estimated_distance")

        lat = None
        lon = None
        coords = s.get("location", {}).get("coordinates", {})
        if coords:
            lat = coords.get("latitude")
            lon = coords.get("longitude")

        enriched.append(
            {
                "id": s.get("id"),
                "slug": s.get("slug"),
                "name": s.get("primary_name") or s.get("concat_name"),
                "address": s.get("location", {}).get("address", {}),
                "latitude": lat,
                "longitude": lon,
                "available_seats": available_seats,
                "occupancy_percent": occupancy,
                "estimated_distance_m": est_distance,
                "detail_url": detail.get("url"),
            }
        )

        time.sleep(0.12)

    csv_file = "ile_de_france_libraries.csv"
    print(f"Saving CSV to {csv_file} ...")
    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "id",
                "slug",
                "name",
                "latitude",
                "longitude",
                "available_seats",
                "occupancy_percent",
                "estimated_distance_m",
                "detail_url",
            ],
        )
        writer.writeheader()
        for r in enriched:
            writer.writerow(
                {
                    "id": r["id"],
                    "slug": r["slug"],
                    "name": r["name"],
                    "latitude": r["latitude"],
                    "longitude": r["longitude"],
                    "available_seats": r["available_seats"],
                    "occupancy_percent": r["occupancy_percent"],
                    "estimated_distance_m": r["estimated_distance_m"],
                    "detail_url": r["detail_url"],
                }
            )

    coords_list = [
        (r["latitude"], r["longitude"])
        for r in enriched
        if r["latitude"] and r["longitude"]
    ]
    if coords_list:
        avg_lat = mean([c[0] for c in coords_list])
        avg_lon = mean([c[1] for c in coords_list])
    else:
        avg_lat, avg_lon = 48.8566, 2.3522

    map_obj = folium.Map(location=[avg_lat, avg_lon], zoom_start=10)

    for r in enriched:
        lat = r["latitude"]
        lon = r["longitude"]
        if lat is None or lon is None:
            continue
        name = r["name"]
        seats = r["available_seats"]
        occ = r["occupancy_percent"]
        addr = r["address"].get("route", "") + " " + r["address"].get("city", "")
        detail_url = r["detail_url"] or f"https://affluences.com/site/{r['slug']}"
        popup_html = f"""
        <strong>{name}</strong><br/>
        {addr}<br/>
        Available seats: {seats if seats is not None else 'unknown'}<br/>
        Occupancy: {occ if occ is not None else 'unknown'}%<br/>
        <a href="{detail_url}" target="_blank">Site detail</a>
        """
        folium.Marker(
            location=[lat, lon],
            popup=folium.Popup(popup_html, max_width=300),
            tooltip=name,
        ).add_to(map_obj)

    map_file = "ile_de_france_libraries_map.html"
    map_obj.save(map_file)
    print(f"Map saved to {map_file}")
    print("Done. Files created:")
    print(f"  - {csv_file}")
    print(f"  - {map_file}")
    print("Open the HTML file in a browser to view the interactive map.")


if __name__ == "__main__":
    main()

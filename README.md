# 📚 Affluences Reverse Engineering (Unofficial)

This script **fetches all library sites from the Affluences API** (category=Library), filters those located in **Île-de-France**, retrieves detailed information for each site, and extracts available seat counts (when present). The reason I made this is because I wanted to find libraries nearby, and usually: bigger seat count == better library == better chances to find a seat.

It generates:
- A **CSV file** listing all enriched libraries and their metadata.
- An **interactive map (HTML)** with markers showing seat availability and occupancy.

⚠️ **Disclaimer**: Please don't hurt me, this is an **unofficial reverse engineering project** for educational purposes only 😭. It would theoretically work, but only IF you run main.py, at which point, it might or might not be against affluence's ToS.

---

## ✨ Features

- Fetch all libraries (filter: Île-de-France only) from Affluences API.
- Retrieve details for each library, including:
  - Name & address
  - Available seats (when indicated)
  - Occupancy percentage
  - Coordinates
  - Direct link to the Affluences page
- Export results to:
  - `ile_de_france_libraries.csv`
  - `ile_de_france_libraries_map.html` (interactive map)
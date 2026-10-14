# Motorcycle Evidence

Independent analysis and presentation for Dr Owen Williams, MotoEng / UWTSD.

## Coverage

- Detailed explorer: final annual STATS19 collision, vehicle and casualty records, 2021–2025.
- Historical context: official DfT RAS0102 national motorcycle casualty counts and mileage rates, 1979–2025.
- Snapshot retrieved 14 October 2026. No runtime AI, tracking, live feed or automatic refresh.
- Public distribution contains aggregate cells without identifiers, coordinates or contact details.

## Refresh

Run `download_recent.py` with the bundled Python runtime to obtain the annual files. The raw inputs remain in `Road Safety/STATS19 2025 release` outside this Site repository. The official tables ZIP and data guide are also stored there with source URLs and hashes in the manifest files. The download years and all coverage labels must be deliberately updated for a later release.

Run `analyse.py` to validate joins and build aggregate JSON and summary CSVs in `dist/data`. The script fails on duplicate keys, unmatched records, invalid severity weights or disagreement with official annual totals. Do not publish after a failed run.

Five 2024 casualties have motorcycle casualty types but non-motorcycle vehicle types. They are retained in casualty counts, with their own vehicle context, and reported in the audit. Vehicle-involvement statistics use vehicle type independently.

`download_data.py` records the attempted complete historical data acquisition. The large transfers stalled and were stopped; incomplete files are not used. Historical analysis instead uses the complete official RAS0102 tables. Do not present the 1979–2025 record-level files as acquired.

## Run and validate

Serve `dist` with a static HTTP server. Check desktop and narrow layouts, all navigation tabs, filters, metric changes, history controls and downloads. `node --check dist/app.js` verifies JavaScript syntax. Counts are checked independently against DfT RAS0102 in `analyse.py`.

## Publication

Use the Sites skill's source helper and native publish tools, preserving `.openai/hosting.json`. Credentials must never be saved in this repository. The user requested public access for anyone with the link.

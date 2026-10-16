# Motorcycle Evidence

Independent analysis and presentation for Dr Owen Williams, MotoEng / UWTSD.

## Coverage

- Detailed explorer: final annual STATS19 collision, vehicle and casualty records, 2021–2025.
- Historical context: official DfT RAS0102 national motorcycle casualty counts and mileage rates, 1979–2025.
- Snapshot retrieved 14 October 2026. Frozen trained models run locally in the browser. No external AI service, tracking, live feed or automatic refresh.
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

## AI research prototype

`train_model.py` defines the cohort, training (2021–2023), calibration (2024), and untouched later-year test (2025). The exported model contains fitted logistic coefficients and boosted decision trees with sigmoid calibration. `dist/ai.js` evaluates these frozen parameters in the browser; it does not retrain or send visitor inputs anywhere. No individual records or identifiers are in the model assets.

The cohort covers 22 police force areas with established injury-based reporting, selected using training-period reporting flags only. Scenario support counts are from the training set. Recorded KSI is the target; adjusted severity probabilities are not predictors or training labels.

The first fixed model experiment favours logistic regression slightly on the 2025 test. This is stated in the UI. Do not tune models on this test set and continue calling it untouched. Revisions require a fresh validation design.

Dependencies were installed in the project-level `ml-dependencies` directory, outside the Site source repository, preserving the bundled runtime. Model library versions are in `dist/data/ai-report.json`. Run `node check_ai.cjs` to compare browser inference with Python-generated reference predictions and check scenario handlers. These checks do not establish browser visual quality.


## Motorcycles and age

`dist/bikes.html` compares all makes and capacities with age filters, age-by-category/capacity/type tables, model-family drilldown and CSV exports. Default: all capacities, riders only, 2020–2025. Age is casualty age, explicitly relabelled for passenger and combined views. Curated bike types remain partial. No personal purchasing shortlist is published. `analyse_bikes.py` validates recorded national totals in all years, adjusted totals from 2021 only. `node check_bikes.cjs` checks age aggregation and interactions. Browser visual QA remains unverified.

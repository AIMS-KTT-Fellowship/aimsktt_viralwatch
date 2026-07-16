# output/ — cleaned datasets for ViralWatch

This folder contains cleaned, scoped datasets produced by the scripts in
`scripts/`. Each file below lists what produced it, what changed from the
raw source, and why — so a reviewer (or future us) doesn't have to
rediscover these decisions.

**Reproducibility note:** the `scripts/` here start from `*_merged.csv`
files (the outer-joined output of each raw dataset's per-metric CSVs).
That outer-join step is not yet itself scripted — if a reviewer runs
"clone + follow README" today, they can regenerate everything *from*
the `*_merged.csv` files, but not the merge step itself yet. Worth
fixing before Friday.

---

## insp_sitrep (target variable + core epi signal)

**Script:** `scripts/clean_insp_sitrep.py`
**Input:** `output/insp_sitrep_merged.csv` (outer join of all 31 insp_sitrep files)

| Output file | Contents |
|---|---|
| `insp_sitrep_zone_level_clean.csv` | Health-zone-level rows only, dtypes fixed, missing dates flagged |
| `insp_sitrep_national_clean.csv` | The rows that were actually national rollups (`nom` blank in the source merge), split out so they don't corrupt zone-level joins |
| `insp_sitrep_training_window.csv` | Zone-level rows scoped to **2026-05-14 to 2026-05-29** |

**Key decisions:**
- `"ND"` (INSP's own missing-value code) is treated as genuinely missing (`NaN`), never as zero — confirmed this matches the source README's own documented convention (0 is reported as a real 0; ND/blank/not-included are all the same "missing" state).
- 36 rows in the raw merge have no `nom` at all — these are national-total rows that don't belong in a per-zone table. Split into `insp_sitrep_national_clean.csv` rather than dropped.
- 1 row (Nyankunde) has a missing `date` — flagged explicitly in script output rather than silently dropped.
- **Target variable (`new_suspected_cases`) is only reported at health-zone level from 2026-05-14 to 2026-05-29** — INSP stops publishing that granular breakdown after that date (confirmed: neither `new_suspected_cases` nor `cumulative_suspected_cases` have any zone-level rows past 2026-05-30). This is a real gap in what was published, not a join bug. Training window scoped to match, since confirmed-case data can't substitute — it's the outcome we're trying to predict *before*, not a proxy for the same signal.

---

## flowminder (mobility / cross-border signal)

**Script:** `scripts/clean_flowminder.py`
**Input:** `output/flowminder_merged.csv`
**Output:** `flowminder_clean.csv` — 468 zones × 9 real metrics (Ituri/North-Kivu subscriber-days prior/follow-up, 5 dated outflow snapshots)

**Key decisions:**
- Every `__static` column was an exact duplicate of its "bare" counterpart (verified byte-identical) — dropped, kept the bare version.
- `__static.matrix` columns were near-empty artifacts (as low as 4-5 non-null values out of ~470 rows) — dropped.
- Dropped the 4 columns belonging to the full `flowminder__inflow/outflow` dataset — team decision was to use `flowminder_short_trips` only, not the full `flowminder/` folder.
- 52 of 519 health zones have no Flowminder data at all (not missing values — absent rows). Expected for a mobile-subscriber-density dataset (low cell-tower coverage in some rural zones) — treat as structurally missing downstream, not zero.

---

## worldpop (population count + density, for rate normalization)

**Script:** `scripts/merge_worldpop.py`
**Input:** `data/external/BDBV2026-Data/build/long/worldpop__*.csv`
**Output:** `worldpop_merged.csv` — 519 zones × (`nom`, `pop_count`, `pop_density`)

**Key decisions:**
- Source files have **no header row** (unlike most of `build/long/`) — column names assigned from the filename itself (`worldpop__pop_count.csv` → `pop_count`).
- `pop_count` is the one actually needed for rate normalization (`case_rate = new_suspected_cases / pop_count`) — without it, large zones look "worse" purely from size, not real outbreak severity. `pop_density` is a secondary context feature, not a substitute.
- Zone-level only (no date) — joins onto every date row for a given zone via a plain merge on `nom`, not `nom`+`date`.

---

## OSRM nearest-active-zone feature (cross-border / proximity signal)

**Script:** `scripts/compute_osrm_nearest_active.py`
**Input:** `data/external/BDBV2026-Data/build/long/osrm__travel_time.csv` + `insp_sitrep_training_window.csv`
**Output:** `osrm_nearest_active_feature.csv` — one row per zone per date: minutes to the nearest zone with active cases that day

**Key decisions:**
- The source file is a full 519×519 travel-time **matrix**, not tidy long format (despite living in the `build/long/` folder) — not melted in full, since only "distance to nearest active zone" is needed, not every pairwise distance.
- Column headers are mangled by R's name-sanitization (spaces/parens replaced with dots, duplicate suffixes like `.1`) and don't reliably match canonical zone spelling as text. Fixed using a verifiable property instead of text-guessing: every zone's distance to itself is 0, confirmed across all 519 diagonal positions, proving row *i* and column *i* are the same zone positionally — then renamed columns from the (already-labeled) row names.
- Row/column names still needed `aliases.csv` resolution afterward (47 don't match canonical shapefile spelling).
- "Active zone" on a given date = any zone with `cumulative_suspected_cases > 0` as of that date. Only 13 of the training-window's dates have any active zone at all — the earliest days of the outbreak genuinely predate any zone crossing that threshold. This feature is undefined for those dates; decide explicitly how the model should treat that rather than silently filling.
- This replaces the original plan of "distance to nearest treatment centre" (which needed `public_health_response` to identify facility locations) — using known active-case zones as the anchor set instead, which is arguably a better fit for an outbreak-proximity watchlist anyway.

---

## public_health_response (not currently used in modeling)

**Script:** `scripts/clean_public_health_response.py`
**Status:** Cleaned and available (`public_health_response_zone_level_clean.csv` etc.), but not part of the current feature set — team decided not to use shapefile-derived/facility-identification data in training. Kept here since the cleaning surfaced a genuinely severe data-quality issue worth documenting even if unused: 95% of the raw merged rows were province/national rollups mixed into what should have been a zone-level table, plus a duplicate-language-column issue (base column == `_en` column, exact duplicates) and inconsistent province-name spelling (`North-Kivu`/`Nord-Kivu`/`North Kivu` all appearing as separate values for the same province).

---

## Shapefile

**Script:** (local, see `scripts/prepare_shapefile.py` or `clean_shapefile.py`)
**Output:** `drc_health_zones_clean.geojson` — 519 zones, `nom`/`zscode`/`province`/`geometry` only

**Key decisions:**
- **Not used as a model input** — geometry is for the dashboard's static base map only, joined to tabular data client-side on `nom`.
- HDX serves an outdated (pre-July-2026) version of this shapefile with different spellings for ~47 zones — confirmed by comparing column signatures against the repo's own `archived/` copy. The canonical file must come from the INRB-UMIE repo directly (`data/shapefiles/DRC_Health_zones.shp`), verified via SHA256 + column-contract check before use.
- 5 invalid geometries in the old HDX file, 0 in the correct one — itself a demonstration of why the source matters.
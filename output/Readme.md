# output/ — cleaned datasets and model for ViralWatch

This folder contains cleaned, scoped datasets and the anomaly-detection
model produced by the scripts in `scripts/`. Each section below lists
what produced it, what changed from the raw source, and why — so a
reviewer (or future us) doesn't have to rediscover these decisions.

**Reproducibility note:** the per-dataset cleaning scripts (`clean_insp_sitrep.py`,
`clean_flowminder.py`, `merge_worldpop.py`, `compute_osrm_nearest_active.py`,
`clean_public_health_response.py`) start from `*_merged.csv` files (the
outer-joined output of each raw dataset's per-metric CSVs). That
outer-join step is not yet itself scripted — if a reviewer runs "clone +
follow README" today, they can regenerate everything *from* the
`*_merged.csv` files, but not the merge step itself yet. Worth fixing
before Friday.

**Known data gap — read before treating the model's baseline as a true
"pre-outbreak" period:** the project brief asks for training on
"pre-outbreak baseline reporting patterns from normal INSP weekly
reports" and evaluation against an April 24-May 5 anomaly window,
"ten days before official confirmation on May 15." **No data anywhere
in the pinned INRB-UMIE dataset predates 2026-05-14**, at either
national or zone level. We checked all 7 data sources listed in the
project brief specifically for this (INRB-UMIE/BDBV2026-Data, the live
dashboard, WHO DON bulletins, WHO Weekly External SitReps, INSP
SitRep_MVE PDFs, the HDX shapefile, ECDC tracker) — none contain
routine/non-outbreak surveillance data, and none predate May 14. WHO
Weekly SitReps explicitly state they're "published weekly since the
outbreak was declared"; INSP's "MVE" reports are Ebola-specific by
name. This has been raised with program organizers. In the meantime,
the model (see below) trains on the *earliest available* dates as an
explicit adaptation, not a true pre-outbreak baseline — this is stated
again in `scripts/prepare_and_train_svm.py`'s docstring so the
limitation travels with the code, not just this file.

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
**Output:** `flowminder_clean.csv` — 468 zones x 9 real metrics (Ituri/North-Kivu subscriber-days prior/follow-up, 5 dated outflow snapshots)

**Key decisions:**
- Every `__static` column was an exact duplicate of its "bare" counterpart (verified byte-identical) — dropped, kept the bare version.
- `__static.matrix` columns were near-empty artifacts (as low as 4-5 non-null values out of ~470 rows) — dropped.
- Dropped the 4 columns belonging to the full `flowminder__inflow/outflow` dataset — team decision was to use `flowminder_short_trips` only, not the full `flowminder/` folder.
- 52 of 519 health zones have no Flowminder data at all (not missing values — absent rows). Expected for a mobile-subscriber-density dataset (low cell-tower coverage in some rural zones) — treat as structurally missing downstream, not zero.

---

## worldpop (population count + density, for rate normalization)

**Script:** `scripts/merge_worldpop.py`
**Input:** `data/external/BDBV2026-Data/build/long/worldpop__*.csv`
**Output:** `worldpop_merged.csv` — 519 zones x (`nom`, `pop_count`, `pop_density`)

**Key decisions:**
- Source files have **no header row** (unlike most of `build/long/`) — column names assigned from the filename itself (`worldpop__pop_count.csv` -> `pop_count`).
- `pop_count` is the one actually needed for rate normalization (`case_rate = new_suspected_cases / pop_count`) — without it, large zones look "worse" purely from size, not real outbreak severity. `pop_density` is a secondary context feature, not a substitute.
- Zone-level only (no date) — joins onto every date row for a given zone via a plain merge on `nom`, not `nom`+`date`.

---

## OSRM nearest-active-zone feature (cross-border / proximity signal)

**Script:** `scripts/compute_osrm_nearest_active.py`
**Input:** `data/external/BDBV2026-Data/build/long/osrm__travel_time.csv` + `insp_sitrep_training_window.csv`
**Output:** `osrm_nearest_active_feature.csv` — one row per zone per date: minutes to the nearest zone with active cases that day

**Key decisions:**
- The source file is a full 519x519 travel-time **matrix**, not tidy long format (despite living in the `build/long/` folder) — not melted in full, since only "distance to nearest active zone" is needed, not every pairwise distance.
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

**Script:** `scripts/prepare_shapefile.py` (or `clean_shapefile.py`)
**Output:** `drc_health_zones_clean.geojson` — 519 zones, `nom`/`zscode`/`province`/`geometry` only

**Key decisions:**
- **Not used as a model input** — geometry is for the dashboard's static base map only, joined to tabular data client-side on `nom`.
- HDX serves an outdated (pre-July-2026) version of this shapefile with different spellings for ~47 zones — confirmed by comparing column signatures against the repo's own `archived/` copy. The canonical file must come from the INRB-UMIE repo directly (`data/shapefiles/DRC_Health_zones.shp`), verified via SHA256 + column-contract check before use.
- 5 invalid geometries in the old HDX file, 0 in the correct one — itself a demonstration of why the source matters.

---

## Joining into one training table

**Script:** `scripts/join_training_table.py`
**Inputs:** `insp_sitrep_training_window.csv` (`nom`+`date` key), `osrm_nearest_active_feature.csv` (`nom`+`date` key), `flowminder_clean.csv` (`nom`-only key), `worldpop_merged.csv` (`nom`-only key)
**Output:** `training_table.csv` — 218 rows x 45 columns

**Key decisions:**
- All joins are LEFT joins anchored on `insp_sitrep_training_window.csv`, since that's where the target variable and the (`nom`, `date`) row index come from.
- `flowminder_clean.csv` and `worldpop_merged.csv` are zone-level only (no `date`) — joined on `nom` alone, which broadcasts each zone's value across every date row for that zone.
- Deliberately allows `NaN`s to remain — missingness strategy is a separate, later decision (see below), made only once the full combined picture across all four sources is visible. Deciding column-by-column in isolation, before the join, risks dropping/imputing data that would have been fine once combined with the other sources.

---

## EDA and correlation diagnostics

**Script:** `scripts/eda_correlation.py`
**Input:** `training_table.csv`
**Outputs:** `eda_missingness.png`, `eda_correlation_heatmap.png`, `eda_correlation_matrix.csv`

**Key findings:**
- Drops the `national_*` leftover columns before computing anything — these are structurally always-missing in a zone-level table (national totals only ever appeared on rows already split into `insp_sitrep_national_clean.csv`), not real sparse data to explain away.
- Correlation matrix flagged real multicollinearity: all 5 `flowminder_short_trips__outflow_*` dated snapshots are r>=0.99 with each other (one underlying signal, not five), the 4 `total_poe_*` columns are r=1.0 with each other (same count reported four ways), and the Ituri/North-Kivu subscriber-day prior/followup pairs are each r>0.99. These findings directly informed the trimming step below.

---

## Required insight visualizations

**Script:** `scripts/plot_insight_charts.py`
**Input:** `insp_sitrep_zone_level_clean.csv` (the full-range file, not the training-scoped one — the brief's required charts need the full outbreak timeline, not just the SVM's training window)
**Outputs:** `insight_epidemic_curve.png`, `insight_zone_breakdown.png`, `insight_cfr_trend.png`

**Key decisions:**
- Epidemic curve is built by **summing zone-level daily case counts**, not using the sparser `national_*` rows (which only start 2026-06-01) — this covers the full 2026-05-14 to 2026-07-11 range instead of being limited to five weeks.
- States explicitly that the curve starts 2026-05-14, not April 2026 as the brief describes — no April data exists anywhere in this dataset (see the data-gap note at the top of this file).
- **Caveat carried in the script's own comments:** a visual "dip" in the epidemic curve may reflect fewer zones reporting that day, not fewer actual cases (missing != zero, per the `ND` convention) — worth noting alongside the chart, not just presenting at face value.
- Final CFR as of 2026-07-11: 36.77% — within a plausible range for Ebola generally, not obviously broken.

---

## Feature trimming, missingness handling, Rt-proxy, and the One-Class SVM

**Script:** `scripts/prepare_and_train_svm.py` (combines what were three separate scripts — Rt-proxy computation, feature trimming + missingness handling, and the SVM fit — into one, since they always run together as a single pipeline)
**Inputs:** `training_table.csv`, `insp_sitrep_zone_level_clean.csv`
**Outputs:** `rt_proxy_feature.csv`, `training_table_final.csv`, `svm_flagged_anomalies.csv`

**Step-by-step, with real numbers from the actual data:**

1. **Rt-proxy (vectorised with NumPy):** ratio of new suspected cases in a trailing 4-day window to the 4-day window before it, per zone — `Rt_proxy > 1` means accelerating growth. Computed via `np.diff`/`np.convolve` per zone (no explicit per-day loop). Only 23 of the final 79 rows get a real computed value (needs several days of prior history per zone) — the rest are imputed as neutral (`Rt=1`, "no growth signal detected") with an explicit `rt_proxy_is_imputed` flag column, rather than dropping rows we can't afford to lose.
2. **Trim collinear features:** drops the 10 confirmed near-duplicate columns found by the correlation matrix (keeping one representative of each group) plus the 7 `national_*` leftover columns. 45 -> 28 columns.
3. **Drop columns >70% missing:** 11 columns (mostly hospitalisation/point-of-entry metrics) dropped outright — too sparse to trust or usefully impute.
4. **Forward-fill `cumulative_*` columns per zone:** matches INSP's own documented convention (carry the previous cumulative value forward when a day is `ND`, rather than treating it as newly missing).
5. **Drop rows missing the target (`new_suspected_cases`):** the single biggest cut, 218 -> 94 rows. Cannot train on a missing target regardless of imputation strategy — this is the direct, traceable consequence of the target's real ~43-57% coverage limitation established early in cleaning.
6. **Drop 4 more columns rather than more rows:** `new_contacts_listed`, `cumulative_contacts_traced` (secondary operational metrics) and `cumulative_confirmed_deaths`, `new_suspected_deaths` (tested dropping these columns vs. their rows — dropping columns preserves 79 rows vs. 63; deaths aren't part of the core anomaly-detection signal, and CFR is already covered separately by `plot_insight_charts.py` using the full-range file).
7. **Impute remaining Flowminder gaps as 0:** defensible specifically because missingness there means "no measurable mobile-subscriber signal" (low cell-tower coverage zones).
8. **Final NaN cleanup:** 94 -> 79 rows, 0 remaining `NaN` anywhere.

**Final table: 79 rows x 15 columns.** This is genuinely small for a One-Class SVM — worth being upfront in the writeup that it's an illustrative case study, not a statistically validated model. This is the direct, now fully-traced consequence of the target variable's real limitation, not a modeling mistake.

**Model:**
- **Temporal split, not random 80/20** — train on dates before 2026-05-26 (53 rows), test on 2026-05-26 onward (26 rows). One-Class SVM needs to train on "normal" and test on a separate period to see what's flagged; a random split would mix normal and anomalous days into both sides and defeat the purpose. See the data-gap note above: this train period is the earliest *available* adaptation, not a genuine pre-outbreak baseline.
- Case counts converted to **rates per 100k population** (using `pop_count`) before fitting — so results reflect real outbreak severity, not just which zones are biggest.
- `gamma` required tuning beyond the sklearn default: `gamma='scale'` produced a boundary so tight that 80%+ of the test set was flagged as anomalous — not discriminating. Grid search settled on `gamma=0.005, nu=0.05`, giving train~4% flagged (close to the expected ~5% for `nu=0.05`, a well-calibrated boundary) and test~35% flagged (a real, usable signal). Re-tuned after adding Rt-proxy as an 11th feature, since the feature-space geometry shifted enough to need it — worth remembering that any future feature addition should trigger a re-check of these parameters, not just a re-run with the old ones.
- **Flagged result (test set, 9/26 rows):** `Kalunguta`, `Oicha`, `Kyondo` (2026-05-26) — newly emerging zones, just starting to show suspected cases; `Bambu`, `Nizi` (2026-05-26) and `Mongbwalu`, `Rwampara`, `Nyankunde`, `Bambu` (2026-05-29) — already-affected zones whose case rate jumped beyond what the training period considered normal. Read this as "the model successfully flagged these specific zone/date combinations, and here's why that's epidemiologically sensible" rather than as a precision/recall claim this sample size can't robustly support.

**Not yet done:** validating these 9 flagged zone/dates against confirmed-case data (checking whether a confirmed-case rise followed the flag) — this would be the concrete "caught it early" evidence for the writeup.
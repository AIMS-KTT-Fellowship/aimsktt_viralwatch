from __future__ import annotations

import csv
import json
import re
import sqlite3
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = REPO_ROOT / "BDBV2026-Data" / "build" / "manifest.json"
DB_PATH = REPO_ROOT / "output" / "viralwatch_starter_schema.db"
REPORT_PATH = REPO_ROOT / "docs" / "viralwatch_starter_schema.md"


def load_manifest() -> dict:
    with MANIFEST_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return [dict(row) for row in reader]


def discover_importable_csvs() -> list[Path]:
    csv_roots = [
        REPO_ROOT / "BDBV2026-Data" / "build" / "long",
        REPO_ROOT / "BDBV2026-Data" / "build" / "matrix",
    ]
    paths: list[Path] = []
    seen: set[Path] = set()
    for root in csv_roots:
        if not root.exists():
            continue
        for path in root.rglob("*.csv"):
            if path in seen:
                continue
            seen.add(path)
            paths.append(path)

    data_root = REPO_ROOT / "BDBV2026-Data" / "data"
    if data_root.exists():
        for processed_path in data_root.rglob("processed/*.csv"):
            name = processed_path.name
            if not (
                name.endswith(".matrix.csv")
                or name.endswith("static_matrix.csv")
                or name == "process_log.csv"
            ):
                continue
            if processed_path in seen:
                continue
            seen.add(processed_path)
            paths.append(processed_path)

        for process_log in data_root.rglob("process_log.csv"):
            if process_log in seen:
                continue
            seen.add(process_log)
            paths.append(process_log)

        for top_level_csv in [
            data_root / "aliases.csv",
            data_root / "province_aliases.csv",
            data_root / "health_area_aliases.csv",
        ]:
            if top_level_csv.exists() and top_level_csv not in seen:
                seen.add(top_level_csv)
                paths.append(top_level_csv)
    return sorted(paths)


def sanitize_table_name(path: Path) -> str:
    relative = path.relative_to(REPO_ROOT).with_suffix("").as_posix()
    table_name = re.sub(r"[^A-Za-z0-9]+", "_", relative).strip("_")
    if not table_name:
        table_name = "csv"
    return f"csv_{table_name}"


def uniquify_headers(headers: list[str]) -> list[str]:
    unique_headers: list[str] = []
    used: dict[str, int] = {}
    for index, header in enumerate(headers):
        name = header.strip() if header else ""
        if not name:
            name = "row_name" if index == 0 else f"column_{index + 1}"
        name = re.sub(r"\s+", "_", name)
        name = re.sub(r"[^A-Za-z0-9_]+", "_", name).strip("_") or f"column_{index + 1}"
        count = used.get(name, 0)
        if count:
            unique_name = f"{name}_{count + 1}"
        else:
            unique_name = name
        used[name] = count + 1
        unique_headers.append(unique_name)
    return unique_headers


def read_csv_matrix(path: Path) -> tuple[list[str], list[list[str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        try:
            raw_headers = next(reader)
        except StopIteration:
            return [], []
        headers = uniquify_headers(raw_headers)
        rows: list[list[str]] = []
        for row in reader:
            if len(row) < len(headers):
                row = row + [""] * (len(headers) - len(row))
            elif len(row) > len(headers):
                row = row[: len(headers)]
            rows.append(row)
    return headers, rows


def insert_imported_csv(conn: sqlite3.Connection, path: Path) -> dict[str, str]:
    headers, rows = read_csv_matrix(path)
    table_name = sanitize_table_name(path)
    if not headers:
        conn.execute(f'CREATE TABLE IF NOT EXISTS "{table_name}" (source_path TEXT)')
        return {"table_name": table_name, "source_path": path.as_posix(), "rows": "0", "columns": "0"}

    column_defs = [f'"{header}" TEXT' for header in headers]
    conn.execute(f'CREATE TABLE IF NOT EXISTS "{table_name}" ({", ".join(column_defs)})')
    placeholders = ", ".join(["?"] * len(headers))
    column_list = ", ".join([f'"{header}"' for header in headers])
    conn.executemany(
        f'INSERT INTO "{table_name}" ({column_list}) VALUES ({placeholders})',
        rows,
    )
    return {
        "table_name": table_name,
        "source_path": path.as_posix(),
        "rows": str(len(rows)),
        "columns": str(len(headers)),
    }


def iso_or_blank(value: str | None) -> str:
    if not value:
        return ""
    return value


def build_dataset_rows(manifest: dict) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for dataset in manifest.get("datasets", []):
        rows.append(
            {
                "dataset_folder": dataset["folder"],
                "source": dataset.get("source", ""),
                "citation": dataset.get("citation", ""),
                "source_url": dataset.get("source_url", ""),
                "retrieved_on": dataset.get("retrieved_on", ""),
                "license": dataset.get("license", ""),
                "contact": dataset.get("contact", ""),
                "status": dataset.get("status", ""),
                "output_count": str(len(dataset.get("outputs", []))),
                "summary": dataset.get("source", ""),
                "notes": dataset.get("citation", ""),
            }
        )
    return rows


def build_file_rows(manifest: dict) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for dataset in manifest.get("datasets", []):
        folder = dataset["folder"]
        for output in dataset.get("outputs", []):
            contract_path = f"BDBV2026-Data/data/{folder}/processed/{output['file']}"
            published_path = output.get("long_csv") or output.get("matrix_csv") or ""
            if published_path:
                published_path = f"BDBV2026-Data/{published_path}"
            rows.append(
                {
                    "dataset_folder": folder,
                    "artifact_name": output["file"],
                    "artifact_kind": output.get("type", ""),
                    "metric": output.get("metric", ""),
                    "resolution": output.get("resolution", ""),
                    "contract_path": contract_path,
                    "published_path": published_path,
                    "in_geojson": str(bool(output.get("in_geojson", False))).lower(),
                    "zones_with_values": str(output.get("zones_with_values", "")),
                    "matrix_csv": output.get("matrix_csv", ""),
                    "long_csv": output.get("long_csv", ""),
                    "notes": json.dumps(output, ensure_ascii=True, sort_keys=True),
                }
            )
    return rows


def simple_vector_columns(value_name: str, *, value_type: str = "numeric", unit: str = "", notes: str = "") -> list[dict[str, str]]:
    return [
        {
            "ordinal": "1",
            "column_name": "nom",
            "data_type": "text",
            "expected_format": "Canonical DRC health-zone name; may also be DRC or a province label for roll-ups.",
            "unit": "",
            "description": "Geographic join key.",
            "allowed_values": "Nom, PROVINCE, DRC, or <Province> (province) where needed.",
            "notes": "All zone-grain tables join to the shapefile Nom column.",
        },
        {
            "ordinal": "2",
            "column_name": value_name,
            "data_type": value_type,
            "expected_format": "Scalar value; exact units and missing-value rules depend on the source folder.",
            "unit": unit,
            "description": notes or value_name,
            "allowed_values": "Non-negative integer, decimal in [0, 1], text narrative, or ND depending on the source.",
            "notes": notes,
        },
    ]


def dated_vector_columns(value_name: str, *, value_type: str = "numeric", unit: str = "", notes: str = "") -> list[dict[str, str]]:
    return [
        {
            "ordinal": "1",
            "column_name": "nom",
            "data_type": "text",
            "expected_format": "Canonical DRC health-zone name; may also be DRC or a province label for roll-ups.",
            "unit": "",
            "description": "Geographic join key.",
            "allowed_values": "Nom, PROVINCE, DRC, or <Province> (province) where needed.",
            "notes": "All zone-grain tables join to the shapefile Nom column.",
        },
        {
            "ordinal": "2",
            "column_name": "date",
            "data_type": "date",
            "expected_format": "ISO 8601 date string YYYY-MM-DD.",
            "unit": "",
            "description": "Report date, notification date, onset date, or cohort end date depending on the family.",
            "allowed_values": "YYYY-MM-DD",
            "notes": notes,
        },
        {
            "ordinal": "3",
            "column_name": value_name,
            "data_type": value_type,
            "expected_format": "Scalar value; exact units and missing-value rules depend on the source folder.",
            "unit": unit,
            "description": notes or value_name,
            "allowed_values": "Non-negative integer, decimal in [0, 1], text narrative, or ND depending on the source.",
            "notes": notes,
        },
    ]


def matrix_columns(*, dated: bool = False, notes: str = "") -> list[dict[str, str]]:
    columns = [
        {
            "ordinal": "1",
            "column_name": "nom",
            "data_type": "text",
            "expected_format": "Origin health-zone name from the canonical shapefile Nom field.",
            "unit": "",
            "description": "Origin row key.",
            "allowed_values": "Canonical zone names; duplicates may be retained in OSRM because the source shapefile has repeated names.",
            "notes": notes,
        }
    ]
    if dated:
        columns.append(
            {
                "ordinal": "2",
                "column_name": "date",
                "data_type": "date",
                "expected_format": "ISO 8601 date string YYYY-MM-DD or YYYY-MM-01 for month snapshots.",
                "unit": "",
                "description": "Snapshot date for the matrix row.",
                "allowed_values": "YYYY-MM-DD",
                "notes": notes,
            }
        )
    columns.append(
        {
            "ordinal": str(len(columns) + 1),
            "column_name": "destination_zone_columns[*]",
            "data_type": "numeric",
            "expected_format": "Wide destination-zone columns named by canonical zone labels.",
            "unit": "depends_on_family",
            "description": "One column per destination zone; cell values are directed flows or distances.",
            "allowed_values": "Non-negative integers, minutes, kilometres, or NA/redacted values depending on the family.",
            "notes": notes,
        }
    )
    return columns


def build_column_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []

    def add(path: str, columns: list[dict[str, str]], dataset_folder: str, notes: str = "") -> None:
        for col in columns:
            rows.append(
                {
                    "dataset_folder": dataset_folder,
                    "artifact_path": path,
                    "ordinal": col["ordinal"],
                    "column_name": col["column_name"],
                    "data_type": col["data_type"],
                    "expected_format": col["expected_format"],
                    "unit": col["unit"],
                    "description": col["description"],
                    "allowed_values": col["allowed_values"],
                    "notes": col["notes"] or notes,
                }
            )

    add(
        "BDBV2026-Data/data/shapefiles/DRC_Health_zones.shp",
        [
            {
                "ordinal": "1",
                "column_name": "Nom",
                "data_type": "text",
                "expected_format": "Canonical health-zone name; repeated names exist for Bili and Lubunga.",
                "unit": "",
                "description": "Primary health-zone label.",
                "allowed_values": "Text; canonical zone names.",
                "notes": "Canonical zone key used by most processed tables.",
            },
            {
                "ordinal": "2",
                "column_name": "PROVINCE",
                "data_type": "text",
                "expected_format": "Canonical province name.",
                "unit": "",
                "description": "Province membership for the zone.",
                "allowed_values": "Text; province names.",
                "notes": "Used for province roll-ups and provincial narratives.",
            },
            {
                "ordinal": "3",
                "column_name": "ZSCode",
                "data_type": "text",
                "expected_format": "Unique administrative code such as CD8308ZS03.",
                "unit": "",
                "description": "Unique health-zone code.",
                "allowed_values": "Pattern CD####ZS##.",
                "notes": "Best strict join key when names collide.",
            },
            {
                "ordinal": "4",
                "column_name": "geometry",
                "data_type": "geometry",
                "expected_format": "Polygon or multipolygon geometry in the source CRS.",
                "unit": "",
                "description": "Health-zone boundary geometry.",
                "allowed_values": "Valid polygons.",
                "notes": "Base geometry layer for the whole repository.",
            },
        ],
        "shapefiles",
    )

    add(
        "BDBV2026-Data/data/aliases.csv",
        [
            {"ordinal": "1", "column_name": "observed_name", "data_type": "text", "expected_format": "Spelling found in a source dataset.", "unit": "", "description": "Observed label to normalise.", "allowed_values": "Text", "notes": "Used by zone-name canonicalisation."},
            {"ordinal": "2", "column_name": "canonical_nom", "data_type": "text", "expected_format": "Canonical health-zone name.", "unit": "", "description": "Resolved health-zone name.", "allowed_values": "Text", "notes": "Join key for zone-grain tables."},
            {"ordinal": "3", "column_name": "source_dataset", "data_type": "text", "expected_format": "Dataset token that produced the alias.", "unit": "", "description": "Source family for the alias.", "allowed_values": "Text", "notes": "Example values: epi, insp_sitrep, shapefile_migration_2026-07."},
            {"ordinal": "4", "column_name": "notes", "data_type": "text", "expected_format": "Free-text explanation.", "unit": "", "description": "Reason for the alias.", "allowed_values": "Text", "notes": "Lookup table for reconciliation."},
        ],
        "aliases",
    )

    add(
        "BDBV2026-Data/data/province_aliases.csv",
        [
            {"ordinal": "1", "column_name": "observed_name", "data_type": "text", "expected_format": "Province spelling used by source material.", "unit": "", "description": "Observed province label.", "allowed_values": "Text", "notes": "Used for province roll-ups."},
            {"ordinal": "2", "column_name": "canonical_province", "data_type": "text", "expected_format": "Canonical province name.", "unit": "", "description": "Resolved province label.", "allowed_values": "Text", "notes": "Join key for provincial rows."},
        ],
        "province_aliases",
    )

    add(
        "BDBV2026-Data/data/health_area_aliases.csv",
        [
            {"ordinal": "1", "column_name": "observed_name", "data_type": "text", "expected_format": "Observed zone spelling.", "unit": "", "description": "Observed zone label.", "allowed_values": "Text", "notes": "Current file is empty in this snapshot."},
            {"ordinal": "2", "column_name": "canonical_nom", "data_type": "text", "expected_format": "Canonical health-zone name.", "unit": "", "description": "Resolved health-zone name.", "allowed_values": "Text", "notes": "Current file is empty in this snapshot."},
            {"ordinal": "3", "column_name": "source_dataset", "data_type": "text", "expected_format": "Dataset token.", "unit": "", "description": "Source family.", "allowed_values": "Text", "notes": "Current file is empty in this snapshot."},
            {"ordinal": "4", "column_name": "notes", "data_type": "text", "expected_format": "Free-text note.", "unit": "", "description": "Reason for the alias.", "allowed_values": "Text", "notes": "Current file is empty in this snapshot."},
        ],
        "health_area_aliases",
    )

    # Simple vector families.
    for path, value_name, unit, notes, folder in [
        ("BDBV2026-Data/data/worldpop/processed/worldpop__pop_count__static.csv", "pop_count", "people", "WorldPop population count, 2025 aggregate.", "worldpop"),
        ("BDBV2026-Data/data/worldpop/processed/worldpop__pop_density__static.csv", "pop_density", "people per km^2", "WorldPop population density, 2025 aggregate.", "worldpop"),
        ("BDBV2026-Data/data/gdp_pc/processed/gdp_pc__gdp_pc__static.csv", "gdp_pc", "2017 international USD per capita", "GDP per capita PPP, 2022 snapshot.", "gdp_pc"),
        ("BDBV2026-Data/data/fao_lccs/processed/fao_lccs__urban_fraction__static.csv", "urban_fraction", "proportion", "Urban fraction from FAO LCCS class 190, 2022 snapshot.", "fao_lccs"),
        ("BDBV2026-Data/data/grid3_healthsites/processed/grid3_healthsites__healthsite_count__static.csv", "healthsite_count", "sites", "GRID3 facility count.", "grid3_healthsites"),
        ("BDBV2026-Data/data/grid3_healthsites/processed/grid3_healthsites__healthsite_density__static.csv", "healthsite_density", "sites per km^2", "GRID3 facility density.", "grid3_healthsites"),
        ("BDBV2026-Data/data/healthsites_io/processed/healthsites_io__healthsite_count__static.csv", "healthsite_count", "sites", "Healthsites.io facility count after filtering.", "healthsites_io"),
        ("BDBV2026-Data/data/healthsites_io/processed/healthsites_io__healthsite_density__static.csv", "healthsite_density", "sites per km^2", "Healthsites.io facility density after filtering.", "healthsites_io"),
        ("BDBV2026-Data/data/refugee_sites/processed/refugee_sites__sites__static.csv", "sites", "sites", "Refugee / IDP site count.", "refugee_sites"),
        ("BDBV2026-Data/data/cross-border-movements/processed/cross_border__poe_passengers__static.csv", "n_poes", "count", "Number of PoEs assigned to the zone.", "cross-border-movements"),
    ]:
        add(path, simple_vector_columns(value_name, unit=unit, notes=notes), folder)

    add(
        "BDBV2026-Data/data/epi_mve_inrb_app/processed/epi_mve_inrb_app__recorded_cases__daily.csv",
        dated_vector_columns("recorded_cases", notes="Daily recorded case counts from the INRB MVE app line list."),
        "epi_mve_inrb_app",
    )

    add(
        "BDBV2026-Data/data/aggregated_insp_linelist/processed/aggregated_insp_linelist__confirmed_cases_onset__daily.csv",
        dated_vector_columns("confirmed_cases_onset", notes="Province-level confirmed cases by symptom onset date."),
        "aggregated_insp_linelist",
    )
    add(
        "BDBV2026-Data/data/aggregated_insp_linelist/processed/aggregated_insp_linelist__national_confirmed_cases_onset__daily.csv",
        dated_vector_columns("national_confirmed_cases_onset", notes="National confirmed cases by symptom onset date; nom = DRC."),
        "aggregated_insp_linelist",
    )

    add(
        "BDBV2026-Data/data/epi/processed/epi__cases__weekly.csv",
        [
            {"ordinal": "1", "column_name": "nom", "data_type": "text", "expected_format": "Canonical health-zone name.", "unit": "", "description": "Health-zone join key.", "allowed_values": "Canonical zone names; DRC not used here.", "notes": "WHO weekly external sitrep extract."},
            {"ordinal": "2", "column_name": "date", "data_type": "date", "expected_format": "ISO 8601 week report date, stored as YYYY-MM-DD.", "unit": "", "description": "WHO report date.", "allowed_values": "YYYY-MM-DD", "notes": "Weekly time grain."},
            {"ordinal": "3", "column_name": "suspected_cases", "data_type": "integer", "expected_format": "Non-negative integer count.", "unit": "cases", "description": "Suspected cases.", "allowed_values": ">= 0 or blank", "notes": "Counts per zone and week."},
            {"ordinal": "4", "column_name": "suspected_deaths", "data_type": "integer", "expected_format": "Non-negative integer count.", "unit": "deaths", "description": "Suspected deaths.", "allowed_values": ">= 0 or blank", "notes": "Counts per zone and week."},
            {"ordinal": "5", "column_name": "confirmed_cases", "data_type": "integer", "expected_format": "Non-negative integer count.", "unit": "cases", "description": "Confirmed cases.", "allowed_values": ">= 0 or blank", "notes": "Counts per zone and week."},
            {"ordinal": "6", "column_name": "confirmed_deaths", "data_type": "integer", "expected_format": "Non-negative integer count.", "unit": "deaths", "description": "Confirmed deaths.", "allowed_values": ">= 0 or blank", "notes": "Counts per zone and week."},
        ],
        "epi",
    )

    add(
        "BDBV2026-Data/data/testing_capacity/processed/africa_cdc__testing_capacity__static_matrix.csv",
        [
            {"ordinal": "1", "column_name": "nom", "data_type": "text", "expected_format": "Canonical health-zone name.", "unit": "", "description": "Zone name.", "allowed_values": "Canonical zone names.", "notes": "Wide snapshot file."},
            {"ordinal": "2", "column_name": "date", "data_type": "date", "expected_format": "Snapshot date in ISO format.", "unit": "", "description": "Snapshot date.", "allowed_values": "YYYY-MM-DD", "notes": "Wide snapshot file."},
            {"ordinal": "3", "column_name": "PCR_machines", "data_type": "integer", "expected_format": "Non-negative integer count.", "unit": "machines", "description": "Planned PCR machines.", "allowed_values": ">= 0", "notes": "Wide snapshot file."},
            {"ordinal": "4", "column_name": "PCR_tests", "data_type": "integer", "expected_format": "Non-negative integer count.", "unit": "tests", "description": "Planned PCR test throughput.", "allowed_values": ">= 0", "notes": "Wide snapshot file."},
        ],
        "testing_capacity",
    )
    add(
        "BDBV2026-Data/data/testing_capacity/processed/testing_capacity__pcr_machines__static.csv",
        simple_vector_columns("PCR_machines", unit="machines", notes="Contract vector extracted from the wide test-capacity snapshot."),
        "testing_capacity",
    )
    add(
        "BDBV2026-Data/data/testing_capacity/processed/testing_capacity__pcr_tests__static.csv",
        simple_vector_columns("PCR_tests", unit="tests", notes="Contract vector extracted from the wide test-capacity snapshot."),
        "testing_capacity",
    )

    add(
        "BDBV2026-Data/data/genomic_surveillance/processed/genomic_surveillance__sequence_count__static.csv",
        simple_vector_columns("sequence_count", unit="sequences", notes="Count of sequenced genomes per health zone."),
        "genomic_surveillance",
    )

    add(
        "BDBV2026-Data/data/genomic_surveillance/raw/bia_fasta_metadata_consensus_v0.1.tsv",
        [
            {"ordinal": "1", "column_name": "taxa", "data_type": "text", "expected_format": "Sequence identifier from FASTA headers.", "unit": "", "description": "Genome sequence ID.", "allowed_values": "Text", "notes": "One row per sequenced genome."},
            {"ordinal": "2", "column_name": "lab_location", "data_type": "text", "expected_format": "Sequencing lab name such as Bunia or Kinshasa.", "unit": "", "description": "Lab location.", "allowed_values": "Text", "notes": "Consensus metadata."},
            {"ordinal": "3", "column_name": "match_scope", "data_type": "text", "expected_format": "both, lab_only, dhis_only, or none.", "unit": "", "description": "Source agreement scope.", "allowed_values": "both | lab_only | dhis_only | none", "notes": "Consensus metadata."},
            {"ordinal": "4", "column_name": "province", "data_type": "text", "expected_format": "Consensus province name.", "unit": "", "description": "Province.", "allowed_values": "Text", "notes": "Consensus metadata."},
            {"ordinal": "5", "column_name": "health_zone", "data_type": "text", "expected_format": "Consensus health-zone name.", "unit": "", "description": "Health zone.", "allowed_values": "Text", "notes": "Resolved upstream before export."},
            {"ordinal": "6", "column_name": "collection_date", "data_type": "date", "expected_format": "ISO date.", "unit": "", "description": "Sample collection date.", "allowed_values": "YYYY-MM-DD", "notes": "Consensus metadata."},
            {"ordinal": "7", "column_name": "sex", "data_type": "text", "expected_format": "Sex category from the upstream table.", "unit": "", "description": "Sex.", "allowed_values": "Text", "notes": "Consensus metadata."},
            {"ordinal": "8", "column_name": "age", "data_type": "text", "expected_format": "Age as recorded upstream.", "unit": "", "description": "Age.", "allowed_values": "Text", "notes": "Consensus metadata."},
        ],
        "genomic_surveillance",
    )
    add(
        "BDBV2026-Data/data/genomic_surveillance/process_log.csv",
        [
            {"ordinal": "1", "column_name": "taxa", "data_type": "text", "expected_format": "Sequence identifier.", "unit": "", "description": "Genome sequence ID.", "allowed_values": "Text", "notes": "Audit trail."},
            {"ordinal": "2", "column_name": "health_zone", "data_type": "text", "expected_format": "Original health-zone name from the consensus table.", "unit": "", "description": "Source zone.", "allowed_values": "Text or blank", "notes": "Audit trail."},
            {"ordinal": "3", "column_name": "province", "data_type": "text", "expected_format": "Source province.", "unit": "", "description": "Source province.", "allowed_values": "Text or blank", "notes": "Audit trail."},
            {"ordinal": "4", "column_name": "resolved_nom", "data_type": "text", "expected_format": "Canonical zone name after alias resolution.", "unit": "", "description": "Resolved health-zone name.", "allowed_values": "Canonical zone names or blank", "notes": "Audit trail."},
            {"ordinal": "5", "column_name": "status", "data_type": "text", "expected_format": "assigned, unresolved, or no_zone.", "unit": "", "description": "Resolution status.", "allowed_values": "assigned | unresolved | no_zone", "notes": "Audit trail."},
        ],
        "genomic_surveillance",
    )

    add(
        "BDBV2026-Data/data/osrm/processed/osrm__travel_time__static.csv",
        matrix_columns(notes="Directed travel-time matrix; first column is logical row name and destination columns are wide zone labels."),
        "osrm",
    )
    add(
        "BDBV2026-Data/data/osrm/processed/osrm__road_distance__static.csv",
        matrix_columns(notes="Directed road-distance matrix; first column is logical row name and destination columns are wide zone labels."),
        "osrm",
    )

    add(
        "BDBV2026-Data/data/IDP/processed/idp__individuals__static.matrix.csv",
        matrix_columns(notes="Directed IDP relocation matrix; wide OD layout."),
        "IDP",
    )
    add(
        "BDBV2026-Data/data/IDP/processed/idp__individuals__weekly.matrix.csv",
        matrix_columns(dated=True, notes="Weekly IDP relocation matrix; date is week_start or normalised week date."),
        "IDP",
    )
    add(
        "BDBV2026-Data/data/IDP/processed/idp__individuals__monthly.matrix.csv",
        matrix_columns(dated=True, notes="Monthly IDP relocation matrix; date is month start (YYYY-MM-01)."),
        "IDP",
    )

    add(
        "BDBV2026-Data/data/flowminder/processed/flowminder__outflow__static.matrix.csv",
        matrix_columns(notes="March 2026 provincial PDF-derived outflow matrix; redacted cells may be blank."),
        "flowminder",
    )
    add(
        "BDBV2026-Data/data/flowminder/processed/flowminder__inflow__static.matrix.csv",
        matrix_columns(notes="March 2026 provincial PDF-derived inflow matrix; transpose of outflow."),
        "flowminder",
    )
    add(
        "BDBV2026-Data/data/flowminder/processed/flowminder__outflow_202604__static.matrix.csv",
        matrix_columns(notes="April 2026 national OD matrix; point estimate est_flows_2026_04."),
        "flowminder",
    )
    add(
        "BDBV2026-Data/data/flowminder/processed/flowminder__inflow_202604__static.matrix.csv",
        matrix_columns(notes="April 2026 national OD matrix; transpose of outflow_202604."),
        "flowminder",
    )

    add(
        "BDBV2026-Data/data/flowminder_short_trips/processed/flowminder_short_trips__outflow_20260524__static.matrix.csv",
        matrix_columns(notes="Annex A proportion snapshot matrix; origin rows repeat the cohort profile."),
        "flowminder_short_trips",
    )
    add(
        "BDBV2026-Data/data/flowminder_short_trips/processed/flowminder_short_trips__ituri_subscriber_days_followup_20260608__static.matrix.csv",
        matrix_columns(notes="HDX cohort subscriber-day matrix; origin rows repeat the cohort profile."),
        "flowminder_short_trips",
    )
    add(
        "BDBV2026-Data/data/flowminder_short_trips/processed/flowminder_short_trips__outflow_20260524__static.csv",
        simple_vector_columns("outflow_20260524", unit="percent", notes="Long vector derived from the matrix for dashboard embedding."),
        "flowminder_short_trips",
    )

    add(
        "BDBV2026-Data/data/insp_sitrep/processed/insp_sitrep__cumulative_confirmed_cases__daily.csv",
        dated_vector_columns("cumulative_confirmed_cases", notes="SitRep quantitative health-zone metric; ND indicates not reported."),
        "insp_sitrep",
    )
    add(
        "BDBV2026-Data/data/insp_sitrep/processed/insp_sitrep__national_cumulative_confirmed_cases__daily.csv",
        dated_vector_columns("national_cumulative_confirmed_cases", notes="National SitRep metric; nom = DRC."),
        "insp_sitrep",
    )
    add(
        "BDBV2026-Data/data/public_health_response/processed/public_health_response__national_epidemiological_coordination__daily.csv",
        dated_vector_columns("activity_text", value_type="text", notes="Narrative public-health-response text; value column varies by pillar and scope."),
        "public_health_response",
    )

    return rows


def build_relationship_rows() -> list[dict[str, str]]:
    return [
        {
            "parent_entity": "BDBV2026-Data/data/shapefiles/DRC_Health_zones.shp",
            "child_entity": "Zone-grain vector tables",
            "join_key": "Nom <-> nom",
            "cardinality": "1-to-many",
            "relation_kind": "canonical_zone_dimension",
            "notes": "Most processed vectors attach to one canonical health-zone row through nom.",
        },
        {
            "parent_entity": "BDBV2026-Data/data/shapefiles/DRC_Health_zones.shp",
            "child_entity": "Province-grain outputs",
            "join_key": "PROVINCE <-> nom",
            "cardinality": "1-to-many",
            "relation_kind": "province_rollup",
            "notes": "Province rows are broadcast to all zones in the province during the build.",
        },
        {
            "parent_entity": "BDBV2026-Data/data/shapefiles/DRC_Health_zones.shp",
            "child_entity": "National roll-ups",
            "join_key": "nom = DRC",
            "cardinality": "1-to-many",
            "relation_kind": "national_rollup",
            "notes": "National files are stored once and applied to every zone in GeoJSON embedding.",
        },
        {
            "parent_entity": "BDBV2026-Data/data/shapefiles/DRC_Health_zones.shp",
            "child_entity": "Matrix tables",
            "join_key": "Nom labels on rows and columns",
            "cardinality": "many-to-many",
            "relation_kind": "od_matrix",
            "notes": "Matrices are zone-by-zone and use canonical zone labels as both origins and destinations.",
        },
        {
            "parent_entity": "BDBV2026-Data/data/aliases.csv",
            "child_entity": "All canonical zone-grain sources",
            "join_key": "observed_name -> canonical_nom",
            "cardinality": "many-to-one",
            "relation_kind": "name_normalization",
            "notes": "Use this lookup for spelling variants and legacy names.",
        },
        {
            "parent_entity": "BDBV2026-Data/data/province_aliases.csv",
            "child_entity": "Province-grain sources",
            "join_key": "observed_name -> canonical_province",
            "cardinality": "many-to-one",
            "relation_kind": "province_normalization",
            "notes": "Use this lookup for provincial spellings in sitreps and aggregates.",
        },
        {
            "parent_entity": "BDBV2026-Data/data/health_area_aliases.csv",
            "child_entity": "Future zone-grain lookups",
            "join_key": "observed_name -> canonical_nom",
            "cardinality": "many-to-one",
            "relation_kind": "reserved_lookup",
            "notes": "The file is currently empty but reserved for future normalization entries.",
        },
    ]


def build_manifest_snapshot(manifest: dict) -> list[dict[str, str]]:
    return [
        {
            "built_at": manifest.get("built_at", ""),
            "commit_hash": manifest.get("commit", ""),
            "shapefile": manifest.get("shapefile", ""),
            "n_features": str(manifest.get("n_features", "")),
        }
    ]


def initialize_database(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        PRAGMA journal_mode = WAL;

        CREATE TABLE manifest_snapshot (
            built_at TEXT,
            commit_hash TEXT,
            shapefile TEXT,
            n_features INTEGER
        );

        CREATE TABLE dataset_catalog (
            dataset_folder TEXT PRIMARY KEY,
            source TEXT,
            citation TEXT,
            source_url TEXT,
            retrieved_on TEXT,
            license TEXT,
            contact TEXT,
            status TEXT,
            output_count INTEGER,
            summary TEXT,
            notes TEXT
        );

        CREATE TABLE file_catalog (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dataset_folder TEXT,
            artifact_name TEXT,
            artifact_kind TEXT,
            metric TEXT,
            resolution TEXT,
            contract_path TEXT,
            published_path TEXT,
            in_geojson INTEGER,
            zones_with_values TEXT,
            matrix_csv TEXT,
            long_csv TEXT,
            notes TEXT,
            FOREIGN KEY(dataset_folder) REFERENCES dataset_catalog(dataset_folder)
        );

        CREATE TABLE column_catalog (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dataset_folder TEXT,
            artifact_path TEXT,
            ordinal INTEGER,
            column_name TEXT,
            data_type TEXT,
            expected_format TEXT,
            unit TEXT,
            description TEXT,
            allowed_values TEXT,
            notes TEXT,
            FOREIGN KEY(dataset_folder) REFERENCES dataset_catalog(dataset_folder)
        );

        CREATE TABLE relationship_catalog (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            parent_entity TEXT,
            child_entity TEXT,
            join_key TEXT,
            cardinality TEXT,
            relation_kind TEXT,
            notes TEXT
        );

        CREATE TABLE alias_lookup (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lookup_type TEXT,
            observed_name TEXT,
            canonical_name TEXT,
            source_dataset TEXT,
            notes TEXT
        );

        CREATE TABLE imported_table_catalog (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            table_name TEXT,
            source_path TEXT,
            rows INTEGER,
            columns INTEGER
        );
        """
    )


def populate_database(conn: sqlite3.Connection, manifest: dict) -> None:
    conn.executemany(
        "INSERT INTO manifest_snapshot (built_at, commit_hash, shapefile, n_features) VALUES (:built_at, :commit_hash, :shapefile, :n_features)",
        build_manifest_snapshot(manifest),
    )

    dataset_rows = build_dataset_rows(manifest)
    conn.executemany(
        """
        INSERT INTO dataset_catalog (
            dataset_folder, source, citation, source_url, retrieved_on, license,
            contact, status, output_count, summary, notes
        ) VALUES (
            :dataset_folder, :source, :citation, :source_url, :retrieved_on, :license,
            :contact, :status, :output_count, :summary, :notes
        )
        """,
        dataset_rows,
    )

    file_rows = build_file_rows(manifest)
    conn.executemany(
        """
        INSERT INTO file_catalog (
            dataset_folder, artifact_name, artifact_kind, metric, resolution,
            contract_path, published_path, in_geojson, zones_with_values,
            matrix_csv, long_csv, notes
        ) VALUES (
            :dataset_folder, :artifact_name, :artifact_kind, :metric, :resolution,
            :contract_path, :published_path, :in_geojson, :zones_with_values,
            :matrix_csv, :long_csv, :notes
        )
        """,
        file_rows,
    )

    column_rows = build_column_rows()
    conn.executemany(
        """
        INSERT INTO column_catalog (
            dataset_folder, artifact_path, ordinal, column_name, data_type,
            expected_format, unit, description, allowed_values, notes
        ) VALUES (
            :dataset_folder, :artifact_path, :ordinal, :column_name, :data_type,
            :expected_format, :unit, :description, :allowed_values, :notes
        )
        """,
        column_rows,
    )

    conn.executemany(
        """
        INSERT INTO relationship_catalog (
            parent_entity, child_entity, join_key, cardinality, relation_kind, notes
        ) VALUES (
            :parent_entity, :child_entity, :join_key, :cardinality, :relation_kind, :notes
        )
        """,
        build_relationship_rows(),
    )

    alias_rows = []
    for row in load_csv_rows(REPO_ROOT / "BDBV2026-Data" / "data" / "aliases.csv"):
        alias_rows.append(
            {
                "lookup_type": "zone",
                "observed_name": row.get("observed_name", ""),
                "canonical_name": row.get("canonical_nom", ""),
                "source_dataset": row.get("source_dataset", ""),
                "notes": row.get("notes", ""),
            }
        )
    for row in load_csv_rows(REPO_ROOT / "BDBV2026-Data" / "data" / "province_aliases.csv"):
        alias_rows.append(
            {
                "lookup_type": "province",
                "observed_name": row.get("observed_name", ""),
                "canonical_name": row.get("canonical_province", ""),
                "source_dataset": "province_aliases",
                "notes": "",
            }
        )
    for row in load_csv_rows(REPO_ROOT / "BDBV2026-Data" / "data" / "health_area_aliases.csv"):
        alias_rows.append(
            {
                "lookup_type": "zone",
                "observed_name": row.get("observed_name", ""),
                "canonical_name": row.get("canonical_nom", ""),
                "source_dataset": row.get("source_dataset", ""),
                "notes": row.get("notes", ""),
            }
        )

    if alias_rows:
        conn.executemany(
            """
            INSERT INTO alias_lookup (
                lookup_type, observed_name, canonical_name, source_dataset, notes
            ) VALUES (
                :lookup_type, :observed_name, :canonical_name, :source_dataset, :notes
            )
            """,
            alias_rows,
        )

    imported_rows = []
    for csv_path in discover_importable_csvs():
        imported_rows.append(insert_imported_csv(conn, csv_path))

    if imported_rows:
        conn.executemany(
            """
            INSERT INTO imported_table_catalog (
                table_name, source_path, rows, columns
            ) VALUES (
                :table_name, :source_path, :rows, :columns
            )
            """,
            imported_rows,
        )


def generate_markdown_report(manifest: dict, imported_rows: list[dict[str, str]]) -> str:
    dataset_rows = build_dataset_rows(manifest)
    file_rows = build_file_rows(manifest)

    lines = [
        "# ViralWatch starter schema",
        "",
        "This file is a metadata-first starter schema for the BDBV2026 data repo. It is designed to seed an analysis database without reading the raw analytical CSV contents.",
        "",
        "## Hierarchy",
        "",
        "1. `data/shapefiles/DRC_Health_zones.shp` is the canonical geometry and zone dimension.",
        "2. `Nom` is the main health-zone join key.",
        "3. `PROVINCE` is the province parent for zone roll-ups.",
        "4. `DRC` is the national roll-up token for province and national files.",
        "5. `aliases.csv` and `province_aliases.csv` normalize spelling variants before joins.",
        f"6. SQLite now loads {len(imported_rows)} CSV tables from canonical build outputs, matrix outputs, and small lookup files.",
        "",
        "## Dataset catalog",
        "",
        "| Folder | Status | Retrieved | Outputs | Source |",
        "|---|---|---|---:|---|",
    ]
    for row in dataset_rows:
        lines.append(
            f"| {row['dataset_folder']} | {row['status']} | {row['retrieved_on']} | {row['output_count']} | {row['source']} |"
        )

    lines.extend([
        "",
        "## File catalog",
        "",
        "| Dataset | Contract path | Published path | Kind | Columns / value shape |",
        "|---|---|---|---|---|",
    ])
    for row in file_rows:
        value_shape = "wide matrix" if row["artifact_kind"] == "matrix" else "vector"
        lines.append(
            f"| {row['dataset_folder']} | {row['contract_path']} | {row['published_path'] or '-'} | {row['artifact_kind']} | {value_shape} |"
        )

    lines.extend([
        "",
        "## SQLite load",
        "",
        f"- Imported CSV tables: {len(imported_rows)}",
        "- Table names are derived from the source path and sanitized for SQLite.",
        "- Vector tables stay as their own loaded tables; matrix CSVs are loaded as wide tables.",
        "",
    ])

    lines.extend([
        "",
        "## Key column rules",
        "",
        "- `nom`: canonical health-zone name, or `DRC` / province roll-up where the source is not zone-grain.",
        "- `date`: ISO `YYYY-MM-DD` unless the file is a matrix snapshot, where monthly files use `YYYY-MM-01`.",
        "- Count fields: non-negative integers, sometimes `ND` or blank when not reported.",
        "- Proportion fields: decimals in `[0, 1]`.",
        "- Text narrative fields: free text extracted from SitRep narrative sections.",
        "- OD matrices: first logical column is the origin zone, destination columns are canonical zone names.",
        "",
        "## Relations",
        "",
        "- Zone-grain vectors join to `Nom`.",
        "- Province-grain rows join to `PROVINCE` and are broadcast to each health zone in the province.",
        "- National rows use `DRC` and are broadcast across all zones during GeoJSON build.",
        "- OD matrices are many-to-many between health zones, not one-to-many fact tables.",
        "",
        "## Notes",
        "",
        "- The database is a starter schema and metadata index, not a replacement for the analytical fact tables.",
        "- Use `ZSCode` for strict joins where zone names collide or duplicate.",
        "- `Bili` and `Lubunga` are the main duplicate-name edge cases in the base shapefile.",
        "",
    ])
    return "\n".join(lines)


def main() -> None:
    manifest = load_manifest()
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    if DB_PATH.exists():
        DB_PATH.unlink()

    with sqlite3.connect(DB_PATH) as conn:
        initialize_database(conn)
        populate_database(conn, manifest)
        conn.commit()

    imported_rows = [{"source_path": csv_path.as_posix()} for csv_path in discover_importable_csvs()]
    REPORT_PATH.write_text(generate_markdown_report(manifest, imported_rows), encoding="utf-8")
    print(f"Wrote {DB_PATH}")
    print(f"Wrote {REPORT_PATH}")


if __name__ == "__main__":
    main()
from __future__ import annotations

import csv
import json
import re
import sqlite3
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = REPO_ROOT / "BDBV2026-Data" / "build" / "manifest.json"
GEOJSON_PATH = REPO_ROOT / "BDBV2026-Data" / "build" / "drc_health_zones.geojson"
DB_PATH = REPO_ROOT / "output" / "viralwatch_star_schema_fact.db"
REPORT_PATH = REPO_ROOT / "docs" / "viralwatch_star_schema.md"


STATIC_SNAPSHOT_DEFAULTS = {
    "worldpop": "2025-01-01",
    "gdp_pc": "2022-01-01",
    "ccvi": "2024-01-01",
    "fao_lccs": "2022-01-01",
    "grid3_healthsites": "2025-01-01",
}


def load_manifest() -> dict:
    with MANIFEST_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_geojson_geographies() -> tuple[list[dict[str, str]], list[str], dict[str, str]]:
    with GEOJSON_PATH.open("r", encoding="utf-8") as handle:
        geojson = json.load(handle)

    zone_rows: list[dict[str, str]] = []
    zone_order: list[str] = []
    zone_lookup: dict[str, str] = {}
    seen_provinces: set[str] = set()
    province_rows: list[dict[str, str]] = []

    features = geojson.get("features", [])
    for index, feature in enumerate(features, start=1):
        props = feature.get("properties", {})
        nom = str(props.get("nom", props.get("Nom", ""))).strip()
        province = str(props.get("province", props.get("PROVINCE", ""))).strip()
        zscode = str(props.get("zscode", props.get("ZSCode", ""))).strip()
        if not nom or not province or not zscode:
            continue

        zone_id = f"zone:{zscode}"
        parent_id = f"province:{province}"
        zone_rows.append(
            {
                "geog_id": zone_id,
                "geog_level": "zone",
                "geog_name": nom,
                "province_name": province,
                "zscode": zscode,
                "parent_geog_id": parent_id,
                "sort_order": str(index),
            }
        )
        zone_order.append(zone_id)
        zone_lookup.setdefault(nom, zone_id)
        zone_lookup.setdefault(f"{nom} ({province})", zone_id)

        if province not in seen_provinces:
            seen_provinces.add(province)
            province_rows.append(
                {
                    "geog_id": parent_id,
                    "geog_level": "province",
                    "geog_name": province,
                    "province_name": province,
                    "zscode": "",
                    "parent_geog_id": "national:DRC",
                    "sort_order": str(len(province_rows) + 1),
                }
            )

    national_row = {
        "geog_id": "national:DRC",
        "geog_level": "national",
        "geog_name": "DRC",
        "province_name": "",
        "zscode": "",
        "parent_geog_id": "",
        "sort_order": "1",
    }

    geography_rows = [national_row] + province_rows + zone_rows

    for province_row in province_rows:
        zone_lookup.setdefault(province_row["geog_name"], province_row["geog_id"])
        zone_lookup.setdefault(f"{province_row['geog_name']} (province)", province_row["geog_id"])
    zone_lookup.setdefault("DRC", "national:DRC")

    return geography_rows, zone_order, zone_lookup


def load_csv_dict_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def load_csv_matrix(path: Path) -> tuple[list[str], list[list[str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        try:
            headers = next(reader)
        except StopIteration:
            return [], []
        rows: list[list[str]] = []
        for row in reader:
            if len(row) < len(headers):
                row = row + [""] * (len(headers) - len(row))
            rows.append(row[: len(headers)])
    return headers, rows


def parse_date(value: str) -> str | None:
    value = (value or "").strip()
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%Y.%m.%d"):
        try:
            return datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            continue
    if re.fullmatch(r"\d{8}", value):
        return datetime.strptime(value, "%Y%m%d").date().isoformat()
    return None


def parse_snapshot_date(folder: str, output: dict[str, str]) -> str:
    file_name = output.get("file", "")
    token = None
    match = re.search(r"(20\d{6}|20\d{4})", file_name)
    if match:
        token = match.group(1)
        if len(token) == 8:
            return datetime.strptime(token, "%Y%m%d").date().isoformat()
        if len(token) == 6:
            return datetime.strptime(token, "%Y%m").date().replace(day=1).isoformat()
    return STATIC_SNAPSHOT_DEFAULTS.get(folder, output.get("retrieved_on", "2026-01-01"))


def infer_numeric(value: str) -> tuple[float | None, str | None]:
    text = (value or "").strip()
    if text == "":
        return None, None
    lowered = text.lower()
    if lowered in {"na", "n/a", "nd", "redacted", "<15"}:
        return None, text
    try:
        return float(text.replace(",", "")), None
    except ValueError:
        return None, text


def is_static_output(output: dict[str, str]) -> bool:
    return output.get("resolution", "") == "static" and output.get("type", "") in {"vector", "matrix"}


def metric_key(source_key: str, metric_name: str) -> str:
    return f"{source_key}:{metric_name}"


def build_source_rows(manifest: dict) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for dataset in manifest.get("datasets", []):
        rows.append(
            {
                "source_key": dataset["folder"],
                "dataset_folder": dataset["folder"],
                "source": dataset.get("source", ""),
                "source_url": dataset.get("source_url", ""),
                "citation": dataset.get("citation", ""),
                "retrieved_on": dataset.get("retrieved_on", ""),
                "license": dataset.get("license", ""),
                "contact": dataset.get("contact", ""),
                "status": dataset.get("status", ""),
            }
        )
    return rows


def build_snapshot_rows(manifest: dict) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for dataset in manifest.get("datasets", []):
        for output in dataset.get("outputs", []):
            if output.get("type") not in {"vector", "matrix"}:
                continue
            if output.get("resolution") != "static":
                continue
            snapshot_key = f"{dataset['folder']}:{output['file']}"
            rows.append(
                {
                    "snapshot_key": snapshot_key,
                    "source_key": dataset["folder"],
                    "snapshot_label": output["file"],
                    "snapshot_date": parse_snapshot_date(dataset["folder"], output),
                    "file_kind": output["type"],
                    "notes": output.get("metric", ""),
                }
            )
    return rows


def build_date_rows_from_values(values: set[str]) -> list[dict[str, str]]:
    date_rows: list[dict[str, str]] = []
    for value in sorted(values):
        parsed = parse_date(value)
        if not parsed:
            continue
        try:
            d = date.fromisoformat(parsed)
        except ValueError:
            continue
        date_key = d.strftime("%Y%m%d")
        date_rows.append(
            {
                "date_key": date_key,
                "date": parsed,
                "year": str(d.year),
                "quarter": str(((d.month - 1) // 3) + 1),
                "month": str(d.month),
                "day": str(d.day),
                "day_of_week": str(d.weekday()),
                "day_name": d.strftime("%A"),
                "is_weekend": str(int(d.weekday() >= 5)),
            }
        )
    return date_rows


def make_metric_row(source_key: str, metric_name: str, measure_kind: str, grain: str, unit: str = "", description: str = "") -> dict[str, str]:
    return {
        "metric_key": metric_key(source_key, metric_name),
        "source_key": source_key,
        "metric_name": metric_name,
        "measure_kind": measure_kind,
        "grain": grain,
        "unit": unit,
        "description": description,
    }


def create_tables(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        PRAGMA journal_mode = WAL;
        PRAGMA synchronous = OFF;

        CREATE TABLE dim_geography (
            geog_id TEXT PRIMARY KEY,
            geog_level TEXT NOT NULL,
            geog_name TEXT NOT NULL,
            province_name TEXT,
            zscode TEXT,
            parent_geog_id TEXT,
            sort_order INTEGER
        );

        CREATE TABLE dim_date (
            date_key TEXT PRIMARY KEY,
            date TEXT NOT NULL,
            year INTEGER,
            quarter INTEGER,
            month INTEGER,
            day INTEGER,
            day_of_week INTEGER,
            day_name TEXT,
            is_weekend INTEGER
        );

        CREATE TABLE dim_source (
            source_key TEXT PRIMARY KEY,
            dataset_folder TEXT NOT NULL,
            source TEXT,
            source_url TEXT,
            citation TEXT,
            retrieved_on TEXT,
            license TEXT,
            contact TEXT,
            status TEXT
        );

        CREATE TABLE dim_snapshot (
            snapshot_key TEXT PRIMARY KEY,
            source_key TEXT NOT NULL,
            snapshot_label TEXT NOT NULL,
            snapshot_date TEXT,
            file_kind TEXT,
            notes TEXT,
            FOREIGN KEY(source_key) REFERENCES dim_source(source_key)
        );

        CREATE TABLE dim_metric (
            metric_key TEXT PRIMARY KEY,
            source_key TEXT NOT NULL,
            metric_name TEXT NOT NULL,
            measure_kind TEXT NOT NULL,
            grain TEXT NOT NULL,
            unit TEXT,
            description TEXT,
            FOREIGN KEY(source_key) REFERENCES dim_source(source_key)
        );

        CREATE TABLE fact_static_scalar_observation (
            fact_id INTEGER PRIMARY KEY AUTOINCREMENT,
            snapshot_key TEXT NOT NULL,
            geog_id TEXT NOT NULL,
            source_key TEXT NOT NULL,
            metric_key TEXT NOT NULL,
            value_numeric REAL,
            value_text TEXT,
            raw_value TEXT,
            FOREIGN KEY(snapshot_key) REFERENCES dim_snapshot(snapshot_key),
            FOREIGN KEY(geog_id) REFERENCES dim_geography(geog_id),
            FOREIGN KEY(source_key) REFERENCES dim_source(source_key),
            FOREIGN KEY(metric_key) REFERENCES dim_metric(metric_key)
        );

        CREATE TABLE fact_time_scalar_observation (
            fact_id INTEGER PRIMARY KEY AUTOINCREMENT,
            date_key TEXT NOT NULL,
            geog_id TEXT NOT NULL,
            source_key TEXT NOT NULL,
            metric_key TEXT NOT NULL,
            value_numeric REAL,
            value_text TEXT,
            raw_value TEXT,
            FOREIGN KEY(date_key) REFERENCES dim_date(date_key),
            FOREIGN KEY(geog_id) REFERENCES dim_geography(geog_id),
            FOREIGN KEY(source_key) REFERENCES dim_source(source_key),
            FOREIGN KEY(metric_key) REFERENCES dim_metric(metric_key)
        );

        CREATE TABLE fact_static_od_observation (
            fact_id INTEGER PRIMARY KEY AUTOINCREMENT,
            snapshot_key TEXT NOT NULL,
            origin_geog_id TEXT NOT NULL,
            destination_geog_id TEXT NOT NULL,
            source_key TEXT NOT NULL,
            metric_key TEXT NOT NULL,
            value_numeric REAL,
            value_text TEXT,
            raw_value TEXT,
            FOREIGN KEY(snapshot_key) REFERENCES dim_snapshot(snapshot_key),
            FOREIGN KEY(origin_geog_id) REFERENCES dim_geography(geog_id),
            FOREIGN KEY(destination_geog_id) REFERENCES dim_geography(geog_id),
            FOREIGN KEY(source_key) REFERENCES dim_source(source_key),
            FOREIGN KEY(metric_key) REFERENCES dim_metric(metric_key)
        );

        CREATE TABLE fact_time_od_observation (
            fact_id INTEGER PRIMARY KEY AUTOINCREMENT,
            date_key TEXT NOT NULL,
            origin_geog_id TEXT NOT NULL,
            destination_geog_id TEXT NOT NULL,
            source_key TEXT NOT NULL,
            metric_key TEXT NOT NULL,
            value_numeric REAL,
            value_text TEXT,
            raw_value TEXT,
            FOREIGN KEY(date_key) REFERENCES dim_date(date_key),
            FOREIGN KEY(origin_geog_id) REFERENCES dim_geography(geog_id),
            FOREIGN KEY(destination_geog_id) REFERENCES dim_geography(geog_id),
            FOREIGN KEY(source_key) REFERENCES dim_source(source_key),
            FOREIGN KEY(metric_key) REFERENCES dim_metric(metric_key)
        );
        """
    )


def safe_lookup(lookup: dict[str, str], value: str) -> str | None:
    key = (value or "").strip()
    if not key:
        return None
    if key in lookup:
        return lookup[key]
    lowered = key.lower()
    for candidate, geog_id in lookup.items():
        if candidate.lower() == lowered:
            return geog_id
    return None


def load_scalar_facts(
    manifest: dict,
    zone_order: list[str],
    zone_lookup: dict[str, str],
    province_lookup: dict[str, str],
    date_values: set[str],
    metric_rows: list[dict[str, str]],
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    static_rows: list[dict[str, str]] = []
    time_rows: list[dict[str, str]] = []

    for dataset in manifest.get("datasets", []):
        source_key = dataset["folder"]
        for output in dataset.get("outputs", []):
            if output.get("type") != "vector":
                continue
            contract_path = REPO_ROOT / "BDBV2026-Data" / "data" / source_key / "processed" / output["file"]
            if not contract_path.exists():
                continue

            rows = load_csv_dict_rows(contract_path)
            if not rows:
                continue

            headers = list(rows[0].keys())
            value_columns = [col for col in headers if col not in {"nom", "date"}]
            grain = "time" if "date" in headers else "static"
            snapshot_key = f"{source_key}:{output['file']}"

            # Pre-register metrics using observed columns.
            for value_column in value_columns:
                example_values = [row.get(value_column, "") for row in rows if row.get(value_column, "").strip()]
                measure_kind = "text" if any(infer_numeric(value)[0] is None and infer_numeric(value)[1] for value in example_values) else "numeric"
                unit = output.get("metric", "") if len(value_columns) == 1 else value_column
                metric_rows.append(
                    make_metric_row(
                        source_key,
                        value_column,
                        measure_kind,
                        grain,
                        unit=unit,
                        description=output.get("metric", value_column),
                    )
                )

            date_groups: dict[str, list[tuple[int, dict[str, str]]]] = defaultdict(list)
            if "date" in headers:
                for row_index, row in enumerate(rows):
                    date_groups[(row.get("date") or "").strip()].append((row_index, row))
            else:
                date_groups[""] = list(enumerate(rows))

            for group_date, indexed_rows in date_groups.items():
                use_zone_order = len(indexed_rows) == len(zone_order) and ("date" not in headers or group_date)
                for position, (row_index, row) in enumerate(indexed_rows):
                    raw_name = (row.get("nom") or "").strip()
                    geog_id: str | None = None
                    if raw_name == "DRC":
                        geog_id = "national:DRC"
                    elif raw_name in province_lookup:
                        geog_id = province_lookup[raw_name]
                    elif use_zone_order:
                        geog_id = zone_order[position]
                    else:
                        geog_id = safe_lookup(zone_lookup, raw_name)

                    if geog_id is None:
                        continue

                    if "date" in headers:
                        parsed_date = parse_date(group_date)
                        if parsed_date:
                            date_values.add(parsed_date)
                            date_key = date.fromisoformat(parsed_date).strftime("%Y%m%d")
                        else:
                            continue
                    else:
                        date_key = ""

                    for value_column in value_columns:
                        raw_value = (row.get(value_column) or "").strip()
                        if raw_value == "":
                            continue
                        numeric_value, text_value = infer_numeric(raw_value)
                        fact = {
                            "geog_id": geog_id,
                            "source_key": source_key,
                            "metric_key": metric_key(source_key, value_column),
                            "value_numeric": numeric_value,
                            "value_text": text_value,
                            "raw_value": raw_value,
                        }
                        if grain == "static":
                            fact["snapshot_key"] = snapshot_key
                            static_rows.append(fact)
                        else:
                            fact["date_key"] = date_key
                            time_rows.append(fact)

    return static_rows, time_rows


def load_od_facts(
    manifest: dict,
    zone_order: list[str],
    zone_lookup: dict[str, str],
    metric_rows: list[dict[str, str]],
    date_values: set[str],
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    static_rows: list[dict[str, str]] = []
    time_rows: list[dict[str, str]] = []

    for dataset in manifest.get("datasets", []):
        source_key = dataset["folder"]
        for output in dataset.get("outputs", []):
            if output.get("type") != "matrix":
                continue
            contract_path = REPO_ROOT / "BDBV2026-Data" / "data" / source_key / "processed" / output["file"]
            if not contract_path.exists():
                continue

            headers, rows = load_csv_matrix(contract_path)
            if not headers or not rows:
                continue

            has_date = bool(headers) and headers[0].strip().lower() == "date"
            dest_start = 2 if has_date else 1
            metric_name = output.get("metric", output["file"].replace(".matrix.csv", ""))
            metric_rows.append(
                make_metric_row(
                    source_key,
                    metric_name,
                    "numeric",
                    "time" if has_date else "static",
                    unit=output.get("metric", ""),
                    description=output.get("file", metric_name),
                )
            )

            snapshot_key = f"{source_key}:{output['file']}"
            for row_index, row in enumerate(rows):
                if len(row) < dest_start:
                    continue
                if has_date:
                    parsed_date = parse_date(row[0])
                    if not parsed_date:
                        continue
                    date_values.add(parsed_date)
                    date_key = date.fromisoformat(parsed_date).strftime("%Y%m%d")
                else:
                    date_key = ""

                origin_name_index = 1 if has_date else 0
                origin_name = (row[origin_name_index] if len(row) > origin_name_index else "").strip()
                origin_geog_id = safe_lookup(zone_lookup, origin_name)
                if origin_geog_id is None:
                    continue

                for dest_index, destination_label in enumerate(headers[dest_start:]):
                    destination_geog_id = safe_lookup(zone_lookup, destination_label.strip())
                    if destination_geog_id is None:
                        continue
                    cell = row[dest_start + dest_index] if dest_start + dest_index < len(row) else ""
                    if cell == "":
                        continue
                    numeric_value, text_value = infer_numeric(cell)
                    fact = {
                        "origin_geog_id": origin_geog_id,
                        "destination_geog_id": destination_geog_id,
                        "source_key": source_key,
                        "metric_key": metric_key(source_key, metric_name),
                        "value_numeric": numeric_value,
                        "value_text": text_value,
                        "raw_value": cell,
                    }
                    if has_date:
                        fact["date_key"] = date_key
                        time_rows.append(fact)
                    else:
                        fact["snapshot_key"] = snapshot_key
                        static_rows.append(fact)

    return static_rows, time_rows


def insert_rows(conn: sqlite3.Connection, table: str, rows: list[dict[str, str]]) -> None:
    if not rows:
        return
    columns = list(rows[0].keys())
    placeholders = ", ".join([f":{column}" for column in columns])
    column_list = ", ".join([f'"{column}"' for column in columns])
    conn.executemany(
        f'INSERT INTO "{table}" ({column_list}) VALUES ({placeholders})',
        rows,
    )


def generate_report(manifest: dict, counts: dict[str, int]) -> str:
    lines = [
        "# ViralWatch star schema",
        "",
        "This database contains only dimensions and facts.",
        "",
        "## Tables",
        "",
        f"- dim_geography: {counts['dim_geography']} rows",
        f"- dim_date: {counts['dim_date']} rows",
        f"- dim_source: {counts['dim_source']} rows",
        f"- dim_snapshot: {counts['dim_snapshot']} rows",
        f"- dim_metric: {counts['dim_metric']} rows",
        f"- fact_static_scalar_observation: {counts['fact_static_scalar_observation']} rows",
        f"- fact_time_scalar_observation: {counts['fact_time_scalar_observation']} rows",
        f"- fact_static_od_observation: {counts['fact_static_od_observation']} rows",
        f"- fact_time_od_observation: {counts['fact_time_od_observation']} rows",
        "",
        "## Join Logic",
        "",
        "- `dim_geography.geog_id` is the master geography key.",
        "- `dim_geography.parent_geog_id` encodes the zone -> province -> national hierarchy.",
        "- Scalar facts join to `dim_geography`, `dim_source`, `dim_metric`, and either `dim_date` or `dim_snapshot`.",
        "- OD facts join to origin and destination `dim_geography` rows, plus either `dim_date` or `dim_snapshot`.",
        "- Province rows use province geographies; national rows use `national:DRC`.",
        "- Zone duplicate names are resolved through `ZSCode` in the geography dimension; where a source uses a province suffix, the loader keeps the canonical lookup variant.",
        "",
        "## Facts Used",
        "",
        "- Static scalar observations: worldpop, gdp_pc, ccvi, fao_lccs, grid3_healthsites, healthsites_io, refugee_sites, cross-border-movements, testing_capacity, genomic_surveillance, and static narrative rollups.",
        "- Time scalar observations: epi, insp_sitrep, epi_mve_inrb_app, aggregated_insp_linelist, public_health_response.",
        "- Static OD observations: osrm, IDP static, flowminder static, flowminder_short_trips static.",
        "- Time OD observations: IDP weekly/monthly and any dated matrix outputs.",
        "",
        "## Notes",
        "",
        "- The schema intentionally avoids extra catalogs and helper tables.",
        "- `dim_metric` is source-scoped so the same column name from different datasets stays unambiguous.",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    manifest = load_manifest()
    geography_rows, zone_order, zone_lookup = load_geojson_geographies()

    province_lookup = {row["geog_name"]: row["geog_id"] for row in geography_rows if row["geog_level"] == "province"}

    metric_rows: list[dict[str, str]] = []
    date_values: set[str] = set()

    source_rows = build_source_rows(manifest)
    snapshot_rows = build_snapshot_rows(manifest)

    static_scalar_rows, time_scalar_rows = load_scalar_facts(
        manifest, zone_order, zone_lookup, province_lookup, date_values, metric_rows
    )
    static_od_rows, time_od_rows = load_od_facts(manifest, zone_order, zone_lookup, metric_rows, date_values)

    date_rows = build_date_rows_from_values(date_values | {row["snapshot_date"] for row in snapshot_rows if row.get("snapshot_date")})

    # Deduplicate metrics while preserving order.
    metric_seen: set[str] = set()
    deduped_metrics: list[dict[str, str]] = []
    for row in metric_rows:
        if row["metric_key"] in metric_seen:
            continue
        metric_seen.add(row["metric_key"])
        deduped_metrics.append(row)

    if DB_PATH.exists():
        DB_PATH.unlink()
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(DB_PATH) as conn:
        create_tables(conn)
        insert_rows(conn, "dim_geography", geography_rows)
        insert_rows(conn, "dim_date", date_rows)
        insert_rows(conn, "dim_source", source_rows)
        insert_rows(conn, "dim_snapshot", snapshot_rows)
        insert_rows(conn, "dim_metric", deduped_metrics)
        insert_rows(conn, "fact_static_scalar_observation", static_scalar_rows)
        insert_rows(conn, "fact_time_scalar_observation", time_scalar_rows)
        insert_rows(conn, "fact_static_od_observation", static_od_rows)
        insert_rows(conn, "fact_time_od_observation", time_od_rows)
        conn.commit()

        counts = {}
        for table in [
            "dim_geography",
            "dim_date",
            "dim_source",
            "dim_snapshot",
            "dim_metric",
            "fact_static_scalar_observation",
            "fact_time_scalar_observation",
            "fact_static_od_observation",
            "fact_time_od_observation",
        ]:
            counts[table] = conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]

    REPORT_PATH.write_text(generate_report(manifest, counts), encoding="utf-8")
    print(f"Wrote {DB_PATH}")
    print(f"Wrote {REPORT_PATH}")


if __name__ == "__main__":
    main()
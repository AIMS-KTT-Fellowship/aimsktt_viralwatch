from pathlib import Path

import pandas as pd


def _read_public_health_response_frame(csv_path: Path) -> pd.DataFrame | None:
    """Read one public health response CSV as a 3-column (nom, date, value) frame."""
    with csv_path.open("r", encoding="utf-8") as handle:
        first_line = handle.readline().strip().split(",")

    header_row = (
        len(first_line) >= 3
        and first_line[0].strip().lower() in {"nom", "zone_de_sante", "zone_sante", "zone"}
        and first_line[1].strip().lower() in {"date", "jour"}
    )

    if header_row:
        frame = pd.read_csv(csv_path)
    else:
        frame = pd.read_csv(csv_path, header=None)
        if frame.shape[1] < 3:
            return None
        frame = frame.iloc[:, :3].copy()
        frame.columns = ["nom", "date", "value"]

    if frame.shape[1] < 3:
        return None

    frame = frame.iloc[:, :3].copy()
    if list(frame.columns)[:2] != ["nom", "date"]:
        frame.columns = ["nom", "date", "value"]

    frame["date"] = pd.to_datetime(frame["date"], errors="coerce", dayfirst=True).dt.strftime("%Y-%m-%d")
    return frame


def join_public_health_response_csvs(input_dir: Path | str, output_path: Path | str) -> pd.DataFrame:
    """
    Join public health response CSV fragments on (nom, date) into a wide table.

    Each file contributes one feature column while preserving all place/date rows.
    If a place/date pair is missing in one file, it is kept with NaN for that feature.
    """
    input_dir = Path(input_dir)
    output_path = Path(output_path)

    csv_files = sorted(input_dir.glob("public_health_response*.csv"))
    if not csv_files:
        raise FileNotFoundError(f"No public_health_response*.csv files found in {input_dir}")

    frames: list[pd.DataFrame] = []
    skipped_files: list[str] = []

    for csv_path in csv_files:
        frame = _read_public_health_response_frame(csv_path)
        if frame is None:
            print(f"Skipping {csv_path.name}: expected at least 3 columns")
            skipped_files.append(csv_path.name)
            continue

        value_col = [column for column in frame.columns if column not in {"nom", "date"}]
        if len(value_col) != 1:
            raise ValueError(f"{csv_path.name} must contain exactly one value column; found {value_col}")

        feature_name = csv_path.stem
        feature_frame = frame[["nom", "date", value_col[0]]].copy()
        feature_frame.rename(columns={value_col[0]: feature_name}, inplace=True)
        frames.append(feature_frame)

    if not frames:
        raise RuntimeError(f"No valid public_health_response frames could be merged. Skipped files: {skipped_files}")

    merged = frames[0]
    for frame in frames[1:]:
        merged = pd.merge(merged, frame, on=["nom", "date"], how="outer")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(output_path, index=False)
    return merged


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    input_dir = repo_root / "BDBV2026-Data" / "build" / "long"
    output_path = repo_root / "output" / "public_health_response_merged.csv"

    merged = join_public_health_response_csvs(input_dir, output_path)
    print(f"Wrote {len(merged)} rows to {output_path}")
    print(f"Unique places: {merged['nom'].nunique()}")
    print(f"Date range: {merged['date'].min()} to {merged['date'].max()}")
    print(merged.head())


if __name__ == "__main__":
    main()

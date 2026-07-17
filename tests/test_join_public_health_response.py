from pathlib import Path

import pandas as pd

from scripts.join_public_health_response import join_public_health_response_csvs


def test_join_public_health_response_csvs_outer_merges_on_nom_and_date(tmp_path: Path) -> None:
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    output_path = tmp_path / "output" / "public_health_response_merged.csv"

    pd.DataFrame(
        [
            ["Goma", "2026-01-01", "yes"],
        ]
    ).to_csv(input_dir / "public_health_response__coordination.csv", header=False, index=False)

    pd.DataFrame(
        [
            ["Beni", "2026-01-02", "no"],
        ]
    ).to_csv(input_dir / "public_health_response__community_engagement.csv", header=False, index=False)

    merged = join_public_health_response_csvs(input_dir, output_path)

    assert output_path.exists()
    assert set(merged.columns.tolist()) == {"nom", "date", "public_health_response__coordination", "public_health_response__community_engagement"}
    assert len(merged) == 2
    assert merged.loc[merged["nom"] == "Goma", "public_health_response__coordination"].iloc[0] == "yes"
    assert merged.loc[merged["nom"] == "Beni", "public_health_response__community_engagement"].iloc[0] == "no"

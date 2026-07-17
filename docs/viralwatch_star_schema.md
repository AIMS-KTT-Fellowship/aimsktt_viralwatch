# ViralWatch star schema

This database contains only dimensions and facts.

## Tables

- dim_geography: 546 rows
- dim_date: 427 rows
- dim_source: 21 rows
- dim_snapshot: 40 rows
- dim_metric: 124 rows
- fact_static_scalar_observation: 7655 rows
- fact_time_scalar_observation: 6376 rows
- fact_static_od_observation: 1252044 rows
- fact_time_od_observation: 729872 rows

## Join Logic

- `dim_geography.geog_id` is the master geography key.
- `dim_geography.parent_geog_id` encodes the zone -> province -> national hierarchy.
- Scalar facts join to `dim_geography`, `dim_source`, `dim_metric`, and either `dim_date` or `dim_snapshot`.
- OD facts join to origin and destination `dim_geography` rows, plus either `dim_date` or `dim_snapshot`.
- Province rows use province geographies; national rows use `national:DRC`.
- Zone duplicate names are resolved through `ZSCode` in the geography dimension; where a source uses a province suffix, the loader keeps the canonical lookup variant.

## Facts Used

- Static scalar observations: worldpop, gdp_pc, ccvi, fao_lccs, grid3_healthsites, healthsites_io, refugee_sites, cross-border-movements, testing_capacity, genomic_surveillance, and static narrative rollups.
- Time scalar observations: epi, insp_sitrep, epi_mve_inrb_app, aggregated_insp_linelist, public_health_response.
- Static OD observations: osrm, IDP static, flowminder static, flowminder_short_trips static.
- Time OD observations: IDP weekly/monthly and any dated matrix outputs.

## Notes

- The schema intentionally avoids extra catalogs and helper tables.
- `dim_metric` is source-scoped so the same column name from different datasets stays unambiguous.

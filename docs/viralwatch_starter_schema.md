# ViralWatch starter schema

This file is a metadata-first starter schema for the BDBV2026 data repo. It is designed to seed an analysis database without reading the raw analytical CSV contents.

## Hierarchy

1. `data/shapefiles/DRC_Health_zones.shp` is the canonical geometry and zone dimension.
2. `Nom` is the main health-zone join key.
3. `PROVINCE` is the province parent for zone roll-ups.
4. `DRC` is the national roll-up token for province and national files.
5. `aliases.csv` and `province_aliases.csv` normalize spelling variants before joins.
6. SQLite now loads 182 CSV tables from canonical build outputs, matrix outputs, and small lookup files.

## Dataset catalog

| Folder | Status | Retrieved | Outputs | Source |
|---|---|---|---:|---|
| ACLED_conflict | placeholder | 2026-05-02 | 0 | Armed Conflict Location & Event Data (ACLED) |
| IDP | active | 2026-01-31 | 3 | International Organisation for Migration (IOM) Displacement Tracking Matrix (DTM) — DRC |
| aggregated_insp_linelist | active | 2026-06-09 | 2 | INSP/DHIS2 MVE epidemic line list — province-level onset aggregates |
| archive | archive | 2026-06-07 | 0 | World Health Organization — Weekly External Situation Reports (2026 Bundibugyo Ebola virus outbreak, DRC) |
| ccvi | active | 2026-05-20 | 2 | Climate Conflict Vulnerability Index (CCVI) — socio-economic vulnerability indicators aggregated to DRC health zones |
| cross-border-movements | active | 2026-05-18 | 1 | Cross-border passenger volumes from sitreps cited in Imperial College report on the 2026 DRC Ebola outbreak |
| epi | active | 2026-05-18 | 1 | WHO Weekly External Situation Report 01 |
| epi_mve_inrb_app | active | 2026-05-28 | 1 | INRB MVE app line-list export (test extract) |
| fao_lccs | active | 2026-05-20 | 1 | Copernicus CDS satellite-land-cover (UN FAO LCCS); urban class 190 aggregated to DRC health zones |
| flowminder | active | 2026-07-14 | 4 | Flowminder.org mobility / population-relocation estimates from Vodacom RDC CDR data |
| flowminder_short_trips | active | 2026-06-08 | 18 | Flowminder Foundation — DRC Ebola Bundibugyo short-trip cohort (May–June 2026) |
| gdp_pc | active | 2026-05-20 | 1 | Kummu et al. (2025) downscaled global GDP per capita (PPP), aggregated to DRC health zones |
| genomic_surveillance | active | 2026-07-07 | 1 | INRB/INOHA BDBV 2026 genomic surveillance (whole-genome sequencing consensus metadata) |
| grid3_healthsites | active | 2026-05-20 | 2 | GRID3 COD Health Facilities v8.0, aggregated to DRC health zones |
| healthsites_io | active | 2026-05-20 | 2 | Healthsites.io OpenStreetMap health-facility extract (DRC), aggregated to health zones |
| insp_sitrep | active | 2026-07-12 | 31 | Institut National de Santé Publique (INSP) Situation Reports — SitRep MVE series (2026 Bundibugyo Ebolavirus outbreak) |
| osrm | active | 2026-03-17 | 2 | OSRM road-network routing (OpenStreetMap) applied to DRC health-zone polygons |
| public_health_response | active | 2026-06-10 | 54 | Institut National de Santé Publique (INSP) Situation Reports — SitRep MVE series (2026 Bundibugyo Ebolavirus outbreak) |
| refugee_sites | active | 2026-05-20 | 1 | OpenStreetMap |
| testing_capacity | active | 2026-05-26 | 2 | Africa CDC — Plan de décentralisation des tests Ebola, RDC |
| worldpop | active | 2026-05-20 | 2 | WorldPop gridded population estimates aggregated to DRC health zones |

## File catalog

| Dataset | Contract path | Published path | Kind | Columns / value shape |
|---|---|---|---|---|
| IDP | BDBV2026-Data/data/IDP/processed/idp__individuals__monthly.matrix.csv | BDBV2026-Data/build/matrix/idp__individuals__monthly.matrix.csv | matrix | wide matrix |
| IDP | BDBV2026-Data/data/IDP/processed/idp__individuals__static.matrix.csv | BDBV2026-Data/build/matrix/idp__individuals__static.matrix.csv | matrix | wide matrix |
| IDP | BDBV2026-Data/data/IDP/processed/idp__individuals__weekly.matrix.csv | BDBV2026-Data/build/matrix/idp__individuals__weekly.matrix.csv | matrix | wide matrix |
| aggregated_insp_linelist | BDBV2026-Data/data/aggregated_insp_linelist/processed/aggregated_insp_linelist__national_confirmed_cases_onset__daily.csv | BDBV2026-Data/build/long/aggregated_insp_linelist__national_confirmed_cases_onset.csv | vector | vector |
| aggregated_insp_linelist | BDBV2026-Data/data/aggregated_insp_linelist/processed/aggregated_insp_linelist__provincial_confirmed_cases_onset__daily.csv | BDBV2026-Data/build/long/aggregated_insp_linelist__provincial_confirmed_cases_onset.csv | vector | vector |
| ccvi | BDBV2026-Data/data/ccvi/processed/ccvi__socioeconomic_deprivation__static.csv | BDBV2026-Data/build/long/ccvi__socioeconomic_deprivation.csv | vector | vector |
| ccvi | BDBV2026-Data/data/ccvi/processed/ccvi__socioeconomic_inequality__static.csv | BDBV2026-Data/build/long/ccvi__socioeconomic_inequality.csv | vector | vector |
| cross-border-movements | BDBV2026-Data/data/cross-border-movements/processed/cross_border__poe_passengers__static.csv | BDBV2026-Data/build/long/cross_border__poe_passengers.csv | vector | vector |
| epi | BDBV2026-Data/data/epi/processed/epi__cases__weekly.csv | BDBV2026-Data/build/long/epi__cases.csv | vector | vector |
| epi_mve_inrb_app | BDBV2026-Data/data/epi_mve_inrb_app/processed/epi_mve_inrb_app__recorded_cases__daily.csv | BDBV2026-Data/build/long/epi_mve_inrb_app__recorded_cases.csv | vector | vector |
| fao_lccs | BDBV2026-Data/data/fao_lccs/processed/fao_lccs__urban_fraction__static.csv | BDBV2026-Data/build/long/fao_lccs__urban_fraction.csv | vector | vector |
| flowminder | BDBV2026-Data/data/flowminder/processed/flowminder__inflow_202604__static.matrix.csv | BDBV2026-Data/build/matrix/flowminder__inflow_202604__static.matrix.csv | matrix | wide matrix |
| flowminder | BDBV2026-Data/data/flowminder/processed/flowminder__inflow__static.matrix.csv | BDBV2026-Data/build/matrix/flowminder__inflow__static.matrix.csv | matrix | wide matrix |
| flowminder | BDBV2026-Data/data/flowminder/processed/flowminder__outflow_202604__static.matrix.csv | BDBV2026-Data/build/matrix/flowminder__outflow_202604__static.matrix.csv | matrix | wide matrix |
| flowminder | BDBV2026-Data/data/flowminder/processed/flowminder__outflow__static.matrix.csv | BDBV2026-Data/build/matrix/flowminder__outflow__static.matrix.csv | matrix | wide matrix |
| flowminder_short_trips | BDBV2026-Data/data/flowminder_short_trips/processed/flowminder_short_trips__ituri_subscriber_days_followup_20260608__static.csv | BDBV2026-Data/build/long/flowminder_short_trips__ituri_subscriber_days_followup_20260608.csv | vector | vector |
| flowminder_short_trips | BDBV2026-Data/data/flowminder_short_trips/processed/flowminder_short_trips__ituri_subscriber_days_followup_20260608__static.matrix.csv | BDBV2026-Data/build/matrix/flowminder_short_trips__ituri_subscriber_days_followup_20260608__static.matrix.csv | matrix | wide matrix |
| flowminder_short_trips | BDBV2026-Data/data/flowminder_short_trips/processed/flowminder_short_trips__ituri_subscriber_days_prior_20260503__static.csv | BDBV2026-Data/build/long/flowminder_short_trips__ituri_subscriber_days_prior_20260503.csv | vector | vector |
| flowminder_short_trips | BDBV2026-Data/data/flowminder_short_trips/processed/flowminder_short_trips__ituri_subscriber_days_prior_20260503__static.matrix.csv | BDBV2026-Data/build/matrix/flowminder_short_trips__ituri_subscriber_days_prior_20260503__static.matrix.csv | matrix | wide matrix |
| flowminder_short_trips | BDBV2026-Data/data/flowminder_short_trips/processed/flowminder_short_trips__nk_subscriber_days_followup_20260608__static.csv | BDBV2026-Data/build/long/flowminder_short_trips__nk_subscriber_days_followup_20260608.csv | vector | vector |
| flowminder_short_trips | BDBV2026-Data/data/flowminder_short_trips/processed/flowminder_short_trips__nk_subscriber_days_followup_20260608__static.matrix.csv | BDBV2026-Data/build/matrix/flowminder_short_trips__nk_subscriber_days_followup_20260608__static.matrix.csv | matrix | wide matrix |
| flowminder_short_trips | BDBV2026-Data/data/flowminder_short_trips/processed/flowminder_short_trips__nk_subscriber_days_prior_20260503__static.csv | BDBV2026-Data/build/long/flowminder_short_trips__nk_subscriber_days_prior_20260503.csv | vector | vector |
| flowminder_short_trips | BDBV2026-Data/data/flowminder_short_trips/processed/flowminder_short_trips__nk_subscriber_days_prior_20260503__static.matrix.csv | BDBV2026-Data/build/matrix/flowminder_short_trips__nk_subscriber_days_prior_20260503__static.matrix.csv | matrix | wide matrix |
| flowminder_short_trips | BDBV2026-Data/data/flowminder_short_trips/processed/flowminder_short_trips__outflow_20260430__static.csv | BDBV2026-Data/build/long/flowminder_short_trips__outflow_20260430.csv | vector | vector |
| flowminder_short_trips | BDBV2026-Data/data/flowminder_short_trips/processed/flowminder_short_trips__outflow_20260430__static.matrix.csv | BDBV2026-Data/build/matrix/flowminder_short_trips__outflow_20260430__static.matrix.csv | matrix | wide matrix |
| flowminder_short_trips | BDBV2026-Data/data/flowminder_short_trips/processed/flowminder_short_trips__outflow_20260507__static.csv | BDBV2026-Data/build/long/flowminder_short_trips__outflow_20260507.csv | vector | vector |
| flowminder_short_trips | BDBV2026-Data/data/flowminder_short_trips/processed/flowminder_short_trips__outflow_20260507__static.matrix.csv | BDBV2026-Data/build/matrix/flowminder_short_trips__outflow_20260507__static.matrix.csv | matrix | wide matrix |
| flowminder_short_trips | BDBV2026-Data/data/flowminder_short_trips/processed/flowminder_short_trips__outflow_20260514__static.csv | BDBV2026-Data/build/long/flowminder_short_trips__outflow_20260514.csv | vector | vector |
| flowminder_short_trips | BDBV2026-Data/data/flowminder_short_trips/processed/flowminder_short_trips__outflow_20260514__static.matrix.csv | BDBV2026-Data/build/matrix/flowminder_short_trips__outflow_20260514__static.matrix.csv | matrix | wide matrix |
| flowminder_short_trips | BDBV2026-Data/data/flowminder_short_trips/processed/flowminder_short_trips__outflow_20260521__static.csv | BDBV2026-Data/build/long/flowminder_short_trips__outflow_20260521.csv | vector | vector |
| flowminder_short_trips | BDBV2026-Data/data/flowminder_short_trips/processed/flowminder_short_trips__outflow_20260521__static.matrix.csv | BDBV2026-Data/build/matrix/flowminder_short_trips__outflow_20260521__static.matrix.csv | matrix | wide matrix |
| flowminder_short_trips | BDBV2026-Data/data/flowminder_short_trips/processed/flowminder_short_trips__outflow_20260524__static.csv | BDBV2026-Data/build/long/flowminder_short_trips__outflow_20260524.csv | vector | vector |
| flowminder_short_trips | BDBV2026-Data/data/flowminder_short_trips/processed/flowminder_short_trips__outflow_20260524__static.matrix.csv | BDBV2026-Data/build/matrix/flowminder_short_trips__outflow_20260524__static.matrix.csv | matrix | wide matrix |
| gdp_pc | BDBV2026-Data/data/gdp_pc/processed/gdp_pc__gdp_pc__static.csv | BDBV2026-Data/build/long/gdp_pc__gdp_pc.csv | vector | vector |
| genomic_surveillance | BDBV2026-Data/data/genomic_surveillance/processed/genomic_surveillance__sequence_count__static.csv | BDBV2026-Data/build/long/genomic_surveillance__sequence_count.csv | vector | vector |
| grid3_healthsites | BDBV2026-Data/data/grid3_healthsites/processed/grid3_healthsites__healthsite_count__static.csv | BDBV2026-Data/build/long/grid3_healthsites__healthsite_count.csv | vector | vector |
| grid3_healthsites | BDBV2026-Data/data/grid3_healthsites/processed/grid3_healthsites__healthsite_density__static.csv | BDBV2026-Data/build/long/grid3_healthsites__healthsite_density.csv | vector | vector |
| healthsites_io | BDBV2026-Data/data/healthsites_io/processed/healthsites_io__healthsite_count__static.csv | BDBV2026-Data/build/long/healthsites_io__healthsite_count.csv | vector | vector |
| healthsites_io | BDBV2026-Data/data/healthsites_io/processed/healthsites_io__healthsite_density__static.csv | BDBV2026-Data/build/long/healthsites_io__healthsite_density.csv | vector | vector |
| insp_sitrep | BDBV2026-Data/data/insp_sitrep/processed/insp_sitrep__contacts_seen__daily.csv | BDBV2026-Data/build/long/insp_sitrep__contacts_seen.csv | vector | vector |
| insp_sitrep | BDBV2026-Data/data/insp_sitrep/processed/insp_sitrep__cumulative_confirmed_cases__daily.csv | BDBV2026-Data/build/long/insp_sitrep__cumulative_confirmed_cases.csv | vector | vector |
| insp_sitrep | BDBV2026-Data/data/insp_sitrep/processed/insp_sitrep__cumulative_confirmed_deaths__daily.csv | BDBV2026-Data/build/long/insp_sitrep__cumulative_confirmed_deaths.csv | vector | vector |
| insp_sitrep | BDBV2026-Data/data/insp_sitrep/processed/insp_sitrep__cumulative_contacts_isolated__daily.csv | BDBV2026-Data/build/long/insp_sitrep__cumulative_contacts_isolated.csv | vector | vector |
| insp_sitrep | BDBV2026-Data/data/insp_sitrep/processed/insp_sitrep__cumulative_contacts_traced__daily.csv | BDBV2026-Data/build/long/insp_sitrep__cumulative_contacts_traced.csv | vector | vector |
| insp_sitrep | BDBV2026-Data/data/insp_sitrep/processed/insp_sitrep__cumulative_suspected_cases__daily.csv | BDBV2026-Data/build/long/insp_sitrep__cumulative_suspected_cases.csv | vector | vector |
| insp_sitrep | BDBV2026-Data/data/insp_sitrep/processed/insp_sitrep__cumulative_suspected_deaths__daily.csv | BDBV2026-Data/build/long/insp_sitrep__cumulative_suspected_deaths.csv | vector | vector |
| insp_sitrep | BDBV2026-Data/data/insp_sitrep/processed/insp_sitrep__hosp_escaped__daily.csv | BDBV2026-Data/build/long/insp_sitrep__hosp_escaped.csv | vector | vector |
| insp_sitrep | BDBV2026-Data/data/insp_sitrep/processed/insp_sitrep__hospitalised__daily.csv | BDBV2026-Data/build/long/insp_sitrep__hospitalised.csv | vector | vector |
| insp_sitrep | BDBV2026-Data/data/insp_sitrep/processed/insp_sitrep__in_bed_previous_day__daily.csv | BDBV2026-Data/build/long/insp_sitrep__in_bed_previous_day.csv | vector | vector |
| insp_sitrep | BDBV2026-Data/data/insp_sitrep/processed/insp_sitrep__national_cumulative_confirmed_cases__daily.csv | BDBV2026-Data/build/long/insp_sitrep__national_cumulative_confirmed_cases.csv | vector | vector |
| insp_sitrep | BDBV2026-Data/data/insp_sitrep/processed/insp_sitrep__national_cumulative_confirmed_deaths__daily.csv | BDBV2026-Data/build/long/insp_sitrep__national_cumulative_confirmed_deaths.csv | vector | vector |
| insp_sitrep | BDBV2026-Data/data/insp_sitrep/processed/insp_sitrep__national_cumulative_recovered_cases__daily.csv | BDBV2026-Data/build/long/insp_sitrep__national_cumulative_recovered_cases.csv | vector | vector |
| insp_sitrep | BDBV2026-Data/data/insp_sitrep/processed/insp_sitrep__national_cumulative_suspected_cases__daily.csv | BDBV2026-Data/build/long/insp_sitrep__national_cumulative_suspected_cases.csv | vector | vector |
| insp_sitrep | BDBV2026-Data/data/insp_sitrep/processed/insp_sitrep__national_cumulative_suspected_deaths__daily.csv | BDBV2026-Data/build/long/insp_sitrep__national_cumulative_suspected_deaths.csv | vector | vector |
| insp_sitrep | BDBV2026-Data/data/insp_sitrep/processed/insp_sitrep__national_suspected_cases_in_isolation__daily.csv | BDBV2026-Data/build/long/insp_sitrep__national_suspected_cases_in_isolation.csv | vector | vector |
| insp_sitrep | BDBV2026-Data/data/insp_sitrep/processed/insp_sitrep__national_suspected_cases_under_investigation__daily.csv | BDBV2026-Data/build/long/insp_sitrep__national_suspected_cases_under_investigation.csv | vector | vector |
| insp_sitrep | BDBV2026-Data/data/insp_sitrep/processed/insp_sitrep__new_confirmed_cases__daily.csv | BDBV2026-Data/build/long/insp_sitrep__new_confirmed_cases.csv | vector | vector |
| insp_sitrep | BDBV2026-Data/data/insp_sitrep/processed/insp_sitrep__new_contacts_isolated__daily.csv | BDBV2026-Data/build/long/insp_sitrep__new_contacts_isolated.csv | vector | vector |
| insp_sitrep | BDBV2026-Data/data/insp_sitrep/processed/insp_sitrep__new_contacts_listed__daily.csv | BDBV2026-Data/build/long/insp_sitrep__new_contacts_listed.csv | vector | vector |
| insp_sitrep | BDBV2026-Data/data/insp_sitrep/processed/insp_sitrep__new_hosp_admissions__daily.csv | BDBV2026-Data/build/long/insp_sitrep__new_hosp_admissions.csv | vector | vector |
| insp_sitrep | BDBV2026-Data/data/insp_sitrep/processed/insp_sitrep__new_hosp_detainees__daily.csv | BDBV2026-Data/build/long/insp_sitrep__new_hosp_detainees.csv | vector | vector |
| insp_sitrep | BDBV2026-Data/data/insp_sitrep/processed/insp_sitrep__new_hosp_other__daily.csv | BDBV2026-Data/build/long/insp_sitrep__new_hosp_other.csv | vector | vector |
| insp_sitrep | BDBV2026-Data/data/insp_sitrep/processed/insp_sitrep__new_suspected_cases__daily.csv | BDBV2026-Data/build/long/insp_sitrep__new_suspected_cases.csv | vector | vector |
| insp_sitrep | BDBV2026-Data/data/insp_sitrep/processed/insp_sitrep__new_suspected_deaths__daily.csv | BDBV2026-Data/build/long/insp_sitrep__new_suspected_deaths.csv | vector | vector |
| insp_sitrep | BDBV2026-Data/data/insp_sitrep/processed/insp_sitrep__total_poe_hand_washing__daily.csv | BDBV2026-Data/build/long/insp_sitrep__total_poe_hand_washing.csv | vector | vector |
| insp_sitrep | BDBV2026-Data/data/insp_sitrep/processed/insp_sitrep__total_poe_passed__daily.csv | BDBV2026-Data/build/long/insp_sitrep__total_poe_passed.csv | vector | vector |
| insp_sitrep | BDBV2026-Data/data/insp_sitrep/processed/insp_sitrep__total_poe_refused_hand_washing__daily.csv | BDBV2026-Data/build/long/insp_sitrep__total_poe_refused_hand_washing.csv | vector | vector |
| insp_sitrep | BDBV2026-Data/data/insp_sitrep/processed/insp_sitrep__total_poe_refused_screening__daily.csv | BDBV2026-Data/build/long/insp_sitrep__total_poe_refused_screening.csv | vector | vector |
| insp_sitrep | BDBV2026-Data/data/insp_sitrep/processed/insp_sitrep__total_poe_sanitised__daily.csv | BDBV2026-Data/build/long/insp_sitrep__total_poe_sanitised.csv | vector | vector |
| insp_sitrep | BDBV2026-Data/data/insp_sitrep/processed/insp_sitrep__total_poe_screened__daily.csv | BDBV2026-Data/build/long/insp_sitrep__total_poe_screened.csv | vector | vector |
| osrm | BDBV2026-Data/data/osrm/processed/osrm__road_distance__static.matrix.csv | BDBV2026-Data/build/matrix/osrm__road_distance__static.matrix.csv | matrix | wide matrix |
| osrm | BDBV2026-Data/data/osrm/processed/osrm__travel_time__static.matrix.csv | BDBV2026-Data/build/matrix/osrm__travel_time__static.matrix.csv | matrix | wide matrix |
| public_health_response | BDBV2026-Data/data/public_health_response/processed/public_health_response__epidemiological_community_engagement_en__daily.csv | BDBV2026-Data/build/long/public_health_response__epidemiological_community_engagement_en.csv | vector | vector |
| public_health_response | BDBV2026-Data/data/public_health_response/processed/public_health_response__epidemiological_community_engagement_fr__daily.csv | BDBV2026-Data/build/long/public_health_response__epidemiological_community_engagement_fr.csv | vector | vector |
| public_health_response | BDBV2026-Data/data/public_health_response/processed/public_health_response__epidemiological_coordination_en__daily.csv | BDBV2026-Data/build/long/public_health_response__epidemiological_coordination_en.csv | vector | vector |
| public_health_response | BDBV2026-Data/data/public_health_response/processed/public_health_response__epidemiological_coordination_fr__daily.csv | BDBV2026-Data/build/long/public_health_response__epidemiological_coordination_fr.csv | vector | vector |
| public_health_response | BDBV2026-Data/data/public_health_response/processed/public_health_response__epidemiological_infection_prevention_controle_en__daily.csv | BDBV2026-Data/build/long/public_health_response__epidemiological_infection_prevention_controle_en.csv | vector | vector |
| public_health_response | BDBV2026-Data/data/public_health_response/processed/public_health_response__epidemiological_infection_prevention_controle_fr__daily.csv | BDBV2026-Data/build/long/public_health_response__epidemiological_infection_prevention_controle_fr.csv | vector | vector |
| public_health_response | BDBV2026-Data/data/public_health_response/processed/public_health_response__epidemiological_laboratory_en__daily.csv | BDBV2026-Data/build/long/public_health_response__epidemiological_laboratory_en.csv | vector | vector |
| public_health_response | BDBV2026-Data/data/public_health_response/processed/public_health_response__epidemiological_laboratory_fr__daily.csv | BDBV2026-Data/build/long/public_health_response__epidemiological_laboratory_fr.csv | vector | vector |
| public_health_response | BDBV2026-Data/data/public_health_response/processed/public_health_response__epidemiological_logistics_en__daily.csv | BDBV2026-Data/build/long/public_health_response__epidemiological_logistics_en.csv | vector | vector |
| public_health_response | BDBV2026-Data/data/public_health_response/processed/public_health_response__epidemiological_logistics_fr__daily.csv | BDBV2026-Data/build/long/public_health_response__epidemiological_logistics_fr.csv | vector | vector |
| public_health_response | BDBV2026-Data/data/public_health_response/processed/public_health_response__epidemiological_management_en__daily.csv | BDBV2026-Data/build/long/public_health_response__epidemiological_management_en.csv | vector | vector |
| public_health_response | BDBV2026-Data/data/public_health_response/processed/public_health_response__epidemiological_management_fr__daily.csv | BDBV2026-Data/build/long/public_health_response__epidemiological_management_fr.csv | vector | vector |
| public_health_response | BDBV2026-Data/data/public_health_response/processed/public_health_response__epidemiological_monitoring_en__daily.csv | BDBV2026-Data/build/long/public_health_response__epidemiological_monitoring_en.csv | vector | vector |
| public_health_response | BDBV2026-Data/data/public_health_response/processed/public_health_response__epidemiological_monitoring_fr__daily.csv | BDBV2026-Data/build/long/public_health_response__epidemiological_monitoring_fr.csv | vector | vector |
| public_health_response | BDBV2026-Data/data/public_health_response/processed/public_health_response__epidemiological_protection_sexual_exploitation_abuse_en__daily.csv | BDBV2026-Data/build/long/public_health_response__epidemiological_protection_sexual_exploitation_abuse_en.csv | vector | vector |
| public_health_response | BDBV2026-Data/data/public_health_response/processed/public_health_response__epidemiological_protection_sexual_exploitation_abuse_fr__daily.csv | BDBV2026-Data/build/long/public_health_response__epidemiological_protection_sexual_exploitation_abuse_fr.csv | vector | vector |
| public_health_response | BDBV2026-Data/data/public_health_response/processed/public_health_response__epidemiological_security_en__daily.csv | BDBV2026-Data/build/long/public_health_response__epidemiological_security_en.csv | vector | vector |
| public_health_response | BDBV2026-Data/data/public_health_response/processed/public_health_response__epidemiological_security_fr__daily.csv | BDBV2026-Data/build/long/public_health_response__epidemiological_security_fr.csv | vector | vector |
| public_health_response | BDBV2026-Data/data/public_health_response/processed/public_health_response__national_epidemiological_community_engagement_en__daily.csv | BDBV2026-Data/build/long/public_health_response__national_epidemiological_community_engagement_en.csv | vector | vector |
| public_health_response | BDBV2026-Data/data/public_health_response/processed/public_health_response__national_epidemiological_community_engagement_fr__daily.csv | BDBV2026-Data/build/long/public_health_response__national_epidemiological_community_engagement_fr.csv | vector | vector |
| public_health_response | BDBV2026-Data/data/public_health_response/processed/public_health_response__national_epidemiological_coordination_en__daily.csv | BDBV2026-Data/build/long/public_health_response__national_epidemiological_coordination_en.csv | vector | vector |
| public_health_response | BDBV2026-Data/data/public_health_response/processed/public_health_response__national_epidemiological_coordination_fr__daily.csv | BDBV2026-Data/build/long/public_health_response__national_epidemiological_coordination_fr.csv | vector | vector |
| public_health_response | BDBV2026-Data/data/public_health_response/processed/public_health_response__national_epidemiological_infection_prevention_controle_en__daily.csv | BDBV2026-Data/build/long/public_health_response__national_epidemiological_infection_prevention_controle_en.csv | vector | vector |
| public_health_response | BDBV2026-Data/data/public_health_response/processed/public_health_response__national_epidemiological_infection_prevention_controle_fr__daily.csv | BDBV2026-Data/build/long/public_health_response__national_epidemiological_infection_prevention_controle_fr.csv | vector | vector |
| public_health_response | BDBV2026-Data/data/public_health_response/processed/public_health_response__national_epidemiological_laboratory_en__daily.csv | BDBV2026-Data/build/long/public_health_response__national_epidemiological_laboratory_en.csv | vector | vector |
| public_health_response | BDBV2026-Data/data/public_health_response/processed/public_health_response__national_epidemiological_laboratory_fr__daily.csv | BDBV2026-Data/build/long/public_health_response__national_epidemiological_laboratory_fr.csv | vector | vector |
| public_health_response | BDBV2026-Data/data/public_health_response/processed/public_health_response__national_epidemiological_logistics_en__daily.csv | BDBV2026-Data/build/long/public_health_response__national_epidemiological_logistics_en.csv | vector | vector |
| public_health_response | BDBV2026-Data/data/public_health_response/processed/public_health_response__national_epidemiological_logistics_fr__daily.csv | BDBV2026-Data/build/long/public_health_response__national_epidemiological_logistics_fr.csv | vector | vector |
| public_health_response | BDBV2026-Data/data/public_health_response/processed/public_health_response__national_epidemiological_management_en__daily.csv | BDBV2026-Data/build/long/public_health_response__national_epidemiological_management_en.csv | vector | vector |
| public_health_response | BDBV2026-Data/data/public_health_response/processed/public_health_response__national_epidemiological_management_fr__daily.csv | BDBV2026-Data/build/long/public_health_response__national_epidemiological_management_fr.csv | vector | vector |
| public_health_response | BDBV2026-Data/data/public_health_response/processed/public_health_response__national_epidemiological_monitoring_en__daily.csv | BDBV2026-Data/build/long/public_health_response__national_epidemiological_monitoring_en.csv | vector | vector |
| public_health_response | BDBV2026-Data/data/public_health_response/processed/public_health_response__national_epidemiological_monitoring_fr__daily.csv | BDBV2026-Data/build/long/public_health_response__national_epidemiological_monitoring_fr.csv | vector | vector |
| public_health_response | BDBV2026-Data/data/public_health_response/processed/public_health_response__national_epidemiological_protection_sexual_exploitation_abuse_en__daily.csv | BDBV2026-Data/build/long/public_health_response__national_epidemiological_protection_sexual_exploitation_abuse_en.csv | vector | vector |
| public_health_response | BDBV2026-Data/data/public_health_response/processed/public_health_response__national_epidemiological_protection_sexual_exploitation_abuse_fr__daily.csv | BDBV2026-Data/build/long/public_health_response__national_epidemiological_protection_sexual_exploitation_abuse_fr.csv | vector | vector |
| public_health_response | BDBV2026-Data/data/public_health_response/processed/public_health_response__national_epidemiological_security_en__daily.csv | BDBV2026-Data/build/long/public_health_response__national_epidemiological_security_en.csv | vector | vector |
| public_health_response | BDBV2026-Data/data/public_health_response/processed/public_health_response__national_epidemiological_security_fr__daily.csv | BDBV2026-Data/build/long/public_health_response__national_epidemiological_security_fr.csv | vector | vector |
| public_health_response | BDBV2026-Data/data/public_health_response/processed/public_health_response__provincial_epidemiological_community_engagement_en__daily.csv | BDBV2026-Data/build/long/public_health_response__provincial_epidemiological_community_engagement_en.csv | vector | vector |
| public_health_response | BDBV2026-Data/data/public_health_response/processed/public_health_response__provincial_epidemiological_community_engagement_fr__daily.csv | BDBV2026-Data/build/long/public_health_response__provincial_epidemiological_community_engagement_fr.csv | vector | vector |
| public_health_response | BDBV2026-Data/data/public_health_response/processed/public_health_response__provincial_epidemiological_coordination_en__daily.csv | BDBV2026-Data/build/long/public_health_response__provincial_epidemiological_coordination_en.csv | vector | vector |
| public_health_response | BDBV2026-Data/data/public_health_response/processed/public_health_response__provincial_epidemiological_coordination_fr__daily.csv | BDBV2026-Data/build/long/public_health_response__provincial_epidemiological_coordination_fr.csv | vector | vector |
| public_health_response | BDBV2026-Data/data/public_health_response/processed/public_health_response__provincial_epidemiological_infection_prevention_controle_en__daily.csv | BDBV2026-Data/build/long/public_health_response__provincial_epidemiological_infection_prevention_controle_en.csv | vector | vector |
| public_health_response | BDBV2026-Data/data/public_health_response/processed/public_health_response__provincial_epidemiological_infection_prevention_controle_fr__daily.csv | BDBV2026-Data/build/long/public_health_response__provincial_epidemiological_infection_prevention_controle_fr.csv | vector | vector |
| public_health_response | BDBV2026-Data/data/public_health_response/processed/public_health_response__provincial_epidemiological_laboratory_en__daily.csv | BDBV2026-Data/build/long/public_health_response__provincial_epidemiological_laboratory_en.csv | vector | vector |
| public_health_response | BDBV2026-Data/data/public_health_response/processed/public_health_response__provincial_epidemiological_laboratory_fr__daily.csv | BDBV2026-Data/build/long/public_health_response__provincial_epidemiological_laboratory_fr.csv | vector | vector |
| public_health_response | BDBV2026-Data/data/public_health_response/processed/public_health_response__provincial_epidemiological_logistics_en__daily.csv | BDBV2026-Data/build/long/public_health_response__provincial_epidemiological_logistics_en.csv | vector | vector |
| public_health_response | BDBV2026-Data/data/public_health_response/processed/public_health_response__provincial_epidemiological_logistics_fr__daily.csv | BDBV2026-Data/build/long/public_health_response__provincial_epidemiological_logistics_fr.csv | vector | vector |
| public_health_response | BDBV2026-Data/data/public_health_response/processed/public_health_response__provincial_epidemiological_management_en__daily.csv | BDBV2026-Data/build/long/public_health_response__provincial_epidemiological_management_en.csv | vector | vector |
| public_health_response | BDBV2026-Data/data/public_health_response/processed/public_health_response__provincial_epidemiological_management_fr__daily.csv | BDBV2026-Data/build/long/public_health_response__provincial_epidemiological_management_fr.csv | vector | vector |
| public_health_response | BDBV2026-Data/data/public_health_response/processed/public_health_response__provincial_epidemiological_monitoring_en__daily.csv | BDBV2026-Data/build/long/public_health_response__provincial_epidemiological_monitoring_en.csv | vector | vector |
| public_health_response | BDBV2026-Data/data/public_health_response/processed/public_health_response__provincial_epidemiological_monitoring_fr__daily.csv | BDBV2026-Data/build/long/public_health_response__provincial_epidemiological_monitoring_fr.csv | vector | vector |
| public_health_response | BDBV2026-Data/data/public_health_response/processed/public_health_response__provincial_epidemiological_protection_sexual_exploitation_abuse_en__daily.csv | BDBV2026-Data/build/long/public_health_response__provincial_epidemiological_protection_sexual_exploitation_abuse_en.csv | vector | vector |
| public_health_response | BDBV2026-Data/data/public_health_response/processed/public_health_response__provincial_epidemiological_protection_sexual_exploitation_abuse_fr__daily.csv | BDBV2026-Data/build/long/public_health_response__provincial_epidemiological_protection_sexual_exploitation_abuse_fr.csv | vector | vector |
| public_health_response | BDBV2026-Data/data/public_health_response/processed/public_health_response__provincial_epidemiological_security_en__daily.csv | BDBV2026-Data/build/long/public_health_response__provincial_epidemiological_security_en.csv | vector | vector |
| public_health_response | BDBV2026-Data/data/public_health_response/processed/public_health_response__provincial_epidemiological_security_fr__daily.csv | BDBV2026-Data/build/long/public_health_response__provincial_epidemiological_security_fr.csv | vector | vector |
| refugee_sites | BDBV2026-Data/data/refugee_sites/processed/refugee_sites__sites__static.csv | BDBV2026-Data/build/long/refugee_sites__sites.csv | vector | vector |
| testing_capacity | BDBV2026-Data/data/testing_capacity/processed/testing_capacity__pcr_machines__static.csv | BDBV2026-Data/build/long/testing_capacity__pcr_machines.csv | vector | vector |
| testing_capacity | BDBV2026-Data/data/testing_capacity/processed/testing_capacity__pcr_tests__static.csv | BDBV2026-Data/build/long/testing_capacity__pcr_tests.csv | vector | vector |
| worldpop | BDBV2026-Data/data/worldpop/processed/worldpop__pop_count__static.csv | BDBV2026-Data/build/long/worldpop__pop_count.csv | vector | vector |
| worldpop | BDBV2026-Data/data/worldpop/processed/worldpop__pop_density__static.csv | BDBV2026-Data/build/long/worldpop__pop_density.csv | vector | vector |

## SQLite load

- Imported CSV tables: 182
- Table names are derived from the source path and sanitized for SQLite.
- Vector tables stay as their own loaded tables; matrix CSVs are loaded as wide tables.


## Key column rules

- `nom`: canonical health-zone name, or `DRC` / province roll-up where the source is not zone-grain.
- `date`: ISO `YYYY-MM-DD` unless the file is a matrix snapshot, where monthly files use `YYYY-MM-01`.
- Count fields: non-negative integers, sometimes `ND` or blank when not reported.
- Proportion fields: decimals in `[0, 1]`.
- Text narrative fields: free text extracted from SitRep narrative sections.
- OD matrices: first logical column is the origin zone, destination columns are canonical zone names.

## Relations

- Zone-grain vectors join to `Nom`.
- Province-grain rows join to `PROVINCE` and are broadcast to each health zone in the province.
- National rows use `DRC` and are broadcast across all zones during GeoJSON build.
- OD matrices are many-to-many between health zones, not one-to-many fact tables.

## Notes

- The database is a starter schema and metadata index, not a replacement for the analytical fact tables.
- Use `ZSCode` for strict joins where zone names collide or duplicate.
- `Bili` and `Lubunga` are the main duplicate-name edge cases in the base shapefile.

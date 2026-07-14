# Data Sources

ViralWatch integrates multiple datasets from the **INRB-UMIE/BDBV2026-Data** repository to support outbreak surveillance, machine learning, and cross-border risk monitoring.

Each dataset provides specific information that contributes to different components of the ViralWatch pipeline.

---

## Primary Data Sources

### 1. `insp_sitrep/`
**Purpose:** Daily epidemiological situation reports.

**Data Includes:**
- Daily confirmed cases
- Daily suspected cases
- Daily deaths
- Hospitalizations
- Contact tracing
- Isolation statistics

**Used For:**
- Epidemic curve visualization
- Case-fatality ratio analysis
- Machine learning feature generation
- Dashboard updates

**Priority:** ⭐⭐⭐⭐⭐

---

### 2. `epi/`
**Purpose:** Weekly WHO epidemiological reports.

**Data Includes:**
- Weekly outbreak summaries
- National surveillance statistics
- Disease progression

**Used For:**
- Weekly trend analysis
- Historical outbreak comparison

**Priority:** ⭐⭐⭐⭐

---

### 3. `worldpop/`
**Purpose:** Population statistics.

**Data Includes:**
- Population count
- Population density

**Used For:**
- Machine learning features
- Risk normalization
- Population-based analysis

**Priority:** ⭐⭐⭐⭐⭐

---

### 4. `osrm/`
**Purpose:** Road network accessibility.

**Data Includes:**
- Road travel time
- Road distance between health zones

**Used For:**
- Accessibility analysis
- Machine learning features
- Healthcare response planning

**Priority:** ⭐⭐⭐⭐⭐

---

### 5. `shapefiles/`
**Purpose:** Geographic boundaries of DRC health zones.

**Data Includes:**
- Health zone polygons
- Administrative boundaries

**Used For:**
- Interactive maps
- Geospatial visualization
- Cross-border dashboard

**Priority:** ⭐⭐⭐⭐⭐

---

### 6. `cross-border-movements/`
**Purpose:** Cross-border mobility data.

**Data Includes:**
- Border crossing estimates
- Passenger movement statistics

**Used For:**
- Cross-border outbreak monitoring
- Risk assessment

**Priority:** ⭐⭐⭐⭐

---

### 7. `flowminder/`
**Purpose:** Human mobility information.

**Data Includes:**
- Population inflow
- Population outflow
- Movement estimates

**Used For:**
- Disease spread modeling
- Mobility analysis

**Priority:** ⭐⭐⭐⭐

---

### 8. `testing_capacity/`
**Purpose:** Laboratory testing resources.

**Data Includes:**
- PCR machine availability
- Testing capacity

**Used For:**
- Healthcare preparedness analysis
- Laboratory capacity assessment

**Priority:** ⭐⭐⭐

---

### 9. `grid3_healthsites/`
**Purpose:** Healthcare facility locations.

**Data Includes:**
- Health facility count
- Health facility density

**Used For:**
- Healthcare accessibility
- Resource availability analysis

**Priority:** ⭐⭐⭐⭐

---

### 10. `healthsites_io/`
**Purpose:** Open-source healthcare facility dataset.

**Data Includes:**
- Healthcare facility locations
- Facility counts

**Used For:**
- Additional healthcare infrastructure mapping

**Priority:** ⭐⭐⭐

---

### 11. `public_health_response/`
**Purpose:** Public health intervention indicators.

**Data Includes:**
- Coordination activities
- Laboratory response
- Surveillance
- Community engagement
- Infection prevention and control

**Used For:**
- Public health response monitoring
- Dashboard context information

**Priority:** ⭐⭐⭐

---

### 12. `refugee_sites/`
**Purpose:** Refugee settlement information.

**Data Includes:**
- Refugee site locations
- Refugee site counts

**Used For:**
- Population vulnerability assessment
- Humanitarian response planning

**Priority:** ⭐⭐

---

# Summary

| Dataset | Description | Primary Use | Priority |
|----------|-------------|-------------|----------|
| `insp_sitrep` | Daily outbreak situation reports | Epidemiological analysis & ML | ⭐⭐⭐⭐⭐ |
| `epi` | Weekly WHO epidemiological reports | Trend analysis | ⭐⭐⭐⭐ |
| `worldpop` | Population statistics | Population features | ⭐⭐⭐⭐⭐ |
| `osrm` | Road travel time & distance | Accessibility analysis | ⭐⭐⭐⭐⭐ |
| `shapefiles` | Health zone boundaries | Mapping & visualization | ⭐⭐⭐⭐⭐ |
| `cross-border-movements` | Border movement estimates | Cross-border surveillance | ⭐⭐⭐⭐ |
| `flowminder` | Human mobility | Disease spread analysis | ⭐⭐⭐⭐ |
| `testing_capacity` | PCR testing resources | Healthcare preparedness | ⭐⭐⭐ |
| `grid3_healthsites` | Health facility locations | Healthcare accessibility | ⭐⭐⭐⭐ |
| `healthsites_io` | Additional health facilities | Infrastructure mapping | ⭐⭐⭐ |
| `public_health_response` | Public health response indicators | Response monitoring | ⭐⭐⭐ |
| `refugee_sites` | Refugee settlement data | Vulnerability assessment | ⭐⭐ |

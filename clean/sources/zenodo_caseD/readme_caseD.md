# AIJ UWE Benchmark Dataset – Case D (Highrise): Wind Tunnel Experiment for Flow around a High-rise Building in City Blocks

## Investigators

### Data Collector

- Yoshihide Tominaga (Niigata Institute of Technology, Japan)

### Dataset Editors and Distributors

- Hideki Kikumoto (The University of Tokyo, Japan)  
- Tsubasa Okaze (Institute of Science Tokyo, Japan)

### Contact for Questions

Yoshihide Tominaga  
Email: tominaga@abe.niit.ac.jp

---

## Overview

This dataset provides wind tunnel measurement results for a high-rise building placed within a district of low-rise buildings. It forms part of the AIJ UWE (Urban Wind Environment) benchmark cases for CFD validation. Wind speed and turbulence data are included for multiple approach flow directions.

---

## Dataset Contents

### File List

- **AF_caseD.csv**  
  Vertical profile of the approaching flow.  
  **Columns:**  
  
  - `z` (m): Height  
  - `U` (m/s): Mean velocity  
  - `k` (m2/s2): Turbulent kinetic energy

- **RS-S_caseD.csv**  
  Hot-wire anemometer data with split fiber probe for 0° approach flow.  
  **Columns:**  
  
  - `No.`: Measurement point ID
  - `x`, `y`, `z` (m): Coordinates  
  - `U`, `V`, `W`, `Vs` (m/s): Mean velocity components and magnitude
  - `u_rms`, `v_rms`, `w_rms` (m/s): Velocity fluctuation RMS  
  - `k` (m2/s2): Turbulent kinetic energy  
    **Note:** `-999.9` denotes unmeasured data.

- **RS-T_caseD.csv**  
  Scalar wind speed from thermistor anemometer (multiple directions: 0°, 22.5°, and 45°).  
  **Columns:**  
  
  - `No.`: Measurement point ID
  - `WD` (deg): Approach flow directions
  - `x`, `y`, `z` (m): Coordinates  
  - `Vs` (m/s): Mean scalar wind speed  
    **Note:** `-999.9` denotes unmeasured data.

- **MP_caseD.png**  
  Measurement point layout at `z/H = 0.02` (2 m at full scale).  
  
  - Legend:  
    - ○: Measured with both hot-wire and thermistor  
    - ●: Thermistor only  
    - ×: Unmeasured

- **BD_caseD.stl**  
  Building geometry of the model (1:400 scale)

- **LF_caseD.xls**  
  Legacy Excel version of the measurement dataset, provided as per the AIJ guidelines. Also available via: [Guidebook for CFD Predictions of Urban Wind Environment](https://www.aij.or.jp/jpn/publish/cfdguide/index_e.htm)

---

## Experimental Methodology

### Experimental Setup

- Model scale: 1:400  
- High-rise building: 0.0625 × 0.0625 × 0.25 m (25 × 25 × 100 m full scale), H = 0.25 m
- Low-rise blocks: 0.1 × 0.1 × 0.025 m (40 × 40 × 10 m full scale)
- Inflow velocity at the central building height: U_H = 6.65 m/s
- Reynolds number (based on high-rise height and upstream velocity): approx. 110,000
- Measurement height: `z/H = 0.02` (2 m at full scale)

### Instrumentation

- **Hot-wire anemometer (split fiber probe)**  
  
  - Used in 0° wind direction case  
  - Sampling rate: 100 Hz  
  - Duration: 60 seconds

- **Thermistor anemometer**  
  
  - Used for scalar wind speed in all directions  
  - Sampling rate: N/A

### Measurement Locations

Niigata Institute of Technology, Kashiwazaki, Japan

---

## Metadata

- **Units:**  
  - Length: meters (m)  
  - Velocity: meters per second (m/s)  
- **File creation date:** 21 April, 2025  
- **Format:** CSV, PNG, STL, XLS  
- **Unmeasured values:** Represented by `-999.9`  
- **License:** CC BY 4.0  
- **Version:** 1.0  

---

## Data Accessibility

- **Repository name:** Zenodo  
- **DOI:** 10.5281/zenodo.15402668
- **Direct URL:** https://zenodo.org/records/15402668

---

## Related Articles

- Tominaga, Y., Mochida, A., Yoshie, R., Kataoka, H., Nozu, T., Yoshikawa, M., & Shirasawa, T. (2008). *AIJ guidelines for practical applications of CFD to pedestrian wind environment around buildings*. *Journal of Wind Engineering and Industrial Aerodynamics*, 96, 1749–1761. https://doi.org/10.1016/j.jweia.2008.02.058

- JAR data paper (in preparation)

---

*Note: This dataset supports CFD validation for pedestrian wind environment around high-rise buildings in complex urban forms.*
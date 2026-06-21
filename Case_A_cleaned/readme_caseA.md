# AIJ UWE Benchmark Dataset – Case A (112): Wind Tunnel Experiment for Flow around a 1:1:2 Shape Building Model

## Investigators

### Data Collectors

- Takeshi Ishihara (The University of Tokyo, Japan)  
- Kazuki Hibi (Numerical Flow Design, Japan)

### Dataset Editors and Distributors

- Yoshihide Tominaga (Niigata Institute of Technology, Japan)  
- Hideki Kikumoto (The University of Tokyo, Japan)  
- Tsubasa Okaze (Institute of Science Tokyo, Japan)

### Contact for Questions

Takeshi Ishihara  
E-mail: [ishihara@bridge.t.u-tokyo.ac.jp](mailto:ishihara@bridge.t.u-tokyo.ac.jp)

---

## Overview

This dataset contains wind tunnel measurement results from the AIJ UWE (Urban Wind Environment) benchmark model "Case A", consisting of a 1:1:2 (width:depth:height) scale building model. The data includes approach flow characteristics, spatial wind velocity measurements, and visualization of measurement locations.

---

## Dataset Contents

### File List

- **AF-caseA.csv**  
  Vertical profile of the approaching flow.  
  **Columns:**  
  
  - `z` (m): Height  
  - `U` (m/s): Mean streamwise velocity  
  - `u_rms`, `v_rms`, `w_rms` (m/s): Root-mean-square values of turbulence components  
  - `k` (m2/s2): Turbulent kinetic energy

- **RS-caseA.csv**  
  Measurement results at various locations around the building.  
  **Columns:**  
  
  - `Point No.`: Measurement ID  
  - `x`, `y`, `z` (m): Coordinates  
  - `U`, `V`, `W` (m/s): Mean velocities in x, y, z directions  
  - `u_rms`, `v_rms`, `w_rms` (m/s): Root-mean-square of velocity fluctuations  
  - `k` (m2/s2): Turbulent kinetic energy

- **MP-y_caseA.png**  
  Measurement point distribution on the vertical center plane (`y/b = 0`).

- **MP-z_caseA.png**  
  Measurement point distribution on two horizontal planes (`z/b = 0.125` and `1.25`).

- **LF_caseA.xls**  
  Legacy Excel version of the measurement dataset, provided as per the AIJ guidelines. Also available via: [Guidebook for CFD Predictions of Urban Wind Environment](https://www.aij.or.jp/jpn/publish/cfdguide/index_e.htm)

---

## Experimental Methodology

### Experimental Setup

- Model dimensions: b = 0.08 m (width, depth), H = 2b = 0.16 m (height)  
- Reynolds number based on building height H and approach wind speed at H: approx. 24,000
- Measurement planes:
  - Vertical center plane: `y/b = 0`
  - Horizontal planes: `z/b = 0.125` and `1.25`

### Instrumentation

- Devices: Hot-wire anemometer with split fiber probes  
  - Streamwise: DANTEC 55R55  
  - Spanwise & Vertical: DANTEC 55R57  
- Sampling rate: 1000 Hz for 60 seconds per point  
- Low-pass filter cutoff: 500 Hz

### Location

Technical Research Institute, Shimizu Corporation, Tokyo, Japan

---

## Metadata

- **Units:**  
  - Length: meters (m)  
  - Wind velocity: meters per second (m/s)  
- **File creation date:** 21 April, 2025  
- **Format:** CSV, PNG, XLS  
- **Missing values:** None  
- **License:** [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)  
- **Version:** 1.0
- **Citation requested:** Meng, Y., & Hibi, K. (1998). *Turbulent measurements of the flow field around a high-rise building*. Journal of Wind Engineering, JAWE, 76, 55?64.

---

## Data Accessibility

- **Repository name:** Zenodo  
- **DOI:** 10.5281/zenodo.15050147
- **Direct URL:** https://zenodo.org/records/15050147

---

## Related Articles

- Meng, Y., & Hibi, K. (1998). *Turbulent measurements of the flow field around a high-rise building*. Journal of Wind Engineering, JAWE, 76, 55?64. [https://doi.org/10.5359/jawe.1998.76_55]()

- Mochida, A., Tominaga, Y., Murakami, S., Yoshie, R., Ishihara T., Ooka, R., 2002. Comparison of various k-ε model and DSM applied to flow around a high-rise building - report on AIJ cooperative project for CFD prediction of wind environment -，Wind & Structures, vol. 5, no. 2-4, 227-244. 
  [https://doi.org/10.12989/was.2002.5.2_3_4.227]()

---

*Note: This dataset is part of the AIJ urban wind environment benchmark project, which aims to support the development and validation of urban flow simulations.*
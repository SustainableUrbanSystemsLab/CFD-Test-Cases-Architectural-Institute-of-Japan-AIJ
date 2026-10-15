# AIJ UWE Benchmark Dataset – Case B (144): Wind Tunnel Experiment for Flow around a 1:4:4 Shape Building Model

## Investigators

### Data Collector

- Yoshihide Tominaga (Niigata Institute of Technology, Japan)

### Dataset Editors and Distributors

- Hideki Kikumoto (The University of Tokyo, Japan)  
- Tsubasa Okaze (Institute of Science Tokyo, Japan)

### Contact for Questions

Yoshihide Tominaga  
E-mail: [tominaga@abe.niit.ac.jp](mailto:tominaga@abe.niit.ac.jp)

---

## Overview

This dataset contains wind tunnel measurement results from the AIJ UWE (Urban Wind Environment) benchmark model "Case B", consisting of a 1:4:4 (depth:width:height) building model. The data includes vertical and horizontal plane velocity fields and approach flow profiles.

---

## Dataset Contents

### File List

- **AF_caseB.csv**  
  Vertical profile of the approaching flow.  
  **Columns:**  
  
  - `z` [m]: Height  
  - `U` [m/s]: Mean streamwise velocity
  - `1/4 power` [m/s]: Mean streamwise velocity fitted with a power function of index 1/4
  - `<u'2>`, `<v'2>`, `<w'2>` [m²/s²]: Variance of turbulence components  
  - `k` [m²/s²]: Turbulent kinetic energy

- **RS_caseB.csv**  
  Wind velocity measurements around the building.  
  **Columns:**  
  
  - `Point No.`: Measurement ID  
  - `x`, `y`, `z` [mm]: Coordinates  
  - `U`, `V`, `W` [m/s]: Mean velocities in x, y, z directions  
  - `<u'2>`, `<v'2>`, `<w'2>` [m²/s²]: Variance of velocity fluctuations  
  - `k` [m²/s²]: Turbulent kinetic energy

- **MP-y_caseB.png**  
  Measurement point layout on the vertical center plane (`y/H = 0`).

- **MP-z_caseB.png**  
  Measurement point layout on the horizontal plane at `z/H = 1/16`.

- **LF_caseB.xls**  
  Legacy Excel version of the measurement dataset, provided as per the AIJ guidelines. Also available via: [Guidebook for CFD Predictions of Urban Wind Environment](https://www.aij.or.jp/jpn/publish/cfdguide/index_e.htm)

---

## Experimental Methodology

### Experimental Setup

- Model dimensions: 0.05 m (depth), 0.20 m (width), 0.20 m (height)  
- Reynolds number based on building height and mean approach flow velocity at height *H*: approx. 72,000
- Measurement planes:
  - Vertical center plane: `y/H = 0`
  - Horizontal plane: `z/H = 1/16`

### Instrumentation

- Location: Niigata Institute of Technology, Kashiwazaki, Japan  
- Device: Hot-wire anemometer with split fiber probe  
- Sampling rate: 100 Hz  
- Measurement duration: 60 seconds per point  

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
- **Citation requested:** Miyazaki, T., Tominaga, Y., 2003. *Wind tunnel experiment on flow field around a building model with a scale ratio of 4:4:1 placed within the surface boundary layer*. Proceedings of Annual Meeting of Hokuriku Chapter, Architectural Institute of Japan, 201-204. (in Japanese)  https://www.aij.or.jp/paper/detail.html?productId=313933

---

## Data Accessibility

- **Repository name:** Zenodo  
- **DOI:** 10.5281/zenodo.15401455 
- **Direct URL:** https://zenodo.org/records/15401455

---

## Related Articles

- Miyazaki, T., Tominaga, Y., 2003. *Wind tunnel experiment on flow field around a building model with a scale ratio of 4:4:1 placed within the surface boundary layer*. Proceedings of Annual Meeting of Hokuriku Chapter, Architectural Institute of Japan, 201-204. (in Japanese)  https://www.aij.or.jp/paper/detail.html?productId=313933
- Tominaga, Y., Mochida, A., Yoshie, R., Kataoka, H., Nozu, T., Yoshikawa, M., & Shirasawa, T. (2008). *AIJ guidelines for practical applications of CFD to pedestrian wind environment around buildings*. *Journal of Wind Engineering and Industrial Aerodynamics*, 96, 1749–1761. https://doi.org/10.1016/j.jweia.2008.02.058

---

*Note: This dataset is part of the AIJ Urban Wind Environment benchmark project to support CFD model validation.*
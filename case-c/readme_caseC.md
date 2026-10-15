# AIJ UWE Benchmark Dataset – Case C (Blocks): Wind Tunnel Experiment for Flow within Simple Building Blocks

## Investigators

### Data Collector

- Yoshitami Nonomura (Yamato University, Japan)

### Dataset Editors and Distributors

- Yoshihide Tominaga (Niigata Institute of Technology, Japan)  
- Hideki Kikumoto (The University of Tokyo, Japan)  
- Tsubasa Okaze (Institute of Science Tokyo, Japan)

### Contact for Questions

Yoshitami Nonomura  
Email: nonomura.yoshitami@yamato-u.ac.jp

---

## Overview

This dataset contains wind tunnel measurement results from the AIJ UWE benchmark "Case C", which simulates urban wind flow around a 3×3 city block array. The center building was tested at three different heights (0D, 1D, 2D), and scalar wind speeds were measured at pedestrian height.

---

## Dataset Contents

### File List

- **AF_caseC.csv**  
  Vertical profile of the approach flow.  
  **Columns:**  
  
  - `z` (m): Height  
  - `U` (m/s): Mean velocity  
  - `u_rms` (m/s): Root-mean-square of velocity fluctuations

- **RS_caseC.csv**  
  Scalar wind speed measurements at horizontal plane `z/D = 0.1`.  
  **Columns:**  
  
  - `No.`: Measurement point ID  
  - `WD`: Wind direction  
  - `CB`: Center building configuration (0D, 1D, 2D)  
  - `x`, `y`, `z` (m): Coordinates  
  - `Vs` (m/s): Mean scalar wind speed  
    **Note:** Missing point numbers: 1, 2, 3, 34, 35, 36, 37, 46, 55, 100, 101, 102

- **MP-z_caseC.png**  
  Measurement point layout at the horizontal plane (`z/D = 0.1`).

- **LF_caseC.xls**  
  Legacy Excel version of the measurement dataset, provided as per the AIJ guidelines. Also available via: [Guidebook for CFD Predictions of Urban Wind Environment](https://www.aij.or.jp/jpn/publish/cfdguide/index_e.htm)

---

## Experimental Methodology

### Setup

- City block layout: 3×3 configuration  
- Surrounding building size: D = 0.20 m (cube)  
- Center building height: tested at 0D (none), 1D (same as others), and 2D  
- Reynolds number based on block size and approach flow: approx. 52,000

### Instrumentation

- Scalar wind speed (Vs) measured using thermistor anemometer at `z/D = 0.1`  
  - Sampling rate: 1.0 Hz  
  - Duration: 30 seconds  
- Approach flow measured using I-type hot wire anemometer  
  - Sampling rate: 500 Hz  
  - Duration: 30 seconds

### Location

Technology Development Division, Fujita Corporation, Tokyo, Japan

---

## Metadata

- **Units:**  
  - Length: meters (m)  
  - Velocity: meters per second (m/s)  
- **File creation date:** 21 April, 2025  
- **Format:** CSV, PNG, XLS  
- **Missing values:** noted in `RS_caseC.csv`  
- **License:** CC BY 4.0  
- **Version:** 1.0  
- **Citation requested:** Nonomura, Y., Kobayashi, N., Tominaga, Y., Mochida, A., 2003. *The cross comparison of CFD results for flow field around building models (part 3): The wind tunnel test for the varification models on the flowfield around building blocks*. Japan Association for Wind Engineering, 95, 83-84. (in Japanese)  https://doi.org/10.14887/jaweam.2003.0.41.0

---

## Data Accessibility

- **Repository name:** Zenodo  
- **DOI:** 10.5281/zenodo.15401791
- **Direct URL:** https://zenodo.org/records/15401791

---

## Related Articles

- Nonomura, Y., Kobayashi, N., Tominaga, Y., Mochida, A., 2003. *The cross comparison of CFD results for flow field around building models (part 3): The wind tunnel test for the varification models on the flowfield around building blocks*. Japan Association for Wind Engineering, 95, 83-84. (in Japanese)  https://doi.org/10.14887/jaweam.2003.0.41.0

- Tominaga, Y., Mochida, A., Yoshie, R., Kataoka, H., Nozu, T., Yoshikawa, M., & Shirasawa, T. (2008). *AIJ guidelines for practical applications of CFD to pedestrian wind environment around buildings*. *Journal of Wind Engineering and Industrial Aerodynamics*, 96, 1749–1761. https://doi.org/10.1016/j.jweia.2008.02.058

- JAR data paper (in preparation)

---

*Note: This dataset is part of the AIJ Urban Wind Environment benchmark project to support CFD model validation in complex urban layouts.*
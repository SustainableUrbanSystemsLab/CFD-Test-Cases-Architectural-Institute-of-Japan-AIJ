# AIJ UWE Benchmark Dataset – Case E (Niigata): Wind Tunnel Experiment for Flow within an Actual Urban Area in Niigata

## Investigators

### Data Collector

- Yoshihide Tominaga (Niigata Institute of Technology, Japan)

### Dataset Editors and Distributors

- Hideki Kikumoto (The University of Tokyo, Japan)  
- Tsubasa Okaze (Institute of Science, Tokyo Japan)

### Contact for Questions

Yoshihide Tominaga  
Email: tominaga@abe.niit.ac.jp

---

## Overview

This dataset contains wind tunnel measurement results from a real urban district in Niigata City, Japan, featuring a dense layout of low-rise two-story buildings. The experiments represent both pre- and post-construction conditions of a 60 m high-rise (Building A) and two 18 m mid-rise buildings (Buildings B and C). The model was scaled at 1:250, and wind conditions were measured at pedestrian height.

---

## Dataset Contents

### File List

- **AF_caseE.csv**  
  Vertical profile of the approaching flow.  
  **Columns:**  
  
  - `z` (m): Height (actual scale)
  - `U` (m/s): Mean wind velocity
  - `k` (m2/s2): Turbulent kinetic energy

- **RS_caseE.csv**  
  Measurement results.  
  **Columns:**  
  
  - `No.`: Measurement point ID
  - `case`: Case name (bc: before construction, ac: after construction)
  - `Wind_direction`: Wind direction (16 wind directions)
  - `x`, `y`, `z` (m): Coordinates (actual scale)
  - `Velocity_Ratio` (-): Velocity ratio at 2m (Mean velocity value normalized by the inflow velocity at 15.9 m (the measuring height of Niigata meteorological station))

- **MP_caseE.png**  
  Measurement point layout at `z = 0.008 m` (corresponds to 2.0 m actual scale).
  
  - Red points: Measurement locations  
  - Blue point: Origin

- **BD_caseE.stl**  
  STL file representing the building geometry after the construction of Buildings A, B, and C.

- **LF_caseE.xls**  
  Legacy Excel version of the measurement dataset, provided as per the AIJ guidelines. Also available via: [Guidebook for CFD Predictions of Urban Wind Environment](https://www.aij.or.jp/jpn/publish/cfdguide/index_e.htm)

---

## Experimental Methodology

### Experimental Setup

- District model: Niigata City urban area near Shinano River  
- Scale: 1/250  
- Buildings:  
  - High-rise: 60 m full-scale (0.24 m in model)  
  - Mid-rise: 18 m full-scale (0.072 m in model)  
- Reynolds number (based on approach velocity and building height): approx. 17,000  
- Measurement height: `z = 0.008 m` (2 m full scale)

### Instrumentation

- Thermistor anemometer  
  - Sampling frequency: 100 Hz  
  - Duration: 60 seconds per point  
  - Measurement type: Mean scalar wind speed

### Location

Wind tunnel at Niigata Institute of Technology, Kashiwazaki, Japan

---

## Metadata

- **Units:**  
  - Length: meters (m)  
  - Wind speed: meters per second (m/s)  
- **File creation date:** 21 April, 2025  
- **Format:** CSV, PNG, STL, XLS  
- **Missing values:** None  
- **License:** CC BY 4.0  
- **Version:** 1.0  

---

## Data Accessibility

- **Repository name:** Zenodo  
- **DOI:** 10.5281/zenodo.15429017
- **URL:** https://zenodo.org/records/15429017

---

## Related Articles

- Tominaga, Y., Mochida, A., Yoshie, R., Kataoka, H., Nozu, T., Yoshikawa, M., & Shirasawa, T. (2008). *AIJ guidelines for practical applications of CFD to pedestrian wind environment around buildings*. *Journal of Wind Engineering and Industrial Aerodynamics*, 96, 1749–1761. https://doi.org/10.1016/j.jweia.2008.02.058

---



*Note: This dataset supports CFD validation in realistic urban environments and is part of the AIJ Urban Wind Environment benchmark series.*
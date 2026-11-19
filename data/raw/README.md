# Dataset for: Performance evaluation of two-phase direct-to-chip liquid cooling combined with air cooling for data centers

Taken from: https://zenodo.org/records/23237930

Experimental time series from nine air-cooled Open Compute Project (OCP) Winterfell servers (2 x Intel Xeon E5-2678 v3 each), tested in the RISE server wind tunnel (RISE ICE datacenter, Luleå, Sweden) with air cooling only and with a ZutaCore HyperCool two-phase direct-to-chip system retrofitted on the CPUs (hybrid cooling).

Supplement to: V.E. Ahmadi, H.A. Barestrand, J. Summers, C. Yilmaz, *Case Studies in Thermal Engineering* 78 (2026) 107650, DOI 10.1016/j.csite.2026.107650.

Funding: HEATWISE project, EU Horizon Europe grant agreement 101138491; Swiss SERI contract 23.00606.

## Files

| File | Content | Rows x columns |
|---|---|---|
| `data/ocp_air_cooling_5min.csv` | Air-cooling benchmark, 2024-10-31 10:00 to 2024-11-05 01:00 (cases 1-5) | 1333 x 219 |
| `data/ocp_hybrid_cooling_5min.csv` | Hybrid cooling, 2024-09-20 15:30 to 2024-09-23 05:00 (cases 6-8), incl. HRU/refrigerant/facility-loop data | 739 x 227 |
| `data/ocp_hybrid_cpu_core_frequency_5min.csv` | Same hybrid period; per-server utilisation, CPU temperature and per-core frequency (used for the throttling analysis) | 739 x 224 |
| `CASES.csv` | The eight test cases of Table 2 with the time window of each | 8 x 9 |
| `DATA_DICTIONARY.csv` | Every column: description, unit, confidence, original source column name | - |
| `scripts/build_clean_csv.py` | Script that produced the CSVs from the original Excel files (input/output paths are those of the curation environment) | - |

## Test cases (paper Table 2)

| Case | Mode | Inlet air (degC) | DP setpoint (kPa) | Vapor setpoint (degC) | File |
|---|---|---|---|---|---|
| 1 | Air | 25 | 2 | - | air |
| 2 | Air | 35 | 4 | - | air |
| 3 | Air | 45 | 6 | - | air |
| 4 | Air | 45 | 8 | - | air |
| 5 | Air | 45 | 10 | - | air |
| 6 | Hybrid | 25 | 2 | 45 | hybrid |
| 7 | Hybrid | 35 | 2 | 45 | hybrid |
| 8 | Hybrid | 45 | 2 | 45 | hybrid |

Within each case the load was stepped through 100 %, 75 %, 50 %, 25 % and idle (stress-ng).

The `case_id` column was **derived** during curation: a row belongs to a case if it lies within a stable stretch (at least 20 samples) of constant inlet-temperature and differential-pressure setpoints. Rows outside these stretches (start-up and transitions between cases) have an empty `case_id`. The original source files contain no case label.

## Format and conventions

- UTF-8 CSV, comma separated, decimal point, one header row, empty cell = no value.
- `time_local`: 5-minute timestamps, `YYYY-MM-DD HH:MM:SS`. The time zone is not stated in the source files (presumably local time, Sweden).
- Column names carry the unit as suffix (`_C`, `_W`, `_Pa`, `_bar`, `_mbar`, `_Hz`, `_rpm`, `_m3_h`) and a per-server index as `srv1` ... `srv9` (`__mean` = mean over servers/sensors).
- Values were converted from text with units in the original files ("25 °C", "2,10 Pa", "200 mPa") to plain numbers; millipascal values were converted to Pa. No other values were modified.
- Air file: the HRU/refrigerant/facility-loop columns are empty in the source (not applicable) and were removed.

## Measurement uncertainty (from the paper, Section 2.8)

Wind-tunnel temperature sensors +/-0.1 degC; pressure transducers +/-0.1 Pa; CPU temperatures via IPMI +/-0.5 degC; energy meter +/-5 W. The paper reports time-averaged values over steady-state periods of at least 10 min, with server-to-server CPU temperature spread within +/-3 degC.

## Known limitations

1. The data are 5-minute values. The paper (Section 2.7) says the acquisition system handles data at intervals of 1 minute or less, but does not state the sampling interval of these tests or whether the 5-minute values were averaged or sampled. Any higher-resolution raw data are not included. (To be clarified with the authors.)
2. Fans of the servers were fixed at the lowest setting (900 rpm), so air flow is set by the tunnel differential pressure.
3. Uninsulated piping and manifold behind the servers absorb heat from the air side, about 200 W at 25 degC inlet (paper Section 4.3). This inflates the liquid-side share at higher inlet temperatures.
4. Memory frequency and timings were not recorded; memory throttling at about 76 degC DIMM temperature is inferred from the temperature plateau.
5. Server 1 in the hybrid runs: `ocp_hybrid_cooling_5min.csv` has no utilisation or CPU-frequency columns for server 1 (power and temperatures are present). Server-1 utilisation is available in `ocp_hybrid_cpu_core_frequency_5min.csv`; server-1 frequency is not available.
6. Utilisation values above 100 % occur in the source data.
7. Per-core frequency columns are only given for servers 2-9, and for the CPU labelled `cpu_1` in the source.
8. Electrical power of the HRU and the facility-side pump, needed for the PUE in Table 3 of the paper, is not a separate column; the overhead in the paper includes estimated values.
9. Columns marked `low` confidence in `DATA_DICTIONARY.csv` (for example `tunnel_pressure_WT3_SA7_Pa`, `tunnel_fan_power_raw`, dry-cooler temperatures) have descriptions inferred during curation and still need confirmation by the data owners. Column groups `cpu_freq_Hz__*_mean/max/min` were assigned from value magnitudes.
10. The cold-plate internal geometry is supplier-proprietary and not part of this dataset.

## Licence

To be confirmed by the authors; CC BY 4.0 is proposed, matching the article.

## Contact and curation

Corresponding author of the article: Henrik A. Barestrand (RISE). Data curation: Richa Upadhyay (RISE).

## How to cite

Cite the article above and this dataset's DOI (assigned by Zenodo on publication).

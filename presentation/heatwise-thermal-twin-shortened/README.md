# Eight-minute concept presentation

This version sets the foundation for a thermal digital twin. It explains the
problem, data, proposed PCE/PI-PCE methods and comparison plan. Model results and
claims of demonstrated control are intentionally absent. The later final
presentation will assess predictions, sensitivity and the operating-point concept.

**Spoken route: slides 1-12 only.** PDF page 13 is a clickable backup index;
the 24 technical backups are labeled A1-F3. The handover is before slide 7:
four minutes per presenter. The timings are a
rehearsal target, not a measured delivery time.

| Slide | Time | Presenter | Message |
| --- | --- | --- | --- |
| 1 | 0:00-0:10 | 1 | Cover |
| 2 | 0:10-0:50 | 1 | Motivation, heat drivers and research question |
| 3 | 0:50-1:25 | 1 | RISE ICE Datacenter photo and experiment |
| 4 | 1:25-2:00 | 1 | Why measured rather than simulated targets |
| 5 | 2:00-2:55 | 1 | From time series to 19 observations |
| 6 | 2:55-4:00 | 1 | PCE and its reference distributions |
| 7 | 4:00-5:05 | 2 | PI-PCE with monotonicity constraints |
| 8 | 5:05-6:00 | 2 | Fair comparison on held-out cases |
| 9 | 6:00-6:40 | 2 | UQ and reference sensitivity |
| 10 | 6:40-7:25 | 2 | Digital twin: decisions, safety and learning |
| 11 | 7:25-7:55 | 2 | Foundation now; evidence for the final presentation |
| 12 | 7:55-8:00 | 2 | Closing |

Use [speaker_notes.md](speaker_notes.md) to rehearse. It includes transitions,
pointing cues, a four-minute handover and short answers for likely questions.
Avoid explaining the backup equations during the main talk.

## Build

In VS Code, save your changes and press **Ctrl+Shift+B**. The default build task
is **Build HEATWISE shortened presentation**, which updates this version's PDF.
For the longer deck, use **Terminal > Run Task > Build HEATWISE presentation**.

From the repository root, using the existing Python environment and LuaLaTeX:

```powershell
.\.venv\Scripts\python.exe presentation/heatwise-thermal-twin-shortened/build.py
```

Output: [pdf/heatwise-thermal-twin-shortened.pdf](pdf/heatwise-thermal-twin-shortened.pdf).
On other installations, use `python`/`python3`, or pass `--engine` with the LuaLaTeX path.
Compilation intermediates remain in this version's own `build/` directory.

The shared RWTH template stays in `../rwth-ci/`. The cover image and original
backup graphics are referenced in place. Keep this directory inside the repository.

## Readable data figure

Slide 5 uses a new vector figure with larger labels and only two signals. Its
green bands use the exact saved start/end times of all 19 accepted intervals.
The temperature curve shows the maximum of 18 recorded CPU values, leaving a gap
when any CPU is missing. The fitted target remains the maximum of the 18 interval
means; it is not the average of the plotted curve or an instantaneous peak.

Rebuild the figure without fitting any model:

```powershell
.\.venv\Scripts\python.exe -B presentation/heatwise-thermal-twin-shortened/scripts/build_figures.py
```

The script checks all 19 targets against raw data and writes provenance hashes to
`images/selection_readable.json`. It does not rerun selection or change raw data.

## Complete information and organized backups

Every non-introduction content slide in the longer presentation is preserved in
full in the categorized backups. Headings, backup codes and Index navigation
are added; B1 also has evenly distributed vertical spacing. Original introductory information is condensed into
the main talk: motivation on slide 2, experiment/photo on slide 3, choice of
measurements on slide 4, and the twin concept/three loops on slide 10.

| Backup category | Codes | PDF pages |
| --- | --- | --- |
| Data and preprocessing | A1-A7 | 14-20 |
| PCE and input reference | B1-B4 | 21-24 |
| PI-PCE and comparison | C1-C4 | 25-28 |
| UQ and sensitivity | D1-D2 | 29-30 |
| Digital twin and operating choices | E1-E4 | 31-34 |
| Outlook and references | F1-F3 | 35-37 |

Click any code on the index (page 13), or follow detail links on main slides.
Every backup shows its code in the title/footer and has an **Index** return link.
The PDF bookmarks also group backups by category. Refer to **A5** for the full
selection checklist, **B1** for software roles/logo, and **E2** for model updates
and version approval.

[coverage_map.md](coverage_map.md) maps **all 30 longer-deck slides** to their
locations here and lists each backup's physical PDF page. `coverage.json` records
source-body hashes. Regenerate the organized backups and check preservation:

```powershell
.\.venv\Scripts\python.exe -B presentation/heatwise-thermal-twin-shortened/scripts/build_backups.py
```

The script verifies all 24 non-introduction content bodies against their sources,
undoing B1's spacing-only adjustment, and checks that no source slide is missed.
Rebuild the PDF afterwards. The
original presentation, scientific code, observations and model results remain
unchanged. This deck now has **37 PDF pages: 12 main, 1 index, 24 backups**.

## Editing

- `main.tex`: shared style, cover and document structure.
- `sections/concept.tex`: all eleven frames after the cover, with timing comments.
- `sections/backup.tex`: generated supporting material outside the eight-minute route; edit its original source or generator deliberately.
- `speaker_notes.md`: explanations and the handover, kept out of the projected PDF.

Future fitting is described as planned work in the talk. Existing implementation
and trial results remain available in the repository for later work; this PDF
neither imports them nor presents their scores.

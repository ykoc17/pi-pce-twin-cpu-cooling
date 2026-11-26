# HEATWISE thermal twin presentation

Current deck: **30 PDF pages: 23 main slides and 7 backup slides**.
Cover date: **1.12.2026**. The assigned talk is eight minutes, equally split
between Yagiz Koc and Ina Dzingarska. A short spoken route is still required.
This is a project-concept presentation: PCE/PI-PCE fitting and comparison are presented as future work. Earlier reviews describe earlier versions.

## Current slide map

| Slides | Source | Content |
| --- | --- | --- |
| 1 | main.tex | RWTH photo cover, authors and date |
| 2-5 | introduction.tex | Motivation, dataset, twin concept, experimental-data choice |
| 6-7 | pce-introduction.tex; uq-sobol-overview.tex | PCE, coefficient moments and hypothetical reference Sobol analysis |
| 8-10 | input-data.tex | Measured ranges/cases, sparsity, suspected throttling and dependence |
| 11-14 | pce-implications.tex; input-data.tex; preprocessing-results.tex; input-distributions.tex | Approximately steady selection, 19 rows, conditioning and basis reference |
| 15 | physics-informed.tex | Proposed PI-PCE with monotonicity constraints and measured-target least squares |
| 16 | physics-informed.tex | Planned PCE vs PI-PCE comparison; no model results |
| 17-18 | conditional-moments.tex; conditional-sensitivity.tex | Illustrative conditional moments and sensitivity interpretation |
| 19 | optimization.tex | Proposed robust constraint, validated-domain restriction and deployment gate |
| 20-22 | project-summary.tex; workflow.tex; remaining-topics.tex | Definitions, proposed workflow and conclusion |
| 23 | closing.tex | Thanks / questions |
| 24-30 | backup.tex | Thresholds, conditioning, control requirements, bibliography, provenance, corner checks and planned comparison protocol |

## Presentation scope and retained implementation

- Slides describe what we **will** do: fit ordinary PCE and compare it with
  **Physics-Informed PCE (PI-PCE)** using monotonicity constraints.
- Both will use the same 19 measured targets, with the maximum of 18 CPU interval
  averages as the response. Data/preprocessing findings remain in the deck.
- No PCE prediction plots, model-error scores or selected-model results appear in
  the main or backup slides. The numerical conditional-moment example is explicitly
  illustrative, not a fitted result. The PDF no longer imports generated model metrics.
- The planned comparison keeps whole cases out and chooses degree inside the
  training cases only. PI-PCE adds assumed derivative signs without generating
  extra temperature labels. Better accuracy is a question to test, not a promise.
- The implementation, tests and saved experimental results in
  `results/monotonic_pce/` are preserved for later use. Their actual repository
  status is documented in the root README and results report; the slides do not
  present their results.
- Optimization and operational sensitivity remain proposed. Independent uniforms
  are a reference for the basis, not a measured operating distribution. No verified
  error bound or operating domain is established. DP remains omitted because of
  unresolved unit provenance.

Build the concept presentation directly; no model fitting is required:

```powershell
.\.venv\Scripts\python.exe presentation/heatwise-thermal-twin/build.py
```

To run the retained implementation later, use
`python scripts/fit_monotonic_pce.py` from the repository root. Historical reviews
and `../../monotonicity_changes.md` describe earlier presentation versions.

## Build from the command line

Prerequisites: Python 3.12+ (already required by the project) and a current
MiKTeX or TeX Live installation with LuaLaTeX. No Python packages, Perl, or
`latexmk` are needed. The build also detects the usual Windows MiKTeX installation
locations if LuaLaTeX is not on PATH.

From the repository root:

```powershell
python presentation/heatwise-thermal-twin/build.py
```

Or from this folder:

```powershell
python build.py
```

On Linux/macOS, use `python3` if `python` is unavailable. To select an executable:

```powershell
python build.py --engine "C:/path/to/lualatex.exe"
```

The PDF is always written to
`presentation/heatwise-thermal-twin/pdf/heatwise-thermal-twin.pdf`, regardless of
the folder from which the script is called. Intermediate files and compilation
logs stay in `build/`. A failed compilation exits with a nonzero status and prints
the LaTeX diagnostics; the last successfully built PDF is preserved.

The script generates the classes and packages from `../rwth-ci/source/` into
`build/rwth-ci/`, then compiles the presentation twice. It uses the supplied
template rather than an independently installed RWTH-CI version and leaves the
template files untouched.

## Edit and build in VS Code

Open the repository folder, edit `main.tex`, and use **Terminal > Run Task >
Build HEATWISE presentation** for this longer deck. **Ctrl+Shift+B** defaults to
the shortened presentation. The longer-deck task calls the same Python script
as the command above. Open the PDF from `pdf/` after building; a
PDF viewer extension is optional. If you open only this presentation folder in
VS Code, use `python build.py` in the integrated terminal.

## Image paths

All image paths are resolved relative to this presentation folder:

- Project figures stay at their existing locations. Use, for example,
  `\includegraphics[width=\linewidth]{../../results/audit/figures/inputs_and_max_temperature_timeseries.png}`.
- Put additional presentation-specific images in `images/` and reference them
  as `images/filename.png`.
- Reference template images directly as `../rwth-ci/<path-to-image>`.
  Do not copy template images into `images/`.

Project figures are referenced in place. The logo is
`../rwth-ci/tex/cf4dt-logo.png`, configured with the `logofile` class option in
`main.tex`. Separate class options with commas, including the option immediately
before `logofile`. To use a different logo, update that path.

## TeX dependencies and troubleshooting

The template requires LaTeX 2023-10-01 or newer and its normal dependencies,
including Beamer, PGF/TikZ, `fontspec`, `babel` (English), `anyfontsize`, and
`trimclip` (from `adjustbox`). Its font setup selects Arial when available and
otherwise uses Arimo. Install any missing packages using MiKTeX Console or the
TeX Live package manager; in MiKTeX, enabling automatic installation of missing
packages makes the first build easier. An up-to-date full TeX Live installation
also provides the dependencies.

For compilation errors, read the diagnostics printed by the build script or
`build/heatwise-thermal-twin.log`. If template generation fails, its log is saved
as `build/rwth-ci.log`. Close external PDF viewers that lock the output file
before rebuilding.

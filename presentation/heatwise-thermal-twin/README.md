# HEATWISE thermal twin presentation

A presentation using the supplied RWTH-CI Beamer template. Edit `main.tex` in
VS Code for the project title, contributor names, and shared formatting.
The PDF contains the template's blue title page followed by:

- **Introduction**, editable in `sections/introduction.tex` (five slides):
  motivation; a facility photo and dataset overview; the air-cooling subset and
  actuator optimization objective; the proposed digital twin;
  the rationale for experimental rather than purely synthetic training data.
- **Input Data**, editable in `sections/input-data.tex` (four slides): operating
  cases and model variables; two slides on dataset problems; preprocessing and
  steady-state selection. Problems are numbered **1. Sparsity**, **2. Unverified
  unit of fan signal**, and **3. Input Dependence**. The first two use the inlet/fan
  scatter plot; the third uses `input_correlation_matrix.pdf` from the audit.

The Introduction has the subsections **Motivation and Context** (three slides),
**Why a Digital Twin?** (one slide), and **Why not Synthetic Data?** (one slide).
No separate divider slides are generated. The dataset overview appears beside
`images/datacenter.jpeg`; the project-specific air-cooling subset and control
objective follow on the next slide. The overview is not repeated in Input Data. The image
credit uses the RWTH template's native `\footlinetext` command with a link to the
RISE source article. The proposed control and safety architecture is explicitly
conceptual; the project scope is offline development and evaluation.

Figures reference the existing vector PDFs in `../../results/audit/figures/`.
Selected panels are cropped using LaTeX `trim` and `clip`; the original figures
remain unchanged. Sources are linked or named at the bottom of each slide.
The institute and date fields remain blank and can be filled in in the preamble.

## Build from the command line

Prerequisites: Python 3.11+ (already required by the project) and a current
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

Open the repository folder, edit `main.tex`, and use **Terminal > Run Build Task**
(`Ctrl+Shift+B`) to run **Build HEATWISE presentation**. The task calls the same
Python script as the command above. Open the PDF from `pdf/` after building; a
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

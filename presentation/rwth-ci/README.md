# RWTH-CI – Corporate Design LaTeX-Templates for RWTH Aachen University

Copyright (C) 2025–2026 Marei Peischl <rwth-ci@peitex.de> and Lukas C. Bossert

RWTH-CI v1.2 (2026-04-03)

***************************************************************************

This material is subject to the LaTeX Project Public License version 1.3c
or later. See http://www.latex-project.org/lppl.txt for details.

***************************************************************************

[Link to the GitLab repository](https://gitlab.git.nrw/rwth-it-center/rwth-latex-templates/rwth-ci)

## Summary

The RWTH-CI-bundle provides a possibility to use the Corporate Design of RWTH Aachen University in LaTeX.
Therefore it contains documentclasses as well as some helper packages and config files together with some templates for user documentation.

## Getting started

### Installing on the local machine

RWTH-CI is part of TeX Live (and MikTeX). Please use these mechanism to install the bundle.

In case this is not an option or you want to contribute to the development setup (Thanks!) you find further instructions within `INSTALL.md`.

### ShareLaTeX/Overleaf

The templates are directly available on the [Overleaf instance used by RWTH Aachen University](https://sharelatex.tu-darmstadt.de/templates/rwth-templates).

And we also provide bundles to be uploaded as a starting point for projects in Overleaf using the  [Artifacts](https://gitlab.git.nrw/rwth-it-center/rwth-latex-templates/rwth-ci/-/jobs/artifacts/main/browse/sharelatex-bundles?job=build)

### Logos

The used Logos can not be published within this bundle. Members of RWTH Aachen University can request logo files from the Marketing team. The bundle is constructed to be fully functional without the logo files.

The GitLab Repository contains additional instructions which can be used for installation of intern logo files to extend the bundle.


## Demo output files and documentation artifacts

The latest build of the demo files can be found within the artifacts of this repository:

https://gitlab.git.nrw/rwth-it-center/rwth-latex-templates/rwth-ci/-/jobs/artifacts/main/browse?job=build




# Version History

- v1.0 (2025-12-18) First public version
- v1.0a (2025-12-27) Modify CTAN package to match TeX Live's defaults
- v1.0b (2026-01-23)
  * Fix pdflatex compatibility of RWTH-Beamer
  * Disable obsolete font warnings.
  * Add logos to the release process for CTAN PDFs
- v1.1 (2026-02-13)
  * Remove obsolete options from demo files
  * Bugfix in letter template
  * Drop Fax
- v1.2 (2026-04-03)
  * Fix department Config for letters
  * Add LICENCE.md
  * Add interface for landscape= #17
  * Fix freefonts=auto to match the documentation  

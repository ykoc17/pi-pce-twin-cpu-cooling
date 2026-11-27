"""Preserve selected source slides and make a categorized appendix index.

Only writes this shortened presentation. Introductory information is mapped to
the condensed main talk; source content is retained, with local B1 spacing.
"""

from pathlib import Path
import hashlib
import json
import re


HERE = Path(__file__).resolve().parents[1]
ORIGINAL = HERE.parent / "heatwise-thermal-twin"
OMITTED = {
    27: "Removed from the shortened deck by request (formerly F2: methods bibliography)",
    28: "Removed from the shortened deck by request (formerly F3: data provenance and units)",
}

# (category, section name, [(original PDF slide, short title), ...])
CATEGORIES = [
    ("A", "Data and preprocessing", [
        (8, "Operating cases and measured ranges"),
        (9, "Coverage, fan units and throttling"),
        (10, "Input dependence"),
        (11, "Why approximately steady targets?"),
        (12, "Full preprocessing checklist"),
        (13, "Selection results and the 19 observations"),
        (24, "Selection-threshold sensitivity"),
    ]),
    ("B", "PCE and input reference", [
        (6, "PCE definition and software"),
        (7, "PCE advantages and UQ / Sobol formulas"),
        (14, "Input bounds, uniforms and scaling"),
        (25, "Polynomial degree and conditioning"),
    ]),
    ("C", "PI-PCE and comparison", [
        (15, "Monotonicity constraints and fitting"),
        (16, "Planned PCE / PI-PCE comparison"),
        (29, "Why eight corners suffice"),
        (30, "Full comparison protocol"),
    ]),
    ("D", "UQ and sensitivity", [
        (17, "Conditional moments: worked example"),
        (18, "Conditional sensitivity coefficients"),
    ]),
    ("E", "Digital twin and operating choices", [
        (20, "Digital twin definition"),
        (21, "Control, learning and safety loops"),
        (19, "Full proposed robust optimization"),
        (26, "What a control error bound requires"),
    ]),
    ("F", "Outlook", [
        (22, "Complete conclusion and outlook"),
    ]),
]

# Authored additions are kept separately from the preserved longer-deck slides.
PRACTICAL_SOURCE = HERE / "sections/physics_in_practice.tex"


def practical_frames():
    source = PRACTICAL_SOURCE.read_text(encoding="utf-8")
    frames = re.findall(r"\\begin\{frame\}.*?\\end\{frame\}", source, re.S)
    result = []
    for frame in frames:
        match = re.match(
            r"\\begin\{frame\}\[.*?label=backup-(C[5-8])\]\{C[5-8]\\enspace\|\\enspace (.*)\}",
            frame.split("\n", 1)[0])
        if not match:
            raise ValueError("Review the authored practical-explanation slide map.")
        result.append((match[1], match[2], frame))
    if [code for code, _, _ in result] != ["C5", "C6", "C7", "C8"]:
        raise ValueError("Expected the four practical explanation slides C5-C8.")
    return result


def expanded_source(path):
    source = path.read_text(encoding="utf-8")
    def include(match):
        child = ORIGINAL / match.group(1)
        if not child.suffix:
            child = child.with_suffix(".tex")
        return expanded_source(child)
    return re.sub(r"\\input\{(sections/[^}]+)\}", include, source)


def body(frame):
    return frame.split("\n", 1)[1].rsplit(r"\end{frame}", 1)[0]


A2_REPLACEMENTS = [
    (r"""        Five trajectories; no full factorial design or LHS\\
        \textbf{Untested:} high fan signals between $25\,{}^\circ$C and $45\,{}^\circ$C""",
     r"""        \begin{itemize}
          \setlength{\itemsep}{1pt}
          \vspace{-1.5mm}
          \item Five trajectories; no full factorial design or LHS.
          \item \textbf{Untested:} high fan signals between $25\,{}^\circ$C and $45\,{}^\circ$C.
        \end{itemize}
        \vspace{-1.5mm}"""),
    (r"""        \textbf{Needed:} confirmation from data owners""",
     r"""        \begin{itemize}
          \vspace{-1.5mm}
          \item \textbf{Needed:} confirmation from data owners.
        \end{itemize}
        \vspace{-1.5mm}"""),
    (r"""        \textbf{6 targets $\geq93.5\,{}^\circ$C}; all are kept.\\
        A temperature flag, not confirmation from frequency data.\\
        Throttling can mask the power--temperature trend.""",
     r"""        \begin{itemize}
          \setlength{\itemsep}{1pt}
          \vspace{-1.5mm}
          \item \textbf{6 targets \boldmath$\geq$\,93.5\,\textdegree C}; all are kept.
          \item A temperature flag, not confirmation from frequency data.
          \item Throttling can mask the power--temperature trend.
        \end{itemize}
        \vspace{-1.5mm}"""),
]


B3_NOTE_OLD = r"""  {\footnotesize \textbf{Separate control assumption:} local inlet variation around its measured value.
  Its range must come from new disturbance measurements, not these global bounds.}"""
B3_NOTE_NEW = r"""  {\footnotesize
  \begin{itemize}
    \setlength{\itemsep}{1pt}
    \vspace{-1.5mm}
    \item \textbf{Separate control assumption:} local inlet variation around its measured value.
    \item Its range must come from new disturbance measurements, not these global bounds.
  \end{itemize}
  \vspace{-1.5mm}}
""".rstrip()


def backup_body(code, original_body):
    if code == "B3":
        if original_body.count(B3_NOTE_OLD) != 1:
            raise ValueError("B3 control-assumption note changed; review its formatting.")
        return original_body.replace(B3_NOTE_OLD, B3_NOTE_NEW)
    if code == "B4":
        return (HERE / "sections/conditioning_explained.tex").read_text(encoding="utf-8")
    if code == "A2":
        adjusted = original_body
        for old, new in A2_REPLACEMENTS:
            if adjusted.count(old) != 1:
                raise ValueError("A2 source changed; review its callout formatting.")
            adjusted = adjusted.replace(old, new)
        return adjusted
    if code == "A6":
        return original_body.replace("(backup).", "(appendix).")
    if code != "B1":
        return original_body
    adjusted, count = re.subn(r"(?m)^  \\smallskip$",
                              lambda _: r"  \par\vfill", original_body)
    if count != 2:
        raise ValueError("B1 layout changed; review its two inter-section gaps.")
    return adjusted


def main():
    additions = practical_frames()
    source = expanded_source(ORIGINAL / "main.tex")
    frames = re.findall(r"\\begin\{frame\}.*?\\end\{frame\}", source, re.S)
    if len(frames) != 29:
        raise ValueError("The source slide map changed; update coverage deliberately.")
    originals = dict(enumerate(frames, start=2))  # native cover is PDF page 1
    selected = [n for _, _, slides in CATEGORIES for n, _ in slides]
    if sorted(selected) != [n for n in range(6, 31) if n != 23 and n not in OMITTED]:
        raise ValueError("Every retained non-introduction source slide must appear exactly once.")

    output = ["% Generated from the longer deck; rebuild with scripts/build_backups.py.\n",
              r"\section{Appendix index}", r"\renewcommand{\backupcode}{Index}",
              r"\begin{frame}[more-space,label=backup-index]{Appendix\enspace|\enspace Topic index}",
              r"\par\medskip", r"{\renewcommand{\arraystretch}{1.8}",
              r"\begin{tabular}{@{}p{0.44\textwidth}p{0.52\textwidth}@{}}",
              r"\toprule\textbf{Topic} & \textbf{Appendix codes}\\\midrule"]
    for letter, name, slides in CATEGORIES:
        links = [rf"\hyperlink{{backup-{letter}{i}}}{{\color{{rwth-blue-100}}\textbf{{{letter}{i}}}}}"
                 for i in range(1, len(slides)+1)]
        if letter == "C":
            links += [rf"\hyperlink{{backup-{code}}}{{\color{{rwth-blue-100}}\textbf{{{code}}}}}"
                      for code, _, _ in additions]
        output.append(rf"\textbf{{{letter}. {name}}} & " + r"\quad ".join(links) + r"\\")
    output += [r"\bottomrule\end{tabular}}", r"\medskip", r"\end{frame}"]

    records = []
    index_page = 13
    navigation = HERE / "build/heatwise-thermal-twin-shortened.nav"
    if navigation.exists():
        ranges = re.findall(r"\\beamer@framepages\s*\{(\d+)\}\s*\{(\d+)\}",
                            navigation.read_text(encoding="utf-8"))
        if len(ranges) >= 13:
            index_page = int(ranges[12][0])  # account for main-slide overlays
    page = index_page + 1
    for letter, name, slides in CATEGORIES:
        output.append(rf"\section{{Appendix {letter}: {name}}}")
        for i, (number, title) in enumerate(slides, 1):
            code = f"{letter}{i}"
            frame = originals[number]
            first_line = frame.split("\n", 1)[0]
            options = re.match(r"\\begin\{frame\}(\[[^\]]*\])?", first_line).group(1)
            options = (options[1:-1]+"," if options else "") + f"label=backup-{code}"
            original_body = body(frame)
            new_frame = (rf"\begin{{frame}}[{options}]{{{code}\enspace|\enspace {title}}}"
                         + "\n" + backup_body(code, original_body) + r"\end{frame}")
            output += [rf"\renewcommand{{\backupcode}}{{{code}}}", new_frame]
            old_title = re.match(r"\\begin\{frame\}(?:\[[^\]]*\])?\{(.*)\}", first_line).group(1)
            records.append({"original_slide": number, "backup_code": code,
                            "pdf_page": page, "category": name, "title": title,
                            "original_title": old_title,
                            "layout_adjustment": ("two bulleted control-assumption sentences" if code == "B3"
                                                  else "condition-number explanation and numerical SVD ratios" if code == "B4"
                                                  else "bulleted callouts and bold threshold" if code == "A2"
                                                  else "even vertical spacing" if code == "B1" else None),
                            "body_sha256": hashlib.sha256(original_body.encode()).hexdigest()})
            page += 1
        if letter == "C":
            output.append(r"\input{sections/physics_in_practice}")
            for code, title, frame in additions:
                records.append({"original_slide": None, "backup_code": code,
                                "pdf_page": page, "category": name, "title": title,
                                "original_title": None, "layout_adjustment": None,
                                "source": "sections/physics_in_practice.tex",
                                "body_sha256": hashlib.sha256(body(frame).encode()).hexdigest()})
                page += 1

    tex = "\n\n".join(output)+"\n"
    generated = re.findall(r"\\begin\{frame\}.*?\\end\{frame\}", tex, re.S)[1:]
    retained = [record for record in records if record["original_slide"] is not None]
    for new, record in zip(generated, retained, strict=True):
        if record["backup_code"] == "B4":
            record["source"] = "sections/conditioning_explained.tex"
            if body(new) != backup_body("B4", ""):
                raise ValueError("B4 must match its authored explanatory source.")
            continue
        # Undo local formatting adjustments before checking source preservation.
        restored = body(new)
        if record["backup_code"] == "B3":
            restored = restored.replace(B3_NOTE_NEW, B3_NOTE_OLD)
        if record["backup_code"] == "A2":
            for old, adjusted in A2_REPLACEMENTS:
                restored = restored.replace(adjusted, old)
        if record["backup_code"] == "A6":
            restored = restored.replace("(appendix).", "(backup).")
        if record["backup_code"] == "B1":
            restored = re.sub(r"(?m)^  \\par\\vfill$",
                              lambda _: r"  \smallskip", restored)
        if restored != body(originals[record["original_slide"]]):
            raise ValueError(f"Lost source content for {record['backup_code']}")
    (HERE/"sections/backup.tex").write_text(tex, encoding="utf-8")
    main_map = {
        1: "Main 1: cover, authors/date, same credited photo",
        2: "Main 2: motivation/statistics/drivers; main 7/9/10: physics, uncertainty and project goals",
        3: "Main 3: RISE ICE photo, location, hardware and original study",
        4: "Main 10: twin concept and three loops; E1/E2: full definition/workflow",
        5: "Main 4: experimental vs simulated targets, CAD/CFD and future data",
        23: "Main 12: thanks and discussion",
    }
    mapping = {str(n): main_map[n] if n in main_map else OMITTED[n] if n in OMITTED else next(
        f"{r['backup_code']} (PDF page {r['pdf_page']}): {r['title']}" for r in records if r['original_slide']==n)
        for n in range(1, 31)}
    evidence = {"main_slides": 12, "main_pdf_pages": index_page-1,
                "backup_index_page": index_page, "backup_slides": len(records),
                "total_pages": page-1, "original_slide_map": mapping, "backups": records,
                "omitted_original_slides": OMITTED,
                "intro_policy": "Introductory content is condensed into the main talk, not duplicated in the appendix",
                "original_pdf_sha256": hashlib.sha256((ORIGINAL/"pdf/heatwise-thermal-twin.pdf").read_bytes()).hexdigest()}
    (HERE/"coverage.json").write_text(json.dumps(evidence, indent=2)+"\n", encoding="utf-8")
    lines = ["# Coverage and appendix reference", "", f"Main talk: slides 1-12. Index: PDF page {index_page}. "
             "Technical appendix: A1-F1. No introduction slides are duplicated in the appendix.", "",
             "Retained source slides keep their complete content; titles, codes and navigation are added. "
             "A2 has bulleted callouts and a bold threshold; B1 has local vertical-spacing adjustments. "
             "B4 is rewritten to explain the design matrix, singular-value ratios and their interpretation. F2 and F3 were removed by request; "
             "their source slides remain in the longer deck. C5-C8 add a practical mathematical explanation of PI-PCE.", "",
             "## Appendix topics", "", "| Code | PDF page | Topic | Longer-deck slide |",
             "| --- | --- | --- | --- |"]
    lines += [f"| {r['backup_code']} | {r['pdf_page']} | {r['title']} | {r['original_slide'] if r['original_slide'] is not None else 'New explanation'} |" for r in records]
    lines += ["", "## Coverage of every original slide", "", "| Longer-deck slide | Where to find the information |",
              "| --- | --- |"]
    lines += [f"| {n} | {mapping[str(n)]} |" for n in range(1,31)]
    lines += ["", "Except for the authored B4 explanation, regenerated appendix bodies are checked against the original source after undoing local formatting and terminology adjustments. "
              "The new main slides retain the introductory facts in a leaner form; their "
              "coverage is reviewed separately rather than claiming identical wording.", ""]
    (HERE/"coverage_map.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"Preserved {len(retained)} original content slides plus {len(additions)} new explanation slides; "
          f"{page-1} PDF pages including the 12-slide main route.")


if __name__ == "__main__":
    main()

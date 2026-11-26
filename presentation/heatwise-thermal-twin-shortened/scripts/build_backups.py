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


def backup_body(code, original_body):
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
              r"\small Click a code to open a slide. Every appendix slide has an Index return link.",
              r"\par\medskip", r"{\renewcommand{\arraystretch}{1.8}",
              r"\begin{tabular}{@{}p{0.44\textwidth}p{0.52\textwidth}@{}}",
              r"\toprule\textbf{Topic} & \textbf{Appendix codes}\\\midrule"]
    for letter, name, slides in CATEGORIES:
        links = [rf"\hyperlink{{backup-{letter}{i}}}{{\color{{rwth-blue-100}}\textbf{{{letter}{i}}}}}"
                 for i in range(1, len(slides)+1)]
        output.append(rf"\textbf{{{letter}. {name}}} & " + r"\quad ".join(links) + r"\\")
    output += [r"\bottomrule\end{tabular}}", r"\medskip",
               r"\begin{beamercolorbox}[sep=2mm,wd=\textwidth]{data panel}",
               r"\small Selection rules: \hyperlink{backup-A5}{\textbf{A5}}. "
               r"Software: \hyperlink{backup-B1}{\textbf{B1}}. "
               r"Full learning loop: \hyperlink{backup-E2}{\textbf{E2}}.",
               r"\end{beamercolorbox}", r"\end{frame}"]

    records = []
    page = 14  # 12 main slides + one backup index
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
                            "layout_adjustment": "even vertical spacing" if code == "B1" else None,
                            "body_sha256": hashlib.sha256(original_body.encode()).hexdigest()})
            page += 1

    tex = "\n\n".join(output)+"\n"
    generated = re.findall(r"\\begin\{frame\}.*?\\end\{frame\}", tex, re.S)[1:]
    for new, record in zip(generated, records, strict=True):
        # Undo the sole local spacing adjustment before checking source preservation.
        restored = body(new)
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
    evidence = {"main_slides": 12, "backup_index_page": 13, "backup_slides": len(records),
                "total_pages": page-1, "original_slide_map": mapping, "backups": records,
                "omitted_original_slides": OMITTED,
                "intro_policy": "Introductory content is condensed into the main talk, not duplicated in the appendix",
                "original_pdf_sha256": hashlib.sha256((ORIGINAL/"pdf/heatwise-thermal-twin.pdf").read_bytes()).hexdigest()}
    (HERE/"coverage.json").write_text(json.dumps(evidence, indent=2)+"\n", encoding="utf-8")
    lines = ["# Coverage and appendix reference", "", "Main talk: slides 1-12. Index: PDF page 13. "
             "Technical appendix: A1-F1. No introduction slides are duplicated in the appendix.", "",
             "Retained source slides keep their complete content; titles, codes and navigation are added. "
             "B1 has local vertical-spacing adjustments. F2 and F3 were removed by request; "
             "their source slides remain in the longer deck.", "",
             "## Appendix topics", "", "| Code | PDF page | Topic | Longer-deck slide |",
             "| --- | --- | --- | --- |"]
    lines += [f"| {r['backup_code']} | {r['pdf_page']} | {r['title']} | {r['original_slide']} |" for r in records]
    lines += ["", "## Coverage of every original slide", "", "| Longer-deck slide | Where to find the information |",
              "| --- | --- |"]
    lines += [f"| {n} | {mapping[str(n)]} |" for n in range(1,31)]
    lines += ["", "The regenerated appendix bodies are checked against the original source after undoing local spacing and terminology adjustments. "
              "The new main slides retain the introductory facts in a leaner form; their "
              "coverage is reviewed separately rather than claiming identical wording.", ""]
    (HERE/"coverage_map.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"Preserved {len(records)} original content slides in A-F; {page-1} PDF pages including the 12-slide main route.")


if __name__ == "__main__":
    main()

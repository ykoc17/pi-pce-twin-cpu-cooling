"""Build the RWTH presentation using only Python and LuaLaTeX."""

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import tempfile


HERE = Path(__file__).resolve().parent
TEMPLATE = HERE.parent / "rwth-ci"
BUILD = HERE / "build"
PDF = HERE / "pdf"
JOB = "heatwise-thermal-twin"


def find_engine(command: str) -> str:
    executable = shutil.which(command)
    if executable:
        return executable
    # A per-user MiKTeX installation may not yet be on Windows' PATH.
    if os.name == "nt" and command == "lualatex":
        for variable, suffix in (
            ("LOCALAPPDATA", "Programs/MiKTeX/miktex/bin/x64/lualatex.exe"),
            ("ProgramFiles", "MiKTeX/miktex/bin/x64/lualatex.exe"),
        ):
            base = os.environ.get(variable)
            if base:
                candidate = Path(base) / suffix
                if candidate.is_file():
                    return str(candidate)
    raise SystemExit(
        f"Cannot find {command!r}. Install MiKTeX or TeX Live with LuaLaTeX, "
        "restart your terminal, or pass --engine with the full executable path."
    )


def run_tex(engine: str, arguments: list[str], cwd: Path, env: dict[str, str]) -> None:
    result = subprocess.run(
        [engine, "-interaction=nonstopmode", "-halt-on-error", "-file-line-error", *arguments],
        cwd=cwd,
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        errors="replace",
    )
    if result.returncode:
        print(result.stdout)
        raise SystemExit(result.returncode)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine", default="lualatex", help="LuaLaTeX executable name or path")
    args = parser.parse_args()
    engine = find_engine(args.engine)
    source = TEMPLATE / "source"
    if not (source / "rwth-ci.ins").is_file():
        raise SystemExit(f"Missing template installer: {source / 'rwth-ci.ins'}")

    BUILD.mkdir(exist_ok=True)
    PDF.mkdir(exist_ok=True)
    generated = BUILD / "rwth-ci"
    generated.mkdir(exist_ok=True)
    env = os.environ.copy()
    # The trailing separator preserves the TeX distribution's normal search paths.
    paths = [generated, TEMPLATE / "tex", source]
    env["TEXINPUTS"] = os.pathsep.join(
        [*(path.as_posix() for path in paths), env.get("TEXINPUTS", ""), ""]
    )

    print("Generating RWTH classes from ../rwth-ci/source/ ...", flush=True)
    # A fresh temporary directory avoids docstrip overwrite prompts on rebuilds.
    # The template directory itself is never modified.
    with tempfile.TemporaryDirectory(prefix="rwth-", dir=BUILD) as temporary:
        staging = Path(temporary)
        try:
            run_tex(engine, ["rwth-ci.ins"], staging, env)
        except SystemExit:
            if (staging / "rwth-ci.log").exists():
                shutil.copy2(staging / "rwth-ci.log", BUILD / "rwth-ci.log")
            raise
        for path in staging.iterdir():
            if path.suffix in {".cls", ".sty", ".clo"}:
                shutil.copy2(path, generated / path.name)

    # Two passes resolve Beamer navigation, slide counts, and cross-references.
    for number in (1, 2):
        print(f"Compiling main.tex (pass {number}/2) ...", flush=True)
        run_tex(
            engine,
            [f"-output-directory={BUILD.as_posix()}", f"-jobname={JOB}", "main.tex"],
            HERE,
            env,
        )
    destination = PDF / f"{JOB}.pdf"
    shutil.copy2(BUILD / f"{JOB}.pdf", destination)
    print(f"PDF: {destination}")


if __name__ == "__main__":
    main()

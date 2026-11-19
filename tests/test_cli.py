"""Exercise command-line success, error reporting, and argument handling."""

import pytest

from thermal_twin.cli import main


def test_inspect_cli(valid_frame, tmp_path, capsys):
    path = tmp_path / "air.csv"
    valid_frame.to_csv(path, index=False)
    assert main(["inspect", "--data", str(path)]) == 0
    captured = capsys.readouterr()
    assert "1333 rows x 219 columns" in captured.out
    assert "Unlabeled transition rows:" in captured.out
    assert "Individual CPU temperature columns: 18" in captured.out
    assert "timestamp spacing: 5 minutes" in captured.out
    assert not captured.err


def test_inspect_missing_file(tmp_path, capsys):
    assert main(["inspect", "--data", str(tmp_path / "missing.csv")]) == 1
    captured = capsys.readouterr()
    assert "error: Dataset file not found" in captured.err
    assert "Traceback" not in captured.err


def test_inspect_invalid_csv(valid_frame, tmp_path, capsys):
    path = tmp_path / "invalid.csv"
    valid_frame.drop(columns="total_cpu_power_W").to_csv(path, index=False)
    assert main(["inspect", "--data", str(path)]) == 1
    assert "Missing required columns: total_cpu_power_W" in capsys.readouterr().err


def test_default_path(valid_frame, tmp_path, monkeypatch, capsys):
    raw = tmp_path / "data/raw"
    raw.mkdir(parents=True)
    valid_frame.to_csv(raw / "ocp_air_cooling_5min.csv", index=False)
    monkeypatch.chdir(tmp_path)
    assert main(["inspect"]) == 0
    assert "Validated HEATWISE" in capsys.readouterr().out


def test_subcommand_is_required():
    with pytest.raises(SystemExit) as exc:
        main([])
    assert exc.value.code == 2

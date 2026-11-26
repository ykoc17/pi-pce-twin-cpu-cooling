"""Monotonicity constraints, derivatives, validation separation and source preservation."""

from dataclasses import replace
from itertools import product
import hashlib
import json

import numpy as np
import pandas as pd
import pytest

from configs.data_config import INPUT_COLUMNS
from configs.pce_config import DEFAULT_PCE_CONFIG, PCEConfig
from thermal_twin.cli import main
from thermal_twin.data import DatasetValidationError
from thermal_twin.monotonic_pce import (
    SIGNS, VERTICES, PCEModel, basis, compare_pce, derivative_constraints,
    fit_pce, indices, run_pce,
)
from thermal_twin.preprocessing import TARGET_COLUMN


@pytest.fixture
def observations():
    records = []
    regimes = [(25., .13, 4), (35., .24, 4), (45., .36, 5), (45., .53, 4), (45., .72, 2)]
    for case, (inlet, fan, count) in enumerate(regimes, 1):
        for i, power in enumerate(np.linspace(400, 1600, count)):
            records.append({"case_id": case, "operating_period_id": len(records)+1,
                            INPUT_COLUMNS[0]: power+case, INPUT_COLUMNS[1]: inlet+.02*i,
                            INPUT_COLUMNS[2]: fan+.002*i})
    frame = pd.DataFrame(records)
    frame[TARGET_COLUMN] = (30+.025*frame[INPUT_COLUMNS[0]]+.9*frame[INPUT_COLUMNS[1]]
                           -10*frame[INPUT_COLUMNS[2]]+np.sin(np.arange(len(frame))))
    frame["start_time"] = pd.date_range("2024-01-01", periods=len(frame), freq="2h")
    frame["end_time"] = frame.start_time+pd.Timedelta(minutes=30)
    return frame


def test_known_monotone_quadratic_and_analytic_derivatives():
    rng = np.random.default_rng(42)
    x = rng.uniform([-1,-1,-1], [1,1,1], size=(30,3))
    y = 80+8*x[:,0]+2*x[:,1]-3*x[:,2]+.5*x[:,0]**2-.2*x[:,2]**2+.2*x[:,0]*x[:,1]
    model = fit_pce(x,y,2,monotonic=True)
    np.testing.assert_allclose(model.predict(x),y,atol=1e-9)
    expected = np.column_stack([8+x[:,0]+.2*x[:,1], 2+.2*x[:,0], -3-.4*x[:,2]])
    np.testing.assert_allclose(model.gradient(x),expected,atol=1e-9)
    for axis in range(3):
        shift = np.zeros(3); shift[axis]=1e-5
        numeric=(model.predict(x+shift)-model.predict(x-shift))/2e-5
        np.testing.assert_allclose(model.gradient(x)[:,axis],numeric,atol=1e-8)


def test_constraints_reject_reverse_trends_and_hold_between_vertices():
    x = np.array(list(product((-1.,0.,1.),repeat=3)))
    y = 80-8*x[:,0]-2*x[:,1]+3*x[:,2]
    ordinary=fit_pce(x,y,2)
    monotonic=fit_pce(x,y,2,monotonic=True)
    assert (ordinary.gradient(x)*SIGNS).min() < -1
    assert np.mean((monotonic.predict(x)-y)**2) >= np.mean((ordinary.predict(x)-y)**2)
    interior=np.random.default_rng(7).uniform(-1,1,size=(500,3))
    assert (monotonic.gradient(interior)*SIGNS).min() >= -1e-7
    # Affine derivatives inside the box equal convex combinations of vertex derivatives.
    vertex_grad=monotonic.gradient(VERTICES)
    weights=np.prod((1+interior[:,None,:]*VERTICES[None,:,:])/2,axis=2)
    np.testing.assert_allclose(monotonic.gradient(interior),weights@vertex_grad,atol=1e-10)
    assert monotonic.diagnostics["rows"]==27
    assert monotonic.diagnostics["synthetic_temperature_targets"]==0


def test_reference_moments_and_json_round_trip():
    powers=indices(2)
    c=np.arange(len(powers),dtype=float)/10; c[0]=80
    model=PCEModel(2,"monotonicity",np.zeros(3),np.ones(3),powers,c,{})
    saved=json.loads(json.dumps(model.to_dict()))
    reconstructed=PCEModel(saved["degree"],saved["method"],np.array(saved["lower"]),
                           np.array(saved["upper"]),np.array(saved["powers"]),
                           np.array(saved["coefficients"]),saved["diagnostics"])
    x=np.random.default_rng(2).uniform(0,1,size=(10,3))
    np.testing.assert_allclose(model.predict(x),reconstructed.predict(x))
    assert model.reference_moments()=={"mean_C":80.,"variance_C2":float(c[1:]@c[1:])}
    assert basis(np.zeros((1,3)),powers).shape==(1,10)
    assert derivative_constraints(powers).shape==(24,10)


@pytest.mark.parametrize("degree",[0,3,4])
def test_unsupported_degrees_cannot_claim_vertex_certificate(degree):
    with pytest.raises(ValueError,match="degree 1 or 2"):
        indices(degree)


def test_invalid_training_inputs_are_rejected():
    with pytest.raises(ValueError,match="nonzero range"):
        fit_pce(np.ones((10,3)),np.ones(10))
    with pytest.raises(ValueError,match="finite"):
        fit_pce(np.full((10,3),np.nan),np.ones(10))
    with pytest.raises(ValueError,match="at least"):
        fit_pce(np.ones((5,3)),np.ones(5),2)
    with pytest.raises(ValueError):
        PCEConfig(degrees=(3,))


def test_failed_solver_is_not_silently_accepted(monkeypatch):
    from types import SimpleNamespace
    monkeypatch.setattr("thermal_twin.monotonic_pce.minimize",
                        lambda *args,**kwargs:SimpleNamespace(success=False,message="test failure"))
    x=np.array(list(product((-1.,0.,1.),repeat=3)))
    with pytest.raises(ValueError,match="did not converge"):
        fit_pce(x,80-8*x[:,0],2,monotonic=True)


def test_test_case_cannot_influence_model_choice_scaling_or_constraints(observations):
    original=compare_pce(observations)
    changed=observations.copy()
    held=changed.case_id.eq(3)
    changed.loc[held,TARGET_COLUMN]+=100
    changed.loc[held,list(INPUT_COLUMNS)]*=2
    modified=compare_pce(changed)
    for name in ["selection","corner_checks"]:
        pd.testing.assert_frame_equal(
            original[name].loc[original[name].held_out_case.eq(3)].reset_index(drop=True),
            modified[name].loc[modified[name].held_out_case.eq(3)].reset_index(drop=True))
    columns=["degree","training_bounds","coefficients","training_period_ids"]
    assert original["folds"].loc[original["folds"].held_out_case.eq(3),columns].to_dict("records")==(
        modified["folds"].loc[modified["folds"].held_out_case.eq(3),columns].to_dict("records"))
    for method,group in original["predictions"].groupby("method"):
        assert sorted(group.operating_period_id)==sorted(observations.operating_period_id)


def test_cli_artifacts_use_only_measured_targets_and_preserve_source(observations,tmp_path,capsys):
    source=tmp_path/"steady.csv"; observations.to_csv(source,index=False)
    digest=hashlib.sha256(source.read_bytes()).hexdigest()
    output=tmp_path/"pce"
    assert main(["fit-pce","--data",str(source),"--output",str(output)])==0
    assert "no synthetic temperature targets" in capsys.readouterr().out
    assert hashlib.sha256(source.read_bytes()).hexdigest()==digest
    manifest=json.loads((output/"manifest.json").read_text())
    assert manifest["synthetic_temperature_targets"]==0
    assert manifest["legacy_thermal_rule_used"] is False
    assert len(pd.read_csv(output/"predictions.csv"))==38
    assert (output/"held_out_comparison.pdf").stat().st_size>0
    assert not any("check_points" in path.name for path in output.iterdir())
    with pytest.raises(DatasetValidationError,match="must not contain"):
        run_pce(source,tmp_path)
    with pytest.raises(DatasetValidationError,match="outside raw"):
        run_pce(source,"data/raw/pce")

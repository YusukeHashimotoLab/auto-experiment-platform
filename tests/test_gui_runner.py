"""src/gui/runner.py: validation, mock run, progress events, stop path.

These tests never import Streamlit: the GUI's execution logic lives in
``src.gui.runner`` precisely so it can be exercised headlessly.
"""
import json
import os
import time

import pytest
from pydantic import ValidationError

from src.devices.safety.mock_robot import MockLabRobot
from src.gui import runner as gui_runner

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ZIF8_FLOW = os.path.join(
    REPO_ROOT, "examples", "zif8", "zif8_two_solution_mixing_speed5.json"
)


def load_zif8():
    with open(ZIF8_FLOW, encoding="utf-8") as f:
        return json.load(f)


# ----------------------------------------------------------------------
# 1. Validation happens before anything is built
# ----------------------------------------------------------------------
def test_invalid_flow_is_rejected_before_a_session_is_created(tmp_path, monkeypatch):
    """A flow that fails the Pydantic schema must not reach the hardware layer."""
    created = []
    monkeypatch.setattr(
        gui_runner, "ExperimentSession",
        lambda **kwargs: created.append(kwargs),
    )
    bad = {
        "name": "missing required parameter",
        "description": "move_z without distance",
        "steps": [{"action": "move_z", "robot_id": 1}],
    }
    with pytest.raises(ValidationError):
        gui_runner.FlowRunner(bad, mock=True, logs_dir=str(tmp_path))

    assert created == [], "no ExperimentSession may be built for an invalid flow"
    assert list(tmp_path.iterdir()) == [], "no run folder may be created either"


def test_unknown_action_is_rejected():
    with pytest.raises(ValidationError):
        gui_runner.validate_workflow(
            {"name": "x", "steps": [{"action": "self_destruct"}]}
        )


def test_broken_loop_structure_is_rejected():
    with pytest.raises(ValueError):
        gui_runner.validate_workflow({
            "name": "x",
            "steps": [{"action": "loop_start", "loop_id": "a", "count": 2},
                      {"action": "go_home", "robot_id": 1}],
        })


@pytest.mark.parametrize("flow, expected", [
    ({"name": "x", "steps": [{"action": "move_z", "robot_id": 1}]},
     "step 1 (move_z): distance"),
    ({"name": "x", "steps": [{"action": "self_destruct"}]},
     "unknown or mistyped action 'self_destruct'"),
    ({"steps": [{"action": "go_home", "robot_id": 1}]}, "name"),
])
def test_validation_errors_are_formatted_for_the_ui(flow, expected):
    """The union schema reports every action type; the UI must show only
    the errors of the action the step actually declares."""
    with pytest.raises(ValidationError) as excinfo:
        gui_runner.validate_workflow(flow)
    text = gui_runner.format_validation_error(excinfo.value, flow)
    assert expected in text
    assert len(text.splitlines()) <= 3, text


def test_loops_are_expanded():
    _, steps = gui_runner.validate_workflow({
        "name": "x",
        "steps": [
            {"action": "loop_start", "loop_id": "a", "count": 3},
            {"action": "go_home", "robot_id": 1},
            {"action": "loop_end", "loop_id": "a"},
        ],
    })
    assert [s["action"] for s in steps] == ["go_home"] * 3
    assert [s["_iteration"] for s in steps] == [1, 2, 3]


# ----------------------------------------------------------------------
# 2. Port defaults come from src.config, not from hard-coded COM numbers
# ----------------------------------------------------------------------
def test_device_defaults_come_from_config():
    from src import config as lab_config

    settings = gui_runner.default_device_settings()
    ports = lab_config.get_robot_ports()
    shared = lab_config.get_shared_devices()
    assert settings["robots"][1]["dobot_port"] == ports[1]["dobot_port"]
    assert settings["robots"][1]["picus2_port"] == ports[1].get("picus2_address", "")
    assert settings["shared"]["scale_port"] == shared["scale_port"]


def test_sidebar_settings_are_translated_for_the_session():
    settings = gui_runner.default_device_settings()
    settings["robots"][1]["dobot_port"] = "COM_EDITED"
    settings["robots"][3]["use_picus2"] = False
    settings["shared"]["scale_port"] = "COM_SCALE"
    robot_ports, shared_config = gui_runner.settings_to_session_args(settings)
    assert robot_ports[1]["dobot_port"] == "COM_EDITED"
    assert robot_ports[3]["picus2_address"] == ""
    assert shared_config["scale_port"] == "COM_SCALE"


# ----------------------------------------------------------------------
# 3. The ZIF-8 flow runs to completion in mock mode
# ----------------------------------------------------------------------
@pytest.fixture(scope="module")
def zif8_mock_run(tmp_path_factory):
    """Run the paper's ZIF-8 flow once in mock mode and keep the artefacts."""
    logs_dir = tmp_path_factory.mktemp("logs")
    events = []
    runner = gui_runner.FlowRunner(
        load_zif8(), mock=True, logs_dir=str(logs_dir),
        source_path=ZIF8_FLOW, on_event=events.append,
    )
    runner.start()
    assert runner.join(300), "the mock run did not finish in time"
    return runner, events


def test_zif8_flow_completes_in_mock_mode(zif8_mock_run):
    runner, _ = zif8_mock_run
    assert runner.status == "completed", runner.error
    assert runner.error is None


def test_zif8_mock_run_writes_the_same_artefacts_as_the_cli(zif8_mock_run):
    runner, _ = zif8_mock_run
    run_dir = runner.log_dir
    for name in ("run.log", "measurements.csv", "metadata.json", "summary.md",
                 "dispense_accuracy.csv",
                 os.path.basename(ZIF8_FLOW)):
        assert os.path.exists(os.path.join(run_dir, name)), f"missing {name}"

    # logs/<date>/<name>_<timestamp>/
    date_dir = os.path.basename(os.path.dirname(run_dir))
    assert len(date_dir) == 10 and date_dir.count("-") == 2

    import csv
    with open(os.path.join(run_dir, "measurements.csv"), encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == len(runner.steps)
    assert all(r["status"] == "ok" for r in rows)
    weights = [r["weight_g"] for r in rows if r["weight_g"]]
    assert weights, "measure_weight results must land in measurements.csv"
    assert all(r["image_path"] for r in rows if r["action"] == "capture_and_save")


def test_progress_callback_gets_one_event_per_step(zif8_mock_run):
    runner, events = zif8_mock_run
    step_events = [e for e in events if e.kind == "step"]
    assert len(step_events) == len(runner.steps)
    assert [e.index for e in step_events] == list(range(1, len(runner.steps) + 1))
    assert all(e.status == "ok" for e in step_events)
    assert all(e.total == len(runner.steps) for e in step_events)

    kinds = [e.kind for e in events]
    assert kinds[0] == "start" and kinds[-1] == "finish"
    assert events[-1].status == "completed"
    assert events[0].log_dir == runner.log_dir
    assert any(e.kind == "log" for e in events), "device logs must reach the UI"


def test_events_can_be_drained_for_streamlit(zif8_mock_run):
    runner, events = zif8_mock_run
    drained = runner.drain_events()
    assert len(drained) == len(events)
    assert runner.drain_events() == []


# ----------------------------------------------------------------------
# 4. Stop cancels the run and triggers the emergency stop
# ----------------------------------------------------------------------
class _RecordingRobot(MockLabRobot):
    """MockLabRobot that remembers whether it was emergency-stopped."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.emergency_stops = 0

    def emergency_stop(self):
        self.emergency_stops += 1
        super().emergency_stop()


def test_stop_button_emergency_stops_and_cleans_up(tmp_path):
    built = []

    def robot_factory(robot_id, *, use_picus2, ports, workspace_validator):
        robot = _RecordingRobot(
            use_dobot=True, use_picus2=use_picus2,
            workspace_validator=workspace_validator,
        )
        built.append(robot)
        return robot

    flow = {
        "name": "stop test",
        "description": "a long wait that gets interrupted",
        "steps": [{"action": "wait", "robot_id": 1, "seconds": 60.0}],
    }
    events = []
    runner = gui_runner.FlowRunner(
        flow, mock=True, logs_dir=str(tmp_path), on_event=events.append,
        robot_factory=robot_factory,
    )
    runner.start()

    # Wait until the step is actually running, then press Stop.
    deadline = time.time() + 30
    while time.time() < deadline:
        if any(e.kind == "log" and "待機中" in e.message for e in list(events)):
            break
        time.sleep(0.05)
    else:
        runner.request_stop()
        pytest.fail("the wait step never started")

    runner.request_stop()
    assert runner.join(30), "the run did not stop"

    assert built and built[0].emergency_stops == 1
    assert runner.status == "aborted"
    assert events[-1].kind == "finish" and events[-1].status == "aborted"
    # The run folder is still finalised, so an aborted GUI run is traceable.
    assert os.path.exists(os.path.join(runner.log_dir, "metadata.json"))
    with open(os.path.join(runner.log_dir, "metadata.json"), encoding="utf-8") as f:
        assert json.load(f)["status"] == "aborted"


def test_stop_before_the_first_step_still_aborts(tmp_path):
    flow = {"name": "stop early", "steps": [{"action": "go_home", "robot_id": 1}]}
    runner = gui_runner.FlowRunner(flow, mock=True, logs_dir=str(tmp_path))
    runner.request_stop()          # pressed before start(): must not run anything
    runner.start()
    assert runner.join(30)
    assert runner.status == "aborted"

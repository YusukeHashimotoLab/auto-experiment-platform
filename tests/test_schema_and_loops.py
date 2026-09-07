"""L2: JSONスキーマ検証とループ展開"""
import pytest
from pydantic import ValidationError

from src.flow.executor import expand_loops
from src.flow.schema import ExperimentWorkflow


def make_workflow(steps):
    return {"name": "テスト", "description": "テスト用", "steps": steps}


def test_valid_workflow_parses():
    wf = ExperimentWorkflow(**make_workflow([
        {"action": "move_z", "robot_id": 1, "distance": -50.0},
        {"action": "aspirate", "robot_id": 1, "volume": 5.0, "speed": 5},
        {"action": "go_home", "robot_id": 1},
    ]))
    assert len(wf.steps) == 3


def test_unknown_action_rejected():
    with pytest.raises(ValidationError):
        ExperimentWorkflow(**make_workflow([
            {"action": "self_destruct", "robot_id": 1},
        ]))


def test_missing_required_param_rejected():
    with pytest.raises(ValidationError):
        ExperimentWorkflow(**make_workflow([
            {"action": "move_xyz", "robot_id": 1, "x": 200.0, "y": 0.0},  # z欠落
        ]))


def test_expand_loops_repeats_body_with_iteration():
    steps = [
        {"action": "loop_start", "loop_id": "L1", "count": 3},
        {"action": "move_z", "robot_id": 1, "distance": -10.0},
        {"action": "go_home", "robot_id": 1},
        {"action": "loop_end", "loop_id": "L1"},
        {"action": "go_home", "robot_id": 1},
    ]
    expanded = expand_loops(steps)
    # 2ステップ×3回 + 末尾の go_home
    assert len(expanded) == 7
    iterations = [s.get("_iteration") for s in expanded[:6]]
    assert iterations == [1, 1, 2, 2, 3, 3]
    assert expanded[6].get("_iteration") is None


def test_expand_loops_nested_raises():
    steps = [
        {"action": "loop_start", "loop_id": "A", "count": 2},
        {"action": "loop_start", "loop_id": "B", "count": 2},
        {"action": "go_home", "robot_id": 1},
        {"action": "loop_end", "loop_id": "B"},
        {"action": "loop_end", "loop_id": "A"},
    ]
    with pytest.raises(ValueError):
        expand_loops(steps)


def test_expand_loops_unclosed_raises():
    steps = [
        {"action": "loop_start", "loop_id": "A", "count": 2},
        {"action": "go_home", "robot_id": 1},
    ]
    with pytest.raises(ValueError):
        expand_loops(steps)

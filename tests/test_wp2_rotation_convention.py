"""WP-2 item 4: 回転角の符号規約がコード・スキーマ・プリセットで一致していること。

真値: LabRobot.rotate_relative は target = 現在のJ1 + delta を PyDobotController.move_angle に渡し、
move_angle は MOVJ_ANGLE で J1 を絶対指定する。Dobot Magician の J1 は正方向が上から見て反時計回り
（+Y 方向）なので、angle が正 = 上から見て反時計回り。
"""
import json
import pathlib

REPO = pathlib.Path(__file__).resolve().parents[1]

# 全ソースで共通に使う表記
CONVENTION = "正=反時計回り（上から見て、+Y方向）、負=時計回り"


def test_schema_states_counter_clockwise():
    from src.flow.schema import ActionRotateRelative

    desc = ActionRotateRelative.model_fields["angle"].description
    assert "反時計回り" in desc, desc
    assert "右回転" not in desc, desc
    assert CONVENTION in desc, desc


def test_lab_robot_docstring_matches_schema():
    from src.devices.safety.lab_robot import LabRobot

    doc = LabRobot.rotate_relative.__doc__
    assert "反時計回り" in doc
    assert "右回転" not in doc


def test_llm_service_prompt_states_same_convention():
    text = (REPO / "src/agent/llm_service.py").read_text(encoding="utf-8")
    assert CONVENTION in text, "llm_service のプロンプトに回転規約が無い"
    assert "右回転" not in text


def test_presets_do_not_use_the_old_wording():
    for path in sorted((REPO / "src/agent/presets").glob("*.json")):
        text = path.read_text(encoding="utf-8")
        assert "右回転" not in text, f"{path.name} に古い表記 '右回転' が残っている"
        json.loads(text)  # JSON として壊れていないこと

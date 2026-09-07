"""ExperimentSession: 正常終了・中断・エラー時の安全枠"""
import asyncio

import pytest

from src.flow.experiment_session import ExperimentSession


class FakeRobot:
    """emergency_stop / go_home / cleanup の呼び出しを記録するダミー"""

    def __init__(self, calls, name):
        self.calls = calls
        self.name = name

    def emergency_stop(self):
        self.calls.append(f"{self.name}:emergency_stop")

    async def go_home(self):
        self.calls.append(f"{self.name}:go_home")

    async def cleanup(self):
        self.calls.append(f"{self.name}:cleanup")


class FakeShared:
    def __init__(self, calls):
        self.calls = calls

    async def cleanup(self):
        self.calls.append("shared:cleanup")


def make_session(calls):
    session = ExperimentSession()
    session.robots[1] = FakeRobot(calls, "r1")
    session.robots[2] = FakeRobot(calls, "r2")
    session.shared = FakeShared(calls)
    return session


def test_completed_flow():
    calls = []
    session = make_session(calls)

    async def body():
        calls.append("body")
        return 42

    result = asyncio.run(session.run(body))
    assert result == 42
    assert session.status == "completed"
    assert session.error is None
    # 緊急停止・ホーム復帰は呼ばれず、クリーンアップのみ
    assert calls == ["body", "r1:cleanup", "r2:cleanup", "shared:cleanup"]


def test_cancelled_triggers_emergency_stop_not_go_home():
    """中断時: 緊急停止する。追加動作（go_home）はさせない"""
    calls = []
    session = make_session(calls)

    async def body():
        raise asyncio.CancelledError()

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(session.run(body))

    assert session.status == "aborted"
    assert "Ctrl+C" in session.error
    assert "r1:emergency_stop" in calls and "r2:emergency_stop" in calls
    assert not any("go_home" in c for c in calls)
    # 緊急停止 → クリーンアップの順
    assert calls.index("r1:emergency_stop") < calls.index("r1:cleanup")
    assert "shared:cleanup" in calls


def test_error_triggers_go_home_not_emergency_stop():
    """エラー時: ホーム復帰して再送出。緊急停止はしない"""
    calls = []
    session = make_session(calls)

    async def body():
        raise ValueError("試験エラー")

    with pytest.raises(ValueError, match="試験エラー"):
        asyncio.run(session.run(body))

    assert session.status == "failed"
    assert session.error == "試験エラー"
    assert "r1:go_home" in calls and "r2:go_home" in calls
    assert not any("emergency_stop" in c for c in calls)
    assert "r1:cleanup" in calls and "shared:cleanup" in calls


def test_go_home_failure_does_not_mask_original_error():
    """ホーム復帰が失敗しても元の例外が伝播する"""
    calls = []
    session = make_session(calls)

    async def bad_go_home():
        raise ConnectionError("切断済み")

    session.robots[1].go_home = bad_go_home

    async def body():
        raise ValueError("元のエラー")

    with pytest.raises(ValueError, match="元のエラー"):
        asyncio.run(session.run(body))
    # robot1 の go_home 失敗後も robot2 は処理される
    assert "r2:go_home" in calls


def test_cleanup_failure_is_swallowed():
    calls = []
    session = make_session(calls)

    async def bad_cleanup():
        calls.append("r1:cleanup_failed")
        raise ConnectionError("切断済み")

    session.robots[1].cleanup = bad_cleanup

    async def body():
        return "ok"

    assert asyncio.run(session.run(body)) == "ok"
    assert "r2:cleanup" in calls and "shared:cleanup" in calls


def test_add_robot_unknown_id_raises_before_hardware():
    session = ExperimentSession()
    with pytest.raises(RuntimeError, match="config.yaml"):
        asyncio.run(session.add_robot(99))
    assert session.robots == {}

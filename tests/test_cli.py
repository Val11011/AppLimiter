# /home/val/MyConfigs/AppLimiter/tests/test_cli_pytest.py

import pytest
import argparse
import sys
import copy
import time

# MODIFIED: 更新导入语句以匹配新的 'src/applimiter' 结构
from applimiter import cli
from applimiter.constants import (
    CONFIG_FILE_PATH,
    USAGE_DATA_PATH,
    INITIAL_USAGE_DATA_STRUCTURE,
)


# ------------------- Pytest Fixtures -------------------

@pytest.fixture
def mock_env(mocker):
    """
    为测试函数准备一个完全隔离的、被模拟好的环境。
    'mocker' 是由 pytest-mock 插件提供的。
    """
    # 1. 创建干净的测试数据
    sample_config = {
        "applications": [
            {
                "name": "Steam",
                "process_keywords": ["steam.sh"],
                "daily_limits_by_day": {"weekdays": 60, "weekends": 120},
                "weekly_limit_minutes": 500,
            }
        ],
        "enable_config_modification_delay": False,
        "pending_modifications": [],
        "config_modification_delay_seconds": 300,
    }
    sample_usage_data = {
        "Steam": {
            **INITIAL_USAGE_DATA_STRUCTURE,
            "daily_seconds_today": 600,
            "weekly_seconds_this_week": 3600,
        }
    }

    # 2. MODIFIED: 更新 mocker.patch 的路径
    # 新的、修正后的 mocker 设置
    mock_load_json = mocker.patch("applimiter.cli.load_json")
    mock_save_json = mocker.patch("applimiter.cli.save_json")
    mock_check_privilege = mocker.patch("applimiter.cli.check_privilege")
    mock_get_pids = mocker.patch("applimiter.cli.get_process_pids")
    mock_time = mocker.patch("applimiter.cli.time.time")

    # --- 新增的代码 ---
    # 导入真正的 datetime 模块，以便我们能创建一个真实的 datetime 对象
    from datetime import datetime

    # 我们需要模拟在 cli 模块中被使用的 datetime 对象
    # 创建一个“假的” datetime 类
    mock_datetime = mocker.MagicMock()
    # 当代码调用 mock_datetime.now() 时，让它返回一个我们指定的日期
    # 2024年6月26日是一个周三 (工作日)
    mock_datetime.now.return_value = datetime(2024, 6, 26, 10, 30, 0)
    # 将 cli 模块中的 datetime.datetime 替换为我们这个“假的”类
    mocker.patch("applimiter.cli.datetime.datetime", mock_datetime)

    # 3. 定义模拟 load_json 的行为
    def _mocked_load_json(pathname, default_data=None, **kwargs):
        if pathname == CONFIG_FILE_PATH:
            # 当加载 config.json 时，我们仍然返回预设的 config
            return copy.deepcopy(sample_config)
        if pathname == USAGE_DATA_PATH:
            # 当加载 usage_data.json 时，我们也返回预设的 usage data
            return copy.deepcopy(sample_usage_data)
        # 对于任何其他情况，返回一个空字典或者 default_data
        return default_data if default_data is not None else {}

    # 4. 配置模拟函数的默认行为
    mock_load_json.side_effect = _mocked_load_json
    mock_get_pids.return_value = []
    mock_check_privilege.return_value = True
    mock_time.return_value = 1700000000.0

    # 5. 将模拟对象和数据返回给测试函数
    yield {
        "load_json": mock_load_json,
        "save_json": mock_save_json,
        "check_privilege": mock_check_privilege,
        "get_pids": mock_get_pids,
        "time": mock_time,
        "config": sample_config,
        "usage_data": sample_usage_data,
    }


# ------------------- 测试用例 (Test Cases) -------------------
# 测试用例的逻辑本身不需要改变

def test_privilege_check_fail(mock_env, capsys):
    """测试：当一个需要 root 的命令在没有权限时被调用，程序应失败退出。"""
    mock_env["check_privilege"].return_value = False
    args = argparse.Namespace(command="add", name="FailApp")

    with pytest.raises(SystemExit) as e:
        cli.handle_cli_command(args)

    assert e.value.code == 1
    captured = capsys.readouterr()
    assert "requires root privileges" in captured.err

def test_add_app_success(mock_env):
    """测试：成功添加一个新应用。"""
    args = argparse.Namespace(
        command="add",
        name="NewGame",
        keywords=["newgame"],
        daily_weekdays=30,
        daily_weekends=90,
        weekly=300,
    )
    config_to_modify = mock_env["load_json"](CONFIG_FILE_PATH)
    cli._handle_add_update_config_delay_commands(args, config_to_modify)
    mock_env["save_json"].assert_called_once()
    call_args, _ = mock_env["save_json"].call_args
    saved_config = call_args[1]
    assert len(saved_config["applications"]) == 2
    assert saved_config["applications"][1]["name"] == "NewGame"
    assert saved_config["applications"][1]["daily_limits_by_day"]["weekdays"] == 30

def test_remove_app_success(mock_env):
    """测试：成功移除一个已存在的应用。"""
    args = argparse.Namespace(command="remove", name="Steam")
    config_to_modify = mock_env["load_json"](CONFIG_FILE_PATH)

    cli._handle_remove_command(args, config_to_modify)

    assert mock_env["save_json"].call_count == 2
    config_save_call = mock_env["save_json"].call_args_list[0]
    assert config_save_call.args[0] == CONFIG_FILE_PATH
    saved_config = config_save_call.args[1]
    assert len(saved_config["applications"]) == 0
    usage_save_call = mock_env["save_json"].call_args_list[1]
    assert usage_save_call.args[0] == USAGE_DATA_PATH
    saved_usage_data = usage_save_call.args[1]
    assert "Steam" not in saved_usage_data

def test_status_command(mock_env, capsys):
    """测试：status 命令是否能正确打印应用状态。"""
    args = argparse.Namespace(command="status")
    mock_env["get_pids"].return_value = [1234, 5678]
    config_to_check = mock_env["load_json"](CONFIG_FILE_PATH)

    cli._handle_status_command(args, config_to_check)

    output = capsys.readouterr().out
    assert "--- Application Status ---" in output
    assert "App: Steam" in output
    assert "Running (PIDs: [1234, 5678])" in output
    assert "Today (Weekday): 10.0 / 60 min" in output

def test_pending_apply_when_locked(mock_env, capsys):
    """测试：当一个待定任务尚未解锁时，尝试应用它会失败。"""
    config_to_modify = mock_env["load_json"](CONFIG_FILE_PATH)
    config_to_modify["pending_modifications"] = [
        {
            "action": "remove_app",
            "payload": {"name": "Steam"},
            "unlock_timestamp": mock_env["time"].return_value + 100,
            "id": "test_id_123"
        }
    ]
    args = argparse.Namespace(command="pending", pending_action="apply", item_number_or_all="1")

    cli._apply_pending_modifications_logic(args, config_to_modify)

    mock_env["save_json"].assert_not_called()
    assert "not yet unlocked" in capsys.readouterr().err

def test_pending_apply_when_unlocked(mock_env):
    """测试：当一个待定任务已解锁时，可以成功应用。"""
    config_to_modify = mock_env["load_json"](CONFIG_FILE_PATH)
    config_to_modify["pending_modifications"] = [
        {
            "action": "remove_app",
            "payload": {"name": "Steam"},
            "unlock_timestamp": mock_env["time"].return_value - 100,
            "id": "test_id_123"
        }
    ]
    args = argparse.Namespace(command="pending", pending_action="apply", item_number_or_all="1")

    cli._apply_pending_modifications_logic(args, config_to_modify)

    mock_env["save_json"].assert_called()
    call_args, _ = mock_env["save_json"].call_args
    saved_config = call_args[1]
    assert len(saved_config["pending_modifications"]) == 0
    assert len(saved_config["applications"]) == 0
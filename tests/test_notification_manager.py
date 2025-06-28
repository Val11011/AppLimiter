import sys
import os
from unittest.mock import patch, MagicMock

# --- 关键的路径设置 ---
# 假设您的项目结构是：
# /.../rewrited_app_limiter/
#    -> notification_manager.py
#    -> test_runner.py
#
# 这段代码确保无论您在哪里执行它，都能正确找到模块
# (虽然放在同一目录下通常不是问题，但这是更健壮的做法)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rewrited_app_limiter.notification_manager import (
    get_desktop_users_with_display_info,
    send_desktop_notification_zenity,
)


def print_test_header(name):
    print("\n" + "=" * 10 + f" RUNNING TEST: {name} " + "=" * 10)


def print_test_result(success):
    if success:
        print(">>> RESULT: PASSED <<<\n")
    else:
        print(">>> RESULT: FAILED <<<\n")


# --- 测试用例 1: 正常情况 ---
def test_happy_path():
    print_test_header("Happy Path for get_desktop_users")
    success = False

    # 使用 patch 作为上下文管理器
    with (
        patch("rewrited_app_limiter.notification_manager.subprocess.run") as mock_run,
        patch(
            "rewrited_app_limiter.notification_manager.pwd.getpwnam"
        ) as mock_getpwnam,
        patch(
            "rewrited_app_limiter.notification_manager.os.path.exists"
        ) as mock_exists,
    ):
        # --- Arrange (准备模拟环境) ---
        mock_run.return_value = MagicMock(stdout="val\n", returncode=0)

        mock_pwnam_val = MagicMock(pw_uid=1000, pw_dir="/home/val")
        mock_getpwnam.return_value = mock_pwnam_val

        # 模拟 os.path.exists 只在特定路径下返回 True
        mock_exists.side_effect = lambda path: path == "/home/val/.Xauthority"

        # --- Act (执行被测函数) ---
        users_info = get_desktop_users_with_display_info()
        print(f"Function returned: {users_info}")

        # --- Assert (验证结果) ---
        try:
            assert len(users_info) == 1
            val_info = users_info[0]
            assert val_info["username"] == "val"
            assert val_info["uid"] == 1000
            assert val_info["xauthority"] == "/home/val/.Xauthority"
            success = True
        except AssertionError as e:
            print(f"Assertion failed: {e}")

    print_test_result(success)
    return success


# --- 测试用例 2: 找不到活跃用户 ---
def test_no_active_users():
    print_test_header("No Active Users Found")
    success = False

    with patch("rewrited_app_limiter.notification_manager.subprocess.run") as mock_run:
        # 模拟命令执行失败
        mock_run.side_effect = FileNotFoundError

        users_info = get_desktop_users_with_display_info()
        print(f"Function returned: {users_info}")

        try:
            assert users_info == []
            success = True
        except AssertionError:
            print("Assertion failed: Expected an empty list")

    print_test_result(success)
    return success


# --- 测试用例 3: 以 root 身份发送通知 ---
def test_send_notification_as_root():
    print_test_header("Send Notification as Root")
    success = False

    # 模拟 geteuid 返回 0 (root)
    with (
        patch("rewrited_app_limiter.notification_manager.os.geteuid", return_value=0),
        patch(
            "rewrited_app_limiter.notification_manager.subprocess.run"
        ) as mock_subprocess_run,
    ):
        user_info = {
            "username": "val",
            "uid": 1000,
            "display": ":0",
            "xauthority": "/home/val/.Xauthority",
            "home": "/home/val",
        }

        send_desktop_notification_zenity("Test Title", "Test Message", user_info)

        try:
            # 验证 subprocess.run 是否被调用
            assert mock_subprocess_run.called, "subprocess.run was not called"

            # 获取调用参数
            args, kwargs = mock_subprocess_run.call_args
            command_list = args[0]
            print(f"Command executed: {' '.join(command_list)}")

            # 验证命令是否包含 'sudo -u val'
            assert "sudo" in command_list
            assert "-u" in command_list
            assert "val" in command_list
            assert "zenity" in command_list

            # 验证环境变量
            env = kwargs.get("env", {})
            assert env.get("DISPLAY") == ":0"
            assert env.get("XAUTHORITY") == "/home/val/.Xauthority"

            success = True
        except AssertionError as e:
            print(f"Assertion failed: {e}")

    print_test_result(success)
    return success


# --- 主执行函数 ---
def main():
    print("=" * 40)
    print("      STARTING NOTIFICATION MANAGER TESTS      ")
    print("=" * 40)

    # 依次运行所有测试
    results = [
        test_happy_path(),
        test_no_active_users(),
        test_send_notification_as_root(),
    ]

    print("\n" + "=" * 40)
    print("              TEST SUMMARY              ")
    print("=" * 40)
    if all(results):
        print(f"All {len(results)} tests passed successfully!")
    else:
        passed_count = sum(1 for r in results if r)
        failed_count = len(results) - passed_count
        print(f"Summary: {passed_count} passed, {failed_count} failed.")


if __name__ == "__main__":
    main()

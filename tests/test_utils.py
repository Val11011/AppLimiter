import os
import logging
import json

# 在测试脚本的开头，我们需要先配置一下日志，这样才能看到 logger 的输出
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s"
)

# 从我们自己的包中导入 utils 模块
# 注意：为了让这个导入能工作，您需要从 rewrited_app_limiter 目录运行此脚本
import rewrited_app_limiter.utils as utils

# --- 测试设置 ---
TEST_DIR = "./test_area"
TEST_FILE = os.path.join(TEST_DIR, "test_config.json")
TEST_DATA = {
    "project": "app_limiter_rewrite",
    "version": 1,
    "user": "Val",
    "features": ["cli", "daemon", "gui"],
}
DEFAULT_TEST_DATA = {"status": "default"}


def cleanup():
    """清理测试环境，删除创建的文件和目录"""
    if os.path.exists(TEST_FILE):
        os.remove(TEST_FILE)
    if os.path.exists(TEST_DIR):
        os.rmdir(TEST_DIR)
    print("\n--- Cleanup complete ---")


def run_tests():
    """运行所有测试用例"""
    print("========= Starting a test run for utils.py =========\n")

    # --- 测试 1: save_json & load_json 的正常流程 ---
    print("--- Test 1: Testing normal save and load ---")
    try:
        utils.save_json(TEST_FILE, TEST_DATA)
        print(f"save_json executed. Checking if file '{TEST_FILE}' exists...")
        assert os.path.exists(TEST_FILE), "FAILED: File was not created by save_json!"
        print("✅ PASSED: File created.")

        loaded_data = utils.load_json(TEST_FILE)
        print("load_json executed. Comparing data...")
        assert loaded_data == TEST_DATA, (
            "FAILED: Loaded data does not match saved data!"
        )
        print("✅ PASSED: Data matches perfectly.\n")
    finally:
        cleanup()

    # --- 测试 2: load_json 在文件不存在时的行为 ---
    print("--- Test 2: Testing load_json when file does not exist ---")
    try:
        print("Attempting to load a non-existent file (read_only=True)...")
        data = utils.load_json(
            "non_existent_file.json", default_data=DEFAULT_TEST_DATA, read_only=True
        )
        assert data == DEFAULT_TEST_DATA, (
            "FAILED: Did not return default data in read_only mode!"
        )
        print("✅ PASSED: Correctly returned default data in read_only mode.")

        print("\nAttempting to load a non-existent file (read_only=False)...")
        data = utils.load_json(
            TEST_FILE, default_data=DEFAULT_TEST_DATA, read_only=False
        )
        assert os.path.exists(TEST_FILE), "FAILED: Did not create a new file!"
        assert data == DEFAULT_TEST_DATA, "FAILED: Did not return created default data!"
        print("✅ PASSED: Correctly created a new file with default data.\n")
    finally:
        cleanup()

    # --- 测试 3: load_json 对损坏文件的恢复能力 ---
    print("--- Test 3: Testing load_json with corrupted file ---")
    try:
        # 手动创建一个损坏的 JSON 文件
        os.makedirs(TEST_DIR, exist_ok=True)
        with open(TEST_FILE, "w") as f:
            f.write('{"key": "value", }')  # 多了一个逗号，这是无效的JSON

        print("Created a corrupted JSON file. Now loading it...")
        loaded_data = utils.load_json(TEST_FILE, default_data=DEFAULT_TEST_DATA)
        assert loaded_data == DEFAULT_TEST_DATA, (
            "FAILED: Did not recover with default data!"
        )
        print("✅ PASSED: Correctly handled corrupted file and returned default data.")

        # 检查文件是否已被修复
        with open(TEST_FILE, "r") as f:
            repaired_data = json.load(f)
        assert repaired_data == DEFAULT_TEST_DATA, (
            "FAILED: File was not repaired with default data!"
        )
        print(
            "✅ PASSED: Corrupted file was successfully overwritten with a clean default.\n"
        )
    finally:
        cleanup()

    # --- 测试 4: check_dependencies ---
    print("--- Test 4: Testing check_dependencies ---")
    print("Checking for 'zenity' (should pass on your system)...")
    assert utils.check_dependencies() is True, (
        "FAILED: check_dependencies should return True if zenity is installed!"
    )
    print("✅ PASSED: check_dependencies returned True.\n")

    print("========= All tests completed successfully! =========\n")


if __name__ == "__main__":
    try:
        run_tests()
    except AssertionError as e:
        print(f"\n🔥🔥🔥 A TEST FAILED! 🔥🔥🔥\n{e}")
        # 在测试失败后也执行清理，避免留下垃圾文件
        cleanup()

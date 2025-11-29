import os
import shutil
import subprocess
import sys
import platform
import zipfile

# ---------------------------------------------------------
# 配置区域
# ---------------------------------------------------------
PROJECT_NAME = "NodeTool"  # 生成的 exe/二进制文件名
SPEC_FILE = "node_tool.spec"  # PyInstaller 配置文件
DIST_DIR = "dist"
BUILD_DIR = "build"
RELEASE_DIR = "release"  # 最终发布的文件夹

# 需要复制到发布目录的外部资源
# 格式: (源路径, 目标文件夹名)
EXTERNAL_ASSETS = [
    # (源路径, 目标路径: 空字符串代表根目录)
    ("app/subscription/nodes", "nodes"),  # 复制 nodes 文件夹
    ("db_config.json", ""),      # 复制数据库配置(如果存在)
    ("app.db", ""),              # 复制数据库(如果存在, 可选)
]

def clean_dirs():
    """清理构建产生的临时文件夹"""
    print(f"🧹 清理旧的构建文件...")
    for d in [DIST_DIR, BUILD_DIR, RELEASE_DIR]:
        if os.path.exists(d):
            shutil.rmtree(d, ignore_errors=True)

def run_pyinstaller():
    """运行 PyInstaller"""
    print(f"📦 开始使用 PyInstaller 打包 ({platform.system()})...")
    
    # 检查 spec 文件是否存在
    if not os.path.exists(SPEC_FILE):
        print(f"❌ 错误: 找不到 {SPEC_FILE}，请先生成 spec 文件。")
        sys.exit(1)

    # 运行 PyInstaller 命令
    try:
        subprocess.check_call([sys.executable, "-m", "PyInstaller", SPEC_FILE, "--clean", "-y"])
        print("✅ PyInstaller 打包完成")
    except subprocess.CalledProcessError:
        print("❌ PyInstaller 打包失败")
        sys.exit(1)

def organize_release():
    """整理发布文件夹：复制 exe 和外部资源"""
    print(f"📂 正在整理发布文件到 '{RELEASE_DIR}'...")
    
    if not os.path.exists(RELEASE_DIR):
        os.makedirs(RELEASE_DIR)

    # 1. 确定生成的可执行文件名字
    system_name = platform.system()
    exe_name = f"{PROJECT_NAME}.exe" if system_name == "Windows" else PROJECT_NAME
    
    src_exe = os.path.join(DIST_DIR, exe_name)
    dst_exe = os.path.join(RELEASE_DIR, exe_name)

    if not os.path.exists(src_exe):
        print(f"❌ 错误: 在 dist 目录找不到生成的文件: {src_exe}")
        sys.exit(1)

    # 2. 移动可执行文件
    shutil.copy2(src_exe, dst_exe)
    print(f"   -> 已复制程序: {exe_name}")

    # 3. 复制外部资源 (nodes 文件夹等)
    for src, dst_folder in EXTERNAL_ASSETS:
        # 构建完整源路径
        if not os.path.exists(src):
            print(f"   ⚠️ 警告: 资源未找到，跳过: {src}")
            continue

        final_dst = os.path.join(RELEASE_DIR, dst_folder)
        
        if os.path.isdir(src):
            # 如果是文件夹 (如 nodes)
            if os.path.exists(final_dst):
                shutil.rmtree(final_dst)
            shutil.copytree(src, final_dst)
            print(f"   -> 已复制文件夹: {src} -> {dst_folder}/")
        else:
            # 如果是文件
            shutil.copy2(src, final_dst)
            print(f"   -> 已复制文件: {src}")

    # 4. 如果是 Linux，赋予执行权限
    if system_name != "Windows":
        os.chmod(dst_exe, 0o755)

def make_archive():
    """压缩发布文件夹"""
    print("🗜️ 正在创建压缩包...")
    
    # 架构名称 (例如 amd64, arm64, win32)
    arch = platform.machine().lower()
    os_name = platform.system().lower()
    zip_name = f"{PROJECT_NAME}_{os_name}_{arch}.zip"
    
    # 切换目录以便压缩包内的路径整洁
    shutil.make_archive(os.path.join(".", zip_name.replace('.zip', '')), 'zip', RELEASE_DIR)
    
    print(f"🎉 打包成功! 文件位于: {os.path.abspath(zip_name)}")

if __name__ == "__main__":
    clean_dirs()
    run_pyinstaller()
    organize_release()
    make_archive()

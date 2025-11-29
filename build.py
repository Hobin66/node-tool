import os
import shutil
import subprocess
import sys
import platform
import zipfile
import glob

# ---------------------------------------------------------
# Configuration Area
# ---------------------------------------------------------
PROJECT_NAME = "NodeTool"
SPEC_FILE = "node_tool.spec"
DIST_DIR = "dist"
BUILD_DIR = "build"
RELEASE_DIR = "release"

EXTERNAL_ASSETS = [
    ("app/subscription/nodes", "nodes"),
    ("db_config.json", ""),
    ("app.db", ""),
]

def clean_dirs():
    """Clean up temporary build directories"""
    print(f"[Clean] Cleaning up old build files...", flush=True)
    for d in [DIST_DIR, BUILD_DIR, RELEASE_DIR]:
        if os.path.exists(d):
            shutil.rmtree(d, ignore_errors=True)

def run_pyinstaller():
    """Run PyInstaller"""
    print(f"[Build] Starting PyInstaller build ({platform.system()})...", flush=True)
    
    if not os.path.exists(SPEC_FILE):
        print(f"[Error] Error: {SPEC_FILE} not found.", flush=True)
        sys.exit(1)

    # 自动修改 .spec 文件以禁用 UPX
    try:
        with open(SPEC_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
        if "upx=True" in content:
            print("[Config] Disabling UPX in spec file...", flush=True)
            content = content.replace("upx=True", "upx=False")
            with open(SPEC_FILE, 'w', encoding='utf-8') as f:
                f.write(content)
    except Exception as e:
        print(f"[Warning] Failed to edit spec file: {e}", flush=True)

    try:
        subprocess.check_call([sys.executable, "-m", "PyInstaller", SPEC_FILE, "--clean", "-y"])
        print("[Success] PyInstaller build completed", flush=True)
    except subprocess.CalledProcessError:
        print("[Error] PyInstaller build failed", flush=True)
        sys.exit(1)

def organize_release():
    """Organize release folder"""
    print(f"[Organize] Organizing release files to '{RELEASE_DIR}'...", flush=True)
    
    if not os.path.exists(RELEASE_DIR):
        os.makedirs(RELEASE_DIR)

    system_name = platform.system()
    found_exe = None
    if system_name == "Windows":
        exe_files = glob.glob(os.path.join(DIST_DIR, "*.exe"))
        if exe_files: found_exe = exe_files[0]
    else:
        potential_files = [f for f in os.listdir(DIST_DIR) if os.path.isfile(os.path.join(DIST_DIR, f))]
        if potential_files: found_exe = os.path.join(DIST_DIR, potential_files[0])

    if not found_exe or not os.path.exists(found_exe):
        print(f"[Error] No executable file found in {DIST_DIR}", flush=True)
        if os.path.exists(DIST_DIR): print(f"Content: {os.listdir(DIST_DIR)}", flush=True)
        sys.exit(1)
        
    exe_filename = os.path.basename(found_exe)
    dst_exe = os.path.join(RELEASE_DIR, exe_filename)
    shutil.copy2(found_exe, dst_exe)

    for src, dst_folder in EXTERNAL_ASSETS:
        if not os.path.exists(src):
            print(f"   [Warning] Asset not found: {src}", flush=True)
            continue
        final_dst = os.path.join(RELEASE_DIR, dst_folder)
        if os.path.isdir(src):
            if os.path.exists(final_dst): shutil.rmtree(final_dst)
            shutil.copytree(src, final_dst)
        else:
            shutil.copy2(src, final_dst)

    if system_name != "Windows":
        os.chmod(dst_exe, 0o755)
    
    print(f"[Done] Release files organized in '{RELEASE_DIR}' folder.", flush=True)

if __name__ == "__main__":
    clean_dirs()
    run_pyinstaller()
    organize_release()
    # make_archive()  <-- 不再在 Python 里压缩，交给 GitHub Actions

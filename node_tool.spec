# -*- mode: python ; coding: utf-8 -*-

import sys
import os
from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

# -----------------------------------------------------------------------------
# 1. 动态收集数据文件的逻辑
# -----------------------------------------------------------------------------
def collect_pkg_data(package_root, include_extensions, exclude_dirs=None):
    datas = []
    if exclude_dirs is None:
        exclude_dirs = []

    for root, dirs, files in os.walk(package_root):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        
        for filename in files:
            ext = os.path.splitext(filename)[1].lower()
            if ext in include_extensions:
                source_path = os.path.join(root, filename)
                target_dir = root 
                datas.append((source_path, target_dir))
                print(f"Adding internal asset: {source_path} -> {target_dir}")
            
    return datas

# 定义需要打包进 exe 的文件类型
internal_extensions = ['.html', '.css', '.js', '.png', '.ico', '.svg', '.sh']

# 🔴 保持排除 nodes 文件夹 (防止打包个人数据)
excluded_folders = ['nodes', '__pycache__']

# 1. 常规收集 (不含 nodes)
added_datas = collect_pkg_data('app', internal_extensions, excluded_folders)

# -----------------------------------------------------------------------------
# 🟢 [新增] 手动打包关键模板文件 (Self-Healing 机制)
# -----------------------------------------------------------------------------
# 我们把这些模板文件打包进 exe 内部的一个特殊目录 'bundled_templates'
# 这样程序运行时如果发现外部缺少文件，可以从这里恢复
template_files = [
    'clash_meta.yaml',
    'customize.list',
    'direct.list',
    'install-singbox.sh'
]

# 假设你的源码结构是 app/subscription/nodes/
base_node_path = os.path.join('app', 'modules', 'subscription', 'nodes')
# 如果你的目录结构不同，请尝试:
if not os.path.exists(base_node_path):
    # 尝试备用路径 (根据你的 Project Tree)
    base_node_path = os.path.join('app', 'subscription', 'nodes')

for filename in template_files:
    src_path = os.path.join(base_node_path, filename)
    if os.path.exists(src_path):
        # 格式: (源文件路径, 目标内部文件夹)
        added_datas.append((src_path, 'bundled_templates'))
        print(f"🟢 [Template] Bundling default: {src_path} -> bundled_templates/{filename}")
    else:
        print(f"⚠️ [Warning] Template not found during build: {src_path}")

# -----------------------------------------------------------------------------
# 2. PyInstaller Analysis
# -----------------------------------------------------------------------------
a = Analysis(
    ['run.py'],
    pathex=[],
    binaries=[],
    datas=added_datas, 
    hiddenimports=['engineio.async_drivers.threading'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='NodeTool',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

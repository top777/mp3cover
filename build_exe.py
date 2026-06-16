"""
一键打包脚本：构建 MP3专辑封面下载器.exe 并生成发布目录
用法: python build_exe.py              # 仅构建 exe
      python build_exe.py --release    # 构建 exe + 生成发布目录
      python build_exe.py --zip        # 构建 exe + 生成 zip 发布包
      python build_exe.py --clean      # 仅清理构建产物
"""
import sys
import os
import shutil
import subprocess
import argparse
import zipfile
from pathlib import Path

PROJECT_DIR = Path(__file__).parent
SPEC_FILE = PROJECT_DIR / "MP3专辑封面下载器.spec"
DIST_DIR = PROJECT_DIR / "dist"
BUILD_DIR = PROJECT_DIR / "build"
RELEASE_DIR = PROJECT_DIR / "release"
EXE_NAME = "MP3专辑封面下载器.exe"
RELEASE_ZIP = PROJECT_DIR / "MP3专辑封面下载器_发布包.zip"


def step(msg):
    print(f"\n{'=' * 60}")
    print(f"  {msg}")
    print(f"{'=' * 60}")


def clean():
    """清理所有构建产物"""
    for d in [BUILD_DIR, DIST_DIR, RELEASE_DIR]:
        if d.exists():
            print(f"  删除: {d}")
            shutil.rmtree(d)
    for f in PROJECT_DIR.glob("*.zip"):
        if "发布包" in f.name:
            print(f"  删除: {f}")
            f.unlink()


def check_venv():
    """检查并激活虚拟环境"""
    venv_python = PROJECT_DIR / "mp3pic_env" / "Scripts" / "python.exe"
    if venv_python.exists():
        return str(venv_python)
    return sys.executable


def ensure_pyinstaller(python_exe):
    """确保 PyInstaller 已安装"""
    try:
        subprocess.run(
            [python_exe, "-c", "import PyInstaller"],
            capture_output=True, check=True
        )
    except subprocess.CalledProcessError:
        print("  PyInstaller 未安装，正在安装...")
        subprocess.run(
            [python_exe, "-m", "pip", "install", "pyinstaller"],
            check=True
        )


def build_exe(python_exe):
    """使用 PyInstaller 构建 exe"""
    ensure_pyinstaller(python_exe)

    cmd = [python_exe, "-m", "PyInstaller", str(SPEC_FILE), "--distpath", str(DIST_DIR), "--workpath", str(BUILD_DIR)]
    print(f"  执行: {' '.join(cmd)}")
    subprocess.run(cmd, check=True, cwd=str(PROJECT_DIR))

    exe_path = DIST_DIR / EXE_NAME
    if exe_path.exists():
        size_mb = exe_path.stat().st_size / (1024 * 1024)
        print(f"\n  构建成功: {exe_path} ({size_mb:.1f} MB)")
    else:
        print(f"\n  错误: 未找到生成的 exe 文件")
        sys.exit(1)


def create_release():
    """创建发布目录"""
    step("生成发布目录")

    if RELEASE_DIR.exists():
        shutil.rmtree(RELEASE_DIR)
    RELEASE_DIR.mkdir()

    # 复制 exe
    exe_src = DIST_DIR / EXE_NAME
    shutil.copy(exe_src, RELEASE_DIR / EXE_NAME)
    print(f"  复制: {EXE_NAME}")

    # 复制 README
    readme = PROJECT_DIR / "README.txt"
    if readme.exists():
        shutil.copy(readme, RELEASE_DIR / "README.txt")
        print(f"  复制: README.txt")

    # 生成安装脚本
    installer_content = f'''@echo off
chcp 65001 >nul
echo =========================================
echo MP3专辑封面下载器 安装程序
echo =========================================
echo.
echo 正在创建桌面快捷方式...
copy "{EXE_NAME}" "%USERPROFILE%\\Desktop\\" >nul 2>&1
echo 桌面快捷方式创建完成！
echo.
echo 安装成功！可以从桌面双击 "{EXE_NAME}" 启动。
echo.
pause
'''
    installer_path = RELEASE_DIR / "安装.bat"
    installer_path.write_text(installer_content, encoding="gbk")
    print(f"  生成: 安装.bat")

    # 创建示例目录
    (RELEASE_DIR / "示例").mkdir()
    print(f"  创建: 示例/ 目录")

    print(f"\n  发布目录已就绪: {RELEASE_DIR}")


def create_zip():
    """生成 zip 发布包"""
    step("生成 ZIP 发布包")

    if RELEASE_ZIP.exists():
        RELEASE_ZIP.unlink()

    with zipfile.ZipFile(RELEASE_ZIP, 'w', zipfile.ZIP_DEFLATED) as zf:
        for f in RELEASE_DIR.rglob("*"):
            arcname = f.relative_to(RELEASE_DIR)
            zf.write(f, arcname)
            print(f"  打包: {arcname}")

    size_mb = RELEASE_ZIP.stat().st_size / (1024 * 1024)
    print(f"\n  发布包已生成: {RELEASE_ZIP} ({size_mb:.1f} MB)")


def main():
    parser = argparse.ArgumentParser(description="MP3专辑封面下载器 一键打包脚本")
    parser.add_argument("--release", action="store_true", help="构建后生成发布目录")
    parser.add_argument("--zip", action="store_true", help="构建后生成 zip 发布包")
    parser.add_argument("--clean", action="store_true", help="仅清理所有构建产物")
    args = parser.parse_args()

    os.chdir(str(PROJECT_DIR))

    if args.clean:
        step("清理构建产物")
        clean()
        print("\n清理完成。")
        return

    # 默认行为：构建 exe
    step("MP3专辑封面下载器 - 一键打包")
    print(f"  项目目录: {PROJECT_DIR}")

    clean()

    python_exe = check_venv()
    print(f"  Python: {python_exe}")

    step("构建 exe")
    build_exe(python_exe)

    if args.release or args.zip:
        create_release()

    if args.zip:
        create_zip()

    step("完成")
    print(f"  可执行文件: {DIST_DIR / EXE_NAME}")
    if args.release:
        print(f"  发布目录:   {RELEASE_DIR}")
    if args.zip:
        print(f"  发布包:     {RELEASE_ZIP}")


if __name__ == "__main__":
    main()

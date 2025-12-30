import argparse
import os
import shutil
import subprocess
import sys
import tarfile
import urllib.request
from pathlib import Path
from typing import Optional

APKTOOL_URL = "https://github.com/iBotPeaches/Apktool/releases/download/v2.12.1/apktool_2.12.1.jar"
LIBLOVELY_URL = "https://github.com/kodenamekrak/lovely-injector/releases/download/v0.8.0-unofficial/lovely-aarch64-linux-android.tar.gz"


def run(cmd, **kwargs):
    try:
        return subprocess.run(cmd, check=True, **kwargs)
    except subprocess.CalledProcessError as e:
        cmd_str = cmd if isinstance(cmd, str) else " ".join(map(str, cmd))
        print(f"\nError: Command failed with exit code {e.returncode}: {cmd_str}")
        sys.exit(1)
    except FileNotFoundError as e:
        print(f"\nError: Command not found: {e}")
        sys.exit(1)


def ensure_setup(
    venv_dir: Path, bin_dir: Path, python: Path, apktool_jar: Path, lovely_path: Path
):
    if not venv_dir.exists():
        print(f"Creating venv in {venv_dir}...")
        subprocess.run([sys.executable, "-m", "venv", venv_dir], check=True)

    print("Installing dependencies...")
    run(f'"{python}" -m pip install buildapp==1.5.0 install-jdk --upgrade', shell=True)
    run([bin_dir / "buildapp_fetch_tools"])

    if not apktool_jar.exists():
        print("Downloading apktool...")
        urllib.request.urlretrieve(APKTOOL_URL, apktool_jar)

    if not lovely_path.exists():
        print("Downloading Lovely library...")
        urllib.request.urlretrieve(LIBLOVELY_URL, lovely_path)


def get_java_cmd(venv_dir: Path, python: Path) -> str:
    java = shutil.which("java")
    if java:
        return java

    jre_dir = venv_dir / "jre"
    java_bin = jre_dir / "bin" / "java"

    if not java_bin.exists():
        print("Java not found. Installing local JRE...")
        install_cmd = f"import install_jdk; print(install_jdk.install('21', jre=True, path='{jre_dir}'))"
        run([python, "-c", install_cmd])

    return str(java_bin)


def patch_apk(
    input_apk: Path,
    output_apk: Path,
    force: bool,
    pkg_name: Optional[str],
    pkg_id: Optional[str],
):
    venv_dir = input_apk.parent / f"{input_apk.stem}_venv"
    bin_dir = venv_dir / ("Scripts" if os.name == "nt" else "bin")
    python = bin_dir / "python"
    apktool_jar = venv_dir / "apktool.jar"
    lovely_path = venv_dir / "lovely.tar.gz"

    ensure_setup(venv_dir, bin_dir, python, apktool_jar, lovely_path)
    java = get_java_cmd(venv_dir, python)
    work_dir = venv_dir / (input_apk.stem + "_decompiled")

    if work_dir.exists() and force:
        shutil.rmtree(work_dir)

    print(f"Decompiling {input_apk}...")
    decompile_cmd = [
        java,
        "-jar",
        apktool_jar,
        "d",
        input_apk,
        "-o",
        work_dir,
    ]
    if force:
        decompile_cmd.append("-f")
    run(decompile_cmd)

    print("Extracting Lovely library...")
    extract_dir = work_dir / "lib" / "arm64-v8a"
    with tarfile.open(lovely_path, "r:gz") as tar:
        tar.extractall(extract_dir)

    smali_file = (
        work_dir / "smali" / "org" / "love2d" / "android" / "GameActivity.smali"
    )
    if smali_file.exists():
        print("Patching GameActivity.smali...")
        with open(smali_file, "r", encoding="utf-8") as f:
            content = f.read()
        original_line = "invoke-direct {p0}, Lorg/libsdl/app/SDLActivity;-><init>()V"
        if original_line in content:
            insert_code = "\n".join(
                [
                    'const-string v0, "lovely"',
                    "\tinvoke-static {v0}, Ljava/lang/System;->loadLibrary(Ljava/lang/String;)V\n\t",
                ]
            )
            new_content = content.replace(
                original_line,
                insert_code + original_line,
                1,
            )
            with open(smali_file, "w", encoding="utf-8") as f:
                f.write(new_content)
        else:
            print("Error: SDLActivity init line not found in GameActivity.smali")
            sys.exit(1)
    else:
        print("Error: GameActivity.smali not found")
        sys.exit(1)

    orig_pkg_id = "com.playstack.balatro.android"
    pkg_id = (orig_pkg_id + ".mod") if not pkg_id else pkg_id

    manifest_file = work_dir / "AndroidManifest.xml"
    if manifest_file.exists():
        print("Patching AndroidManifest.xml...")
        with open(manifest_file, "r", encoding="utf-8") as f:
            content = f.read()
        if orig_pkg_id in content:
            new_content = content.replace(orig_pkg_id, pkg_id)
            if pkg_name:
                orig_pkg_name = 'android:label="Balatro"'
                if orig_pkg_name in new_content:
                    new_content = new_content.replace(
                        orig_pkg_name, f'android:label="{pkg_name}"'
                    )
                else:
                    print(
                        "Warning: Original package name not found in AndroidManifest.xml, skipping name patch"
                    )
            with open(manifest_file, "w", encoding="utf-8") as f:
                f.write(new_content)
        else:
            print(
                "Warning: Original package ID not found in AndroidManifest.xml, skipping package ID patch"
            )
    else:
        print("Error: AndroidManifest.xml not found")
        sys.exit(1)

    print(f"Rebuilding to {output_apk}...")
    rebuild_cmd = [
        bin_dir / "buildapp",
        "-d",
        work_dir,
        "-o",
        output_apk,
    ]
    run(rebuild_cmd)

    print(f"\nSuccessfully patched: {output_apk}")


def main():
    parser = argparse.ArgumentParser(description="Self-contained APK Patcher Gist")
    parser.add_argument("input", type=Path, help="Input APK path")
    parser.add_argument("-o", "--output", type=Path, help="Output APK path")
    parser.add_argument("--package-name", help="New package name")
    parser.add_argument("--package-id", help="New package ID")
    parser.add_argument(
        "-f", "--force", action="store_true", help="Overwrite existing files"
    )

    args = parser.parse_args()

    if not args.input.exists():
        print(f"Error: Input file {args.input} not found.")
        sys.exit(1)

    output = args.output or args.input.with_suffix(".mod.apk")

    try:
        patch_apk(args.input, output, args.force, args.package_name, args.package_id)
    except KeyboardInterrupt:
        print("\nInterrupted by user.")
        sys.exit(1)


if __name__ == "__main__":
    main()

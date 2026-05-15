#!/usr/bin/env python3
"""Claude Code Vietnamese IME Fix - Test Runner."""

import json
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
SOURCES_DIR = SCRIPT_DIR / "tests" / "sources"
PATCHER = SCRIPT_DIR / "patcher.py"

GREEN = "\033[0;32m"
RED = "\033[0;31m"
BLUE = "\033[0;34m"
NC = "\033[0m"
LEGACY_JS_VERSION = "2.1.96"


def get_latest_versions(count=3):
    """Get latest N versions from npm registry."""
    result = subprocess.run(
        ["npm", "view", "@anthropic-ai/claude-code", "versions", "--json"],
        capture_output=True, text=True, timeout=30
    )
    versions = json.loads(result.stdout)

    def semver_key(v):
        parts = v.replace("-", ".").split(".")
        return tuple(int(p) if p.isdigit() else 0 for p in parts[:3])

    return sorted(versions, key=semver_key, reverse=True)[:count]


def safe_extract_package(tar, destination):
    """Extract package/* entries without requiring Python 3.12's filter arg."""
    destination = destination.resolve()
    for member in tar.getmembers():
        if not member.name.startswith("package/"):
            continue
        relative = member.name[8:]
        if not relative:
            continue
        target = (destination / relative).resolve()
        if destination not in target.parents and target != destination:
            raise RuntimeError(f"unsafe tar entry: {member.name}")
        member.name = relative
        tar.extract(member, destination)


def platform_native_package(version):
    """Return the current platform's native Claude Code package name."""
    system = platform.system().lower()
    machine = platform.machine().lower()

    if machine in ("arm64", "aarch64"):
        arch = "arm64"
    elif machine in ("x86_64", "amd64"):
        arch = "x64"
    else:
        raise RuntimeError(f"unsupported test arch: {machine}")

    if system == "darwin":
        key = f"darwin-{arch}"
    elif system == "linux":
        key = f"linux-{arch}"
    elif system == "windows":
        key = f"win32-{arch}"
    else:
        raise RuntimeError(f"unsupported test platform: {system}")

    return f"@anthropic-ai/claude-code-{key}@{version}"


def extract_npm_package(package_spec, destination):
    """Download an npm package and extract it into destination."""
    with tempfile.TemporaryDirectory() as temp_dir:
        subprocess.run(
            ["npm", "pack", package_spec],
            cwd=temp_dir, capture_output=True, timeout=120, check=True
        )
        tarball = list(Path(temp_dir).glob("*.tgz"))[0]

        destination.mkdir(parents=True, exist_ok=True)
        with tarfile.open(tarball, "r:gz") as tar:
            safe_extract_package(tar, destination)


def download_npm(version):
    """Download Claude Code and return (target path, package kind)."""
    version_dir = SOURCES_DIR / f"v{version}"
    extract_npm_package(f"@anthropic-ai/claude-code@{version}", version_dir)

    cli_js = version_dir / "cli.js"
    if cli_js.exists():
        return cli_js, "cli-js"

    native_dir = version_dir / "native"
    extract_npm_package(platform_native_package(version), native_dir)
    binary = native_dir / ("claude.exe" if platform.system() == "Windows" else "claude")
    if not binary.exists():
        raise RuntimeError(f"native binary not found for {version}")
    if platform.system() != "Windows":
        os.chmod(binary, 0o755)
    return binary, "native"


def run_patcher(args):
    """Run patcher with args, return (success, stdout, stderr)."""
    result = subprocess.run(
        [sys.executable, str(PATCHER)] + args,
        capture_output=True, text=True, timeout=30
    )
    return result.returncode == 0, result.stdout, result.stderr


def verify_runs(file_path, kind):
    """Verify target runs with --version."""
    cmd = ["node", str(file_path), "--version"] if kind == "cli-js" else [str(file_path), "--version"]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
    return result.returncode == 0, result.stdout.strip()


def verify_fix_logic(file_path):
    """Verify patched code contains correct fix logic (backspace + insert)."""
    content = Path(file_path).read_text(encoding='utf-8')

    # Must have patch marker
    if "/* Vietnamese IME fix */" not in content:
        return False, "missing patch marker"

    # Extract the fix block (from marker to next return;})
    marker_idx = content.index("/* Vietnamese IME fix */")
    fix_end = content.find("return;}", marker_idx)
    if fix_end == -1:
        return False, "cannot find fix block end"
    fix_block = content[marker_idx:fix_end + 8]

    # Must have backspace loop
    if ".backspace()" not in fix_block:
        return False, "missing .backspace() in fix"

    # Must have insert loop
    if ".insert(" not in fix_block:
        return False, "missing .insert() in fix"

    # Original bug pattern should be gone (deleteTokenBefore is in the old bug block)
    # Note: deleteTokenBefore may still exist elsewhere in the file, so check
    # that there's no block combining includes(\x7f) with deleteTokenBefore
    del_char = chr(127)
    bug_pattern = f'.includes("{del_char}")'
    # Count occurrences - should only appear in our fix block
    occurrences = content.count(bug_pattern)
    if occurrences > 1:
        return False, f"bug pattern appears {occurrences} times (expected 1 from fix)"

    return True, "fix logic OK"


def main():
    print()
    print("=" * 60)
    print("  Claude Code Vietnamese IME Fix - Test Suite")
    print("=" * 60)
    print()

    # Clean old sources
    if SOURCES_DIR.exists():
        print(f"{BLUE}-> Cleaning old sources...{NC}")
        shutil.rmtree(SOURCES_DIR)

    # Get versions
    print(f"{BLUE}-> Getting latest versions...{NC}")
    versions = get_latest_versions(3)
    if LEGACY_JS_VERSION not in versions:
        versions.append(LEGACY_JS_VERSION)
    print(f"   {', '.join(versions)}")
    print()

    results = []

    for version in versions:
        print(f"{BLUE}-> Testing v{version}{NC}")
        print(f"   downloading...", end=" ", flush=True)

        try:
            target, kind = download_npm(version)

            # Test patch
            print("patch...", end=" ", flush=True)
            ok, stdout, stderr = run_patcher(["--path", str(target)])
            if not ok:
                print(f"{RED}✗{NC} Patch failed: {stderr}")
                results.append(("patch", version, False))
                continue

            # Verify --version
            print("verify...", end=" ", flush=True)
            ok, output = verify_runs(target, kind)
            if not ok:
                print(f"{RED}✗{NC} --version failed")
                results.append(("verify", version, False))
                continue

            if kind == "native":
                if "không cần patch" not in stdout.lower():
                    print(f"{RED}✗{NC} native detection message missing")
                    results.append(("native", version, False))
                    continue
                print(f"{GREEN}✓{NC} native {output}")
                results.append(("native", version, True))
                continue

            # Verify fix logic (backspace + insert)
            print("logic...", end=" ", flush=True)
            ok, detail = verify_fix_logic(target)
            if not ok:
                print(f"{RED}✗{NC} {detail}")
                results.append(("logic", version, False))
                continue

            # Test double-patch
            print("double-patch...", end=" ", flush=True)
            ok, stdout, _ = run_patcher(["--path", str(target)])
            if "Đã patch" not in stdout:
                print(f"{RED}✗{NC} double-patch not detected")
                results.append(("double", version, False))
                continue

            # Test restore
            print("restore...", end=" ", flush=True)
            ok, _, stderr = run_patcher(["--restore", "--path", str(target)])
            if not ok:
                print(f"{RED}✗{NC} restore failed: {stderr}")
                results.append(("restore", version, False))
                continue

            print(f"{GREEN}✓{NC} {output}")
            results.append(("npm", version, True))

        except Exception as e:
            print(f"{RED}✗{NC} {e}")
            results.append(("npm", version, False))

        print()

    # Edge case: nonexistent file
    print(f"{BLUE}-> Testing edge cases{NC}")
    print(f"   nonexistent file...", end=" ", flush=True)
    ok, _, _ = run_patcher(["--path", "/nonexistent/file.js"])
    if not ok:
        print(f"{GREEN}✓{NC} correctly rejected")
        results.append(("edge", "N/A", True))
    else:
        print(f"{RED}✗{NC} should have failed")
        results.append(("edge", "N/A", False))
    print()

    # Summary
    print("=" * 60)
    passed = sum(1 for _, _, ok in results if ok)
    total = len(results)

    if passed == total:
        print(f"{GREEN}All {total} tests passed!{NC}")
        return 0
    else:
        print(f"{RED}{passed}/{total} tests passed{NC}")
        return 1


if __name__ == "__main__":
    sys.exit(main())

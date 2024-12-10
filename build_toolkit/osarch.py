import platform
import re

def get_os_arch():
    # Map Python's OS names to normalized OS names
    # These match Go's GOOS naming
    os_map = {
        "Linux": "linux",
        "Darwin": "darwin",
        "Windows": "windows",
        "FreeBSD": "freebsd",
        "OpenBSD": "openbsd",
        "NetBSD": "netbsd",
        "DragonFly": "dragonfly",
        "SunOS": "solaris",
        "Solaris": "solaris",
        "AIX": "aix",
        "JS": "js",
        "WASI": "wasip1",
    }

    # Patterns for Cygwin/Msys/MinGW on Windows
    cygwin_msys_pattern = re.compile(r'(CYGWIN_NT|MSYS_NT|MINGW64_NT|MINGW32_NT)')

    # Map Python's machine (arch) to normalized architecture names
    # These match Go's GOARCH naming
    arch_map = {
        # 64-bit x86
        "x86_64": "amd64",
        "AMD64": "amd64",
        "x64": "amd64",

        # 32-bit x86
        "i386": "386",
        "i686": "386",
        "x86": "386",

        # ARM and ARM64 variants
        "arm64": "arm64",
        "aarch64": "arm64",
        "armv5": "arm",
        "armv6": "arm",
        "armv7": "arm",
        "armv7l": "arm",
        "armhf": "arm",
        "armel": "arm",
        "arm": "arm",

        # PowerPC
        "ppc64": "ppc64",
        "ppc64le": "ppc64le",

        # IBM S/390
        "s390x": "s390x",

        # MIPS variants
        "mips": "mips",
        "mipsle": "mipsle",
        "mips64": "mips64",
        "mips64le": "mips64le",

        # RISC-V
        "riscv64": "riscv64",

        # LoongArch
        "loongarch64": "loong64",

        # WebAssembly
        "wasm": "wasm",
        "wasm32": "wasm",
        "wasm64": "wasm",
    }

    os_name = platform.system()
    machine = platform.machine()

    # Normalize OS
    if cygwin_msys_pattern.search(os_name):
        normalized_os = "windows"
    else:
        normalized_os = os_map.get(os_name, os_name.lower())

    # Normalize Arch
    normalized_arch = arch_map.get(machine, machine.lower())

    return normalized_os, normalized_arch

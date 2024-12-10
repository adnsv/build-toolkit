# Operating System and Architecture Normalization

This document describes the normalized values used for operating systems and CPU architectures in the build system. The normalization is designed to be compatible with Go's GOOS/GOARCH values while supporting additional common variations.

## Operating Systems

The build system uses the following normalized OS values:

| Normalized Value | Description | Common Variations |
|-----------------|-------------|-------------------|
| `windows` | Microsoft Windows | `win32`, `win64`, `win` |
| `linux` | Linux-based systems | `gnu/linux` |
| `darwin` | macOS | `macos`, `osx` |
| `ios` | iOS | - |
| `android` | Android | - |
| `freebsd` | FreeBSD | - |
| `netbsd` | NetBSD | - |
| `openbsd` | OpenBSD | - |
| `dragonfly` | DragonFly BSD | - |
| `solaris` | Oracle Solaris | `sunos` |
| `illumos` | illumos | - |
| `aix` | IBM AIX | - |
| `plan9` | Plan 9 | - |
| `js` | JavaScript runtime | `node`, `browser` |
| `wasip1` | WASI Preview 1 | `wasi` |

## CPU Architectures

The build system uses the following normalized architecture values:

| Normalized Value | Description | Common Variations |
|-----------------|-------------|-------------------|
| `386` | 32-bit x86 | `i386`, `i686`, `x86` |
| `amd64` | 64-bit x86 | `x86_64`, `x64` |
| `arm` | 32-bit ARM | `armv7`, `armv7l` |
| `arm64` | 64-bit ARM | `aarch64`, `armv8` |
| `ppc64` | 64-bit PowerPC | - |
| `ppc64le` | Little-endian 64-bit PowerPC | - |
| `mips` | MIPS | - |
| `mipsle` | Little-endian MIPS | - |
| `mips64` | MIPS64 | - |
| `mips64le` | Little-endian MIPS64 | - |
| `s390x` | IBM System z | - |
| `riscv64` | 64-bit RISC-V | - |
| `loong64` | LoongArch 64-bit | - |
| `wasm` | WebAssembly | `wasm32`, `wasm64` |

## Special Platform Combinations

Some platforms have specific OS/architecture combinations:

- `js/wasm`: JavaScript environment (browser or Node.js) with WebAssembly
- `wasip1/wasm`: WASI Preview 1 with WebAssembly

## Usage

The normalized values are used for target configuration:

- Target configuration functions (`get_targets(os, arch, compiler_id, options)`)
- Toolchain definitions
- Platform-specific build settings


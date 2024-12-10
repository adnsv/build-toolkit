# Toolchain Configuration

The Toolchain class configures compiler paths, flags, and output file naming for a specific platform.

## Constructor

```python
Toolchain(
    os: str,                  # Target operating system
    arch: str,                # Target architecture
    cc: str,                  # C compiler path/command
    cxx: str,                 # C++ compiler path/command
    ar: str,                  # Archiver path/command
    cflags: List[str] = [],   # C compiler flags
    cxxflags: List[str] = [], # C++ compiler flags
    arflags: List[str] = [],  # Archiver flags
    lib_prefix: str = "",     # Prefix for library names
    lib_extension: str = ".a" # Extension for library files
)
```

## Fields

### Platform Identification
- `os`: Target operating system (e.g. "windows", "linux", "darwin")
- `arch`: Target architecture (e.g. "amd64", "arm64", "386")
- `compiler_id`: Compiler identifier, derived from cc/cxx (e.g. "gcc", "msvc", "clang")

### Compiler Commands
- `cc`: C compiler command (e.g. "gcc", "clang")
- `cxx`: C++ compiler command (e.g. "g++", "clang++")
- `ar`: Archiver command (e.g. "ar", "lib.exe")

### Compiler Flags
- `cflags`: List of flags for C compilation
- `cxxflags`: List of flags for C++ compilation
- `arflags`: List of flags for archive creation

### Library Naming
- `lib_prefix`: Prefix added to library names (e.g. "lib" on Unix systems, "" on Windows)
- `lib_extension`: File extension for library files (e.g. ".a" for static libraries, ".so" for shared libraries)

## Example Usage

Basic GCC toolchain:
```python
toolchain = Toolchain(
    os="linux",
    arch="amd64",
    cc="gcc",
    cxx="g++",
    ar="ar",
    cflags=[
        "-c",           # Compile only
        "-Wall",        # Enable warnings
        "-O2"           # Optimize
    ],
    cxxflags=[
        "-c",
        "-Wall",
        "-std=c++17",   # C++ standard
        "-O2"
    ],
    arflags=["rcs"]     # Create archive with symbol table
)
```

## Using with Builder

The toolchain is passed to Builder to configure compilation:

```python
builder = Builder(
    toolchain=toolchain,
    gen_dir="build/gen",
    obj_dir="build/obj",
    lib_dir="build/lib",
    tmp_dir="build/tmp"
)
```

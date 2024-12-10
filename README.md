# Build Toolkit

A Python-based build system for C/C++ libraries that provides:
- Cross-platform compilation
- Feature detection
- File generation
- Dependency management
- Build reporting

## Overview

Build Toolkit provides a simple way to build C++ static libraries through Python:
- Clean Python API with type hints
- Straightforward configuration of compiler toolchains
- Parallel compilation of source files
- HTML build report for easy navigation through results

> **Note:** This project is currently in early alpha stage and the API may change significantly between versions.


## Features

### Feature Detection
Run compile-time tests to detect compiler capabilities that can be used for file
generation:
- Header availability
- Type definitions
- Function declarations
- Struct members
- Compiler flags

### File Generation
Generate header files from templates with:
- CMake-style configuration
- Feature test results
- Custom definitions

### Dependency Management
- Public/private include paths
- Public/private definitions
- Target dependencies

### Build Reports
Generate HTML reports showing:
- Build configuration
- Feature test results
- Compilation statistics
- Error messages
- Timing information

## Documentation

- [Toolchain](docs/toolchain.md) - Compiler toolchain configuration
- [Builder](docs/builder.md) - Build workflow
- [Target Configuration](docs/target.md) - How to configure library targets
- [OS/Architecture](docs/os_arch.md) - Platform detection


## Basic Usage

```python
from build_toolkit import Toolchain, Builder, make_dashboard

# Configure toolchain
toolchain = Toolchain(
    os="linux",
    arch="amd64",
    cc="gcc",
    cxx="g++",
    ar="ar"
)

# Create builder
builder = Builder(
    toolchain=toolchain,
    gen_dir="build/gen",
    obj_dir="build/obj",
    lib_dir="build/lib",
    tmp_dir="build/tmp"
)

# Load and build targets
builder.load_targets(script_path="build_config.py")
builder.build_all()

# Generate build report
make_dashboard(builder, "build-report.html")
```

## Requirements
- Python 3.7+
- C/C++ compiler (gcc, clang, or msvc)
- ar or equivalent archiver

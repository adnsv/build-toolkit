# Build Configuration

The build toolkit uses a Python-based configuration system that allows flexible
and programmatic definition of build targets. The configuration is defined in a
`build_config.py` file, which should be placed in the library's root directory.

## Configuration File Structure

A `build_config.py` file must export the following function:

```python
def get_targets(os: str, arch: str, compiler_id: str, options: dict) -> Union[dict, list[dict]]:
    """Get build configurations for all targets.

    Args:
        os: Target operating system (e.g. "windows", "linux", "darwin")
        arch: Target architecture (e.g. "amd64", "arm64", "386")
        compiler_id: Compiler identifier (e.g. "gcc", "msvc", "clang")
        options: Build configuration options

    Returns:
        Single target configuration or list of target configurations
    """
```

The function can return either:
- A single target configuration dictionary
- A list of target configurations
- None if no targets should be built for this platform

## Target Configuration

Each target configuration is a dictionary with the following fields:

```python
{
    # Required fields
    "name": str,           # Target name, must be unique
    "sources": list[str],  # Source files relative to root

    # Optional fields
    "root": str,           # Root directory for sources and includes
                           # Default: directory containing build_config.py
    
    "output": str,         # Output library name
                           # Defaults to target name
                           # Note: Builder's output_archive overrides this
    
    "include_dirs": list[str],     # Public include directories
                                   # Passed to this target and dependents
    
    "private_include_dirs": list[str], # Private include directories
                                       # Only used by this target
    
    "dependencies": list[str],     # Library dependencies
                                   # Names of other targets this depends on
    
    "definitions": list[str],      # Public preprocessor definitions
                                   # Passed to this target and dependents
    
    "private_definitions": list[str], # Private preprocessor definitions
                                      # Only used by this target
    
    "feature_tests": list[dict],    # Feature tests to run
                                    # Results available in generated files
    
    "generated_files": list[dict]   # Files to generate from templates
}
```

## Multiple Targets Example

Here's an example configuration with multiple targets:

```python
def get_targets(os: str, arch: str, compiler_id: str, options: dict) -> list[dict]:
    # Core library target
    core = {
        "name": "core",
        "sources": [
            "src/core/thread.cpp",
            "src/core/mutex.cpp",
            "src/core/queue.cpp"
        ],
        "include_dirs": ["include"],
        "definitions": ["CORE_EXPORTS"]
    }
    
    # Network module target depending on core
    network = {
        "name": "network",
        "sources": [
            "src/network/socket.cpp",
            "src/network/address.cpp",
            "src/network/server.cpp"
        ],
        "include_dirs": ["include"],
        "dependencies": ["core"],
        "definitions": ["NETWORK_EXPORTS"]
    }
    
    # Optional SSL module
    if options.get("USE_SSL"):
        ssl = {
            "name": "ssl",
            "sources": [
                "src/ssl/context.cpp",
                "src/ssl/certificate.cpp"
            ],
            "dependencies": ["network"]
        }
        return [core, network, ssl]
    
    return [core, network]
```

This example shows:
- Multiple targets with dependencies
- Conditional target inclusion based on options
- Feature tests for optional components
- Public includes and definitions

## Example Configuration

Here's an example configuration for a library with platform-specific networking code:

```python
def get_targets(os: str, arch: str, compiler_id: str, options: dict) -> dict:
    sources = ["src/common/socket.cpp"]
    include_dirs = ["include"]
    definitions = []
    feature_tests = []

    if os == "windows":
        sources += ["src/windows/winsock.cpp"]
        definitions += ["USE_WINSOCK"]
        feature_tests.append({
            "type": "header",
            "variable": "HAVE_WINSOCK2_H",
            "headers": ["winsock2.h"],
            "language": "c++"
        })
    else:
        sources += ["src/posix/bsd_socket.cpp"]
        definitions += ["USE_BSD_SOCKET"]
        feature_tests.append({
            "type": "header", 
            "variable": "HAVE_SYS_SOCKET_H",
            "headers": ["sys/socket.h"],
            "language": "c"
        })

    return {
        "name": "network",
        "sources": sources,
        "include_dirs": include_dirs,
        "definitions": definitions,
        "feature_tests": feature_tests,
        "generated_files": [{
            "output": "socket_config.h",
            "template": "socket_config.h.in",
            "type": "cmake_configure",
            "definitions": {
                "VERSION": "1.0.0"
                # Feature test results HAVE_WINSOCK2_H or HAVE_SYS_SOCKET_H
                # will be added automatically
            }
        }]
    }
```

Template file (`socket_config.h.in`):
```cmake
#ifndef SOCKET_CONFIG_H
#define SOCKET_CONFIG_H

/* Windows socket API */
#cmakedefine HAVE_WINSOCK2_H 1

/* POSIX socket API */
#cmakedefine HAVE_SYS_SOCKET_H 1

#if defined(HAVE_WINSOCK2_H)
#  include <winsock2.h>
#elif defined(HAVE_SYS_SOCKET_H)
#  include <sys/socket.h>
#else
#  error "No supported socket API found"
#endif

#endif /* SOCKET_CONFIG_H */
```

## Feature Tests

The `feature_tests` field allows specifying compile-time feature detection tests. 
Feature test results are only available for use in generated files through the 
`#cmakedefine` directive. Each feature test's result is automatically added to 
the definitions passed to all generated files in the same target.

### Types of Feature Tests

#### Compiler Flag Test
Tests if a compiler flag is supported.

```python
{
    "type": "compiler_flag",
    "variable": "HAVE_FLAG_WERROR",  # Name for the test result
    "language": "c++",               # "c" or "c++"
    "flag": "-Werror"               # Flag to test
}
```

The test compiles an empty source file with the specified flag. If compilation
succeeds, the flag is supported.

#### Header Test
Tests if one or more headers are available.

```python
{
    "type": "header",
    "variable": "HAVE_PTHREAD_H",
    "language": "c",                # "c" or "c++"
    "headers": ["pthread.h"]        # List of headers to include
}
```

The test attempts to include all specified headers. All headers must be found
for the test to pass.

#### Type Test
Tests if a specific type is defined.

```python
{
    "type": "type",
    "variable": "HAVE_SIZE_T",
    "language": "c",                # "c" or "c++"
    "headers": ["stddef.h"],        # Headers that might define the type
    "type_name": "size_t"          # Type name to check for
}
```

The test checks if the specified type name is defined after including the given
headers.

#### Function Test
Tests if a function exists.

```python
{
    "type": "function",
    "variable": "HAVE_MALLOC",
    "language": "c",                # "c" or "c++"
    "headers": ["stdlib.h"],        # Headers that declare the function
    "function": "malloc"           # Function name to check for
}
```

The test verifies that the function is declared and can be referenced after
including the specified headers.

#### Struct Member Test
Tests if a struct has a specific member.

```python
{
    "type": "struct_member",
    "variable": "HAVE_STAT_ST_MTIM",
    "language": "c",                # "c" or "c++"
    "headers": ["sys/stat.h"],      # Headers that define the struct
    "struct_name": "struct stat",   # Struct to check
    "member": "st_mtim"            # Member name to check for
}
```

The test checks if the specified struct contains the named member field.

### Using Test Results

Test results are automatically added to the definitions of all generated files in the same target. For example:

```cmake
#cmakedefine HAVE_PTHREAD_H 1
```

This will be replaced with either:
```c
#define HAVE_PTHREAD_H 1      /* If test passed */
/* #undef HAVE_PTHREAD_H */   /* If test failed */
```

### Test Deduplication

If multiple targets request the same feature test (same type and parameters),
the test will only be run once. The result will be shared among all requesting
targets.

## Build Options

The `target_options` dictionary in the Builder constructor allows passing
configuration options to all targets. These options are passed directly to the
`get_targets()` function as its `options` parameter when loading targets.

For example:
```python
# Configure builder with options
builder = Builder(
    toolchain=toolchain_config,
    target_options={"USE_STATIC_RUNTIME": True},
    output_archive="mylib"
)

# Load targets - the options are passed to get_targets
builder.load_targets(script_path=script_path)
```

In the build configuration file:
```python
def get_targets(os: str, arch: str, compiler_id: str, options: dict) -> dict:
    # Access builder's target_options through the options parameter
    use_static = options.get("USE_STATIC_RUNTIME", False)
    
    definitions = []
    if use_static:
        definitions.append("STATIC_RUNTIME")
    
    return {
        "name": "mylib",
        "sources": ["src/lib.cpp"],
        "definitions": definitions
    }
``` 
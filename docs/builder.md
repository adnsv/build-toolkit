# Builder

The Builder class manages the complete build process for C/C++ libraries. It
handles dependency resolution, feature detection, file generation, compilation,
and archive creation.

## Constructor

```python
Builder(
    toolchain: Toolchain,          # Compiler toolchain configuration
    gen_dir: str,                  # Directory for generated files
    obj_dir: str,                  # Directory for object files
    lib_dir: str,                  # Directory for output libraries
    tmp_dir: str,                  # Directory for temporary files
    compile_commands_path: Optional[str] = None,  # Path for compile_commands.json
    output_archive: Optional[str] = None,         # Override all target outputs
    target_options: Optional[dict] = None         # Options passed to get_targets
)
```

### Parameters

- `toolchain`: Toolchain configuration with compiler paths and flags
- `gen_dir`: Directory where generated files will be placed
- `obj_dir`: Directory for compiled object files
- `lib_dir`: Directory for output static libraries
- `tmp_dir`: Directory for temporary files (feature tests, etc)
- `compile_commands_path`: Optional path to write compile_commands.json
- `output_archive`: Optional name to override all target output names
- `target_options`: Optional dictionary passed to get_targets functions

## Methods

### load_targets

```python
def load_targets(self, *, script_path: str) -> None
```

Loads target configurations from a build script. The script must define a
`get_targets` function that returns target configurations.

### build_all

```python
def build_all(self) -> None
```

Executes the complete build process:
1. Resolves dependencies
2. Sets up tasks
3. Runs feature tests
4. Generates files
5. Compiles sources
6. Creates archives

### get_unresolved_dependencies

```python
def get_unresolved_dependencies(self) -> List[str]
```

Returns list of dependencies that are referenced but don't exist in known tasks.

## Fields

### compile_tasks

```python
compile_tasks: List[CompileTask]
```

List of all compilation tasks. Each task represents one target and tracks:
- Source files to compile
- Include directories
- Preprocessor definitions
- Dependencies on other tasks
- Generated files
- Compilation results

### archive_tasks

```python
archive_tasks: List[ArchiveTask]
```

List of archive creation tasks. Each task:
- Has an output library path
- Groups object files from compile tasks
- Tracks archive command and result

### feature_tests

```python
feature_tests: Set[FeatureTestTask]
```

Set of unique feature tests from all targets. Tests are deduplicated based on
type and parameters.

## Example Usage

```python
# Create builder
builder = Builder(
    toolchain=toolchain_config,
    gen_dir="build/gen",
    obj_dir="build/obj",
    lib_dir="build/lib",
    tmp_dir="build/tmp",
    compile_commands_path="compile_commands.json"
)

# Load main targets
builder.load_targets(script_path="build_config.py")

# Check for missing dependencies
missing = builder.get_unresolved_dependencies()
if "libusb" in missing:
    # Load additional targets
    builder.load_targets(script_path="ext/libusb/build_config.py")

# Build everything
builder.build_all()
```

## Directory Structure

The builder creates and manages the following directory structure:

```
{gen_dir}/           # Generated files
└── target_name/     # One directory per target
    └── file.h       # Generated header files

{obj_dir}/           # Object files
└── target_name/     # One directory per target
    └── src/         # Mirrors source directory structure
        └── file.o   # Compiled object files

{lib_dir}/           # Output libraries
└── libtarget.a     # Static libraries

{tmp_dir}/           # Temporary files
└── feature_tests/   # Feature test files
```

## Error Handling

The build process will stop with an error if:
- A target depends on a non-existent target
- A feature test fails to compile
- A file generation step fails
- A source file fails to compile
- An archive creation fails

Error messages include:
- Command output (stdout/stderr)
- File paths
- Timing information
- Error descriptions 

## Build Dashboard

The build dashboard provides a visual overview of the build process and results, helping to diagnose issues and track performance. It displays compilation statistics, error messages, timing information, and feature test results in an organized HTML report that can be generated using the `make_dashboard` function.

```python
from build_toolkit import make_dashboard

make_dashboard(builder, "build-report.html")
```


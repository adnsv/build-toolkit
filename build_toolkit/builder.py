"""Core build system implementation.
Handles C++ compilation and static library creation with parallel builds.
"""

import os
import subprocess
import time
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable, Set
import importlib.util
import shlex  # Add this import at the top with other imports

from .target import Target, GeneratedFile
from .toolchain import Toolchain
from .utils import ensure_dir, normalize_path
from .feature import FeatureTestTask

@dataclass
class CommandResult:
    """Result of executing a command.
    Contains stdout/stderr, timing, and status information."""
    succeeded: bool = False
    error: Optional[str] = None
    duration: float = 0.0
    stdout: str = ""
    stderr: str = ""

@dataclass
class CompileCommand:
    """Represents a single source file compilation.
    Created by Builder for each source file in Target.
    Contains normalized paths and full command."""
    directory: str      # Directory to run command in
    command: List[str]  # Full compilation command as list of strings
    source_file: str    # Source file path
    output_file: str    # Output object file path
    result: Optional[CommandResult] = None

    def to_json_dict(self) -> dict:
        """Convert to compile_commands.json format."""
        return {
            "directory": self.directory,
            "command": shlex.join(self.command),  # Use shlex.join for proper escaping
            "file": self.source_file
        }

def _generate_cmake_config(step: 'GeneratedStep') -> None:
    """Generate a file using CMake-style configuration."""
    from .cmake_configure import cmake_configure_file
    cmake_configure_file(
        template_path=step.template,
        output_path=step.output,
        definitions=step.definitions or {}
    )

def _generate_copy(step: 'GeneratedStep') -> None:
    """Simply copy the template to output."""
    with open(step.template, 'r') as f:
        template_content = f.read()
    with open(step.output, 'w') as f:
        f.write(template_content)

# Map of generator types to their implementation functions
GENERATORS: Dict[str, Callable[['GeneratedStep'], None]] = {
    'cmake_configure': _generate_cmake_config,
    'copy': _generate_copy,
}

@dataclass
class GeneratedStep:
    """Represents a single file generation step.
    Contains both configuration and results of the generation process."""
    
    # Configuration
    template: str      # Template file path
    output: str       # Output file path
    type: str         # Generator type (e.g. "cmake_configure")
    definitions: Dict[str, Any]  # Template variable definitions
    
    # Generator function
    generator: Callable[['GeneratedStep'], None] = field(init=False)
    
    # Results
    succeeded: bool = False
    error: Optional[str] = None
    duration: float = 0.0
    
    def __post_init__(self):
        """Validate and set up the generator function."""
        if self.type not in GENERATORS:
            raise ValueError(f"Unknown generator type: {self.type}")
        self.generator = GENERATORS[self.type]

    def generate(self) -> None:
        """Execute the generation step."""
        try:
            start_time = time.time()
            
            # Create output directory
            os.makedirs(os.path.dirname(self.output), exist_ok=True)
            
            # Run the generator
            self.generator(self)
            
            # Record success
            self.duration = time.time() - start_time
            self.succeeded = True
            
        except Exception as e:
            # Record failure
            self.duration = time.time() - start_time
            self.succeeded = False
            self.error = str(e)
            raise

@dataclass
class CompileTask:
    """Holds all information needed for compiling a target.
    This includes both configuration and results of the compilation process."""
    
    # Initial configuration
    target: Target
    
    # These are populated during setup phase
    obj_dir: str = ""  # Directory for object files
    lib_path: str = ""  # Path to output library
    public_include_dirs: List[str] = field(default_factory=list)  # Include dirs from this target and dependencies
    private_include_dirs: List[str] = field(default_factory=list) # Include dirs only for this target
    public_definitions: List[str] = field(default_factory=list)   # Definitions from this target and dependencies
    private_definitions: List[str] = field(default_factory=list)  # Definitions only for this target
    commands: List[CompileCommand] = field(default_factory=list)  # List of commands to compile this target
    obj_files: List[str] = field(default_factory=list)           # List of output object files
    dependencies: List['CompileTask'] = field(default_factory=list)  # List of dependent tasks
    generated_steps: List[GeneratedStep] = field(default_factory=list)  # List of file generation steps
    
    # This is populated after compilation phase
    succeeded: bool = False

@dataclass
class ArchiveTask:
    """Represents a single archive creation task.
    Created by Builder for each output library.
    Contains all information needed to create and track the archive."""
    
    output_file: str  # Path to output library file
    command: List[str]  # Full archive command as list
    compile_tasks: List[CompileTask]  # Tasks that contribute to this archive
    result: Optional[CommandResult] = None

class Builder:
    """Manages the build process for a collection of targets.
    
    The build process consists of several phases:
    1. Add targets - creates compile tasks for each target
    2. Setup phase:
        - Resolve dependencies between targets
        - Set up include paths and definitions
        - Create compile commands
        - Group targets by output library and create archive tasks
    3. Compile phase - compile all source files in parallel
    4. Archive phase - create static libraries from object files
    """
    
    def __init__(self, toolchain: Toolchain, gen_dir: str, obj_dir: str, lib_dir: str, 
                 tmp_dir: str, compile_commands_path: Optional[str] = None,
                 output_archive: Optional[str] = None,
                 target_options: Optional[dict] = None):
        """Initialize builder with toolchain and output directories.
        
        Args:
            toolchain: Toolchain configuration
            gen_dir: Directory for generated files
            obj_dir: Directory for object files
            lib_dir: Directory for library files
            tmp_dir: Directory for temporary files
            compile_commands_path: Optional path to write compile_commands.json
            output_archive: Optional name for a single output archive that overrides target archives
            target_options: Optional dictionary of options used when loading all targets
        """
        self.toolchain = toolchain
        self.gen_dir = gen_dir
        self.obj_dir = obj_dir
        self.lib_dir = lib_dir
        self.tmp_dir = tmp_dir
        self.compile_commands_path = compile_commands_path
        self.output_archive = output_archive
        self.target_options = target_options or {}
        self.compile_tasks: List[CompileTask] = []
        self.archive_tasks: List[ArchiveTask] = []
        self._tasks: Dict[str, CompileTask] = {}  # Maps target names to compile tasks
        self.total_compile_time: float = 0.0  # Total wall-clock time for parallel compilation
        self.feature_tests: Set[FeatureTestTask] = set()  # Unique feature tests

    def add_target(self, target: Target) -> None:
        """Add a target to be built.
        
        Creates a compile task for the target and determines its output library path.
        Archive tasks are created later during the setup phase.
        
        Args:
            target: Target configuration
        """
        task = CompileTask(target=target)
        
        # Get library name from target output or name
        lib_name = target.output if target.output else target.name
        
        # Add extension and prefix from toolchain
        lib_name = f"{self.toolchain.lib_prefix}{lib_name}{self.toolchain.lib_extension}"
        
        # Set library path
        task.lib_path = os.path.join(self.lib_dir, lib_name)
        
        # Add to compile tasks list
        self.compile_tasks.append(task)
        
        # Store task by name for dependency lookup
        self._tasks[target.name] = task

    def load_targets(
        self,
        *,
        script_path: str,
    ) -> None:
        """Load target configurations from a build script.

        Loads the specified build script and calls get_targets()
        which should return a list of target configurations.
        
        Args:
            script_path: Path to build script (e.g. "build_config.py")
            
        Raises:
            ImportError: If script exists but cannot be imported
            AttributeError: If script doesn't define get_targets
        """
        # Check if script exists
        if not os.path.exists(script_path):
            return
        
        # Import the build script module
        script_dir = os.path.dirname(os.path.abspath(script_path))
        spec = importlib.util.spec_from_file_location("build_config", script_path)
        if not spec or not spec.loader:
            raise ImportError(f"Could not load build script: {script_path}")
        
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Get target configurations
        if not hasattr(module, 'get_targets'):
            raise AttributeError(f"Build script missing get_targets(): {script_path}")
        
        result = module.get_targets(self.toolchain.os, self.toolchain.arch, self.toolchain.compiler_id, self.target_options)
        if result is None:
            return
            
        configs = result if isinstance(result, list) else [result]
            
        # Add each target
        for config in configs:
            # Make root path absolute by joining with script directory
            if "root" in config:
                config["root"] = os.path.normpath(os.path.join(script_dir, config["root"]))
                
            # If output archive is specified, use it for all targets
            if self.output_archive:
                config["output"] = self.output_archive
            
            # Extract feature tests before creating target
            feature_tests = config.pop("feature_tests", [])
            target = Target.from_dict(data=config)
            
            # Process feature tests
            for test_dict in feature_tests:
                test = FeatureTestTask(**test_dict)
                # Try to find existing identical test
                existing_test = next((t for t in self.feature_tests if t == test), None)
                if existing_test:
                    # Add this target to existing test's requesters
                    existing_test.requesting_targets.add(target.name)
                else:
                    # Add new test with this target as first requester
                    test.requesting_targets.add(target.name)
                    self.feature_tests.add(test)
            
            self.add_target(target)

    def build_all(self):
        """Build all targets."""
        print("Preparing tasks...")
        self._resolve_dependencies()
        self._setup_all_tasks()
        
        # Write compile_commands.json if path is specified
        if self.compile_commands_path:
            self._write_compile_commands()
            
        self._execute_feature_tests()
        self._generate_files()
        self._execute_compile_tasks()
        self._execute_archive_tasks()

    def _resolve_dependencies(self):
        """Resolve dependencies between tasks.
        
        This builds a dependency graph and ensures all dependencies are satisfied,
        regardless of the order in which tasks were added.
        """
        # First pass: collect all available target names
        available_targets = {task.target.name for task in self.compile_tasks}
        
        # Second pass: validate all dependencies exist
        for task in self.compile_tasks:
            for dep_name in task.target.dependencies:
                if dep_name not in available_targets:
                    raise ValueError(f"Target {task.target.name} depends on {dep_name} which does not exist")
        
        # Third pass: resolve dependencies for each task
        for task in self.compile_tasks:
            task.dependencies = []
            for dep_name in task.target.dependencies:
                dep_task = next(t for t in self.compile_tasks if t.target.name == dep_name)
                task.dependencies.append(dep_task)

    def _setup_all_tasks(self) -> None:
        """Set up all tasks with their paths, include directories, definitions, and compile commands.
        
        First sets up all compile tasks with their includes, definitions, and commands.
        Then groups compile tasks by output library and creates archive tasks.
        """
        # First set up includes, definitions and commands
        for task in self.compile_tasks:
            print(f"- {task.target.name} target")
            
            # Set up generated files
            for gen_file in task.target.generated_files:
                expanded_template = self._expand_target_path_vars(gen_file.template, task.target)
                expanded_output = self._expand_target_path_vars(gen_file.output, task.target)
                task.generated_steps.append(GeneratedStep(
                    template=normalize_path(os.path.join(task.target.root, expanded_template)),
                    output=normalize_path(os.path.join(self.gen_dir, task.target.name, expanded_output)),
                    type=gen_file.type,
                    definitions=gen_file.definitions
                ))
            # Set up includes and definitions
            self._setup_task_includes_and_definitions(task)
            
            # Create compile commands
            self._create_commands(task)
            
            # Print summary
            print(f"  {len(task.commands)} files to compile")
            
        # Then set up archive tasks
        print("\nSetting up archive tasks...")
        self._setup_archive_tasks()

    def _setup_task_includes_and_definitions(self, task: CompileTask, visited: Optional[set] = None):
        """Set up include directories and definitions for a task.
        Resolves all includes and definitions, including those from dependencies.
        
        Args:
            task: The task to set up
            visited: Set of already visited targets to prevent cycles (internal use)
        """
        if visited is None:
            visited = set()
            
        # Prevent cycles in dependency graph
        if task.target.name in visited:
            return
        visited.add(task.target.name)
        
        # Add target's own includes
        for inc in task.target.include_dirs:
            expanded_inc = self._expand_target_path_vars(inc, task.target)
            if os.path.isabs(expanded_inc):
                include_path = expanded_inc
            else:
                include_path = os.path.join(task.target.root, expanded_inc)
            # Make absolute and normalize
            include_path = normalize_path(os.path.abspath(include_path))
            task.public_include_dirs.append(include_path)
        
        for inc in task.target.private_include_dirs:
            expanded_inc = self._expand_target_path_vars(inc, task.target)
            if os.path.isabs(expanded_inc):
                include_path = expanded_inc
            else:
                include_path = os.path.join(task.target.root, expanded_inc)
            # Make absolute and normalize
            include_path = normalize_path(os.path.abspath(include_path))
            task.private_include_dirs.append(include_path)
        
        # Add target's own definitions
        task.public_definitions.extend(task.target.definitions)
        task.private_definitions.extend(task.target.private_definitions)
        
        # Process dependencies after own includes/definitions
        for dep_name in task.target.dependencies:
            dep_task = next((t for t in self.compile_tasks if t.target.name == dep_name), None)
            if dep_task:
                # Recursively set up dependency if not already done
                self._setup_task_includes_and_definitions(dep_task, visited)
                # Collect public includes and definitions from dependency
                task.public_include_dirs.extend(dep_task.public_include_dirs)
                task.public_definitions.extend(dep_task.public_definitions)
        
        # Remove duplicates while preserving order
        task.public_include_dirs = list(dict.fromkeys(task.public_include_dirs))
        task.private_include_dirs = list(dict.fromkeys(task.private_include_dirs))
        task.public_definitions = list(dict.fromkeys(task.public_definitions))
        task.private_definitions = list(dict.fromkeys(task.private_definitions))

    def _create_commands(self, task: CompileTask):
        """Create compilation commands for a task.
        Must be called after setting up includes and definitions.
        
        Args:
            task: The task to create compile commands for
        """
        task.commands.clear()
        task.obj_files.clear()
        
        for source in task.target.sources:
            # Convert source path to absolute and normalize
            if os.path.isabs(source):
                src_path = source
            else:
                src_path = os.path.join(task.target.root, source)
            src_path = normalize_path(os.path.abspath(src_path))
            
            # Form object file path within obj_dir
            rel_path = os.path.relpath(src_path, task.target.root)
            target_obj_dir = os.path.join(self.obj_dir, task.target.name)
            obj_path = os.path.join(target_obj_dir, os.path.splitext(rel_path)[0] + ".o")
            # Normalize obj path
            obj_path = normalize_path(obj_path)
            
            # Choose compiler and flags based on file extension
            is_cpp = os.path.splitext(source)[1].lower() in ['.cpp', '.cxx', '.cc']
            compiler = self.toolchain.cxx if is_cpp else self.toolchain.cc
            flags = self.toolchain.cxxflags if is_cpp else self.toolchain.cflags
            
            # Use all include directories (both public and private)
            include_flags = [f"-I{dir}" for dir in task.public_include_dirs + task.private_include_dirs]
            
            # Use all definitions (both public and private)
            define_flags = [f"-D{define}" for define in task.public_definitions + task.private_definitions]
            
            # Build command as list
            cmd = compiler + flags + include_flags + define_flags + [
                "-o", obj_path, src_path
            ]
            
            task.commands.append(CompileCommand(
                directory=os.path.dirname(obj_path),
                command=cmd,  # Store as list
                source_file=src_path,
                output_file=obj_path
            ))
            task.obj_files.append(obj_path)

    def _setup_archive_tasks(self) -> None:
        """Set up archive tasks for all targets.
        
        Groups compile tasks by their output library path and creates archive tasks.
        Multiple compile tasks can contribute to a single archive if they share
        the same output library path. When Builder's output_archive is specified, 
        it will be used as the output file for all archive tasks, regardless of their
        names or the custom output name specified in the target.
        
        Must be called after all compile tasks are set up with their object files.
        """
        # Clear existing archive tasks
        self.archive_tasks.clear()
        
        # Group compile tasks by library path
        lib_tasks: Dict[str, List[CompileTask]] = {}
        for task in self.compile_tasks:
            if task.lib_path not in lib_tasks:
                lib_tasks[task.lib_path] = []
            lib_tasks[task.lib_path].append(task)
            
        # Create archive tasks
        for lib_path, compile_tasks in lib_tasks.items():
            # Normalize library path
            lib_path = normalize_path(lib_path)
            
            # Collect all object files
            obj_files = []
            for task in compile_tasks:
                obj_files.extend(task.obj_files)
                
            # Create archive command as list
            command = self.toolchain.ar + self.toolchain.arflags + [lib_path] + obj_files
            
            # Create archive task
            archive = ArchiveTask(
                output_file=lib_path,
                command=command,
                compile_tasks=compile_tasks
            )
            self.archive_tasks.append(archive)
            print(f"- {os.path.basename(lib_path)} ({len(compile_tasks)} targets)")

    def _execute_compile_tasks(self):
        """Execute all compile tasks in parallel and return True if all succeeded, False otherwise."""
        # Gather all commands from compile tasks
        all_commands = []
        for task in self.compile_tasks:
            all_commands.extend(task.commands)
        
        # If there are no commands, nothing to do
        if not all_commands:
            return True  # No failures if there is nothing to compile
        
        # Calculate formatting widths for printing
        total_commands = len(all_commands)
        counter_width = len(str(total_commands))
        max_filename_len = max(len(os.path.basename(cmd.source_file)) for cmd in all_commands)
        filename_width = min(max(max_filename_len + 2, 25), 40)

        print(f"\nCompiling {total_commands} files...")

        n_failed = 0
        start_time = time.time()

        # Map each future to its corresponding command for efficient lookup
        future_to_cmd = {}
        # You can specify max_workers if needed, e.g., ThreadPoolExecutor(max_workers=8)
        with ThreadPoolExecutor() as executor:
            for cmd in all_commands:
                future = executor.submit(self._execute_command, cmd)
                future_to_cmd[future] = cmd

            completed = 0
            for future in as_completed(future_to_cmd):
                completed += 1
                cmd = future_to_cmd[future]

                try:
                    result = future.result()
                    cmd.result = result

                    # Print status if we have a result
                    if result is not None:
                        status = "succeeded" if result.succeeded else "failed"
                        filename = os.path.basename(cmd.source_file)
                        print(f"[{completed:{counter_width}d}/{total_commands}]  "
                            f"{filename:<{filename_width}} ... {status} ({result.duration:.1f}s)")

                    if not result.succeeded:
                        n_failed += 1

                except Exception as e:
                    # If there's an exception, mark this command as failed and log the error
                    print(f"Error executing {cmd.source_file}: {e}")
                    cmd.result = CommandResult(succeeded=False, error=str(e))
                    n_failed += 1

        self.total_compile_time = time.time() - start_time

        # Update each task's success state
        for task in self.compile_tasks:
            task.succeeded = all(cmd.result and cmd.result.succeeded for cmd in task.commands)

        # Return True if no failures occurred, else False
        return n_failed == 0


    def _execute_command(self, cmd: CompileCommand) -> CommandResult:
        """Run single compilation command and collect output"""
        result = CommandResult()
        ensure_dir(cmd.directory)
        
        try:
            start_time = time.time()
            process = subprocess.run(
                cmd.command,  # Pass command list directly
                shell=False,  # Set shell=False when using command list
                cwd=cmd.directory,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            result.duration = time.time() - start_time
            result.stdout = process.stdout.decode('utf-8')
            result.stderr = process.stderr.decode('utf-8')
            
            if process.returncode == 0:
                result.succeeded = True
            else:
                result.succeeded = False
                result.error = f"Command failed with return code {process.returncode}"
                
        except Exception as e:
            result.succeeded = False
            result.error = str(e)
            
        cmd.result = result
        return result

    def _execute_archive_tasks(self):
        """Archive all object files into static libraries."""
        if not self.archive_tasks:
            return
            
        # Calculate padding widths
        total_archives = len(self.archive_tasks)
        counter_width = len(str(total_archives))
        max_libname_len = max(len(os.path.basename(archive.output_file)) for archive in self.archive_tasks)
        libname_width = min(max(max_libname_len + 2, 25), 40)

        print(f"\nArchiving {total_archives} libraries...")
        
        n_failed = 0
            
        for i, archive in enumerate(self.archive_tasks, 1):
            lib_name = os.path.basename(archive.output_file)
            result = CommandResult()
            
            # Skip if compilation failed
            if not all(task.succeeded for task in archive.compile_tasks):
                result.succeeded = False
                result.error = f"Cannot create {lib_name} - compilation failed"
                archive.result = result
                print(f"[{i:{counter_width}d}/{total_archives}]  {lib_name:<{libname_width}} ... failed (compilation failed)")
                n_failed += 1
                continue
                
            try:
                ensure_dir(os.path.dirname(archive.output_file))
                start_time = time.time()
                process = subprocess.run(
                    archive.command,
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE
                )
                result.duration = time.time() - start_time
                result.stdout = process.stdout.decode('utf-8')
                result.stderr = process.stderr.decode('utf-8')
                result.succeeded = process.returncode == 0
                archive.result = result
                
                status = "succeeded" if result.succeeded else "failed"
                print(f"[{i:{counter_width}d}/{total_archives}]  {lib_name:<{libname_width}} ... {status} ({result.duration:.1f}s)")
                
                if not result.succeeded:
                    print(f"Error: {result.error}")
                    if result.stdout:
                        print("stdout:", result.stdout)
                    if result.stderr:
                        print("stderr:", result.stderr)
                    
            except Exception as e:
                print(f"Error creating {lib_name}: {e}")
                result.succeeded = False
                result.error = str(e)
                archive.result = result
                
            if not result.succeeded:
                n_failed += 1
        
        # Print summary
        if n_failed:
            print(f"\n{n_failed} of {total_archives} libraries failed to build")
            return False
        else:
            print("\nAll libraries built successfully")
            return True

    def _expand_target_path_vars(self, path: str, target: Target) -> str:
        """Expand variables in a path string.
        
        Args:
            path: Path string that may contain variables
            target: Target context for variable expansion
            
        Returns:
            Path with all variables expanded
        """
        # Replace ${gen} with target's generated files directory
        if "${gen}" in path:
            gen_dir = os.path.join(self.gen_dir, target.name)
            path = path.replace("${gen}", gen_dir)
        
        return path

    def _generate_files(self):
        """Generate all files from templates."""
        # Collect all generated files
        all_steps = []
        for task in self.compile_tasks:
            all_steps.extend(task.generated_steps)

        if not all_steps:
            return

        print(f"\nGenerating {len(all_steps)} files...")

        # Calculate padding widths for nice output formatting
        counter_width = len(str(len(all_steps)))
        max_filename_len = max(len(os.path.basename(f.output)) for f in all_steps)
        filename_width = min(max(max_filename_len + 2, 25), 40)

        n_failed = 0
        for i, step in enumerate(all_steps, 1):
            filename = os.path.basename(step.output)
            try:
                # Merge feature test results into definitions
                if step.type == "cmake_configure":
                    # Find all feature tests that affect this target
                    target_name = os.path.relpath(os.path.dirname(step.output), self.gen_dir)
                    for test in self.feature_tests:
                        if target_name in test.requesting_targets:
                            step.definitions[test.variable] = test.result
                
                # Execute generation
                step.generate()
                print(f"[{i:{counter_width}d}/{len(all_steps)}]  {filename:<{filename_width}} ... succeeded ({step.duration:.1f}s)")

            except Exception as e:
                print(f"[{i:{counter_width}d}/{len(all_steps)}]  {filename:<{filename_width}} ... failed")
                print(f"Error: {step.error}")
                n_failed += 1

        if n_failed:
            print(f"\n{n_failed} of {len(all_steps)} files failed to generate")
            return False
        else:
            return True

    def _write_compile_commands(self):
        """Write compile commands to compile_commands.json."""
        compile_commands = []
        for task in self.compile_tasks:
            for command in task.commands:
                compile_commands.append(command.to_json_dict())
        
        # Create directory if it doesn't exist
        if self.compile_commands_path:
            os.makedirs(os.path.dirname(self.compile_commands_path), exist_ok=True)
            # Write JSON file
            with open(self.compile_commands_path, 'w') as f:
                json.dump(compile_commands, f, indent=2)

    def _execute_feature_tests(self):
        """Execute all feature tests in the scratch directory."""
        if not self.feature_tests:
            return

        print(f"\nRunning {len(self.feature_tests)} feature tests...")

        # Calculate padding widths for nice output formatting
        counter_width = len(str(len(self.feature_tests)))
        max_varname_len = max(len(test.variable) for test in self.feature_tests)
        varname_width = min(max(max_varname_len + 2, 25), 40)

        # Create scratch subdirectory for tests
        test_dir = os.path.join(self.tmp_dir, "feature_tests")
        os.makedirs(test_dir, exist_ok=True)

        n_failed = 0
        start_time = time.time()
        for i, test in enumerate(sorted(self.feature_tests, key=lambda t: t.variable), 1):
            try:
                test_start_time = time.time()
                # Create test file with appropriate extension
                ext = ".cpp" if test.language == "c++" else ".c"
                test_file = os.path.join(test_dir, f"test_{test.variable}{ext}")
                obj_file = os.path.join(test_dir, f"test_{test.variable}.o")
                
                # Generate test file content based on test type
                if test.type == "compiler_flag":
                    from .feature import COMPILER_FLAG_TEST_TEMPLATE
                    content = COMPILER_FLAG_TEST_TEMPLATE.strip()
                    compiler = self.toolchain.cxx if test.language == "c++" else self.toolchain.cc
                    flags = [test.flag] if test.flag else []
                elif test.type == "header":
                    from .feature import HEADER_TEST_TEMPLATE
                    # Create include directives for each header
                    if not hasattr(test, 'headers') or not test.headers:
                        raise ValueError(f"Header test {test.variable} has no headers specified")
                    includes = []
                    for header in test.headers:
                        includes.append(f"#include <{header}>")
                    content = HEADER_TEST_TEMPLATE.strip().replace(
                        "{includes}",
                        "\n".join(includes)
                    )
                    compiler = self.toolchain.cxx if test.language == "c++" else self.toolchain.cc
                    flags = []
                elif test.type == "type":
                    from .feature import TYPE_TEST_TEMPLATE
                    # Create include directives for each header
                    if not hasattr(test, 'headers') or not test.headers:
                        raise ValueError(f"Type test {test.variable} has no headers specified")
                    if not hasattr(test, 'type_name') or not test.type_name:
                        raise ValueError(f"Type test {test.variable} has no type specified")
                    includes = []
                    for header in test.headers:
                        includes.append(f"#include <{header}>")
                    content = TYPE_TEST_TEMPLATE.strip().replace(
                        "{includes}",
                        "\n".join(includes)
                    ).replace(
                        "{type_name}",
                        test.type_name
                    )
                    compiler = self.toolchain.cxx if test.language == "c++" else self.toolchain.cc
                    flags = []
                elif test.type == "function":
                    from .feature import FUNCTION_TEST_TEMPLATE
                    # Create include directives for each header
                    if not hasattr(test, 'headers') or not test.headers:
                        raise ValueError(f"Function test {test.variable} has no headers specified")
                    if not hasattr(test, 'function') or not test.function:
                        raise ValueError(f"Function test {test.variable} has no function specified")
                    includes = []
                    for header in test.headers:
                        includes.append(f"#include <{header}>")
                    content = FUNCTION_TEST_TEMPLATE.strip().replace(
                        "{includes}",
                        "\n".join(includes)
                    ).replace(
                        "{function}",
                        test.function
                    )
                    compiler = self.toolchain.cxx if test.language == "c++" else self.toolchain.cc
                    flags = []
                elif test.type == "struct_member":
                    from .feature import STRUCT_MEMBER_TEST_TEMPLATE
                    # Create include directives for each header
                    if not hasattr(test, 'headers') or not test.headers:
                        raise ValueError(f"Struct member test {test.variable} has no headers specified")
                    if not hasattr(test, 'struct_name') or not test.struct_name:
                        raise ValueError(f"Struct member test {test.variable} has no struct specified")
                    if not hasattr(test, 'member') or not test.member:
                        raise ValueError(f"Struct member test {test.variable} has no member specified")
                    includes = []
                    for header in test.headers:
                        includes.append(f"#include <{header}>")
                    content = STRUCT_MEMBER_TEST_TEMPLATE.strip().replace(
                        "{includes}",
                        "\n".join(includes)
                    ).replace(
                        "{struct_name}",
                        test.struct_name
                    ).replace(
                        "{member}",
                        test.member
                    )
                    compiler = self.toolchain.cxx if test.language == "c++" else self.toolchain.cc
                    flags = []
                else:
                    raise ValueError(f"Unknown test type: {test.type}")
                
                # Write test file
                with open(test_file, 'w') as f:
                    f.write(content)
                    f.write('\n')  # Add trailing newline
                
                # Get base compiler flags
                base_flags = self.toolchain.cxxflags if test.language == "c++" else self.toolchain.cflags
                
                # Run test compilation
                cmd = compiler + base_flags + flags + ["-c", test_file, "-o", obj_file]                
                result = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                
                # Update test result
                test.result = result.returncode == 0
                test.duration = time.time() - test_start_time
                
                # Print status
                status = "available" if test.result else "not available"
                print(f"[{i:{counter_width}d}/{len(self.feature_tests)}]  {test.variable:<{varname_width}} ... {status} ({test.duration:.1f}s)")
                                
            except Exception as e:
                print(f"[{i:{counter_width}d}/{len(self.feature_tests)}]  {test.variable:<{varname_width}} ... failed")
                print(f"Subprocess Error: {e}")
                test.result = False
                test.duration = time.time() - test_start_time
                n_failed += 1

        if n_failed:
            print(f"\n{n_failed} of {len(self.feature_tests)} feature tests failed")
        else:
            print("\nAll feature tests completed")
            
        total_time = time.time() - start_time
        print(f"Total feature test time: {total_time:.1f}s")

    def get_unresolved_dependencies(self) -> List[str]:
        """Get list of dependencies that don't exist in known tasks.
        
        Returns:
            List of dependency names that are referenced but don't exist
        """
        # Collect all available target names
        available_targets = {task.target.name for task in self.compile_tasks}
        
        # Find all dependencies that don't exist
        unresolved = set()
        for task in self.compile_tasks:
            for dep_name in task.target.dependencies:
                if dep_name not in available_targets:
                    unresolved.add(dep_name)
                    
        return sorted(list(unresolved))


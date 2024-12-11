"""Tests for include directory handling in build system."""

import os
from typing import List

from build_toolkit import Target, Builder, Toolchain
from build_toolkit.utils import normalize_path


def normalize_paths(paths: List[str]) -> List[str]:
    """Normalize paths for comparison."""
    return [os.path.normpath(p) for p in paths]


def create_test_builder(root_dir: str) -> Builder:
    """Create a builder instance for testing with absolute paths."""
    build_dir = os.path.join(root_dir, "build")
    return Builder(
        toolchain=Toolchain(
            os="linux",
            arch="x86_64",
            cc=["gcc"], 
            cxx=["g++"],
            cflags=[],
            cxxflags=[],
            ar="ar",
            arflags=["-rcs"],
            compiler_id="gcc"
        ),
        gen_dir=os.path.join(build_dir, "gen"),
        obj_dir=os.path.join(build_dir, "obj"),
        lib_dir=os.path.join(build_dir, "lib"),
        tmp_dir=os.path.join(build_dir, "tmp")
    )


def test_basic_includes():
    """Test basic include directory handling."""
    # Use absolute paths for all directories
    root_dir = os.path.abspath("test_root")
    
    target = Target(
        name="test",
        root=root_dir,
        include_dirs=["include"],
        private_include_dirs=["src/internal"]
    )
    
    # Create builder and add target
    builder = create_test_builder(root_dir)
    builder.add_target(target)
    builder._setup_all_tasks()  # Set up includes and definitions
    
    # Get the compile task for our target
    task = next(t for t in builder.compile_tasks if t.target.name == "test")
    
    # Verify includes
    expected_public = normalize_paths([os.path.join(root_dir, "include")])
    expected_private = normalize_paths([os.path.join(root_dir, "src/internal")])
    
    actual_public = normalize_paths(task.public_include_dirs)
    actual_private = normalize_paths(task.private_include_dirs)
    
    assert expected_public == actual_public, "Public include dirs should match"
    assert expected_private == actual_private, "Private include dirs should match"


def test_dependency_includes():
    """Test include directory handling with dependencies."""
    root_dir = os.path.abspath("test_root")
    
    # Create dependency target
    dep = Target(
        name="dep",
        root=os.path.join(root_dir, "dep"),
        include_dirs=["include"],
        private_include_dirs=["internal"]
    )
    
    # Create main target depending on dep
    main = Target(
        name="main",
        root=os.path.join(root_dir, "main"),
        include_dirs=["include"],
        private_include_dirs=["src"],
        dependencies=["dep"]
    )
    
    # Create builder and add targets
    builder = create_test_builder(root_dir)
    builder.add_target(dep)
    builder.add_target(main)
    builder._setup_all_tasks()  # Set up includes and definitions
    
    # Get the compile task for main target
    task = next(t for t in builder.compile_tasks if t.target.name == "main")
    
    # Verify includes
    expected_public = normalize_paths([
        os.path.join(root_dir, "main/include"),
        os.path.join(root_dir, "dep/include")
    ])
    expected_private = normalize_paths([
        os.path.join(root_dir, "main/src")
    ])
    
    actual_public = normalize_paths(task.public_include_dirs)
    actual_private = normalize_paths(task.private_include_dirs)
    
    assert set(expected_public) == set(actual_public), "Public include dirs should include dependency's public includes"
    assert expected_private == actual_private, "Private include dirs should only contain own private includes"


def test_diamond_dependency():
    """Test include directory handling with diamond dependency pattern."""
    root_dir = os.path.abspath("test_root")
    
    # Create base target
    base = Target(
        name="base",
        root=os.path.join(root_dir, "base"),
        include_dirs=["include"]
    )
    
    # Create left and right dependencies
    left = Target(
        name="left",
        root=os.path.join(root_dir, "left"),
        include_dirs=["include"],
        dependencies=["base"]
    )
    
    right = Target(
        name="right",
        root=os.path.join(root_dir, "right"),
        include_dirs=["include"],
        dependencies=["base"]
    )
    
    # Create main target depending on both left and right
    main = Target(
        name="main",
        root=os.path.join(root_dir, "main"),
        include_dirs=["include"],
        dependencies=["left", "right"]
    )
    
    # Create builder and add all targets
    builder = create_test_builder(root_dir)
    builder.add_target(base)
    builder.add_target(left)
    builder.add_target(right)
    builder.add_target(main)
    builder._setup_all_tasks()  # Set up includes and definitions
    
    # Get the compile task for main target
    task = next(t for t in builder.compile_tasks if t.target.name == "main")
    
    # Verify includes
    expected = normalize_paths([
        os.path.join(root_dir, "main/include"),
        os.path.join(root_dir, "left/include"),
        os.path.join(root_dir, "right/include"),
        os.path.join(root_dir, "base/include")
    ])
    
    actual = normalize_paths(task.public_include_dirs)
    
    assert set(expected) == set(actual), "Include dirs should handle diamond dependency correctly"
  
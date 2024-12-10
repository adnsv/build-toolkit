import os
import unittest
from build_toolkit import Target, Builder, Toolchain
from build_toolkit.builder import get_all_include_dirs

def create_test_builder(*, gen_dir="/build/gen"):
    """Create a builder instance for testing."""
    return Builder(
        toolchain=Toolchain(
            os="linux",
            arch="x86_64",
            cxx="g++",
            ar="ar",
            cxxflags=["-c", "-Wall"],
            arflags=["rcs"],
            compiler_id="gcc"
        ),
        gen_dir=gen_dir,
        obj_dir="/build/obj",
        lib_dir="/build/lib"
    )

def test_expand_gen_var_exact():
    """Test expanding ${gen} when it's the exact path"""
    builder = create_test_builder()
    target = Target(name="test", root="/src/test")
    builder.add_target(target)

    expanded = os.path.normpath(target._expand_path_vars("${gen}", builder))
    expected = os.path.normpath(os.path.join("/build/gen", "test"))
    assert expanded == expected

def test_expand_gen_var_in_path():
    """Test expanding ${gen} when it's part of a larger path"""
    builder = create_test_builder()
    target = Target(name="test", root="/src/test")
    builder.add_target(target)

    expanded = os.path.normpath(target._expand_path_vars("${gen}/include", builder))
    expected = os.path.normpath(os.path.join("/build/gen", "test", "include"))
    assert expanded == expected

def test_expand_gen_var_middle_path():
    """Test expanding ${gen} when it's in the middle of a path"""
    builder = create_test_builder()
    target = Target(name="test", root="/src/test")
    builder.add_target(target)

    expanded = os.path.normpath(target._expand_path_vars("prefix/${gen}/suffix", builder))
    # ${gen} is simply replaced with its path, preserving the rest of the path
    gen_path = os.path.join("/build/gen", "test")
    expected = os.path.normpath(f"prefix/{gen_path}/suffix")
    assert expanded == expected

def test_expand_gen_var_relative_path():
    """Test expanding ${gen} when it's in a relative path"""
    # Use relative gen_dir
    builder = create_test_builder(gen_dir="build/gen")
    target = Target(name="test", root="src/test")
    builder.add_target(target)

    expanded = os.path.normpath(target._expand_path_vars("prefix/${gen}/suffix", builder))
    # When gen_dir is relative, it should be kept relative in the output
    gen_path = os.path.join("build/gen", "test")
    expected = os.path.normpath(os.path.join("prefix", gen_path, "suffix"))
    assert expanded == expected

def test_no_gen_var():
    """Test path without ${gen} variable"""
    builder = create_test_builder()
    target = Target(name="test", root="/src/test")
    builder.add_target(target)

    expanded = os.path.normpath(target._expand_path_vars("include/dir", builder))
    expected = os.path.normpath("include/dir")
    assert expanded == expected

def test_multiple_gen_vars():
    """Test path with multiple ${gen} variables - each occurrence is replaced"""
    builder = create_test_builder()
    target = Target(name="test", root="/src/test")
    builder.add_target(target)

    expanded = os.path.normpath(target._expand_path_vars("${gen}/include/${gen}", builder))
    # Each ${gen} is replaced with the same path
    gen_path = os.path.join("/build/gen", "test")
    expected = os.path.normpath(f"{gen_path}/include/{gen_path}")
    assert expanded == expected

def test_get_include_dirs_with_gen():
    """Test that include directories handle ${gen} paths correctly"""
    builder = create_test_builder()
    target = Target(
        name="test_includes",
        root="/src/test",
        include_dirs=[
            ".",
            "${gen}",
            "${gen}/include",
            "prefix/${gen}/suffix"
        ]
    )
    builder.add_target(target)
    
    include_dirs = get_all_include_dirs(target, builder)
    # ${gen} is replaced with its path, preserving any prefix
    gen_path = os.path.join("/build/gen", "test_includes")
    expected_paths = {
        os.path.normpath("/src/test"),
        os.path.normpath(gen_path),
        os.path.normpath(os.path.join(gen_path, "include")),
        os.path.normpath(os.path.join("prefix", gen_path, "suffix"))
    }
    
    # Convert both sets to normalized paths for comparison
    actual_paths = {os.path.normpath(p) for p in include_dirs}
    assert actual_paths == expected_paths

def test_private_include_dirs_with_gen():
    """Test that private include directories handle ${gen} paths correctly"""
    builder = create_test_builder()
    target = Target(
        name="test_private",
        root="/src/test",
        private_include_dirs=[
            "${gen}/private",
            "private/${gen}/include"
        ]
    )
    builder.add_target(target)
    
    include_dirs = get_all_include_dirs(target, builder, include_private=True)
    expected_paths = {
        os.path.normpath("/build/gen/test_private/private"),
        os.path.normpath(os.path.join("private", "/build/gen/test_private/include"))
    }
    
    # Convert both sets to normalized paths for comparison
    actual_paths = {os.path.normpath(p) for p in include_dirs}
    assert actual_paths == expected_paths

def test_dependency_include_dirs():
    """Test that include directories from dependencies handle ${gen} paths correctly"""
    builder = create_test_builder()
    dep_target = Target(
        name="dep",
        root="/src/dep",
        include_dirs=["${gen}/dep_include"]
    )
    main_target = Target(
        name="main",
        root="/src/main",
        include_dirs=["${gen}/main_include"],
        dependencies=["dep"]
    )
    
    builder.add_target(dep_target)
    builder.add_target(main_target)
    
    include_dirs = get_all_include_dirs(main_target, builder)
    expected_paths = {
        os.path.normpath("/build/gen/main/main_include"),
        os.path.normpath("/build/gen/dep/dep_include")
    }
    
    # Convert both sets to normalized paths for comparison
    actual_paths = {os.path.normpath(p) for p in include_dirs}
    assert actual_paths == expected_paths 
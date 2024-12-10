"""Tests for the Toolchain class."""

import pytest
from build_toolkit.toolchain import Toolchain


def test_toolchain_cxx_only():
    """Test Toolchain with only C++ settings."""
    toolchain = Toolchain(
        os="linux",
        arch="x86_64",
        cxx="g++",
        cxxflags=["-Wall", "-std=c++20"],
        ar="ar",
        arflags=["rcs"]
    )
    
    # C++ settings should be as provided
    assert toolchain.cxx == "g++", "C++ compiler should be g++"
    assert toolchain.cxxflags == ["-Wall", "-std=c++20"], "C++ flags should match input"
    
    # C settings should default to C++ settings
    assert toolchain.cc == toolchain.cxx, "C compiler should default to C++ compiler"
    assert toolchain.cflags == toolchain.cxxflags, "C flags should default to C++ flags"


def test_toolchain_separate_c_settings():
    """Test Toolchain with separate C and C++ settings."""
    toolchain = Toolchain(
        os="linux",
        arch="x86_64",
        cxx="g++",
        cxxflags=["-Wall", "-std=c++20"],
        cc="gcc",
        cflags=["-Wall", "-std=c17"],
        ar="ar",
        arflags=["rcs"]
    )
    
    # C++ settings should be as provided
    assert toolchain.cxx == "g++", "C++ compiler should be g++"
    assert toolchain.cxxflags == ["-Wall", "-std=c++20"], "C++ flags should match input"
    
    # C settings should be as provided
    assert toolchain.cc == "gcc", "C compiler should be gcc"
    assert toolchain.cflags == ["-Wall", "-std=c17"], "C flags should match input"


def test_toolchain_partial_c_settings():
    """Test Toolchain with only C compiler but no C flags."""
    toolchain = Toolchain(
        os="linux",
        arch="x86_64",
        cxx="g++",
        cxxflags=["-Wall", "-std=c++20"],
        cc="gcc",  # Only specify C compiler
        ar="ar",
        arflags=["rcs"]
    )
    
    # C++ settings should be as provided
    assert toolchain.cxx == "g++", "C++ compiler should be g++"
    assert toolchain.cxxflags == ["-Wall", "-std=c++20"], "C++ flags should match input"
    
    # C compiler should be as provided, but flags should default to C++
    assert toolchain.cc == "gcc", "C compiler should be gcc"
    assert toolchain.cflags == toolchain.cxxflags, "C flags should default to C++ flags"


def test_toolchain_empty_flags():
    """Test Toolchain with empty flag lists."""
    toolchain = Toolchain(
        os="linux",
        arch="x86_64",
        cxx="g++",
        cxxflags=[],  # Empty C++ flags
        cc="gcc",
        cflags=[],    # Empty C flags
        ar="ar",
        arflags=["rcs"]
    )
    
    assert toolchain.cxxflags == [], "C++ flags should be empty list"
    assert toolchain.cflags == [], "C flags should be empty list"


def test_toolchain_none_flags():
    """Test Toolchain with None for C flags."""
    toolchain = Toolchain(
        os="linux",
        arch="x86_64",
        cxx="g++",
        cxxflags=["-Wall"],
        cc="gcc",
        cflags=None,  # None should default to cxxflags
        ar="ar",
        arflags=["rcs"]
    )
    
    assert toolchain.cflags == toolchain.cxxflags, "None C flags should default to C++ flags"


def test_toolchain_library_naming():
    """Test Toolchain library naming settings."""
    toolchain = Toolchain(
        os="linux",
        arch="x86_64",
        cxx="g++",
        cxxflags=["-Wall"],
        ar="ar",
        arflags=["rcs"],
        lib_prefix="lib",
        lib_extension=".a"
    )
    
    assert toolchain.lib_prefix == "lib", "Library prefix should be set"
    assert toolchain.lib_extension == ".a", "Library extension should be set"


def test_toolchain_default_library_naming():
    """Test Toolchain default library naming settings."""
    toolchain = Toolchain(
        os="linux",
        arch="x86_64",
        cxx="g++",
        cxxflags=["-Wall"],
        ar="ar",
        arflags=["rcs"]
    )
    
    assert toolchain.lib_prefix == "", "Default library prefix should be empty"
    assert toolchain.lib_extension == ".a", "Default library extension should be .a" 
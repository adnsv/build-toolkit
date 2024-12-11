"""Tests for compiler identification functionality."""

from build_toolkit.compiler import determine_compiler_id

def test_gcc_variants():
    """Test GCC compiler identification."""
    assert determine_compiler_id("gcc", "g++") == "gcc"
    assert determine_compiler_id("/usr/bin/gcc", "/usr/bin/g++") == "gcc"
    assert determine_compiler_id("x86_64-w64-mingw32-gcc", "x86_64-w64-mingw32-g++") == "gcc"
    assert determine_compiler_id("i686-w64-mingw32-gcc.exe", "i686-w64-mingw32-g++.exe") == "gcc"

def test_clang_variants():
    """Test Clang compiler identification."""
    assert determine_compiler_id("clang", "clang++") == "clang"
    assert determine_compiler_id("/usr/bin/clang", "/usr/bin/clang++") == "clang"
    # Zig is identified as clang since it uses LLVM/Clang internally
    assert determine_compiler_id("zig", "zig") == "clang"
    assert determine_compiler_id("/usr/local/bin/zig", "/usr/local/bin/zig") == "clang"

def test_msvc_variants():
    """Test MSVC compiler identification.
    
    Note: clang-cl is identified as msvc since it's designed to be MSVC-compatible,
    using MSVC's command line interface and flags.
    """
    assert determine_compiler_id("cl", "cl") == "msvc"
    assert determine_compiler_id("cl.exe", "cl.exe") == "msvc"
    assert determine_compiler_id("clang-cl", "clang-cl") == "msvc"
    assert determine_compiler_id("clang-cl.exe", "clang-cl.exe") == "msvc"
    assert determine_compiler_id("C:\\Program Files\\Microsoft Visual Studio\\cl.exe", 
                             "C:\\Program Files\\Microsoft Visual Studio\\cl.exe") == "msvc"

def test_unknown_compilers():
    """Test unknown compiler identification."""
    assert determine_compiler_id("cc", "c++") == "unknown"
    assert determine_compiler_id("", "") == "unknown"

"""Tests for CMake-style configure_file functionality."""

import os
import tempfile
from textwrap import dedent
from build_toolkit.cmake_configure import cmake_configure_file


def _create_temp_file(content: str) -> str:
    """Create a temporary file with given content and return its path."""
    fd, path = tempfile.mkstemp(text=True)
    os.close(fd)
    with open(path, 'w') as f:
        f.write(dedent(content))
    return path


def _read_file(path: str) -> str:
    """Read file contents as string."""
    with open(path) as f:
        return f.read()


def test_empty_string_handling():
    """Test handling of empty string values."""
    template = """
        #cmakedefine EMPTY_VAL @EMPTY_VAL@
        #cmakedefine EMPTY_SIMPLE
        #define VISIBILITY @VISIBILITY@
        #define ANOTHER_EMPTY @ANOTHER_EMPTY@
    """
    
    expected = """
        #define EMPTY_VAL
        #define EMPTY_SIMPLE
        #define VISIBILITY
        #define ANOTHER_EMPTY
    """
    
    in_path = _create_temp_file(template)
    out_path = in_path + ".out"
    
    try:
        cmake_configure_file(in_path, out_path, {
            "EMPTY_VAL": "",
            "EMPTY_SIMPLE": "",
            "VISIBILITY": "",
            "ANOTHER_EMPTY": ""
        })
        
        assert _read_file(out_path).strip() == dedent(expected).strip()
    finally:
        os.unlink(in_path)
        if os.path.exists(out_path):
            os.unlink(out_path)


def test_basic_cmakedefine():
    """Test basic #cmakedefine processing."""
    template = """
        #cmakedefine FEATURE_A
        #cmakedefine FEATURE_B
        #cmakedefine FEATURE_C
    """
    
    expected = """
        #define FEATURE_A 1
        /* #undef FEATURE_B */
        #define FEATURE_C 1
    """
    
    in_path = _create_temp_file(template)
    out_path = in_path + ".out"
    
    try:
        cmake_configure_file(in_path, out_path, {
            "FEATURE_A": True,
            "FEATURE_B": False,
            "FEATURE_C": 1
        })
        
        assert _read_file(out_path).strip() == dedent(expected).strip()
    finally:
        os.unlink(in_path)
        if os.path.exists(out_path):
            os.unlink(out_path)


def test_cmakedefine01():
    """Test #cmakedefine01 processing."""
    template = """
        #cmakedefine01 FEATURE_A
        #cmakedefine01 FEATURE_B
    """
    
    expected = """
        #define FEATURE_A 1
        #define FEATURE_B 0
    """
    
    in_path = _create_temp_file(template)
    out_path = in_path + ".out"
    
    try:
        cmake_configure_file(in_path, out_path, {
            "FEATURE_A": True,
            "FEATURE_B": False
        })
        
        assert _read_file(out_path).strip() == dedent(expected).strip()
    finally:
        os.unlink(in_path)
        if os.path.exists(out_path):
            os.unlink(out_path)


def test_variable_substitution():
    """Test @VAR@ and ${VAR} substitution."""
    template = """
        #define VERSION @VERSION@
        #define FULL_VERSION "${VERSION}.${PATCH}"
        #cmakedefine FEATURE_A @FEATURE_A@
    """
    
    expected = """
        #define VERSION "1.0"
        #define FULL_VERSION "1.0.5"
        #define FEATURE_A enabled
    """
    
    in_path = _create_temp_file(template)
    out_path = in_path + ".out"
    
    try:
        cmake_configure_file(in_path, out_path, {
            "VERSION": "1.0",
            "PATCH": "5",
            "FEATURE_A": "enabled"
        })
        
        assert _read_file(out_path).strip() == dedent(expected).strip()
    finally:
        os.unlink(in_path)
        if os.path.exists(out_path):
            os.unlink(out_path)


def test_at_only_mode():
    """Test @ONLY mode for variable substitution."""
    template = """
        #define VERSION @VERSION@
        #define FULL_VERSION "${VERSION}.${PATCH}"
    """
    
    expected = """
        #define VERSION "1.0"
        #define FULL_VERSION "${VERSION}.${PATCH}"
    """
    
    in_path = _create_temp_file(template)
    out_path = in_path + ".out"
    
    try:
        cmake_configure_file(in_path, out_path, {
            "VERSION": "1.0",
            "PATCH": "5"
        }, at_only=True)
        
        assert _read_file(out_path).strip() == dedent(expected).strip()
    finally:
        os.unlink(in_path)
        if os.path.exists(out_path):
            os.unlink(out_path)


def test_value_formatting():
    """Test different value type formatting."""
    template = """
        #cmakedefine STRING_VAL @STRING_VAL@
        #cmakedefine INT_VAL @INT_VAL@
        #cmakedefine SPACED_VAL @SPACED_VAL@
        #cmakedefine BOOL_VAL
    """
    
    expected = """
        #define STRING_VAL simple
        #define INT_VAL 42
        #define SPACED_VAL "with spaces"
        #define BOOL_VAL 1
    """
    
    in_path = _create_temp_file(template)
    out_path = in_path + ".out"
    
    try:
        cmake_configure_file(in_path, out_path, {
            "STRING_VAL": "simple",
            "INT_VAL": 42,
            "SPACED_VAL": "with spaces",
            "BOOL_VAL": True
        })
        
        assert _read_file(out_path).strip() == dedent(expected).strip()
    finally:
        os.unlink(in_path)
        if os.path.exists(out_path):
            os.unlink(out_path)


def test_newline_handling():
    """Test newline handling options."""
    template = "line1\nline2\n"
    
    in_path = _create_temp_file(template)
    out_path = in_path + ".out"
    
    try:
        # Test LF
        cmake_configure_file(in_path, out_path, {}, newline="LF")
        with open(out_path, 'rb') as f:
            content = f.read()
            assert b'\r\n' not in content
            assert content.count(b'\n') == 2
        
        # Test CRLF
        cmake_configure_file(in_path, out_path, {}, newline="CRLF")
        with open(out_path, 'rb') as f:
            content = f.read()
            assert content.count(b'\r\n') == 2
    finally:
        os.unlink(in_path)
        if os.path.exists(out_path):
            os.unlink(out_path) 
"""Compiler identification and utilities."""

import os

def _strip_exe_suffix(path: str) -> str:
    """Strip .exe suffix from path if present.
    
    Args:
        path: Path that may end with .exe
        
    Returns:
        Path with .exe suffix removed if present
    """
    if path.lower().endswith(".exe"):
        return path[:-4]
    return path

def determine_compiler_id(cc: str, cxx: str) -> str:
    """Determine compiler ID from compiler executables.
    
    Args:
        cc: C compiler executable path
        cxx: C++ compiler executable path
        
    Returns:
        Compiler identifier (gcc, clang, msvc, unknown)
        
    Notes:
        - clang-cl is identified as 'msvc' since it's designed to be MSVC-compatible,
          using MSVC's command line interface and flags. This allows build systems to
          treat it the same way as the MSVC compiler.
        - Zig cc/c++ is identified as 'clang' since it uses LLVM/Clang internally.
    """
    # Strip .exe suffix and get base names
    cc_base = os.path.basename(_strip_exe_suffix(cc))
    cxx_base = os.path.basename(_strip_exe_suffix(cxx))
    
    # Check for GCC
    gcc_names = {"gcc", "x86_64-w64-mingw32-gcc", "i686-w64-mingw32-gcc"}
    gxx_names = {"g++", "x86_64-w64-mingw32-g++", "i686-w64-mingw32-g++"}
    if cc_base in gcc_names or cxx_base in gxx_names:
        return "gcc"
    
    # Check for MSVC (including clang-cl which mimics MSVC interface)
    msvc_names = {"cl", "clang-cl"}
    if cc_base in msvc_names or cxx_base in msvc_names:
        return "msvc"
    
    # Check for Clang (excluding clang-cl which is handled above)
    clang_names = {"clang", "zig"}
    clangxx_names = {"clang++", "zig"}
    if cc_base in clang_names or cxx_base in clangxx_names:
        return "clang"
            
    # Unknown compiler
    return "unknown"
"""Compiler toolchain configuration module."""

from typing import List, Optional
from .compiler import determine_compiler_id


class Toolchain:
    """Compiler toolchain configuration."""
    def __init__(self, *, 
                 os: str,
                 arch: str,
                 # C++ compiler settings
                 cxx: str, 
                 cxxflags: List[str],
                 # C compiler settings
                 cc: Optional[str] = None,
                 cflags: Optional[List[str]] = None,
                 # Library archiver
                 ar: str = "ar",
                 arflags: Optional[List[str]] = None,
                 # Library naming
                 lib_prefix: str = "",
                 lib_extension: str = ".a",
                 # Compiler identification
                 compiler_id: Optional[str] = None) -> None:
        """Initialize toolchain configuration.
        
        Args:
            os: Target operating system identifier
            arch: Target architecture identifier
            cxx: C++ compiler executable
            cxxflags: C++ compiler flags
            cc: C compiler executable (optional, defaults to cxx)
            cflags: C compiler flags (optional, defaults to cxxflags)
            ar: Library archiver executable
            arflags: Library archiver flags (optional, defaults to ["-rcs"])
            lib_prefix: Prefix for library names (default: "")
            lib_extension: Extension for library files (default: ".a")
            compiler_id: Compiler identifier (gcc, clang, msvc) (optional, auto-detected if not specified)
        """
        self.os = os
        self.arch = arch
        
        # Compilers and flags
        self.cxx = cxx
        self.cxxflags = cxxflags
        self.cc = cc if cc is not None else cxx  # Default C compiler to C++ compiler
        self.cflags = cflags if cflags is not None else cxxflags  # Default C flags to C++ flags
        
        # Library archiver
        self.ar = ar
        self.arflags = arflags if arflags is not None else ["-rcs"]  # Default ar flags
        
        # Library naming
        self.lib_prefix = lib_prefix
        self.lib_extension = lib_extension

        # Compiler identification
        self.compiler_id = compiler_id if compiler_id is not None else determine_compiler_id(self.cc, self.cxx)

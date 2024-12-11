"""Compiler toolchain configuration module."""

from typing import List, Optional
from .compiler import determine_compiler_id


class Toolchain:
    """Compiler toolchain configuration."""
    def __init__(self, *, 
                 os: str,
                 arch: str,
                 # C++ compiler settings
                 cxx: str | List[str],
                 cxxflags: List[str],
                 # C compiler settings
                 cc: str | List[str],
                 cflags: List[str],
                 # Library archiver
                 ar: str | List[str],
                 arflags: List[str],
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
                
        self.cxx = cxx if isinstance(cxx, list) else [cxx]
        self.cxxflags = cxxflags
        self.cc = cc if isinstance(cc, list) else [cc]
        self.cflags = cflags
        
        # Library archiver
        self.ar = ar if isinstance(ar, list) else [ar]   
        self.arflags = arflags
        
        # Library naming
        self.lib_prefix = lib_prefix
        self.lib_extension = lib_extension
        
        # Compilers and flags
        if len(self.cxx) == 0:
            raise ValueError("Missing C++ compiler")
        if len(self.cc) == 0:
            raise ValueError("Missing C compiler")
        if len(self.ar) == 0:
            raise ValueError("Missing AR archiver")

        # Compiler identification
        self.compiler_id = compiler_id if compiler_id is not None else determine_compiler_id(self.cc[0], self.cxx[0])

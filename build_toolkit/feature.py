"""Feature discovery and testing module.

Provides functionality similar to CMake's check_* functions for testing
compiler features, headers, functions, and symbols at build time.
"""

import os
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Set

@dataclass
class CompilerFlagCheck:
    """Check if a compiler flag is supported."""
    flag: str                # The flag to test
    variable: str           # Variable to store the result
    language: str = "c"     # Language to test with ("c" or "c++")
    result: bool = False    # Test result

@dataclass
class HeaderCheck:
    """Check if header files exist and can be included."""
    headers: List[str]      # Headers to check
    variable: str          # Variable to store the result
    language: str = "c"    # Language to test with ("c" or "c++")
    result: bool = False   # Test result

@dataclass
class TypeCheck:
    """Check if a type is defined and can be used."""
    type_name: str        # Type to check
    headers: List[str]    # Headers to include
    variable: str        # Variable to store the result
    language: str = "c"  # Language to test with ("c" or "c++")
    result: bool = False # Test result

@dataclass
class FeatureTestTask:
    """Represents a feature test to be executed.
    
    A feature test task can be requested by multiple targets but will only be executed once.
    The result will be shared among all requesting targets.
    
    Test types and their required fields:
    - compiler_flag: flag
    - header: headers
    - type: type_name, headers
    - function: function, headers
    """
    # Required fields
    type: str                # Test type (compiler_flag, header, type, function)
    variable: str           # Variable name to store result
    
    # Optional fields with defaults
    language: str = "c"     # Language to test with ("c" or "c++")
    headers: List[str] = field(default_factory=list)  # Headers to check
    result: bool = False    # Test result
    requesting_targets: Set[str] = field(default_factory=set)  # Set of target names that requested this test
    duration: float = 0.0   # Time taken to execute the test
    
    # Test-specific fields
    flag: Optional[str] = None  # Flag to test (for compiler_flag type)
    type_name: Optional[str] = None  # Type to check (for type type)
    function: Optional[str] = None  # Function to check (for function type)
    struct_name: Optional[str] = None  # Struct to check (for struct_member type)
    member: Optional[str] = None  # Member to check (for struct_member type)
    
    def __post_init__(self):
        """Validate required fields based on test type."""
        if self.type == 'compiler_flag':
            if not self.flag:
                raise ValueError(f"Compiler flag test {self.variable} missing required 'flag' field")
        elif self.type == 'type':
            if not self.type_name:
                raise ValueError(f"Type test {self.variable} missing required 'type_name' field")
            if not self.headers:
                raise ValueError(f"Type test {self.variable} missing required 'headers' field")
        elif self.type == 'function':
            if not self.function:
                raise ValueError(f"Function test {self.variable} missing required 'function' field")
            if not self.headers:
                raise ValueError(f"Function test {self.variable} missing required 'headers' field")
        elif self.type == 'header':
            if not self.headers:
                raise ValueError(f"Header test {self.variable} missing required 'headers' field")
        elif self.type == 'struct_member':
            if not self.struct_name:
                raise ValueError(f"Struct member test {self.variable} missing required 'struct_name' field")
            if not self.member:
                raise ValueError(f"Struct member test {self.variable} missing required 'member' field")
            if not self.headers:
                raise ValueError(f"Struct member test {self.variable} missing required 'headers' field")
        else:
            raise ValueError(f"Unknown test type: {self.type}")

    def __hash__(self) -> int:
        """Hash based on test attributes that determine uniqueness."""
        return hash((self.type, self.variable, self.language, self.flag, 
                    tuple(sorted(self.headers)), self.type_name, self.function,
                    self.struct_name, self.member))

    def __eq__(self, other) -> bool:
        """Equality based on test attributes that determine uniqueness."""
        if not isinstance(other, FeatureTestTask):
            return False
        return (self.type == other.type and
                self.variable == other.variable and
                self.language == other.language and
                self.flag == other.flag and
                sorted(self.headers) == sorted(other.headers) and
                self.type_name == other.type_name and
                self.function == other.function and
                self.struct_name == other.struct_name and
                self.member == other.member)

# Template for testing compiler flags
COMPILER_FLAG_TEST_TEMPLATE = """
int main(void) {
    return 0;
}
"""

# Template for testing headers
HEADER_TEST_TEMPLATE = """
{includes}

int main(void) {
    return 0;
}
"""

# Template for testing types
TYPE_TEST_TEMPLATE = """
{includes}

char (*p(void))[sizeof({type_name})];
int main(void) {
    return 0;
}
"""

# Template for testing functions
FUNCTION_TEST_TEMPLATE = """
{includes}

int main(void) {
    return (unsigned long long){function};
}
"""

# Template for testing struct members
STRUCT_MEMBER_TEST_TEMPLATE = """
{includes}

int main(void) {
    /* The array size will be negative if member doesn't exist */
    char (*p)[sizeof(((struct {struct_name}*)0)->{member})];
    return 0;
}
""" 
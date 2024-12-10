"""CMake-style template configuration.

This module provides functionality similar to CMake's configure_file command,
processing template files with variable substitutions and conditional defines.
"""

from typing import Union, Dict, Optional, Any


def _format_define_value(value: Union[bool, int, str, None], *, raw: bool = False) -> Optional[str]:
    """Format a value for #define directive.
    
    Args:
        value: The value to format:
            - True -> "1"
            - False -> "0" (for #cmakedefine01) or None (for #cmakedefine)
            - None -> None (explicit #undef)
            - str -> quoted if contains spaces/special chars or raw=False
            - int -> string representation
            - empty string -> None (to match CMake behavior)
        raw: If True, don't quote string values unless they contain spaces/special chars
    
    Returns:
        Formatted string value or None if should be undefined
    """
    if value is None:
        return None
    if isinstance(value, bool):
        return "1" if value else None
    if isinstance(value, int):
        return str(value)
    if isinstance(value, str):
        # Empty string should result in no value
        if not value:
            return None
        # Always quote if contains spaces or special chars
        needs_quotes = any(c.isspace() or not c.isalnum() for c in value)
        return f'"{value}"' if needs_quotes or not raw else value
    raise ValueError(f"Unsupported value type: {type(value)}")


def _process_cmakedefine(line: str, name: str, value: Union[bool, int, str, None], is_01: bool) -> str:
    """Process a #cmakedefine or #cmakedefine01 line.
    
    Args:
        line: Original template line
        name: Variable name
        value: Variable value
        is_01: True if processing #cmakedefine01
    
    Returns:
        Processed line with appropriate #define or #undef
    """
    if is_01:
        # #cmakedefine01 -> always #define with 0 or 1
        return f"#define {name} {'1' if value else '0'}"
    
    # For regular #cmakedefine, both None and False mean undefined
    if value is None or value is False:
        return f"/* #undef {name} */"
    
    # Replace @VAR@ in the original line if present
    if "@" in line:
        define_part = line.split(None, 1)[1]
        if isinstance(value, str):
            # Empty string should result in no value
            if not value:
                return f"#define {name}"
            # Quote only if contains spaces or special chars
            needs_quotes = any(c.isspace() or not c.isalnum() for c in value)
            formatted = f'"{value}"' if needs_quotes else value
        else:
            formatted = str(_format_define_value(value, raw=False) or "")
        return f"#define {define_part}".replace(f"@{name}@", formatted)
    
    # Regular #cmakedefine without @VAR@
    formatted = _format_define_value(value, raw=False)
    if formatted is None:
        if isinstance(value, str) and not value:
            # Empty string should result in just #define NAME
            return f"#define {name}"
        # Other None values should be undefined
        return f"/* #undef {name} */"
    return f"#define {name} {formatted}"


def _substitute_vars(line: str, definitions: Dict[str, Union[bool, int, str, None]], at_only: bool) -> str:
    """Perform variable substitution in a line.
    
    Args:
        line: Line to process
        definitions: Variable definitions
        at_only: If True, only substitute @VAR@ syntax
    
    Returns:
        Line with variables substituted
    """
    result = line
    
    def substitute_pattern(pattern: str, name: str, value: Any, in_string: bool) -> str:
        """Helper to substitute a single pattern.
        
        Args:
            pattern: String containing the pattern
            name: Pattern to replace (e.g. @VAR@ or ${VAR})
            value: Value to substitute
            in_string: Whether we're substituting inside an existing string
        """
        # Empty string should result in empty substitution
        if isinstance(value, str) and not value:
            # Replace the pattern and trim any trailing whitespace
            replaced = pattern.replace(name, "")
            return replaced.rstrip() if not in_string else replaced
        # Use raw values when substituting inside strings
        formatted = _format_define_value(value, raw=in_string)
        if formatted is not None:
            if in_string and isinstance(value, str) and formatted.startswith('"'):
                # Remove quotes when interpolating into a string
                formatted = formatted[1:-1]
            return pattern.replace(name, formatted)
        return pattern
    
    # Always process @VAR@ syntax
    for name, value in definitions.items():
        if value is not None:
            # @VAR@ substitutions are typically not inside strings
            result = substitute_pattern(result, f"@{name}@", value, False)
    
    # Process ${VAR} syntax unless at_only is True
    if not at_only:
        for name, value in definitions.items():
            if value is not None:
                # ${VAR} substitutions are typically inside strings
                result = substitute_pattern(result, f"${{{name}}}", value, True)
    
    return result


def cmake_configure_file(
    template_path: str,
    output_path: str,
    definitions: Dict[str, Union[bool, int, str, None]],
    *,
    at_only: bool = False,
    newline: Optional[str] = None,
    encoding: str = 'utf-8'
) -> None:
    """Process a template file similar to CMake's configure_file command.
    
    Template directives:
        #cmakedefine VAR         -> #define VAR 1 or /* #undef VAR */
        #cmakedefine01 VAR       -> #define VAR 0 or #define VAR 1
        @VAR@                    -> replaced with value
        ${VAR}                   -> replaced with value (unless at_only=True)
    
    Args:
        template_path: Input .in template file
        output_path: Where to write the processed result
        definitions: Dictionary mapping names to their values where:
            - True -> defined as 1
            - False -> defined as 0 (for #cmakedefine01) or undefined
            - None -> explicitly undefined
            - str/int -> defined with that value
        at_only: If True, only process @VAR@ syntax
        newline: None (platform), "LF", "CRLF"
        encoding: File encoding (default: utf-8)
    """
    newline_chars = {
        None: None,  # Platform default
        "LF": "\n",
        "CRLF": "\r\n"
    }[newline]
    
    with open(template_path, 'r', encoding=encoding, newline='') as f:
        lines = f.readlines()
    
    processed_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#cmakedefine01 "):
            name = stripped.split(None, 1)[1].split(None, 1)[0]
            value = definitions.get(name)
            processed = _process_cmakedefine(stripped, name, value, True)
        elif stripped.startswith("#cmakedefine "):
            name = stripped.split(None, 1)[1].split(None, 1)[0]
            value = definitions.get(name)
            processed = _process_cmakedefine(stripped, name, value, False)
        else:
            processed = _substitute_vars(line.rstrip('\r\n'), definitions, at_only)
        
        processed_lines.append(processed)
    
    with open(output_path, 'w', encoding=encoding, newline=newline_chars) as f:
        for line in processed_lines:
            print(line, file=f) 
"""Build target configuration module."""

import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

@dataclass
class GeneratedFile:
    """Configuration for a file to be generated.
    
    Attributes:
        template: Template file path (relative to target root)
        output: Output file path (relative to gen/)
        type: Generator type (e.g. "cmake_configure")
        definitions: Dictionary of template variable definitions
    """
    template: str
    output: str
    type: str
    definitions: Dict[str, Any] = field(default_factory=dict)

    def __init__(self, template: str, output: str, type: str, definitions: dict):
        self.template = template
        self.output = output
        self.type = type
        self.definitions = definitions

    @classmethod
    def from_dict(cls, data: dict) -> 'GeneratedFile':
        """Create a GeneratedFile instance from a dictionary."""
        required_fields = {'template', 'output', 'type', 'definitions'}
        missing_fields = required_fields - set(data.keys())
        if missing_fields:
            raise ValueError(f"Generated file missing required fields: {missing_fields}")
            
        string_fields = {'template', 'output', 'type'}
        for field in string_fields:
            if not isinstance(data[field], str):
                raise ValueError(f"Generated file field '{field}' must be a string")
        
        # Validate definitions field
        if not isinstance(data['definitions'], dict):
            raise ValueError("Generated file field 'definitions' must be a dictionary")

        return cls(
            template=data['template'],
            output=data['output'],
            type=data['type'],
            definitions=data['definitions']
        )

@dataclass
class Target:
    """Build target configuration.
    
    Attributes:
        name: Target name
        root: Root directory for source files
        sources: List of source files
        include_dirs: List of public include directories
        private_include_dirs: List of private include directories
        definitions: List of public preprocessor definitions
        private_definitions: List of private preprocessor definitions
        dependencies: List of target dependencies
        system_dependencies: List of system library dependencies
        output: Optional output library name
        generated_files: List of generated file configurations
        options: Dictionary of target-specific options
        feature_tests: List of feature test configurations
    """
    name: str
    root: str = "."
    sources: List[str] = field(default_factory=list)
    include_dirs: List[str] = field(default_factory=list)
    private_include_dirs: List[str] = field(default_factory=list)
    definitions: List[str] = field(default_factory=list)
    private_definitions: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    system_dependencies: List[str] = field(default_factory=list)
    output: Optional[str] = None
    generated_files: List[GeneratedFile] = field(default_factory=list)
    options: Dict[str, Any] = field(default_factory=dict)
    feature_tests: List[Any] = field(default_factory=list)

    @classmethod
    def from_dict(cls, *, data: Dict[str, Any]) -> 'Target':
        """Create Target instance from dictionary.
        
        Args:
            data: Dictionary with target configuration
                Required fields:
                    - name: str
                Optional fields:
                    - root: str (default: ".")
                    - sources: List[str] (default: [])
                    - include_dirs: List[str] (default: [])
                    - private_include_dirs: List[str] (default: [])
                    - definitions: List[str] (default: [])
                    - private_definitions: List[str] (default: [])
                    - dependencies: List[str] (default: [])
                    - system_dependencies: List[str] (default: [])
                    - output: str (default: None)
                    - generated_files: List[GeneratedFile] (default: [])
                    - options: Dict[str, Any] (default: {})
                    - feature_tests: List[Any] (default: [])
            
        Returns:
            New Target instance
            
        Raises:
            ValueError: If name is missing, if any fields have invalid types,
                       or if unknown fields are present
        """
        # Check for unknown fields
        valid_fields = {'name', 'root', 'sources', 
                       'include_dirs', 'private_include_dirs',
                       'definitions', 'private_definitions',
                       'dependencies', 'system_dependencies',
                       'output', 'generated_files', 'options', 'feature_tests'}
        unknown_fields = set(data.keys()) - valid_fields
        if unknown_fields:
            raise ValueError(f"Unknown fields in configuration: {', '.join(unknown_fields)}")

        # Validate required name field
        if 'name' not in data:
            raise ValueError("Missing required field 'name'")
        if not isinstance(data['name'], str):
            raise ValueError("Field 'name' must be of type str")
        
        # Set defaults for optional list fields
        list_fields = {
            'sources': [],
            'include_dirs': [],
            'private_include_dirs': [],
            'definitions': [],
            'private_definitions': [],
            'dependencies': [],
            'system_dependencies': [],
            'feature_tests': []
        }
        
        # Validate and set defaults for list fields
        for field, default in list_fields.items():
            if field in data:
                if data[field] is None:
                    data[field] = default
                elif not isinstance(data[field], list):
                    raise ValueError(f"Field '{field}' must be of type list")
                elif not all(isinstance(item, str) for item in data[field]):
                    raise ValueError(f"All elements in '{field}' must be of type str")
            else:
                data[field] = default
        
        # Validate optional string fields
        string_fields = ['root', 'output']
        for field in string_fields:
            if field in data and data[field] is not None:
                if not isinstance(data[field], str):
                    raise ValueError(f"Field '{field}' must be of type str")
        
        # Handle generated_files
        if 'generated_files' in data:
            if data['generated_files'] is not None:
                if not isinstance(data['generated_files'], list):
                    raise ValueError("Field 'generated_files' must be of type list")
                # Convert each dict to GeneratedFile
                data['generated_files'] = [GeneratedFile.from_dict(gen_file) for gen_file in data['generated_files']]
        
        # Handle options
        if 'options' in data:
            if data['options'] is not None and not isinstance(data['options'], dict):
                raise ValueError("Field 'options' must be of type dict")
        
        # Handle feature_tests
        if 'feature_tests' in data:
            if data['feature_tests'] is not None:
                if not isinstance(data['feature_tests'], list):
                    raise ValueError("Field 'feature_tests' must be of type list")
        
        # Create new instance with validated data
        return cls(**data)

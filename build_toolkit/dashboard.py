"""Dashboard generation module for build results visualization."""

import os
import subprocess
from typing import List, Optional, Sequence
from dataclasses import dataclass
from datetime import datetime
from string import Template
from build_toolkit.builder import Builder, CompileTask

# Load HTML template
TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), "templates", "dashboard.html")

with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
    HTML_TEMPLATE = Template(f.read())

@dataclass
class TaskSummary:
    """Summary of a compilation task."""
    name: str
    task: 'CompileTask'  # Reference to the original task
    succeeded: bool
    compile_results: list

def _summarize_task(task):
    """Create a summary of a compile task."""
    compile_results = []
    succeeded = True
    
    for command in task.commands:
        result = command.result
        if result is None or not result.succeeded:
            succeeded = False
            
        compile_results.append({
            'command': command,
            'success': result.succeeded if result else False,
            'duration': result.duration if result else 0.0,
            'stdout': result.stdout if result else '',
            'stderr': result.stderr if result else ''
        })
        
    return TaskSummary(
        name=task.target.name,
        task=task,
        succeeded=succeeded,
        compile_results=compile_results
    )

def _generate_result_id(command_result, task_name: str) -> str:
    """Generate a consistent ID for a compilation result.
    
    Args:
        command_result: Dictionary containing command and result info
        task_name: Name of the task this command belongs to
        
    Returns:
        A stable ID string based on the task name and source file
    """
    command = command_result['command']
    # Use task name and source file for a stable ID
    safe_path = os.path.basename(command.source_file).replace('.', '_')
    return f"compile-{task_name}-{safe_path}"

def _generate_task_section(task_summary: TaskSummary) -> str:
    """Generate HTML for a compilation task section."""
    content = []
    target_id = f"target-{task_summary.name}"
    
    content.append(f'''
        <div id="{target_id}">
            <h1>Target: {task_summary.name}</h1>
    ''')

    # Dependencies section
    if task_summary.task.target.dependencies:
        deps_str = "\n".join(task_summary.task.target.dependencies)
        content.append(f'''
            <h2>Dependencies</h2>
            <div class="code-block">
                <pre class="dependencies">{deps_str}</pre>
            </div>
        ''')

    # Include directories section
    if task_summary.task.public_include_dirs or task_summary.task.private_include_dirs:
        content.append('''
            <h2>Include Directories</h2>
            <div class="code-block">
        ''')
        
        # Show public includes if any
        if task_summary.task.public_include_dirs:
            paths = "\n".join(task_summary.task.public_include_dirs)
            content.append(f'''
                <div class="section-header">Public</div>
                <pre class="include-paths">{paths}</pre>
            ''')
        
        # Show private includes if any
        if task_summary.task.private_include_dirs:
            paths = "\n".join(task_summary.task.private_include_dirs)
            content.append(f'''
                <div class="section-header">Private</div>
                <pre class="include-paths">{paths}</pre>
            ''')
        
        content.append('''
            </div>
        ''')

    # System Dependencies section
    if task_summary.task.target.system_dependencies:
        content.append('''
            <h2>System Dependencies</h2>
            <div class="code-block">
        ''')
        sys_deps_str = "\n".join(task_summary.task.target.system_dependencies)
        content.append(f'''
            <pre class="system-dependencies">{sys_deps_str}</pre>
        ''')
        content.append('''
            </div>
        ''')

    # Definitions section
    if task_summary.task.public_definitions or task_summary.task.private_definitions:
        content.append('''
            <h2>Definitions</h2>
            <div class="code-block">
        ''')
        
        # Show public definitions if any
        if task_summary.task.public_definitions:
            definitions_str = "\n".join(task_summary.task.public_definitions)
            content.append(f'''
                <div class="section-header">Public</div>
                <pre>{definitions_str}</pre>
            ''')
        
        # Show private definitions if any
        if task_summary.task.private_definitions:
            private_defs = "\n".join(task_summary.task.private_definitions)
            content.append(f'''
                <div class="section-header">Private</div>
                <pre>{private_defs}</pre>
            ''')
        
        content.append('''
            </div>
        ''')

    # Add file generation section if present
    if task_summary.task.generated_steps:
        for step in task_summary.task.generated_steps:
            status_class = 'success' if step.succeeded else 'failure'
            status_text = 'Success' if step.succeeded else 'Failed'
            content.append(f'''
            <div class="compilation-header">
                <h2>Generate {os.path.basename(step.output)}</h2>
                <div class="status-indicator">
                    <span class="duration-pill">{step.duration:.1f}s</span>
                    <span class="status-pill {status_class}">{status_text}</span>
                </div>
            </div>
            <div class="code-block">
                <div class="code-caption">
                    <span>Template File</span>
                </div>
                <pre>{step.template}</pre>
                <div class="code-caption">
                    <span>Output File</span>
                </div>
                <pre>{step.output}</pre>
                <div class="code-caption">
                    <span>Type</span>
                </div>
                <pre>{step.type}</pre>
            </div>''')
            if step.definitions:
                content.append('''
                <div class="code-block">
                    <div class="code-caption">
                        <span>Definitions</span>
                    </div>
                    <pre>''')
                for key, value in step.definitions.items():
                    content.append(f"{key} = {value}")
                content.append('''</pre>
                </div>''')
            if not step.succeeded and step.error:
                content.append(f'''
                <div class="code-block error">
                    <div class="code-caption">
                        <span>Error</span>
                    </div>
                    <pre>{step.error}</pre>
                </div>''')
            content.append('')

    # Use compile results in their original order
    for i, command_result in enumerate(task_summary.compile_results):
        result_id = _generate_result_id(command_result, task_summary.name)
        status_class = 'success' if command_result['success'] else 'failure'
        status_text = 'Success' if command_result['success'] else 'Failed'
        command = command_result['command']

        content.append(rf'''
            <div id="{result_id}">
                <div class="compilation-header">
                    <h2>Compile {os.path.basename(command.source_file)}</h2>
                    <div class="status-indicator">
                        <span class="duration-pill">{command_result['duration']:.1f}s</span>
                        <span class="status-pill {status_class}">{status_text}</span>
                    </div>
                </div>

                <div class="code-block">
                    <div class="code-caption">
                        <span>Input File</span>
                    </div>
                    <pre>{command.source_file}</pre>
                    <div class="code-caption">
                        <span>Output File</span>
                    </div>
                    <pre>{command.output_file}</pre>
                </div>

                <div class="code-block command-block">
                    <div class="code-caption">
                        <span>Compilation Command</span>
                    </div>
                    <pre>{command.command}</pre>
                </div>
        ''')

        # Show command output if any
        if command_result['stdout'] or command_result['stderr']:
            output = []
            if command_result['stdout']:
                output.append(command_result['stdout'])
            if command_result['stderr']:
                if output:  # If we already have stdout
                    output.append("\n--- stderr ---\n")
                output.append(command_result['stderr'])
                
            content.append(rf'''
                <div class="code-block output-block">
                    <div class="code-caption">
                        <span>Command Output</span>
                    </div>
                    <div class="collapsible-content">
                        <pre>{"".join(output)}</pre>
                        <button class="show-more" onclick="toggleOutput(this)">More</button>
                    </div>
                </div>
            ''')

        content.append('</div>')

    content.append('</div>')
    return "\n".join(content)

def _generate_libraries_section(archive_tasks) -> str:
    """Generate HTML content for the libraries section."""
    content = []
    
    # Add section header with ID
    content.append('''
        <div id="libraries">
            <h1>Output Libraries</h1>
    ''')
    
    for archive in archive_tasks:
        lib_id = f"lib-{os.path.basename(archive.output_file)}"
        status_class = "success" if archive.result and archive.result.succeeded else "failure"
        status_text = "Success" if archive.result and archive.result.succeeded else "Failed"
        
        try:
            size = os.path.getsize(archive.output_file) if archive.result and archive.result.succeeded else 0
            size_str = f"{size / 1024:.1f} KB" if size >= 1024 else f"{size} bytes"
        except OSError:
            size_str = "Unknown"
        
        content.append(rf'''
            <div id="{lib_id}">
                <div class="compilation-header">
                    <h2>Library: {os.path.basename(archive.output_file)}</h2>
                    <div class="status-indicator">
                        <span class="duration-pill">{archive.result.duration:.1f}s</span>
                        <span class="status-pill {status_class}">{status_text}</span>
                    </div>
                </div>
                {f'<p>Size: {size_str}</p>' if archive.result and archive.result.succeeded else ''}
                
                <div class="code-block">
                    <div class="code-caption">
                        <span>Object Files</span>
                    </div>
                    <pre>''')
        
        # Collect all object files
        object_files = []
        for task in archive.compile_tasks:
            for command in task.commands:
                object_files.append(command.output_file)
        
        # Join with explicit line breaks and append to content
        content.append('\n'.join(object_files))
        
        content.append(f'''</pre>
                    <div class="code-caption">
                        <span>Output File</span>
                    </div>
                    <pre>{archive.output_file}</pre>
                </div>
                
                <div class="code-block command-block">
                    <div class="code-caption">
                        <span>Archive Command</span>
                    </div>
                    <pre>{archive.command}</pre>
                </div>''')
        
        if archive.result:
            # Show error message if failed
            if not archive.result.succeeded and archive.result.error:
                content.append(rf'''
                    <div class="code-block error">
                        <div class="code-caption">
                            <span>Error</span>
                        </div>
                        <pre>{archive.result.error}</pre>
                    </div>
                ''')

            # Show command output if any
            if archive.result.stdout or archive.result.stderr:
                output = []
                if archive.result.stdout:
                    output.append(archive.result.stdout)
                if archive.result.stderr:
                    if output:  # If we already have stdout
                        output.append("\n--- stderr ---\n")
                    output.append(archive.result.stderr)
                    
                content.append(rf'''
                    <div class="code-block output-block">
                        <div class="code-caption">
                            <span>Command Output</span>
                        </div>
                        <div class="collapsible-content">
                            <pre>{"".join(output)}</pre>
                            <button class="show-more" onclick="toggleOutput(this)">More</button>
                        </div>
                    </div>
                ''')
        
        content.append('</div>')
    
    return "\n".join(content)

def _generate_tree_view(builder: Builder) -> list[str]:
    """Generate the tree view HTML content."""
    tree_content = []
    
    # Calculate overall build status
    all_succeeded = True
    for task in builder.compile_tasks:
        for command in task.commands:
            if not command.result or not command.result.succeeded:
                all_succeeded = False
                break
    for archive in builder.archive_tasks:
        if not archive.result or not archive.result.succeeded:
            all_succeeded = False
            break
    
    # Add build overview
    tree_content.append(f'''
        <div class="tree-node">
            <div class="tree-item" data-target="overview">
                <div class="tree-item-content">
                    <span style="width: 1em; display: inline-block;">&nbsp;</span>
                    <span onclick="scrollToSection('overview')">Build Overview</span>
                </div>
                <div class="tree-item-indicators">
                    <span class="status-dot {'success' if all_succeeded else 'failure'}"></span>
                </div>
            </div>
        </div>
    ''')
    
    # Add feature tests section if there are any
    if builder.feature_tests:
        tree_content.append(f'''
            <div class="tree-node">
                <div class="tree-item" data-target="feature-tests">
                    <div class="tree-item-content">
                        <span style="width: 1em; display: inline-block;">&nbsp;</span>
                        <span onclick="scrollToSection('feature-tests')">Feature Tests</span>
                    </div>
                </div>
            </div>
        ''')
    
    # Add targets
    task_summaries = [_summarize_task(task) for task in builder.compile_tasks]
    for task_summary in task_summaries:
        target_id = f"target-{task_summary.name}"
        status_class = "success" if task_summary.succeeded else "failure"
        
        tree_content.append(rf'''
            <div class="tree-node">
                <div class="tree-item" data-target="{target_id}">
                    <div class="tree-item-content">
                        <span class="arrow">▶</span>
                        <span onclick="scrollToSection('{target_id}')">Target {task_summary.name}</span>
                    </div>
                    <div class="tree-item-indicators">
                        <span class="status-dot {status_class}"></span>
                    </div>
                </div>
                <div class="tree-children">
        ''')
        
        # Use compile results in their original order
        for i, command_result in enumerate(task_summary.compile_results):
            result_id = _generate_result_id(command_result, task_summary.name)
            status_class = 'success' if command_result['success'] else 'failure'
            tree_content.append(rf'''
                    <div class="tree-item child" data-target="{result_id}">
                        <div class="tree-item-content">
                            <span class="file-icon">📄</span>
                            <span onclick="scrollToSection('{result_id}')" title="{command_result['command'].source_file}">{os.path.basename(command_result['command'].source_file)}</span>
                        </div>
                        <div class="tree-item-indicators">
                            <span class="duration-pill">{command_result['duration']:.1f}s</span>
                            <span class="status-dot {status_class}"></span>
                        </div>
                    </div>
            ''')
        
        tree_content.append('''
                </div>
            </div>
        ''')

    # Add libraries section
    if builder.archive_tasks:
        # Calculate overall library status
        libs_succeeded = all(archive.result and archive.result.succeeded for archive in builder.archive_tasks)
        
        tree_content.append(rf'''
            <div class="tree-node">
                <div class="tree-item" data-target="libraries">
                    <div class="tree-item-content">
                        <span class="arrow">▶</span>
                        <span onclick="scrollToSection('libraries')">Output Libraries</span>
                    </div>
                    <div class="tree-item-indicators">
                        <span class="status-dot {'success' if libs_succeeded else 'failure'}"></span>
                    </div>
                </div>
                <div class="tree-children">
        ''')
        
        # Add archive tasks as children
        for archive in builder.archive_tasks:
            lib_id = f"lib-{os.path.basename(archive.output_file)}"
            status_class = "success" if archive.result and archive.result.succeeded else "failure"
            duration = archive.result.duration if archive.result else 0.0
            
            tree_content.append(rf'''
                    <div class="tree-item child" data-target="{lib_id}">
                        <div class="tree-item-content">
                            <span class="file-icon">📄</span>
                            <span onclick="scrollToSection('{lib_id}')">{os.path.basename(archive.output_file)}</span>
                        </div>
                        <div class="tree-item-indicators">
                            <span class="duration-pill">{duration:.1f}s</span>
                            <span class="status-dot {status_class}"></span>
                        </div>
                    </div>
            ''')
            
        tree_content.append('''
                </div>
            </div>
        ''')
    
    return tree_content

def _generate_overview_section(builder: Builder) -> str:
    """Generate HTML for the overview section."""
    content = []
    
    # Calculate stats for each phase
    total_features = len(builder.feature_tests)
    feature_time = sum(test.duration for test in builder.feature_tests if hasattr(test, 'duration'))
    
    total_generated = sum(len(task.generated_steps) for task in builder.compile_tasks)
    generation_time = sum(step.duration for task in builder.compile_tasks for step in task.generated_steps if step.succeeded)
    
    total_compiled = sum(len(task.commands) for task in builder.compile_tasks)
    compilation_time = builder.total_compile_time
    
    total_archived = len(builder.archive_tasks)
    archive_time = sum(archive.result.duration for archive in builder.archive_tasks if archive.result and archive.result.succeeded)
    
    total_time = feature_time + generation_time + compilation_time + archive_time
    
    content.append('<h1>Build Overview</h1>')
    content.append('''
        <table class="stats">
            <tr>
                <th class="stat-label">Phase</th>
                <th class="stat-value">Count</th>
                <th class="stat-time">Time</th>
                <th class="stat-status" style="text-align: center">Status</th>
            </tr>''')
    
    if total_features > 0:
        content.append(f'''
            <tr>
                <td class="stat-label">Feature Tests</td>
                <td class="stat-value">{total_features} features</td>
                <td class="stat-time">{feature_time:.1f}s</td>
                <td class="stat-status" style="text-align: center"><span class="status-dot success"></span></td>
            </tr>''')
    
    if total_generated > 0:
        gen_success = all(step.succeeded for task in builder.compile_tasks for step in task.generated_steps)
        content.append(f'''
            <tr>
                <td class="stat-label">File Generation</td>
                <td class="stat-value">{total_generated} files</td>
                <td class="stat-time">{generation_time:.1f}s</td>
                <td class="stat-status" style="text-align: center"><span class="status-dot {'success' if gen_success else 'failure'}"></span></td>
            </tr>''')
    
    compile_success = all(command.result and command.result.succeeded for task in builder.compile_tasks for command in task.commands)
    content.append(f'''
        <tr>
            <td class="stat-label">Compilation</td>
            <td class="stat-value">{len(builder.compile_tasks)} targets / {total_compiled} files</td>
            <td class="stat-time">{compilation_time:.1f}s</td>
            <td class="stat-status" style="text-align: center"><span class="status-dot {'success' if compile_success else 'failure'}"></span></td>
        </tr>''')
    
    archive_success = all(archive.result and archive.result.succeeded for archive in builder.archive_tasks)
    content.append(f'''
        <tr>
            <td class="stat-label">Archive</td>
            <td class="stat-value">{total_archived} libraries</td>
            <td class="stat-time">{archive_time:.1f}s</td>
            <td class="stat-status" style="text-align: center"><span class="status-dot {'success' if archive_success else 'failure'}"></span></td>
        </tr>''')
    
    overall_success = (not total_generated or gen_success) and \
                     compile_success and \
                     archive_success
    content.append(f'''
            <tr class="total">
                <td>Total</td>
                <td></td>
                <td class="stat-time">{total_time:.1f}s</td>
                <td class="stat-status" style="text-align: center"><span class="status-dot {'success' if overall_success else 'failure'}"></span></td>
            </tr>
        </table>''')

    return '\n'.join(content)

def _generate_feature_tests_section(builder: Builder) -> str:
    """Generate HTML content for the feature tests section."""
    if not builder.feature_tests:
        return ""
        
    content = []
    content.append('''
        <div id="feature-tests">
            <h1>Feature Tests</h1>
    ''')
    
    # Group tests by type
    tests_by_type = {}
    for test in builder.feature_tests:
        if test.type not in tests_by_type:
            tests_by_type[test.type] = []
        tests_by_type[test.type].append(test)
    
    # Add each test type section
    for test_type, tests in sorted(tests_by_type.items()):
        content.append(f'''
            <h2>{test_type.replace('_', ' ').title()} Tests</h2>
            <div class="code-block">
                <table class="feature-tests" style="width: 100%; border-spacing: 0; padding: 0.25em;">
                    <tr>
                        <th style="text-align: left; padding: 0.25em 1em;">Variable</th>
                        <th style="text-align: left; padding: 0.25em 1em;">Details</th>
                        <th style="text-align: center; padding: 0.25em 1em;">Available</th>
                        <th style="text-align: left; padding: 0.25em 1em;">Used By</th>
                    </tr>
        ''')
        
        for test in sorted(tests, key=lambda t: t.variable):
            # Format test details based on type
            if test.type == "compiler_flag":
                details = test.flag
            elif test.type == "header":
                details = ", ".join(test.headers)
            elif test.type == "type":
                details = f"{test.type_name} in {', '.join(test.headers)}"
            elif test.type == "function":
                details = f"{test.function} in {', '.join(test.headers)}"
            elif test.type == "struct_member":
                details = f"{test.member} in struct {test.struct_name} ({', '.join(test.headers)})"
            else:
                details = "Unknown test type"
            
            # Format requesting targets
            targets = ", ".join(sorted(test.requesting_targets))
            
            content.append(f'''
                <tr>
                    <td style="padding: 0.25em 1em;">{test.variable}</td>
                    <td style="padding: 0.25em 1em;">{details}</td>
                    <td style="text-align: center; padding: 0.25em 1em;">{str(test.result).lower()}</td>
                    <td style="padding: 0.25em 1em;">{targets}</td>
                </tr>
            ''')
        
        content.append('''
                </table>
            </div>
        ''')
    
    content.append('</div>')
    return "\n".join(content)

def _generate_content_sections(builder: Builder) -> List[str]:
    """Generate all content sections for the dashboard."""
    content_sections = []
    
    # Add overview section
    content_sections.append(_generate_overview_section(builder))
    
    # Add feature tests section if there are any
    if builder.feature_tests:
        content_sections.append(_generate_feature_tests_section(builder))
    
    # Add target sections
    for task in builder.compile_tasks:
        task_summary = _summarize_task(task)
        content_sections.append(_generate_task_section(task_summary))
    
    # Add libraries section if there are any archive tasks
    if builder.archive_tasks:
        content_sections.append(_generate_libraries_section(builder.archive_tasks))
    
    return content_sections

def make_dashboard(builder: Builder, output_path: str) -> None:
    """Generate an HTML dashboard for build results.
    
    Args:
        builder: Builder instance with build results
        output_path: Path to write the HTML file
    """
    # Generate tree view and content sections
    tree_content = _generate_tree_view(builder)
    content_sections = _generate_content_sections(builder)
    
    # Combine sections and apply template
    html = HTML_TEMPLATE.substitute(
        tree_content="\n".join(tree_content),
        content="\n".join(content_sections)
    )
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Write to file
    with open(output_path, "w", encoding='utf-8') as f:
        f.write(html)

def _format_output(stdout: str, stderr: str, success: bool) -> str:
    """Format command output with proper styling"""
    
    status_class = "success" if success else "failure"
    return f'''
        <div class="code-block output-block">
            <div class="code-caption">
                <span>Command Output</span>
            </div>
            <div class="collapsible-content">
                <pre>{stdout}{stderr}</pre>
                <button class="show-more" onclick="toggleOutput(this)">More</button>
            </div>
        </div>
    '''

def _generate_command_output_section(command_result):
    """Generate HTML for command output section."""
    if command_result['stdout'] or command_result['stderr']:
        output = []
        if command_result['stdout']:
            output.append(command_result['stdout'])
        if command_result['stderr']:
            if output:  # If we already have stdout
                output.append("\n--- stderr ---\n")
            output.append(command_result['stderr'])
            
        return rf'''
            <div class="code-block output-block">
                <div class="code-caption">
                    <span>Command Output</span>
                </div>
                <div class="collapsible-content">
                    <pre>{"".join(output)}</pre>
                    <button class="show-more" onclick="toggleOutput(this)">More</button>
                </div>
            </div>
        '''
    return ''

def _print_feature_tests(builder: Builder) -> None:
    """Print feature test results."""
    if not builder.feature_tests:
        return

    print("\nFeature Tests:")
    print("  " + "-" * 60)

    # Sort tests by duration (descending) then name
    sorted_tests = sorted(builder.feature_tests, key=lambda t: (-t.duration, t.variable))

    # Calculate padding for nice alignment
    max_name_len = max(len(test.variable) for test in builder.feature_tests)
    name_width = min(max(max_name_len + 2, 25), 40)

    # Print each test with its status and duration
    for test in sorted_tests:
        status = "available" if test.result else "not available"
        print(f"  {test.variable:<{name_width}} ... {status:<13} ({test.duration:.1f}s)")

    print("  " + "-" * 60)
    total_time = sum(test.duration for test in builder.feature_tests)
    print(f"  Total feature test time: {total_time:.1f}s")

if __name__ == '__main__':
    print("This module is not meant to be run directly. Import it and use make_dashboard() instead.") 
# Python Refactor Advisor Tool
"""
Refactor Advisor - An automated code analysis tool that provides refactoring suggestions.

This tool analyzes Python files in a given directory, breaks them into manageable chunks,
and uses Amazon Q CLI to provide refactoring suggestions.
"""

import argparse
import os
import subprocess
import sys
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import shutil
import textwrap


class ColorText:
    """Class to handle colored terminal output."""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

    @staticmethod
    def colorize(text: str, color: str) -> str:
        """Add color to text."""
        return f"{color}{text}{ColorText.ENDC}"


class RefactorAdvisor:
    """Main class for the Refactor Advisor tool."""

    def __init__(self, project_path: str, output_path: Optional[str] = None, chunk_size: int = 100):
        """
        Initialize the Refactor Advisor.

        Args:
            project_path: Path to the project directory to analyze
            output_path: Path to save analysis reports (optional)
            chunk_size: Number of lines per code chunk
        """
        self.project_path = os.path.abspath(project_path)
        self.output_path = output_path
        self.chunk_size = chunk_size
        
        if output_path:
            os.makedirs(output_path, exist_ok=True)

    def find_python_files(self) -> List[str]:
        """
        Find all Python files in the project directory.

        Returns:
            List of paths to Python files
        """
        python_files = []
        for root, _, files in os.walk(self.project_path):
            for file in files:
                if file.endswith('.py'):
                    python_files.append(os.path.join(root, file))
        return python_files

    def split_into_chunks(self, file_content: str) -> List[str]:
        """
        Split file content into chunks of specified size.

        Args:
            file_content: Content of the file to split

        Returns:
            List of code chunks
        """
        lines = file_content.splitlines()
        chunks = []
        
        for i in range(0, len(lines), self.chunk_size):
            chunk = '\n'.join(lines[i:i + self.chunk_size])
            chunks.append(chunk)
            
        return chunks

    def analyze_chunk(self, chunk: str, file_path: str, chunk_index: int) -> Dict[str, Any]:
        """
        Analyze a code chunk using Amazon Q CLI.

        Args:
            chunk: Code chunk to analyze
            file_path: Path to the source file
            chunk_index: Index of the chunk in the file

        Returns:
            Dictionary containing analysis results
        """
        prompt = f"""
        Analyze this Python code chunk (chunk {chunk_index + 1} from {file_path}):
        
        ```python
        {chunk}
        ```
        
        Please provide:
        1. A brief summary of what this code does
        2. Any code smells or anti-patterns you detect
        3. Specific refactoring suggestions with reasoning (based on DRY, SOLID, readability, performance)
        
        Format your response as JSON with these keys: "summary", "code_smells", "refactoring_suggestions"
        """
        
        try:
            # Try using AWS CLI v2 with Q functionality
            try:
                result = subprocess.run(
                    ["aws", "q", "cli", "--prompt", prompt, "--output", "json"],
                    capture_output=True,
                    text=True,
                    check=True
                )
            except (subprocess.SubprocessError, FileNotFoundError):
                # Fallback to direct Amazon Q CLI if available
                try:
                    result = subprocess.run(
                        ["amazon-q", "developer", "chat", "--prompt", prompt, "--output", "json"],
                        capture_output=True,
                        text=True,
                        check=True
                    )
                except (subprocess.SubprocessError, FileNotFoundError):
                    # If both fail, provide a mock response
                    print(f"  Warning: Could not connect to Amazon Q. Providing basic analysis.")
                    return self._generate_basic_analysis(chunk)
            
            # Parse the JSON response
            try:
                response = json.loads(result.stdout)
                # Extract the content from the response
                if isinstance(response, dict) and "content" in response:
                    content = response["content"]
                    # Try to extract JSON from the content
                    try:
                        # Find JSON content within the response
                        json_start = content.find('{')
                        json_end = content.rfind('}') + 1
                        if json_start >= 0 and json_end > json_start:
                            json_content = content[json_start:json_end]
                            analysis = json.loads(json_content)
                            return analysis
                    except json.JSONDecodeError:
                        pass
                
                # Fallback: return the raw content
                return {
                    "summary": "Failed to parse structured response",
                    "code_smells": [],
                    "refactoring_suggestions": [],
                    "raw_response": content
                }
            except json.JSONDecodeError:
                return {
                    "summary": "Failed to parse Amazon Q response",
                    "code_smells": [],
                    "refactoring_suggestions": [],
                    "raw_response": result.stdout
                }
                
        except subprocess.CalledProcessError as e:
            print(f"Error calling Amazon Q CLI: {e}")
            return self._generate_basic_analysis(chunk)
        except Exception as e:
            print(f"Unexpected error: {e}")
            return {
                "summary": "Unexpected error during analysis",
                "code_smells": [],
                "refactoring_suggestions": [],
                "error": str(e)
            }
    
    def _generate_basic_analysis(self, chunk: str) -> Dict[str, Any]:
        """
        Generate a basic analysis when Amazon Q is not available.
        
        Args:
            chunk: Code chunk to analyze
            
        Returns:
            Dictionary containing basic analysis results
        """
        # Count lines, imports, functions, and classes
        lines = chunk.split('\n')
        import_count = sum(1 for line in lines if line.strip().startswith('import ') or line.strip().startswith('from '))
        function_count = sum(1 for line in lines if line.strip().startswith('def '))
        class_count = sum(1 for line in lines if line.strip().startswith('class '))
        
        # Check for some basic code smells
        code_smells = []
        if len(lines) > 50 and function_count == 1:
            code_smells.append("Function might be too long (consider breaking it down)")
        
        if import_count > 15:
            code_smells.append("High number of imports (consider organizing imports or using dependency injection)")
        
        # Look for long lines
        long_lines = sum(1 for line in lines if len(line) > 100)
        if long_lines > 5:
            code_smells.append(f"Contains {long_lines} lines longer than 100 characters (consider breaking them for readability)")
        
        # Look for TODOs
        todos = sum(1 for line in lines if 'TODO' in line or 'FIXME' in line)
        if todos > 0:
            code_smells.append(f"Contains {todos} TODO/FIXME comments that should be addressed")
        
        # Generate suggestions
        suggestions = []
        if code_smells:
            suggestions.append("Consider addressing the identified code smells")
        
        if function_count > 5 and class_count == 0:
            suggestions.append("Consider grouping related functions into classes for better organization")
        
        return {
            "summary": f"This code chunk contains {len(lines)} lines with {import_count} imports, {function_count} functions, and {class_count} classes.",
            "code_smells": code_smells,
            "refactoring_suggestions": suggestions
        }

    def analyze_file(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Analyze a Python file by breaking it into chunks and analyzing each chunk.

        Args:
            file_path: Path to the Python file

        Returns:
            List of analysis results for each chunk
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            print(f"Error reading file {file_path}: {e}")
            return []

        chunks = self.split_into_chunks(content)
        results = []
        
        print(f"\nAnalyzing {file_path} ({len(chunks)} chunks)...")
        
        for i, chunk in enumerate(chunks):
            print(f"  Processing chunk {i+1}/{len(chunks)}...", end='', flush=True)
            result = self.analyze_chunk(chunk, file_path, i)
            results.append(result)
            print(" Done")
            
        return results

    def display_results(self, file_path: str, results: List[Dict[str, Any]]) -> None:
        """
        Display analysis results in the terminal.

        Args:
            file_path: Path to the analyzed file
            results: List of analysis results
        """
        rel_path = os.path.relpath(file_path, self.project_path)
        
        print("\n" + "=" * 80)
        print(ColorText.colorize(f"ANALYSIS RESULTS FOR: {rel_path}", ColorText.HEADER + ColorText.BOLD))
        print("=" * 80)
        
        for i, result in enumerate(results):
            print(f"\n{ColorText.colorize(f'CHUNK {i+1}:', ColorText.BOLD)}")
            
            # Display summary
            if "summary" in result:
                print(f"\n{ColorText.colorize('SUMMARY:', ColorText.BLUE + ColorText.BOLD)}")
                print(textwrap.fill(result["summary"], width=80))
            
            # Display code smells
            if "code_smells" in result and result["code_smells"]:
                print(f"\n{ColorText.colorize('CODE SMELLS:', ColorText.YELLOW + ColorText.BOLD)}")
                if isinstance(result["code_smells"], list):
                    for smell in result["code_smells"]:
                        if isinstance(smell, str):
                            print(f"• {smell}")
                        elif isinstance(smell, dict) and "description" in smell:
                            print(f"• {smell['description']}")
                else:
                    print(textwrap.fill(str(result["code_smells"]), width=80))
            
            # Display refactoring suggestions
            if "refactoring_suggestions" in result and result["refactoring_suggestions"]:
                print(f"\n{ColorText.colorize('REFACTORING SUGGESTIONS:', ColorText.GREEN + ColorText.BOLD)}")
                if isinstance(result["refactoring_suggestions"], list):
                    for suggestion in result["refactoring_suggestions"]:
                        if isinstance(suggestion, str):
                            print(f"• {suggestion}")
                        elif isinstance(suggestion, dict) and "description" in suggestion:
                            print(f"• {suggestion['description']}")
                else:
                    print(textwrap.fill(str(result["refactoring_suggestions"]), width=80))
            
            # Display raw response if structured parsing failed
            if "raw_response" in result:
                print(f"\n{ColorText.colorize('RAW RESPONSE:', ColorText.RED)}")
                print(textwrap.fill(result["raw_response"], width=80))
            
            print("\n" + "-" * 40)

    def save_markdown_report(self, file_path: str, results: List[Dict[str, Any]]) -> None:
        """
        Save analysis results to a markdown file.

        Args:
            file_path: Path to the analyzed file
            results: List of analysis results
        """
        if not self.output_path:
            return
            
        rel_path = os.path.relpath(file_path, self.project_path)
        # Fix the f-string backslash issue
        safe_filename = rel_path.replace('/', '_').replace('\\', '_')
        output_file = os.path.join(self.output_path, f"{safe_filename}.md")
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"# Refactoring Analysis: {rel_path}\n\n")
            
            for i, result in enumerate(results):
                f.write(f"## Chunk {i+1}\n\n")
                
                # Write summary
                if "summary" in result:
                    f.write("### Summary\n\n")
                    f.write(f"{result['summary']}\n\n")
                
                # Write code smells
                if "code_smells" in result and result["code_smells"]:
                    f.write("### Code Smells\n\n")
                    if isinstance(result["code_smells"], list):
                        for smell in result["code_smells"]:
                            if isinstance(smell, str):
                                f.write(f"- {smell}\n")
                            elif isinstance(smell, dict) and "description" in smell:
                                f.write(f"- {smell['description']}\n")
                    else:
                        f.write(f"{result['code_smells']}\n")
                    f.write("\n")
                
                # Write refactoring suggestions
                if "refactoring_suggestions" in result and result["refactoring_suggestions"]:
                    f.write("### Refactoring Suggestions\n\n")
                    if isinstance(result["refactoring_suggestions"], list):
                        for suggestion in result["refactoring_suggestions"]:
                            if isinstance(suggestion, str):
                                f.write(f"- {suggestion}\n")
                            elif isinstance(suggestion, dict) and "description" in suggestion:
                                f.write(f"- {suggestion['description']}\n")
                    else:
                        f.write(f"{result['refactoring_suggestions']}\n")
                    f.write("\n")
                
                # Write raw response if structured parsing failed
                if "raw_response" in result:
                    f.write("### Raw Response\n\n")
                    f.write("```\n")
                    f.write(f"{result['raw_response']}\n")
                    f.write("```\n\n")
                
                f.write("---\n\n")
        
        print(f"Report saved to: {output_file}")

    def run(self) -> None:
        """Run the Refactor Advisor tool."""
        # Check if Amazon Q CLI is installed
        has_amazon_q = self._check_amazon_q_cli()
        if not has_amazon_q:
            print(ColorText.colorize(
                "Warning: Amazon Q CLI is not installed or not in PATH. Using basic analysis mode.", 
                ColorText.YELLOW
            ))
            
        # Find Python files
        python_files = self.find_python_files()
        if not python_files:
            print("No Python files found in the specified directory.")
            return
            
        print(f"Found {len(python_files)} Python files to analyze.")
        
        # Analyze each file
        for file_path in python_files:
            results = self.analyze_file(file_path)
            self.display_results(file_path, results)
            
            if self.output_path:
                self.save_markdown_report(file_path, results)
    
    def _check_amazon_q_cli(self) -> bool:
        """
        Check if Amazon Q CLI is installed.
        
        Returns:
            True if installed, False otherwise
        """
        try:
            # Try direct Amazon Q CLI
            subprocess.run(
                ["amazon-q", "--version"], 
                capture_output=True, 
                check=False
            )
            return True
        except FileNotFoundError:
            try:
                # Try AWS CLI v2 with Q functionality
                result = subprocess.run(
                    ["aws", "--version"],
                    capture_output=True,
                    text=True,
                    check=False
                )
                # Check if it's AWS CLI v2
                if "aws-cli/2" in result.stdout:
                    try:
                        subprocess.run(
                            ["aws", "q", "help"],
                            capture_output=True,
                            check=False
                        )
                        return True
                    except:
                        pass
            except:
                pass
            
            return False


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Automated Code Refactor Advisor using Amazon Q CLI"
    )
    parser.add_argument(
        "--path", 
        type=str, 
        default=".", 
        help="Path to the project directory to analyze (default: current directory)"
    )
    parser.add_argument(
        "--output", 
        type=str, 
        help="Path to save analysis reports (optional)"
    )
    parser.add_argument(
        "--chunk-size", 
        type=int, 
        default=100, 
        help="Number of lines per code chunk (default: 100)"
    )
    
    args = parser.parse_args()
    
    # Create and run the advisor
    advisor = RefactorAdvisor(
        project_path=args.path,
        output_path=args.output,
        chunk_size=args.chunk_size
    )
    
    try:
        advisor.run()
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
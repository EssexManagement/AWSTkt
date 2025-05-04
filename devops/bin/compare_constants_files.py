#!/usr/bin/env python3

"""
    How to Run:
        python3    operations/bin/sync_constants_files.py     constants.py   ./api/runtime/constants.py

        ./constants.py
        ./backend/etl/runtime/constants.py
        ./api/runtime/constants.py
        ./api/runtime_report/src/constants.py

        ./operations/CDK/OperationsPrerequisites/constants.py  (this is a symlink to the reference file)
        ### ./api/runtime/common/constants.py     <--------- This is VERY DIFFERENT by design.  Do --NOT-- edit this file.


    Description:
        I have globally useful constants defined in multiple Python files.
        Due to human mistakes, the SEMANTIC-CONTENT of these files may drift apart.
        Specifically, we will focus on the 'global-constants' only and we will ignore the 'Functions' in these files.

        I'd like to do the following:
        1. Take EVERY SINGLE definition inside a Python constants file and create a JSON file
            using the "json.dumps(..., default=str, indent=4)" for each constant defined, where the JSON is sorted by key.
        2. Compare multiple constants files to identify differences between them.
"""

import os
import sys
import json
import importlib.util
from typing import Dict, Any, Optional

# Import our custom json utils
from common.json_utils import compare_two_files, sort_object_by_key

### ==============================================================================================
### ..............................................................................................
### ==============================================================================================

def extract_constants_from_module(module: Any) -> Dict[str, Any]:
    """
        Extract constants from a module, excluding functions

        Args:
            module: The imported module object

        Returns:
        Dictionary containing the module's constants
    """
    constants_dict = {}
    for key in dir(module):
        if (not key.startswith('_') and
            not callable(getattr(module, key)) and
            key != "PROJ_ROOT_FLDR_PATH"
        ):
            constants_dict[key] = getattr(module, key)
    return constants_dict

### ..............................................................................................

def extract_constants(file_path: str, dest_path: Optional[str] = None) -> str:
    """
        Extract constants from a Python file, sort that JSON, write it to a new file, and return the new file path

        Args:
            file_path: Path to the Python file containing constants
            dest_path: Optional custom output file path

        Returns:
            Path to the generated JSON file
    """
    print(f"Extracting constants from Python file: {file_path}")

    # Get absolute path
    resolved_path = os.path.abspath(file_path)

    # Check if file exists
    if not os.path.exists(resolved_path):
        print(f"Error: File not found: {resolved_path}")
        sys.exit(61)

    # Load the module dynamically
    module_name = os.path.basename(file_path).replace(".py", "")
    spec = importlib.util.spec_from_file_location(module_name, resolved_path)

    if spec is None:
        print(f"Error: Could not create spec for module: {module_name}")
        sys.exit(71)

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    # Extract and sort constants
    module_contents_dict = extract_constants_from_module(module)
    module_sorted_contents_dict = sort_object_by_key(module_contents_dict)

    # Determine output path
    if dest_path is None:
        base_name = os.path.basename(file_path).replace('.py', '')
        dirnm = os.path.dirname(file_path)
        # print( f"dirnm: '{dirnm}'")
        if dirnm == "":
            dirnm = "."
        dest_path = dirnm +f"/json-export-of_{base_name}.json"
    json_file_path = os.path.abspath(dest_path)

    # Write sorted constants to JSON file
    with open(json_file_path, 'w') as f:
        json.dump(module_sorted_contents_dict, f, indent=4, default=str)

    print(f"Constants extracted to: {json_file_path}")
    return json_file_path

### ==============================================================================================
### ..............................................................................................
### ==============================================================================================

def main():
    """ See header of this file for full documentation """
    # Check for command line arguments
    if len(sys.argv) <= 2:
        print(f"Usage: python {sys.argv[0]} <file1.py> [file2.py]")
        print(f"Example: python3 {sys.argv[0]}   constants.py   ./api/runtime/constants.py")
        sys.exit(1)

    file1 = sys.argv[1]
    file2 = sys.argv[2]

    # Check file extension
    if not file1.endswith('.py'):
        print(f"Error: File must be a Python file (*.py): {file1}")
        sys.exit(21)
    if not file2.endswith('.py'):
        print(f"Error: File must be a Python file (*.py): {file2}")
        sys.exit(41)


    json_file_path1 = extract_constants(file1)
    json_file_path2 = extract_constants(file2)
    compare_two_files(json_file_path1, json_file_path2)

if __name__ == "__main__":
    main()

### EoF

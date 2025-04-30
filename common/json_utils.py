import json
from typing import Dict, Any, Set, List

### ..............................................................................................

def sort_object_by_key(obj: Dict[str, Any]) -> Dict[str, Any]:
    """
        Sort an object's keys alphabetically

        Args:
            obj: Dictionary to sort

        Returns:
            New dictionary with sorted keys
    """
    return {key: obj[key] for key in sorted(obj.keys())}

### ==============================================================================================
### ..............................................................................................
### ==============================================================================================

def compare_two_files(
    reference_json_file_path: str,
    any_json_file_path: str,
    debug: bool = False
) -> None:
    """
        Compare two JSON files containing constants and report differences

        Args:
            reference_json_file_path: Path to the first JSON file
            any_json_file_path: Path to the second JSON file
            debug: Whether to output detailed debugging information
    """
    if debug:
        print(f"Comparing:\n - {reference_json_file_path}\n - {any_json_file_path}")

    try:
        with open(reference_json_file_path, 'r') as f:
            reference_json = json.load(f)

        with open(any_json_file_path, 'r') as f:
            any_json = json.load(f)

        ref_json_keys = set(reference_json.keys())
        any_json_keys = set(any_json.keys())

        has_differences = False

        # Find keys that exist in file1 but not in file2
        unique_reference_keys = [key for key in ref_json_keys if key not in any_json_keys]
        if unique_reference_keys:
            print("\033[33m\nConstants in input-file but missing in Reference-file\033[0m")
            for key in unique_reference_keys:
                print(f" - {key}: {json.dumps(reference_json[key])}")

        # Find keys that exist in file2 but not in file1
        unique_keys = [key for key in any_json_keys if key not in ref_json_keys]
        if unique_keys:
            has_differences = True
            print("\033[33m\nConstants in Reference-file are missing in input-file:\033[0m")
            for key in unique_keys:
                print(f" - {key}: {json.dumps(any_json[key])}")

        # Check for different values for the same keys
        different_values: List[str] = []

        for key in ref_json_keys:
            if key in any_json_keys:
                reference_value = reference_json[key]
                input_json_value = any_json[key]

                # Deep compare values to handle arrays and objects
                if json.dumps(reference_value) != json.dumps(input_json_value):
                    has_differences = True
                    different_values.append(key)

        if len(different_values) <= 0 and len(unique_reference_keys) <= 0:
            print("\033[32mAll constants match perfectly between the two files!\n\n\033[0m")
        else:
            print("\033[33m❌Constants are different!\033[0m")

            if not debug:
                s = json.dumps(different_values, indent=4)
                # if s > 10 lines, then truncate it
                lines = s.split('\n')
                if len(lines) > 10:
                    print('\n'.join(lines[:10]))
                    print(f"... and {len(lines) - 10} more lines")
                else:  # else, just print it
                    print(s)
            else:
                max_10_different_values = different_values[:10]
                for key in max_10_different_values:
                    print(f"  - {key}:")
                    print(f"    Refrnc Value: {json.dumps(reference_json[key])}")
                    print(f"    Other  Value: {json.dumps(any_json[key])}")

    except Exception as error:
        print(f"Error comparing files: {error}")

### EoF

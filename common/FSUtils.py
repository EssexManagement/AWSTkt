import os
import pathlib
import hashlib
from typing import Union, TypeVar

PathLike = TypeVar('PathLike', str, pathlib.PurePath)

### ==============================================================================================
### ..............................................................................................
### ==============================================================================================

def is_valid_directory(pth: PathLike) -> bool:
    """
    Check if a path represents a valid directory.

    Args:
        pth: Path-like object or string representing the path

    Returns:
        bool: True if path is a valid directory, False otherwise
    """
    try:
        path_str = str(pth)
        return os.path.isdir(path_str)
    except Exception:
        return False

### ..............................................................................................

def is_valid_file(pth: PathLike) -> bool:
    """
    Check if a path represents a valid file.

    Args:
        pth: Path-like object or string representing the path

    Returns:
        bool: True if path is a valid file, False otherwise
    """
    try:
        path_str = str(pth)
        return os.path.isfile(path_str)
    except Exception:
        return False

# Example usage:
# dir_path = pathlib.PurePath('/Users/test/LocalDevelopment/AWS/CDK/cdk-ApiGW-λ-TypeScript')
# file_path = pathlib.PurePath('/Users/test/LocalDevelopment/AWS/CDK/cdk-ApiGW-λ-TypeScript/src/index.ts')
# print(is_valid_directory(dir_path))  # Outputs: True or False
# print(is_valid_file(file_path))      # Outputs: True or False

### ..............................................................................................


def assert_not_newer_than(
    myfile :pathlib.Path,
    newer_than_this: pathlib.Path,
    ignore_missing_files :bool = False,
):
    """
    Verifies that Pipfile has not been modified more recently than Pipfile.lock.
    This helps prevent deploying with outdated dependencies.
    Please run 'pipenv lock --dev --python ${PYTHON_VERSION} --clear'.
    Please run 'python -m piptools compile  --quiet requirements.in'.

    Args:
        myfile: The file whose timestamp matters.
        newer_than_this: the REFERENCE file against which we compare timestamps
        ignore_missing_files: if either file is missing, and this param is TRUE, an exception is raised

    Raises:
        FileNotFoundError: If either Pipfile or Pipfile.lock is missing
        RuntimeError: If Pipfile is newer than Pipfile.lock
    """
    myfile = pathlib.Path('Pipfile')
    newer_than_this = pathlib.Path('Pipfile.lock')

    # Check if both files exist
    if ignore_missing_files:
        if not myfile.exists():
            return
        if not newer_than_this.exists():
            return
    else:
        if not myfile.exists():
            raise FileNotFoundError( f"{myfile} not found" )
        if not newer_than_this.exists():
            raise FileNotFoundError( f"{newer_than_this} not found" )

    # Get modification timestamps
    myfile_mtime = os.path.getmtime(myfile)
    compare_to_mtime = os.path.getmtime(newer_than_this)

    # Compare timestamps
    if myfile_mtime > compare_to_mtime:
        raise RuntimeError(
            f"{myfile} is newer than {newer_than_this}! "
        )


### ==============================================================================================
### ..............................................................................................
### ==============================================================================================

def join_path(lhs: PathLike, rhs: PathLike) -> pathlib.PurePath:
    """
    Join two paths together.

    Args:
        lhs: Left-hand path component
        rhs: Right-hand path component

    Returns:
        pathlib.PurePath: Combined path object
    """
    return pathlib.PurePath(str(lhs)) / str(rhs)

### ==============================================================================================
### ..............................................................................................
### ==============================================================================================

def get_sha_hash_for_file(req_file_path: PathLike) -> str:
    """
    Calculate SHA256 hash of a file's contents.
    Meant to be used for generating a custom-hash for the Lambda code/Lambda-layer code.

    Args:
        req_file_path: Path to the file

    Returns:
        str: Hexadecimal representation of the SHA256 hash

    Raises:
        ValueError: If the file is not found or cannot be read
    """
    path_str = str(req_file_path)

    ### Check if requirements.txt exists
    if not is_valid_file(path_str):
        raise ValueError(f"!! ERROR !! file '{path_str}' not found!")

    sha256_hash = hashlib.sha256()

    ### Per CDK's aws_lambda.Code.from_asset(..)
    ###    this custom hash will be SHA256 hashed and encoded as hex.
    with open(path_str, 'rb') as f:
        # Read the file in chunks to handle large files efficiently
        for chunk in iter(lambda: f.read(4096), b''):
            sha256_hash.update(chunk)

    return sha256_hash.hexdigest()


### ..............................................................................................

def getSHAHashForFile2(
   fldrPath :Union[pathlib.Path,str],
   simpleFilename :str,
) -> str:
    """
    * Polymorphic function to get the SHA256 hash given a folder-path that contains a simple-filename.
    * This invokes the `getSHAHashForFile(..)` function, after combining the `fldrPath` and `simpleFileName`.
    * @param fldrPath - can be a string or a Path.ParsedPath object, can be invalid-path.
    * @returns a SHA256 hash of the file contents.
    * @throws Error if the file is not found.
    """
    if type(fldrPath) == str:
        fldrPath = pathlib.Path(fldrPath)
    reqFilePath = join_path( lhs = fldrPath, rhs = simpleFilename )

    ### Check if requirements.txt exists
    if ( not is_valid_file(reqFilePath) ):
        raise RuntimeError( f"!! ERROR !! file '${simpleFilename}' not found inside Folder: '${fldrPath}'." )

    return get_sha_hash_for_file( reqFilePath )

### ==============================================================================================
### ..............................................................................................
### ==============================================================================================

### EoF


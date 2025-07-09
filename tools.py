import os
import re
import time
import functools
from langchain.tools import Tool
from langchain_core.tools import tool

def tool_logger(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        args_repr = [repr(a) for a in args]
        kwargs_repr = [f"{k}={v!r}" for k, v in kwargs.items()]
        signature = ", ".join(args_repr + kwargs_repr)
        print(f"Calling tool: {func.__name__}({signature})")
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            end_time = time.time()
            print(f"Tool {func.__name__} executed successfully in {end_time - start_time:.2f} seconds.")
            return result
        except Exception as e:
            end_time = time.time()
            print(f"Tool {func.__name__} failed after {end_time - start_time:.2f} seconds with error: {e}")
            raise
    return wrapper

@tool
@tool_logger
def list_files_in_repository(repo: str) -> list[str]:
    """
    Lists all files in a given repository directory recursively.

    Returns:
        list: A list of file paths relative to the repository root, or an error message.
    """
    repo_path = f"/Users/jannik/Lokale-Dokumente/University/Msc/ASE/repos/{repo}"
    try:
        if not os.path.exists(repo_path):
            return [f"Error: Repository path '{repo_path}' does not exist."]

        file_list = []
        for root, _, files in os.walk(repo_path):
            for file in files:
                # Construct the relative file path
                relative_path = os.path.relpath(os.path.join(root, file), repo_path)
                file_list.append(relative_path)

        return file_list
    except Exception as e:
        return [f"Error: An error occurred while listing files: {e}"]


@tool
@tool_logger
def get_file_content(file_path: str, repo: str) -> str:
    """
    Reads the content of a file and returns it as a string. Always provide the base repo.

    Args:
        repo (str): The name of the repository (e.g. repo_1, repo_2)
        file_path (str): Path to the file to be read.

    Returns:
        str: Content of the file or an error message.
    """
    file_path = f"/Users/jannik/Lokale-Dokumente/University/Msc/ASE/repos/{repo}/{file_path}"
    try:
        with open(file_path, "r") as file:
            return file.read()
    except FileNotFoundError:
        return f"Error: File '{file_path}' not found."
    except Exception as e:
        return f"Error: An error occurred while reading the file: {e}"


@tool
@tool_logger
def overwrite_file(repository_name: str, file_path: str, content: str) -> str:
    """
    Create a new File with content or Overwrite an existing file with new content.
    
    Args:
        repository_name (str): The name of the repository (e.g. repo_1, repo_2)
        file_path (str): Path to the file.
        content (str): Content to write or append (default: "").
        
    Returns:
        str: Result of the operation or the content of the file.
    """
    file_path = f"/Users/jannik/Lokale-Dokumente/University/Msc/ASE/repos/{repository_name}/{file_path}"
    try:
        with open(file_path, "w") as file:
            file.write(content)
        return f"File {file_path} written successfully."
    except Exception as e:
        return f"An error occurred while writing to the file: {e}"


@tool
@tool_logger
def find_and_replace(repository_name: str, file_path: str, pattern: str, replacement: str) -> str:
    """
    Allows to use search and replace writing operations via Regex expressions.

    Args:
        repository_name (str): The name of the repository (e.g. repo_1, repo_2)
        file_path (str): Path to the file.
        pattern (str): The regex pattern to replace.
        replacement (str): Content to replace the pattern with.

    Returns:
        str: Result of the operation or the content of the file.
    """
    file_path = f"/Users/jannik/Lokale-Dokumente/University/Msc/ASE/repos/{repository_name}/{file_path}"

    print(f"[DEBUG] Starting find_and_replace operation.")
    print(f"[DEBUG] Repository Name: {repository_name}")
    print(f"[DEBUG] File Path: {file_path}")
    print(f"[DEBUG] Regex Pattern: {pattern}")
    print(f"[DEBUG] Replacement String: {replacement}")

    try:
        # Read the file content
        print(f"[DEBUG] Attempting to read file: {file_path}")
        with open(file_path, "r", encoding="utf-8") as file:
            content = file.read()
        print(f"[DEBUG] File content successfully read. Content length: {len(content)} characters.")

        # Apply the regex replacement
        print(f"[DEBUG] Applying regex replacement...")
        modified_content = re.sub(rf"{pattern}", rf"{replacement}", content)
        print(f"[DEBUG] Regex replacement applied. Modified content length: {len(modified_content)} characters.")

        # Debug: Print a snippet of the modified content
        print(f"[DEBUG] Modified Content Snippet:\n{modified_content}...")

        # Write the modified content back to the file
        print(f"[DEBUG] Writing modified content back to file: {file_path}")
        with open(file_path, "w", encoding="utf-8") as file:
            file.write(modified_content)
        print(f"[DEBUG] File successfully updated.")

        return f"FIND AND REPLACE in {file_path} successful!"
    except FileNotFoundError:
        error_message = f"[ERROR] File not found: {file_path}"
        print(error_message)
        return error_message
    except Exception as e:
        error_message = f"[ERROR] An error occurred during find and replace: {e}"
        print(error_message)
        return error_message
@tool
@tool_logger
def delete_lines(repository_name: str, file_path: str, start_line: int, end_line: int) -> None:
    """
    Delete a range of lines from a file.

    Parameters:
        repository_name (str): The name of the repository (e.g. repo_1, repo_2)
        file_path (str): Path to the target file.
        start_line (int): The starting line number (1-based index) of the range to delete.
        end_line (int): The ending line number (inclusive, 1-based index) of the range to delete.

    Raises:
        ValueError: If start_line or end_line are out of bounds or invalid.
        IOError: If the file cannot be read or written.
    """
    if start_line == 0:
        start_line += 1
    if end_line == 0:
        end_line += 1
    file_path = f"/Users/jannik/Lokale-Dokumente/University/Msc/ASE/repos/{repository_name}/{file_path}"
    with open(file_path, 'r', encoding='utf-8') as file:
        lines = file.readlines()

    if start_line < 1 or end_line > len(lines) or start_line > end_line:
        raise ValueError("Invalid line range specified.")

    del lines[start_line - 1:end_line]

    with open(file_path, 'w', encoding='utf-8') as file:
        file.writelines(lines)


@tool
@tool_logger
def insert_at_line(repository_name: str, file_path: str, line_number: int, content: str) -> None:
    """
    Insert a line of text at a specific position in a file.

    Parameters:
        repository_name (str): The name of the repository (e.g. repo_1, repo_2)    
        file_path (str): Path to the target file.
        line_number (int): The line number (1-based index) at which to insert the new content.
        content (str): The content to insert into the file.

    Raises:
        ValueError: If line_number is out of bounds.
        IOError: If the file cannot be read or written.
    """
    if line_number == 0:
        line_number += 1
    file_path = f"/Users/jannik/Lokale-Dokumente/University/Msc/ASE/repos/{repository_name}/{file_path}"
    with open(file_path, 'r', encoding='utf-8') as file:
        lines = file.readlines()

    if line_number < 1 or line_number > len(lines) + 1:
        raise ValueError("Invalid line number specified.")

    lines.insert(line_number - 1, content + '\n')

    with open(file_path, 'w', encoding='utf-8') as file:
        file.writelines(lines)


@tool
@tool_logger
def replace_lines(repository_name: str, file_path: str, start_line: int, end_line: int, new_content: list[str]) -> None:
    """
    Replace a range of lines in a file with new content.

    Parameters:
        repository_name (str): The name of the repository (e.g. repo_1, repo_2)    
        file_path (str): Path to the target file.
        start_line (int): The starting line number (1-based index) of the range to replace.
        end_line (int): The ending line number (inclusive, 1-based index) of the range to replace.
        new_content (list[str]): A list of strings to replace the specified lines.

    Raises:
        ValueError: If start_line or end_line are out of bounds or invalid.
        IOError: If the file cannot be read or written.
    """
    if start_line == 0:
        start_line += 1
    if end_line == 0:
        end_line += 1

    file_path = f"/Users/jannik/Lokale-Dokumente/University/Msc/ASE/repos/{repository_name}/{file_path}"
    with open(file_path, 'r', encoding='utf-8') as file:
        lines = file.readlines()

    if start_line < 1 or end_line > len(lines) or start_line > end_line:
        raise ValueError("Invalid line range specified.")

    lines[start_line - 1:end_line] = [line + '\n' if not line.endswith('\n') else line for line in new_content]

    with open(file_path, 'w', encoding='utf-8') as file:
        file.writelines(lines)


tools = [
    list_files_in_repository,
    get_file_content,
    # overwrite_file,
    find_and_replace,
    delete_lines,
    insert_at_line,
    replace_lines
]

read_tools = [
    list_files_in_repository,
    get_file_content
]

read_write_tools = [
    find_and_replace,
    list_files_in_repository,
    get_file_content
]




def get_tools():
    return tools
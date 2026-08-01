```markdown
# DuckTap Development Patterns

> Auto-generated skill from repository analysis

## Overview
This skill teaches the core development conventions and workflows found in the DuckTap Python repository. You'll learn about the project's file organization, code style, commit patterns, and how to write and run tests following the repository's standards. Whether you're contributing code or reviewing pull requests, this guide ensures consistency and quality across the codebase.

## Coding Conventions

### File Naming
- Use `snake_case` for all file names.
  - **Example:**  
    ```plaintext
    data_processor.py
    utils/helper_functions.py
    ```

### Import Style
- Use **relative imports** within the package.
  - **Example:**  
    ```python
    from .utils import helper_function
    from ..models import DataModel
    ```

### Export Style
- Use **named exports** for functions, classes, and variables.
  - **Example:**  
    ```python
    def process_data(data):
        ...

    class DataHandler:
        ...
    ```

### Commit Patterns
- Follow **conventional commit** messages.
- Use prefixes like `fix` or `docs`.
- Keep commit messages concise (average ~67 characters).
  - **Examples:**  
    ```
    fix: handle empty input in data_processor
    docs: update README with usage instructions
    ```

## Workflows

### Writing a Fix
**Trigger:** When you need to resolve a bug or issue in the codebase  
**Command:** `/fix`

1. Identify the bug or issue.
2. Create a new branch for your fix.
3. Make code changes following the coding conventions.
4. Write a commit message starting with `fix:`.
5. Submit a pull request for review.

### Updating Documentation
**Trigger:** When documentation needs to be added or improved  
**Command:** `/docs`

1. Edit or add documentation files (e.g., `README.md`, inline docstrings).
2. Use clear, concise language.
3. Commit your changes with a message starting with `docs:`.
4. Submit a pull request for review.

## Testing Patterns

- Test files use the pattern `*.test.*` (e.g., `data_processor.test.py`).
- The specific testing framework is not specified; use standard Python testing practices.
- Place tests alongside the modules they test or in a dedicated `tests/` directory.
- Example test file:
  ```python
  # data_processor.test.py
  from .data_processor import process_data

  def test_process_data_handles_empty():
      assert process_data([]) == []
  ```

## Commands
| Command | Purpose |
|---------|---------|
| /fix    | Start a bug fix workflow |
| /docs   | Start a documentation update workflow |
```

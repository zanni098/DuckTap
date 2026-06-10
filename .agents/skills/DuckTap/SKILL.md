```markdown
# DuckTap Development Patterns

> Auto-generated skill from repository analysis

## Overview
This skill teaches the core development patterns and conventions used in the DuckTap Python codebase. DuckTap is a Python project with no detected framework, focusing on clean code organization, consistent naming, and modular exports. This guide covers file naming, import/export styles, commit message conventions, and testing patterns to help you contribute effectively.

## Coding Conventions

### File Naming
- Use **camelCase** for all file names.
  - Example: `dataProcessor.py`, `userManager.py`

### Import Style
- Use **relative imports** within the codebase.
  - Example:
    ```python
    from .utilities import parseData
    from .models.user import User
    ```

### Export Style
- Use **named exports** by explicitly listing what is exported from each module.
  - Example:
    ```python
    # In userManager.py
    class UserManager:
        pass

    __all__ = ['UserManager']
    ```

### Commit Message Patterns
- Commit types are **mixed**, with common prefixes like `chore` and `quality`.
- Keep commit messages concise (average 53 characters).
  - Example: `chore: update requirements for security patch`

## Workflows

### Code Quality Improvements
**Trigger:** When you want to improve code quality, refactor, or clean up.
**Command:** `/quality-improvement`

1. Identify areas for code quality improvement (e.g., refactoring, linting).
2. Make changes following the coding conventions above.
3. Use a commit message prefix `quality:`.
4. Push your changes and open a pull request.

### Dependency or Maintenance Tasks
**Trigger:** When updating dependencies or performing routine maintenance.
**Command:** `/chore-update`

1. Update dependencies or perform maintenance tasks.
2. Ensure all changes follow the codebase conventions.
3. Use a commit message prefix `chore:`.
4. Push your changes and open a pull request.

## Testing Patterns

- Test files use the pattern `*.test.*` (e.g., `userManager.test.py`).
- The testing framework is **unknown**, so check existing test files for structure.
- Place tests alongside or near the modules they test.
- Example test file:
  ```python
  # userManager.test.py
  from .userManager import UserManager

  def test_user_creation():
      manager = UserManager()
      assert manager.create_user("test") is not None
  ```

## Commands
| Command               | Purpose                                           |
|-----------------------|---------------------------------------------------|
| /quality-improvement  | Start a code quality improvement workflow         |
| /chore-update         | Begin a dependency or maintenance update workflow |
```

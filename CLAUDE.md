# CLAUDE.md

## Project Overview
SmartStock - Python stock analysis project.

## Core Principles

### Minimize Changes
- Always prefer editing existing files over creating new ones
- Make the smallest possible diff to achieve the goal
- Avoid refactoring unrelated code during a fix or feature task
- If unsure, read the codebase first instead of guessing patterns

## Code Style

- Comments in English only
- Prefer functional programming over OOP
- Use OOP only for connectors and interfaces to external systems
- Write pure functions - only modify return values, never input parameters or global state
- Follow DRY, KISS, and YAGNI principles
- Use strict typing everywhere - function returns, variables, collections
- Avoid untyped variables and generic types like `Any` or `Dict[str, Any]`
- Never use default parameter values - make all parameters explicit
- Create proper type definitions (dataclasses, TypedDict, Pydantic models) for complex data structures
- All imports at the top of the file
- Write simple single-purpose functions - no multi-mode behavior, no flag parameters

## Error Handling

- Always raise errors explicitly, never silently ignore them
- Use specific error types that clearly indicate what went wrong
- Avoid catch-all exception handlers (`except Exception`) that hide root cause
- Error messages should be clear and actionable
- No fallbacks unless explicitly requested
- Fix root causes, not symptoms
- External API/service calls: use retries with warnings, then raise the last error
- Error messages must include context: request params, response body, status codes
- Use structured logging fields, not string interpolation in log messages

## Python Specifics

- Prefer structured data models (dataclasses, Pydantic) over loose dictionaries
- Use `pyproject.toml` for project configuration and dependencies
- Use modern Python features: type hints, f-strings, walrus operator where appropriate
- Install dependencies in project virtual environments, not globally
- Add dependencies to `pyproject.toml`, not as one-off manual installs

## Testing

- Respect the existing test strategy and test suite
- Do not add new unit tests by default
- Prefer integration/end-to-end tests that validate real behavior
- Use unit tests only for stable pure data transformations
- Never add tests just to increase coverage
- Avoid mocks when real calls are practical
- Add only the minimum test coverage needed for the requested change

## Terminal Usage

- Prefer non-interactive commands with flags
- Use `git --no-pager diff` or `git diff | cat` for git diffs
- Prefer `rg` (ripgrep) for searching code and files

## Workflow

- Read existing code and relevant files before editing
- Keep changes minimal and focused on the current request
- Match the existing style of the repository
- Do not revert unrelated changes
- If unsure, inspect the codebase instead of inventing patterns
- Run lint/test commands before finishing if the task changed code

## Documentation

- Code is the primary documentation - use clear naming, types, and docstrings
- Keep docs in docstrings of the functions/classes they describe, not separate files
- Never duplicate documentation across files

## Commits

- Never create a git commit unless explicitly asked
- Prefer `git merge` over `git squash` unless explicitly requested
- Keep changes uncommitted until asked, so the diff stays clean and reviewable

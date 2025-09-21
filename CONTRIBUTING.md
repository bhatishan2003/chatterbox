# Contributing

Thank you for considering contributing! 🎉
Please follow these steps to set up your development environment and keep contributions consistent.

## Development Notes

- For development (editable mode), do following installation:

  - Core only:

    ```bash
    pip install -e .
    ```

  - With tests:
    ```bash
    pip install -e .[test]
    ```
  - With dev tools:

    ```bash
    pip install -e .[dev]
    ```

  - All dependencies (test + dev):
    ```bash
    pip install -e .[all]
    ```

- Pre-commit

  We use pre-commit to automate linting of our codebase.

  - Install hooks:
    ```bash
    pre-commit install
    ```
  - Run Hooks manually (optional):
    ```bash
    pre-commit run --all-files
    ```

- Ruff:

  - Lint and format:
    ```bash
    ruff check --fix
    ruff format
    ```

## Testing

Run following command to check test cases.

```bash
pip install -e .[test]
pytest -v
```

## Versioning

We use [bump-my-version](https://github.com/callowayproject/bump-my-version) to manage version numbers consistently.

### Install

```bash
pip install .[dev]
```

### Bump Version Options

- Patch (bug fixes, backward compatible):

  ```bash
  bump-my-version bump patch
  ```

- Minor (new features, backward compatible):

  ```bash
  bump-my-version bump minor
  ```

- Major (breaking changes):

  ```bash
  bump-my-version bump major
  ```

### Check Current Version

```bash
bump-my-version bump show
```

### Recommended Workflow

- Run tests and linting.
- Bump the version (patch/minor/major).
- Push to git:

  ```bash
  git push --follow-tags
  ```

## Release Notes

- Always run test cases.
- Install twine/build dependancies
  ```bash
  python -m pip install --upgrade build twine
  ```
- Build
  ```bash
  python -m build
  ```
- Upload
  ```bash
  python -m twine upload dist/*
  ```

# Contributing to zone-new-companion

Thank you for your interest in contributing to zone-new-companion! This document provides guidelines and information for contributors.

## 🤝 How to Contribute

### Reporting Issues

1. **Search Existing Issues**: Check if the issue already exists
2. **Create New Issue**: Use the appropriate issue template
3. **Provide Details**: Include steps to reproduce, expected behavior, and environment
4. **Add Screenshots**: If applicable, add screenshots to help explain the issue

### Suggesting Features

1. **Check Roadmap**: Review the project roadmap for planned features
2. **Create Discussion**: Start a discussion in the "Ideas" category
3. **Provide Use Case**: Explain the problem you're trying to solve
4. **Consider Implementation**: Think about how the feature could be implemented

### Code Contributions

1. **Fork Repository**: Fork the project to your GitHub account
2. **Create Branch**: Create a feature branch from `main`
3. **Make Changes**: Implement your changes following the coding standards
4. **Test Changes**: Ensure your changes work as expected
5. **Submit Pull Request**: Create a pull request with detailed description

## 🛠️ Development Setup

### Prerequisites

- Python 3.8 or higher
- Git
- VLC media player
- FFmpeg (for OCR functionality)
- Tesseract OCR (for OCR functionality)

### Setup Steps

1. **Clone Repository**
   ```bash
   git clone https://github.com/kidpoleon/zone-new-companion.git
   cd zone-new-companion
   ```

2. **Create Virtual Environment**
   ```bash
   python3 -m venv dev-env
   source dev-env/bin/activate  # Linux/macOS
   # or dev-env\Scripts\activate  # Windows
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt  # if available
   ```

4. **Install Pre-commit Hooks** (if configured)
   ```bash
   pre-commit install
   ```

5. **Run Tests**
   ```bash
   python -m pytest
   ```

6. **Run Application**
   ```bash
   python main.py
   ```

## 📝 Coding Standards

### Python Style

- Follow PEP 8 style guidelines
- Use 4 spaces for indentation
- Maximum line length: 88 characters (Black formatter)
- Use type hints where appropriate
- Add docstrings to all public functions and classes

### Code Organization

```
zone_new_companion/
├── __init__.py          # Package initialization
├── app.py              # Application entry point
├── config.py           # Configuration management
├── models.py           # Data models
├── state.py            # State management
├── controllers/        # Business logic
├── services/           # External services
├── ui/                 # User interface
└── workers/            # Background tasks
```

### Naming Conventions

- **Classes**: `PascalCase` (e.g., `StreamVerifier`)
- **Functions/Methods**: `snake_case` (e.g., `verify_stream`)
- **Variables**: `snake_case` (e.g., `stream_url`)
- **Constants**: `UPPER_SNAKE_CASE` (e.g., `DEFAULT_TIMEOUT`)
- **Private Members**: Prefix with `_` (e.g., `_session`)

### Documentation

- Add docstrings to all public functions and classes
- Use Google-style docstrings
- Include parameter types and return types
- Add examples for complex functions

```python
def verify_stream_url(self, stream_url: str, timeout: float = 10.0) -> bool:
    """Verify if a stream URL is accessible and contains valid content.
    
    Args:
        stream_url: The URL of the stream to verify.
        timeout: Maximum time to wait for response in seconds.
        
    Returns:
        True if the stream is accessible and valid, False otherwise.
        
    Example:
        >>> verifier = StreamVerifier()
        >>> result = verifier.verify_stream_url("http://example.com/stream.m3u8")
        >>> print(result)
        True
    """
    pass
```

## 🧪 Testing

### Running Tests

```bash
# Run all tests
python -m pytest

# Run with coverage
python -m pytest --cov=zone_new_companion

# Run specific test file
python -m pytest tests/test_stream_verifier.py

# Run with verbose output
python -m pytest -v
```

### Writing Tests

- Write unit tests for all new functionality
- Use descriptive test names
- Test both success and failure cases
- Mock external dependencies when appropriate
- Aim for high code coverage

### Test Structure

```
tests/
├── __init__.py
├── test_stream_verifier.py
├── test_m3u_service.py
├── test_xtream_service.py
├── test_stalker_service.py
└── conftest.py
```

## 📋 Pull Request Process

### Before Submitting

1. **Update Documentation**: Update README if needed
2. **Add Tests**: Ensure new code is tested
3. **Run Tests**: Make sure all tests pass
4. **Format Code**: Use Black formatter
5. **Check Linting**: Use flake8 or similar tool
6. **Update Changelog**: Add entry to CHANGELOG.md

### Pull Request Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] All tests pass
- [ ] New tests added
- [ ] Manual testing completed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] Changelog updated
```

### Review Process

1. **Automated Checks**: CI/CD pipeline runs tests and checks
2. **Code Review**: Maintainer reviews code for quality and correctness
3. **Testing**: Changes are tested on multiple platforms if applicable
4. **Approval**: Maintainer approves and merges the PR

## 🐛 Bug Reports

### Bug Report Template

```markdown
**Describe the Bug**
Clear description of the bug

**To Reproduce**
Steps to reproduce the behavior:
1. Go to '...'
2. Click on '....'
3. Scroll down to '....'
4. See error

**Expected Behavior**
What you expected to happen

**Screenshots**
Add screenshots if applicable

**Environment**
- OS: [e.g. Windows 11, Ubuntu 22.04]
- Python version: [e.g. 3.9.0]
- App version: [e.g. 1.1.4]
- VLC version: [e.g. 3.0.18]

**Additional Context**
Any other relevant information
```

## 💡 Feature Requests

### Feature Request Template

```markdown
**Feature Description**
Clear description of the feature

**Problem Statement**
What problem does this feature solve?

**Proposed Solution**
How do you envision this feature working?

**Alternatives Considered**
What other approaches did you consider?

**Additional Context**
Any other relevant information
```

## 🏆 Recognition

Contributors will be recognized in:

- README.md contributors section
- Release notes for significant contributions
- Special thanks in major releases

## 📞 Getting Help

- **Discussions**: Use GitHub Discussions for questions
- **Issues**: Use GitHub Issues for bugs and feature requests
- **Discord**: Join our Discord server (if available)
- **Email**: Contact maintainers directly for sensitive issues

## 📄 License

By contributing to this project, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing to zone-new-companion! 🎉

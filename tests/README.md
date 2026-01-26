# Test Suite

## Overview

Comprehensive test suite for the AI Chess Game Review Coach MVP.

## Test Structure

```
tests/
├── __init__.py
├── conftest.py              # Pytest fixtures and configuration
├── test_pgn_service.py      # PGN parsing and validation tests
├── test_move_classification.py  # Move classification logic tests
├── test_accuracy_rating.py  # Accuracy and rating calculation tests
├── test_models.py          # Database model tests
├── test_api_games.py       # Game API endpoint tests
├── test_api_chat.py        # Chat API endpoint tests
├── test_api_status.py      # Status and health endpoint tests
└── test_validation.py      # Input validation and error handling tests
```

## Running Tests

### Run All Tests
```bash
pytest
```

### Run Specific Test File
```bash
pytest tests/test_pgn_service.py
```

### Run Specific Test
```bash
pytest tests/test_pgn_service.py::test_parse_pgn
```

### Run with Coverage
```bash
pytest --cov=app --cov-report=html
```

### Run with Verbose Output
```bash
pytest -v
```

## Test Categories

### Unit Tests
- **PGN Service**: Parsing, validation, metadata extraction
- **Move Classification**: Classification logic for different move qualities
- **Accuracy Rating**: Accuracy calculation and rating estimation
- **Models**: Database model creation and relationships

### Integration Tests
- **API Games**: Game upload, retrieval, analysis endpoints
- **API Chat**: Chat functionality and history
- **API Status**: Health checks and system status

### Validation Tests
- **Input Validation**: Pydantic schema validation
- **Error Handling**: Error response formats

## Test Fixtures

### Database Fixtures
- `test_db`: In-memory SQLite database for each test
- `client`: FastAPI test client

### Data Fixtures
- `sample_pgn`: Full sample PGN game
- `sample_pgn_minimal`: Minimal PGN for quick tests
- `invalid_pgn`: Invalid PGN for error testing

### Mock Fixtures
- `mock_redis`: Mock Redis client

## Test Configuration

Configuration is in `pytest.ini`:
- Test paths: `tests/`
- Coverage: Enabled with HTML reports
- Markers: `unit`, `integration`, `slow`, `requires_stockfish`, `requires_llm`, etc.

## Test Environment

Tests use:
- **SQLite in-memory database** for fast, isolated tests
- **Test client** for API endpoint testing
- **Mock services** where external dependencies aren't needed

## Running Specific Test Types

### Unit Tests Only
```bash
pytest -m unit
```

### Integration Tests Only
```bash
pytest -m integration
```

### Skip Slow Tests
```bash
pytest -m "not slow"
```

## Coverage Goals

- **Target**: >80% code coverage
- **Critical paths**: 100% coverage
- **Services**: >90% coverage
- **API endpoints**: >85% coverage

## Continuous Integration

Tests should be run:
- Before committing code
- In CI/CD pipeline
- Before deployment

## Notes

- Some tests may require external services (Stockfish, Redis, Qdrant, Ollama, Groq)
- These are marked with appropriate pytest markers
- Use `--skip-external` to skip tests requiring external services
- Mock services are used where possible for faster test execution

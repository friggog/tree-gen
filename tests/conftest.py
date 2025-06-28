import os
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock
import pytest


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    temp_path = tempfile.mkdtemp()
    yield Path(temp_path)
    shutil.rmtree(temp_path)


@pytest.fixture
def mock_config():
    """Provide a mock configuration object."""
    config = Mock()
    config.debug = False
    config.verbose = False
    config.output_dir = "/tmp/test_output"
    config.log_level = "INFO"
    return config


@pytest.fixture
def sample_tree_params():
    """Provide sample tree parameters for testing."""
    return {
        "height": 10.0,
        "trunk_radius": 1.0,
        "branch_length": 2.0,
        "branch_angle": 45.0,
        "leaf_size": 0.5,
        "seed": 42,
    }


@pytest.fixture
def mock_turtle():
    """Provide a mock turtle object for testing drawing operations."""
    turtle = Mock()
    turtle.xcor.return_value = 0.0
    turtle.ycor.return_value = 0.0
    turtle.heading.return_value = 90.0
    turtle.isdown.return_value = True
    return turtle


@pytest.fixture
def test_data_dir():
    """Provide path to test data directory."""
    return Path(__file__).parent / "data"


@pytest.fixture
def capture_stdout(monkeypatch):
    """Capture stdout for testing print statements."""
    import io
    import sys
    
    captured_output = io.StringIO()
    monkeypatch.setattr(sys, 'stdout', captured_output)
    yield captured_output
    

@pytest.fixture
def mock_file_system(tmp_path):
    """Create a mock file system structure for testing."""
    # Create some test directories and files
    (tmp_path / "trees").mkdir()
    (tmp_path / "output").mkdir()
    
    # Create sample files
    (tmp_path / "trees" / "oak.py").write_text("# Oak tree parameters")
    (tmp_path / "trees" / "pine.py").write_text("# Pine tree parameters")
    
    return tmp_path


@pytest.fixture(autouse=True)
def reset_random_seed():
    """Reset random seed before each test for reproducibility."""
    import random
    random.seed(42)
    
    # Also reset numpy random seed if numpy is available
    try:
        import numpy as np
        np.random.seed(42)
    except ImportError:
        pass


@pytest.fixture
def mock_gui_window():
    """Provide a mock GUI window for testing GUI components."""
    window = Mock()
    window.title = "Test Window"
    window.width = 800
    window.height = 600
    window.is_open = True
    return window


@pytest.fixture
def parametric_tree_module():
    """Provide access to the parametric tree module."""
    import parametric.gen
    return parametric.gen


# Markers for test organization
def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "slow: Tests that take significant time")
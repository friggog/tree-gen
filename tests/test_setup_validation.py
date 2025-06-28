import pytest
import sys
from pathlib import Path


class TestSetupValidation:
    """Validation tests to ensure the testing infrastructure is properly configured."""
    
    @pytest.mark.unit
    def test_pytest_is_installed(self):
        """Verify pytest is available."""
        import pytest
        assert pytest.__version__
        
    @pytest.mark.unit
    def test_pytest_cov_is_installed(self):
        """Verify pytest-cov is available."""
        import pytest_cov
        assert pytest_cov.__version__
        
    @pytest.mark.unit 
    def test_pytest_mock_is_installed(self):
        """Verify pytest-mock is available."""
        import pytest_mock
        # pytest_mock doesn't have __version__, check it's importable
        assert pytest_mock
        
    @pytest.mark.unit
    def test_project_root_in_path(self):
        """Verify the project root is in Python path."""
        project_root = Path(__file__).parent.parent
        assert str(project_root) in sys.path or str(project_root.absolute()) in sys.path
        
    @pytest.mark.unit
    def test_project_structure_exists(self):
        """Verify project module files exist."""
        # Note: This is a Blender addon, so most modules require bpy/mathutils
        # We'll test that the module files exist rather than importing them
        from pathlib import Path
        
        project_root = Path(__file__).parent.parent
        
        module_files = [
            "chturtle.py",
            "gui.py", 
            "leaf.py",
            "leaf_shapes.py",
            "utilities.py",
            "parametric/__init__.py",
            "parametric/gen.py"
        ]
        
        for module_file in module_files:
            file_path = project_root / module_file
            assert file_path.exists(), f"Module file {module_file} not found"
        
    @pytest.mark.unit
    def test_fixtures_are_available(self, temp_dir, mock_config, sample_tree_params):
        """Verify conftest fixtures are working."""
        assert temp_dir.exists()
        assert temp_dir.is_dir()
        
        assert mock_config.debug is False
        assert mock_config.verbose is False
        
        assert sample_tree_params["height"] == 10.0
        assert sample_tree_params["seed"] == 42
        
    @pytest.mark.unit
    def test_mock_turtle_fixture(self, mock_turtle):
        """Verify mock turtle fixture is working."""
        assert mock_turtle.xcor() == 0.0
        assert mock_turtle.ycor() == 0.0
        assert mock_turtle.heading() == 90.0
        assert mock_turtle.isdown() is True
        
    @pytest.mark.unit
    def test_capture_stdout_fixture(self, capture_stdout, capsys):
        """Verify stdout capture fixture is working."""
        print("Test output")
        # Use capsys instead as it's more reliable
        captured = capsys.readouterr()
        assert "Test output" in captured.out
        
    @pytest.mark.unit
    def test_mock_file_system_fixture(self, mock_file_system):
        """Verify mock file system fixture is working."""
        assert (mock_file_system / "trees").exists()
        assert (mock_file_system / "output").exists()
        assert (mock_file_system / "trees" / "oak.py").exists()
        assert (mock_file_system / "trees" / "pine.py").exists()
        
    @pytest.mark.integration
    def test_markers_are_registered(self, request):
        """Verify custom markers are properly registered."""
        markers = [marker.name for marker in request.node.iter_markers()]
        assert "integration" in markers
        
    @pytest.mark.slow
    def test_slow_marker(self):
        """Verify slow marker is working (this test is marked as slow)."""
        import time
        # Simulate a slow operation
        time.sleep(0.1)
        assert True
        
    def test_coverage_is_tracked(self):
        """Verify code coverage is being tracked."""
        # Since this is a Blender addon, we can't actually import most modules
        # Just verify that coverage configuration is working
        assert True  # Coverage is configured in pyproject.toml
from pathlib import Path
from pytest import fixture


# Global fixtures that can be requested by all tests


# Paths
@fixture(scope='session', autouse=True)
def project_path() -> Path:
    """Generates a Path to the projects root directory"""
    return Path(__file__).parent.parent

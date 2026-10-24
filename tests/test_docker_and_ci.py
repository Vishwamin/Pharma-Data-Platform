"""
Phase 9 — Test Module 7: Production Containerization & CI/CD Tests
==================================================================
Validates the Docker containerization assets and GitHub Actions CI/CD
workflow configuration.

Tests:
  1. Dockerfile configuration:
     - Base image, environment variables, system packages
     - Dependency installation and layer caching
     - Source copying and directory structure
     - Default CMD directive
  2. docker-compose.yml architecture:
     - Services: postgres, pipeline-runner, api-serving, dashboard
     - Port mappings (5432, 8000, 8501)
     - Health checks and service dependency ordering
     - Persistent volume and network definitions
  3. .dockerignore hygiene:
     - Excludes virtual environments, pycache, local sqlite DBs, logs
  4. GitHub Actions CI/CD Workflow:
     - Trigger events (push & pull_request to main)
     - PostgreSQL service container configuration
     - Pytest test execution and orchestrator execution steps
     - Artifact archiving
  5. PostgreSQL Init Script:
     - scripts/init_db.sql syntax and database creation

Run with:
  pytest tests/test_docker_and_ci.py -v
"""

import sys
import re
from pathlib import Path
import pytest

# Ensure project root is in Python path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# ===========================================================================
# 1. DOCKERFILE VALIDATION
# ===========================================================================
class TestDockerfileConfiguration:
    """Verifies that the production Dockerfile follows container best practices."""

    @pytest.fixture(scope="module")
    def dockerfile_content(self) -> str:
        dockerfile = PROJECT_ROOT / "Dockerfile"
        assert dockerfile.exists(), f"Dockerfile missing at {dockerfile}"
        return dockerfile.read_text(encoding="utf-8")

    def test_dockerfile_base_image(self, dockerfile_content):
        """Must use official Python 3.11 slim base image."""
        assert re.search(r"FROM\s+python:3\.11-slim", dockerfile_content), (
            "Dockerfile should use python:3.11-slim base image"
        )

    def test_dockerfile_environment_variables(self, dockerfile_content):
        """Must configure standard Python container environment flags."""
        assert "PYTHONUNBUFFERED=1" in dockerfile_content
        assert "PYTHONDONTWRITEBYTECODE=1" in dockerfile_content
        assert "PIP_NO_CACHE_DIR=1" in dockerfile_content

    def test_dockerfile_system_dependencies(self, dockerfile_content):
        """Must install required native libraries for psycopg2 and pyarrow compilation."""
        assert "libpq-dev" in dockerfile_content
        assert "build-essential" in dockerfile_content
        assert "apt-get update" in dockerfile_content
        assert "rm -rf /var/lib/apt/lists/*" in dockerfile_content  # Clean apt cache

    def test_dockerfile_layer_caching(self, dockerfile_content):
        """Requirements.txt must be copied and installed BEFORE full source code."""
        req_copy_pos = dockerfile_content.find("COPY requirements.txt")
        src_copy_pos = dockerfile_content.find("COPY src/")
        assert req_copy_pos != -1, "COPY requirements.txt not found"
        assert src_copy_pos != -1, "COPY src/ not found"
        assert req_copy_pos < src_copy_pos, (
            "requirements.txt should be copied before src/ to maximize layer caching"
        )

    def test_dockerfile_working_directory(self, dockerfile_content):
        """Must specify WORKDIR /app."""
        assert "WORKDIR /app" in dockerfile_content

    def test_dockerfile_default_cmd(self, dockerfile_content):
        """Default command should execute the Phase 7 master orchestrator."""
        assert 'CMD ["python", "src/orchestrator.py"]' in dockerfile_content


# ===========================================================================
# 2. DOCKER COMPOSE CONFIGURATION
# ===========================================================================
class TestDockerComposeArchitecture:
    """Verifies the multi-service docker-compose.yml configuration."""

    @pytest.fixture(scope="module")
    def compose_content(self) -> str:
        compose_file = PROJECT_ROOT / "docker-compose.yml"
        assert compose_file.exists(), f"docker-compose.yml missing at {compose_file}"
        return compose_file.read_text(encoding="utf-8")

    def test_compose_version(self, compose_content):
        """Compose file must specify a valid compose specification version."""
        assert 'version: "3.8"' in compose_content or "version: '3.8'" in compose_content

    @pytest.mark.parametrize("service_name", [
        "postgres",
        "pipeline-runner",
        "api-serving",
        "dashboard",
    ])
    def test_required_services_defined(self, compose_content, service_name):
        """All 4 essential architecture services must be defined."""
        assert f"{service_name}:" in compose_content, (
            f"Service '{service_name}' missing from docker-compose.yml"
        )

    def test_postgres_service_configuration(self, compose_content):
        """PostgreSQL service must configure image, ports, healthcheck, and data volume."""
        assert "postgres:15-alpine" in compose_content
        assert '"5432:5432"' in compose_content or "'5432:5432'" in compose_content
        assert "pg_isready" in compose_content
        assert "postgres_data:" in compose_content

    def test_service_health_dependencies(self, compose_content):
        """Application services must wait for PostgreSQL to be healthy."""
        assert "condition: service_healthy" in compose_content

    def test_port_mappings(self, compose_content):
        """API must expose port 8000 and dashboard must expose port 8501."""
        assert '"8000:8000"' in compose_content or "'8000:8000'" in compose_content
        assert '"8501:8501"' in compose_content or "'8501:8501'" in compose_content

    def test_network_definition(self, compose_content):
        """Must define a shared bridge network for container-to-container communication."""
        assert "pharma-network:" in compose_content
        assert "driver: bridge" in compose_content


# ===========================================================================
# 3. DOCKERIGNORE VALIDATION
# ===========================================================================
class TestDockerIgnoreHygiene:
    """Verifies .dockerignore properly excludes bloat and sensitive files."""

    @pytest.fixture(scope="module")
    def dockerignore_content(self) -> str:
        ignore_file = PROJECT_ROOT / ".dockerignore"
        assert ignore_file.exists(), f".dockerignore missing at {ignore_file}"
        return ignore_file.read_text(encoding="utf-8")

    @pytest.mark.parametrize("pattern", [
        "venv/",
        "__pycache__/",
        "*.db",
        "*.sqlite",
        ".git/",
    ])
    def test_critical_patterns_ignored(self, dockerignore_content, pattern):
        """Critical local development files must not be copied into Docker image."""
        assert pattern in dockerignore_content, (
            f"Pattern '{pattern}' should be present in .dockerignore"
        )


# ===========================================================================
# 4. GITHUB ACTIONS CI/CD WORKFLOW
# ===========================================================================
class TestGitHubActionsWorkflow:
    """Verifies that the GitHub Actions CI workflow is correctly specified."""

    @pytest.fixture(scope="module")
    def workflow_content(self) -> str:
        wf_file = PROJECT_ROOT / ".github" / "workflows" / "pipeline_ci.yml"
        assert wf_file.exists(), f"Workflow file missing at {wf_file}"
        return wf_file.read_text(encoding="utf-8")

    def test_workflow_trigger_events(self, workflow_content):
        """Workflow must trigger on pushes and pull requests to main."""
        assert "branches: [ main ]" in workflow_content or "branches: [main]" in workflow_content
        assert "pull_request:" in workflow_content
        assert "push:" in workflow_content

    def test_workflow_runner_environment(self, workflow_content):
        """Workflow should run on ubuntu-latest with Python 3.11."""
        assert "runs-on: ubuntu-latest" in workflow_content
        assert 'python-version: "3.11"' in workflow_content or "python-version: '3.11'" in workflow_content

    def test_workflow_database_service_container(self, workflow_content):
        """Must spin up a PostgreSQL service container with health check."""
        assert "postgres:15-alpine" in workflow_content
        assert "5432:5432" in workflow_content
        assert "pg_isready" in workflow_content

    def test_workflow_executes_pytest_and_orchestrator(self, workflow_content):
        """Must run the pytest test suite and Phase 7 orchestrator."""
        assert "pytest tests/" in workflow_content
        assert "python src/orchestrator.py" in workflow_content

    def test_workflow_uploads_logs_artifact(self, workflow_content):
        """Must upload execution logs as workflow artifacts."""
        assert "actions/upload-artifact" in workflow_content
        assert "path: logs/" in workflow_content


# ===========================================================================
# 5. POSTGRESQL INITIALIZATION SCRIPT
# ===========================================================================
class TestInitDBScript:
    """Verifies scripts/init_db.sql correctly sets up the database."""

    def test_init_db_script_exists_and_valid(self):
        """scripts/init_db.sql must exist and grant privileges."""
        init_file = PROJECT_ROOT / "scripts" / "init_db.sql"
        assert init_file.exists()
        content = init_file.read_text(encoding="utf-8")
        assert "pharma_clinical_db" in content
        assert "pharma_admin" in content

"""Tests for CLI to FastAPI communication."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from pydantic_temporal_example.api import CLIWorkflowRequest
from pydantic_temporal_example.app import app

client = TestClient(app)


class TestCLIWorkflowAPI:
    """Test CLI workflow API endpoints."""

    def test_submit_cli_workflow_success(self):
        """Test successful CLI workflow submission."""
        with patch("pydantic_temporal_example.api.get_temporal_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_get_client.return_value = mock_client

            # Mock successful workflow start
            mock_client.start_workflow = AsyncMock()

            request_data = {
                "prompt": "Test prompt",
                "repeat": False,
                "repeat_interval": 30,
                "repo_name": "test-repo",
                "session_id": "test-session",
            }

            response = client.post("/cli-workflow", json=request_data)

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "workflow_id" in data
            assert data["message"] == "Workflow assigned to a worker."
            assert data["is_repeating"] is False

    def test_submit_cli_workflow_with_repeat(self):
        """Test CLI workflow submission with repeat enabled."""
        with patch("pydantic_temporal_example.api.get_temporal_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_get_client.return_value = mock_client

            # Mock successful workflow start
            mock_client.start_workflow = AsyncMock()

            request_data = {
                "prompt": "Test repeating prompt",
                "repeat": True,
                "repeat_interval": 60,
                "repo_name": "test-repo",
            }

            response = client.post("/cli-workflow", json=request_data)

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["is_repeating"] is True
            assert "Repeating mode enabled" in data["message"]
            # Should have two workflow IDs (main + periodic)
            assert "," in data["workflow_id"]

    def test_submit_cli_workflow_invalid_data(self):
        """Test CLI workflow submission with invalid data."""
        request_data = {
            "prompt": "",  # Empty prompt should fail validation
            "repeat": False,
            "repeat_interval": 30,
            "repo_name": "test-repo",
        }

        response = client.post("/cli-workflow", json=request_data)

        assert response.status_code == 422  # Validation error

    def test_get_workflow_response_success(self):
        """Test successful workflow response retrieval."""
        with patch("pydantic_temporal_example.api.get_temporal_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_get_client.return_value = mock_client

            # Mock workflow handle and query
            mock_handle = AsyncMock()
            mock_client.get_workflow_handle_for.return_value = mock_handle

            # Mock response
            mock_response = {"content": "Test response", "metadata": {"timestamp": "2024-10-29T14:30:22"}}
            mock_handle.query.return_value = mock_response

            response = client.get("/cli-workflow/test-workflow-id/response")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "completed"
            assert data["response"]["content"] == "Test response"

    def test_get_workflow_response_pending(self):
        """Test workflow response when no response available."""
        with patch("pydantic_temporal_example.api.get_temporal_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_get_client.return_value = mock_client

            # Mock workflow handle and query
            mock_handle = AsyncMock()
            mock_client.get_workflow_handle_for.return_value = mock_handle
            mock_handle.query.return_value = None

            response = client.get("/cli-workflow/test-workflow-id/response")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "pending"
            assert data["response"] is None

    def test_get_workflow_response_not_found(self):
        """Test workflow response when workflow doesn't exist."""
        with patch("pydantic_temporal_example.api.get_temporal_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_get_client.return_value = mock_client

            # Mock TemporalError for workflow not found
            from temporalio.exceptions import TemporalError

            mock_client.get_workflow_handle_for.side_effect = TemporalError("Workflow not found")

            response = client.get("/cli-workflow/nonexistent-workflow/response")

            assert response.status_code == 404

    def test_stop_workflow_success(self):
        """Test successful workflow stopping."""
        with patch("pydantic_temporal_example.api.get_temporal_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_get_client.return_value = mock_client

            # Mock workflow handle and signal
            mock_handle = AsyncMock()
            mock_client.get_workflow_handle_for.return_value = mock_handle
            mock_handle.signal = AsyncMock()

            response = client.delete("/cli-workflow/test-workflow-id")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "stopped successfully" in data["message"]

    def test_stop_workflow_not_found(self):
        """Test workflow stopping when workflow doesn't exist."""
        with patch("pydantic_temporal_example.api.get_temporal_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_get_client.return_value = mock_client

            # Mock TemporalError for workflow not found
            from temporalio.exceptions import TemporalError

            mock_client.get_workflow_handle_for.side_effect = TemporalError("Workflow not found")

            response = client.delete("/cli-workflow/nonexistent-workflow")

            assert response.status_code == 404


class TestCLIWorkflowRequest:
    """Test CLI workflow request model validation."""

    def test_valid_request(self):
        """Test valid request model."""
        request = CLIWorkflowRequest(prompt="Test prompt", repeat=False, repeat_interval=30, repo_name="test-repo")
        assert request.prompt == "Test prompt"
        assert request.repeat is False
        assert request.repeat_interval == 30
        assert request.repo_name == "test-repo"

    def test_request_with_repeat(self):
        """Test request model with repeat enabled."""
        request = CLIWorkflowRequest(
            prompt="Test repeating prompt", repeat=True, repeat_interval=60, session_id="test-session"
        )
        assert request.repeat is True
        assert request.repeat_interval == 60
        assert request.session_id == "test-session"

    def test_invalid_repeat_interval(self):
        """Test request model with invalid repeat interval."""
        with pytest.raises(ValueError):
            CLIWorkflowRequest(
                prompt="Test prompt",
                repeat=True,
                repeat_interval=0,  # Should be >= 1
            )

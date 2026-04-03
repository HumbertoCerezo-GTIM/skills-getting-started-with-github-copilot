"""
Tests for the FastAPI application in src/app.py

Tests cover all endpoints with successful requests, validation errors,
and edge cases to ensure robust operation of the activity management system.
"""

import pytest
from copy import deepcopy
from fastapi.testclient import TestClient
from src.app import app, activities


@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    return TestClient(app)


@pytest.fixture
def reset_activities():
    """Save and restore the activities state before and after each test
    
    This fixture ensures that mutations to the in-memory activities dict
    during tests do not affect subsequent tests.
    """
    # Save the initial state
    initial_state = deepcopy(activities)
    
    yield
    
    # Restore the initial state after the test
    activities.clear()
    activities.update(initial_state)


class TestRootEndpoint:
    """Tests for the root endpoint"""
    
    def test_root_redirects_to_static_index(self, client):
        """GET / should redirect to /static/index.html"""
        # Arrange
        # (No setup needed; client is provided by fixture)
        
        # Act
        response = client.get("/", follow_redirects=False)
        
        # Assert
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"


class TestGetActivities:
    """Tests for retrieving the list of activities"""
    
    def test_get_activities_returns_all_activities(self, client, reset_activities):
        """GET /activities should return the full activities list"""
        # Arrange
        expected_activity_count = 9
        
        # Act
        response = client.get("/activities")
        data = response.json()
        
        # Assert
        assert response.status_code == 200
        assert isinstance(data, dict)
        assert "Chess Club" in data
        assert "Programming Class" in data
        assert "Gym Class" in data
        assert len(data) == expected_activity_count
    
    def test_get_activities_contains_activity_structure(self, client, reset_activities):
        """GET /activities should return activities with correct structure"""
        # Arrange
        expected_keys = {"description", "schedule", "max_participants", "participants"}
        activity_name = "Chess Club"
        
        # Act
        response = client.get("/activities")
        data = response.json()
        activity = data[activity_name]
        
        # Assert
        assert response.status_code == 200
        assert all(key in activity for key in expected_keys)
        assert isinstance(activity["participants"], list)


class TestSignupForActivity:
    """Tests for signing up for activities"""
    
    def test_signup_new_participant_success(self, client, reset_activities):
        """POST /activities/{name}/signup should add a new participant"""
        # Arrange
        activity_name = "Basketball Team"
        email = "test@mergington.edu"
        
        # Act
        response = client.post(
            f"/activities/{activity_name}/signup?email={email}"
        )
        data = response.json()
        
        # Verify participant was added
        activities_response = client.get("/activities")
        updated_activities = activities_response.json()
        participants_list = updated_activities[activity_name]["participants"]
        
        # Assert
        assert response.status_code == 200
        assert "Signed up" in data["message"]
        assert email in data["message"]
        assert email in participants_list
    
    def test_signup_duplicate_participant_returns_400(self, client, reset_activities):
        """Attempting to sign up twice should return 400"""
        # Arrange
        activity_name = "Chess Club"
        email = "new@mergington.edu"
        
        # Act - First signup (should succeed)
        response1 = client.post(
            f"/activities/{activity_name}/signup?email={email}"
        )
        
        # Act - Second signup with same email (should fail)
        response2 = client.post(
            f"/activities/{activity_name}/signup?email={email}"
        )
        data2 = response2.json()
        
        # Assert
        assert response1.status_code == 200
        assert response2.status_code == 400
        assert "already signed up" in data2["detail"]
    
    def test_signup_already_existing_participant_returns_400(self, client, reset_activities):
        """Signing up a participant already in an activity should return 400"""
        # Arrange
        activity_name = "Chess Club"
        existing_email = "michael@mergington.edu"  # Already in Chess Club initially
        
        # Act
        response = client.post(
            f"/activities/{activity_name}/signup?email={existing_email}"
        )
        data = response.json()
        
        # Assert
        assert response.status_code == 400
        assert "already signed up" in data["detail"]
    
    def test_signup_nonexistent_activity_returns_404(self, client, reset_activities):
        """Signing up for a nonexistent activity should return 404"""
        # Arrange
        activity_name = "Nonexistent Club"
        email = "test@mergington.edu"
        
        # Act
        response = client.post(
            f"/activities/{activity_name}/signup?email={email}"
        )
        data = response.json()
        
        # Assert
        assert response.status_code == 404
        assert "not found" in data["detail"]


class TestUnregisterFromActivity:
    """Tests for unregistering from activities"""
    
    def test_unregister_registered_participant_success(self, client, reset_activities):
        """DELETE /activities/{name}/signup should remove a participant"""
        # Arrange
        activity_name = "Chess Club"
        email = "michael@mergington.edu"  # Already registered initially
        
        # Act
        response = client.delete(
            f"/activities/{activity_name}/signup?email={email}"
        )
        data = response.json()
        
        # Verify participant was removed
        activities_response = client.get("/activities")
        updated_activities = activities_response.json()
        participants_list = updated_activities[activity_name]["participants"]
        
        # Assert
        assert response.status_code == 200
        assert "Unregistered" in data["message"]
        assert email in data["message"]
        assert email not in participants_list
    
    def test_unregister_not_signed_up_returns_400(self, client, reset_activities):
        """Unregistering a non-registered participant should return 400"""
        # Arrange
        activity_name = "Basketball Team"
        email = "noone@mergington.edu"
        
        # Act
        response = client.delete(
            f"/activities/{activity_name}/signup?email={email}"
        )
        data = response.json()
        
        # Assert
        assert response.status_code == 400
        assert "not signed up" in data["detail"]
    
    def test_unregister_nonexistent_activity_returns_404(self, client, reset_activities):
        """Unregistering from a nonexistent activity should return 404"""
        # Arrange
        activity_name = "Nonexistent Club"
        email = "test@mergington.edu"
        
        # Act
        response = client.delete(
            f"/activities/{activity_name}/signup?email={email}"
        )
        data = response.json()
        
        # Assert
        assert response.status_code == 404
        assert "not found" in data["detail"]


class TestActivityStateIsolation:
    """Tests to verify state isolation between test cases"""
    
    def test_signup_and_unregister_isolation(self, client, reset_activities):
        """Test that activities state is fresh in this test case"""
        # Arrange
        activity_name = "Basketball Team"
        
        # Act
        response = client.get("/activities")
        data = response.json()
        participants_count = len(data[activity_name]["participants"])
        
        # Assert
        assert response.status_code == 200
        assert participants_count == 0, "Basketball Team should start empty"
    
    def test_another_state_isolation_check(self, client, reset_activities):
        """Verify state is still fresh in a different test case"""
        # Arrange
        activity_name = "Basketball Team"
        
        # Act
        response = client.get("/activities")
        data = response.json()
        participants_count = len(data[activity_name]["participants"])
        
        # Assert
        assert response.status_code == 200
        assert participants_count == 0, "Basketball Team should still be empty"

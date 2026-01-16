from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)


def test_root():
    """Test root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "Building APIs Factory" in data["message"]
    assert "timestamp" in data


def test_health_check():
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data
    assert "environment" in data
    assert "version" in data


def test_api_info():
    """Test API info endpoint"""
    response = client.get("/api/info")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Building APIs Factory"
    assert "features" in data
    assert "cloud_platforms" in data
    assert isinstance(data["features"], list)
    assert isinstance(data["cloud_platforms"], list)

def test_health_check(client):
    """Test GET /api/health returns status 200 OK and {"status": "UP"}."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data == {"status": "UP"}

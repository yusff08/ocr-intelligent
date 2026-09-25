def test_register_user_success(client):
    """Test registering a new user account."""
    payload = {
        "email": "testuser@example.com",
        "password": "SecurePassword123!"
    }
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data.get("success") is True
    assert data.get("email") == "testuser@example.com"
    assert "user_id" in data


def test_register_duplicate_email(client):
    """Test registration with an already registered email returns 400 Bad Request."""
    payload = {
        "email": "duplicate@example.com",
        "password": "Password123!"
    }
    # First registration
    client.post("/api/auth/register", json=payload)

    # Second registration attempt
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 400
    assert "already registered" in response.json().get("detail", "").lower()


def test_login_user_success(client):
    """Test authenticating registered user returns JWT access token."""
    register_payload = {
        "email": "loginuser@example.com",
        "password": "MySecretPassword123"
    }
    client.post("/api/auth/register", json=register_payload)

    login_payload = {
        "email": "loginuser@example.com",
        "password": "MySecretPassword123"
    }
    response = client.post("/api/auth/login", json=login_payload)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data.get("token_type") == "bearer"
    assert data.get("user", {}).get("email") == "loginuser@example.com"


def test_login_user_invalid_credentials(client):
    """Test login with incorrect password returns 401 Unauthorized."""
    register_payload = {
        "email": "invalidlogin@example.com",
        "password": "RightPassword123"
    }
    client.post("/api/auth/register", json=register_payload)

    login_payload = {
        "email": "invalidlogin@example.com",
        "password": "WrongPassword123"
    }
    response = client.post("/api/auth/login", json=login_payload)
    assert response.status_code == 401


def test_protected_route_access_control(client):
    """Test GET /api/auth/me requires valid Bearer token."""
    # 1. Unauthenticated request -> 401
    response_unauth = client.get("/api/auth/me")
    assert response_unauth.status_code == 401

    # 2. Register and login
    email = "protected@example.com"
    pwd = "ProtectedPassword123"
    client.post("/api/auth/register", json={"email": email, "password": pwd})
    login_res = client.post("/api/auth/login", json={"email": email, "password": pwd})
    token = login_res.json().get("access_token")

    # 3. Authenticated request -> 200 OK
    headers = {"Authorization": f"Bearer {token}"}
    response_auth = client.get("/api/auth/me", headers=headers)
    assert response_auth.status_code == 200
    profile = response_auth.json()
    assert profile.get("success") is True
    assert profile.get("user", {}).get("email") == email

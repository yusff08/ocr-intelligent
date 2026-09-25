from unittest.mock import patch


def test_document_history_persistence_and_fetch(client):
    """Test saving document processing history when authenticated and fetching via GET /api/documents/history."""
    # 1. Register and login user
    email = "historyuser@example.com"
    pwd = "HistoryPassword123"
    client.post("/api/auth/register", json={"email": email, "password": pwd})
    login_res = client.post("/api/auth/login", json={"email": email, "password": pwd})
    token = login_res.json().get("access_token")
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Upload document while authenticated
    with patch("main.perform_ocr") as mock_ocr:
        mock_ocr.return_value = ("Document History Test Content", 0.95)
        files = {"file": ("receipt.png", b"fake-png-bytes", "image/png")}
        ocr_res = client.post("/api/ocr", files=files, headers=headers)
        assert ocr_res.status_code == 200
        ocr_data = ocr_res.json()
        assert ocr_data.get("document_id") is not None

    # 3. Fetch document history
    history_res = client.get("/api/documents/history", headers=headers)
    assert history_res.status_code == 200
    history_data = history_res.json()
    assert history_data.get("success") is True
    assert history_data.get("count") == 1
    docs = history_data.get("documents", [])
    assert len(docs) == 1
    assert docs[0]["filename"] == "receipt.png"
    assert "Document History Test Content" in docs[0]["raw_text"]


def test_document_history_unauthenticated(client):
    """Test fetching history without authorization token returns 401 Unauthorized."""
    response = client.get("/api/documents/history")
    assert response.status_code == 401


def test_document_history_delete_by_id(client):
    """Test deleting a document record from user history."""
    email = "deletehistory@example.com"
    pwd = "DeletePassword123"
    client.post("/api/auth/register", json={"email": email, "password": pwd})
    login_res = client.post("/api/auth/login", json={"email": email, "password": pwd})
    token = login_res.json().get("access_token")
    headers = {"Authorization": f"Bearer {token}"}

    # Upload doc
    with patch("main.perform_ocr") as mock_ocr:
        mock_ocr.return_value = ("To Be Deleted", 0.90)
        files = {"file": ("delete_me.png", b"dummy-data", "image/png")}
        ocr_res = client.post("/api/ocr", files=files, headers=headers)
        doc_id = ocr_res.json().get("document_id")

    # Delete doc
    del_res = client.delete(f"/api/documents/history/{doc_id}", headers=headers)
    assert del_res.status_code == 200
    assert del_res.json().get("success") is True

    # Verify history is now empty
    history_res = client.get("/api/documents/history", headers=headers)
    assert history_res.json().get("count") == 0

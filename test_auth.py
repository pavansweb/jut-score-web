from app import app, format_size, normalize_storage_path


def test_normalize_storage_path():
    assert normalize_storage_path("") == "storage"
    assert normalize_storage_path("storage/semester-1") == "storage/semester-1"
    assert normalize_storage_path("../outside") == "storage"


def test_format_size():
    assert format_size(900) == "900 B"
    assert format_size(1024) == "1.0 KB"


def test_login_screen_is_public():
    with app.test_client() as client:
        response = client.get("/login")
        assert response.status_code == 200


def test_dashboard_requires_auth():
    with app.test_client() as client:
        response = client.get("/")
        assert response.status_code == 302
        assert "/login" in response.location

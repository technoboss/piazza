# "client" comes from conftest.py. pytest matches it by parameter name.
def test_health(client):
    response = client.get("/health")  # simulates an HTTP request, no real server needed
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
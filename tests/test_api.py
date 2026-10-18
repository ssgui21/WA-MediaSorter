import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_api_dashboard_endpoint(client):
    """Testa o endpoint de resumo do painel inicial."""
    res = client.get("/api/dashboard")
    assert res.status_code == 200
    data = res.json()
    assert "app_status" in data
    assert "whatsapp" in data
    assert "destination" in data
    assert "rules" in data
    assert "session_stats" in data


def test_api_rules_crud_endpoints(client):
    """Testa endpoints de CRUD e alternância de regras."""
    # 1. Criar regra
    new_rule = {
        "name": "Regra Teste API",
        "criteria_type": "text",
        "specific_config": {
            "keywords": ["teste", "api"],
            "match_mode": "any"
        },
        "is_active": True,
        "logical_operator": "OR",
        "confidence_threshold": 0.5
    }
    create_res = client.post("/api/rules", json=new_rule)
    assert create_res.status_code == 201
    created_data = create_res.json()
    rule_id = created_data["id"]
    assert created_data["name"] == "Regra Teste API"

    # 2. Listar regras
    list_res = client.get("/api/rules")
    assert list_res.status_code == 200
    rules_list = list_res.json()
    assert any(r["id"] == rule_id for r in rules_list)

    # 3. Consultar regra por ID
    get_res = client.get(f"/api/rules/{rule_id}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == rule_id

    # 4. Alternar status (Toggle)
    toggle_res = client.patch(f"/api/rules/{rule_id}/toggle")
    assert toggle_res.status_code == 200
    assert toggle_res.json()["is_active"] is False

    # 5. Atualizar regra
    update_res = client.put(f"/api/rules/{rule_id}", json={"name": "Regra Renomeada"})
    assert update_res.status_code == 200
    assert update_res.json()["name"] == "Regra Renomeada"

    # 6. Excluir regra
    del_res = client.delete(f"/api/rules/{rule_id}")
    assert del_res.status_code == 204


def test_api_destination_endpoints(client, tmp_path):
    """Testa validação e atualização da pasta de destino."""
    # Obter destino atual
    get_res = client.get("/api/destination")
    assert get_res.status_code == 200
    assert "path" in get_res.json()

    # Validar caminho válido
    val_res = client.post("/api/destination/validate", json={"path": str(tmp_path)})
    assert val_res.status_code == 200
    assert val_res.json()["is_valid"] is True

    # Validar caminho vazio (deve indicar inválido)
    val_empty = client.post("/api/destination/validate", json={"path": " "})
    assert val_empty.status_code == 200
    assert val_empty.json()["is_valid"] is False


def test_api_whatsapp_status_endpoint(client):
    """Testa consulta ao status do WhatsApp."""
    res = client.get("/api/whatsapp/status")
    assert res.status_code == 200
    data = res.json()
    assert "state" in data
    assert "message" in data


def test_api_processing_endpoints(client):
    """Testa endpoints de prévia e status de processamento."""
    status_res = client.get("/api/processing/status")
    assert status_res.status_code == 200
    assert "status" in status_res.json()

    preview_res = client.post("/api/processing/preview", json={"source_mode": "sample"})
    assert preview_res.status_code == 200
    assert isinstance(preview_res.json(), list)

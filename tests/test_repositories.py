import pytest
from app.repositories.rule_repository import RuleRepository
from app.repositories.history_repository import HistoryRepository
from app.models.rule import RuleCreate, RuleUpdate, CriteriaType, LogicalOperator
from app.models.history import ExecutionRecord


def test_rule_repository_crud_and_persistence(tmp_path):
    """Testa criação, persistência, leitura, atualização e exclusão de regras no JSON."""
    settings_file = tmp_path / "settings.json"
    repo = RuleRepository(settings_file)

    # 1. Criação
    rule_in = RuleCreate(
        name="Regra Teste 1",
        criteria_type=CriteriaType.TEXT,
        specific_config={"keywords": ["recibo"], "match_mode": "any"},
        is_active=True,
        logical_operator=LogicalOperator.OR,
        confidence_threshold=0.6
    )
    created = repo.create_rule(rule_in)
    assert created.id.startswith("rule-")
    assert created.name == "Regra Teste 1"

    # 2. Leitura
    retrieved = repo.get_rule(created.id)
    assert retrieved is not None
    assert retrieved.name == "Regra Teste 1"
    assert retrieved.confidence_threshold == 0.6

    # 3. Atualização
    update_in = RuleUpdate(name="Regra Atualizada", confidence_threshold=0.8)
    updated = repo.update_rule(created.id, update_in)
    assert updated.name == "Regra Atualizada"
    assert updated.confidence_threshold == 0.8

    # 4. Alternância de status (Toggle)
    toggled = repo.toggle_rule(created.id)
    assert toggled.is_active is False
    toggled_back = repo.toggle_rule(created.id)
    assert toggled_back.is_active is True

    # 5. Persistência após recriação da instância do repositório
    new_repo_instance = RuleRepository(settings_file)
    rules_persisted = new_repo_instance.list_rules()
    assert len(rules_persisted) == 1
    assert rules_persisted[0].name == "Regra Atualizada"

    # 6. Exclusão
    deleted = new_repo_instance.delete_rule(created.id)
    assert deleted is True
    assert len(new_repo_instance.list_rules()) == 0


def test_destination_setting_persistence(tmp_path):
    """Testa persistência e recuperação do caminho de destino configurado."""
    settings_file = tmp_path / "settings.json"
    repo = RuleRepository(settings_file)

    test_path = "C:\\MinhasImagens\\Whatsapp"
    saved = repo.set_destination_path(test_path)
    assert saved == test_path

    # Nova instância carregando do mesmo arquivo
    repo2 = RuleRepository(settings_file)
    assert repo2.get_destination_path() == test_path


def test_history_repository_sqlite(tmp_path):
    """Testa gravação e consulta de execuções e hashes de deduplicação no SQLite."""
    db_file = tmp_path / "history.db"
    history = HistoryRepository(db_file)

    # 1. Inserção de execução
    rec = ExecutionRecord(
        source_group="Grupo Teste",
        analyzed_count=10,
        approved_count=5,
        rejected_count=5,
        saved_count=5,
        errors_count=0,
        details="Teste OK"
    )
    rec_id = history.add_execution(rec)
    assert rec_id is not None

    # 2. Listagem de execuções
    history_list = history.list_executions()
    assert len(history_list) == 1
    assert history_list[0].source_group == "Grupo Teste"
    assert history_list[0].saved_count == 5

    # 3. Hash de deduplicação
    assert history.is_hash_known("hash123") is False
    history.record_saved_hash("hash123", "foto.jpg", "C:\\downloads\\foto.jpg")
    assert history.is_hash_known("hash123") is True

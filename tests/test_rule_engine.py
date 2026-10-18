import pytest
from app.models.item import MediaItem
from app.models.rule import (
    Rule,
    CriteriaType,
    LogicalOperator,
)
from app.services.rule_engine import RuleEngine
from app.services.image_analyzer import ImageAnalyzer


@pytest.fixture
def rule_engine():
    return RuleEngine()


@pytest.fixture
def sample_receipt_item():
    return MediaItem(
        id="item-1",
        filename="recibo_01.jpg",
        source_group="Grupo Finanças",
        caption="Segue o comprovante de pagamento do boleto."
    )


@pytest.fixture
def sample_casual_item():
    return MediaItem(
        id="item-2",
        filename="passeio.jpg",
        source_group="Grupo Família",
        caption="Olha essa foto da praia no final de semana!"
    )


def test_text_criterion_met_and_not_met(rule_engine, sample_receipt_item, sample_casual_item):
    """Testa se critério textual é aprovado quando palavra-chave existe e rejeitado quando ausente."""
    rule = Rule(
        id="r-text-1",
        name="Buscar Comprovantes",
        criteria_type=CriteriaType.TEXT,
        specific_config={"keywords": ["comprovante", "pagamento"], "match_mode": "any"},
        is_active=True,
        logical_operator=LogicalOperator.OR,
        confidence_threshold=0.5
    )

    # Item que atende às palavras
    res_met = rule_engine.evaluate_rule(rule, sample_receipt_item)
    assert res_met.approved is True
    assert len(res_met.criteria_met) > 0
    assert len(res_met.criteria_not_met) == 0

    # Item que não atende
    res_not_met = rule_engine.evaluate_rule(rule, sample_casual_item)
    assert res_not_met.approved is False
    assert len(res_not_met.criteria_met) == 0
    assert len(res_not_met.criteria_not_met) > 0


def test_logical_operator_and_all_met(rule_engine):
    """Testa operador lógico AND quando todos os critérios são atendidos."""
    item = MediaItem(
        id="item-3",
        filename="fatura_boleto.png",
        source_group="Contas",
        caption="fatura e boleto pagos"
    )
    rule = Rule(
        id="r-and-1",
        name="Fatura E Boleto",
        criteria_type=CriteriaType.COMBINATION,
        specific_config={
            "sub_criteria": [
                {"name": "Tem Fatura", "type": "text", "keywords": ["fatura"], "match_mode": "any"},
                {"name": "Tem Boleto", "type": "text", "keywords": ["boleto"], "match_mode": "any"}
            ]
        },
        is_active=True,
        logical_operator=LogicalOperator.AND,
        confidence_threshold=0.5
    )

    res = rule_engine.evaluate_rule(rule, item)
    assert res.approved is True
    assert len(res.criteria_met) == 2


def test_logical_operator_and_partial_fail(rule_engine):
    """Testa operador lógico AND reprovando quando apenas parte dos critérios é atendida."""
    item = MediaItem(
        id="item-4",
        filename="apenas_fatura.png",
        source_group="Contas",
        caption="Segue fatura mensal"
    )
    rule = Rule(
        id="r-and-2",
        name="Fatura E Boleto",
        criteria_type=CriteriaType.COMBINATION,
        specific_config={
            "sub_criteria": [
                {"name": "Tem Fatura", "type": "text", "keywords": ["fatura"], "match_mode": "any"},
                {"name": "Tem Boleto", "type": "text", "keywords": ["boleto"], "match_mode": "any"}
            ]
        },
        is_active=True,
        logical_operator=LogicalOperator.AND,
        confidence_threshold=0.5
    )

    res = rule_engine.evaluate_rule(rule, item)
    assert res.approved is False
    assert "Tem Fatura" in res.criteria_met
    assert "Tem Boleto" in res.criteria_not_met


def test_logical_operator_or(rule_engine):
    """Testa operador lógico OR aprovando quando apenas um dos critérios é atendido."""
    item = MediaItem(
        id="item-5",
        filename="nota_fiscal.png",
        source_group="Contas",
        caption="Arquivo de nota fiscal"
    )
    rule = Rule(
        id="r-or-1",
        name="Boleto OU Nota Fiscal",
        criteria_type=CriteriaType.COMBINATION,
        specific_config={
            "sub_criteria": [
                {"name": "Boleto", "type": "text", "keywords": ["boleto"], "match_mode": "any"},
                {"name": "Nota Fiscal", "type": "text", "keywords": ["nota fiscal"], "match_mode": "any"}
            ]
        },
        is_active=True,
        logical_operator=LogicalOperator.OR,
        confidence_threshold=0.5
    )

    res = rule_engine.evaluate_rule(rule, item)
    assert res.approved is True
    assert "Nota Fiscal" in res.criteria_met


def test_deactivated_rule_not_evaluated(rule_engine, sample_receipt_item):
    """Testa se uma regra desativada não é considerada aprovada."""
    rule = Rule(
        id="r-inactive-1",
        name="Regra Desativada",
        criteria_type=CriteriaType.TEXT,
        specific_config={"keywords": ["comprovante"], "match_mode": "any"},
        is_active=False,
        logical_operator=LogicalOperator.OR,
        confidence_threshold=0.5
    )

    res = rule_engine.evaluate_rule(rule, sample_receipt_item)
    assert res.approved is False
    assert "desativada" in res.justification.lower()

    # Na avaliação global, se todas as regras estiverem inativas, a imagem deve ser rejeitada
    overall = rule_engine.evaluate_all_rules([rule], sample_receipt_item)
    assert overall.approved is False


def test_confidence_threshold_rejection(rule_engine):
    """Testa rejeição quando a confiança obtida é menor que o limite configurado."""
    # Simula correspondência parcial com match_mode 'any' de 4 palavras onde apenas 1 é encontrada (confiança 0.25)
    item = MediaItem(
        id="item-6",
        filename="teste.png",
        source_group="Geral",
        caption="Apenas comprovante aqui"
    )
    rule = Rule(
        id="r-conf-1",
        name="Alta Confiança Exigida",
        criteria_type=CriteriaType.TEXT,
        specific_config={
            "keywords": ["comprovante", "fatura", "recibo", "boleto"],
            "match_mode": "any"
        },
        is_active=True,
        logical_operator=LogicalOperator.OR,
        confidence_threshold=0.5 # Exige pelo menos 50%
    )

    res = rule_engine.evaluate_rule(rule, item)
    # 1 de 4 palavras = 0.25 de confiança < 0.5 threshold
    assert res.approved is False
    assert len(res.criteria_not_met) > 0


def test_unavailable_criterion_never_auto_passed(rule_engine):
    """
    Requisito estrito: Não considerar um critério indisponível como automaticamente atendido.
    """
    item = MediaItem(
        id="item-7",
        filename="foto.png",
        source_group="Geral",
        caption=""
    )
    # Critério de logotipo apontando para arquivo que não existe
    rule = Rule(
        id="r-unavail-1",
        name="Logotipo Inexistente",
        criteria_type=CriteriaType.LOGO,
        specific_config={"reference_logo_path": "C:\\caminho\\inexistente\\logo.png"},
        is_active=True,
        logical_operator=LogicalOperator.OR,
        confidence_threshold=0.5
    )

    fake_bytes = b"\x89PNG\r\n\x1a\nfakeimagebytes"
    res = rule_engine.evaluate_rule(rule, item, fake_bytes)

    assert res.approved is False
    assert len(res.criteria_unavailable) > 0
    assert len(res.criteria_met) == 0
    assert "indisponível" in res.justification.lower()

from fastapi import APIRouter, HTTPException, status
from typing import List, Optional
from app.models.rule import Rule, RuleCreate, RuleUpdate
from app.repositories.rule_repository import RuleRepository

router = APIRouter(prefix="/api/rules", tags=["Regras"])
rule_repo = RuleRepository()


@router.get("", response_model=List[Rule])
def list_rules():
    """Lista todas as regras configuradas pelo usuário."""
    return rule_repo.list_rules()


@router.post("", response_model=Rule, status_code=status.HTTP_201_CREATED)
def create_rule(rule_in: RuleCreate):
    """Cria uma nova regra com validação dos parâmetros."""
    # Validações semânticas adicionais
    if rule_in.confidence_threshold < 0.0 or rule_in.confidence_threshold > 1.0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="O limite de confiança deve estar entre 0.0 e 1.0."
        )
    return rule_repo.create_rule(rule_in)


@router.get("/{rule_id}", response_model=Rule)
def get_rule(rule_id: str):
    """Obtém detalhes de uma regra específica."""
    rule = rule_repo.get_rule(rule_id)
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Regra com ID '{rule_id}' não encontrada."
        )
    return rule


@router.put("/{rule_id}", response_model=Rule)
def update_rule(rule_id: str, rule_in: RuleUpdate):
    """Atualiza as configurações de uma regra existente."""
    updated = rule_repo.update_rule(rule_id, rule_in)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Regra com ID '{rule_id}' não encontrada para atualização."
        )
    return updated


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_rule(rule_id: str):
    """Exclui uma regra pelo identificador."""
    deleted = rule_repo.delete_rule(rule_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Regra com ID '{rule_id}' não encontrada para exclusão."
        )
    return None


@router.patch("/{rule_id}/toggle", response_model=Rule)
def toggle_rule(rule_id: str, is_active: Optional[bool] = None):
    """Ativa ou desativa uma regra."""
    rule = rule_repo.toggle_rule(rule_id, is_active)
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Regra com ID '{rule_id}' não encontrada."
        )
    return rule

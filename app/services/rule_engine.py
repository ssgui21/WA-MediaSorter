from typing import List, Optional, Tuple
from app.models.item import MediaItem
from app.models.rule import (
    CriteriaType,
    LogicalOperator,
    Rule,
    CriterionEvaluation,
    RuleEvaluationResult,
    OverallEvaluationResult,
)
from app.services.image_analyzer import ImageAnalyzer


class RuleEngine:
    """
    Motor de avaliação de regras para imagens.
    Executa de forma determinística, sem dynamic code evaluation ('eval' / 'exec').
    Garante que critérios indisponíveis nunca sejam considerados atendidos automaticamente.
    """

    def __init__(self, image_analyzer: Optional[ImageAnalyzer] = None):
        self.analyzer = image_analyzer or ImageAnalyzer()

    def evaluate_rule(self, rule: Rule, item: MediaItem, image_bytes: Optional[bytes] = None) -> RuleEvaluationResult:
        """
        Avalia uma única regra contra uma imagem.
        """
        if not rule.is_active:
            return RuleEvaluationResult(
                rule_id=rule.id,
                rule_name=rule.name,
                approved=False,
                evaluated_criteria=[],
                criteria_met=[],
                criteria_not_met=[],
                criteria_unavailable=[],
                justification=f"A regra '{rule.name}' está desativada e não foi avaliada."
            )

        evaluated_criteria: List[CriterionEvaluation] = []
        criteria_met: List[str] = []
        criteria_not_met: List[str] = []
        criteria_unavailable: List[str] = []

        cfg = rule.specific_config or {}

        # 1. Critério Textual
        if rule.criteria_type == CriteriaType.TEXT:
            keywords = cfg.get("keywords", [])
            match_mode = cfg.get("match_mode", "any")
            case_sensitive = cfg.get("case_sensitive", False)

            met, conf, details = self.analyzer.analyze_text_criterion(
                caption=item.caption or "",
                filename=item.filename or "",
                keywords=keywords,
                match_mode=match_mode,
                case_sensitive=case_sensitive
            )

            # Verificar limite de confiança se configurado
            if met and conf < rule.confidence_threshold:
                met = False
                details += f" (Confiança {conf:.2f} inferior ao limite mínimo de {rule.confidence_threshold:.2f})"

            crit_name = f"Texto ({match_mode})"
            ev = CriterionEvaluation(
                criterion_name=crit_name,
                criteria_type=CriteriaType.TEXT,
                met=met,
                available=True,
                confidence=conf,
                details=details
            )
            evaluated_criteria.append(ev)
            if met:
                criteria_met.append(crit_name)
            else:
                criteria_not_met.append(crit_name)

        # 2. Critério de Logotipo / Marca
        elif rule.criteria_type == CriteriaType.LOGO:
            ref_path = cfg.get("reference_logo_path")
            crit_name = f"Logotipo ({ref_path or 'Não configurado'})"

            if not image_bytes:
                ev = CriterionEvaluation(
                    criterion_name=crit_name,
                    criteria_type=CriteriaType.LOGO,
                    met=False,
                    available=False,
                    confidence=0.0,
                    details="Conteúdo binário da imagem não fornecido para busca de logotipo."
                )
                evaluated_criteria.append(ev)
                criteria_unavailable.append(crit_name)
            else:
                met, available, conf, details = self.analyzer.analyze_logo_criterion(
                    image_bytes=image_bytes,
                    reference_logo_path=ref_path
                )
                if available and met and conf < rule.confidence_threshold:
                    met = False
                    details += f" (Confiança {conf:.2f} inferior ao limite {rule.confidence_threshold:.2f})"

                ev = CriterionEvaluation(
                    criterion_name=crit_name,
                    criteria_type=CriteriaType.LOGO,
                    met=met if available else False,
                    available=available,
                    confidence=conf if available else None,
                    details=details
                )
                evaluated_criteria.append(ev)
                if not available:
                    criteria_unavailable.append(crit_name)
                elif met:
                    criteria_met.append(crit_name)
                else:
                    criteria_not_met.append(crit_name)

        # 3. Critério de Objeto / Conteúdo Visual
        elif rule.criteria_type == CriteriaType.OBJECT:
            obj_desc = cfg.get("object_description", "")
            crit_name = f"Objeto Visual: {obj_desc}"

            if not image_bytes:
                ev = CriterionEvaluation(
                    criterion_name=crit_name,
                    criteria_type=CriteriaType.OBJECT,
                    met=False,
                    available=False,
                    confidence=0.0,
                    details="Conteúdo da imagem indisponível para análise visual."
                )
                evaluated_criteria.append(ev)
                criteria_unavailable.append(crit_name)
            else:
                met, available, conf, details = self.analyzer.analyze_object_criterion(
                    image_bytes=image_bytes,
                    object_description=obj_desc,
                    confidence_threshold=rule.confidence_threshold
                )
                ev = CriterionEvaluation(
                    criterion_name=crit_name,
                    criteria_type=CriteriaType.OBJECT,
                    met=met if available else False,
                    available=available,
                    confidence=conf if available else None,
                    details=details
                )
                evaluated_criteria.append(ev)
                if not available:
                    criteria_unavailable.append(crit_name)
                elif met:
                    criteria_met.append(crit_name)
                else:
                    criteria_not_met.append(crit_name)

        # 4. Combinação de Subcritérios (AND / OR)
        elif rule.criteria_type == CriteriaType.COMBINATION:
            sub_criteria = cfg.get("sub_criteria", [])
            for idx, sub in enumerate(sub_criteria):
                sub_type = sub.get("type")
                sub_name = sub.get("name", f"Subcritério {idx + 1} ({sub_type})")

                if sub_type == "text":
                    keywords = sub.get("keywords", [])
                    m_mode = sub.get("match_mode", "any")
                    c_sens = sub.get("case_sensitive", False)
                    met, conf, details = self.analyzer.analyze_text_criterion(
                        caption=item.caption or "",
                        filename=item.filename or "",
                        keywords=keywords,
                        match_mode=m_mode,
                        case_sensitive=c_sens
                    )
                    sub_thresh = sub.get("confidence_threshold", rule.confidence_threshold)
                    if met and conf < sub_thresh:
                        met = False
                        details += f" (Confiança {conf:.2f} abaixo de {sub_thresh:.2f})"
                    ev = CriterionEvaluation(
                        criterion_name=sub_name,
                        criteria_type=CriteriaType.TEXT,
                        met=met,
                        available=True,
                        confidence=conf,
                        details=details
                    )
                    evaluated_criteria.append(ev)
                    if met:
                        criteria_met.append(sub_name)
                    else:
                        criteria_not_met.append(sub_name)

                elif sub_type == "logo":
                    ref_p = sub.get("reference_logo_path")
                    if not image_bytes:
                        ev = CriterionEvaluation(
                            criterion_name=sub_name,
                            criteria_type=CriteriaType.LOGO,
                            met=False,
                            available=False,
                            confidence=0.0,
                            details="Bytes da imagem indisponíveis."
                        )
                        evaluated_criteria.append(ev)
                        criteria_unavailable.append(sub_name)
                    else:
                        met, available, conf, details = self.analyzer.analyze_logo_criterion(
                            image_bytes=image_bytes,
                            reference_logo_path=ref_p
                        )
                        sub_thresh = sub.get("confidence_threshold", rule.confidence_threshold)
                        if available and met and conf < sub_thresh:
                            met = False
                            details += f" (Confiança {conf:.2f} abaixo de {sub_thresh:.2f})"
                        ev = CriterionEvaluation(
                            criterion_name=sub_name,
                            criteria_type=CriteriaType.LOGO,
                            met=met if available else False,
                            available=available,
                            confidence=conf if available else None,
                            details=details
                        )
                        evaluated_criteria.append(ev)
                        if not available:
                            criteria_unavailable.append(sub_name)
                        elif met:
                            criteria_met.append(sub_name)
                        else:
                            criteria_not_met.append(sub_name)

                elif sub_type == "object":
                    obj_desc = sub.get("object_description", "")
                    if not image_bytes:
                        ev = CriterionEvaluation(
                            criterion_name=sub_name,
                            criteria_type=CriteriaType.OBJECT,
                            met=False,
                            available=False,
                            confidence=0.0,
                            details="Bytes da imagem indisponíveis."
                        )
                        evaluated_criteria.append(ev)
                        criteria_unavailable.append(sub_name)
                    else:
                        met, available, conf, details = self.analyzer.analyze_object_criterion(
                            image_bytes=image_bytes,
                            object_description=obj_desc,
                            confidence_threshold=rule.confidence_threshold
                        )
                        ev = CriterionEvaluation(
                            criterion_name=sub_name,
                            criteria_type=CriteriaType.OBJECT,
                            met=met if available else False,
                            available=available,
                            confidence=conf if available else None,
                            details=details
                        )
                        evaluated_criteria.append(ev)
                        if not available:
                            criteria_unavailable.append(sub_name)
                        elif met:
                            criteria_met.append(sub_name)
                        else:
                            criteria_not_met.append(sub_name)

        # Decisão lógica da regra baseada no operador (AND / OR)
        total_eval = len(evaluated_criteria)
        if total_eval == 0:
            approved = False
            justification = "Nenhum critério foi configurado para esta regra."
        elif rule.logical_operator == LogicalOperator.AND:
            # Em AND, TODOS os critérios devem estar disponíveis E atendidos
            # Critérios indisponíveis NÃO podem ser considerados atendidos
            approved = (len(criteria_met) == total_eval) and (len(criteria_unavailable) == 0)
            if approved:
                justification = f"Todos os {total_eval} critérios (AND) foram atendidos com sucesso."
            elif criteria_unavailable:
                justification = f"Reprovada: critério(s) indisponível(is): {', '.join(criteria_unavailable)}."
            else:
                justification = f"Reprovada: critério(s) não atendido(s): {', '.join(criteria_not_met)}."
        else:  # LogicalOperator.OR
            # Em OR, basta que pelo menos UM critério disponível seja atendido
            approved = len(criteria_met) > 0
            if approved:
                justification = f"Critério(s) atendido(s) via OR: {', '.join(criteria_met)}."
            elif criteria_unavailable and len(criteria_not_met) == 0:
                justification = f"Reprovada: critério(s) indisponível(is) para avaliação: {', '.join(criteria_unavailable)}."
            else:
                justification = f"Nenhum critério atendido via OR. Não atendidos: {', '.join(criteria_not_met)}."

        return RuleEvaluationResult(
            rule_id=rule.id,
            rule_name=rule.name,
            approved=approved,
            evaluated_criteria=evaluated_criteria,
            criteria_met=criteria_met,
            criteria_not_met=criteria_not_met,
            criteria_unavailable=criteria_unavailable,
            justification=justification
        )

    def evaluate_all_rules(
        self,
        rules: List[Rule],
        item: MediaItem,
        image_bytes: Optional[bytes] = None
    ) -> OverallEvaluationResult:
        """
        Avalia o conjunto de regras sobre a mídia.
        Se qualquer regra ativa aprovar a imagem (ou se não houver regras ativas),
        gera a decisão consolidada.
        """
        active_rules = [r for r in rules if r.is_active]
        if not active_rules:
            return OverallEvaluationResult(
                approved=False,
                evaluations=[],
                justification="Nenhuma regra ativa para avaliar imagens. Todas as imagens foram ignoradas por segurança."
            )

        evaluations: List[RuleEvaluationResult] = []
        any_approved = False
        approved_rule_names = []

        for rule in active_rules:
            res = self.evaluate_rule(rule, item, image_bytes)
            evaluations.append(res)
            if res.approved:
                any_approved = True
                approved_rule_names.append(rule.name)

        if any_approved:
            justification = f"Imagem aprovada pelas regras: {', '.join(approved_rule_names)}."
        else:
            justification = "Imagem rejeitada: nenhuma das regras ativas atendeu aos critérios necessários."

        return OverallEvaluationResult(
            approved=any_approved,
            evaluations=evaluations,
            justification=justification
        )

from __future__ import annotations

from typing import Any, Dict, List

class PatternAnalyzer:
    """
    Analisa o histórico de evaluations para identificar padrões de falha e sucesso.
    Sugere ajustes automáticos na estratégia do sistema.
    """

    def analyze(self, evaluations: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not evaluations:
            return {
                "weak_patterns": [],
                "strong_patterns": [],
                "underused_capabilities": [],
                "recommended_adjustments": []
            }
            
        # Filtra por scores baixos e altos
        low_scores = [ev for ev in evaluations if ev.get('overall', 0) < 0.5]
        high_scores = [ev for ev in evaluations if ev.get('overall', 0) > 0.8]
        
        weak_patterns = self._extract_dominant_flags(low_scores)
        strong_patterns = self._extract_dominant_flags(high_scores)
        
        # Identifica recomendações baseadas no conjunto de falhas
        recommended_adjustments = []
        
        if "too_long" in weak_patterns:
            recommended_adjustments.append("adjust_efficiency_threshold")
        
        if "off_topic" in weak_patterns:
            recommended_adjustments.append("rebalance_intent_weights")
            
        if "empty_response" in weak_patterns:
            recommended_adjustments.append("reinforce_fallback_strategy")
            
        # Análise básica de capabilities (placeholder para integração com logs de uso)
        underused = [] # Futuramente preenchido comparando registry vs usage_logs
        
        return {
            "evaluation_count": len(evaluations),
            "weak_patterns": weak_patterns,
            "strong_patterns": strong_patterns,
            "underused_capabilities": underused,
            "recommended_adjustments": list(set(recommended_adjustments))
        }

    def _extract_dominant_flags(self, evaluations: List[Dict[str, Any]]) -> List[str]:
        flag_counts: Dict[str, int] = {}
        for ev in evaluations:
            for flag in ev.get('flags', []):
                flag_counts[flag] = flag_counts.get(flag, 0) + 1
        
        # Retorna apenas flags que aparecem em mais de 20% dos casos analisados
        threshold = len(evaluations) * 0.2
        return [f for f, count in flag_counts.items() if count >= threshold]

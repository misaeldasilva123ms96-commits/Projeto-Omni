from __future__ import annotations

import time
import re
from typing import Any, Dict, List

class ResponseEvaluator:
    """
    Avalia a qualidade das respostas geradas pelo sistema Omini.
    Utiliza heurísticas leves para calcular scores multidimensionais.
    """

    def evaluate(
        self, 
        session_id: str, 
        turn_id: str, 
        input_text: str, 
        output_text: str, 
        history: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        # 1. Relevance: similaridade semântica input ↔ output
        relevance = self._calculate_relevance(input_text, output_text)
        
        # 2. Coherence: consistência com histórico da sessão
        coherence = self._calculate_coherence(output_text, history)
        
        # 3. Completeness: todas as intenções do input foram endereçadas
        completeness = self._calculate_completeness(input_text, output_text)
        
        # 4. Efficiency: resposta adequada ao tamanho necessário
        efficiency = self._calculate_efficiency(output_text)
        
        overall = (relevance + coherence + completeness + efficiency) / 4.0
        
        flags = []
        if len(output_text) > 800:
            flags.append("too_long")
        if relevance < 0.2:
            flags.append("off_topic")
        if output_text.strip() == "":
            flags.append("empty_response")
            overall = 0.0

        return {
            "session_id": session_id,
            "turn_id": turn_id,
            "scores": {
                "relevance": round(relevance, 2),
                "coherence": round(coherence, 2),
                "completeness": round(completeness, 2),
                "efficiency": round(efficiency, 2)
            },
            "overall": round(overall, 2),
            "flags": flags,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }

    def _calculate_relevance(self, input_text: str, output_text: str) -> float:
        input_words = set(re.findall(r'\w+', input_text.lower()))
        output_words = set(re.findall(r'\w+', output_text.lower()))
        if not input_words:
            return 1.0
        
        # Remove stop words comuns (heurística simples)
        stop_words = {"e", "o", "a", "que", "em", "do", "da", "um", "para", "com", "não", "é", "uma", "os", "as"}
        input_filtered = input_words - stop_words
        
        if not input_filtered:
            return 1.0
            
        intersection = input_filtered.intersection(output_words)
        return min(len(intersection) / len(input_filtered) * 1.5, 1.0)

    def _calculate_coherence(self, output_text: str, history: List[Dict[str, str]]) -> float:
        if not history:
            return 1.0
            
        # Verifica se a resposta não é uma repetição exata da última resposta do assistente
        assistant_history = [h['content'] for h in history if h.get('role') == 'assistant']
        if not assistant_history:
            return 1.0
            
        last_resp = assistant_history[-1].strip().lower()
        curr_resp = output_text.strip().lower()
        
        if curr_resp == last_resp:
            return 0.1
            
        return 1.0

    def _calculate_completeness(self, input_text: str, output_text: str) -> float:
        # Heurística: se há interrogação no input, o output deve ter tamanho razoável
        if "?" in input_text:
            if len(output_text) > 30:
                return 1.0
            return 0.5
        return 0.9

    def _calculate_efficiency(self, output_text: str) -> float:
        length = len(output_text)
        if length == 0:
            return 0.0
        if length < 50:
            return 1.0
        if length < 300:
            return 0.9
        if length < 600:
            return 0.7
        return 0.4

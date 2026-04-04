from __future__ import annotations

import re
import time
import unicodedata
from typing import Any, Dict, List


class ResponseEvaluator:
    """
    Avalia a qualidade das respostas geradas pelo sistema Omini.
    Utiliza heuristicas leves para calcular scores multidimensionais.
    """

    def evaluate(
        self,
        session_id: str,
        turn_id: str,
        input_text: str,
        output_text: str,
        history: List[Dict[str, str]],
    ) -> Dict[str, Any]:
        task_category = self._detect_task_category(input_text)
        relevance = self._calculate_relevance(input_text, output_text, task_category)
        coherence = self._calculate_coherence(output_text, history)
        completeness = self._calculate_completeness(input_text, output_text, task_category)
        efficiency = self._calculate_efficiency(output_text)
        instruction_following = self._calculate_instruction_following(input_text, output_text)

        overall = (relevance + coherence + completeness + efficiency + instruction_following) / 5.0
        success_thresholds = {
            'short_prompt': 0.55,
            'memory': 0.6,
            'planning': 0.62,
            'logic': 0.72,
            'creativity': 0.68,
            'multi_perspective': 0.7,
            'explanation': 0.68,
        }
        success = overall >= success_thresholds.get(task_category, 0.68)

        flags = []
        if len(output_text) > 800:
            flags.append('too_long')
        if relevance < 0.2:
            flags.append('off_topic')
        if instruction_following < 0.5:
            flags.append('instruction_miss')
        if self._looks_like_generic_fallback(output_text):
            flags.append('generic_fallback')
            overall = min(overall, 0.45)
            success = False
        if output_text.strip() == '':
            flags.append('empty_response')
            overall = 0.0
            success = False

        return {
            'session_id': session_id,
            'turn_id': turn_id,
            'scores': {
                'relevance': round(relevance, 2),
                'coherence': round(coherence, 2),
                'completeness': round(completeness, 2),
                'efficiency': round(efficiency, 2),
                'instruction_following': round(instruction_following, 2),
            },
            'overall': round(overall, 2),
            'flags': flags,
            'task_category': task_category,
            'success': success,
            'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        }

    @staticmethod
    def _normalize_text(value: str) -> str:
        normalized = unicodedata.normalize('NFD', value or '')
        normalized = ''.join(char for char in normalized if unicodedata.category(char) != 'Mn')
        return re.sub(r'\s+', ' ', normalized.lower()).strip()

    def _looks_like_generic_fallback(self, output_text: str) -> bool:
        normalized = self._normalize_text(output_text)
        generic_markers = (
            'vou continuar a partir do contexto recente',
            'e um conceito que vale entender',
            'se quiser, eu tambem posso aprofundar',
            'posso te ajudar com explicacoes, planos, comparacoes',
        )
        return any(marker in normalized for marker in generic_markers)

    def _detect_task_category(self, input_text: str) -> str:
        normalized = self._normalize_text(input_text)
        words = re.findall(r'\w+', normalized)

        if len(words) <= 3:
            return 'short_prompt'
        if any(token in normalized for token in ('qual e o meu nome', 'voce lembra meu nome', 'com o que eu trabalho', 'meu nome e')):
            return 'memory'
        if 'perspectiva' in normalized or 'perspectivas' in normalized:
            return 'multi_perspective'
        if any(token in normalized for token in ('plano', 'etapas', 'startup', 'lancar uma startup', 'lancar uma empresa')):
            return 'planning'
        if any(token in normalized for token in ('analogia', 'imagine', 'cozinha', 'tempestade de areia em marte')):
            return 'creativity'
        if 'joao' in normalized and 'maria' in normalized:
            return 'logic'
        return 'explanation'

    def _calculate_instruction_following(self, input_text: str, output_text: str) -> float:
        normalized_input = self._normalize_text(input_text)
        normalized_output = self._normalize_text(output_text)
        checks: list[float] = []

        steps_match = re.search(r'(\d+)\s+etapas?', normalized_input)
        if steps_match:
            expected_steps = int(steps_match.group(1))
            rendered_steps = len(re.findall(r'(?:^|\n)\s*\d+\.', output_text))
            checks.append(1.0 if rendered_steps == expected_steps else 0.4 if rendered_steps > 0 else 0.0)

        if 'uma unica frase' in normalized_input or '1 frase' in normalized_input:
            sentence_count = len([part for part in re.split(r'[.!?]+', output_text) if part.strip()])
            checks.append(1.0 if sentence_count == 1 else 0.2)

        if 'analogia' in normalized_input:
            checks.append(1.0 if any(token in normalized_output for token in ('como ', 'livro de contabilidade', 'panela', 'cozinha')) else 0.2)

        if 'depois' in normalized_input:
            checks.append(1.0 if len([part for part in re.split(r'[.!?]+', output_text) if part.strip()]) >= 2 else 0.3)

        if 'perspectiva' in normalized_input or 'perspectivas' in normalized_input:
            expected_labels = ('economista', 'ambientalista', 'agricultor')
            checks.append(1.0 if all(label in normalized_output for label in expected_labels) else 0.2)

        if 'joao' in normalized_input:
            checks.append(1.0 if 'mesa' in normalized_output else 0.1)

        if not checks:
            return 0.9

        return sum(checks) / len(checks)

    def _calculate_relevance(self, input_text: str, output_text: str, task_category: str) -> float:
        normalized_input = self._normalize_text(input_text)
        normalized_output = self._normalize_text(output_text)

        if task_category == 'short_prompt' and any(token in normalized_input for token in ('ola', 'oi', 'bom dia', 'boa tarde', 'boa noite')):
            return 1.0 if any(token in normalized_output for token in ('ola', 'posso te ajudar', 'bom dia', 'boa tarde', 'boa noite')) else 0.2

        if task_category == 'memory' and 'nome' in normalized_input:
            return 1.0 if 'seu nome' in normalized_output else 0.3

        if task_category == 'memory' and 'trabalho' in normalized_input:
            return 1.0 if 'trabalha com' in normalized_output else 0.3

        input_words = set(re.findall(r'\w+', normalized_input))
        output_words = set(re.findall(r'\w+', normalized_output))
        if not input_words:
            return 1.0

        stop_words = {'e', 'o', 'a', 'que', 'em', 'do', 'da', 'um', 'para', 'com', 'nao', 'uma', 'os', 'as'}
        input_filtered = input_words - stop_words
        if not input_filtered:
            return 1.0

        intersection = input_filtered.intersection(output_words)
        return min(len(intersection) / len(input_filtered) * 1.5, 1.0)

    def _calculate_coherence(self, output_text: str, history: List[Dict[str, str]]) -> float:
        if not history:
            return 1.0

        assistant_history = [item['content'] for item in history if item.get('role') == 'assistant']
        if not assistant_history:
            return 1.0

        last_resp = assistant_history[-1].strip().lower()
        curr_resp = output_text.strip().lower()
        if curr_resp == last_resp:
            return 0.1
        return 1.0

    def _calculate_completeness(self, input_text: str, output_text: str, task_category: str) -> float:
        normalized_input = self._normalize_text(input_text)
        normalized_output = self._normalize_text(output_text)

        if task_category == 'memory' and 'nome' in normalized_input:
            return 1.0 if 'misael' in normalized_output or 'seu nome' in normalized_output else 0.4
        if task_category == 'memory' and 'trabalho' in normalized_input:
            return 1.0 if 'inteligencia artificial' in normalized_output or 'trabalha com' in normalized_output else 0.4
        if '?' in input_text and len(output_text) <= 30 and task_category not in {'short_prompt', 'memory'}:
            return 0.5
        if 'depois' in normalized_input and len([part for part in re.split(r'[.!?]+', output_text) if part.strip()]) < 2:
            return 0.4
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

from __future__ import annotations

import logging
import threading
import time
import json
from pathlib import Path
from typing import Any, Dict, List

from .evaluator import ResponseEvaluator
from .pattern_analyzer import PatternAnalyzer
from .strategy_updater import StrategyUpdater

class EvolutionLoop(threading.Thread):
    """
    Loop de auto-evolução real que roda em background (daemon thread).
    Avalia sessões recentes, analisa padrões de falha e ajusta a estratégia.
    """

    def __init__(self, brain_paths: Any, interval_minutes: int = 15):
        super().__init__(name="EvolutionLoop", daemon=True)
        self.paths = brain_paths
        self.interval = interval_minutes * 60
        self.running = True
        
        self.evaluator = ResponseEvaluator()
        self.analyzer = PatternAnalyzer()
        
        # Define diretório de snapshots e versão atual
        self.snapshots_dir = self.paths.python_root / "brain" / "evolution" / "snapshots"
        self.updater = StrategyUpdater(self.snapshots_dir)
        
        # Estratégia padrão inicial
        self.current_strategy = self._load_current_strategy()

    def run(self):
        logging.info(f"Evolution Loop iniciado. Ciclo: {self.interval}s")
        while self.running:
            try:
                self._evolution_cycle()
            except Exception as e:
                logging.error(f"Erro no ciclo de evolução: {str(e)}")
            
            time.sleep(self.interval)

    def _evolution_cycle(self):
        # 1. Carrega o learning.json que contém as avaliações acumuladas
        learning_data = self._load_learning_data()
        evaluations = learning_data.get("evolution_evals", [])
        
        if not evaluations:
            return

        # 2. Analisa padrões
        analysis = self.analyzer.analyze(evaluations)
        adjustments = analysis.get("recommended_adjustments", [])
        
        if not adjustments:
            return

        # 3. Propõe ajustes e gera nova estratégia se Score Gain > Threshold (heurística)
        # Por enquanto aplicamos se houver falhas recorrentes
        new_strategy = self.updater.update(self.current_strategy, adjustments)
        
        if new_strategy["version"] > self.current_strategy.get("version", 0):
            logging.info(f"Nova estratégia gerada: v{new_strategy['version']}")
            self.current_strategy = new_strategy
            self._persist_evolution_log(analysis, new_strategy)

    def _load_current_strategy(self) -> Dict[str, Any]:
        latest_ver = self.updater.get_latest_version()
        if latest_ver > 0:
            return self.updater.rollback(latest_ver)
            
        return {
            "version": 0,
            "last_update": None,
            "adjustments": [],
            "params": {
                "max_length_threshold": 500,
                "direct_memory_strictness": 0.5
            },
            "registry_overrides": {}
        }

    def _load_learning_data(self) -> Dict[str, Any]:
        if not self.paths.memory_json.exists():
            return {}
        try:
            with open(self.paths.memory_json, "r", encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}

    def _persist_evolution_log(self, analysis: Dict[str, Any], strategy: Dict[str, Any]):
        evolution_log_path = self.paths.python_root / "brain" / "evolution" / "evolution_history.json"
        
        log_entry = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "analysis": analysis,
            "new_version": strategy["version"]
        }
        
        logs = []
        if evolution_log_path.exists():
            with open(evolution_log_path, "r", encoding='utf-8') as f:
                logs = json.load(f)
        
        logs.append(log_entry)
        with open(evolution_log_path, "w", encoding='utf-8') as f:
            json.dump(logs, f, indent=2, ensure_ascii=False)

    def stop(self):
        self.running = False

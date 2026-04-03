from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List

class StrategyUpdater:
    """
    Gera novas versões da estratégia de evolução com base nas recomendações do analyzer.
    Mantém snapshots versionados para auditoria e rollback.
    """

    def __init__(self, snapshots_dir: Path):
        self.snapshots_dir = snapshots_dir
        self.snapshots_dir.mkdir(parents=True, exist_ok=True)

    def update(self, current_strategy: Dict[str, Any], adjustments: List[str]) -> Dict[str, Any]:
        if not adjustments:
            return current_strategy
            
        new_version = current_strategy.get("version", 0) + 1
        new_strategy = {
            "version": new_version,
            "last_update": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "adjustments": adjustments,
            "params": current_strategy.get("params", {}).copy(),
            "registry_overrides": current_strategy.get("registry_overrides", {}).copy()
        }
        
        # Aplica ajustes específicos
        for adj in adjustments:
            if adj == "adjust_efficiency_threshold":
                # Reduz o threshold de comprimento se houver excesso de respostas longas
                curr_max = new_strategy["params"].get("max_length_threshold", 500)
                new_strategy["params"]["max_length_threshold"] = max(200, curr_max - 50)
                
            elif adj == "rebalance_intent_weights":
                # Incrementa prioridade de roteamento (exemplo hipotético)
                overrides = new_strategy["registry_overrides"].get("intent_priority", {})
                for intent in ["decision", "dinheiro"]:
                    overrides[intent] = overrides.get(intent, 1.0) + 0.1
                new_strategy["registry_overrides"]["intent_priority"] = overrides
                
            elif adj == "reinforce_fallback_strategy":
                # Ajusta a agressividade da busca por memória direta
                new_strategy["params"]["direct_memory_strictness"] = 0.8
                
        self._save_snapshot(new_strategy)
        return new_strategy

    def _save_snapshot(self, strategy: Dict[str, Any]):
        version = strategy.get("version", 0)
        snapshot_file = self.snapshots_dir / f"strategy_v{version}.json"
        
        with open(snapshot_file, "w", encoding='utf-8') as f:
            json.dump(strategy, f, indent=2, ensure_ascii=False)

    def rollback(self, version: int) -> Dict[str, Any]:
        snapshot_file = self.snapshots_dir / f"strategy_v{version}.json"
        if not snapshot_file.exists():
            raise FileNotFoundError(f"Snapshot version {version} not found.")
            
        with open(snapshot_file, "r", encoding='utf-8') as f:
            return json.load(f)

    def get_latest_version(self) -> int:
        snapshots = list(self.snapshots_dir.glob("strategy_v*.json"))
        if not snapshots:
            return 0
        
        versions = []
        for s in snapshots:
            try:
                ver = int(s.stem.replace("strategy_v", ""))
                versions.append(ver)
            except ValueError:
                continue
        
        return max(versions) if versions else 0

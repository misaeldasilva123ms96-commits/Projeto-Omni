from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

def run_dashboard():
    """
    CLI para visualizar o status da auto-evolução do Projeto Omini.
    Uso: python -m brain.evolution.dashboard
    """
    # Localização dos arquivos (baseado no diretório atual)
    python_root = Path(__file__).resolve().parents[2]
    learning_path = python_root / "memory" / "learning.json"
    evolution_path = python_root / "brain" / "evolution" / "evolution_history.json"
    snapshots_dir = python_root / "brain" / "evolution" / "snapshots"

    print("\n" + "="*50)
    print("      OMINI AI PLATFORM - EVOLUTION DASHBOARD")
    print("="*50)

    # 1. Pontuação Média e Últimas Avaliações
    if learning_path.exists():
        with open(learning_path, "r", encoding='utf-8') as f:
            data = json.load(f)
            evals = data.get("evolution_evals", [])
            if evals:
                avg_score = sum(ev.get("overall", 0) for ev in evals) / len(evals)
                print(f"[*] Score Médio Recente: {avg_score:.2f} ({len(evals)} turnos)")
                
                # Top Padrões de Falha (Flags)
                flags = {}
                for ev in evals:
                    for f_item in ev.get("flags", []):
                        flags[f_item] = flags.get(f_item, 0) + 1
                
                sorted_flags = sorted(flags.items(), key=lambda x: x[1], reverse=True)[:3]
                if sorted_flags:
                    print(f"[*] Principais Pontos de Melhoria: ")
                    for f_name, count in sorted_flags:
                        print(f"   - {f_name}: {count} ocorrências")
    else:
        print("[!] Nenhum log de evolução encontrado em learning.json.")

    # 2. Histórico de Estratégias
    print("\n" + "-"*50)
    print("  HISTÓRICO DE VERSÕES (SNAPSHOTS)")
    print("-"*50)
    
    if snapshots_dir.exists():
        snapshots = sorted(list(snapshots_dir.glob("strategy_v*.json")), key=lambda x: x.stat().st_mtime, reverse=True)
        if snapshots:
            for s in snapshots[:5]:
                with open(s, "r", encoding='utf-8') as f:
                    s_data = json.load(f)
                    time_upd = s_data.get("last_update", "desconhecido")
                    ver = s_data.get("version", "?")
                    adjusts = ", ".join(s_data.get("adjustments", []))
                    print(f"[v{ver}] Atualizado em: {time_upd}")
                    print(f"      Ajustes: {adjusts}")
        else:
            print("[.] Nenhuma versão de estratégia gerada ainda.")
    else:
        print("[!] Diretório de snapshots não existe.")

    # 3. Último Ciclo de Evolução
    if evolution_path.exists():
        with open(evolution_path, "r", encoding='utf-8') as f:
            history = json.load(f)
            if history:
                last = history[-1]
                print("\n" + "-"*50)
                print(f"  ÚLTIMO CICLO: {last.get('timestamp', 'N/A')}")
                print(f"  Analise: {last.get('analysis', {}).get('recommended_adjustments', [])}")
                print("-"*50)

    print("\n" + "="*50)

if __name__ == "__main__":
    run_dashboard()

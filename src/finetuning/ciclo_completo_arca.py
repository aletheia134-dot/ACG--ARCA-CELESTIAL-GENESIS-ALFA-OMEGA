# ciclo_completo_arca.py

#!/usr/bin/env python3
"""
ðŸ”„ CICLO COMPLETO AUTOMÍTICO PARA ARCA
Treina, converte e substitui todas as IAs em sequência
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from .orquestrador_com_conversor import OrquestradorComConversor

def ciclo_automatico():
    """Executa ciclo completo para todas as IAs automaticamente"""
    
    print("""
â•”â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•—
â•‘     ðŸ”„ CICLO COMPLETO AUTOMÍTICO - ARCA                 â•‘
â•‘     Treinamento â†’ Conversão â†’ Substituição              â•‘
â•šâ•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    """)
    
    orquestrador = OrquestradorComConversor()
    
    for nome_ia in orquestrador.ias.keys():
        print(f"\n{'='*60}")
        print(f"ðŸš€ PROCESSANDO {nome_ia.upper()}")
        print(f"{'='*60}")
        
        # Perguntar se quer processar esta IA
        resposta = input(f"\nProcessar {nome_ia.upper()}? (s/n/t=todas): ").lower()
        
        if resposta == 't':
            # Processar todas a partir daqui
            for ia in list(orquestrador.ias.keys())[list(orquestrador.ias.keys()).index(nome_ia):]:
                print(f"\nðŸ“Œ Processando {ia.upper()}...")
                orquestrador.treinar_ia(ia)
            break
        elif resposta == 's':
            orquestrador.treinar_ia(nome_ia)
        else:
            print(f"â­ï¸  Pulando {nome_ia.upper()}")

if __name__ == "__main__":
    ciclo_automatico()

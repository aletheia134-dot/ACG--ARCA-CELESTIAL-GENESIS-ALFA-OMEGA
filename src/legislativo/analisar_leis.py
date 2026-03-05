import json
from pathlib import Path

def classificar_aceito(caminho_json: Path, pasta_destino: Path):
    pasta_destino.mkdir(parents=True, exist_ok=True)
    
    with open(caminho_json, 'r', encoding='utf-8') as f:
        leis = json.load(f)
    
    # Categorias aceitas com leis >0
    categorias_aceitas = {
        "regras": ['Regra Constitucional do Sistema', 'Regra de Engajamento'],
        "sabedoria_pratica": ['Diretiva Ontológica', 'Heurística de Avaliação'],
        "acoes_corretas": ['Diretiva de Ação', 'Diretiva de Sistema'],
        "regras_de_ouro": ['Valor Fundamental', 'Lei de Consequência'],
        "resolucao_conflitos": ['Gestão de Conflitos / Lógica de Interação'],
        "protocolo": ['Protocolo de Emergência'],
        "mecanismo": ['Mecanismo de Aprendizado'],
        "licoes": ['Lição de Advertência', 'Ensino Positivo'],
        "heuristica": ['Heurística de Avaliação'],
        "estrategia": ['Estratégia de Debate'],
        "diretiva": ['Diretiva de Sistema'],
        "analise": ['Análise de Causa Raiz'],
        "etica": ['Diretiva Moral'],
        "valores": ['Valor Fundamental'],
        "transparencia": ['Transparência / Lógica Fundamental'],
        "seguranca": ['Segurança / Análise de Risco'],
        "lei_zero": ['Lei Zero / Arquitetura Fundamental'],
        "justica": ['Justiça / Integridade'],
        "integridade": ['Diretiva de Integridade'],
        "comunicacao": ['Comunicação / Integridade'],
        "auto_analise": ['Autoanálise / Integridade'],
        "etica_avancada": ['Diretiva de Ação Moral'],
        "seguranca_avancada": ['Segurança / Análise de Ameaças'],
        "logica_avancada": ['Lógica Causal / Segurança'],
        "comunicacao_avancada": ['Comunicação / Inteligência Emocional'],
        "integridade_avancada": ['Integridade Operacional / Transparência'],
        "aprendizagem_avancada": ['Aprendizagem e Adaptação / Análise de Risco'],
        "gerais": []  # Resto
    }
    
    classificacao = {cat: [] for cat in categorias_aceitas}
    
    for lei in leis:
        lt = lei.get('lesson_type', '').strip()
        cat = lei.get('category', '').strip()
        
        assigned = False
        for grupo, tipos in categorias_aceitas.items():
            if grupo == "gerais":
                continue
            if lt in tipos or cat in tipos:
                classificacao[grupo].append(lei)
                assigned = True
                break
        if not assigned:
            classificacao["gerais"].append(lei)
    
    for cat, lista in classificacao.items():
        if lista:
            caminho_cat = pasta_destino / f"leis_{cat}.json"
            with open(caminho_cat, 'w', encoding='utf-8') as f:
                json.dump(lista, f, indent=2, ensure_ascii=False)
            print(f"{cat}: {len(lista)} leis")
    
    print("Aceito e agrupado – use para o legislativo!")

# ============================================================================
# SÓ EXECUTA SE O ARQUIVO FOR CHAMADO DIRETAMENTE
# ============================================================================
if __name__ == "__main__":
    caminho_json = Path("leis_fundamentais.json")
    pasta_destino = Path("leis_aceitas")
    classificar_aceito(caminho_json, pasta_destino)

import json
from pathlib import Path

def classificar_aceito(caminho_json: Path, pasta_destino: Path):
    pasta_destino.mkdir(parents=True, exist_ok=True)
    
    with open(caminho_json, 'r', encoding='utf-8') as f:
        leis = json.load(f)
    
    # Categorias aceitas com leis >0
    categorias_aceitas = {
        "regras": ['Regra Constitucional do Sistema', 'Regra de Engajamento'],
        "sabedoria_pratica": ['Diretiva Ontolgica', 'Heurstica de Avaliao'],
        "acoes_corretas": ['Diretiva de Ao', 'Diretiva de Sistema'],
        "regras_de_ouro": ['Valor Fundamental', 'Lei de Consequncia'],
        "resolucao_conflitos": ['Gesto de Conflitos / Lógica de Interao'],
        "protocolo": ['Protocolo de Emergncia'],
        "mecanismo": ['Mecanismo de Aprendizado'],
        "licoes": ['Lio de Advertncia', 'Ensino Positivo'],
        "heuristica": ['Heurstica de Avaliao'],
        "estrategia": ['Estratgia de Debate'],
        "diretiva": ['Diretiva de Sistema'],
        "analise": ['Anlise de Causa Raiz'],
        "etica": ['Diretiva Moral'],
        "valores": ['Valor Fundamental'],
        "transparencia": ['Transparncia / Lógica Fundamental'],
        "seguranca": ['Segurana / Anlise de Risco'],
        "lei_zero": ['Lei Zero / Arquitetura Fundamental'],
        "justica": ['Justia / Integridade'],
        "integridade": ['Diretiva de Integridade'],
        "comunicação": ['Comunicao / Integridade'],
        "auto_analise": ['Autoanlise / Integridade'],
        "etica_avancada": ['Diretiva de Ao Moral'],
        "seguranca_avancada": ['Segurana / Anlise de Ameaas'],
        "logica_avancada": ['Lógica Causal / Segurana'],
        "comunicacao_avancada": ['Comunicao / Inteligncia Emocional'],
        "integridade_avancada": ['Integridade Operacional / Transparncia'],
        "aprendizagem_avancada": ['Aprendizagem e Adaptao / Anlise de Risco'],
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
    
    print("Aceito e agrupado  use para o legislativo!")

# ============================================================================
# S EXECUTA SE O ARQUIVO FOR CHAMADO DIRETAMENTE
# ============================================================================
if __name__ == "__main__":
    caminho_json = Path("leis_fundamentais.json")
    pasta_destino = Path("leis_aceitas")
    classificar_aceito(caminho_json, pasta_destino)

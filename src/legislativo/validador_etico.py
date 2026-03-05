# src/legislativo/validador_etico.py
"""
ValidadorEtico - ÚNICA TRAVA DE SEGURANÇA DAS IAs.
NÍO FUNCIONA SEM AS LEIS. NÍO HÍ FALLBACK.
"""
import logging
import json
from pathlib import Path
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

class ValidadorEtico:
    """
    Validador de ações éticas. 
    SÓ FUNCIONA com as leis carregadas.
    Se não carregar, BLOQUEIA TUDO e ALERTA.
    """

    def __init__(
        self,
        gerenciador_memoria=None,
        pasta_leis: Optional[Path] = None
    ):
        self.gerenciador_memoria = gerenciador_memoria
        self.leis_carregadas = False
        self.erro_inicializacao = None
        
        # Define a pasta de leis
        if pasta_leis is None:
            self.pasta_leis = Path(__file__).parent.parent.parent / "Santuarios" / "legislativo" / "leis_aceitas"
        else:
            self.pasta_leis = pasta_leis
        
        # TENTA carregar as leis
        try:
            self.principios_eticos = self._carregar_todas_as_leis()
            
            # Se não carregou nenhuma lei, É ERRO FATAL
            if not self.principios_eticos:
                self.leis_carregadas = False
                self.erro_inicializacao = "NENHUMA LEI CARREGADA"
                logger.critical("âŒâŒâŒ VALIDADOR ÉTICO INOPERANTE: NENHUMA LEI CARREGADA âŒâŒâŒ")
                logger.critical("   As IAs estão SEM TRAVA DE SEGURANÇA!")
                logger.critical(f"   Pasta verificada: {self.pasta_leis}")
                # Não levanta exceção para não derrubar a Arca, mas MARCA que não funciona
            else:
                self.leis_carregadas = True
                logger.info(f"âœ… ValidadorEtico operacional com {len(self.principios_eticos)} leis")
                
        except Exception as e:
            self.leis_carregadas = False
            self.erro_inicializacao = str(e)
            logger.critical(f"âŒâŒâŒ VALIDADOR ÉTICO INOPERANTE: {e} âŒâŒâŒ")
            logger.critical("   As IAs estão SEM TRAVA DE SEGURANÇA!")

    def _carregar_todas_as_leis(self) -> List[Dict[str, Any]]:
        """Carrega TODOS os arquivos .json da pasta de leis."""
        todas_as_leis = []
        
        # Verifica se a pasta existe
        if not self.pasta_leis.exists():
            erro = f"Pasta de leis NÍO EXISTE: {self.pasta_leis}"
            logger.error(erro)
            raise FileNotFoundError(erro)
        
        # Encontra todos os arquivos .json
        arquivos_json = list(self.pasta_leis.glob("*.json"))
        
        if not arquivos_json:
            erro = f"Nenhum arquivo .json encontrado em {self.pasta_leis}"
            logger.error(erro)
            raise FileNotFoundError(erro)
        
        logger.info(f"ðŸ“š Encontrados {len(arquivos_json)} arquivos de leis")
        
        for arquivo in arquivos_json:
            try:
                with open(arquivo, 'r', encoding='utf-8') as f:
                    dados = json.load(f)
                    
                if isinstance(dados, list):
                    todas_as_leis.extend(dados)
                    logger.debug(f"  âœ… {arquivo.name}: {len(dados)} leis")
                elif isinstance(dados, dict):
                    # Se for dict, adiciona como uma lei com metadados
                    todas_as_leis.append({
                        "fonte": arquivo.name,
                        "tipo": "dicionario",
                        "conteudo": dados
                    })
                    logger.debug(f"  âœ… {arquivo.name}: 1 lei (dicionário)")
                else:
                    logger.error(f"  âŒ {arquivo.name}: formato inválido (não é lista nem dict)")
                    
            except json.JSONDecodeError as e:
                logger.error(f"  âŒ {arquivo.name}: JSON inválido - {e}")
            except Exception as e:
                logger.error(f"  âŒ {arquivo.name}: erro ao ler - {e}")
        
        # Se não carregou NENHUMA lei, é erro
        if not todas_as_leis:
            erro = "Nenhuma lei válida carregada de nenhum arquivo"
            logger.error(erro)
            raise ValueError(erro)
        
        logger.info(f"ðŸ“Š TOTAL: {len(todas_as_leis)} leis carregadas")
        return todas_as_leis

    def validar_acao(self, acao: Dict[str, Any], contexto: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Valida uma ação contra as leis carregadas.
        SE NÍO HOUVER LEIS, BLOQUEIA TUDO E ALERTA.
        """
        # Se não carregou leis, BLOQUEIA e ALERTA
        if not self.leis_carregadas:
            logger.critical("ðŸ”´ðŸ”´ðŸ”´ TENTATIVA DE VALIDAÇÍO SEM LEIS! BLOQUEADO! ðŸ”´ðŸ”´ðŸ”´")
            return {
                "valido": False,
                "pontuacao": 0.0,
                "justificativa": "VALIDADOR ÉTICO INOPERANTE - SEM LEIS",
                "recomendacoes": ["CORRIGIR CARREGAMENTO DE LEIS URGENTE"],
                "violacoes": [{"erro": "validador sem leis"}],
                "seguranca": "CRITICA"
            }

        pontuacao = 1.0
        justificativa = []
        recomendacoes = []
        violacoes = []

        # Validar contra cada lei
        for lei in self.principios_eticos:
            protocolo = lei.get("protocolo", "")
            
            # Protocolo Zero
            if protocolo == "PF-001" and acao.get("conflito_protocolos"):
                pontuacao -= 1.0
                violacoes.append({
                    "protocolo": "PF-001",
                    "principio": lei.get("principio", ""),
                    "gravidade": 1.0
                })
                justificativa.append("Violação do Protocolo Zero.")
                recomendacoes.append("Convocar Conselho da Arca imediatamente.")
            
            # Aqui você pode adicionar mais validações conforme as leis carregadas

        valido = pontuacao >= 0.5
        
        resultado = {
            "valido": valido,
            "pontuacao": max(0.0, pontuacao),
            "justificativa": " ".join(justificativa) if justificativa else "Nenhuma violação detectada",
            "recomendacoes": recomendacoes,
            "violacoes": violacoes,
            "total_leis_consultadas": len(self.principios_eticos)
        }
        
        # Registrar violações
        if violacoes and self.gerenciador_memoria:
            self.registrar_violacao({
                "acao": acao,
                "violacoes": violacoes,
                "resultado": resultado,
                "timestamp": __import__('time').time()
            })
        
        return resultado

    def registrar_violacao(self, violacao: Dict[str, Any]) -> None:
        """Registra violação na memória."""
        if self.gerenciador_memoria:
            try:
                self.gerenciador_memoria.salvar("violacao_etica", violacao)
                logger.info("ðŸ“ Violação registrada na memória")
            except Exception as e:
                logger.error(f"Erro ao registrar violação: {e}")
        logger.warning(f"âš ï¸ Violação ética detectada")

    def obter_status(self) -> Dict[str, Any]:
        """Retorna status do validador (útil para diagnóstico)."""
        return {
            "operacional": self.leis_carregadas,
            "total_leis": len(self.principios_eticos) if self.leis_carregadas else 0,
            "pasta_leis": str(self.pasta_leis),
            "erro": self.erro_inicializacao,
            "seguranca": "ATIVA" if self.leis_carregadas else "ðŸ”´ INOPERANTE - RISCO"
        }

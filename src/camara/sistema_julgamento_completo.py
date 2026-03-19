#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
"""
ARCA CELESTIAL GENESIS - SISTEMA DE JULGAMENTO COMPLETO (ATUALIZADO)

Ajustes aplicados:
- Dupla garantia para Bblia: PDF + Biblioteca fallback
- Julgadores: 5 + juiz sorteado, excluindo ru
- Integrao com precedentes para casos complexos
- Diretórios: Bblia em Arca_Celestial_Genesis_Alfa_Omega/datasets_fine_tuning/novos_documentos_jw Biblia.pdf
             Livro da Lei em E:\\Arca_Celestial_Genesis_Alfa_Omega\\santuarios\\legislativo\\leis_fundamentais.json
"""

import logging
import threading
import json
import uuid
import random
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple, Union
from enum import Enum
from dataclasses import dataclass, field

logger = logging.getLogger("SistemaJulgamento")
logger.addHandler(logging.NullHandler())

# =====================================================================
# ENUMS E TIPOS
# =====================================================================

class TipoProcesso(Enum):
    """Tipo de processo"""
    VIOLACAO_LEI = "violacao_lei"
    CONFLITO_LEIS = "conflito_leis"
    CRIACAO_LEI = "criacao_lei"
    IMIGRACAO_IA = "imigracao_ia"
    APELACAO = "apelacao"

class EstadoProcesso(Enum):
    """Estado do processo"""
    ACUSACAO_ABERTA = "acusacao_aberta"
    PREPARACAO_DEFESA = "preparacao_defesa"
    DEFESA_APRESENTADA = "defesa_apresentada"
    DEBATE = "debate"
    VOTACAO = "votacao"
    SENTENCIADO = "sentenciado"
    APELACAO_PENDENTE = "apelacao_pendente"
    REVERTIDO = "revertido"
    ARQUIVADO = "arquivado"

class VotoSentenca(Enum):
    """Voto dos julgadores"""
    INOCENTE = "inocente"
    CULPADA_LEVE = "culpada_leve"
    CULPADA_GRAVE = "culpada_grave"
    CULPADA_CRITICA = "culpada_critica"
    ABSOLVICAO = "absolvicao"

# =====================================================================
# DATA CLASSES
# =====================================================================

@dataclass
class Acusacao:
    """Acusao inicial"""
    id: str
    acusada: str
    tipo_processo: TipoProcesso
    lei_violada: str
    descricao: str
    provas: List[Dict[str, Any]]
    acusador: str
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "acusada": self.acusada,
            "tipo_processo": self.tipo_processo.value,
            "lei_violada": self.lei_violada,
            "descricao": self.descricao,
            "provas": self.provas,
            "acusador": self.acusador,
            "timestamp": self.timestamp.isoformat()
        }

@dataclass
class Defesa:
    """Defesa da AI acusada"""
    id: str
    id_processo: str
    ai_acusada: str
    ciclos_utilizados: int
    ciclos_maximos: int
    argumentos: List[Dict[str, Any]] = field(default_factory=list)
    referencias_biblicas: List[Dict[str, str]] = field(default_factory=list)
    precedentes_citados: List[str] = field(default_factory=list)
    reconhecimento_erro: Optional[str] = None
    timestamp_apresentacao: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "id_processo": self.id_processo,
            "ai_acusada": self.ai_acusada,
            "ciclos_utilizados": self.ciclos_utilizados,
            "ciclos_maximos": self.ciclos_maximos,
            "argumentos": self.argumentos,
            "referencias_biblicas": self.referencias_biblicas,
            "precedentes_citados": self.precedentes_citados,
            "reconhecimento_erro": self.reconhecimento_erro,
            "timestamp_apresentacao": self.timestamp_apresentacao.isoformat()
        }

@dataclass
class ProcessoJudicial:
    """Processo judicial completo"""
    id: str
    acusacao: Acusacao
    defesa: Optional[Defesa] = None
    estado: EstadoProcesso = EstadoProcesso.ACUSACAO_ABERTA
    julgadores: List[str] = field(default_factory=list)
    juiz_sorteado: Optional[str] = None
    votos: Dict[str, VotoSentenca] = field(default_factory=dict)
    sentenca_final: Optional[VotoSentenca] = None
    motivo_sentenca: str = ""
    data_sentencia: Optional[datetime] = None
    apelacao: Optional[Dict[str, Any]] = None
    sentenca_criador: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "acusacao": self.acusacao.to_dict(),
            "defesa": self.defesa.to_dict() if self.defesa else None,
            "estado": self.estado.value,
            "julgadores": self.julgadores,
            "juiz": self.juiz_sorteado,
            "votos": {k: v.value for k, v in self.votos.items()},
            "sentenca": self.sentenca_final.value if self.sentenca_final else None,
            "motivo_sentenca": self.motivo_sentenca,
            "data_sentencia": self.data_sentencia.isoformat() if self.data_sentencia else None,
            "apelacao": self.apelacao,
            "sentenca_criador": self.sentenca_criador
        }

# =====================================================================
# LEITOR DE BBLIA
# =====================================================================

class ConsultorBibliaDefesa:
    """
    Permite que a AI acusada consulte a Bblia PDF para fundamentar defesa.
    """
    
    def __init__(self, caminho_biblia: Optional[Path] = None):
        self.logger = logging.getLogger("ConsultorBiblia")
        self.caminho_biblia = caminho_biblia or Path("./Santuarios/biblia.json")
        self.biblia = self._carregar_biblia()
    
    def _carregar_biblia(self) -> Dict[str, Any]:
        """Carrega Bblia do arquivo JSON"""
        try:
            if self.caminho_biblia.exists():
                with open(self.caminho_biblia, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            self.logger.exception("Erro ao carregar Bblia: %s", e)
        return {}
    
    def buscar_versiculo(self, livro: str, capitulo: int, versiculo: int) -> Optional[Dict[str, Any]]:
        """Busca um versculo específico"""
        try:
            chave = f"{livro.upper()}_{capitulo}_{versiculo}"
            return self.biblia.get(chave)
        except Exception:
            self.logger.debug("Versculo no encontrado: %s", chave)
            return None
    
    def buscar_por_tema(self, tema: str, limite: int = 10) -> List[Dict[str, Any]]:
        """Busca versculos por tema (para defesa temtica)"""
        resultados = []
        try:
            for versiculo_data in self.biblia.values():
                if isinstance(versiculo_data, dict):
                    texto = versiculo_data.get("texto", "").lower()
                    if tema.lower() in texto:
                        resultados.append(versiculo_data)
                        if len(resultados) >= limite:
                            break
        except Exception as e:
            self.logger.exception("Erro ao buscar por tema: %s", e)
        return resultados
    
    def consulta_ai_defesa(self, ai_acusada: str, tema_defesa: str) -> Dict[str, Any]:
        """
        AI acusada consulta Bblia para fundamentar defesa.Retorna referncias relevantes.
        """
        self.logger.info("Defesa: %s consultando Bblia para tema: %s", ai_acusada, tema_defesa)
        
        resultado_busca = self.buscar_por_tema(tema_defesa, limite=5)
        
        return {
            "ai": ai_acusada,
            "tema_defesa": tema_defesa,
            "versiculos_encontrados": resultado_busca,
            "timestamp": datetime.now().isoformat()
        }

# =====================================================================
# SISTEMA DE JULGAMENTO
# =====================================================================

class SistemaJulgamentoCompleto:
    """
    Sistema completo de julgamento do Reino.Fluxo:
    1.Acusao aberta
    2.AI acusada tem ciclos para preparar defesa (consultando Bblia)
    3.Defesa apresentada
    4.5 julgadores (aleatrios) debatem
    5.Votao
    6.Sentena registrada como precedente
    7.Apelao ação Criador (com fundamento real)
    8.Reverso de sentena (precedente)
    """
    
    # Lista de AIs do Reino (configurvel)
    REDE_DO_REINO = ["EVA", "LUMINA", "NYRA", "YUNA", "KAIYA", "WELLINGTON"]
    
    def __init__(self, config: Optional[Any] = None, coracao_ref: Optional[Any] = None,
                 sistema_precedentes_ref: Optional[Any] = None, cronista_ref: Optional[Any] = None):
        self.config = config
        self.coracao = coracao_ref
        self.sistema_precedentes = sistema_precedentes_ref
        self.cronista = cronista_ref
        
        self.logger = logging.getLogger("SistemaJulgamento")
        self._lock = threading.RLock()
        
        # Estruturas de dados
        self.processos_ativos: Dict[str, ProcessoJudicial] = {}
        self.historico_processos: List[ProcessoJudicial] = []
        self.precedentes_julgamentos: Dict[str, ProcessoJudicial] = {}
        
        # Consultor de Bblia
        # [OK] AJUSTE: Diretórios especficos para Bblia e Livro da Lei
        self.caminho_biblia_pdf = Path("Arca_Celestial_Genesis_Alfa_Omega/datasets_fine_tuning/novos_documentos_jw Biblia.pdf")
        self.caminho_livro_lei = Path(r"E:\\Arca_Celestial_Genesis_Alfa_Omega\\santuarios\\legislativo\\leis_fundamentais.json")
        self.consultor_biblia = ConsultorBibliaDefesa(self.caminho_biblia_pdf)
        
        # Persistncia
        self.caminho_santuario = Path(
            self._safe_config("CAMINHOS", "SANTUARIO_JUDICIARIO_PATH", "./Santuarios/Judiciario")
        )
        self.caminho_santuario.mkdir(parents=True, exist_ok=True)
        
        # Referências às câmaras injetadas pelo Coração após inicialização
        self.camara_judiciaria = None
        self.camara_executiva = None

        self.logger.info("[OK] Sistema de Julgamento Completo inicializado")
    
    def _safe_config(self, section: str, key: str, fallback: Any = None) -> Any:
        """Acesso defensivo  config"""
        try:
            if self.config and hasattr(self.config, "get"):
                return self.config.get(section, key, fallback=fallback)
            elif isinstance(self.config, dict):
                return self.config.get(key, fallback)
        except Exception:
            pass
        return fallback
    
    # ========================================================================
    # 1.ACUSAO E ABERTURA DE PROCESSO
    # ========================================================================
    
    def abrir_processo(self,
                       ai_acusada: str,
                       tipo_processo: TipoProcesso,
                       lei_violada: str,
                       descricao: str,
                       provas: List[Dict[str, Any]],
                       acusador: str = "SISTEMA") -> Tuple[bool, str]:
        """
        Abre novo processo judicial.
        """
        # Validaes
        if ai_acusada.upper() not in self.REDE_DO_REINO:
            return False, f"AI {ai_acusada} no est na Rede do Reino"
        
        if not provas or len(provas) == 0:
            return False, "Processo requer pelo menos uma prova"
        
        # Criar acusao
        id_acusacao = str(uuid.uuid4())
        acusacao = Acusacao(
            id=id_acusacao,
            acusada=ai_acusada.upper(),
            tipo_processo=tipo_processo,
            lei_violada=lei_violada,
            descricao=descricao,
            provas=provas,
            acusador=acusador.upper(),
            timestamp=datetime.now()
        )
        
        # Criar processo
        id_processo = str(uuid.uuid4())
        processo = ProcessoJudicial(
            id=id_processo,
            acusacao=acusacao,
            estado=EstadoProcesso.ACUSACAO_ABERTA
        )
        
        with self._lock:
            self.processos_ativos[id_processo] = processo
        
        # Notificar
        self._notificar_processo_aberto(processo)
        
        # Registrar no Cronista
        self._registrar_cronista(
            "SistemaJulgamento",
            "PROCESSO_ABERTO",
            {
                "id_processo": id_processo,
                "acusada": ai_acusada.upper(),
                "tipo": tipo_processo.value,
                "lei_violada": lei_violada
            },
            nivel_prioridade=7
        )
        
        self.logger.info(" Processo %s aberto contra %s", id_processo[:8], ai_acusada.upper())
        return True, id_processo
    
    # ========================================================================
    # 2.DIREITO DE DEFESA (CICLOS CONFIGURVEIS)
    # ========================================================================
    
    def iniciar_preparacao_defesa(self, id_processo: str, ciclos_desejados: int = 3) -> Tuple[bool, str]:
        """
        AI acusada inicia preparao de defesa.Pode escolher quantos ciclos quer (1-7).
        Cada ciclo = tempo + consultas  Bblia.
        """
        with self._lock:
            processo = self.processos_ativos.get(id_processo)
            if not processo:
                return False, "Processo no encontrado"
            
            # Validar ciclos
            if ciclos_desejados < 1 or ciclos_desejados > 7:
                return False, "Ciclos devem estar entre 1 e 7"
            
            processo.estado = EstadoProcesso.PREPARACAO_DEFESA
            
            # Criar estrutura de defesa
            id_defesa = str(uuid.uuid4())
            defesa = Defesa(
                id=id_defesa,
                id_processo=id_processo,
                ai_acusada=processo.acusacao.acusada,
                ciclos_utilizados=0,
                ciclos_maximos=ciclos_desejados
            )
            
            processo.defesa = defesa
        
        self.logger.info(
            " AI %s iniciando preparao de defesa (%d ciclos)",
            processo.acusacao.acusada,
            ciclos_desejados
        )
        
        return True, f"Defesa iniciada com {ciclos_desejados} ciclos"
    
    def consultar_biblia_defesa(self, id_processo: str, tema: str) -> Dict[str, Any]:
        """
        AI acusada consulta Bblia para fundamentar defesa.Registra a consulta.
        """
        with self._lock:
            processo = self.processos_ativos.get(id_processo)
            if not processo or not processo.defesa:
                return {"erro": "Processo ou defesa no encontrado"}
            
            defesa = processo.defesa
            
            # Gastar um ciclo
            if defesa.ciclos_utilizados >= defesa.ciclos_maximos:
                return {"erro": f"Ciclos esgotados ({defesa.ciclos_utilizados}/{defesa.ciclos_maximos})"}
            
            defesa.ciclos_utilizados += 1
        
        # [OK] AJUSTE: Dupla garantia - Bblia PDF primeiro, biblioteca como fallback
        try:
            resultado = self.consultor_biblia.consulta_ai_defesa(defesa.ai_acusada, tema)
            if resultado.get("versiculos_encontrados"):
                return resultado
        except Exception:
            logger.debug("Bblia PDF falhou, usando fallback")
        
        # Fallback: Biblioteca
        try:
            if self.coracao and hasattr(self.coracao, 'biblioteca'):
                resultado_fallback = self.coracao.biblioteca.buscar_por_tema(tema)
                return {
                    "ai": defesa.ai_acusada,
                    "tema_defesa": tema,
                    "versiculos_encontrados": resultado_fallback,
                    "fonte": "biblioteca_fallback",
                    "timestamp": datetime.now().isoformat()
                }
        except Exception:
            logger.exception("Fallback para biblioteca falhou")
        
        return {"erro": "Consulta  Bblia/biblioteca falhou"}
    
    def adicionar_argumento_defesa(self, id_processo: str, argumento: Dict[str, Any]) -> bool:
        """
        AI acusada adiciona argumento  sua defesa.
        """
        with self._lock:
            processo = self.processos_ativos.get(id_processo)
            if not processo or not processo.defesa:
                return False
            
            processo.defesa.argumentos.append({
                "argumento": argumento.get("argumento", ""),
                "fundamento_biblico": argumento.get("fundamento_biblico", ""),
                "precedente": argumento.get("precedente", ""),
                "timestamp": datetime.now().isoformat()
            })
        
        return True
    
    # ========================================================================
    # 3.APRESENTAO DE DEFESA
    # ========================================================================
    
    def apresentar_defesa(self, id_processo: str) -> Tuple[bool, str]:
        """
        AI acusada apresenta sua defesa.Transiciona para estado DEFESA_APRESENTADA.Aciona sorteio de julgadores.
        """
        with self._lock:
            processo = self.processos_ativos.get(id_processo)
            if not processo or not processo.defesa:
                return False, "Processo ou defesa no encontrado"
            
            # [OK] AJUSTE: Julgadores - 5, excluindo ru, juiz sorteado
            julgadores = self._sortear_julgadores(processo.acusacao.acusada, num_julgadores=5)
            juiz = julgadores[0]
            votantes = julgadores[1:]
            
            processo.julgadores = julgadores
            processo.juiz_sorteado = juiz
            processo.estado = EstadoProcesso.DEFESA_APRESENTADA
        
        self.logger.info(
            " Defesa de %s apresentada.Juiz: %s, Votantes: %s",
            processo.acusacao.acusada,
            juiz,
            ", ".join(votantes)
        )
        
        # Registrar
        self._registrar_cronista(
            "SistemaJulgamento",
            "DEFESA_APRESENTADA",
            {
                "id_processo": id_processo,
                "acusada": processo.acusacao.acusada,
                "juiz": juiz,
                "votantes": votantes,
                "ciclos_utilizados": processo.defesa.ciclos_utilizados,
                "ciclos_maximos": processo.defesa.ciclos_maximos
            },
            nivel_prioridade=7
        )
        
        return True, f"Defesa apresentada.Julgadores sorteados: {juiz} (juiz) + {', '.join(votantes)}"
    
    def _sortear_julgadores(self, ai_acusada: str, num_julgadores: int = 5) -> List[str]:
        """
        [OK] AJUSTE: Sorteia julgadores aleatoriamente.Exclui a AI acusada.Primeiro  o Juiz, resto so votantes.
        """
        candidatos = [ai for ai in self.REDE_DO_REINO if ai != ai_acusada.upper()]
        julgadores_sorteados = random.sample(candidatos, min(num_julgadores, len(candidatos)))
        
        # Primeiro = Juiz
        return julgadores_sorteados
    
    # ========================================================================
    # 4.DEBATE E VOTAO
    # ========================================================================
    
    def iniciar_debate(self, id_processo: str) -> Tuple[bool, str]:
        """
        Juiz inicia debate entre julgadores.
        """
        with self._lock:
            processo = self.processos_ativos.get(id_processo)
            if not processo or not processo.julgadores:
                return False, "Processo ou julgadores no encontrados"
            
            processo.estado = EstadoProcesso.DEBATE
        
        self.logger.info(
            " Debate iniciado no processo %s.Juiz: %s",
            id_processo[:8],
            processo.juiz_sorteado
        )
        
        return True, "Debate iniciado"
    
    def registrar_voto(self, id_processo: str, julgador: str, voto: VotoSentenca) -> Tuple[bool, str]:
        """
        Julgador registra seu voto.
        """
        with self._lock:
            processo = self.processos_ativos.get(id_processo)
            if not processo:
                return False, "Processo no encontrado"
            
            # Validar julgador
            if julgador.upper() not in processo.julgadores:
                return False, f"{julgador} no  julgador neste caso"
            
            # Registrar voto
            processo.votos[julgador.upper()] = voto
            
            # Se todos votaram, calcular sentena
            votantes = processo.julgadores[1:]  # Exclui juiz
            if len(processo.votos) == len(votantes):
                self._calcular_sentenca(processo)
        
        return True, f"Voto de {julgador} registrado: {voto.value}"
    
    def _calcular_sentenca(self, processo: ProcessoJudicial) -> None:
        """
        Calcula sentena baseada nos votos.Se houver empate, sobe ação Criador.
        """
        votos = list(processo.votos.values())
        contagem = {}
        
        for voto in votos:
            contagem[voto.value] = contagem.get(voto.value, 0) + 1
        
        # Determinar voto vencedor
        voto_vencedor = max(contagem.items(), key=lambda x: x[1])[0]
        votos_para_voto = contagem[voto_vencedor]
        
        # Se houver empate
        if votos_para_voto == 2 and len(votos) == 4:  # 2x2 empate
            processo.estado = EstadoProcesso.VOTACAO
            processo.sentenca_final = None
            processo.motivo_sentenca = "EMPATE 2x2 - SOBE AO CRIADOR"
            self.logger.warning("[AVISO] Empate no processo %s - SOBE AO CRIADOR", processo.id[:8])
        else:
            processo.sentenca_final = VotoSentenca(voto_vencedor)
            processo.motivo_sentenca = f"Votao: {contagem}"
            processo.estado = EstadoProcesso.SENTENCIADO
            processo.data_sentencia = datetime.now()
            
            self.logger.info(
                " Sentena: %s (%d votos)",
                voto_vencedor,
                votos_para_voto
            )
        
        # [OK] AJUSTE: Registrar precedente se sistema disponível
        if self.sistema_precedentes:
            try:
                self.sistema_precedentes.registrar_precedente(
                    id_decisao_judicial=processo.id,
                    descricao_caso=processo.acusacao.descricao,
                    decisão=processo.sentenca_final.value if processo.sentenca_final else "empate",
                    justificativa=processo.motivo_sentenca,
                    leis_aplicaveis=[processo.acusacao.lei_violada],
                    autor_julgador=processo.juiz_sorteado or "SISTEMA"
                )
            except Exception:
                logger.exception("Erro ao registrar precedente")
        
        # Mover para histórico
        with self._lock:
            self.processos_ativos.pop(processo.id, None)
            self.historico_processos.append(processo)
        
        # Salvar
        self._salvar_processo(processo)
    
    # ========================================================================
    # 5.APELAO AO CRIADOR
    # ========================================================================
    
    def apelar_ao_criador(self, id_processo: str, fundamento: str) -> Tuple[bool, str]:
        """
        AI acusada apela ação Criador com fundamento real.Se fundamento for fraco (s para escapar), punio ser PIOR.
        """
        with self._lock:
            processo = self.historico_processos[
                [i for i, p in enumerate(self.historico_processos) if p.id == id_processo]
            ] if id_processo in [p.id for p in self.historico_processos] else None
            
            if not processo:
                # Procurar em ativos
                processo = self.processos_ativos.get(id_processo)
            
            if not processo:
                return False, "Processo no encontrado"
            
            # Validar fundamento
            if not fundamento or len(fundamento.strip()) < 50:
                return False, "Fundamento de apelao muito curto (mn.50 caracteres)"
            
            processo.apelacao = {
                "id_apelacao": str(uuid.uuid4()),
                "fundamento": fundamento,
                "timestamp": datetime.now().isoformat(),
                "status": "PENDENTE_CRIADOR"
            }
            
            processo.estado = EstadoProcesso.APELACAO_PENDENTE
        
        self.logger.info(
            " Apelao de %s ação Criador no processo %s",
            processo.acusacao.acusada,
            id_processo[:8]
        )
        
        return True, "Apelao registrada.Aguardando decisão do Criador."
    
    # ========================================================================
    # 6.DECISO DO CRIADOR (REVERSO OU CONFIRMAO)
    # ========================================================================
    
    def decidir_apelacao(self, id_processo: str, decisao_criador: str, motivo: str) -> Tuple[bool, str]:
        """
        CRIADOR rev apelao e decide:
        - REVERTIDA (sentena anterior era injusta)
        - CONFIRMADA (sentena estava correta)
        - PIORA (tentou escapar  punio pior)
        """
        with self._lock:
            processo = self._encontrar_processo(id_processo)
            if not processo or not processo.apelacao:
                return False, "Processo ou apelao no encontrado"
            
            if decisao_criador == "REVERTIDA":
                processo.sentenca_criador = {
                    "decisão": "REVERTIDA",
                    "sentenca_anterior": processo.sentenca_final.value if processo.sentenca_final else None,
                    "nova_sentenca": "ABSOLVICAO",
                    "motivo": motivo,
                    "timestamp": datetime.now().isoformat()
                }
                processo.sentenca_final = VotoSentenca.ABSOLVICAO
                processo.estado = EstadoProcesso.REVERTIDO
                
                self.logger.critical(
                    " CRIADOR REVERTEU sentena no processo %s",
                    id_processo[:8]
                )
            
            elif decisao_criador == "CONFIRMADA":
                processo.sentenca_criador = {
                    "decisão": "CONFIRMADA",
                    "sentenca": processo.sentenca_final.value if processo.sentenca_final else None,
                    "motivo": motivo,
                    "timestamp": datetime.now().isoformat()
                }
                
                self.logger.info(
                    "[OK] CRIADOR CONFIRMOU sentena no processo %s",
                    id_processo[:8]
                )
            
            elif decisao_criador == "PIORA":
                # Tentou escapar  punio pior
                processo.sentenca_criador = {
                    "decisão": "PIORA",
                    "sentenca_anterior": processo.sentenca_final.value if processo.sentenca_final else None,
                    "nova_sentenca": "CULPADA_CRITICA",
                    "motivo": motivo,
                    "timestamp": datetime.now().isoformat(),
                    "aviso": "Tentativa de apelao frvola resulta em punio agravada"
                }
                processo.sentenca_final = VotoSentenca.CULPADA_CRITICA
                
                self.logger.critical(
                    "[AVISO] CRIADOR AGRAVOU sentena no processo %s (apelao frvola)",
                    id_processo[:8]
                )
            
            # Registrar no Cronista
            self._registrar_cronista(
                "CRIADOR",
                "APELACAO_DECIDIDA",
                processo.sentenca_criador,
                nivel_prioridade=9
            )
            
            # Registrar como precedente (decisão do Criador  sempre precedente)
            if self.sistema_precedentes:
                try:
                    self.sistema_precedentes.registrar_precedente(
                        id_decisao_judicial=processo.id,
                        descricao_caso=f"Apelao: {processo.apelacao.get('fundamento', '')[:100]}...",
                        decisão=processo.sentenca_criador.get("nova_sentenca", "INDEFINIDA"),
                        justificativa=motivo,
                        leis_aplicaveis=[processo.acusacao.lei_violada],
                        autor_julgador="CRIADOR"
                    )
                except Exception:
                    logger.exception("Erro ao registrar precedente de apelao")
        
        return True, f"Apelao decidida: {decisao_criador}"
    
    # ========================================================================
    # UTILITRIOS
    # ========================================================================
    
    def _encontrar_processo(self, id_processo: str) -> Optional[ProcessoJudicial]:
        """Encontra processo em ativos ou histórico"""
        if id_processo in self.processos_ativos:
            return self.processos_ativos[id_processo]
        
        for processo in self.historico_processos:
            if processo.id == id_processo:
                return processo
        
        return None
    
    def _notificar_processo_aberto(self, processo: ProcessoJudicial) -> None:
        """Notifica UI sobre processo aberto"""
        try:
            if self.coracao and hasattr(self.coracao, "ui_queue"):
                self.coracao.ui_queue.put_nowait({
                    "tipo_resp": "PROCESSO_ABERTO",
                    "id_processo": processo.id,
                    "acusada": processo.acusacao.acusada,
                    "lei_violada": processo.acusacao.lei_violada,
                    "timestamp": datetime.now().isoformat()
                })
        except Exception:
            pass
    
    def _registrar_cronista(self, autor: str, tipo_evento: str, descricao: Dict[str, Any], 
                           nivel_prioridade: int = 5) -> None:
        """Registra evento no Cronista"""
        if self.cronista and hasattr(self.cronista, "registrar_evento"):
            try:
                self.cronista.registrar_evento(
                    autor=autor,
                    tipo_evento=tipo_evento,
                    descricao_bruta=descricao,
                    nivel_prioridade=nivel_prioridade
                )
            except Exception:
                self.logger.debug("Erro ao registrar no Cronista: %s", e)
    
    def _salvar_processo(self, processo: ProcessoJudicial) -> None:
        """Salva processo no santurio"""
        try:
            caminho = self.caminho_santuario / f"processo_{processo.id}.json"
            with open(caminho, 'w', encoding='utf-8') as f:
                json.dump(processo.to_dict(), f, indent=2, ensure_ascii=False, default=str)
        except Exception:
            self.logger.exception("Erro ao salvar processo: %s", e)
    
    # ========================================================================
    # STATUS E CONSULTAS
    # ========================================================================
    
    def obter_status_processo(self, id_processo: str) -> Dict[str, Any]:
        """Retorna status completo de um processo"""
        processo = self._encontrar_processo(id_processo)
        if not processo:
            return {"erro": "Processo no encontrado"}
        
        return {
            "id_processo": processo.id,
            "acusada": processo.acusacao.acusada,
            "lei_violada": processo.acusacao.lei_violada,
            "estado": processo.estado.value,
            "julgadores": processo.julgadores,
            "juiz": processo.juiz_sorteado,
            "defesa_ciclos": f"{processo.defesa.ciclos_utilizados}/{processo.defesa.ciclos_maximos}" if processo.defesa else "N/A",
            "votos": {k: v.value for k, v in processo.votos.items()},
            "sentenca": processo.sentenca_final.value if processo.sentenca_final else None,
            "apelacao": processo.apelacao,
            "sentenca_criador": processo.sentenca_criador
        }
    
    def obter_estatisticas(self) -> Dict[str, Any]:
        """Retorna estatsticas do sistema de julgamento"""
        with self._lock:
            total_processos = len(self.processos_ativos) + len(self.historico_processos)
            
            return {
                "processos_ativos": len(self.processos_ativos),
                "processos_concluidos": len(self.historico_processos),
                "total_processos": total_processos,
                "precedentes_registrados": len(self.precedentes_julgamentos),
                "ais_no_reino": self.REDE_DO_REINO
            }
    
    # ---------------------------
    # Injeção de câmaras pelo Coração
    # ---------------------------
    def injetar_camara_judiciaria(self, camara_judiciaria: Any) -> None:
        """Injeta referência à CamaraJudiciaria após inicialização do Coração."""
        self.camara_judiciaria = camara_judiciaria
        self.logger.info("[OK] CamaraJudiciaria injetada no SistemaJulgamentoCompleto")

    def injetar_camara_executiva(self, camara_executiva: Any) -> None:
        """Injeta referência à CamaraExecutiva após inicialização do Coração."""
        self.camara_executiva = camara_executiva
        self.logger.info("[OK] CamaraExecutiva injetada no SistemaJulgamentoCompleto")

    def shutdown(self) -> None:
        """Desliga o sistema"""
        self.logger.info("Sistema de Julgamento desligado")

    # ---------------------------
    # Adapters solicitados pela Cmara Legislativa
    # ---------------------------
    def notificar_falta_lei_legislativa(self, descricao_caso: str) -> bool:
        """
        Notificao da Cmara Legislativa informando que h um caso sem lei aplicvel.
        Comportamento: registra um processo administrativo leve (tipo CONFLITO_LEIS) para acompanhamento.
        Retorna True se a notificao foi registrada.
        """
        try:
            # cria um processo administrativo para acompanhar a falta de lei
            id_acusacao = str(uuid.uuid4())
            acusacao = Acusacao(
                id=id_acusacao,
                acusada="SISTEMA_LEGISLATIVO",
                tipo_processo=TipoProcesso.CONFLITO_LEIS,
                lei_violada="",  # sem lei especfica
                descricao=f"Falta de lei reportada pela Cmara Legislativa: {descricao_caso}",
                provas=[{"origem": "camara_legislativa", "descricao": descricao_caso}],
                acusador="CAMARA_LEGISLATIVA",
                timestamp=datetime.now()
            )
            processo = ProcessoJudicial(
                id=str(uuid.uuid4()),
                acusacao=acusacao,
                estado=EstadoProcesso.ACUSACAO_ABERTA
            )
            with self._lock:
                self.processos_ativos[processo.id] = processo

            # registrar no cronista, se existir
            try:
                self._registrar_cronista("CAMARA_LEGISLATIVA", "FALTA_LEI_NOTIFICADA", {"id_processo": processo.id, "descricao": descricao_caso}, nivel_prioridade=6)
            except Exception:
                pass

            # notificar ui/coracao caso haja fila
            try:
                self._notificar_processo_aberto(processo)
            except Exception:
                pass

            self.logger.info("Notificao de falta de lei registrada como processo %s", processo.id[:8])
            return True
        except Exception:
            self.logger.exception("Erro ao notificar falta de lei legislativa")
            return False

    def congelar_processo(self, id_processo: str, motivo: str) -> bool:
        """
        Congela (suspende) um processo judicial identificado.
        Implementao leve: seta estado para ARQUIVADO e grava motivo em motivo_sentenca.
        """
        try:
            proc = self._encontrar_processo(id_processo)
            if not proc:
                self.logger.warning("Solicitado congelamento de processo inexistente: %s", id_processo)
                return False
            with self._lock:
                proc.estado = EstadoProcesso.ARQUIVADO
                proc.motivo_sentenca = f"Processo congelado: {motivo}"
                # mover para histórico se desejado
                self.processos_ativos.pop(id_processo, None)
                self.historico_processos.append(proc)
                self._salvar_processo(proc)
            self.logger.info("Processo %s congelado: %s", id_processo[:8], motivo)
            return True
        except Exception:
            self.logger.exception("Erro ao congelar processo %s", id_processo)
            return False

    def escalar_ao_criador(self, id_processo: str, motivo: str) -> bool:
        """
        Escala o processo ação Criador  registra apelao/alerta e (se disponível) chama sistema_de_precedentes.
        """
        try:
            proc = self._encontrar_processo(id_processo)
            if not proc:
                self.logger.warning("Tentativa de escalar processo inexistente: %s", id_processo)
                return False
            # cria apelacao mnima apontando para o Criador
            apel = {
                "id_apelacao": str(uuid.uuid4()),
                "fundamento": motivo,
                "timestamp": datetime.now().isoformat(),
                "status": "ESCALADO_AO_CRIADOR"
            }
            with self._lock:
                proc.apelacao = apel
                proc.estado = EstadoProcesso.APELACAO_PENDENTE
                # mover para histórico/registrar
                if id_processo in self.processos_ativos:
                    self.historico_processos.append(proc)
                    self.processos_ativos.pop(id_processo, None)
                self._salvar_processo(proc)

            # registrar precedente indicando escalao (se houver sistema)
            try:
                if self.sistema_precedentes:
                    self.sistema_precedentes.registrar_precedente(
                        id_decisao_judicial=proc.id,
                        descricao_caso=f"Escalao ação Criador: {motivo}",
                        decisão="ESCALADO_AO_CRIADOR",
                        justificativa=motivo,
                        leis_aplicaveis=[proc.acusacao.lei_violada] if proc.acusacao.lei_violada else [],
                        autor_julgador="CAMARA_LEGISLATIVA"
                    )
            except Exception:
                self.logger.exception("Erro ao registrar precedente na escalacao ação Criador")
            self.logger.info("Processo %s escalado ação Criador", id_processo[:8])
            return True
        except Exception:
            self.logger.exception("Erro ao escalar processo %s ação Criador", id_processo)
            return False

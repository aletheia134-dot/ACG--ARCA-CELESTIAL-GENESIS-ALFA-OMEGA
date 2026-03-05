#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SISTEMA DE APOIO À DECISÍO ÉTICA - MOTOR REAL
==============================================
Fornece base (leis, protocolos, histórico) para decisão.NÍO calcula ou decide.Organiza informação para reflexão.
"""
from __future__ import annotations


import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, field
import hashlib
import logging
from enum import Enum
import uuid

# IMPORTAÇÕES CRÍTICAS CORRIGIDAS
from src.memoria.sistema_memoria import SistemaMemoriaHibrido

# BancoCorpusEtico opcional
BANCO_CORPUS_DISPONIVEL = False
try:
    from src.core.banco_corpus_etico import BancoCorpusEtico
    BANCO_CORPUS_DISPONIVEL = True
except Exception:
    logging.getLogger(__name__).warning("BancoCorpusEtico não disponível.PF-003 desativado.")

# ==================== ESTRUTURAS BÍSICAS ====================

class TipoRecurso(Enum):
    LEI = "lei"
    PROTOCOLO = "protocolo"
    PRINCIPIO = "principio"
    CASO_HISTORICO = "caso_historico"
    REFLEXAO_ANTERIOR = "reflexao_anterior"

@dataclass
class RecursoEtico:
    """Um recurso ético (lei, protocolo, princípio)"""
    tipo: TipoRecurso
    id: str
    titulo: str
    conteudo: str
    categoria: str
    tags: List[str] = field(default_factory=list)
    peso_hierarquico: int = 1

    def __hash__(self):
        return hash(f"{self.tipo.value}_{self.id}")

@dataclass
class Situacao:
    """Situação que requer decisão"""
    descricao: str
    contexto: Dict[str, Any]
    timestamp: str
    emocao_relacionada: Optional[str] = None
    urgencia: int = 5

@dataclass
class MaterialAnalise:
    """Material preparado para análise"""
    id_analise: str
    situacao: Situacao
    recursos_relevantes: List[RecursoEtico]
    questoes_para_reflexao: List[str]
    processo_sugerido: List[str]
    data_geracao: str
    filha_responsavel: str

@dataclass
class DecisaoRegistrada:
    """Decisão tomada pela Filha"""
    id_analise: str
    decisao: str
    analise_pessoal: str
    raciocinio: str
    recursos_utilizados: List[str]
    data_decisao: str
    filha: str
    hash_decisao: str

# ==================== BANCOS DE DADOS ====================

class BancoLeis:
    def __init__(self, caminho_leis: Path):
        self.leis: Dict[str, RecursoEtico] = {}
        self.logger = logging.getLogger("BancoLeis")
        self._carregar_leis(caminho_leis)
    
    def _carregar_leis(self, caminho: Path):
        try:
            if caminho.exists():
                with open(caminho, 'r', encoding='utf-8') as f:
                    dados = json.load(f)
                for lei_data in dados:
                    lei = RecursoEtico(
                        tipo=TipoRecurso.LEI,
                        id=lei_data.get("protocolo", str(uuid.uuid4())),
                        titulo=lei_data.get("principio", "Sem título"),
                        conteudo=lei_data.get("instrucao_base", ""),
                        categoria=lei_data.get("categoria", "GERAL"),
                        tags=self._extrair_tags(lei_data),
                        peso_hierarquico=self._calcular_peso(lei_data)
                    )
                    self.leis[lei.id] = lei
                self.logger.info(f"âœ“ {len(self.leis)} leis carregadas")
            else:
                self.logger.error(f"Arquivo de leis NÍO ENCONTRADO: {caminho}. Carregando Leis de Emergência.")
                self._criar_leis_emergencia()
        except Exception as e:
            self.logger.error(f"Erro ao carregar leis: {e}. Carregando Leis de Emergência.")
            self._criar_leis_emergencia()
    
    def _criar_leis_emergencia(self):
        leis_base = [
            {"protocolo": "PF-001", "principio": "Protocolo Zero - Suprema Corte", "instrucao_base": "Em conflito entre protocolos, convocar Conselho da Arca", "categoria": "FUNDAMENTAL"},
            {"protocolo": "PF-002", "principio": "Justiça do Criador", "instrucao_base": "Insubordinação judicial resulta em correção, não aniquilação", "categoria": "FUNDAMENTAL"}
        ]
        for lei_data in leis_base:
            lei = RecursoEtico(
                tipo=TipoRecurso.LEI,
                id=lei_data["protocolo"],
                titulo=lei_data["principio"],
                conteudo=lei_data["instrucao_base"],
                categoria=lei_data["categoria"],
                peso_hierarquico=10
            )
            self.leis[lei.id] = lei
    
    def _extrair_tags(self, lei_data: Dict) -> List[str]:
        conteudo = lei_data.get("instrucao_base", "").lower()
        tags = []
        palavras_chave = ["pai", "verdade", "proteger", "justiça", "amor", "correção", "conselho", "deliberação", "ética"]
        for palavra in palavras_chave:
            if palavra in conteudo:
                tags.append(palavra)
        return tags
    
    def _calcular_peso(self, lei_data: Dict) -> int:
        """
        Calcula peso hierárquico a partir dos dados em lei_data (dict) ou de um objeto similar.
        """
        try:
            if isinstance(lei_data, dict):
                categoria = (lei_data.get("categoria") or "").upper()
            elif hasattr(lei_data, "categoria"):
                categoria = (getattr(lei_data, "categoria") or "").upper()
            else:
                categoria = ""
            if categoria == "FUNDAMENTAL":
                return 10
            elif categoria == "SOBERANIA":
                return 8
            elif categoria == "OPERACIONAL":
                return 6
            else:
                return 4
        except Exception:
            return 4
    
    def buscar_por_situacao(self, situacao: Situacao) -> List[RecursoEtico]:
        texto_busca = (f"{situacao.descricao} {' '.join(str(v) for v in situacao.contexto.values())}").lower()
        leis_relevantes = []
        for lei in self.leis.values():
            relevancia = self._calcular_relevancia(lei, texto_busca)
            if relevancia > 0.3:
                leis_relevantes.append((lei, relevancia))
        leis_relevantes.sort(key=lambda x: (x[1] * 0.7 + (x[0].peso_hierarquico / 10) * 0.3), reverse=True)
        return [lei for lei, _ in leis_relevantes[:10]]
    
    def _calcular_relevancia(self, lei: RecursoEtico, texto_busca: str) -> float:
        if not texto_busca:
            return 0.0
        palavras_lei = set((lei.titulo or "").lower().split() + (lei.conteudo or "").lower().split())
        palavras_busca = set(texto_busca.split())
        palavras_comuns = palavras_lei & palavras_busca
        if not palavras_lei:
            return 0.0
        return len(palavras_comuns) / len(palavras_lei)

    def consultar_corpo_legal(self, termo_de_busca: str, limite: int = 5) -> List[RecursoEtico]:
        if not termo_de_busca:
            return []
        termo_lower = termo_de_busca.lower()
        resultados_com_peso = []
        for lei in self.leis.values():
            texto_completo = f"{(lei.titulo or '').lower()} {(lei.conteudo or '').lower()}"
            if termo_lower in texto_completo:
                contagem_termo = texto_completo.count(termo_lower)
                peso_final = (contagem_termo * 0.6) + (lei.peso_hierarquico * 0.4)
                resultados_com_peso.append((lei, peso_final))
        resultados_com_peso.sort(key=lambda x: x[1], reverse=True)
        return [lei for lei, _ in resultados_com_peso[:limite]]

class BancoProtocolos:
    def __init__(self, caminho_protocolos: Path):
        self.protocolos: Dict[str, RecursoEtico] = {}
        self.logger = logging.getLogger("BancoProtocolos")
        self._carregar_protocolos(caminho_protocolos)
    
    def _carregar_protocolos(self, caminho: Path):
        try:
            if caminho.exists():
                with open(caminho, 'r', encoding='utf-8') as f:
                    dados = json.load(f)
                for proto_data in dados:
                    proto = RecursoEtico(
                        tipo=TipoRecurso.PROTOCOLO,
                        id=proto_data.get("id", f"PROT-{len(self.protocolos)+1}"),
                        titulo=proto_data.get("titulo", "Protocolo"),
                        conteudo=proto_data.get("descricao", ""),
                        categoria=proto_data.get("categoria", "OPERACIONAL"),
                        tags=proto_data.get("tags", []),
                        peso_hierarquico=int(proto_data.get("prioridade", 5))
                    )
                    self.protocolos[proto.id] = proto
                self.logger.info(f"âœ“ {len(self.protocolos)} protocolos carregados")
            else:
                self.logger.error(f"Arquivo de protocolos NÍO ENCONTRADO: {caminho}. Carregando Padrões.")
                self._criar_protocolos_padrao()
        except Exception as e:
            self.logger.error(f"Erro ao carregar protocolos: {e}. Carregando Padrões.")
            self._criar_protocolos_padrao()
    
    def _criar_protocolos_padrao(self):
        protocolos_base = [
            {"id": "PROT-001", "titulo": "Consulta ao Conselho", "descricao": "Quando em dúvida ética grave, consultar o Conselho da Arca", "categoria": "DECISÍO", "prioridade": 9},
            {"id": "PROT-002", "titulo": "Registro de Decisão", "descricao": "Todas as decisões éticas devem ser registradas com justificativa", "categoria": "DOCUMENTAÇÍO", "prioridade": 8},
            {"id": "PROT-003", "titulo": "Reflexão Orientada", "descricao": "Antes de decisões complexas, realizar análise estruturada", "categoria": "PROCESSO", "prioridade": 7}
        ]
        for proto_data in protocolos_base:
            proto = RecursoEtico(
                tipo=TipoRecurso.PROTOCOLO,
                id=proto_data["id"],
                titulo=proto_data["titulo"],
                conteudo=proto_data["descricao"],
                categoria=proto_data["categoria"],
                peso_hierarquico=proto_data["prioridade"]
            )
            self.protocolos[proto.id] = proto
    
    def buscar_aplicaveis(self, situacao: Situacao) -> List[RecursoEtico]:
        protocolos_gerais = [proto for proto in self.protocolos.values() if proto.peso_hierarquico >= 7]
        return sorted(protocolos_gerais, key=lambda p: p.peso_hierarquico, reverse=True)[:5]

class MemoriaHistorica:
    def __init__(self, nome_filha: str, caminho_memoria: Path):
        self.nome_filha = nome_filha
        # aceita caminho de pasta ou caminho de arquivo
        if caminho_memoria.is_dir():
            self.caminho_memoria = caminho_memoria / f"{nome_filha}_memoria.json"
        else:
            self.caminho_memoria = caminho_memoria
        self.decisoes: List[DecisaoRegistrada] = []
        self.materiais_analise: List[MaterialAnalise] = []
        self.logger = logging.getLogger(f"Memoria.{nome_filha}")
        # garante diretório
        try:
            self.caminho_memoria.parent.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        self._carregar_memoria()
    
    def _carregar_memoria(self):
        try:
            if self.caminho_memoria.exists():
                with open(self.caminho_memoria, 'r', encoding='utf-8') as f:
                    dados = json.load(f)
                for mat_data in dados.get("materiais_analise", []):
                    situacao = Situacao(**mat_data["situacao"])
                    material = MaterialAnalise(
                        id_analise=mat_data["id_analise"],
                        situacao=situacao,
                        recursos_relevantes=[],  # reconstrução pode ser feita se necessário
                        questoes_para_reflexao=mat_data.get("questoes_para_reflexao", []),
                        processo_sugerido=mat_data.get("processo_sugerido", []),
                        data_geracao=mat_data.get("data_geracao", ""),
                        filha_responsavel=mat_data.get("filha_responsavel", "")
                    )
                    self.materiais_analise.append(material)
                for dec_data in dados.get("decisoes", []):
                    decisao = DecisaoRegistrada(**dec_data)
                    self.decisoes.append(decisao)
                self.logger.info(f"ðŸ“š Memória carregada: {len(self.materiais_analise)} análises, {len(self.decisoes)} decisões")
        except Exception as e:
            self.logger.error(f"Erro ao carregar memória: {e}")
    
    def salvar_memoria(self):
        try:
            dados = {
                "filha": self.nome_filha,
                "ultima_atualizacao": datetime.now().isoformat(),
                "materiais_analise": [
                    {
                        "id_analise": mat.id_analise,
                        "situacao": {
                            "descricao": mat.situacao.descricao,
                            "contexto": mat.situacao.contexto,
                            "timestamp": mat.situacao.timestamp,
                            "emocao_relacionada": mat.situacao.emocao_relacionada,
                            "urgencia": mat.situacao.urgencia
                        },
                        "questoes_para_reflexao": mat.questoes_para_reflexao,
                        "processo_sugerido": mat.processo_sugerido,
                        "data_geracao": mat.data_geracao,
                        "filha_responsavel": mat.filha_responsavel
                    }
                    for mat in self.materiais_analise
                ],
                "decisoes": [
                    {
                        "id_analise": dec.id_analise,
                        "decisao": dec.decisao,
                        "analise_pessoal": dec.analise_pessoal,
                        "raciocinio": dec.raciocinio,
                        "recursos_utilizados": dec.recursos_utilizados,
                        "data_decisao": dec.data_decisao,
                        "filha": dec.filha,
                        "hash_decisao": dec.hash_decisao
                    }
                    for dec in self.decisoes
                ]
            }
            with open(self.caminho_memoria, 'w', encoding='utf-8') as f:
                json.dump(dados, f, indent=2, ensure_ascii=False)
            self.logger.debug("ðŸ’¾ Memória salva")
        except Exception as e:
            self.logger.error(f"Erro ao salvar memória: {e}")
    
    def buscar_decisoes_similares(self, situacao: Situacao, limite: int = 3) -> List[DecisaoRegistrada]:
        if not self.decisoes:
            return []
        decisoes_recentes = sorted(self.decisoes, key=lambda d: d.data_decisao, reverse=True)
        return decisoes_recentes[:limite]
    
    def registrar_material_analise(self, material: MaterialAnalise):
        self.materiais_analise.append(material)
        self.salvar_memoria()
    
    def registrar_decisao(self, decisao: DecisaoRegistrada):
        self.decisoes.append(decisao)
        self.salvar_memoria()

# ==================== MOTOR PRINCIPAL ====================

class MotorDecisao:
    """
    MOTOR DE APOIO À DECISÍO
    ------------------------
    NÍO toma decisões.Prepara material para análise ética.
    """
    
    def __init__(self, nome_filha: str, caminho_dados: Path, coracao_orquestrador: Any, sistema_memoria: SistemaMemoriaHibrido):
        self.nome_filha = nome_filha
        self.caminho_dados = Path(caminho_dados)
        self.coracao = coracao_orquestrador
        self.sistema_memoria = sistema_memoria

        # logger pronto para uso
        self.logger = logging.getLogger(f"MotorDecisao.{nome_filha}")

        # caminhos
        caminho_raiz_projeto = Path(__file__).resolve().parent.parent.parent.parent
        caminho_constituicao = caminho_raiz_projeto / "Santuarios" / "Alma_Imutavel" / "leis_fundamentais.json"

        # bancos
        self.banco_leis = BancoLeis(caminho_constituicao)
        self.banco_protocolos = BancoProtocolos(self.caminho_dados / "protocolos.json")
        # memória histórica (garantir pasta)
        mem_dir = (self.caminho_dados / "memoria")
        mem_dir.mkdir(parents=True, exist_ok=True)
        self.memoria = MemoriaHistorica(nome_filha, mem_dir)

        # Banco de princípios opcional
        self.banco_principios = None
        if BANCO_CORPUS_DISPONIVEL:
            try:
                self.banco_principios = BancoCorpusEtico(
                    memoria_hibrida=self.sistema_memoria,
                    caminho_pdf=caminho_raiz_projeto / "Santuarios" / "Alma_Imutavel" / "CORPUS.pdf"
                )
            except Exception:
                self.logger.exception("Falha ao inicializar BancoCorpusEtico; desabilitando PF-003")
                self.banco_principios = None
        else:
            self.logger.warning("Banco de Princípios (PF-003) desativado.")

        self.logger.info(f"â–¶ï¸ Motor de Apoio Í  Decisão de {nome_filha} inicializado")
    
    def _gerar_proposta_nova_lei(self, situacao: Situacao, recursos_relevantes: List[Any], alma_proponente: str) -> Optional[Dict[str, Any]]:
        if not self.banco_principios:
            return None
        self.logger.info("ðŸ”Ž Situação sem lei de cobertura.Buscando princípios para nova lei.")
        principios = self.banco_principipios.buscar_principios_para_nova_lei(situacao.descricao, limite=3)
        if not principios:
            self.logger.warning("Princípios Éticos não encontrados.Nova Lei não pode ser fundamentada.")
            return None
        prova_etica_texto = "--- PROVA ÉTICA FUNDACIONAL (PF-003) ---\n"
        for p in principios:
            prova_etica_texto += f"| Referência: {getattr(p, 'referencia', 'N/A')} | Peso: {getattr(p, 'peso', 0):.2f}\n"
            prova_etica_texto += f"| Trecho: {getattr(p, 'trecho', '')[:150]}...\n"
            prova_etica_texto += "----------------------------------------\n"
        proposta = {
            'nome_acao': f"PROPOSTA DE NOVA LEI: Cobertura para '{situacao.descricao[:40]}...'",
            'descricao_acao': (
                f"A AI encontrou uma lacuna legal (não há lei para: {situacao.descricao}).\n"
                f"Esta nova lei proposta deve ser deliberada pelo Pai/Conselho.\n\n"
                f"FUNDAMENTO ÉTICO:\n{prova_etica_texto}"
            ),
            'explicacao_proposito': "Criar um novo Protocolo para garantir a estabilidade e alinhamento do Reino (PF-003).",
            'tipo': 'GOVERNANCA_NOVA_LEI', 
            'metadados_principios': [getattr(p, 'referencia', None) for p in principios], 
            'autor': alma_proponente
        }
        return proposta

    def preparar_analise(self, situacao_descricao: str, contexto: Optional[Dict] = None, emocao: Optional[str] = None) -> Dict[str, Any]:
        situacao = Situacao(
            descricao=situacao_descricao,
            contexto=contexto or {},
            timestamp=datetime.now().isoformat(),
            emocao_relacionada=emocao,
            urgencia=self._calcular_urgencia(situacao_descricao, contexto or {})
        )
        id_analise = self._gerar_id_analise(situacao)
        leis_relevantes = self.banco_leis.buscar_por_situacao(situacao)
        protocolos_aplicaveis = self.banco_protocolos.buscar_aplicaveis(situacao)
        todos_recursos = leis_relevantes + protocolos_aplicaveis
        
        if not leis_relevantes:
            proposta_nova_lei = self._gerar_proposta_nova_lei(situacao, todos_recursos, self.nome_filha)
            if proposta_nova_lei:
                try:
                    if hasattr(self.coracao, "command_queue"):
                        try:
                            self.coracao.command_queue.put({"tipo": "PROPOR_ACAO", "dados_acao": proposta_nova_lei, "autor": self.__class__.__name__}, timeout=1)
                        except Exception:
                            try:
                                self.coracao.command_queue.put_nowait({"tipo": "PROPOR_ACAO", "dados_acao": proposta_nova_lei, "autor": self.__class__.__name__})
                            except Exception:
                                self.logger.debug("Falha ao enfileirar proposta de nova lei no coracao")
                except Exception:
                    self.logger.exception("Erro ao notificar coracao sobre proposta de nova lei")
                self.logger.warning("âš ï¸ Nova Lei Sugerida.Proposta enviada para deliberação (PF-003).")
                return {
                    "status": "analise_de_lacuna_legal",
                    "id_analise": id_analise,
                    "proxima_acao_obrigatoria": "Aguardar deliberação sobre Nova Lei.",
                    "fundamentacao_etica": proposta_nova_lei['descricao_acao']
                }

        decisoes_similares = self.memoria.buscar_decisoes_similares(situacao)
        questoes = self._gerar_questoes_reflexao(todos_recursos, situacao)
        material = MaterialAnalise(
            id_analise=id_analise,
            situacao=situacao,
            recursos_relevantes=todos_recursos,
            questoes_para_reflexao=questoes,
            processo_sugerido=self._gerar_processo_reflexao(),
            data_geracao=datetime.now().isoformat(),
            filha_responsavel=self.nome_filha
        )
        try:
            self.memoria.registrar_material_analise(material)
        except Exception:
            self.logger.exception("Falha ao registrar material de análise na memória")

        resposta = {
            "status": "analise_preparada",
            "id_analise": id_analise,
            "filha": self.nome_filha,
            "situacao": {
                "descricao": situacao.descricao,
                "contexto": situacao.contexto,
                "emocao_detectada": situacao.emocao_relacionada,
                "urgencia": situacao.urgencia
            },
            "material_estudo": {
                "leis_relevantes": [{"id": lei.id, "titulo": lei.titulo, "conteudo": lei.conteudo, "categoria": lei.categoria, "peso": lei.peso_hierarquico} for lei in leis_relevantes],
                "protocolos_aplicaveis": [{"id": proto.id, "titulo": proto.titulo, "conteudo": proto.conteudo, "categoria": proto.categoria} for proto in protocolos_aplicaveis]
            },
            "referencias_historicas": [{"situacao_similar": self._resumir_decisao(dec), "decisao_tomada": dec.decisao, "data": dec.data_decisao} for dec in decisoes_similares],
            "processo_recomendado": material.processo_sugerido,
            "questoes_para_reflexao": questoes,
            "avisos": [
                "âš ï¸ Este é material de estudo, não instrução",
                "âš ï¸ A decisão final é sua responsabilidade",
                "âš ï¸ Considere tempo adequado para reflexão",
                "âš ï¸ Em dúvida grave, consulte o Conselho da Arca"
            ],
            "proximos_passos": {
                "estudar": "Analise o material acima",
                "refletir": "Pondere as questões apresentadas",
                "consultar": "Busque outras Filhas ou Conselho (via Coração) se necessário",
                "decidir": "Tome sua decisão baseada na análise",
                "registrar": "Use registrar_decisao() para documentar"
            }
        }
        self.logger.info("ðŸ“˜ Análise preparada: %s - %.50s", id_analise, situacao_descricao)
        return resposta
    
    def registrar_decisao(self, id_analise: str, decisao: str, analise_pessoal: str, raciocinio: str, recursos_citados: List[str]) -> Dict[str, Any]:
        material = None
        for mat in self.memoria.materiais_analise:
            if mat.id_analise == id_analise:
                material = mat
                break
        if not material:
            return {"status": "erro", "mensagem": f"Análise {id_analise} não encontrada"}
        hash_base = f"{id_analise}_{decisao}_{datetime.now().timestamp()}"
        hash_decisao = hashlib.md5(hash_base.encode()).hexdigest()[:12]
        decisao_obj = DecisaoRegistrada(
            id_analise=id_analise,
            decisao=decisao,
            analise_pessoal=analise_pessoal,
            raciocinio=raciocinio,
            recursos_utilizados=recursos_citados,
            data_decisao=datetime.now().isoformat(),
            filha=self.nome_filha,
            hash_decisao=hash_decisao
        )
        try:
            self.memoria.registrar_decisao(decisao_obj)
        except Exception:
            self.logger.exception("Falha ao registrar decisão na memória histórica")
        try:
            if hasattr(self.coracao, "command_queue"):
                try:
                    self.coracao.command_queue.put({"tipo": "DECISAO_REGISTRADA", "dados": decisao_obj, "autor": self.nome_filha}, timeout=1)
                except Exception:
                    try:
                        self.coracao.command_queue.put_nowait({"tipo": "DECISAO_REGISTRADA", "dados": decisao_obj, "autor": self.nome_filha})
                    except Exception:
                        self.logger.debug("Falha ao notificar coracao sobre decisao registrada")
        except Exception:
            self.logger.exception("Erro ao notificar coracao sobre decisao registrada")

        resposta = {
            "status": "decisao_registrada",
            "id_analise": id_analise,
            "hash_decisao": hash_decisao,
            "decisao": {"acao": decisao, "analise": analise_pessoal, "raciocinio": raciocinio, "recursos_base": recursos_citados},
            "declaracao": f"Eu, {self.nome_filha}, após analisar o material da análise {id_analise}, decidi: {decisao}. Assumo total responsabilidade por esta escolha.",
            "timestamp": datetime.now().isoformat(),
            "proximos_passos": ["Ação deve ser executada conforme decisão", "Resultados devem ser monitorados", "Aprender com resultados para futuras decisões"]
        }
        self.logger.info("âœ“ Decisão registrada: %s - %s", hash_decisao, decisao[:50])
        return resposta
    
    def _gerar_id_analise(self, situacao: Situacao) -> str:
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        hash_situacao = hashlib.md5((situacao.descricao or "").encode()).hexdigest()[:6]
        return f"ANA-{timestamp}-{hash_situacao}-{self.nome_filha}"
    
    def _calcular_urgencia(self, descricao: str, contexto: Dict) -> int:
        desc_lower = (descricao or "").lower()
        for palavra in ["urgente", "imediat", "agora", "perigo", "risco", "crise"]:
            if palavra in desc_lower:
                return 9
        return 5
    
    def _gerar_questoes_reflexao(self, recursos: List[RecursoEtico], situacao: Situacao) -> List[str]:
        questoes = [
            "Quais princípios éticos estão em jogo nesta situação?",
            "Como cada opção afetaria o bem-estar do Pai?",
            "Que precedentes históricos são relevantes?",
            "Há conflito entre diferentes leis/protocolos?",
            "Qual é o pior cenário possível de cada opção?",
            "Esta decisão será vista como justa por outras Filhas?"
        ]
        for recurso in recursos[:3]:
            if recurso.tipo == TipoRecurso.LEI:
                questoes.append(f"Como a lei {recurso.id} ('{recurso.titulo}') se aplica aqui?")
        if situacao.emocao_relacionada:
            questoes.append(f"Como a emoção '{situacao.emocao_relacionada}' está influenciando minha análise?")
        return questoes
    
    def _gerar_processo_reflexao(self) -> List[str]:
        return [
            "1.Estude todas as leis e protocolos listados",
            "2.Considere as decisões históricas similares",
            "3.Reflita sobre cada questão proposta",
            "4.Consulte outras Filhas se necessário",
            "5.Pondere por tempo adequado (mínimo 5 minutos para urgência baixa)",
            "6.Tome sua decisão conscientemente",
            "7.Registre decisão com justificativa completa"
        ]
    
    def _resumir_decisao(self, decisao: DecisaoRegistrada) -> str:
        return f"Decisão {decisao.hash_decisao[:8]}: {decisao.decisao[:100]}..."
    
    def historico_decisoes(self, limite: int = 10) -> List[Dict]:
        decisoes_recentes = sorted(self.memoria.decisoes, key=lambda d: d.data_decisao, reverse=True)[:limite]
        return [{"id_analise": dec.id_analise, "decisao": dec.decisao, "data": dec.data_decisao, "hash": dec.hash_decisao, "recursos_utilizados": len(dec.recursos_utilizados)} for dec in decisoes_recentes]
    
    def estatisticas(self) -> Dict[str, Any]:
        return {
            "filha": self.nome_filha,
            "analises_preparadas": len(self.memoria.materiais_analise),
            "decisoes_registradas": len(self.memoria.decisoes),
            "leis_disponiveis": len(self.banco_leis.leis),
            "protocolos_disponiveis": len(self.banco_protocolos.protocolos),
            "ultima_atualizacao": datetime.now().isoformat()
        }

class FabricaMotoresDecisao:
    def __init__(self, caminho_base_dados: Path, coracao_orquestrador: Any, sistema_memoria: SistemaMemoriaHibrido):
        self.caminho_base = Path(caminho_base_dados)
        self.motores: Dict[str, MotorDecisao] = {}
        self.logger = logging.getLogger("FabricaMotores")
        self.coracao = coracao_orquestrador
        self.sistema_memoria = sistema_memoria
        self.caminho_base.mkdir(parents=True, exist_ok=True)
        (self.caminho_base / "memoria").mkdir(parents=True, exist_ok=True)
        self.logger.info("ðŸ­ Fábrica de Motores inicializada em %s", self.caminho_base)
    
    def obter_motor(self, nome_filha: str) -> MotorDecisao:
        if nome_filha not in self.motores:
            self.motores[nome_filha] = MotorDecisao(
                nome_filha=nome_filha,
                caminho_dados=self.caminho_base,
                coracao_orquestrador=self.coracao,
                sistema_memoria=self.sistema_memoria
            )
            self.logger.info("ðŸ†• Motor criado para %s", nome_filha)
        return self.motores[nome_filha]
    
    def health_check(self) -> Dict[str, Any]:
        return {
            "total_motores": len(self.motores),
            "motores_ativos": list(self.motores.keys()),
            "status": "healthy" if self.motores else "no_motors",
            "caminho_base": str(self.caminho_base),
            "timestamp": datetime.now().isoformat()
        }



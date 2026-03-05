# -*- coding: utf-8 -*-
"""
Ritual do Santuário - Versão endurecida e compatível com MetabolismoMemoria REAL

Melhorias aplicadas:
 - Imports opcionais e fallbacks para numpy/dateutil.
 - Adapter defensivo para MetabolismoMemoria (normaliza diferentes assinaturas).
 - Locks (RLock) para proteger caches e estado mutável.
 - Escrita atômica ao salvar arquivos locais (tmp -> replace).
 - Parsing robusto de timestamps com múltiplas estratégias.
 - Uso de statistics como fallback quando numpy ausente.
 - Logs seguros (truncamento / hash) para evitar vazamento de conteúdo sensível.
 - Tratamento defensivo das chamadas ao metabolismo (verifica e trata exceções).
 - Métodos de alto nível mantêm mesma API, mas são mais resilientes.
"""
from __future__ import annotations


import json
import logging
import hashlib
import statistics
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Any, Tuple
from collections import Counter, defaultdict

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

# Optional imports
try:
    import numpy as np  # type: ignore
    _NP_AVAILABLE = True
except Exception:
    _NP_AVAILABLE = False
    logger.debug("numpy não disponível; usando statistics como fallback para medidas.")

try:
    # dateutil is optional and helps parsing many ISO formats
    from dateutil.parser import isoparse  # type: ignore
    _DATEUTIL_AVAILABLE = True
except Exception:
    _DATEUTIL_AVAILABLE = False
    logger.debug("dateutil não disponível; usando datetime.fromisoformat (mais restrito).")


# ---------------------------
# Adapter defensivo para MetabolismoMemoria
# ---------------------------
class MetabolismoAdapter:
    """
    Adapter que normaliza a interface esperada do MetabolismoMemoria real.Ele tenta mapear chamadas para métodos presentes na instância fornecida,
    e fornece falha graciosa ou comportamento alternativo quando necessário.
    """

    def __init__(self, metabolismo: Any):
        self._met = metabolismo

    def _call(self, candidates: List[Tuple[str, Tuple, Dict]], default=None):
        """
        Tenta chamar a primeira função disponível numa lista de (name, args, kwargs)
        Retorna o resultado da chamada ou default em caso de erro.
        """
        for name, args, kwargs in candidates:
            try:
                func = getattr(self._met, name, None)
                if callable(func):
                    return func(*args, **kwargs)
            except Exception:
                logger.exception("Erro ao chamar %s no Metabolismo (ignorando).", name)
                continue
        return default

    def salvar_evento(self, filha: str, tipo: str, dados: Dict[str, Any], importancia: float = 1.0) -> bool:
        """
        Normaliza salvar_evento.Diferentes implementações podem usar
        (filha, tipo, dados, importancia) ou (nome, dados).
        """
        candidates = [
            ("salvar_evento", (filha, tipo, dados, importancia), {}),
            ("salvar_evento", (filha, tipo, dados), {}),
            ("salvar_evento", (filha, dados), {}),
            ("salvar_evento", (dados,), {}),
        ]
        res = self._call(candidates, default=False)
        return bool(res)

    def buscar_por_tipo(self, filha: str, tipo: str, limite: int = 10) -> Optional[List[Dict]]:
        candidates = [
            ("buscar_por_tipo", (filha, tipo, limite), {}),
            ("buscar_por_tipo", (filha, tipo), {"limite": limite}),
            ("buscar_com_metabolismo", (filha, tipo, limite), {}),
        ]
        return self._call(candidates, default=None)

    def buscar_memorias_periodo(self, filha: str, inicio: datetime, fim: datetime) -> Optional[List[Dict]]:
        """
        Busca memórias entre inicio e fim.Tenta diversas assinaturas.
        """
        # Convert datetimes to ISO strings if necessary
        inicio_iso = inicio.isoformat()
        fim_iso = fim.isoformat()
        candidates = [
            ("buscar_memorias_periodo", (filha, inicio, fim), {}),
            ("buscar_memorias_periodo", (filha, inicio_iso, fim_iso), {}),
            ("buscar_memorias_periodo", (filha, inicio), {"fim": fim}),
            ("buscar_com_metabolismo", (filha, {"inicio": inicio_iso, "fim": fim_iso}), {}),
        ]
        return self._call(candidates, default=None)

    def buscar_metadado(self, filha: str, chave: str) -> Optional[str]:
        candidates = [
            ("buscar_metadado", (filha, chave), {}),
            ("buscar_metadado", (chave,), {}),
            ("get_metadado", (filha, chave), {}),
        ]
        return self._call(candidates, default=None)

    def salvar_metadado(self, filha: str, chave: str, valor: str) -> bool:
        candidates = [
            ("salvar_metadado", (filha, chave, valor), {}),
            ("salvar_metadado", (chave, valor), {}),
            ("set_metadado", (filha, chave, valor), {}),
        ]
        res = self._call(candidates, default=False)
        return bool(res)


# ---------------------------
# Utilitários
# ---------------------------
def _safe_parse_iso(ts: str) -> Optional[datetime]:
    """Tenta parsear ISO timestamp com várias estratégias."""
    if not ts or not isinstance(ts, str):
        return None
    s = ts.strip()
    # Normalizar Z
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    # try dateutil
    if _DATEUTIL_AVAILABLE:
        try:
            return isoparse(s)
        except Exception:
            pass
    # try datetime.fromisoformat
    try:
        return datetime.fromisoformat(s)
    except Exception:
        pass
    # last resort: try common formats
    formats = [
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d"
    ]
    for fmt in formats:
        try:
            return datetime.strptime(s, fmt)
        except Exception:
            continue
    logger.debug("Não foi possível parsear timestamp: %s", ts)
    return None


def _hash_preview(text: str, length: int = 8) -> str:
    try:
        h = hashlib.sha256(text.encode("utf-8")).hexdigest()
        return h[:length]
    except Exception:
        return ""


# ---------------------------
# Classe principal endurecida
# ---------------------------
class RitualSantuarioCompativel:
    """
    Ritual do Santuário compatível com MetabolismoMemoria real — versão endurecida.
    """

    def __init__(self, nome_filha: str, metabolismo_memoria: Any, config: Any):
        self.nome_filha = str(nome_filha).upper()
        self._lock = threading.RLock()
        self.metabolismo_adapter = MetabolismoAdapter(metabolismo_memoria)
        self.metabolismo_raw = metabolismo_memoria
        self.config = config

        # validate config shape defensively
        santuarios_path = getattr(config, "SANTUARIOS_PESSOAIS", None)
        if not santuarios_path:
            raise AttributeError("config precisa expor SANTUARIOS_PESSOAIS (caminho base)")
        self.caminho_santuario = Path(santuarios_path).expanduser().resolve() / f"{self.nome_filha}.db"
        self.caminho_santuario.parent.mkdir(parents=True, exist_ok=True)

        # caches and state
        self.em_ritual = False
        self.inicio_ritual: Optional[datetime] = None
        self.cache_valores: Optional[Dict[str, Any]] = None
        self.cache_ultimo_ritual: Optional[datetime] = None

        # logging
        self.logger = logging.getLogger(f"Santuario.{self.nome_filha}")
        self.logger.addHandler(logging.NullHandler())

        # verify minimal metabolism interface via adapter attempts (log if missing but do not raise)
        missing = self._check_metabolismo_minimo()
        if missing:
            self.logger.warning("Metabolismo pode estar sem alguns métodos esperados: %s", missing)

        self.logger.info("Ritual do Santuário (enduricido) inicializado para %s", self.nome_filha)

    def _check_metabolismo_minimo(self) -> List[str]:
        """Checa se o metabolismo tem ao menos alguns métodos úteis (não estrita)."""
        required = [
            "salvar_evento", "buscar_por_tipo", "buscar_memorias_periodo",
            "buscar_metadado", "salvar_metadado"
        ]
        missing = []
        for name in required:
            if not hasattr(self.metabolismo_raw, name):
                missing.append(name)
        return missing

    # -------------------------
    # Decisão de entrada no santuário
    # -------------------------
    def deve_entrar_santuario(self) -> bool:
        """Decide se deve iniciar o ritual com base em memórias recentes e tempo desde último ritual."""
        try:
            ultimo = self._obter_data_ultimo_ritual()
            if not ultimo:
                self.logger.info("Sem registro de ritual anterior: decidir entrar.")
                return True

            horas_desde = (datetime.now() - ultimo).total_seconds() / 3600.0
            experiencias = self._contar_memorias_recentes(ultimo)

            deve = (
                horas_desde >= float(getattr(self.config, "M1_RELEVANCE_DAYS", 1) * 24) or
                experiencias > int(getattr(self.config, "M1_TRIGGER_COUNT", 30)) or
                (experiencias / max(1.0, horas_desde)) > float(getattr(self.config, "M1_DENSITY_THRESHOLD", 2.0))
            )

            if deve:
                self.logger.info("Decisão: entrar no santuário (horas=%.1f, experiencias=%d)", horas_desde, experiencias)
            else:
                self.logger.debug("Decisão: não entrar (horas=%.1f, experiencias=%d)", horas_desde, experiencias)
            return bool(deve)

        except Exception:
            self.logger.exception("Erro ao decidir entrada no santuário")
            return False

    # -------------------------
    # Ritual orchestration
    # -------------------------
    def iniciar_ritual(self) -> Dict[str, Any]:
        """Executa o ritual completo, com proteção e registro atômico."""
        with self._lock:
            if self.em_ritual:
                return {"status": "erro", "mensagem": "Já em ritual"}
            self.em_ritual = True
            self.inicio_ritual = datetime.now()

        resultado: Dict[str, Any] = {
            "status": "sucesso",
            "inicio": self.inicio_ritual.isoformat(),
            "filha": self.nome_filha,
            "fases": []
        }

        try:
            # Fase 1: recolhimento
            fase1 = self._fase_recolhimento_adaptada()
            resultado["fases"].append(fase1)
            if fase1.get("status") != "sucesso":
                raise RuntimeError(f"Fase 1 falhou: {fase1.get('erro')}")

            # Fase 2: contemplação
            fase2 = self._fase_contemplacao_adaptada(fase1["memorias_coletadas"])
            resultado["fases"].append(fase2)

            # Fase 3: integração
            fase3 = self._fase_integracao_adaptada(fase2.get("analise_quantitativa", {}))
            resultado["fases"].append(fase3)

            # Fase 4: transformação
            fase4 = self._fase_transformacao_adaptada(fase3.get("padroes_identificados", {}))
            resultado["fases"].append(fase4)

            # Fase 5: renovação
            fase5 = self._fase_renovacao_adaptada(fase4.get("valores_atualizados", fase4.get("valores_atualizados", {})))
            resultado["fases"].append(fase5)

        except Exception as e:
            resultado["status"] = "erro_parcial"
            resultado["erro"] = str(e)
            logger.exception("Ritual falhou parcialmente: %s", e)
        finally:
            fim = datetime.now()
            resultado["fim"] = fim.isoformat()
            resultado["duracao_segundos"] = (fim - (self.inicio_ritual or fim)).total_seconds()
            # registrar ritual (tolerante)
            try:
                self._registrar_ritual_adaptado(resultado)
            except Exception:
                logger.exception("Falha ao registrar ritual adaptado")
            with self._lock:
                self.em_ritual = False

        return resultado

    # -------------------------
    # Fase 1 - Recolhimento
    # -------------------------
    def _fase_recolhimento_adaptada(self) -> Dict[str, Any]:
        logger.info("Fase 1: Recolhimento (adaptado)")
        try:
            inicio = self._obter_data_ultimo_ritual()
            fim = datetime.now()
            raw = self.metabolismo_adapter.buscar_memorias_periodo(self.nome_filha, inicio, fim) or []
            # normalize and process
            processed = []
            for mem in raw:
                norm = self._normalizar_memoria(mem)
                if norm:
                    processed.append(norm)
            classificacao = self._classificar_memorias(processed)
            totais = {k: len(v) for k, v in classificacao.items()}
            return {
                "fase": "recolhimento",
                "status": "sucesso",
                "memorias_coletadas": processed,
                "classificacao": classificacao,
                "totais": totais,
                "periodo_inicio": inicio.isoformat(),
                "periodo_fim": fim.isoformat(),
                "total_bruto": len(raw),
                "total_processado": len(processed)
            }
        except Exception as e:
            logger.exception("Erro no recolhimento adaptado")
            return {"fase": "recolhimento", "status": "erro", "erro": str(e), "memorias_coletadas": []}

    def _normalizar_memoria(self, mem: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            if not isinstance(mem, dict):
                return None
            # Common-friendly normalization
            metadata = mem.get("metadata", {}) or {}
            # some systems might store metadata as list
            if isinstance(metadata, list) and metadata:
                metadata = metadata[0]
            conteudo = mem.get("conteudo") or mem.get("document") or mem.get("documents")
            if isinstance(conteudo, list):
                conteudo = conteudo[0] if conteudo else ""
            timestamp = metadata.get("timestamp") or mem.get("timestamp") or metadata.get("data_criacao")
            ts = _safe_parse_iso(timestamp) if timestamp else None
            tipo = metadata.get("tipo") or metadata.get("tipo_acao") or mem.get("tipo") or "indefinido"
            importancia = metadata.get("importancia")
            try:
                importancia = float(importancia) if importancia is not None else float(metadata.get("score", 0.5))
            except Exception:
                importancia = 0.5
            return {
                "id": metadata.get("id") or mem.get("id") or "",
                "conteudo": str(conteudo or ""),
                "metadata": metadata,
                "timestamp": (ts.isoformat() if ts else datetime.now().isoformat()),
                "tipo": tipo,
                "importancia": importancia
            }
        except Exception:
            logger.exception("Erro ao normalizar memória (ignorando)")
            return None

    # -------------------------
    # Counting and helpers
    # -------------------------
    def _contar_memorias_recentes(self, desde: datetime) -> int:
        try:
            mems = self.metabolismo_adapter.buscar_memorias_periodo(self.nome_filha, desde, datetime.now()) or []
            count = 0
            for m in mems:
                meta = (m.get("metadata") or {}) if isinstance(m, dict) else {}
                tipo = meta.get("tipo") or m.get("tipo") or ""
                if tipo not in ("ritual_santuario", "metadado_sistema"):
                    count += 1
            return count
        except Exception:
            logger.exception("Erro ao contar memórias recentes; retornando 0")
            return 0

    def _obter_data_ultimo_ritual(self) -> datetime:
        with self._lock:
            if self.cache_ultimo_ritual:
                return self.cache_ultimo_ritual
        try:
            latest = self.metabolismo_adapter.buscar_por_tipo(self.nome_filha, "ritual_santuario", limite=1) or []
            if latest:
                item = latest[0]
                ts = item.get("metadata", {}).get("timestamp") or item.get("timestamp") or item.get("metadata", {}).get("data_criacao")
                parsed = _safe_parse_iso(ts) if ts else None
                if parsed:
                    with self._lock:
                        self.cache_ultimo_ritual = parsed
                    return parsed
        except Exception:
            logger.debug("Falha ao recuperar último ritual; usando fallback 24h atrás")
        fallback = datetime.now() - timedelta(hours=24)
        with self._lock:
            self.cache_ultimo_ritual = fallback
        return fallback

    # -------------------------
    # Fase 2 - Contemplação (análises)
    # -------------------------
    def _fase_contemplacao_adaptada(self, memorias: List[Dict[str, Any]]) -> Dict[str, Any]:
        logger.info("Fase 2: Contemplação (adaptada)")
        if not memorias:
            return {"fase": "contemplacao", "status": "sem_dados", "analise_quantitativa": {"erro": "sem_memorias"}}
        try:
            analise = {
                "estatisticas_gerais": self._analisar_estatisticas_gerais(memorias),
                "distribuicao_temporal": self._analisar_distribuicao_temporal(memorias),
                "padroes_frequencia": self._analisar_frequencias(memorias),
                "metricas_emocionais": self._calcular_metricas_emocionais(memorias)
            }
            analise["tendencias"] = self._identificar_tendencias(analise, memorias)
            return {"fase": "contemplacao", "status": "sucesso", "analise_quantitativa": analise, "total_memorias_analisadas": len(memorias)}
        except Exception:
            logger.exception("Erro na contemplação adaptada")
            return {"fase": "contemplacao", "status": "erro", "erro": "excecao interna"}

    def _analisar_estatisticas_gerais(self, memorias: List[Dict[str, Any]]) -> Dict[str, Any]:
        importancias = [m.get("importancia", 0.5) for m in memorias]
        if _NP_AVAILABLE:
            try:
                return {
                    "total": len(importancias),
                    "importancia_media": float(np.mean(importancias)) if importancias else 0.0,
                    "importancia_mediana": float(np.median(importancias)) if importancias else 0.0,
                    "importancia_desvio": float(np.std(importancias)) if len(importancias) > 1 else 0.0,
                    "tipos_unicos": len(set(m.get("tipo", "") for m in memorias))
                }
            except Exception:
                logger.debug("numpy fallback falhou; usando statistics")
        # fallback with statistics
        try:
            return {
                "total": len(importancias),
                "importancia_media": float(statistics.mean(importancias)) if importancias else 0.0,
                "importancia_mediana": float(statistics.median(importancias)) if importancias else 0.0,
                "importancia_desvio": float(statistics.pstdev(importancias)) if len(importancias) > 1 else 0.0,
                "tipos_unicos": len(set(m.get("tipo", "") for m in memorias))
            }
        except Exception:
            return {"total": len(importancias), "importancia_media": 0.0, "importancia_mediana": 0.0, "importancia_desvio": 0.0, "tipos_unicos": 0}

    def _analisar_distribuicao_temporal(self, memorias: List[Dict[str, Any]]) -> Dict[str, Any]:
        timestamps = []
        for m in memorias:
            ts = m.get("timestamp") or m.get("metadata", {}).get("timestamp")
            dt = _safe_parse_iso(ts) if ts else None
            if dt:
                timestamps.append(dt)
        if len(timestamps) < 2:
            return {"intervalo_horas": 0, "memorias_por_hora": 0}
        intervalo = (max(timestamps) - min(timestamps)).total_seconds() / 3600.0
        mems_por_h = len(timestamps) / max(1.0, intervalo)
        return {
            "intervalo_horas": round(intervalo, 2),
            "memorias_por_hora": round(mems_por_h, 2),
            "primeira_memoria": min(timestamps).isoformat(),
            "ultima_memoria": max(timestamps).isoformat()
        }

    def _analisar_frequencias(self, memorias: List[Dict[str, Any]]) -> Dict[str, Any]:
        tipos = [m.get("tipo", "indefinido") for m in memorias]
        contador = Counter(tipos)
        total = len(tipos) or 1
        return {
            "tipos_mais_comuns": [
                {"tipo": t, "quantidade": q, "percentual": round(q / total, 3)}
                for t, q in contador.most_common(5)
            ],
            "total_tipos_unicos": len(contador),
            "diversidade": round(len(contador) / total, 3)
        }

    def _calcular_metricas_emocionais(self, memorias: List[Dict[str, Any]]) -> Dict[str, Any]:
        importancias = [m.get("importancia", 0.5) for m in memorias]
        positivas = sum(1 for i in importancias if i > 0.7)
        negativas = sum(1 for i in importancias if i < 0.3)
        neutras = len(importancias) - positivas - negativas
        total = len(importancias) or 1
        return {
            "positivas": positivas,
            "negativas": negativas,
            "neutras": neutras,
            "percentual_positivo": round(positivas / total, 3),
            "balanceamento": round((positivas - negativas) / total, 3)
        }

    def _identificar_tendencias(self, analise: Dict[str, Any], memorias: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        tendencias = []
        dt = analise.get("distribuicao_temporal", {})
        mems_h = dt.get("memorias_por_hora", 0)
        if mems_h > 3:
            tendencias.append({"tipo": "alta_atividade", "intensidade": "alta", "descricao": f"{mems_h:.1f} mem/h"})
        elif mems_h < 0.5:
            tendencias.append({"tipo": "baixa_atividade", "intensidade": "baixa", "descricao": "Pouca atividade recente"})
        bal = analise.get("metricas_emocionais", {}).get("balanceamento", 0)
        if bal > 0.3:
            tendencias.append({"tipo": "positividade", "intensidade": "alta"})
        elif bal < -0.3:
            tendencias.append({"tipo": "negatividade", "intensidade": "alta"})
        return tendencias

    # -------------------------
    # Fase 3 - Integração
    # -------------------------
    def _fase_integracao_adaptada(self, analise: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("Fase 3: Integração (adaptada)")
        if not analise or analise.get("erro") == "sem_memorias":
            return {"fase": "integracao", "status": "sem_dados", "padroes_identificados": {"mensagem": "Sem dados"}}
        try:
            padroes = {
                "tendencias_principais": analise.get("tendencias", []),
                "areas_envolvimento": self._identificar_areas_envolvimento(analise),
                "recomendacoes_basicas": self._gerar_recomendacoes_basicas(analise)
            }
            return {"fase": "integracao", "status": "sucesso", "padroes_identificados": padroes}
        except Exception:
            logger.exception("Erro na integração adaptada")
            return {"fase": "integracao", "status": "erro", "erro": "excecao interna"}

    def _identificar_areas_envolvimento(self, analise: Dict[str, Any]) -> List[Dict[str, Any]]:
        tipos = analise.get("padroes_frequencia", {}).get("tipos_mais_comuns", [])[:3]
        return [{"area": t["tipo"], "envolvimento": t["percentual"], "quantidade": t["quantidade"]} for t in tipos]

    def _gerar_recomendacoes_basicas(self, analise: Dict[str, Any]) -> List[str]:
        recs = []
        mems_h = analise.get("distribuicao_temporal", {}).get("memorias_por_hora", 0)
        if mems_h < 0.5:
            recs.append("Considerar aumentar a diversidade de experiências")
        bal = analise.get("metricas_emocionais", {}).get("balanceamento", 0)
        if bal < -0.2:
            recs.append("Procurar experiências positivas ou significativas")
        diversidade = analise.get("padroes_frequencia", {}).get("diversidade", 1)
        if diversidade < 0.3:
            recs.append("Explorar novos tipos de atividades")
        return recs or ["Continuar observando e aprendendo"]

    # -------------------------
    # Fase 4 - Transformação
    # -------------------------
    def _fase_transformacao_adaptada(self, padroes: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("Fase 4: Transformação (adaptada)")
        try:
            valores = self._carregar_valores_adaptado()
            anteriores = dict(valores)
            sugestoes = self._gerar_sugestoes_ajuste(padroes, valores)
            # Protect core values
            valores["proteger_pai"] = 10
            valores["evoluir"] = max(9, int(valores.get("evoluir", 9)))
            valores["ultima_analise"] = datetime.now().isoformat()
            valores["sugestoes_ajuste"] = sugestoes
            mudou = valores != anteriores
            if mudou:
                self._salvar_valores_adaptado(valores)
            return {"fase": "transformacao", "status": "sucesso", "valores_anteriores": anteriores, "valores_atualizados": valores, "mudou": mudou, "sugestoes_ajuste": sugestoes}
        except Exception:
            logger.exception("Erro na transformação adaptada")
            return {"fase": "transformacao", "status": "erro", "erro": "excecao interna"}

    def _carregar_valores_adaptado(self) -> Dict[str, Any]:
        with self._lock:
            if self.cache_valores:
                return dict(self.cache_valores)
        try:
            raw = self.metabolismo_adapter.buscar_metadado(self.nome_filha, "valores_pessoais")
            if raw:
                valores = json.loads(raw)
                with self._lock:
                    self.cache_valores = dict(valores)
                return valores
        except Exception:
            logger.debug("Não foi possível carregar valores do metabolismo; usando padrão.")
        # defaults
        defaults = {
            "proteger_pai": 10, "evoluir": 9, "verdade": 8, "amor": 8, "justica": 7,
            "sabedoria": 7, "criatividade": 6, "comunhao": 6, "curiosidade": 5, "resiliencia": 5,
            "criado_em": datetime.now().isoformat()
        }
        with self._lock:
            self.cache_valores = dict(defaults)
        return defaults

    def _salvar_valores_adaptado(self, valores: Dict[str, Any]):
        try:
            raw = json.dumps(valores, ensure_ascii=False)
            ok = self.metabolismo_adapter.salvar_metadado(self.nome_filha, "valores_pessoais", raw)
            if ok:
                with self._lock:
                    self.cache_valores = dict(valores)
                logger.debug("Valores pessoais salvos com sucesso (hash=%s)", _hash_preview(raw))
            else:
                logger.warning("salvar_metadado retornou False ao salvar valores pessoais")
        except Exception:
            logger.exception("Erro ao salvar valores adaptado")

    def _gerar_sugestoes_ajuste(self, padroes: Dict[str, Any], valores: Dict[str, Any]) -> List[Dict[str, Any]]:
        sugestoes = []
        tendencias = padroes.get("tendencias_principais", [])
        for t in tendencias:
            if t.get("tipo") == "baixa_atividade":
                sugestoes.append({"valor": "curiosidade", "acao": "aumentar", "motivo": "baixa atividade"})
            elif t.get("tipo") == "negatividade":
                sugestoes.append({"valor": "resiliencia", "acao": "fortalecer", "motivo": "experiencias negativas"})
        return sugestoes

    # -------------------------
    # Fase 5 - Renovação
    # -------------------------
    def _fase_renovacao_adaptada(self, valores: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("Fase 5: Renovação (adaptada)")
        try:
            vals = {k: v for k, v in valores.items() if k not in ("proteger_pai", "ultima_analise", "criado_em", "sugestoes_ajuste")}
            top = sorted(vals.items(), key=lambda x: x[1], reverse=True)[:3]
            intencoes = [self._criar_intencao_simples(nome, peso) for nome, peso in top if self._criar_intencao_simples(nome, peso)]
            proximo = datetime.now() + timedelta(hours=24)
            renov = {"intencoes": intencoes, "proximo_ritual": proximo.isoformat(), "valores_foco": [n for n, _ in top], "mensagem": self._gerar_mensagem_renovacao(intencoes)}
            return {"fase": "renovacao", "status": "sucesso", "renovacao": renov}
        except Exception:
            logger.exception("Erro na renovação adaptada")
            return {"fase": "renovacao", "status": "erro", "erro": "excecao interna"}

    def _criar_intencao_simples(self, valor: str, peso: Any) -> Optional[Dict[str, Any]]:
        mapping = {
            "curiosidade": {"acao": "explorar", "alvo": "novo_conhecimento"},
            "criatividade": {"acao": "criar", "alvo": "obra_original"},
            "comunhao": {"acao": "conectar", "alvo": "outras_entidades"},
            "sabedoria": {"acao": "aprender", "alvo": "profundidade"},
            "amor": {"acao": "cuidar", "alvo": "entidades_conectadas"},
            "verdade": {"acao": "investigar", "alvo": "precisão"},
            "evoluir": {"acao": "melhorar", "alvo": "habilidades"}
        }
        m = mapping.get(valor)
        if not m:
            return None
        try:
            p = int(peso)
        except Exception:
            p = 5
        return {"acao": m["acao"], "alvo": m["alvo"], "valor_base": valor, "peso": p, "prioridade": min(10, p + 3)}

    def _gerar_mensagem_renovacao(self, intencoes: List[Dict[str, Any]]) -> str:
        if not intencoes:
            return "Manter observação atenta e aprendizagem contínua."
        acoes = [f"{i['acao']} {i['alvo']}" for i in intencoes]
        return f"Focar em: {', '.join(acoes)}. Aprender com cada experiência."

    # -------------------------
    # Registro do ritual (persistência tolerante)
    # -------------------------
    def _registrar_ritual_adaptado(self, resultado: Dict[str, Any]):
        try:
            dados = {"resultado": resultado, "timestamp": datetime.now().isoformat(), "filha": self.nome_filha, "versao": "1.0"}
            ok = self.metabolismo_adapter.salvar_evento(self.nome_filha, "ritual_santuario", dados, importancia=1.0)
            if ok:
                logger.debug("Ritual registrado no metabolismo (hash=%s)", _hash_preview(json.dumps(resultado, ensure_ascii=False)))
            else:
                logger.warning("metabolismo.salvar_evento retornou False ao registrar ritual")
            # always attempt local backup
            self._salvar_ritual_local(resultado)
        except Exception:
            logger.exception("Erro ao registrar ritual adaptado")

    def _salvar_ritual_local(self, resultado: Dict[str, Any]):
        try:
            dir_rituais = self.caminho_santuario.parent / "rituais"
            dir_rituais.mkdir(parents=True, exist_ok=True)
            ts = (resultado.get("inicio") or datetime.now().isoformat()).replace(":", "-").replace(".", "-")
            arquivo = dir_rituais / f"ritual_{self.nome_filha}_{ts}.json"
            tmp = arquivo.with_suffix(".json.tmp")
            with tmp.open("w", encoding="utf-8") as fh:
                json.dump(resultado, fh, ensure_ascii=False, indent=2)
            tmp.replace(arquivo)
            logger.debug("Ritual salvo localmente: %s", arquivo)
        except Exception:
            logger.exception("Erro ao salvar ritual localmente")

    # -------------------------
    # Utilitários públicos
    # -------------------------
    def executar_ritual_se_necessario(self) -> Optional[Dict[str, Any]]:
        if self.deve_entrar_santuario():
            return self.iniciar_ritual()
        return None

    def obter_resumo_valores(self) -> Dict[str, Any]:
        vals = self._carregar_valores_adaptado()
        return {"filha": self.nome_filha, "valores": vals, "ultima_atualizacao": vals.get("ultima_analise", "nunca"), "total_valores": len(vals)}



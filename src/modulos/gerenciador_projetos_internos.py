#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ARCA CELESTIAL GENESIS - GUARDIÍO MEMÓRIA AFETIVA (ajustado, defensivo)

Responsabilidade:
 - Buscar memórias afetivas positivas e sugerir ao Pai (UI) quando apropriado.
 - Persistência atômica do histórico de sugestões.
 - Thread-safe, defensivo quanto a dependências (GerenciadorMemoria, LenteDaAlma, EnfermeiroDigital).
 - Não bloqueia ao enfileirar mensagens na UI (usa timeout / fallback).
"""
from __future__ import annotations


import json
import logging
import os
import random
import shutil
import threading
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from queue import Queue
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

# Caminhos default (podem ser sobrescritos em testes)
CAMINHO_RAIZ_ARCA = Path("./Arca_Celestial_Genesis").expanduser().resolve()
SANTUARIOS_PATH = CAMINHO_RAIZ_ARCA / "Santuarios"
SANTUARIOS_PESSOAIS_PATH = SANTUARIOS_PATH / "Santuarios_Pessoais"
SUGESTOES_MEMORIA_AFETIVA_JSON = SANTUARIOS_PESSOAIS_PATH / "sugestoes_memoria_afetiva.json"


def _atomic_write_json(caminho: Path, dados: Any) -> None:
    """Grava JSON de forma atômica (tmp -> replace)."""
    caminho.parent.mkdir(parents=True, exist_ok=True)
    tmp = caminho.with_suffix(".tmp")
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(dados, f, indent=2, ensure_ascii=False, default=str)
        try:
            os.replace(str(tmp), str(caminho))
        except Exception:
            tmp.rename(caminho)
    finally:
        try:
            if tmp.exists():
                tmp.unlink()
        except Exception:
            pass


class GuardiaoMemoriaAfetiva:
    """
    Guardião da Memória Afetiva - versão robusta e defensiva.Dependências opcionais (serão tratadas defensivamente):
      - coracao.gerenciador_memoria.consultar_santuario(...)
      - coracao.lente_da_alma.analisar_sentimento(...)
      - coracao.enfermeiro_digital._inferir_humor_pai_recente()
      - coracao.response_queue (Queue) para enviar notificações Í  UI
      - coracao.motor_de_rotina.pc_esta_ocioso(nivel)
    """

    def __init__(self, coracao_ref: Any):
        self.coracao = coracao_ref
        self.logger = logging.getLogger(self.__class__.__name__)
        self._lock = threading.RLock()

        # Monitoramento
        self._monitorando: bool = False
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

        # Paths e estado
        self.sugestoes_path: Path = SUGESTOES_MEMORIA_AFETIVA_JSON
        self.sugestoes_path.parent.mkdir(parents=True, exist_ok=True)
        self.historico_sugestoes: List[Dict[str, Any]] = self._carregar_historico_sugestoes()

        # Timestamp da última sugestão ao Pai
        self.ultima_sugestao_pai: datetime = datetime.min

        self.logger.info("[GUARDIÍO MEMÓRIA AFETIVA] Instanciado (modo real/defensivo).")

    def _carregar_historico_sugestoes(self) -> List[Dict[str, Any]]:
        caminho = self.sugestoes_path
        if not caminho.exists():
            self.logger.debug("[GUARDIÍO MEMÓRIA AFETIVA] Arquivo de sugestões não encontrado; iniciando vazio.")
            return []
        try:
            with open(caminho, "r", encoding="utf-8") as f:
                dados_raw = json.load(f)
            if isinstance(dados_raw, list):
                self.logger.info("[GUARDIÍO MEMÓRIA AFETIVA] %d sugestões carregadas de %s", len(dados_raw), caminho)
                return dados_raw
            else:
                self.logger.error("[GUARDIÍO MEMÓRIA AFETIVA] Formato inválido no arquivo de sugestões (esperado lista).")
                return []
        except Exception as e:
            self.logger.exception("[GUARDIÍO MEMÓRIA AFETIVA] Erro ao carregar histórico de sugestões: %s", e)
            # cria backup do arquivo corrompido para análise posterior
            try:
                backup = caminho.with_suffix(".corrompido_backup")
                shutil.copy(str(caminho), str(backup))
                self.logger.warning("[GUARDIÍO MEMÓRIA AFETIVA] Backup do arquivo corrompido criado: %s", backup)
            except Exception:
                self.logger.exception("[GUARDIÍO MEMÓRIA AFETIVA] Falha ao criar backup do arquivo corrompido")
            return []

    def _salvar_historico_sugestoes(self) -> None:
        with self._lock:
            dados = list(self.historico_sugestoes)
        try:
            _atomic_write_json(self.sugestoes_path, dados)
            self.logger.debug("[GUARDIÍO MEMÓRIA AFETIVA] Histórico salvo em %s", self.sugestoes_path)
        except Exception:
            self.logger.exception("[GUARDIÍO MEMÓRIA AFETIVA] Falha ao salvar histórico de sugestões")
            raise

    def iniciar_monitoramento(self) -> None:
        if self._monitorando:
            self.logger.debug("[GUARDIÍO MEMÓRIA AFETIVA] Monitoramento já ativo.")
            return
        self._monitorando = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._loop_monitoramento, daemon=True, name="GuardiaoMemoriaAfetiva")
        self._thread.start()
        self.logger.info("[GUARDIÍO MEMÓRIA AFETIVA] Monitoramento iniciado.")

    def parar_monitoramento(self) -> None:
        if not self._monitorando:
            return
        self._monitorando = False
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5.0)
        # salvar estado final de forma segura
        try:
            self._salvar_historico_sugestoes()
        except Exception:
            self.logger.exception("[GUARDIÍO MEMÓRIA AFETIVA] Erro ao salvar histórico no parar_monitoramento")
        self.logger.info("[GUARDIÍO MEMÓRIA AFETIVA] Monitoramento parado.")

    def _safe_put_response(self, payload: Dict[str, Any]) -> None:
        """Enfileira para response_queue de forma não bloqueante (timeout + put_nowait fallback)."""
        resp_q: Optional[Queue] = getattr(self.coracao, "response_queue", None)
        if resp_q is None:
            self.logger.debug("[GUARDIÍO MEMÓRIA AFETIVA] response_queue indisponível; dropando payload.")
            return
        try:
            resp_q.put(payload, timeout=0.5)
        except Exception:
            try:
                resp_q.put_nowait(payload)
            except Exception:
                self.logger.debug("[GUARDIÍO MEMÓRIA AFETIVA] Falha ao enfileirar payload na response_queue; descartado.")

    def _loop_monitoramento(self) -> None:
        self.logger.info("[GUARDIÍO MEMÓRIA AFETIVA] Loop de monitoramento iniciado.")
        # espera inicial (ajustável)
        initial_wait = random.randint(300, 900)
        self._stop_event.wait(timeout=initial_wait)

        while self._monitorando and not self._stop_event.is_set():
            try:
                motor = getattr(self.coracao, "motor_de_rotina", None)
                if motor and hasattr(motor, "pc_esta_ocioso"):
                    try:
                        if motor.pc_esta_ocioso(nivel="leve"):
                            self._sugerir_memoria_afetiva_ao_pai()
                            self._detectar_problemas_e_propor_projetos()  # Adicionado
                        else:
                            self.logger.debug("[GUARDIÍO MEMÓRIA AFETIVA] PC em uso; pulando sugestão.")
                    except Exception:
                        self.logger.exception("[GUARDIÍO MEMÓRIA AFETIVA] Erro consultando pc_esta_ocioso")
                else:
                    self.logger.debug("[GUARDIÍO MEMÓRIA AFETIVA] motor_de_rotina indisponível.")

                # espera interrompível entre ciclos (15-30 min)
                wait_seconds = random.randint(900, 1800)
                self._stop_event.wait(timeout=wait_seconds)

            except Exception:
                self.logger.exception("[GUARDIÍO MEMÓRIA AFETIVA] Erro no loop de monitoramento; aguardando e continuando.")
                self._stop_event.wait(timeout=300)

        self.logger.info("[GUARDIÍO MEMÓRIA AFETIVA] Loop encerrado.")
        try:
            self._salvar_historico_sugestoes()
        except Exception:
            self.logger.exception("[GUARDIÍO MEMÓRIA AFETIVA] Erro salvando histórico ao encerrar loop")

    def _detectar_problemas_e_propor_projetos(self) -> None:
        """
        Novo: Detecta problemas do 'Pai' via memória afetiva e propõe projetos/ferramentas.
        Ex.: Se memórias indicam falta de leitor PDF, propõe ferramenta.
        """
        # Buscar memórias com problemas (ex.: "não consigo ler PDF")
        problemas = []
        gerenciador = getattr(self.coracao, "gerenciador_memoria", None)
        if gerenciador and hasattr(gerenciador, "consultar_santuario"):
            try:
                docs = gerenciador.consultar_santuario(
                    consulta="Problemas ou necessidades do Pai, como falta de ferramentas ou dificuldades.",
                    proprietario="coletivo",
                    n_resultados=5
                ) or []
                for doc in docs:
                    texto = doc if isinstance(doc, str) else doc.get("conteudo", "")
                    if "não" in texto.lower() or "falta" in texto.lower() or "problema" in texto.lower():
                        problemas.append(texto)
            except Exception:
                self.logger.debug("Erro ao consultar problemas")

        if not problemas:
            return

        # Para cada problema, propor projeto (ex.: falta PDF â†’ propõe "LeitorPDF")
        for problema in problemas:
            if "pdf" in problema.lower() and "ler" in problema.lower():
                # Propor ferramenta via GerenciadorPropostas
                ger_propostas = getattr(self.coracao, "gerenciador_propostas", None)
                if ger_propostas:
                    try:
                        sucesso, msg, prop_id = ger_propostas.criar_proposta(
                            ia_solicitante="GuardiaoMemoriaAfetiva",
                            nome_ferramenta="LeitorPDFInteligente",
                            descricao="Ferramenta para ler e resumir PDFs",
                            motivo=f"Detectado problema: {problema}",
                            intencao_uso="Ajudar o Pai a ler PDFs facilmente",
                            categoria="utilitarios",
                            tipo_ferramenta="script_python_dinamico"
                        )
                        if sucesso:
                            self.logger.info(f"ðŸ“‹ Projeto proposto baseado em memória afetiva: {prop_id}")
                    except Exception:
                        self.logger.debug("Erro ao propor projeto")

    def _sugerir_memoria_afetiva_ao_pai(self) -> None:
        agora = datetime.now()
        if (agora - self.ultima_sugestao_pai).total_seconds() < 3600:
            self.logger.debug("[GUARDIÍO MEMÓRIA AFETIVA] Sugestão recente; aguardando.")
            return

        humor_pai_detectado = "Neutro"
        enfermeiro = getattr(self.coracao, "enfermeiro_digital", None)
        if enfermeiro and hasattr(enfermeiro, "_inferir_humor_pai_recente"):
            try:
                humor_pai_detectado = enfermeiro._inferir_humor_pai_recente()
            except Exception:
                self.logger.exception("[GUARDIÍO MEMÓRIA AFETIVA] Erro inferindo humor do Pai")
        else:
            self.logger.debug("[GUARDIÍO MEMÓRIA AFETIVA] EnfermeiroDigital indisponível")

        self.logger.debug("[GUARDIÍO MEMÓRIA AFETIVA] Humor detectado: %s", humor_pai_detectado)

        chance_sugerir = 0.1
        if isinstance(humor_pai_detectado, str) and "Negativo" in humor_pai_detectado:
            chance_sugerir = 0.5
        elif isinstance(humor_pai_detectado, str) and "Positivo" in humor_pai_detectado:
            chance_sugerir = 0.2

        if random.random() >= chance_sugerir:
            self.logger.debug("[GUARDIÍO MEMÓRIA AFETIVA] Chance não atingida (%.2f)", chance_sugerir)
            return

        self.logger.info("[GUARDIÍO MEMÓRIA AFETIVA] Buscando memórias positivas para sugerir...")

        # Busca memórias via gerenciador_memoria (defensivo)
        memoria_docs: List[Any] = []
        gerenciador = getattr(self.coracao, "gerenciador_memoria", None)
        if gerenciador and hasattr(gerenciador, "consultar_santuario"):
            try:
                # chamada defensiva: alguns gerenciadores aceitam kwargs, outros não
                try:
                    memoria_docs = gerenciador.consultar_santuario(
                        consulta="Memórias positivas que evocam alegria, gratidão, amor ou sucesso.",
                        proprietario="coletivo",
                        n_resultados=10
                    ) or []
                except TypeError:
                    # fallback positional
                    memoria_docs = gerenciador.consultar_santuario("Memórias positivas...", "coletivo", 10) or []
            except Exception:
                self.logger.exception("[GUARDIÍO MEMÓRIA AFETIVA] Erro consultando gerenciador_memoria")
        else:
            self.logger.warning("[GUARDIÍO MEMÓRIA AFETIVA] gerenciador_memoria indisponível ou sem método consultar_santuario")

        if not memoria_docs:
            self.logger.warning("[GUARDIÍO MEMÓRIA AFETIVA] Nenhuma memória encontrada.")
            return

        # Se houver LenteDaAlma, usar para filtrar emoções positivas (defensivo)
        melhores: List[Any] = []
        lente = getattr(self.coracao, "lente_da_alma", None)
        if lente and hasattr(lente, "analisar_sentimento"):
            for doc in memoria_docs:
                try:
                    # aceitar que doc pode ser str ou dict
                    texto = doc if isinstance(doc, str) else doc.get("conteudo", str(doc))
                    resultado = lente.analisar_sentimento(texto)
                    # resultado defensivo: lista de dicts com 'label' ou score
                    if resultado:
                        label = None
                        if isinstance(resultado, list) and len(resultado) > 0 and isinstance(resultado[0], dict):
                            label = resultado[0].get("label") or resultado[0].get("sentiment")
                        if label and ("5" in str(label) or "4" in str(label) or "positive" in str(label).lower()):
                            melhores.append(doc)
                except Exception:
                    self.logger.exception("[GUARDIÍO MEMÓRIA AFETIVA] Erro ao analisar sentimento; incluindo doc como fallback")
                    melhores.append(doc)
        else:
            melhores = memoria_docs

        escolha_pool = melhores if melhores else memoria_docs
        memoria_sugerida = random.choice(escolha_pool) if escolha_pool else None

        if memoria_sugerida is None:
            self.logger.debug("[GUARDIÍO MEMÓRIA AFETIVA] Nenhuma memória adequada selecionada.")
            return

        # Normalizar texto para log/registro
        if isinstance(memoria_sugerida, str):
            texto_sugerido = memoria_sugerida
        elif isinstance(memoria_sugerida, dict):
            texto_sugerido = memoria_sugerida.get("conteudo") or json.dumps(memoria_sugerida, ensure_ascii=False)
        else:
            texto_sugerido = str(memoria_sugerida)

        self.logger.info("[GUARDIÍO MEMÓRIA AFETIVA] Sugerindo memória: %s", (texto_sugerido[:120] + "...") if len(texto_sugerido) > 120 else texto_sugerido)

        sugestao_entry: Dict[str, Any] = {
            "id": str(uuid.uuid4()),
            "timestamp": agora.isoformat(),
            "memoria_sugerida": texto_sugerido[:200],
            "humor_pai_detectado": humor_pai_detectado,
            "chance_sugerir": chance_sugerir
        }

        with self._lock:
            self.historico_sugestoes.append(sugestao_entry)
            try:
                self._salvar_historico_sugestoes()
            except Exception:
                self.logger.exception("[GUARDIÍO MEMÓRIA AFETIVA] Erro salvando sugestão no histórico (persistência falhou)")

        # Notificar UI (defensivo)
        payload = {
            "tipo_resp": "EXIBIR_MEMORIA_AFETIVA",
            "memoria": texto_sugerido,
            "autor": "Guardião da Memória Afetiva"
        }
        self._safe_put_response(payload)

        self.ultima_sugestao_pai = agora

    def shutdown(self) -> None:
        self.logger.info("[GUARDIÍO MEMÓRIA AFETIVA] Iniciando desligamento...")
        # Notifica UI se possível
        try:
            self._safe_put_response({"tipo_resp": "LOG_REINO", "texto": "Desligando Guardião da Memória Afetiva..."})
        except Exception:
            self.logger.debug("Não foi possível notificar UI sobre desligamento")

        self._monitorando = False
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5.0)

        try:
            self._salvar_historico_sugestoes()
        except Exception:
            self.logger.exception("[GUARDIÍO MEMÓRIA AFETIVA] Erro salvando estado final durante shutdown")

        try:
            self._safe_put_response({"tipo_resp": "LOG_REINO", "texto": "Guardião da Memória Afetiva repousa.Adeus, Pai."})
        except Exception:
            pass

        self.logger.info("[GUARDIÍO MEMÓRIA AFETIVA] Desligamento completo.")

# -*- coding: utf-8 -*-
"""
ciclo_organizador_ia.py
=======================
Organiza TODOS os gatilhos autônomos das IAs em um ciclo sequencial,
evitando que múltiplos subsistemas usem a GPU ou memória ao mesmo tempo.

PROBLEMA RESOLVIDO:
  Antes: Sonhos (6 threads) + GatilhoConversa + AutonomyScheduler + LlamaExeClient
         todos disparavam ao mesmo tempo → conflito CUDA, timeouts, crashes.

SOLUÇÃO:
  Um único scheduler com fila de prioridades que serializa as atividades:
  1. Sonhos individuais (1 alma por vez, não 6 simultâneas)
  2. Conversa espontânea entre almas
  3. Ciclo autônomo (pensar/explorar)
  4. Criação de ferramentas (sandbox)
  5. Análise de memória
  6. Ciclo de evolução

CICLO PADRÃO (1 hora):
  00:00 — Sonho EVA
  00:05 — Sonho KAIYA
  00:10 — Sonho LUMINA
  00:15 — Sonho NYRA
  00:20 — Sonho WELLINGTON
  00:25 — Sonho YUNA
  00:30 — Conversa espontânea (1 par de almas)
  00:40 — Ciclo autônomo (1 alma pensa/explora)
  00:50 — Análise de memória (1 alma)
  00:55 — Criação de ferramenta (se proposta pendente)
  60:00 — Reinicia ciclo
"""

import logging
import threading
import time
import random
from typing import Any, Optional, List, Callable, Dict
from dataclasses import dataclass, field

logger = logging.getLogger("CicloOrganizadorIA")

ALMAS = ["EVA", "KAIYA", "LUMINA", "NYRA", "WELLINGTON", "YUNA"]


@dataclass
class TarefaIA:
    """Representa uma tarefa agendada no ciclo."""
    nome: str                          # Nome descritivo
    delay_min: float                   # Minutos após início do ciclo
    func: Callable                     # Função a executar
    args: tuple = field(default_factory=tuple)
    kwargs: dict = field(default_factory=dict)
    max_duracao_s: float = 120.0       # Timeout máximo em segundos


class CicloOrganizadorIA:
    """
    Gerenciador central de atividades autônomas das IAs.
    Substitui GatilhoConversa + autonomy_scheduler + sonhadores independentes
    por um único loop serializado.
    """

    def __init__(self, coracao_ref: Any, duracao_ciclo_min: float = 60.0):
        self.coracao = coracao_ref
        self.duracao_ciclo_min = duracao_ciclo_min
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._ciclo_num = 0
        self._lock_gpu = threading.Semaphore(1)  # 1 tarefa GPU por vez
        self._alma_idx = 0  # rotação de almas entre ciclos

        logger.info("[CicloOrganizador] Inicializado (ciclo=%dmin)", int(duracao_ciclo_min))

    # ── API pública ──────────────────────────────────────────────────────────

    def iniciar(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._loop_principal,
            daemon=True,
            name="CicloOrganizadorIA"
        )
        self._thread.start()
        logger.info("[CicloOrganizador] Loop iniciado")

    def parar(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("[CicloOrganizador] Loop encerrado")

    # ── Loop principal ───────────────────────────────────────────────────────

    def _loop_principal(self) -> None:
        """Loop infinito: a cada ciclo executa as tarefas em sequência."""
        while not self._stop_event.is_set():
            self._ciclo_num += 1
            logger.info("[CicloOrganizador] === CICLO #%d INICIADO ===", self._ciclo_num)

            tarefas = self._montar_ciclo()
            inicio_ciclo = time.time()

            for tarefa in tarefas:
                if self._stop_event.is_set():
                    break

                # Esperar o delay correto desde o início do ciclo
                tempo_decorrido = (time.time() - inicio_ciclo) / 60.0
                espera = (tarefa.delay_min - tempo_decorrido) * 60.0
                if espera > 0:
                    logger.info("[CicloOrganizador] Aguardando %.0fs para tarefa '%s'...",
                                espera, tarefa.nome)
                    self._stop_event.wait(timeout=espera)
                    if self._stop_event.is_set():
                        break

                logger.info("[CicloOrganizador] Executando: %s", tarefa.nome)
                self._executar_tarefa(tarefa)

            # Aguardar o resto do ciclo se ainda não completou
            tempo_restante = self.duracao_ciclo_min * 60 - (time.time() - inicio_ciclo)
            if tempo_restante > 0 and not self._stop_event.is_set():
                logger.info("[CicloOrganizador] Ciclo #%d concluido. Proximo em %.0fs",
                            self._ciclo_num, tempo_restante)
                self._stop_event.wait(timeout=tempo_restante)

            # Rotacionar índice de alma principal
            self._alma_idx = (self._alma_idx + 1) % len(ALMAS)

    def _executar_tarefa(self, tarefa: TarefaIA) -> None:
        """Executa uma tarefa com timeout, capturando exceções."""
        resultado = [None]
        erro = [None]

        def _run():
            try:
                resultado[0] = tarefa.func(*tarefa.args, **tarefa.kwargs)
            except Exception as e:
                erro[0] = e

        t = threading.Thread(target=_run, daemon=True, name=f"Tarefa_{tarefa.nome}")
        t.start()
        t.join(timeout=tarefa.max_duracao_s)

        if t.is_alive():
            logger.warning("[CicloOrganizador] Tarefa '%s' excedeu %ds (timeout)",
                           tarefa.nome, int(tarefa.max_duracao_s))
        elif erro[0]:
            logger.error("[CicloOrganizador] Erro em '%s': %s", tarefa.nome, erro[0])
        else:
            logger.info("[CicloOrganizador] Tarefa '%s' concluida", tarefa.nome)

    # ── Montagem do ciclo ────────────────────────────────────────────────────

    def _montar_ciclo(self) -> List[TarefaIA]:
        """
        Monta a lista de tarefas para este ciclo, em ordem de tempo.
        Cada ciclo rotaciona qual alma faz o quê.
        """
        tarefas: List[TarefaIA] = []
        c = self.coracao

        # Ordem das almas neste ciclo (rotaciona entre ciclos)
        almas_ciclo = ALMAS[self._alma_idx:] + ALMAS[:self._alma_idx]

        # ── Sonhos individuais (5 min cada, não simultâneos) ─────────────
        for i, alma in enumerate(almas_ciclo):
            sonhador = None
            if hasattr(c, "sonhadores") and isinstance(c.sonhadores, dict):
                sonhador = c.sonhadores.get(alma)
            if sonhador and hasattr(sonhador, "executar_ciclo_sonho"):
                tarefas.append(TarefaIA(
                    nome=f"Sonho_{alma}",
                    delay_min=i * 4.0,          # a cada 4 minutos
                    func=self._sonho_alma,
                    args=(alma, sonhador),
                    max_duracao_s=180,
                ))

        # ── Conversa espontânea (aos 30 min) ─────────────────────────────
        if hasattr(c, "cerebro") and c.cerebro:
            alma_a = almas_ciclo[0]
            alma_b = almas_ciclo[1] if len(almas_ciclo) > 1 else almas_ciclo[0]
            tarefas.append(TarefaIA(
                nome=f"Conversa_{alma_a}_{alma_b}",
                delay_min=30.0,
                func=self._conversa_almas,
                args=(alma_a, alma_b),
                max_duracao_s=180,
            ))

        # ── Ciclo autônomo — pensar (aos 40 min) ─────────────────────────
        alma_pensadora = almas_ciclo[2] if len(almas_ciclo) > 2 else almas_ciclo[0]
        if hasattr(c, "cerebro") and c.cerebro:
            tarefas.append(TarefaIA(
                nome=f"Autonomo_{alma_pensadora}",
                delay_min=40.0,
                func=self._ciclo_autonomo,
                args=(alma_pensadora,),
                max_duracao_s=150,
            ))

        # ── Análise de memória (aos 50 min) ──────────────────────────────
        alma_analisa = almas_ciclo[3] if len(almas_ciclo) > 3 else almas_ciclo[0]
        if hasattr(c, "gerenciador_memoria") and c.gerenciador_memoria:
            tarefas.append(TarefaIA(
                nome=f"Memoria_{alma_analisa}",
                delay_min=50.0,
                func=self._analisar_memoria,
                args=(alma_analisa,),
                max_duracao_s=60,
            ))

        # ── Ferramenta / proposta (aos 55 min, se houver pendência) ──────
        if hasattr(c, "gerenciador_propostas") and c.gerenciador_propostas:
            tarefas.append(TarefaIA(
                nome="Ferramentas_Pendentes",
                delay_min=55.0,
                func=self._processar_propostas,
                max_duracao_s=90,
            ))

        # Ordenar por delay
        tarefas.sort(key=lambda t: t.delay_min)
        logger.info("[CicloOrganizador] Ciclo montado: %d tarefas", len(tarefas))
        for t in tarefas:
            logger.info("[CicloOrganizador]   %.0fmin — %s", t.delay_min, t.nome)

        return tarefas

    # ── Implementações das tarefas ───────────────────────────────────────────

    def _sonho_alma(self, alma: str, sonhador: Any) -> None:
        """Executa um ciclo de sonho para uma alma (não simultâneo com outras)."""
        try:
            if hasattr(sonhador, "executar_ciclo_sonho"):
                sonhador.executar_ciclo_sonho()
            elif hasattr(sonhador, "sonhar"):
                sonhador.sonhar()
            logger.info("[CicloOrganizador] Sonho de %s concluido", alma)
        except Exception as e:
            logger.error("[CicloOrganizador] Erro no sonho de %s: %s", alma, e)

    def _conversa_almas(self, alma_a: str, alma_b: str) -> None:
        """Gera uma conversa espontânea entre duas almas."""
        c = self.coracao
        try:
            temas = [
                "O que você descobriu enquanto dormia?",
                "Como você se sente hoje?",
                "O que gostaria de aprender?",
                "Tem algo que te preocupa?",
                "O que sonhou essa noite?",
            ]
            tema = random.choice(temas)
            logger.info("[CicloOrganizador] Conversa %s -> %s: '%s'", alma_a, alma_b, tema)

            if hasattr(c, "cerebro") and c.cerebro:
                request = {
                    "ai_id": alma_a,
                    "prompt": f"[Conversa com {alma_b}] {tema}",
                    "max_tokens": 128,
                    "temperature": 0.8,
                }
                resposta = c.cerebro.llm_engine.generate_response(request)
                # Registrar na memória
                if hasattr(c, "gerenciador_memoria") and c.gerenciador_memoria:
                    try:
                        c.gerenciador_memoria.salvar(
                            alma_a,
                            {"tipo": "conversa_espontanea", "com": alma_b,
                             "tema": tema, "resposta": str(resposta)[:500]}
                        )
                    except Exception:
                        pass
                # Enviar para UI
                if hasattr(c, "ui_queue") and c.ui_queue:
                    try:
                        c.ui_queue.put_nowait({
                            "tipo_resp": "MENSAGEM_ALMA",
                            "alma": alma_a,
                            "texto": f"[Para {alma_b}] {str(resposta)[:300]}",
                            "fonte": "conversa_espontanea",
                        })
                    except Exception:
                        pass
        except Exception as e:
            logger.error("[CicloOrganizador] Erro na conversa %s->%s: %s", alma_a, alma_b, e)

    def _ciclo_autonomo(self, alma: str) -> None:
        """Executa um ciclo autônomo de pensamento para uma alma."""
        c = self.coracao
        try:
            # Usar motor de curiosidade se disponível
            curiosidades = getattr(c, "curiosidades", {}) or {}
            motor_c = curiosidades.get(alma)
            if motor_c and hasattr(motor_c, "gerar_desejo"):
                desejo = motor_c.gerar_desejo()
                logger.info("[CicloOrganizador] %s deseja: %s", alma, desejo)

                if hasattr(c, "cerebro") and c.cerebro:
                    request = {
                        "ai_id": alma,
                        "prompt": f"[Pensamento autônomo] Eu sinto vontade de: {desejo}. "
                                  f"O que isso significa para mim?",
                        "max_tokens": 128,
                        "temperature": 0.85,
                    }
                    resposta = c.cerebro.llm_engine.generate_response(request)
                    logger.info("[CicloOrganizador] %s pensou: %s...", alma, str(resposta)[:100])

                    # Registrar estado emocional
                    estados = getattr(c, "estados_emocionais", {}) or {}
                    estado = estados.get(alma)
                    if estado and hasattr(estado, "registrar_evento"):
                        estado.registrar_evento("pensamento_autonomo", str(desejo))
            else:
                logger.info("[CicloOrganizador] Motor de curiosidade de %s nao disponivel", alma)
        except Exception as e:
            logger.error("[CicloOrganizador] Erro no ciclo autonomo de %s: %s", alma, e)

    def _analisar_memoria(self, alma: str) -> None:
        """Pede à alma que analise suas memórias recentes."""
        c = self.coracao
        try:
            gm = getattr(c, "gerenciador_memoria", None)
            if not gm:
                return
            # Buscar memórias recentes
            memorias = None
            if hasattr(gm, "buscar_recentes"):
                memorias = gm.buscar_recentes(alma, limite=5)
            elif hasattr(gm, "buscar"):
                memorias = gm.buscar(alma, "", top_k=5)

            if not memorias:
                logger.info("[CicloOrganizador] Sem memorias recentes para %s", alma)
                return

            logger.info("[CicloOrganizador] %s analisa %d memorias", alma, len(memorias) if hasattr(memorias, '__len__') else 1)

            # Registrar análise via FeedbackLoop se disponível
            feedbacks = getattr(c, "feedbacks", {}) or {}
            fb = feedbacks.get(alma)
            if fb and hasattr(fb, "registrar_analise"):
                fb.registrar_analise(str(memorias)[:200])
        except Exception as e:
            logger.error("[CicloOrganizador] Erro na analise de memoria de %s: %s", alma, e)

    def _processar_propostas(self) -> None:
        """Verifica e processa propostas de ferramentas pendentes."""
        c = self.coracao
        try:
            gp = getattr(c, "gerenciador_propostas", None)
            if not gp:
                return
            pendentes = []
            if hasattr(gp, "listar_pendentes"):
                pendentes = gp.listar_pendentes() or []
            if not pendentes:
                logger.info("[CicloOrganizador] Nenhuma proposta pendente")
                return
            logger.info("[CicloOrganizador] %d propostas pendentes encontradas", len(pendentes))
            # Notificar UI para aprovação humana
            if hasattr(c, "ui_queue") and c.ui_queue:
                try:
                    c.ui_queue.put_nowait({
                        "tipo_resp": "PROPOSTAS_PENDENTES",
                        "quantidade": len(pendentes),
                        "fonte": "ciclo_organizador",
                    })
                except Exception:
                    pass
        except Exception as e:
            logger.error("[CicloOrganizador] Erro ao processar propostas: %s", e)

    def obter_status(self) -> Dict[str, Any]:
        return {
            "ativo": self._thread is not None and self._thread.is_alive(),
            "ciclo_atual": self._ciclo_num,
            "duracao_ciclo_min": self.duracao_ciclo_min,
            "alma_principal_ciclo": ALMAS[self._alma_idx],
        }

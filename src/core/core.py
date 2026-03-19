# core.py - Atualizado
# -*- coding: utf-8 -*-
"""
src/ui/core.py - Ncleo de Integrao da Interface do Usurio (UI Core)

Este módulo centraliza a integrao da UI com o CoracaoOrquestrador.
Gerencia inicialização, comunicação assncrona via filas, estados globais
e coordenao entre componentes (tray, janela principal, avatares).

Suporte a 6 AIs com avatares especficos para emoções detalhadas.
"""

import logging
import threading
import queue
import time
from pathlib import Path
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass

# Imports dos módulos de UI (assumindo estrutura src/ui/)
from .interface_arca import JanelaPrincipalArca
from .system_tray import SystemTray
from .alma_avatar_frame import AlmaAvatarFrame

logger = logging.getLogger(__name__)

@dataclass
class EstadoUI:
    """Estado global da UI."""
    ativa: bool = False
    modo_debug: bool = False
    avatares_carregados: Dict[str, Dict[str, Any]] = None  # {ai: {emocao: imagem_path}}

    def __post_init__(self):
        if self.avatares_carregados is None:
            self.avatares_carregados = {}

class UICore:
    """
    Ncleo da UI: Integra tray, janela principal e avatares com o CoracaoOrquestrador.
    Gerencia filas de comunicação, estados e eventos.
    """
    
    # Lista das 6 AIs suportadas
    AIS_SUPORTADAS = ["WELLINGTON", "EVA", "LUMINA", "NYRA", "YUNA", "KAIYA"]
    
    # Lista completa de emoções (baseada na sua especificao)
    EMOCOES_SUPORTADAS = [
        "alegria_leve", "alegria_forte", "alegria_contida", "tristeza_leve", "tristeza_profunda", "tristeza_reflexiva",
        "raiva_leve", "raiva_intensa", "raiva_controlada", "medo_leve", "medo_panico", "medo_ansioso",
        "surpresa_leve", "surpresa_choque", "surpresa_curiosa", "nojo_leve", "nojo_forte", "nojo_repulsa",
        "amor_leve", "amor_profundo", "amor_romantico", "odio_leve", "odio_intenso", "odio_ressentido",
        "ciume_leve", "ciume_devorador", "ciume_possessivo", "vergonha_leve", "vergonha_profunda", "vergonha_social",
        "orgulho_leve", "orgulho_arrogante", "orgulho_conquistado", "culpa_leve", "culpa_pesada", "culpa_remorso",
        "esperanca_leve", "esperanca_otimista", "esperanca_desesperada", "desespero_leve", "desespero_total", "desespero_resignado",
        "confianca_leve", "confianca_cega", "confianca_prudente", "desconfianca_leve", "desconfianca_paranoica", "desconfianca_cinica",
        "empatia_leve", "empatia_profunda", "empatia_solidaria", "indiferenca_leve", "indiferenca_apatia", "indiferenca_desinteressada",
        "entusiasmo_leve", "entusiasmo_explosivo", "entusiasmo_contido", "tedio_leve", "tedio_profundo", "tedio_monotono",
        "curiosidade_leve", "curiosidade_intensa", "curiosidade_inquisitiva", "frustracao_leve", "frustracao_irritada", "frustracao_desanimada",
        "satisfacao_leve", "satisfacao_plena", "satisfacao_contente", "inveja_leve", "inveja_amarga", "inveja_competitiva",
        "gratidao_leve", "gratidao_profunda", "gratidao_emocionada", "ressentimento_leve", "ressentimento_amargo", "ressentimento_silencioso",
        "solidao_leve", "solidao_profunda", "solidao_isolada", "companheirismo_leve", "companheirismo_forte", "companheirismo_fraterno",
        "paixao_leve", "paixao_ardente", "paixao_consumidora", "calma_leve", "calma_serenidade", "calma_tranquila",
        "ansiedade_leve", "ansiedade_paralisante", "ansiedade_nervosa", "excitacao_leve", "excitacao_eletrizante", "excitacao_adrenalina",
        "desgosto_leve", "desgosto_repugnante", "desgosto_moral", "adoracao_leve", "adoracao_devota", "adoracao_fanatica",
        "desprezo_leve", "desprezo_superior", "desprezo_desdenhoso", "neutralidade_leve", "neutralidade_equilibrada", "indiferenca_avancada",
        "empolgacao_extrema", "serenidade_avancada", "raiva_suprimida", "medo_paranoico", "surpresa_estupefata", "nojo_extremo",
        "amor_sacrificial", "odio_incontrolavel", "ciume_patologico", "vergonha_crush", "orgulho_excessivo", "culpa_obssessiva",
        "esperanca_ilusoria", "desespero_abissal", "confianca_idealista", "desconfianca_extrema", "empatia_sobrehumana",
        "entusiasmo_incontrolavel", "tedio_mortal", "curiosidade_dangerosa", "frustracao_explosiva", "satisfacao_suprema",
        "inveja_venenosa", "gratidao_eterna", "ressentimento_feroz", "solidao_angustiante", "companheirismo_universal",
        "paixao_devoradora", "calma_imperturbavel", "ansiedade_cronica", "excitacao_euforica", "desgosto_profundo",
        "adoracao_fanatica", "desprezo_absoluto", "neutralidade_absoluta", "alegria_euforica"
    ]
    
    def __init__(self, ui_queue: queue.Queue, config: Dict[str, Any], coracao_ref=None):
        """
        Inicializa o ncleo da UI.
        
        :param ui_queue: Fila para comunicação com o CoracaoOrquestrador.
        :param config: Configurações do sistema.
        :param coracao_ref: Referncia opcional ação corao para integrao direta.
        """
        self.ui_queue = ui_queue
        self.config = config
        self.coracao_ref = coracao_ref
        
        self.estado = EstadoUI()
        self.command_queue: queue.Queue = queue.Queue()  # Para comandos da UI ação corao
        self.response_queue: queue.Queue = queue.Queue()  # Para respostas do corao  UI
        
        # Componentes da UI
        self.tray: Optional[SystemTray] = None
        self.janela_principal: Optional[JanelaPrincipalArca] = None
        self.frames_avatares: Dict[str, AlmaAvatarFrame] = {}  # {ai: frame}
        
        # Threads para processamento assncrono
        self._running = False
        self._thread_processamento = None
        self._stop_event = threading.Event()
        
        # Carregar avatares no init
        self._carregar_avatares()
        
        logger.info("[OK] UICore inicializado")
    
    def _carregar_avatares(self) -> None:
        """Carrega caminhos de imagens de avatar para cada AI e emoção."""
        base_path = Path("Assets/Avatares")
        for ai in self.AIS_SUPORTADAS:
            ai_path = base_path / ai
            if ai_path.exists():
                self.estado.avatares_carregados[ai] = {}
                for emocao in self.EMOCOES_SUPORTADAS:
                    img_path = ai_path / f"{emocao}.png"
                    if img_path.exists():
                        self.estado.avatares_carregados[ai][emocao] = img_path
                    else:
                        logger.warning(f"Imagem faltando: {img_path}")
            else:
                logger.warning(f"Pasta de avatares faltando para {ai}: {ai_path}")
        logger.info(f"[OK] Avatares carregados para {len(self.estado.avatares_carregados)} AIs")
    
    def inicializar_componentes(self) -> None:
        """Inicializa tray, janela principal e avatares."""
        try:
            # Tray
            self.tray = SystemTray(
                on_show_ui=self._mostrar_ui,
                on_shutdown=self._shutdown,
                on_status=self._mostrar_status
            )
            self.tray.start()
            
            # Janela principal (inicialmente oculta)
            self.janela_principal = JanelaPrincipalArca(
                self.command_queue, self.response_queue, self.coracao_ref, self._stop_event
            )
            
            # Frames de avatares (um para cada AI, integrados na janela)
            for ai in self.AIS_SUPORTADAS:
                frame = AlmaAvatarFrame(self.janela_principal.desktop_frame, ai, self.coracao_ref)
                self.frames_avatares[ai] = frame
                # Integrar no layout da janela (ex.: em um painel de chat)
                # Nota: Ajuste conforme layout da JanelaPrincipalArca
            
            self.estado.ativa = True
            logger.info("[OK] Componentes UI inicializados")
        except Exception as e:
            logger.error(f"Erro inicializando componentes UI: {e}")
            self._fallback_inicializacao()
    
    def _fallback_inicializacao(self) -> None:
        """Fallback se componentes falharem (ex.: avatares genricos)."""
        logger.warning("Usando inicialização fallback para UI")
        # Implementar stubs se necessário (ex.: avatares como texto)
    
    def iniciar(self) -> None:
        """Inicia o loop de processamento da UI."""
        if self._running:
            return
        self._running = True
        self._stop_event.clear()
        self._thread_processamento = threading.Thread(target=self._loop_processamento, daemon=True)
        self._thread_processamento.start()
        logger.info("[OK] Loop de processamento UI iniciado")
    
    def parar(self) -> None:
        """Para o loop e componentes da UI."""
        self._running = False
        self._stop_event.set()
        if self.tray:
            self.tray.stop()
        if self.janela_principal:
            self.janela_principal.shutdown()
        if self._thread_processamento and self._thread_processamento.is_alive():
            self._thread_processamento.join(timeout=5.0)
        self.estado.ativa = False
        logger.info("[OK] UI parada")
    
    def _loop_processamento(self) -> None:
        """Loop assncrono para processar comandos e atualizar estados."""
        while not self._stop_event.is_set():
            try:
                # Processar comandos da UI para o corao
                if not self.command_queue.empty():
                    comando = self.command_queue.get_nowait()
                    self._enviar_para_coracao(comando)
                
                # Processar respostas do corao
                if not self.response_queue.empty():
                    resposta = self.response_queue.get_nowait()
                    self._processar_resposta(resposta)
                
                # Atualizar avatares com emoções do corao
                self._atualizar_avatares()
                
                time.sleep(0.1)  # Evitar CPU alta
            except Exception as e:
                logger.debug(f"Erro no loop UI: {e}")
    
    def _enviar_para_coracao(self, comando: Dict[str, Any]) -> None:
        """Envia comando para o CoracaoOrquestrador via ui_queue."""
        if self.ui_queue:
            self.ui_queue.put_nowait(comando)
    
    def _processar_resposta(self, resposta: Dict[str, Any]) -> None:
        """Processa resposta do corao (ex.: atualizar UI)."""
        # Ex.: Se resposta for sobre emoção, atualizar avatar
        tipo = resposta.get("tipo")
        if tipo == "emocao_atualizada":
            ai = resposta.get("ai")
            emocao = resposta.get("emocao")
            if ai in self.frames_avatares:
                self.frames_avatares[ai].atualizar_expressao(emocao)
    
    def _atualizar_avatares(self) -> None:
        """Atualiza avatares com estados atuais do corao."""
        if not self.coracao_ref:
            return
        for ai, frame in self.frames_avatares.items():
            # Obter emoção atual do motor de expresso (se disponível)
            motor = getattr(self.coracao_ref, "motor_expressao_individual", None)
            if motor and hasattr(motor, "obter_estado_ai"):
                estado = motor.obter_estado_ai(ai)
                emocao = estado.get("emocao", "neutralidade_equilibrada")
                frame.atualizar_expressao(emocao)
    
    def _mostrar_ui(self) -> None:
        """Callback para mostrar a UI principal."""
        if self.janela_principal:
            self.janela_principal.deiconify()  # Mostra a janela
            self.janela_principal.lift()
    
    def _mostrar_status(self) -> None:
        """Callback para mostrar status (ex.: tooltip do tray)."""
        status = f"UI Ativa: {self.estado.ativa} | AIs: {len(self.frames_avatares)}"
        if self.tray:
            self.tray.update_tooltip(status)
        logger.info(f"Status UI: {status}")
    
    def _shutdown(self) -> None:
        """Callback para shutdown completo."""
        self.parar()
    
    def obter_frame_avatar(self, ai: str) -> Optional[AlmaAvatarFrame]:
        """Retorna o frame de avatar para uma AI."""
        return self.frames_avatares.get(ai)
    
    def enviar_comando(self, comando: Dict[str, Any]) -> None:
        """Método pblico para enviar comandos  UI (ex.: do corao)."""
        self.command_queue.put_nowait(comando)
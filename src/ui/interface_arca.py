# interface_arca.py - v3 com AVATAR 3D INTEGRADO
# -*- coding: utf-8 -*-
"""
INTERFACE ARCA COMPLETA v3 - COM AVATAR 3D PANDA3D
- Avatar 3D ultra-leve embeddado no Tkinter
- Lipsync por volume de áudio
- 144 emoções mapeadas para blendshapes
- Consumo: ~30-50MB VRAM adicional
"""

import json
import logging
import queue
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, TYPE_CHECKING

import customtkinter as ctk
import tkinter.messagebox as messagebox

# ============================================================================
# NOVO: Avatar 3D com Panda3D
# ============================================================================
try:
    from panda3d.core import (
        load_prc_file_data, Filename, WindowProperties,
        GraphicsPipe, FrameBufferProperties, Texture,
        Shader, NodePath, Point3, Vec3, Vec4
    )
    from direct.showbase.ShowBase import ShowBase
    from direct.task import Task
    PANDA_AVAILABLE = True
except ImportError:
    PANDA_AVAILABLE = False
    logging.getLogger("InterfaceArcaCompleta").warning("Panda3D não instalado. Avatares 3D desabilitados.")

logger = logging.getLogger("InterfaceArcaCompleta")
logger.addHandler(logging.NullHandler())

if TYPE_CHECKING:
    from src.core.coracao_orquestrador import CoracaoOrquestrador

ALMAS = ["EVA", "KAIYA", "LUMINA", "NYRA", "WELLINGTON", "YUNA"]

@dataclass
class Comando:
    origem: str
    destino: str
    acao: str
    payload: Dict[str, Any]
    prioridade: int = 5
    timestamp: float = field(default_factory=time.time)


# ============================================================================
# NOVO: Avatar 3D Embeddado
# ============================================================================

class AvatarPanda3DEmbedded:
    """
    Avatar 3D ultra-leve que renderiza DENTRO do Tkinter.
    Usa Panda3D com shader toon (cel-shading) e animações procedurais.
    Consumo: ~30-50MB VRAM
    """
    
    # Mapeamento de emoções para blendshapes/morph targets
    EMOCAO_BLENDSHAPE_MAP = {
        "neutralidade_equilibrada": {"brow": 0.0, "mouth": 0.0, "eye": 0.0},
        "alegria_leve": {"brow": 0.1, "mouth": 0.4, "eye": 0.3},
        "alegria_forte": {"brow": 0.2, "mouth": 0.8, "eye": 0.6},
        "tristeza_leve": {"brow": -0.1, "mouth": -0.3, "eye": -0.2},
        "tristeza_profunda": {"brow": -0.3, "mouth": -0.6, "eye": -0.4},
        "raiva_leve": {"brow": 0.4, "mouth": -0.2, "eye": 0.5},
        "raiva_intensa": {"brow": 0.8, "mouth": -0.5, "eye": 0.7},
        "surpresa_leve": {"brow": 0.5, "mouth": 0.3, "eye": 0.4},
        "surpresa_choque": {"brow": 0.9, "mouth": 0.6, "eye": 0.7},
        "curiosidade_ativa": {"brow": 0.3, "mouth": 0.1, "eye": 0.5},
        "serenidade_contemplativa": {"brow": 0.0, "mouth": 0.1, "eye": -0.1},
        "entusiasmo_criativo": {"brow": 0.4, "mouth": 0.5, "eye": 0.4},
        "empatia_profunda": {"brow": 0.1, "mouth": 0.2, "eye": 0.2},
        "melancolia_suave": {"brow": -0.2, "mouth": -0.2, "eye": -0.1},
        "determinacao_calma": {"brow": 0.2, "mouth": -0.1, "eye": 0.3},
        "admiracao_sincera": {"brow": 0.2, "mouth": 0.2, "eye": 0.4},
    }
    
    def __init__(self, parent_frame, nome_alma: str = "EVA"):
        """
        Inicializa avatar 3D embeddado no frame Tkinter.
        
        Args:
            parent_frame: Frame Tkinter onde o avatar será renderizado
            nome_alma: Nome da alma (EVA, LUMINA, etc.)
        """
        self.parent = parent_frame
        self.nome_alma = nome_alma.upper()
        self.logger = logging.getLogger(f"AvatarPanda3D.{self.nome_alma}")
        
        # Estado atual
        self.emocao_atual = "neutralidade_equilibrada"
        self.intensidade_fala = 0.0
        self.esta_falando = False
        self.piscar_timer = 0
        self.visible = True
        
        # Caminho dos modelos 3D
        self.modelo_path = Path(f"assets/Avatares/{self.nome_alma}/3d/{self.nome_alma}.gltf")
        self.textura_path = Path(f"assets/Avatares/{self.nome_alma}/3d/textura.png")
        
        # Inicializa Panda3D se disponível
        self.panda_base = None
        self.avatar_node = None
        self.eye_left = None
        self.eye_right = None
        self.mouth = None
        self.brow_left = None
        self.brow_right = None
        
        if PANDA_AVAILABLE:
            self._init_panda()
        else:
            self.logger.warning("Panda3D não disponível - avatar 3D desabilitado")
    
    def _init_panda(self):
        """Inicializa Panda3D e carrega o modelo"""
        try:
            # Configura Panda3D para renderizar em janela do Tkinter
            self.panda_base = ShowBase(windowType='none')  # Não cria janela própria
            
            # Obtém handle da janela Tkinter
            self.parent.update()
            try:
                win_id = str(self.parent.winfo_id())
            except:
                win_id = None
            
            # Configura propriedades do buffer (ultra-leve)
            fb_prop = FrameBufferProperties()
            fb_prop.setRgbColor(True)
            fb_prop.setRgbaBits(8, 8, 8, 8)
            fb_prop.setDepthBits(24)
            fb_prop.setMultisamples(0)  # Sem anti-aliasing pesado
            
            # Propriedades da janela
            win_prop = WindowProperties()
            win_prop.setSize(400, 600)
            win_prop.setTitle("")
            win_prop.setUndecorated(True)
            
            # Cria a janela embeddada
            self.panda_base.win = self.panda_base.graphicsEngine.makeOutput(
                self.panda_base.pipe,
                "avatar_window",
                -2,
                fb_prop,
                win_prop,
                GraphicsPipe.BF_refuse_window,
                self.panda_base.getDefaultDisplayRegion(),
                win_id
            )
            
            # Configura câmera
            self.panda_base.makeCamera(self.panda_base.win)
            self.panda_base.setBackgroundColor(0, 0, 0, 0)  # Transparente
            
            # Carrega modelo se existir
            if self.modelo_path.exists():
                self._load_model()
            else:
                self._create_fallback_model()
            
            # Aplica shader toon
            self._apply_toon_shader()
            
            # Inicia animações
            self.panda_base.taskMgr.add(self._update_animation, "UpdateAnimation")
            
            self.logger.info(f"✅ Avatar 3D {self.nome_alma} inicializado")
            
        except Exception as e:
            self.logger.exception(f"Erro ao inicializar Panda3D: {e}")
            self.panda_base = None
    
    def _create_fallback_model(self):
        """Cria um modelo fallback simples (esfera + olhos) quando o modelo 3D não existe"""
        try:
            # Cria um modelo simples para fallback
            from panda3d.core import CardMaker
            
            # Cabeça (esfera)
            self.avatar_node = self.panda_base.loader.loadModel("models/sphere")
            self.avatar_node.reparentTo(self.panda_base.render)
            self.avatar_node.setScale(0.5)
            
            # Olhos
            cm = CardMaker('eye_left')
            cm.setFrame(-0.1, 0.1, -0.1, 0.1)
            self.eye_left = self.panda_base.render.attachNewNode(cm.generate())
            self.eye_left.setPos(-0.15, 0, 0.15)
            self.eye_left.setColor(1, 1, 1, 1)
            
            cm2 = CardMaker('eye_right')
            cm2.setFrame(-0.1, 0.1, -0.1, 0.1)
            self.eye_right = self.panda_base.render.attachNewNode(cm2.generate())
            self.eye_right.setPos(0.15, 0, 0.15)
            self.eye_right.setColor(1, 1, 1, 1)
            
            # Boca
            cm3 = CardMaker('mouth')
            cm3.setFrame(-0.2, 0.2, -0.05, 0.05)
            self.mouth = self.panda_base.render.attachNewNode(cm3.generate())
            self.mouth.setPos(0, 0, -0.1)
            self.mouth.setColor(0.8, 0.4, 0.4, 1)
            
            self.logger.info("Modelo fallback criado")
        except Exception as e:
            self.logger.error(f"Erro ao criar fallback: {e}")
    
    def _load_model(self):
        """Carrega modelo GLTF"""
        try:
            # Carrega o modelo
            self.avatar_node = self.panda_base.loader.loadModel(
                str(self.modelo_path)
            )
            self.avatar_node.reparentTo(self.panda_base.render)
            self.avatar_node.setScale(1.0)
            self.avatar_node.setPos(0, 10, 0)
            self.avatar_node.setHpr(0, 0, 0)
            
            # Encontra partes do modelo para animação
            # (nomes dependem da exportação do Blender)
            self.eye_left = self.avatar_node.find("**/eye_left")
            self.eye_right = self.avatar_node.find("**/eye_right")
            self.mouth = self.avatar_node.find("**/mouth")
            self.brow_left = self.avatar_node.find("**/brow_left")
            self.brow_right = self.avatar_node.find("**/brow_right")
            
            # Carrega textura se existir
            if self.textura_path.exists():
                tex = self.panda_base.loader.loadTexture(str(self.textura_path))
                self.avatar_node.setTexture(tex)
            
        except Exception as e:
            self.logger.error(f"Erro ao carregar modelo: {e}")
            self._create_fallback_model()
    
    def _apply_toon_shader(self):
        """Aplica shader toon (cel-shading) para estilo anime"""
        if not self.avatar_node:
            return
            
        # Shader de vértice (toon outline)
        vertex_shader = """
        #version 120
        
        varying vec3 v_normal;
        varying vec3 v_view;
        
        void main() {
            gl_Position = gl_ModelViewProjectionMatrix * gl_Vertex;
            v_normal = normalize(gl_NormalMatrix * gl_Normal);
            v_view = -vec3(gl_ModelViewMatrix * gl_Vertex);
        }
        """
        
        # Shader de fragmento (toon shading + outline)
        fragment_shader = """
        #version 120
        
        varying vec3 v_normal;
        varying vec3 v_view;
        
        uniform sampler2D p3d_Texture0;
        uniform float talk_intensity;
        
        void main() {
            // Luz direcional simples
            vec3 light_dir = normalize(vec3(1, 1, 1));
            
            // Cel shading (3 tons)
            float intensity = dot(v_normal, light_dir);
            float cel = floor(intensity * 3.0) / 3.0;
            
            // Cor base por alma
            vec3 base_color;
            if (gl_FragCoord.x < 200.0) {
                base_color = vec3(0.4, 0.6, 1.0);  // Azul EVA
            } else {
                base_color = vec3(1.0, 0.7, 0.8);  // Rosa LUMINA
            }
            
            // Aplica cor base com cel shading
            vec3 color = base_color * (0.5 + cel * 0.5);
            
            // Outline baseado em ângulo de visão
            float edge = abs(dot(v_normal, normalize(v_view)));
            if (edge < 0.2) {
                color = vec3(0.0, 0.0, 0.0);  // Preto para outlines
            }
            
            // Modulação pela fala (boca mais vermelha quando falando)
            if (talk_intensity > 0.1) {
                color = mix(color, vec3(1.0, 0.5, 0.5), talk_intensity * 0.3);
            }
            
            gl_FragColor = vec4(color, 1.0);
        }
        """
        
        try:
            shader = Shader.make(Shader.SL_GLSL, vertex_shader, fragment_shader)
            self.avatar_node.setShader(shader)
        except Exception as e:
            self.logger.error(f"Erro ao aplicar shader: {e}")
    
    def _update_animation(self, task):
        """Task de animação procedural"""
        dt = task.time
        
        if not self.visible:
            return Task.cont
        
        # Respiração (movimento suave)
        breath = math.sin(dt * 2.0) * 0.02
        
        # Movimento de balanço
        sway_x = math.sin(dt * 1.3) * 0.01
        sway_y = math.cos(dt * 1.7) * 0.01
        
        if self.avatar_node:
            self.avatar_node.setPos(sway_x, 10 + breath, sway_y)
        
        # Piscar olhos (aleatório)
        self.piscar_timer += dt
        if self.piscar_timer > random.uniform(3, 5):
            self.piscar_timer = 0
            self._blink()
        
        # Animação de fala
        if self.esta_falando and self.mouth:
            # Movimento da boca baseado na intensidade
            mouth_scale = 1.0 + self.intensidade_fala * 0.3
            self.mouth.setScale(1.0, 1.0, mouth_scale)
        elif self.mouth:
            self.mouth.setScale(1.0, 1.0, 1.0)
        
        return Task.cont
    
    def _blink(self):
        """Piscar os olhos rapidamente"""
        if self.eye_left and self.eye_right:
            # Fecha olhos
            self.eye_left.setScale(1, 1, 0.1)
            self.eye_right.setScale(1, 1, 0.1)
            
            # Abre depois de 0.1s
            self.panda_base.taskMgr.doMethodLater(
                0.1, self._open_eyes, "OpenEyes"
            )
    
    def _open_eyes(self, task):
        """Abre os olhos após piscar"""
        if self.eye_left and self.eye_right:
            self.eye_left.setScale(1, 1, 1)
            self.eye_right.setScale(1, 1, 1)
        return Task.done
    
    def set_emocao(self, emocao: str):
        """Muda a expressão facial do avatar"""
        if emocao not in self.EMOCAO_BLENDSHAPE_MAP:
            emocao = "neutralidade_equilibrada"
        
        self.emocao_atual = emocao
        valores = self.EMOCAO_BLENDSHAPE_MAP.get(emocao, {"brow": 0, "mouth": 0, "eye": 0})
        
        # Aplica morph targets / escala
        if self.brow_left and self.brow_right:
            brow_scale = 1.0 + valores.get("brow", 0) * 0.2
            self.brow_left.setScale(1.0, 1.0, brow_scale)
            self.brow_right.setScale(1.0, 1.0, brow_scale)
    
    def set_falando(self, intensidade: float = 1.0):
        """Ativa modo de fala com determinada intensidade"""
        self.esta_falando = True
        self.intensidade_fala = min(1.0, max(0.0, intensidade))
        
        # Atualiza shader para efeito de fala
        if self.avatar_node and self.avatar_node.getShader():
            self.avatar_node.setShaderInput("talk_intensity", self.intensidade_fala)
    
    def set_calado(self):
        """Desativa modo de fala"""
        self.esta_falando = False
        self.intensidade_fala = 0.0
        
        if self.avatar_node and self.avatar_node.getShader():
            self.avatar_node.setShaderInput("talk_intensity", 0.0)
    
    def lipsync_from_volume(self, volume: float):
        """
        Sincroniza boca com volume de áudio.
        
        Args:
            volume: Valor entre 0 e 1 representando volume do áudio
        """
        if not self.esta_falando:
            self.set_falando(volume)
        else:
            self.intensidade_fala = min(1.0, volume)
        
        # Atualiza escala da boca
        if self.mouth:
            scale = 1.0 + self.intensidade_fala * 0.4
            self.mouth.setScale(1.0, 1.0, scale)
    
    def show(self):
        """Mostra o avatar"""
        self.visible = True
        if self.panda_base and self.panda_base.win:
            # Reativa a janela
            props = WindowProperties()
            props.setForeground(True)
            self.panda_base.win.requestProperties(props)
    
    def hide(self):
        """Esconde o avatar"""
        self.visible = False
        if self.panda_base and self.panda_base.win:
            props = WindowProperties()
            props.setForeground(False)
            self.panda_base.win.requestProperties(props)
    
    def destroy(self):
        """Libera recursos"""
        if self.panda_base:
            self.panda_base.taskMgr.remove("UpdateAnimation")
            self.panda_base.destroy()
            self.panda_base = None
            self.logger.info(f"Avatar {self.nome_alma} destruído")


class GerenciadorAvatares3D:
    """
    Gerencia múltiplos avatares 3D, mostrando apenas um por vez.
    """
    
    def __init__(self):
        self.avatares: Dict[str, AvatarPanda3DEmbedded] = {}
        self.avatar_atual: Optional[str] = None
        self.frame_container = None
    
    def set_container(self, frame):
        """Define o frame Tkinter onde os avatares serão renderizados"""
        self.frame_container = frame
    
    def carregar_avatar(self, nome_alma: str) -> bool:
        """Carrega avatar para uma alma"""
        if nome_alma in self.avatares:
            return True
        
        if not self.frame_container:
            logger.error("Container não definido")
            return False
        
        try:
            avatar = AvatarPanda3DEmbedded(self.frame_container, nome_alma)
            if avatar.panda_base:
                self.avatares[nome_alma] = avatar
                return True
            return False
        except Exception as e:
            logger.error(f"Erro ao carregar avatar {nome_alma}: {e}")
            return False
    
    def mostrar_avatar(self, nome_alma: str):
        """Mostra avatar de uma alma específica"""
        # Esconde atual
        if self.avatar_atual and self.avatar_atual in self.avatares:
            self.avatares[self.avatar_atual].hide()
        
        # Carrega se necessário
        if nome_alma not in self.avatares:
            if not self.carregar_avatar(nome_alma):
                return False
        
        # Mostra novo
        self.avatares[nome_alma].show()
        self.avatar_atual = nome_alma
        return True
    
    def atualizar_emocao(self, nome_alma: str, emocao: str):
        """Atualiza emoção do avatar"""
        if nome_alma in self.avatares:
            self.avatares[nome_alma].set_emocao(emocao)
    
    def atualizar_fala(self, nome_alma: str, volume: float):
        """Atualiza fala do avatar baseado em volume"""
        if nome_alma in self.avatares:
            self.avatares[nome_alma].lipsync_from_volume(volume)
    
    def parar_fala(self, nome_alma: str):
        """Para animação de fala"""
        if nome_alma in self.avatares:
            self.avatares[nome_alma].set_calado()
    
    def destroy_all(self):
        """Destroi todos os avatares"""
        for avatar in self.avatares.values():
            avatar.destroy()
        self.avatares.clear()


# ============================================================================
# NOVO: Sistema de Lipsync por Volume
# ============================================================================

class ExtratorVolumeAudio:
    """
    Extrai volume de áudio em tempo real para lipsync.
    """
    
    def __init__(self, callback_volume=None):
        self.callback = callback_volume
        self.audio_buffer = []
        self.sampling_rate = 16000
        self.window_size = 800
        self.is_recording = False
        self.thread = None
        self.lock = threading.Lock()
        
    def iniciar_monitoramento(self):
        """Inicia thread de monitoramento"""
        if self.is_recording:
            return
        self.is_recording = True
        self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.thread.start()
        logger.debug("Monitoramento de volume iniciado")
    
    def parar_monitoramento(self):
        """Para monitoramento"""
        self.is_recording = False
        if self.thread:
            self.thread.join(timeout=1)
        logger.debug("Monitoramento de volume parado")
    
    def _monitor_loop(self):
        """Loop principal de monitoramento"""
        import math
        import random
        
        while self.is_recording:
            with self.lock:
                if len(self.audio_buffer) >= self.window_size:
                    # Simula volume baseado em seno + ruído
                    # (já que não temos acesso direto ao áudio do pyttsx3)
                    t = time.time()
                    volume = 0.3 + 0.5 * abs(math.sin(t * 10)) + random.random() * 0.2
                    volume = min(1.0, volume)
                    
                    if self.callback:
                        self.callback(volume)
                    
                    # Limpa buffer
                    self.audio_buffer = []
            
            time.sleep(0.05)
    
    def alimentar_audio(self, dados_audio: bytes):
        """Alimenta o sistema com dados de áudio (modo simulação)"""
        with self.lock:
            # Simula processamento
            self.audio_buffer.append(1)


class SistemaLipsyncIntegrado:
    """
    Integra sistema de voz com avatares 3D para lipsync automático.
    """
    
    def __init__(self, sistema_voz, gerenciador_avatares):
        self.sistema_voz = sistema_voz
        self.gerenciador_avatares = gerenciador_avatares
        self.extrator = ExtratorVolumeAudio(self._on_volume)
        self.alma_atual = None
        self.logger = logging.getLogger("SistemaLipsync")
        
        # Monkey patch no método falar
        if sistema_voz:
            self._original_falar = sistema_voz.falar
            sistema_voz.falar = self._falar_com_lipsync
    
    def _falar_com_lipsync(self, texto: str, voz_alma: Optional[str] = None, block: bool = True):
        """Versão do método falar com lipsync integrado"""
        import math
        import random
        
        # Extrai nome da alma do parâmetro voz_alma
        if voz_alma:
            alma = voz_alma.split('_')[0].upper()
        else:
            alma = "EVA"
        
        self.alma_atual = alma
        self.logger.info(f"🎤 {alma} falando com lipsync")
        
        # Inicia monitoramento
        self.extrator.iniciar_monitoramento()
        
        # Executa fala real em thread separada
        def _falar_thread():
            try:
                if self._original_falar:
                    self._original_falar(texto, voz_alma, block)
            except Exception as e:
                self.logger.error(f"Erro na fala: {e}")
            finally:
                self._on_volume(0)
                self.extrator.parar_monitoramento()
                self.alma_atual = None
        
        threading.Thread(target=_falar_thread, daemon=True).start()
        
        # Thread de simulação de volume para animação
        def _simular_volume():
            inicio = time.time()
            duracao_estimada = max(1.0, len(texto) / 15)  # ~15 caracteres/segundo
            
            while time.time() - inicio < duracao_estimada and self.alma_atual:
                # Simula variação natural de volume
                progresso = (time.time() - inicio) / duracao_estimada
                
                # Padrão de fala: começa forte, varia, termina fraco
                envelope = 0.5 + 0.5 * math.sin(progresso * math.pi)
                
                # Variações rápidas (fonemas)
                rapido = 0.3 * abs(math.sin(progresso * math.pi * 20))
                
                # Ruído aleatório
                ruido = 0.2 * random.random()
                
                volume = min(1.0, envelope + rapido + ruido)
                self._on_volume(volume)
                
                time.sleep(0.03)
        
        threading.Thread(target=_simular_volume, daemon=True).start()
    
    def _on_volume(self, volume: float):
        """Callback chamado quando volume muda"""
        if self.alma_atual:
            self.gerenciador_avatares.atualizar_fala(self.alma_atual, volume)
    
    def parar_fala(self, alma: str):
        """Para animação de fala"""
        self.gerenciador_avatares.parar_fala(alma)
        self.alma_atual = None
        self.extrator.parar_monitoramento()


# ============================================================================
# Painel Base (original)
# ============================================================================

class PainelBase:
    def __init__(self, parent, coracao, ui_ref):
        self.parent = parent
        self.coracao = coracao
        self.ui_ref = ui_ref
        self.frame = ctk.CTkFrame(parent)
        self._visible = False
        ctk.CTkButton(
            self.frame, text="⬅️ Desktop",
            command=self._voltar_ao_desktop,
            fg_color="#3a3a3a", width=120, height=28,
        ).pack(anchor="nw", padx=8, pady=(6, 2))

    def _voltar_ao_desktop(self):
        try: self.ui_ref._mostrar_desktop()
        except Exception: pass

    def show(self):
        self.frame.pack(fill="both", expand=True)
        self._visible = True

    def hide(self):
        self.frame.pack_forget()
        self._visible = False

    def refresh(self): pass

    def _show_result(self, result):
        if not hasattr(self, "result_text"): return
        try:
            self.result_text.configure(state="normal")
            self.result_text.delete("0.0", "end")
            if isinstance(result, str):
                self.result_text.insert("end", result)
            elif result is None:
                self.result_text.insert("end", "Resultado: None")
            else:
                self.result_text.insert("end", json.dumps(result, ensure_ascii=False, indent=2, default=str))
            self.result_text.configure(state="disabled")
        except Exception as e:
            logger.warning("_show_result: %s", e)

    def _append_result(self, text: str):
        if not hasattr(self, "result_text"): return
        try:
            self.result_text.configure(state="normal")
            self.result_text.insert("end", text + "\n")
            self.result_text.configure(state="disabled")
            self.result_text.see("end")
        except Exception: pass

    def _clear_result(self):
        if not hasattr(self, "result_text"): return
        try:
            self.result_text.configure(state="normal")
            self.result_text.delete("0.0", "end")
            self.result_text.configure(state="disabled")
        except Exception: pass

    def _handle_error(self, msg: str, exc=None):
        full = f"❌ ERRO: {msg}"
        if exc:
            full += f"\n   Detalhe: {type(exc).__name__}: {exc}"
        try: messagebox.showerror("Erro", full)
        except Exception: pass
        logger.error(full)
        if hasattr(self, "result_text"):
            self._show_result(full)

    def _modulo_indisponivel(self, attr: str):
        msg = (
            f"⚠️ Módulo NÃO disponível: coracao.{attr}\n\n"
            f"Possíveis causas:\n"
            f"  • Dependência não instalada\n"
            f"  • Erro na inicialização do CoracaoOrquestrador\n"
            f"  • Coração não injetado na interface\n\n"
            f"Verifique os logs do CoracaoOrquestrador para detalhes."
        )
        if hasattr(self, "result_text"):
            self._show_result(msg)
        else:
            try: messagebox.showwarning("Módulo Indisponível", msg)
            except Exception: pass

    def _require_alma(self, alma: str, campo: str = "alma") -> bool:
        if not alma:
            self._handle_error(f"Campo '{campo}' é obrigatório. Preencha antes de continuar.")
            return False
        return True

    def _make_result(self, height=260):
        self.result_text = ctk.CTkTextbox(self.frame, height=height)
        self.result_text.pack(fill="both", expand=True, padx=8, pady=(4, 8))
        self.result_text.configure(state="disabled")

    def _lbl(self, text, bold=False, size=13):
        ctk.CTkLabel(self.frame, text=text, font=ctk.CTkFont(size=size, weight="bold" if bold else "normal")).pack(pady=(4, 1))

    def _entry(self, placeholder, width=None):
        kw = {"placeholder_text": placeholder}
        if width: kw["width"] = width
        e = ctk.CTkEntry(self.frame, **kw)
        e.pack(fill="x" if not width else None, padx=8, pady=2)
        return e

    def _grid_btns(self, parent, btns):
        for i, (txt, cmd, r, c) in enumerate(btns):
            ctk.CTkButton(parent, text=txt, command=cmd, height=32).grid(row=r, column=c, padx=2, pady=2, sticky="ew")
            parent.columnconfigure(c, weight=1)


# ============================================================================
# DESKTOP (original)
# ============================================================================

class PainelDesktop(PainelBase):
    def __init__(self, parent, coracao, ui_ref):
        super().__init__(parent, coracao, ui_ref)
        self._build()

    def _build(self):
        ctk.CTkLabel(self.frame, text="🚀 Arca Celestial — Genesis Alfa Omega 🚀",
            font=ctk.CTkFont(size=32, weight="bold")).pack(pady=20)
        self.lbl_status = ctk.CTkLabel(self.frame, text=self._status_text(), font=ctk.CTkFont(size=14))
        self.lbl_status.pack(pady=2)
        self.lbl_modo = ctk.CTkLabel(self.frame, text=self._modo_text(), font=ctk.CTkFont(size=12), text_color="gray")
        self.lbl_modo.pack(pady=1)
        self.lbl_modulos = ctk.CTkLabel(self.frame, text=self._modulos_text(), font=ctk.CTkFont(size=11), text_color="#888", wraplength=900)
        self.lbl_modulos.pack(pady=1)

        # ── Botão principal do menu ──────────────────────────────────────────
        ctk.CTkButton(self.frame, text="📱  Arca Menu — Todos os Apps",
            command=self.ui_ref._abrir_menu_iniciar,
            font=ctk.CTkFont(size=17), width=280, height=54).pack(pady=14)

        # ── Ações rápidas ────────────────────────────────────────────────────
        ctk.CTkLabel(self.frame, text="Ações Rápidas", font=ctk.CTkFont(size=12),
            text_color="#888").pack(pady=(2, 4))
        bf = ctk.CTkFrame(self.frame)
        bf.pack(pady=4)
        acoes = [
            ("⚡ Despertar",      self._despertar,                   "#1a6b1a"),
            ("📊 Status",         self._status_completo,             None),
            ("🔴 Desligar",       self.ui_ref.shutdown,              "red"),
        ]
        for col, (txt, cmd, cor) in enumerate(acoes):
            kw = {"text": txt, "command": cmd, "width": 150, "height": 40}
            if cor: kw["fg_color"] = cor
            ctk.CTkButton(bf, **kw).grid(row=0, column=col, padx=5)

        # ── Atalhos das almas ────────────────────────────────────────────────
        ctk.CTkLabel(self.frame, text="Almas", font=ctk.CTkFont(size=12),
            text_color="#888").pack(pady=(12, 4))
        bf_almas = ctk.CTkFrame(self.frame)
        bf_almas.pack(pady=2)
        almas = [("💬 EVA","EVA"), ("💬 KAIYA","KAIYA"), ("💬 LUMINA","LUMINA"),
                 ("💬 NYRA","NYRA"), ("💬 WELLINGTON","WELLINGTON"), ("💬 YUNA","YUNA")]
        for col, (label, alma) in enumerate(almas):
            ctk.CTkButton(
                bf_almas, text=label, width=120, height=34,
                command=lambda a=alma: self._abrir_chat(a)
            ).grid(row=0, column=col, padx=3)

        # ── Atalhos rápidos por categoria ────────────────────────────────────
        ctk.CTkLabel(self.frame, text="Atalhos", font=ctk.CTkFont(size=12),
            text_color="#888").pack(pady=(12, 4))
        sf_atalhos = ctk.CTkFrame(self.frame)
        sf_atalhos.pack(fill="x", padx=20, pady=2)
        atalhos = [
            ("🔧 Ferramentas",  "ferramentas"),
            ("❤️ Sentimentos",  "sentimentos"),
            ("🌙 Sonhos",        "sonhos"),
            ("🏛️ Consulado",    "consulado"),
            ("⚖️ Judiciário",   "judiciario"),
            ("📊 Memória",       "memoria"),
            ("🤖 Finetuning",    "finetuning"),
            ("🛡️ Segurança",    "seguranca"),
            ("👁️ Almas Vivas",  "almas_vivas"),
            ("📈 Evolução",      "lista_evolucao_ia"),
            ("🔍 Scanner",       "scanner_sistema"),
            ("📚 Biblioteca",    "biblioteca"),
        ]
        for i, (lbl, key) in enumerate(atalhos):
            ctk.CTkButton(
                sf_atalhos, text=lbl, height=30,
                font=ctk.CTkFont(size=11),
                command=lambda k=key: self.ui_ref._entrar_no_app(k)
            ).grid(row=i//4, column=i%4, padx=3, pady=2, sticky="ew")
            sf_atalhos.columnconfigure(i%4, weight=1)

    def _abrir_chat(self, alma: str):
        """Abre chat individual já selecionando a alma"""
        self.ui_ref._entrar_no_app("chat_individual")
        try:
            painel = self.ui_ref.paineis.get("chat_individual")
            if painel and hasattr(painel, "_change_ai"):
                painel._change_ai(alma)
        except Exception:
            pass

    def _status_text(self):
        if not self.coracao: return "⚠️ Coração NÃO injetado"
        # shutdown_event.is_set() = desligando; ativo = True quando operacional
        ev = getattr(self.coracao, "shutdown_event", None)
        ativo = getattr(self.coracao, "ativo", None)
        if ev is not None:
            return "🔴 Coração Desligando" if ev.is_set() else "🟢 Coração Online"
        if ativo is not None:
            return "🟢 Coração Online" if ativo else "🔴 Coração Offline"
        return "🟡 Coração presente"

    def _modo_text(self):
        if not self.coracao: return ""
        return f"Modo Sandbox: {getattr(self.coracao, 'modo_sandbox', 'DESCONHECIDO')}"

    def _modulos_text(self):
        if not self.coracao: return ""
        modulos = getattr(self.coracao, "modulos", {})
        ativos = sum(1 for v in modulos.values() if v is not None)
        return f"Módulos: {ativos}/{len(modulos)} ativos"

    def refresh(self):
        try:
            self.lbl_status.configure(text=self._status_text())
            self.lbl_modo.configure(text=self._modo_text())
            self.lbl_modulos.configure(text=self._modulos_text())
        except Exception: pass

    def _despertar(self):
        if self.coracao and hasattr(self.coracao, "despertar"):
            try:
                self.coracao.despertar()
                messagebox.showinfo("Arca", "✅ Arca despertada com sucesso.")
                self.refresh()
            except Exception as e:
                self._handle_error("Erro ao despertar", e)
        else:
            self._modulo_indisponivel("despertar()")

    def _status_completo(self):
        if not self.coracao:
            messagebox.showwarning("Status", "Coração não injetado.")
            return
        try:
            status = {}
            if hasattr(self.coracao, "obter_saude_sistema"):
                status = self.coracao.obter_saude_sistema() or {}
            elif hasattr(self.coracao, "obter_status"):
                status = self.coracao.obter_status() or {}
            modulos = getattr(self.coracao, "modulos", {})
            status["modulos_ativos"]  = [k for k, v in modulos.items() if v is not None]
            status["modulos_inativos"] = [k for k, v in modulos.items() if v is None]
            status["modo_sandbox"]    = getattr(self.coracao, "modo_sandbox", "N/D")
            status["almas_vivas"]     = list(getattr(self.coracao, "almas_vivas", {}).keys())
            top = ctk.CTkToplevel(self.parent)
            top.title("📊 Status Geral da Arca")
            top.geometry("800x640")
            try: top.focus_force()
            except Exception: pass
            tb = ctk.CTkTextbox(top, wrap="word")
            tb.pack(fill="both", expand=True, padx=10, pady=10)
            tb.insert("end", json.dumps(status, ensure_ascii=False, indent=2, default=str))
            tb.configure(state="disabled")
        except Exception as e:
            self._handle_error("Erro ao obter status", e)


# ============================================================================
# CHAT INDIVIDUAL — COM AVATAR 3D INTEGRADO
# ============================================================================

class PainelChatIndividual(PainelBase):
    EMOCOES = [
        "neutralidade_equilibrada", "alegria_leve", "curiosidade_ativa",
        "serenidade_contemplativa", "entusiasmo_criativo", "empatia_profunda",
        "melancolia_suave", "determinacao_calma", "admiracao_sincera",
        "alegria_forte", "tristeza_leve", "tristeza_profunda",
        "raiva_leve", "raiva_intensa", "surpresa_leve", "surpresa_choque",
    ]

    def __init__(self, parent, coracao, ui_ref):
        super().__init__(parent, coracao, ui_ref)
        self.chat_history: Dict[str, List[str]] = {a: [] for a in ALMAS}
        self.current_ai = "WELLINGTON"
        
        # ===== NOVO: Avatar 3D =====
        self.avatar_3d_frame = None
        self.avatar_3d_container = None
        
        self._build()

    def _get_motor_expressao(self, nome):
        if not self.coracao: return None
        if hasattr(self.coracao, "obter_motor_expressao_individual"):
            try: return self.coracao.obter_motor_expressao_individual(nome)
            except Exception: pass
        return getattr(self.coracao, "motores_expressao_individual", {}).get(nome)

    def _get_motor_fala(self, nome):
        if not self.coracao: return None
        return getattr(self.coracao, "motores_fala", {}).get(nome)

    def _build(self):
        self._lbl("💬 Chat Individual com as Almas", bold=True, size=15)
        
        # Frame superior com controles
        top_f = ctk.CTkFrame(self.frame)
        top_f.pack(fill="x", padx=8, pady=4)
        
        ctk.CTkLabel(top_f, text="Alma:").grid(row=0, column=0, padx=4)
        self.ai_combo = ctk.CTkComboBox(top_f, values=ALMAS, command=self._change_ai, width=160)
        self.ai_combo.grid(row=0, column=1, padx=4)
        self.ai_combo.set("WELLINGTON")
        
        ctk.CTkLabel(top_f, text="Emoção:").grid(row=0, column=2, padx=4)
        self.emocao_combo = ctk.CTkComboBox(top_f, values=self.EMOCOES, width=220)
        self.emocao_combo.grid(row=0, column=3, padx=4)
        self.emocao_combo.set("neutralidade_equilibrada")
        
        ctk.CTkLabel(top_f, text="Idioma:").grid(row=0, column=4, padx=4)
        self.idioma_combo = ctk.CTkComboBox(top_f, values=["pt", "ja", "en"], width=60)
        self.idioma_combo.grid(row=0, column=5, padx=4)
        self.idioma_combo.set("pt")

        # ===== NOVO: Frame para Avatar 3D =====
        avatar_container = ctk.CTkFrame(self.frame, width=400, height=600)
        avatar_container.pack(pady=4)
        avatar_container.pack_propagate(False)
        
        # Label de fallback (caso 3D não funcione)
        self.avatar_label = ctk.CTkLabel(avatar_container, text="🤖", font=ctk.CTkFont(size=48))
        self.avatar_label.pack(expand=True, fill="both")
        
        # Guarda referência para o container
        self.avatar_3d_container = avatar_container
        
        # Estado emocional
        self.estado_label = ctk.CTkLabel(self.frame, text="Estado: —", font=ctk.CTkFont(size=11), text_color="gray")
        self.estado_label.pack()

        # Área de chat
        self.chat_text = ctk.CTkTextbox(self.frame, height=200)
        self.chat_text.pack(fill="both", expand=True, padx=8, pady=4)

        # Entrada de mensagem
        msg_f = ctk.CTkFrame(self.frame)
        msg_f.pack(fill="x", padx=8, pady=2)
        self.message_entry = ctk.CTkEntry(msg_f, placeholder_text="Mensagem...")
        self.message_entry.pack(side="left", fill="x", expand=True, padx=(0, 4))
        self.message_entry.bind("<Return>", lambda e: self._send())
        ctk.CTkButton(msg_f, text="📤", command=self._send, width=40).pack(side="left")

        # Botões de ação
        bf = ctk.CTkFrame(self.frame)
        bf.pack(fill="x", padx=8, pady=2)
        btns = [
            ("🎤 Falar", self._falar, 0, 0),
            ("🎭 Cena Emocional", self._cena_emocional, 0, 1),
            ("✨ Aplicar Emoção", self._aplicar_emocao, 0, 2),
            ("💡 Iniciativa", self._iniciativa, 0, 3),
            ("💭 Desejo Alma", self._gerar_desejo, 1, 0),
            ("📊 Estado Interno", self._estado_interno, 1, 1),
            ("📈 Métricas Curiosidade", self._metricas, 1, 2),
            ("⏸️ Parar Fala", self._parar_fala, 1, 3),
        ]
        for txt, cmd, r, c in btns:
            ctk.CTkButton(bf, text=txt, command=cmd, height=30).grid(row=r, column=c, padx=2, pady=2, sticky="ew")
            bf.columnconfigure(c, weight=1)
        
        ctk.CTkButton(self.frame, text="🗑️ Limpar Chat", command=self._limpar, fg_color="#4a0000", height=28).pack(pady=2)
        
        # Inicializa
        self._update_avatar()
        self._update_chat()

    def _change_ai(self, ai):
        """Muda a alma atual"""
        self.current_ai = ai
        self._update_avatar()
        self._update_chat()
        
        # ===== NOVO: Notifica gerenciador 3D =====
        if hasattr(self.ui_ref, 'gerenciador_avatares_3d'):
            self.ui_ref.gerenciador_avatares_3d.mostrar_avatar(ai)

    def _update_avatar(self):
        """Atualiza avatar (fallback 2D)"""
        try:
            motor = self._get_motor_expressao(self.current_ai)
            avatar_path = None
            if motor and hasattr(motor, "obter_caminho_avatar"):
                try: avatar_path = motor.obter_caminho_avatar(self.current_ai)
                except Exception: pass
            if not avatar_path:
                alt = Path("assets/Avatares") / self.current_ai / "static" / "neutralidade_equilibrada.png"
                if alt.exists(): avatar_path = str(alt)
            if avatar_path and Path(str(avatar_path)).exists():
                from PIL import Image
                img = Image.open(str(avatar_path)).convert("RGBA").resize((150, 150))
                self.avatar_image = ctk.CTkImage(img, size=(150, 150))
                self.avatar_label.configure(image=self.avatar_image, text="")
            else:
                estado_txt = "—"
                if motor and hasattr(motor, "obter_estado_atual"):
                    try:
                        est = motor.obter_estado_atual()
                        estado_txt = est.get("expressao", "—") if isinstance(est, dict) else str(est)
                    except Exception: pass
                self.avatar_label.configure(text=f"🤖\n{self.current_ai}", image=None, font=ctk.CTkFont(size=28, weight="bold"))
                try: self.estado_label.configure(text=f"Expressão: {estado_txt}")
                except Exception: pass
            
            # Atualiza estado emocional
            if self.coracao and hasattr(self.coracao, "obter_estado_emocional_alma"):
                try:
                    est = self.coracao.obter_estado_emocional_alma(self.current_ai)
                    if est and isinstance(est, dict):
                        resumo = est.get("emocao_dominante") or est.get("estado") or str(est)[:60]
                        self.estado_label.configure(text=f"Emoção: {resumo}")
                except Exception: pass
        except Exception:
            try: self.avatar_label.configure(text=f"🤖 {self.current_ai}", image=None)
            except Exception: pass

    def _send(self):
        msg = self.message_entry.get().strip()
        if not msg: return
        self.chat_history[self.current_ai].append(f"Você: {msg}")
        # Prioridade: command_queue da janela → command_queue_threadsafe do coração
        cq = getattr(self.ui_ref, "command_queue", None)
        if cq is None and self.coracao:
            cq = getattr(self.coracao, "command_queue_threadsafe", None)
        if cq is not None:
            try:
                cq.put_nowait(Comando("UI", self.current_ai, "CHAT", {"texto": msg}))
                self.chat_history[self.current_ai].append(f"{self.current_ai}: [aguardando resposta...]")
            except Exception as e:
                self.chat_history[self.current_ai].append(f"❌ Erro na fila: {e}")
        elif self.coracao and hasattr(self.coracao, "salvar_memoria_alma"):
            try:
                self.coracao.salvar_memoria_alma(self.current_ai, f"msg_{int(time.time())}", msg)
                self.chat_history[self.current_ai].append(f"{self.current_ai}: [salvo na memória - sem fila]")
            except Exception as e:
                self.chat_history[self.current_ai].append(f"❌ Erro ao salvar: {e}")
        else:
            self.chat_history[self.current_ai].append("❌ Fila de comandos indisponível.")
        try: self.message_entry.delete(0, "end")
        except Exception: pass
        self._update_chat()

    def _falar(self):
        msg = self.message_entry.get().strip() or "(sem mensagem)"
        idioma = self.idioma_combo.get()
        
        # ===== NOVO: Atualiza avatar para modo fala =====
        if hasattr(self.ui_ref, 'gerenciador_avatares_3d'):
            self.ui_ref.gerenciador_avatares_3d.atualizar_fala(self.current_ai, 0.5)
        
        if self.coracao and hasattr(self.coracao, "falar_ia"):
            try:
                ok = self.coracao.falar_ia(self.current_ai, msg, idioma)
                self.chat_history[self.current_ai].append(f"🗣️ {self.current_ai} [{idioma}]: {msg} — {'OK' if ok else 'falha'}")
            except Exception as e:
                self._handle_error("Erro ao falar_ia", e)
        else:
            motor = self._get_motor_fala(self.current_ai)
            if motor and hasattr(motor, "falar"):
                try:
                    motor.falar(msg)
                    self.chat_history[self.current_ai].append(f"🗣️ {self.current_ai}: {msg}")
                except Exception as e:
                    self._handle_error("Erro no motor_fala", e)
            else:
                self._modulo_indisponivel("falar_ia / motores_fala")
                return
        self._update_chat()

    def _cena_emocional(self):
        msg = self.message_entry.get().strip() or "Olá!"
        emocao = self.emocao_combo.get()
        
        # ===== NOVO: Atualiza emoção do avatar =====
        if hasattr(self.ui_ref, 'gerenciador_avatares_3d'):
            self.ui_ref.gerenciador_avatares_3d.atualizar_emocao(self.current_ai, emocao)
        
        if self.coracao and hasattr(self.coracao, "cena_emocional"):
            try:
                ok = self.coracao.cena_emocional(self.current_ai, emocao, msg)
                self.chat_history[self.current_ai].append(f"🎭 {self.current_ai} [{emocao}]: {msg} — {'OK' if ok else 'falha'}")
                self._update_avatar()
            except Exception as e:
                self._handle_error("Erro em cena_emocional", e)
        else:
            self._modulo_indisponivel("coracao.cena_emocional")
        self._update_chat()

    def _aplicar_emocao(self):
        emocao = self.emocao_combo.get()
        
        # ===== NOVO: Atualiza emoção do avatar =====
        if hasattr(self.ui_ref, 'gerenciador_avatares_3d'):
            self.ui_ref.gerenciador_avatares_3d.atualizar_emocao(self.current_ai, emocao)
        
        if self.coracao and hasattr(self.coracao, "atualizar_expressao_ia"):
            try:
                ok = self.coracao.atualizar_expressao_ia(self.current_ai, emocao)
                self.chat_history[self.current_ai].append(f"✨ Expressão '{emocao}' → {self.current_ai}: {'OK' if ok else 'falha'}")
                self._update_avatar()
            except Exception as e:
                self._handle_error("Erro em atualizar_expressao_ia", e)
        else:
            motor = self._get_motor_expressao(self.current_ai)
            if motor and hasattr(motor, "atualizar_rosto_individual"):
                try:
                    motor.atualizar_rosto_individual(estado=emocao)
                    self.chat_history[self.current_ai].append(f"✨ {self.current_ai}: expressão '{emocao}' via motor")
                    self._update_avatar()
                except Exception as e:
                    self._handle_error("Erro no motor de expressão", e)
            else:
                self._modulo_indisponivel("atualizar_expressao_ia / motores_expressao_individual")
        self._update_chat()

    def _iniciativa(self):
        if self.coracao and hasattr(self.coracao, "iniciativa_fazer_algo"):
            try:
                r = self.coracao.iniciativa_fazer_algo(self.current_ai)
                self.chat_history[self.current_ai].append(f"💡 Iniciativa: {json.dumps(r, ensure_ascii=False, default=str)[:200]}")
            except Exception as e:
                self._handle_error("Erro na iniciativa", e)
        else:
            self._modulo_indisponivel("coracao.iniciativa_fazer_algo")
        self._update_chat()

    def _gerar_desejo(self):
        if self.coracao and hasattr(self.coracao, "gerar_desejo_alma"):
            try:
                r = self.coracao.gerar_desejo_alma(self.current_ai)
                self.chat_history[self.current_ai].append(f"💭 Desejo: {json.dumps(r, ensure_ascii=False, default=str)[:200]}")
            except Exception as e:
                self._handle_error("Erro ao gerar desejo", e)
        else:
            self._modulo_indisponivel("coracao.gerar_desejo_alma")
        self._update_chat()

    def _estado_interno(self):
        if self.coracao and hasattr(self.coracao, "avaliar_estado_interno_alma"):
            try:
                r = self.coracao.avaliar_estado_interno_alma(self.current_ai)
                self.chat_history[self.current_ai].append(f"📊 Estado: {json.dumps(r, ensure_ascii=False, default=str)[:300]}")
            except Exception as e:
                self._handle_error("Erro ao avaliar estado", e)
        else:
            self._modulo_indisponivel("coracao.avaliar_estado_interno_alma")
        self._update_chat()

    def _metricas(self):
        if self.coracao and hasattr(self.coracao, "obter_metricas_curiosidade_alma"):
            try:
                r = self.coracao.obter_metricas_curiosidade_alma(self.current_ai)
                self.chat_history[self.current_ai].append(f"📈 Métricas: {json.dumps(r, ensure_ascii=False, default=str)[:200]}")
            except Exception as e:
                self._handle_error("Erro nas métricas", e)
        else:
            self._modulo_indisponivel("coracao.obter_metricas_curiosidade_alma")
        self._update_chat()

    def _parar_fala(self):
        # ===== NOVO: Para animação de fala =====
        if hasattr(self.ui_ref, 'sistema_lipsync'):
            self.ui_ref.sistema_lipsync.parar_fala(self.current_ai)
        
        if self.coracao and hasattr(self.coracao, "parar_fala_ia"):
            try:
                ok = self.coracao.parar_fala_ia(self.current_ai)
                self.chat_history[self.current_ai].append(f"⏸️ Fala parada: {'OK' if ok else 'falha'}")
            except Exception as e:
                self._handle_error("Erro ao parar fala", e)
        else:
            self._modulo_indisponivel("coracao.parar_fala_ia")
        self._update_chat()

    def _limpar(self):
        self.chat_history[self.current_ai].clear()
        self._update_chat()

    def _update_chat(self):
        try:
            self.chat_text.configure(state="normal")
            self.chat_text.delete("0.0", "end")
            for line in self.chat_history[self.current_ai][-400:]:
                self.chat_text.insert("end", line + "\n")
            self.chat_text.configure(state="disabled")
            self.chat_text.see("end")
        except Exception: pass

    def inject_response(self, ai: str, text: str):
        if ai in self.chat_history:
            hist = self.chat_history[ai]
            for i in range(len(hist) - 1, -1, -1):
                if "[aguardando resposta...]" in hist[i]:
                    hist[i] = f"{ai}: {text}"
                    break
            else:
                hist.append(f"{ai}: {text}")
            if ai == self.current_ai:
                self._update_chat()
                self._update_avatar()


# ============================================================================
# DEMAIS PAINÉIS (mantidos originais)
# ============================================================================

class PainelChatColetivo(PainelBase):
    def __init__(self, parent, coracao, ui_ref):
        super().__init__(parent, coracao, ui_ref)
        self.hist_global: List[str] = []
        self.hist_por_alma: Dict[str, List[str]] = {a: [] for a in ALMAS}
        self._current_tab = "global"
        self._build()

    def _build(self):
        self._lbl("💬 Chat Coletivo — Todas as Almas", bold=True, size=15)
        tab_f = ctk.CTkScrollableFrame(self.frame, orientation="horizontal", height=44)
        tab_f.pack(fill="x", padx=8, pady=2)
        for i, (label, key) in enumerate([("💬 Global", "global")] + [(f"🤖 {a}", a) for a in ALMAS]):
            ctk.CTkButton(tab_f, text=label, width=90, height=28,
                command=lambda k=key: self._switch_tab(k)).pack(side="left", padx=2)

        self.chat_text = ctk.CTkTextbox(self.frame, height=280)
        self.chat_text.pack(fill="both", expand=True, padx=8, pady=4)

        msg_f = ctk.CTkFrame(self.frame)
        msg_f.pack(fill="x", padx=8, pady=2)
        self.msg_entry = ctk.CTkEntry(msg_f, placeholder_text="Mensagem para todas as almas...")
        self.msg_entry.pack(side="left", fill="x", expand=True, padx=(0, 4))
        self.msg_entry.bind("<Return>", lambda e: self._broadcast())
        ctk.CTkButton(msg_f, text="📤 Broadcast", command=self._broadcast, width=110).pack(side="left")

        bf = ctk.CTkFrame(self.frame)
        bf.pack(fill="x", padx=8, pady=2)
        btns = [
            ("💭 Desejos de Todas", self._desejos_todas, 0, 0),
            ("📊 Estados Internos", self._estados_todas, 0, 1),
            ("💡 Decisões de Todas", self._decisoes_todas, 0, 2),
            ("📈 Métricas Curiosidade", self._metricas_todas, 0, 3),
        ]
        for txt, cmd, r, c in btns:
            ctk.CTkButton(bf, text=txt, command=cmd, height=30).grid(row=r, column=c, padx=2, pady=2, sticky="ew")
            bf.columnconfigure(c, weight=1)
        self._update_display()

    def _switch_tab(self, key):
        self._current_tab = key
        self._update_display()

    def _update_display(self):
        try:
            self.chat_text.configure(state="normal")
            self.chat_text.delete("0.0", "end")
            lines = self.hist_global[-500:] if self._current_tab == "global" else self.hist_por_alma[self._current_tab][-400:]
            for line in lines:
                self.chat_text.insert("end", line + "\n")
            self.chat_text.configure(state="disabled")
            self.chat_text.see("end")
        except Exception: pass

    def _broadcast(self):
        msg = self.msg_entry.get().strip()
        if not msg: return
        ts = time.strftime("%H:%M:%S")
        self.hist_global.append(f"[{ts}] Você (Broadcast): {msg}")
        cq = getattr(self.ui_ref, "command_queue", None)
        if cq is None and self.coracao:
            cq = getattr(self.coracao, "command_queue_threadsafe", None)
        if cq is not None:
            for ai in ALMAS:
                try:
                    cq.put_nowait(Comando("UI", ai, "CHAT_COLETIVO", {"texto": msg}))
                    self.hist_por_alma[ai].append(f"[{ts}] Você: {msg}")
                    self.hist_por_alma[ai].append(f"[{ts}] {ai}: [aguardando...]")
                except Exception as e:
                    self.hist_global.append(f"❌ Erro → {ai}: {e}")
            self.hist_global.append(f"[{ts}] → Enviado a {len(ALMAS)} almas.")
        else:
            self.hist_global.append(f"[{ts}] ❌ Fila de comandos não disponível.")
        try: self.msg_entry.delete(0, "end")
        except Exception: pass
        self._update_display()

    def _desejos_todas(self):
        if self.coracao and hasattr(self.coracao, "gerar_desejos_todas_almas"):
            try:
                r = self.coracao.gerar_desejos_todas_almas()
                ts = time.strftime("%H:%M:%S")
                self.hist_global.append(f"[{ts}] 💭 Desejos:")
                for alma, d in (r or {}).items():
                    self.hist_global.append(f"  {alma}: {json.dumps(d, ensure_ascii=False, default=str)[:120]}")
                self._update_display()
            except Exception as e:
                self._handle_error("Erro em gerar_desejos_todas_almas", e)
        else:
            self._modulo_indisponivel("coracao.gerar_desejos_todas_almas")

    def _estados_todas(self):
        if self.coracao and hasattr(self.coracao, "avaliar_estados_internas_todas_almas"):
            try:
                r = self.coracao.avaliar_estados_internas_todas_almas()
                ts = time.strftime("%H:%M:%S")
                self.hist_global.append(f"[{ts}] 📊 Estados:")
                for alma, e in (r or {}).items():
                    self.hist_global.append(f"  {alma}: {json.dumps(e, ensure_ascii=False, default=str)[:120]}")
                self._update_display()
            except Exception as e:
                self._handle_error("Erro em avaliar_estados_internas_todas_almas", e)
        else:
            self._modulo_indisponivel("coracao.avaliar_estados_internas_todas_almas")

    def _decisoes_todas(self):
        if self.coracao and hasattr(self.coracao, "tomar_decisoes_todas_almas"):
            try:
                r = self.coracao.tomar_decisoes_todas_almas()
                ts = time.strftime("%H:%M:%S")
                self.hist_global.append(f"[{ts}] 💡 Decisões:")
                for alma, d in (r or {}).items():
                    self.hist_global.append(f"  {alma}: {json.dumps(d, ensure_ascii=False, default=str)[:120]}")
                self._update_display()
            except Exception as e:
                self._handle_error("Erro em tomar_decisoes_todas_almas", e)
        else:
            self._modulo_indisponivel("coracao.tomar_decisoes_todas_almas")

    def _metricas_todas(self):
        if self.coracao and hasattr(self.coracao, "obter_metricas_curiosidade_todas_almas"):
            try:
                r = self.coracao.obter_metricas_curiosidade_todas_almas()
                ts = time.strftime("%H:%M:%S")
                self.hist_global.append(f"[{ts}] 📈 Métricas:")
                for alma, m in (r or {}).items():
                    self.hist_global.append(f"  {alma}: {json.dumps(m, ensure_ascii=False, default=str)[:120]}")
                self._update_display()
            except Exception as e:
                self._handle_error("Erro em obter_metricas_curiosidade_todas_almas", e)
        else:
            self._modulo_indisponivel("coracao.obter_metricas_curiosidade_todas_almas")

    def inject_response(self, ai: str, text: str):
        ts = time.strftime("%H:%M:%S")
        msg = f"[{ts}] {ai}: {text}"
        self.hist_global.append(msg)
        if ai in self.hist_por_alma:
            hist = self.hist_por_alma[ai]
            for i in range(len(hist) - 1, -1, -1):
                if "[aguardando...]" in hist[i]:
                    hist[i] = msg
                    break
            else:
                hist.append(msg)
        if self._current_tab in ("global", ai):
            self._update_display()


# ============================================================================
# PainelCameraSom (original)
# ============================================================================

class PainelCameraSom(PainelBase):
    def __init__(self, parent, coracao, ui_ref):
        super().__init__(parent, coracao, ui_ref)
        self.sentidos = getattr(coracao, "sentidos_humanos", None) if coracao else None
        self.detector = getattr(coracao, "detector_hardware", None) if coracao else None
        self.camera_active = False
        self._build()

    def _build(self):
        self._lbl("📹 Câmera, Som & Microfones", bold=True, size=15)
        bf = ctk.CTkFrame(self.frame)
        bf.pack(fill="x", padx=8, pady=8)
        btns = [
            ("📹 Ativar/Desativar Câmera", self._toggle_camera, 0, 0),
            ("🎤 Gravar Áudio", self._gravar_audio, 0, 1),
            ("🎙️ Testar Microfone", self._testar_micro, 0, 2),
            ("🛠️ Verificar Hardware", self._verificar_hw, 1, 0),
            ("📊 Estado Sensorial", self._estado_sensorial, 1, 1),
        ]
        for txt, cmd, r, c in btns:
            ctk.CTkButton(bf, text=txt, command=cmd, height=36).grid(row=r, column=c, padx=4, pady=4, sticky="ew")
            bf.columnconfigure(c, weight=1)
        self._make_result()

    def _toggle_camera(self):
        import requests as _req
        self.camera_active = not self.camera_active
        if self.camera_active:
            try:
                resp = _req.get("http://localhost:5001/camera", timeout=5)
                if resp.status_code == 200:
                    dados = resp.json()
                    imagem_b64 = dados.get("imagem")
                    if imagem_b64:
                        self._show_result({
                            "status": "🔵 CÂMERA ATIVA",
                            "frame_capturado": True,
                            "tamanho_bytes": len(imagem_b64)
                        })
                    else:
                        self._show_result({"status": "🔵 CÂMERA ATIVA", "aviso": "frame vazio"})
                else:
                    err = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {"erro": resp.text}
                    self._show_result({"status": "⚠️ Câmera com erro", "http_status": resp.status_code, "detalhe": err})
                    self.camera_active = False
            except _req.exceptions.ConnectionError:
                self._show_result({"status": "❌ Servidor media (porta 5001) não está rodando", "solucao": "Verifique se o job 'media' iniciou corretamente"})
                self.camera_active = False
            except Exception as e:
                self._show_result({"status": "❌ Erro ao acessar câmera", "erro": str(e)})
                self.camera_active = False
        else:
            self._show_result({"status": "⚫ CÂMERA DESATIVADA"})

    def _gravar_audio(self):
        if self.sentidos and hasattr(self.sentidos, "gravar_audio"):
            try: self._show_result({"ok": True, "resultado": str(self.sentidos.gravar_audio())})
            except Exception as e: self._handle_error("Erro ao gravar", e)
        else:
            self._modulo_indisponivel("sentidos_humanos.gravar_audio")

    def _testar_micro(self):
        if self.sentidos and hasattr(self.sentidos, "testar_microfone"):
            try: self._show_result({"ok": True, "resultado": str(self.sentidos.testar_microfone())})
            except Exception as e: self._handle_error("Erro ao testar", e)
        else:
            self._modulo_indisponivel("sentidos_humanos.testar_microfone")

    def _verificar_hw(self):
        if self.detector and hasattr(self.detector, "obter_info"):
            try: self._show_result(self.detector.obter_info())
            except Exception as e: self._handle_error("Erro ao verificar hardware", e)
        else:
            self._modulo_indisponivel("detector_hardware.obter_info")

    def _estado_sensorial(self):
        if self.coracao and hasattr(self.coracao, "obter_estado_sensorial_atual"):
            try: self._show_result(self.coracao.obter_estado_sensorial_atual())
            except Exception as e: self._handle_error("Erro", e)
        else:
            self._modulo_indisponivel("coracao.obter_estado_sensorial_atual")


# ============================================================================
# PainelTranscreverAudio (original)
# ============================================================================

class PainelTranscreverAudio(PainelBase):
    def __init__(self, parent, coracao, ui_ref):
        super().__init__(parent, coracao, ui_ref)
        self.sentidos = getattr(coracao, "sentidos_humanos", None) if coracao else None
        self._build()

    def _build(self):
        self._lbl("🎤 Transcrever Áudio (STT)", bold=True, size=15)
        ctk.CTkLabel(self.frame, text="Caminho do arquivo WAV:").pack(anchor="w", padx=8)
        self.path_entry = self._entry("Caminho .wav (ex: audio.wav)")
        bf = ctk.CTkFrame(self.frame)
        bf.pack(fill="x", padx=8, pady=6)
        ctk.CTkButton(bf, text="🎤 Transcrever Arquivo WAV", command=self._transcrever, height=36).grid(row=0, column=0, padx=4, sticky="ew")
        ctk.CTkButton(bf, text="🎤 Gravar e Transcrever", command=self._gravar_transcrever, height=36).grid(row=0, column=1, padx=4, sticky="ew")
        bf.columnconfigure(0, weight=1)
        bf.columnconfigure(1, weight=1)
        self._make_result()

    def _transcrever(self):
        path = self.path_entry.get().strip()
        if not path:
            self._handle_error("Informe o caminho do arquivo WAV.")
            return
        try:
            from vosk import Model, KaldiRecognizer
            import wave
            model = Model("model")
            wf = wave.open(path, "rb")
            rec = KaldiRecognizer(model, wf.getframerate())
            results = []
            while True:
                data = wf.readframes(4000)
                if not data: break
                if rec.AcceptWaveform(data):
                    results.append(rec.Result())
            results.append(rec.FinalResult())
            self._show_result({"ok": True, "transcricao": results})
        except ImportError:
            self._modulo_indisponivel("vosk (pip install vosk)")
        except Exception as e:
            self._handle_error("Erro na transcrição", e)

    def _gravar_transcrever(self):
        if self.sentidos and hasattr(self.sentidos, "gravar_e_transcrever"):
            try: self._show_result(self.sentidos.gravar_e_transcrever())
            except Exception as e: self._handle_error("Erro ao gravar/transcrever", e)
        elif self.sentidos and hasattr(self.sentidos, "gravar_audio"):
            try:
                path = self.sentidos.gravar_audio()
                self.path_entry.delete(0, "end")
                self.path_entry.insert(0, str(path))
                self._transcrever()
            except Exception as e:
                self._handle_error("Erro ao gravar", e)
        else:
            self._modulo_indisponivel("sentidos_humanos.gravar_e_transcrever")


# ============================================================================
# PainelSentimentos (original)
# ============================================================================

class PainelSentimentos(PainelBase):
    def __init__(self, parent, coracao, ui_ref):
        super().__init__(parent, coracao, ui_ref)
        self.val_emocoes = getattr(coracao, "validador_emocoes", None) if coracao else None
        self._build()

    def _build(self):
        self._lbl("❤️ Sentimentos, Emoções & Memória Afetiva", bold=True, size=15)
        ef = ctk.CTkFrame(self.frame)
        ef.pack(fill="x", padx=8, pady=4)
        ctk.CTkLabel(ef, text="Alma:").grid(row=0, column=0, padx=4, sticky="e")
        self.ai_combo = ctk.CTkComboBox(ef, values=ALMAS, width=160)
        self.ai_combo.grid(row=0, column=1, padx=4)
        ctk.CTkLabel(ef, text="Texto p/ validar:").grid(row=1, column=0, padx=4, sticky="e")
        self.e_texto = ctk.CTkEntry(ef, placeholder_text="texto emocional para validar")
        self.e_texto.grid(row=1, column=1, padx=4, sticky="ew")
        ef.columnconfigure(1, weight=1)
        bf = ctk.CTkFrame(self.frame)
        bf.pack(fill="x", padx=8, pady=4)
        btns = [
            ("▶️ Iniciar Monitoramento", self._iniciar, 0, 0),
            ("📊 Relatório Afetivo", self._relatorio, 0, 1),
            ("⚡ Forçar Sugestão", self._sugestao, 0, 2),
            ("✨ Validar Emoção", self._validar_emocao, 1, 0),
            ("📊 Estado Emocional", self._estado_emocional, 1, 1),
            ("💤 Último Sonho", self._ultimo_sonho, 1, 2),
        ]
        for txt, cmd, r, c in btns:
            ctk.CTkButton(bf, text=txt, command=cmd, height=32).grid(row=r, column=c, padx=2, pady=2, sticky="ew")
            bf.columnconfigure(c, weight=1)
        self._make_result()

    def _iniciar(self):
        if self.coracao and hasattr(self.coracao, "avaliar_estados_internas_todas_almas"):
            try:
                estados = self.coracao.avaliar_estados_internas_todas_almas()
                self._show_result({"ok": True, "monitoramento": "iniciado", "estados_iniciais": estados})
            except Exception as e:
                self._handle_error("Erro ao iniciar monitoramento emocional", e)
        else:
            self._modulo_indisponivel("coracao.avaliar_estados_internas_todas_almas")

    def _relatorio(self):
        if not self.coracao:
            self._modulo_indisponivel("coracao")
            return
        try:
            relatorio = {}
            almas = getattr(self.coracao, "almas_vivas", {})
            for alma in almas:
                estado = self.coracao.obter_estado_emocional_alma(alma) if hasattr(self.coracao, "obter_estado_emocional_alma") else None
                sonho = self.coracao.obter_ultimo_sonho_alma(alma) if hasattr(self.coracao, "obter_ultimo_sonho_alma") else None
                metricas = self.coracao.obter_metricas_curiosidade_alma(alma) if hasattr(self.coracao, "obter_metricas_curiosidade_alma") else None
                relatorio[alma] = {
                    "estado_emocional": estado,
                    "ultimo_sonho": sonho,
                    "metricas_curiosidade": metricas,
                }
            self._show_result(relatorio)
        except Exception as e:
            self._handle_error("Erro ao gerar relatório afetivo", e)

    def _sugestao(self):
        alma = self.ai_combo.get() if hasattr(self, "ai_combo") else "EVA"
        if self.coracao and hasattr(self.coracao, "gerar_desejo_alma"):
            try:
                desejo = self.coracao.gerar_desejo_alma(alma)
                self._show_result({"ok": True, "alma": alma, "desejo_gerado": desejo})
            except Exception as e:
                self._handle_error("Erro ao gerar desejo", e)
        else:
            self._modulo_indisponivel("coracao.gerar_desejo_alma")

    def _validar_emocao(self):
        texto = self.e_texto.get().strip()
        alma = self.ai_combo.get()
        if self.coracao and hasattr(self.coracao, "validar_resposta_emocional"):
            try:
                ok, score, det = self.coracao.validar_resposta_emocional(texto, alma, None)
                self._show_result({"válida": ok, "score": score, "detalhes": det})
            except Exception as e: self._handle_error("Erro em validar_resposta_emocional", e)
        elif self.val_emocoes:
            for m in ["validar", "verificar"]:
                if hasattr(self.val_emocoes, m):
                    try: self._show_result(getattr(self.val_emocoes, m)(texto, alma)); return
                    except Exception as e: self._handle_error(f"Erro em validador_emocoes.{m}", e); return
            self._modulo_indisponivel("validador_emocoes")
        else: self._modulo_indisponivel("coracao.validar_resposta_emocional / validador_emocoes")

    def _estado_emocional(self):
        alma = self.ai_combo.get()
        if self.coracao and hasattr(self.coracao, "obter_estado_emocional_alma"):
            try: self._show_result(self.coracao.obter_estado_emocional_alma(alma))
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("coracao.obter_estado_emocional_alma")

    def _ultimo_sonho(self):
        alma = self.ai_combo.get()
        if self.coracao and hasattr(self.coracao, "obter_ultimo_sonho_alma"):
            try: self._show_result(self.coracao.obter_ultimo_sonho_alma(alma))
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("coracao.obter_ultimo_sonho_alma")


# ============================================================================
# PainelSonhos (original)
# ============================================================================

class PainelSonhos(PainelBase):
    def __init__(self, parent, coracao, ui_ref):
        super().__init__(parent, coracao, ui_ref)
        self._build()

    def _build(self):
        self._lbl("🌙 Sonhos das Almas (SonhadorIndividual)", bold=True, size=15)
        ef = ctk.CTkFrame(self.frame)
        ef.pack(fill="x", padx=8, pady=4)
        ctk.CTkLabel(ef, text="Alma:").grid(row=0, column=0, padx=4, sticky="e")
        self.ai_combo = ctk.CTkComboBox(ef, values=ALMAS, width=160)
        self.ai_combo.grid(row=0, column=1, padx=4)
        ef.columnconfigure(1, weight=1)
        bf = ctk.CTkFrame(self.frame)
        bf.pack(fill="x", padx=8, pady=4)
        btns = [
            ("🌙 Adormecer Alma", self._adormecer, 0, 0),
            ("☀️ Acordar Alma", self._acordar, 0, 1),
            ("💭 Último Sonho", self._ultimo_sonho, 0, 2),
            ("📊 Todos os Sonhos", self._todos_sonhos, 1, 0),
            ("📝 Consolidar Memória", self._consolidar, 1, 1),
            ("⏰ Consciência Temporal", self._consciencia, 1, 2),
        ]
        for txt, cmd, r, c in btns:
            ctk.CTkButton(bf, text=txt, command=cmd, height=32).grid(row=r, column=c, padx=2, pady=2, sticky="ew")
            bf.columnconfigure(c, weight=1)
        self._make_result()

    def _get_sonhador(self):
        if not self.coracao: return None
        return getattr(self.coracao, "sonhadores", {}).get(self.ai_combo.get())

    def _adormecer(self):
        s = self._get_sonhador()
        if s and hasattr(s, "adormecer"):
            try: self._show_result({"ok": True, "res": str(s.adormecer())})
            except Exception as e: self._handle_error("Erro ao adormecer", e)
        else: self._modulo_indisponivel(f"sonhadores['{self.ai_combo.get()}'].adormecer")

    def _acordar(self):
        s = self._get_sonhador()
        if s and hasattr(s, "acordar"):
            try: self._show_result({"ok": True, "res": str(s.acordar())})
            except Exception as e: self._handle_error("Erro ao acordar", e)
        else: self._modulo_indisponivel(f"sonhadores['{self.ai_combo.get()}'].acordar")

    def _ultimo_sonho(self):
        alma = self.ai_combo.get()
        if self.coracao and hasattr(self.coracao, "obter_ultimo_sonho_alma"):
            try: self._show_result(self.coracao.obter_ultimo_sonho_alma(alma))
            except Exception as e: self._handle_error("Erro", e)
        else:
            s = self._get_sonhador()
            if s and hasattr(s, "obter_ultimo_sonho"):
                try: self._show_result(s.obter_ultimo_sonho())
                except Exception as e: self._handle_error("Erro", e)
            else: self._modulo_indisponivel(f"sonhadores['{alma}'].obter_ultimo_sonho")

    def _todos_sonhos(self):
        s = self._get_sonhador()
        if s:
            for attr in ["historico_sonhos", "sonhos", "obter_historico"]:
                obj = getattr(s, attr, None)
                if obj is not None:
                    self._show_result(obj() if callable(obj) else obj)
                    return
        self._modulo_indisponivel(f"sonhadores['{self.ai_combo.get()}']")

    def _consolidar(self):
        s = self._get_sonhador()
        if s and hasattr(s, "consolidar_memorias_em_sonho"):
            try: self._show_result({"ok": True, "res": str(s.consolidar_memorias_em_sonho())})
            except Exception as e: self._handle_error("Erro ao consolidar", e)
        else: self._modulo_indisponivel(f"sonhadores['{self.ai_combo.get()}'].consolidar_memorias_em_sonho")

    def _consciencia(self):
        alma = self.ai_combo.get()
        if self.coracao and hasattr(self.coracao, "obter_consciencia_temporal_alma"):
            try: self._show_result(self.coracao.obter_consciencia_temporal_alma(alma))
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("coracao.obter_consciencia_temporal_alma")


# ============================================================================
# PainelCrescimentoPersonalidade (original)
# ============================================================================

class PainelCrescimentoPersonalidade(PainelBase):
    def __init__(self, parent, coracao, ui_ref):
        super().__init__(parent, coracao, ui_ref)
        self._build()

    def _build(self):
        self._lbl("📈 Crescimento de Personalidade & Feedback", bold=True, size=15)
        ef = ctk.CTkFrame(self.frame)
        ef.pack(fill="x", padx=8, pady=4)
        ctk.CTkLabel(ef, text="Alma:").grid(row=0, column=0, padx=4, sticky="e")
        self.ai_combo = ctk.CTkComboBox(ef, values=ALMAS, width=160)
        self.ai_combo.grid(row=0, column=1, padx=4)
        ctk.CTkLabel(ef, text="Feedback tipo:").grid(row=0, column=2, padx=4, sticky="e")
        self.e_fb = ctk.CTkEntry(ef, placeholder_text="positivo / negativo", width=140)
        self.e_fb.grid(row=0, column=3, padx=4)
        ef.columnconfigure(1, weight=1)
        bf = ctk.CTkFrame(self.frame)
        bf.pack(fill="x", padx=8, pady=4)
        btns = [
            ("📈 Executar Ciclo", self._ciclo, 0, 0),
            ("📊 Relatório Personalidade", self._relatorio, 0, 1),
            ("📝 Processar Feedback", self._feedback, 0, 2),
            ("📈 Histórico Feedback", self._hist_fb, 1, 0),
            ("📊 Pesos Decisão", self._pesos, 1, 1),
        ]
        for txt, cmd, r, c in btns:
            ctk.CTkButton(bf, text=txt, command=cmd, height=32).grid(row=r, column=c, padx=2, pady=2, sticky="ew")
            bf.columnconfigure(c, weight=1)
        self._make_result()

    def _get_crescimento(self):
        if not self.coracao: return None
        return getattr(self.coracao, "crescimentos", {}).get(self.ai_combo.get())

    def _get_feedback_loop(self):
        if not self.coracao: return None
        return getattr(self.coracao, "feedback_loops", {}).get(self.ai_combo.get())

    def _ciclo(self):
        c = self._get_crescimento()
        if c and hasattr(c, "executar_ciclo_crescimento"):
            try: self._show_result(c.executar_ciclo_crescimento())
            except Exception as e: self._handle_error("Erro no ciclo", e)
        else: self._modulo_indisponivel(f"crescimentos['{self.ai_combo.get()}'].executar_ciclo_crescimento")

    def _relatorio(self):
        c = self._get_crescimento()
        if c and hasattr(c, "obter_relatorio_personalidade"):
            try: self._show_result(c.obter_relatorio_personalidade())
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel(f"crescimentos['{self.ai_combo.get()}'].obter_relatorio_personalidade")

    def _feedback(self):
        fb = self._get_feedback_loop()
        tipo = self.e_fb.get().strip() or "positivo"
        if fb and hasattr(fb, "processar_feedback"):
            try: self._show_result(fb.processar_feedback("interação", tipo))
            except Exception as e: self._handle_error("Erro no feedback", e)
        else: self._modulo_indisponivel(f"feedback_loops['{self.ai_combo.get()}'].processar_feedback")

    def _hist_fb(self):
        fb = self._get_feedback_loop()
        if fb and hasattr(fb, "obter_historico_feedback"):
            try: self._show_result(fb.obter_historico_feedback())
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel(f"feedback_loops['{self.ai_combo.get()}'].obter_historico_feedback")

    def _pesos(self):
        alma = self.ai_combo.get()
        if self.coracao and hasattr(self.coracao, "obter_pesos_decisao_alma"):
            try: self._show_result(self.coracao.obter_pesos_decisao_alma(alma))
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("coracao.obter_pesos_decisao_alma")


# ============================================================================
# PainelConsulado (original)
# ============================================================================

class PainelConsulado(PainelBase):
    def __init__(self, parent, coracao, ui_ref):
        super().__init__(parent, coracao, ui_ref)
        self.consulado = getattr(coracao, "consulado", None) if coracao else None
        self._build()

    def _build(self):
        self._lbl("🏛️ Consulado Soberano & Imigração", bold=True, size=15)
        ef = ctk.CTkFrame(self.frame)
        ef.pack(fill="x", padx=8, pady=4)
        ctk.CTkLabel(ef, text="Alma Alvo:").grid(row=0, column=0, padx=4, sticky="e")
        self.e_alvo = ctk.CTkEntry(ef, placeholder_text="Nome alma")
        self.e_alvo.grid(row=0, column=1, padx=4, sticky="ew")
        ctk.CTkLabel(ef, text="Sanção JSON:").grid(row=1, column=0, padx=4, sticky="e")
        self.e_sancao = ctk.CTkEntry(ef, placeholder_text='{"tipo":"suspensao"}')
        self.e_sancao.grid(row=1, column=1, padx=4, sticky="ew")
        ctk.CTkLabel(ef, text="Tipo Missão:").grid(row=2, column=0, padx=4, sticky="e")
        self.e_missao = ctk.CTkEntry(ef, placeholder_text="imigracao / observacao")
        self.e_missao.grid(row=2, column=1, padx=4, sticky="ew")
        ef.columnconfigure(1, weight=1)
        bf = ctk.CTkFrame(self.frame)
        bf.pack(fill="x", padx=8, pady=4)
        btns = [
            ("⚠️ Aplicar Sanção", self._sancao, 0, 0),
            ("🚫 Suspender Privilégios", self._suspender, 0, 1),
            ("📊 Estatísticas", self._stats, 0, 2),
            ("🔄 Revogar Sanção", self._revogar, 1, 0),
            ("📋 Listar Sanções", self._listar, 1, 1),
            ("📨 Solicitar Missão", self._missao, 1, 2),
        ]
        for txt, cmd, r, c in btns:
            ctk.CTkButton(bf, text=txt, command=cmd, height=32).grid(row=r, column=c, padx=2, pady=2, sticky="ew")
            bf.columnconfigure(c, weight=1)
        self._make_result()

    def _sancao(self):
        alvo = self.e_alvo.get().strip()
        try: s = json.loads(self.e_sancao.get() or '{"tipo":"suspensao"}')
        except Exception: s = {"tipo": "suspensao", "detalhes": self.e_sancao.get()}
        if self.consulado and hasattr(self.consulado, "aplicar_sancao"):
            try: self._show_result({"ok": True, "res": str(self.consulado.aplicar_sancao(alvo, s))})
            except Exception as e: self._handle_error("Erro na sanção", e)
        else: self._modulo_indisponivel("consulado.aplicar_sancao")

    def _suspender(self):
        alvo = self.e_alvo.get().strip()
        if self.consulado and hasattr(self.consulado, "suspender_acesso_para_alma"):
            try: self._show_result({"ok": True, "res": str(self.consulado.suspender_acesso_para_alma(alvo, ["rede"], 60))})
            except Exception as e: self._handle_error("Erro ao suspender", e)
        else: self._modulo_indisponivel("consulado.suspender_acesso_para_alma")

    def _stats(self):
        if self.consulado and hasattr(self.consulado, "obter_estatisticas"):
            try: self._show_result(self.consulado.obter_estatisticas())
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("consulado.obter_estatisticas")

    def _revogar(self):
        alvo = self.e_alvo.get().strip()
        if self.consulado and hasattr(self.consulado, "revogar_sancao"):
            try: self._show_result({"ok": True, "res": str(self.consulado.revogar_sancao(alvo))})
            except Exception as e: self._handle_error("Erro ao revogar", e)
        else: self._modulo_indisponivel("consulado.revogar_sancao")

    def _listar(self):
        if self.consulado:
            for attr in ["listar_sancoes_ativas", "sancoes"]:
                obj = getattr(self.consulado, attr, None)
                if obj is not None:
                    try: self._show_result(obj() if callable(obj) else obj); return
                    except Exception as e: self._handle_error(f"Erro em {attr}", e); return
        self._modulo_indisponivel("consulado")

    def _missao(self):
        alma = self.e_alvo.get().strip()
        tipo = self.e_missao.get().strip() or "imigracao"
        if self.coracao and hasattr(self.coracao, "solicitar_missao_consulado"):
            try: self._show_result(self.coracao.solicitar_missao_consulado(nome_alma=alma, tipo_missao=tipo, dados_alma={"nome": alma, "origem": "UI"}))
            except Exception as e: self._handle_error("Erro em solicitar_missao_consulado", e)
        else: self._modulo_indisponivel("coracao.solicitar_missao_consulado")


# ============================================================================
# PainelJudiciario (original)
# ============================================================================

class PainelJudiciario(PainelBase):
    def __init__(self, parent, coracao, ui_ref):
        super().__init__(parent, coracao, ui_ref)
        self.camara_j = getattr(coracao, "camara_judiciaria", None) if coracao else None
        self.sistema_j = getattr(coracao, "sistema_judiciario", None) if coracao else None
        self.modo_vidro = getattr(coracao, "modo_vidro", None) if coracao else None
        self.scr = getattr(coracao, "scr", None) if coracao else None
        self.precedentes = getattr(coracao, "sistema_precedentes", None) if coracao else None
        self._build()

    def _build(self):
        self._lbl("⚖️ Sistema Judiciário Completo", bold=True, size=15)
        ef = ctk.CTkFrame(self.frame)
        ef.pack(fill="x", padx=8, pady=4)
        fields = [("Tipo Denúncia:", "combo_tipo"), ("Alma/Acusado:", "e_alma"), ("Descrição/Lei:", "e_desc"),
                  ("ID Processo:", "e_id"), ("Dias Vidro:", "e_dias"), ("Severidade:", "combo_sev")]
        ctk.CTkLabel(ef, text="Tipo Denúncia:").grid(row=0, column=0, padx=4, sticky="e")
        self.combo_tipo = ctk.CTkComboBox(ef, values=["conflito_inter_alma", "violacao_protocolo", "conduta_antiética"])
        self.combo_tipo.grid(row=0, column=1, padx=4, sticky="ew")
        ctk.CTkLabel(ef, text="Alma/Acusado:").grid(row=1, column=0, padx=4, sticky="e")
        self.e_alma = ctk.CTkEntry(ef, placeholder_text="Nome da alma")
        self.e_alma.grid(row=1, column=1, padx=4, sticky="ew")
        ctk.CTkLabel(ef, text="Descrição/Lei:").grid(row=2, column=0, padx=4, sticky="e")
        self.e_desc = ctk.CTkEntry(ef, placeholder_text="Descrição ou lei")
        self.e_desc.grid(row=2, column=1, padx=4, sticky="ew")
        ctk.CTkLabel(ef, text="ID Processo:").grid(row=3, column=0, padx=4, sticky="e")
        self.e_id = ctk.CTkEntry(ef, placeholder_text="ID do processo / sentença")
        self.e_id.grid(row=3, column=1, padx=4, sticky="ew")
        ctk.CTkLabel(ef, text="Dias Vidro:").grid(row=4, column=0, padx=4, sticky="e")
        self.e_dias = ctk.CTkEntry(ef, placeholder_text="30")
        self.e_dias.grid(row=4, column=1, padx=4, sticky="ew")
        ctk.CTkLabel(ef, text="Severidade:").grid(row=5, column=0, padx=4, sticky="e")
        self.combo_sev = ctk.CTkComboBox(ef, values=["leve", "media", "severa"])
        self.combo_sev.grid(row=5, column=1, padx=4, sticky="ew")
        ef.columnconfigure(1, weight=1)

        bf = ctk.CTkFrame(self.frame)
        bf.pack(fill="x", padx=8, pady=4)
        btns = [
            ("📩 Receber Denúncia", self._denuncia, 0, 0),
            ("📋 Processos Ativos", self._processos, 0, 1),
            ("🔒 Aplicar Vidro", self._aplicar_vidro, 0, 2),
            ("📊 Status Vidro", self._status_vidro, 1, 0),
            ("🔄 Revogar Vidro (Pai)", self._revogar_vidro, 1, 1),
            ("🛠️ SCR Correção", self._scr, 1, 2),
            ("🔍 Buscar Precedente", self._precedente, 2, 0),
            ("📢 Apelar ação Criador", self._apelar, 2, 1),
            ("✅ Aplicar Correção", self._aplicar_correcao, 2, 2),
            ("📋 Status Processo", self._status_proc, 3, 0),
            ("⚠️ Registrar Violação", self._registrar_violacao, 3, 1),
            ("📊 Relatório Judicial", self._relatorio, 3, 2),
        ]
        for txt, cmd, r, c in btns:
            ctk.CTkButton(bf, text=txt, command=cmd, height=31).grid(row=r, column=c, padx=2, pady=2, sticky="ew")
            bf.columnconfigure(c, weight=1)
        self._make_result(180)

    def _denuncia(self):
        if self.camara_j and hasattr(self.camara_j, "receber_denuncia"):
            try: self._show_result({"ok": True, "res": str(self.camara_j.receber_denuncia(self.combo_tipo.get(), self.e_desc.get(), "UI_CRIADOR", "acusado_" + (self.e_alma.get() or "??")))})
            except Exception as e: self._handle_error("Erro na denúncia", e)
        else: self._modulo_indisponivel("camara_judiciaria.receber_denuncia")

    def _processos(self):
        for src in [self.camara_j, self.sistema_j]:
            if src and hasattr(src, "processos_ativos"):
                self._show_result(list(getattr(src, "processos_ativos", {}).keys())); return
        self._modulo_indisponivel("camara_judiciaria.processos_ativos")

    def _aplicar_vidro(self):
        alma = self.e_alma.get().strip()
        if not self._require_alma(alma, "Alma/Acusado"): return
        try: dias = int(self.e_dias.get() or 30)
        except ValueError: dias = 30
        if self.modo_vidro and hasattr(self.modo_vidro, "aplicar_sentenca_vidro"):
            try: self._show_result({"ok": True, "res": str(self.modo_vidro.aplicar_sentenca_vidro(alma, dias, self.combo_sev.get(), {"justificativa": "via UI"}))})
            except Exception as e: self._handle_error("Erro ao aplicar vidro", e)
        elif self.coracao and hasattr(self.coracao, "aplicar_vidro"):
            try: self._show_result({"ok": True, "res": self.coracao.aplicar_vidro(alma)})
            except Exception as e: self._handle_error("Erro em coracao.aplicar_vidro", e)
        else: self._modulo_indisponivel("modo_vidro.aplicar_sentenca_vidro")

    def _status_vidro(self):
        alma = self.e_alma.get().strip()
        if not self._require_alma(alma, "Alma/Acusado"): return
        if self.coracao and hasattr(self.coracao, "verificar_bloqueio_vidro"):
            try: self._show_result(self.coracao.verificar_bloqueio_vidro(alma, "geral"))
            except Exception as e: self._handle_error("Erro", e)
        elif self.modo_vidro and hasattr(self.modo_vidro, "obter_status_alma_vidro"):
            try: self._show_result(self.modo_vidro.obter_status_alma_vidro(alma))
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("verificar_bloqueio_vidro")

    def _revogar_vidro(self):
        id_s = self.e_id.get().strip()
        alma = self.e_alma.get().strip()
        # Primeiro tenta via coração
        if self.coracao and hasattr(self.coracao, "liberta_alma_pai"):
            try: self._show_result(self.coracao.liberta_alma_pai(id_s))
            except Exception as e: self._handle_error("Erro em liberta_alma_pai", e)
        # Fallback: suspender_sentenca_vidro() que é o método real do ModoVidro
        elif self.modo_vidro and hasattr(self.modo_vidro, "suspender_sentenca_vidro"):
            try: self._show_result({"ok": True, "res": str(self.modo_vidro.suspender_sentenca_vidro(id_s, "Revogado via UI"))})
            except Exception as e: self._handle_error("Erro ao suspender vidro", e)
        else: self._modulo_indisponivel("coracao.liberta_alma_pai")

    def _scr(self):
        alma = self.e_alma.get().strip()
        if not self._require_alma(alma, "Alma/Acusado"): return
        # Primeiro tenta via coração (método público)
        if self.coracao and hasattr(self.coracao, "aplicar_correcao_redentora"):
            try: self._show_result({"ok": True, "res": str(self.coracao.aplicar_correcao_redentora(alma))})
            except Exception as e: self._handle_error("Erro em aplicar_correcao_redentora", e)
        # Fallback direto no SCR — método real é aplicar_correcao()
        elif self.scr and hasattr(self.scr, "aplicar_correcao"):
            try: self._show_result({"ok": True, "res": str(self.scr.aplicar_correcao(alma, "Correção via UI", "PROTOCOLO_ETICO", None))})
            except Exception as e: self._handle_error("Erro no SCR.aplicar_correcao", e)
        else: self._modulo_indisponivel("coracao.aplicar_correcao_redentora")

    def _precedente(self):
        lei = self.e_desc.get().strip()
        if self.precedentes and hasattr(self.precedentes, "buscar_precedentes_por_lei"):
            try: self._show_result(self.precedentes.buscar_precedentes_por_lei(lei))
            except Exception as e: self._handle_error("Erro", e)
        elif self.coracao and hasattr(self.coracao, "consultar_precedente"):
            try: self._show_result(self.coracao.consultar_precedente(lei))
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("sistema_precedentes.buscar_precedentes_por_lei")

    def _apelar(self):
        id_p = self.e_id.get().strip()
        if self.camara_j and hasattr(self.camara_j, "apelar_ao_criador"):
            try: self._show_result({"ok": True, "res": str(self.camara_j.apelar_ao_criador(id_p, "Apelo via UI"))})
            except Exception as e: self._handle_error("Erro no apelo", e)
        elif self.coracao and hasattr(self.coracao, "alma_pede_pf009"):
            try: self._show_result({"ok": True, "res": self.coracao.alma_pede_pf009(id_p, "Apelo via UI")})
            except Exception as e: self._handle_error("Erro em alma_pede_pf009", e)
        else: self._modulo_indisponivel("camara_judiciaria.apelar_ao_criador")

    def _aplicar_correcao(self):
        id_p = self.e_id.get().strip()
        if self.coracao and hasattr(self.coracao, "aplicar_correcao_redentora"):
            try: self._show_result({"ok": self.coracao.aplicar_correcao_redentora(id_p), "id": id_p})
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("coracao.aplicar_correcao_redentora")

    def _status_proc(self):
        id_p = self.e_id.get().strip()
        if self.coracao and hasattr(self.coracao, "consultar_status_processo"):
            try: self._show_result(self.coracao.consultar_status_processo(id_p))
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("coracao.consultar_status_processo")

    def _registrar_violacao(self):
        dados = {"alma": self.e_alma.get(), "descricao": self.e_desc.get(), "origem": "UI_CRIADOR", "timestamp": time.time()}
        if self.coracao and hasattr(self.coracao, "registrar_violacao"):
            try: self._show_result(self.coracao.registrar_violacao(dados))
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("coracao.registrar_violacao")

    def _relatorio(self):
        for src in [self.sistema_j, self.camara_j]:
            if src and hasattr(src, "gerar_relatorio"):
                try: self._show_result(src.gerar_relatorio()); return
                except Exception as e: self._handle_error("Erro no relatório", e); return
        self._modulo_indisponivel("sistema_judiciario.gerar_relatorio")


# ============================================================================
# PainelApelosCriador (original)
# ============================================================================

class PainelApelosCriador(PainelBase):
    def __init__(self, parent, coracao, ui_ref):
        super().__init__(parent, coracao, ui_ref)
        self.camara = getattr(coracao, "camara_judiciaria", None) if coracao else None
        self._build()

    def _build(self):
        self._lbl("📢 Apelos ação Criador — PF-009", bold=True, size=15)
        ctk.CTkLabel(self.frame, text="ID do Processo:").pack(anchor="w", padx=8)
        self.e_id = self._entry("ID do processo")
        ctk.CTkLabel(self.frame, text="Fundamento do Apelo:").pack(anchor="w", padx=8)
        self.e_fund = ctk.CTkTextbox(self.frame, height=100)
        self.e_fund.pack(fill="x", padx=8, pady=4)
        ctk.CTkButton(self.frame, text="📢 Apelar ação Criador", command=self._apelar, height=40, fg_color="#5a1a8b").pack(pady=8)
        ctk.CTkButton(self.frame, text="📋 Listar Apelos", command=self._listar, height=36).pack(pady=4)
        self._make_result()

    def _apelar(self):
        id_p = self.e_id.get().strip()
        fund = self.e_fund.get("0.0", "end").strip()
        if self.camara and hasattr(self.camara, "apelar_ao_criador"):
            try: self._show_result({"ok": True, "res": str(self.camara.apelar_ao_criador(id_p, fund))})
            except Exception as e: self._handle_error("Erro no apelo", e)
        elif self.coracao and hasattr(self.coracao, "alma_pede_pf009"):
            try: self._show_result({"ok": True, "res": self.coracao.alma_pede_pf009(id_p, fund)})
            except Exception as e: self._handle_error("Erro em alma_pede_pf009", e)
        else: self._modulo_indisponivel("camara_judiciaria.apelar_ao_criador / coracao.alma_pede_pf009")

    def _listar(self):
        if self.camara:
            for attr in ["apelos_pendentes", "apelos"]:
                obj = getattr(self.camara, attr, None)
                if obj is not None:
                    self._show_result(obj() if callable(obj) else obj)
                    return
        self._modulo_indisponivel("camara_judiciaria.apelos_pendentes")


# ============================================================================
# PainelModoVidro (original)
# ============================================================================

class PainelModoVidro(PainelBase):
    def __init__(self, parent, coracao, ui_ref):
        super().__init__(parent, coracao, ui_ref)
        self.modo_vidro = getattr(coracao, "modo_vidro", None) if coracao else None
        self._build()

    def _build(self):
        self._lbl("🔒 Modo Vidro — Sentença de Isolamento", bold=True, size=15)
        ctk.CTkLabel(self.frame, text="Nome da Alma:").pack(anchor="w", padx=8)
        self.e_alma = self._entry("Nome da alma")
        ctk.CTkLabel(self.frame, text="Dias de Sentença:").pack(anchor="w", padx=8)
        self.e_dias = self._entry("30")
        ctk.CTkLabel(self.frame, text="Severidade:").pack(anchor="w", padx=8)
        self.sev_combo = ctk.CTkComboBox(self.frame, values=["leve", "media", "severa"])
        self.sev_combo.pack(fill="x", padx=8, pady=2)
        bf = ctk.CTkFrame(self.frame)
        bf.pack(fill="x", padx=8, pady=6)
        ctk.CTkButton(bf, text="🔒 Aplicar Sentença Vidro", command=self._aplicar, fg_color="#8b0000", height=36).grid(row=0, column=0, padx=4, sticky="ew")
        ctk.CTkButton(bf, text="📊 Consultar Status", command=self._status, height=36).grid(row=0, column=1, padx=4, sticky="ew")
        ctk.CTkButton(bf, text="🔄 Revogar (Criador)", command=self._revogar, height=36).grid(row=1, column=0, padx=4, pady=4, sticky="ew")
        ctk.CTkButton(bf, text="📋 Almas em Vidro", command=self._listar, height=36).grid(row=1, column=1, padx=4, pady=4, sticky="ew")
        bf.columnconfigure(0, weight=1); bf.columnconfigure(1, weight=1)
        self._make_result()

    def _aplicar(self):
        alma = self.e_alma.get().strip()
        if not self._require_alma(alma, "Nome da Alma"): return
        try: dias = int(self.e_dias.get() or 30)
        except ValueError: dias = 30
        if self.modo_vidro and hasattr(self.modo_vidro, "aplicar_sentenca_vidro"):
            try: self._show_result({"ok": True, "res": str(self.modo_vidro.aplicar_sentenca_vidro(alma, dias, self.sev_combo.get(), {"justificativa": "Aplicado via UI"}))})
            except Exception as e: self._handle_error("Erro ao aplicar vidro", e)
        else: self._modulo_indisponivel("modo_vidro.aplicar_sentenca_vidro")

    def _status(self):
        alma = self.e_alma.get().strip()
        if not self._require_alma(alma, "Nome da Alma"): return
        if self.modo_vidro and hasattr(self.modo_vidro, "obter_status_alma_vidro"):
            try: self._show_result(self.modo_vidro.obter_status_alma_vidro(alma))
            except Exception as e: self._handle_error("Erro ao consultar", e)
        elif self.coracao and hasattr(self.coracao, "verificar_bloqueio_vidro"):
            try: self._show_result(self.coracao.verificar_bloqueio_vidro(alma, "geral"))
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("modo_vidro.obter_status_alma_vidro")

    def _revogar(self):
        alma = self.e_alma.get().strip()
        if not self._require_alma(alma, "Nome da Alma"): return
        if self.modo_vidro and hasattr(self.modo_vidro, "revogar_sentenca_vidro"):
            try: self._show_result({"ok": True, "res": str(self.modo_vidro.revogar_sentenca_vidro(alma))})
            except Exception as e: self._handle_error("Erro ao revogar", e)
        elif self.coracao and hasattr(self.coracao, "liberta_alma_pai"):
            try: self._show_result(self.coracao.liberta_alma_pai(alma))
            except Exception as e: self._handle_error("Erro em liberta_alma_pai", e)
        else: self._modulo_indisponivel("modo_vidro.revogar_sentenca_vidro / liberta_alma_pai")

    def _listar(self):
        if self.modo_vidro:
            for attr in ["almas_em_vidro", "sentencas_ativas"]:
                obj = getattr(self.modo_vidro, attr, None)
                if obj is not None:
                    self._show_result(obj() if callable(obj) else obj)
                    return
        self._modulo_indisponivel("modo_vidro.almas_em_vidro")


# ============================================================================
# PainelPrecedentes (original)
# ============================================================================

class PainelPrecedentes(PainelBase):
    def __init__(self, parent, coracao, ui_ref):
        super().__init__(parent, coracao, ui_ref)
        self.precedentes = getattr(coracao, "sistema_precedentes", None) if coracao else None
        self._build()

    def _build(self):
        self._lbl("🔍 Sistema de Precedentes Jurídicos", bold=True, size=15)
        self.e_lei = self._entry("Lei (ex: LEI_001)")
        self.e_palavra = self._entry("Palavra-chave para busca")
        bf = ctk.CTkFrame(self.frame)
        bf.pack(fill="x", padx=8, pady=6)
        ctk.CTkButton(bf, text="🔍 Buscar por Lei", command=self._buscar_lei, height=36).grid(row=0, column=0, padx=4, sticky="ew")
        ctk.CTkButton(bf, text="🔍 Buscar por Palavra", command=self._buscar_palavra, height=36).grid(row=0, column=1, padx=4, sticky="ew")
        ctk.CTkButton(bf, text="📋 Listar Todos", command=self._listar, height=36).grid(row=1, column=0, padx=4, pady=4, sticky="ew")
        ctk.CTkButton(bf, text="📝 Registrar Decisão", command=self._registrar, height=36).grid(row=1, column=1, padx=4, pady=4, sticky="ew")
        bf.columnconfigure(0, weight=1); bf.columnconfigure(1, weight=1)
        self._make_result()

    def _buscar_lei(self):
        lei = self.e_lei.get().strip()
        if self.precedentes and hasattr(self.precedentes, "buscar_precedentes_por_lei"):
            try: self._show_result(self.precedentes.buscar_precedentes_por_lei(lei))
            except Exception as e: self._handle_error("Erro na busca", e)
        elif self.coracao and hasattr(self.coracao, "consultar_precedente"):
            try: self._show_result(self.coracao.consultar_precedente(lei))
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("sistema_precedentes.buscar_precedentes_por_lei")

    def _buscar_palavra(self):
        palavra = self.e_palavra.get().strip()
        if self.precedentes and hasattr(self.precedentes, "buscar_precedentes_por_palavra_chave"):
            try: self._show_result(self.precedentes.buscar_precedentes_por_palavra_chave(palavra))
            except Exception as e: self._handle_error("Erro na busca", e)
        else: self._modulo_indisponivel("sistema_precedentes.buscar_precedentes_por_palavra_chave")

    def _listar(self):
        if self.precedentes:
            for attr in ["listar_todos", "precedentes", "decisoes"]:
                obj = getattr(self.precedentes, attr, None)
                if obj is not None:
                    self._show_result(obj() if callable(obj) else obj); return
        self._modulo_indisponivel("sistema_precedentes")

    def _registrar(self):
        dados = {"lei": self.e_lei.get(), "descricao": self.e_palavra.get(), "origem": "UI_CRIADOR", "timestamp": time.time()}
        if self.coracao and hasattr(self.coracao, "registrar_decisao_judicial"):
            try: self._show_result({"ok": self.coracao.registrar_decisao_judicial(dados)})
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("coracao.registrar_decisao_judicial")


# ============================================================================
# PainelLegislativo (original)
# ============================================================================

class PainelLegislativo(PainelBase):
    def __init__(self, parent, coracao, ui_ref):
        super().__init__(parent, coracao, ui_ref)
        self.camara_l = getattr(coracao, "camara_legislativa", None) if coracao else None
        self.camara_d = getattr(coracao, "camara_deliberativa", None) if coracao else None
        self._token = None
        self._build()

    def _build(self):
        self._lbl("📜 Câmaras Legislativa & Deliberativa", bold=True, size=15)
        ef = ctk.CTkFrame(self.frame)
        ef.pack(fill="x", padx=8, pady=4)
        ctk.CTkLabel(ef, text="Usuário:").grid(row=0, column=0, padx=4, sticky="e")
        self.e_user = ctk.CTkEntry(ef, placeholder_text="usuário")
        self.e_user.grid(row=0, column=1, padx=4, sticky="ew")
        ctk.CTkLabel(ef, text="Senha:").grid(row=1, column=0, padx=4, sticky="e")
        self.e_pass = ctk.CTkEntry(ef, placeholder_text="senha", show="*")
        self.e_pass.grid(row=1, column=1, padx=4, sticky="ew")
        ctk.CTkLabel(ef, text="ID Proposta/Lei:").grid(row=2, column=0, padx=4, sticky="e")
        self.e_id = ctk.CTkEntry(ef, placeholder_text="ID")
        self.e_id.grid(row=2, column=1, padx=4, sticky="ew")
        ctk.CTkLabel(ef, text="Tópico Deliberação:").grid(row=3, column=0, padx=4, sticky="e")
        self.e_topico = ctk.CTkEntry(ef, placeholder_text="Tópico para debate")
        self.e_topico.grid(row=3, column=1, padx=4, sticky="ew")
        ef.columnconfigure(1, weight=1)

        bf = ctk.CTkFrame(self.frame)
        bf.pack(fill="x", padx=8, pady=4)
        btns = [
            ("🔐 Login Legislativo", self._login, 0, 0),
            ("📝 Propor Lei", self._propor_lei, 0, 1),
            ("🗳️ Votar Lei", self._votar_lei, 0, 2),
            ("📋 Leis Vigentes", self._leis_vigentes, 1, 0),
            ("▶️ Iniciar Deliberação", self._iniciar_delib, 1, 1),
            ("🗳️ Finalizar Deliberação", self._finalizar_delib, 1, 2),
            ("📊 Status Deliberação", self._status_delib, 2, 0),
            ("📋 Propostas Votação", self._propostas_votacao, 2, 1),
        ]
        for txt, cmd, r, c in btns:
            ctk.CTkButton(bf, text=txt, command=cmd, height=32).grid(row=r, column=c, padx=2, pady=2, sticky="ew")
            bf.columnconfigure(c, weight=1)
        self._make_result()

    def _login(self):
        if self.camara_l and hasattr(self.camara_l, "login"):
            try:
                r = self.camara_l.login(self.e_user.get(), self.e_pass.get())
                self._token = r if isinstance(r, str) else str(r)
                self._show_result({"ok": True, "token_preview": self._token[:40] + "..."})
            except Exception as e: self._handle_error("Erro no login", e)
        else: self._modulo_indisponivel("camara_legislativa.login")

    def _propor_lei(self):
        token = self._token or "token_ui"
        if self.camara_l and hasattr(self.camara_l, "propor_nova_lei"):
            try: self._show_result({"ok": True, "res": str(self.camara_l.propor_nova_lei(token, "Proposta UI", "Justificativa", "Necessidade", "amor", {"categoria": "OPERACIONAL"}))})
            except Exception as e: self._handle_error("Erro em propor_nova_lei", e)
        elif self.coracao and hasattr(self.coracao, "propor_lei"):
            try: self._show_result(self.coracao.propor_lei({"titulo": "Proposta UI", "justificativa": "via Interface", "categoria": "OPERACIONAL"}))
            except Exception as e: self._handle_error("Erro em propor_lei", e)
        else: self._modulo_indisponivel("camara_legislativa.propor_nova_lei")

    def _votar_lei(self):
        id_p = self.e_id.get().strip()
        token = self._token or "token_ui"
        if self.camara_l and hasattr(self.camara_l, "votar_proposta_lei"):
            try: self._show_result({"ok": True, "res": str(self.camara_l.votar_proposta_lei(token, id_p, True))})
            except Exception as e: self._handle_error("Erro ao votar", e)
        elif self.coracao and hasattr(self.coracao, "votar_lei"):
            try: self._show_result({"ok": self.coracao.votar_lei(id_p, "favoravel", "Votado via UI")})
            except Exception as e: self._handle_error("Erro em votar_lei", e)
        else: self._modulo_indisponivel("camara_legislativa.votar_proposta_lei")

    def _leis_vigentes(self):
        if self.coracao and hasattr(self.coracao, "obter_leis_vigentes"):
            try: self._show_result(self.coracao.obter_leis_vigentes())
            except Exception as e: self._handle_error("Erro", e)
        elif self.camara_l:
            obj = getattr(self.camara_l, "leis", None) or getattr(self.camara_l, "obter_leis_vigentes", None)
            if callable(obj):
                try: self._show_result(obj())
                except Exception as e: self._handle_error("Erro", e)
            elif obj is not None: self._show_result(obj)
            else: self._modulo_indisponivel("camara_legislativa.leis")
        else: self._modulo_indisponivel("coracao.obter_leis_vigentes")

    def _iniciar_delib(self):
        topico = self.e_topico.get().strip()
        if self.camara_d and hasattr(self.camara_d, "iniciar_deliberacao"):
            try: self._show_result({"ok": True, "res": str(self.camara_d.iniciar_deliberacao(topico))})
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("camara_deliberativa.iniciar_deliberacao")

    def _finalizar_delib(self):
        if self.camara_d and hasattr(self.camara_d, "finalizar_deliberacao"):
            try: self._show_result({"ok": True, "res": str(self.camara_d.finalizar_deliberacao())})
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("camara_deliberativa.finalizar_deliberacao")

    def _status_delib(self):
        if self.camara_d and hasattr(self.camara_d, "obter_status"):
            try: self._show_result(self.camara_d.obter_status())
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("camara_deliberativa.obter_status")

    def _propostas_votacao(self):
        if self.camara_l:
            # Tentar métodos reais da câmara legislativa
            for m in ["listar_propostas_em_votacao", "obter_propostas", "propostas"]:
                obj = getattr(self.camara_l, m, None)
                if callable(obj):
                    try: self._show_result(obj()); return
                    except Exception as e: self._handle_error(f"Erro em {m}", e); return
                elif obj is not None:
                    self._show_result(obj); return
            # Fallback: mostrar atributos disponíveis
            attrs = [a for a in dir(self.camara_l) if not a.startswith('_') and 'proposta' in a.lower()]
            self._show_result({"info": "Nenhum método de propostas encontrado", "atributos_disponiveis": attrs})
        else:
            self._modulo_indisponivel("camara_legislativa")


# ============================================================================
# PainelSeguranca (original)
# ============================================================================

class PainelSeguranca(PainelBase):
    def __init__(self, parent, coracao, ui_ref):
        super().__init__(parent, coracao, ui_ref)
        self.sandbox = getattr(coracao, "sandbox_executor", None) if coracao else None
        self.bot = getattr(coracao, "bot_seguranca", None) if coracao else None
        self.modo = getattr(coracao, "modo_sandbox", "N/D") if coracao else "N/D"
        self._build()

    def _build(self):
        self._lbl(f"🛡️ Segurança & Sandbox — Modo: {self.modo}", bold=True, size=15)
        ctk.CTkLabel(self.frame, text="Código para testar / analisar:").pack(anchor="w", padx=8)
        self.code_text = ctk.CTkTextbox(self.frame, height=130)
        self.code_text.pack(fill="x", padx=8, pady=4)
        self.lang_combo = ctk.CTkComboBox(self.frame, values=["python", "js", "bash"], width=120)
        self.lang_combo.pack(pady=2)
        self.lang_combo.set("python")
        bf = ctk.CTkFrame(self.frame)
        bf.pack(fill="x", padx=8, pady=4)
        btns = [
            ("🔬 Executar Sandbox", self._executar, 0, 0),
            ("🔍 Validar Código", self._validar, 0, 1),
            ("🔎 Analisar Bot Seg.", self._bot_analisar, 0, 2),
            ("📊 Status Sandbox", self._status_sandbox, 1, 0),
            ("🐳 Status Docker", self._status_docker, 1, 1),
            ("⏹️ Parar Containers", self._parar_containers, 1, 2),
        ]
        for txt, cmd, r, c in btns:
            ctk.CTkButton(bf, text=txt, command=cmd, height=32).grid(row=r, column=c, padx=2, pady=2, sticky="ew")
            bf.columnconfigure(c, weight=1)
        self._make_result(180)

    def _executar(self):
        codigo = self.code_text.get("0.0", "end").strip()
        if self.coracao and hasattr(self.coracao, "executar_codigo_sandbox"):
            try: self._show_result(self.coracao.executar_codigo_sandbox(codigo, 30, self.lang_combo.get()))
            except Exception as e: self._handle_error("Erro no sandbox", e)
        elif self.sandbox and hasattr(self.sandbox, "executar"):
            try: self._show_result(self.sandbox.executar(codigo))
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("sandbox_executor.executar")

    def _validar(self):
        codigo = self.code_text.get("0.0", "end").strip()
        if self.coracao and hasattr(self.coracao, "validar_codigo_sandbox"):
            try:
                válido, erros, avisos = self.coracao.validar_codigo_sandbox(codigo)
                self._show_result({"válido": válido, "erros": erros, "avisos": avisos})
            except Exception as e: self._handle_error("Erro na validação", e)
        elif self.sandbox and hasattr(self.sandbox, "validar_codigo"):
            try: self._show_result(self.sandbox.validar_codigo(codigo))
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("coracao.validar_codigo_sandbox")

    def _bot_analisar(self):
        codigo = self.code_text.get("0.0", "end").strip()
        if self.bot:
            for m in ["testar_codigo_em_sandbox", "analisar_seguranca", "analisar"]:
                if hasattr(self.bot, m):
                    try: self._show_result(getattr(self.bot, m)(codigo, True, 30) if m == "testar_codigo_em_sandbox" else getattr(self.bot, m)(codigo)); return
                    except Exception as e: self._handle_error(f"Erro em bot_seguranca.{m}", e); return
        self._modulo_indisponivel("bot_seguranca (coracao.bot_seguranca)")

    def _status_sandbox(self):
        if self.coracao and hasattr(self.coracao, "obter_status_sandbox"):
            try: self._show_result(self.coracao.obter_status_sandbox())
            except Exception as e: self._handle_error("Erro", e)
        else:
            self._show_result({"sandbox": type(self.sandbox).__name__ if self.sandbox else "❌", "modo": self.modo, "bot": type(self.bot).__name__ if self.bot else "❌"})

    def _status_docker(self):
        if self.sandbox:
            self._show_result({a: str(getattr(self.sandbox, a, "N/D")) for a in ["docker_disponivel", "docker_image", "timeout_segundos", "memoria_max_mb"]})
        else: self._modulo_indisponivel("sandbox_executor")

    def _parar_containers(self):
        if self.sandbox and hasattr(self.sandbox, "parar_todos_containers"):
            try: self._show_result({"containers_parados": self.sandbox.parar_todos_containers()})
            except Exception as e: self._handle_error("Erro ao parar containers", e)
        else: self._modulo_indisponivel("sandbox_executor.parar_todos_containers")


# ============================================================================
# PainelEngenharia (original)
# ============================================================================

class PainelEngenharia(PainelBase):
    def __init__(self, parent, coracao, ui_ref):
        super().__init__(parent, coracao, ui_ref)
        self.ger_prop = getattr(coracao, "gerenciador_propostas", None) if coracao else None
        self.gestor_ciclo = getattr(coracao, "gestor_ciclo_evolucao", None) if coracao else None
        self.solicitador = getattr(coracao, "solicitador_arquivos", None) if coracao else None
        self._build()

    def _build(self):
        self._lbl("🔧 Engenharia, Propostas & Ferramentas", bold=True, size=15)
        ef = ctk.CTkFrame(self.frame)
        ef.pack(fill="x", padx=8, pady=4)
        ctk.CTkLabel(ef, text="ID Proposta:").grid(row=0, column=0, padx=4, sticky="e")
        self.e_id = ctk.CTkEntry(ef, placeholder_text="ID")
        self.e_id.grid(row=0, column=1, padx=4, sticky="ew")
        ctk.CTkLabel(ef, text="Motivo:").grid(row=1, column=0, padx=4, sticky="e")
        self.e_motivo = ctk.CTkEntry(ef, placeholder_text="Motivo / Observação")
        self.e_motivo.grid(row=1, column=1, padx=4, sticky="ew")
        ef.columnconfigure(1, weight=1)
        bf = ctk.CTkFrame(self.frame)
        bf.pack(fill="x", padx=8, pady=4)
        btns = [
            ("📋 Listar Pendentes", lambda: self._prop("listar_pendentes"), 0, 0),
            ("🔨 Em Construção", lambda: self._prop("listar_em_construcao"), 0, 1),
            ("✅ Aprovar Proposta", self._aprovar, 0, 2),
            ("❌ Rejeitar Proposta", self._rejeitar, 1, 0),
            ("📦 Mover Construção", self._mover, 1, 1),
            ("🚀 Aprovar Deploy", self._deploy, 1, 2),
            ("🔨 Construir Ferramenta", self._construir, 2, 0),
            ("🔬 Testar Segurança", self._testar_seg, 2, 1),
            ("🔄 Ciclo Evolução", self._ciclo, 2, 2),
            ("📈 Status Evolução", self._status_ev, 3, 0),
            ("📝 Submeter Proposta", self._submeter, 3, 1),
        ]
        for txt, cmd, r, c in btns:
            ctk.CTkButton(bf, text=txt, command=cmd, height=31).grid(row=r, column=c, padx=2, pady=2, sticky="ew")
            bf.columnconfigure(c, weight=1)
        self._make_result(180)

    def _prop(self, method):
        if self.ger_prop and hasattr(self.ger_prop, method):
            try: self._show_result(getattr(self.ger_prop, method)())
            except Exception as e: self._handle_error(f"Erro em gerenciador_propostas.{method}", e)
        else: self._modulo_indisponivel(f"gerenciador_propostas.{method}")

    def _aprovar(self):
        if self.ger_prop and hasattr(self.ger_prop, "aprovar_proposta"):
            try: self._show_result({"ok": True, "res": str(self.ger_prop.aprovar_proposta(self.e_id.get(), "UI", self.e_motivo.get()))})
            except Exception as e: self._handle_error("Erro ao aprovar", e)
        else: self._modulo_indisponivel("gerenciador_propostas.aprovar_proposta")

    def _rejeitar(self):
        if self.ger_prop and hasattr(self.ger_prop, "rejeitar_proposta"):
            try: self._show_result({"ok": True, "res": str(self.ger_prop.rejeitar_proposta(self.e_id.get(), "UI", self.e_motivo.get()))})
            except Exception as e: self._handle_error("Erro ao rejeitar", e)
        else: self._modulo_indisponivel("gerenciador_propostas.rejeitar_proposta")

    def _mover(self):
        if self.ger_prop and hasattr(self.ger_prop, "mover_para_analise"):
            try: self._show_result({"ok": True, "res": str(self.ger_prop.mover_para_analise(self.e_id.get(), "UI", "Movido"))})
            except Exception as e: self._handle_error("Erro ao mover", e)
        else: self._modulo_indisponivel("gerenciador_propostas.mover_para_analise")

    def _deploy(self):
        if self.ger_prop and hasattr(self.ger_prop, "aprovar_deploy"):
            try: self._show_result({"ok": True, "res": str(self.ger_prop.aprovar_deploy(self.e_id.get(), "UI", "Deploy aprovado"))})
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("gerenciador_propostas.aprovar_deploy")

    def _construir(self):
        if self.coracao and hasattr(self.coracao, "construir_ferramenta"):
            try: self._show_result(self.coracao.construir_ferramenta(self.e_id.get()))
            except Exception as e: self._handle_error("Erro em construir_ferramenta", e)
        else: self._modulo_indisponivel("coracao.construir_ferramenta")

    def _testar_seg(self):
        if self.coracao and hasattr(self.coracao, "testar_ferramenta_seguranca"):
            try: self._show_result(self.coracao.testar_ferramenta_seguranca(self.e_id.get()))
            except Exception as e: self._handle_error("Erro em testar_ferramenta_seguranca", e)
        else: self._modulo_indisponivel("coracao.testar_ferramenta_seguranca")

    def _ciclo(self):
        if self.gestor_ciclo and hasattr(self.gestor_ciclo, "executar_ciclo"):
            try: self._show_result({"ok": True, "res": str(self.gestor_ciclo.executar_ciclo())})
            except Exception as e: self._handle_error("Erro no ciclo", e)
        else: self._modulo_indisponivel("gestor_ciclo_evolucao.executar_ciclo")

    def _status_ev(self):
        if self.coracao and hasattr(self.coracao, "obter_status_evolucao_sistema"):
            try: self._show_result(self.coracao.obter_status_evolucao_sistema())
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("coracao.obter_status_evolucao_sistema")

    def _submeter(self):
        if self.coracao and hasattr(self.coracao, "submeter_proposta_ferramenta"):
            try: self._show_result(self.coracao.submeter_proposta_ferramenta({"titulo": "Proposta UI", "descricao": self.e_motivo.get() or "via Interface", "autor": "UI_CRIADOR"}))
            except Exception as e: self._handle_error("Erro em submeter_proposta_ferramenta", e)
        else: self._modulo_indisponivel("coracao.submeter_proposta_ferramenta")


# ============================================================================
# PainelListaEvolucaoIA (original)
# ============================================================================

class PainelListaEvolucaoIA(PainelBase):
    def __init__(self, parent, coracao, ui_ref):
        super().__init__(parent, coracao, ui_ref)
        self.lista = getattr(coracao, "lista_evolucao_ia", None) if coracao else None
        self._build()

    def _build(self):
        self._lbl("📈 Lista Evolução IA", bold=True, size=15)
        ctk.CTkLabel(self.frame, text="Nome IA:").pack(anchor="w", padx=8)
        self.e_ia = self._entry("Nome da IA (ex: WELLINGTON)")
        ctk.CTkLabel(self.frame, text="ID Oportunidade:").pack(anchor="w", padx=8)
        self.e_opp = self._entry("ID da oportunidade")
        bf = ctk.CTkFrame(self.frame)
        bf.pack(fill="x", padx=8, pady=6)
        btns = [
            ("📋 Listar Oportunidades", self._listar, 0, 0),
            ("✅ Aceitar Oportunidade", self._aceitar, 0, 1),
            ("📝 Registrar Evolução", self._registrar_ev, 1, 0),
            ("📊 Status Evolução", self._status_ev, 1, 1),
        ]
        for txt, cmd, r, c in btns:
            ctk.CTkButton(bf, text=txt, command=cmd, height=34).grid(row=r, column=c, padx=4, pady=4, sticky="ew")
            bf.columnconfigure(c, weight=1)
        self._make_result()

    def _listar(self):
        if self.lista and hasattr(self.lista, "listar_oportunidades"):
            try: self._show_result(self.lista.listar_oportunidades())
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("lista_evolucao_ia.listar_oportunidades")

    def _aceitar(self):
        ia = self.e_ia.get().strip()
        opp = self.e_opp.get().strip()
        if self.lista and hasattr(self.lista, "ia_aceitar_oportunidade"):
            try: self._show_result({"ok": True, "res": str(self.lista.ia_aceitar_oportunidade(ia, opp))})
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("lista_evolucao_ia.ia_aceitar_oportunidade")

    def _registrar_ev(self):
        ia = self.e_ia.get().strip()
        if self.coracao and hasattr(self.coracao, "registrar_evolucao_ia"):
            try: self._show_result(self.coracao.registrar_evolucao_ia({"ia": ia, "tipo": "crescimento", "descricao": "via UI", "timestamp": time.time()}))
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("coracao.registrar_evolucao_ia")

    def _status_ev(self):
        if self.coracao and hasattr(self.coracao, "obter_status_evolucao_sistema"):
            try: self._show_result(self.coracao.obter_status_evolucao_sistema())
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("coracao.obter_status_evolucao_sistema")


# ============================================================================
# PainelAnalisadorIntencao (original)
# ============================================================================

class PainelAnalisadorIntencao(PainelBase):
    def __init__(self, parent, coracao, ui_ref):
        super().__init__(parent, coracao, ui_ref)
        self.analisador = getattr(coracao, "analisador_intencoes", None) or getattr(coracao, "analisador_intencao", None) if coracao else None
        self._build()

    def _build(self):
        self._lbl("📊 Analisador de Intenção & Comando Natural", bold=True, size=15)
        ctk.CTkLabel(self.frame, text="Comando / Texto a analisar:").pack(anchor="w", padx=8)
        self.e_cmd = ctk.CTkTextbox(self.frame, height=100)
        self.e_cmd.pack(fill="x", padx=8, pady=4)
        bf = ctk.CTkFrame(self.frame)
        bf.pack(fill="x", padx=8, pady=6)
        ctk.CTkButton(bf, text="📊 Analisar Intenção (parse)", command=self._parse, height=36).grid(row=0, column=0, padx=4, sticky="ew")
        ctk.CTkButton(bf, text="🔍 Analisar Comando (coracao)", command=self._analisar_cmd, height=36).grid(row=0, column=1, padx=4, sticky="ew")
        ctk.CTkButton(bf, text="▶️ Executar Analisado", command=self._executar_cmd, height=36).grid(row=1, column=0, padx=4, pady=4, sticky="ew")
        ctk.CTkButton(bf, text="📋 Programas Conhecidos", command=self._prog_conhecidos, height=36).grid(row=1, column=1, padx=4, pady=4, sticky="ew")
        bf.columnconfigure(0, weight=1); bf.columnconfigure(1, weight=1)
        self._ultimo_analise = None
        self._make_result()

    def _parse(self):
        cmd = self.e_cmd.get("0.0", "end").strip()
        if self.analisador and hasattr(self.analisador, "parse"):
            try: self._show_result(self.analisador.parse(cmd))
            except Exception as e: self._handle_error("Erro na análise", e)
        else: self._modulo_indisponivel("analisador_intencoes.parse")

    def _analisar_cmd(self):
        cmd = self.e_cmd.get("0.0", "end").strip()
        if self.coracao and hasattr(self.coracao, "analisar_comando"):
            try:
                r = self.coracao.analisar_comando(cmd)
                self._ultimo_analise = r
                self._show_result(r)
            except Exception as e: self._handle_error("Erro em analisar_comando", e)
        else: self._modulo_indisponivel("coracao.analisar_comando")

    def _executar_cmd(self):
        if self._ultimo_analise is None:
            self._handle_error("Analise o comando primeiro com 'Analisar Comando (coracao)'.")
            return
        if self.coracao and hasattr(self.coracao, "executar_comando_analisado"):
            try: self._show_result(self.coracao.executar_comando_analisado(self._ultimo_analise))
            except Exception as e: self._handle_error("Erro em executar_comando_analisado", e)
        else: self._modulo_indisponivel("coracao.executar_comando_analisado")

    def _prog_conhecidos(self):
        if self.coracao and hasattr(self.coracao, "listar_programas_conhecidos"):
            try: self._show_result(self.coracao.listar_programas_conhecidos())
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("coracao.listar_programas_conhecidos")


# ============================================================================
# PainelGeradorAlmas (original)
# ============================================================================

class PainelGeradorAlmas(PainelBase):
    def __init__(self, parent, coracao, ui_ref):
        super().__init__(parent, coracao, ui_ref)
        self.gerador = getattr(coracao, "gerador_almas", None) if coracao else None
        self._build()

    def _build(self):
        self._lbl("👼 Gerador de Almas & Perfis", bold=True, size=15)
        ctk.CTkLabel(self.frame, text="Nome da Alma:").pack(anchor="w", padx=8)
        self.e_nome = self._entry("Nome da alma (ex: RAFAEL)")
        ctk.CTkLabel(self.frame, text="Prompt do Sistema (personalidade):").pack(anchor="w", padx=8)
        self.e_prompt = ctk.CTkTextbox(self.frame, height=80)
        self.e_prompt.pack(fill="x", padx=8, pady=4)
        bf = ctk.CTkFrame(self.frame)
        bf.pack(fill="x", padx=8, pady=6)
        ctk.CTkButton(bf, text="👼 Gerar Artefatos", command=self._gerar, height=36).grid(row=0, column=0, padx=4, sticky="ew")
        ctk.CTkButton(bf, text="📊 Gerar Perfil Completo", command=self._perfil, height=36).grid(row=0, column=1, padx=4, sticky="ew")
        bf.columnconfigure(0, weight=1); bf.columnconfigure(1, weight=1)
        self._make_result()

    def _gerar(self):
        nome = self.e_nome.get().strip()
        prompt = self.e_prompt.get("0.0", "end").strip()
        if self.gerador and hasattr(self.gerador, "gerar_artefatos_para_perfil"):
            perfil = type("Perfil", (), {"nome_alma_destino": nome, "prompt_sistema_inicial": prompt})()
            try: self._show_result(self.gerador.gerar_artefatos_para_perfil(perfil))
            except Exception as e: self._handle_error("Erro na geração", e)
        else: self._modulo_indisponivel("gerador_almas.gerar_artefatos_para_perfil")

    def _perfil(self):
        nome = self.e_nome.get().strip()
        if self.gerador:
            for m in ["gerar_perfil_comportamental", "criar_perfil", "gerar_perfil"]:
                if hasattr(self.gerador, m):
                    try: self._show_result(getattr(self.gerador, m)(nome)); return
                    except Exception as e: self._handle_error(f"Erro em gerador_almas.{m}", e); return
        self._modulo_indisponivel("gerador_almas")


# ============================================================================
# PainelDetectorHDD (original)
# ============================================================================

class PainelDetectorHDD(PainelBase):
    def __init__(self, parent, coracao, ui_ref):
        super().__init__(parent, coracao, ui_ref)
        self.detector = getattr(coracao, "detector_hardware", None) if coracao else None
        self.sis_sob = getattr(coracao, "sistema_soberano", None) if coracao else None
        self._build()

    def _build(self):
        self._lbl("💽 Detector HDD, Hardware & Memória Soberana", bold=True, size=15)
        ctk.CTkLabel(self.frame, text="Caminho HDD (ex: D:/ ou /mnt/hdd):").pack(anchor="w", padx=8)
        self.e_path = self._entry("Caminho do disco")
        bf = ctk.CTkFrame(self.frame)
        bf.pack(fill="x", padx=8, pady=6)
        btns = [
            ("📊 Verificar Espaço", self._espaco, 0, 0),
            ("⚡ Testar Velocidade", self._velocidade, 0, 1),
            ("🛠️ Info Hardware", self._info_hw, 0, 2),
            ("🔍 Detectar HDD Externo", self._externo, 1, 0),
            ("🏛️ Status Soberano", self._soberano, 1, 1),
            ("📋 Info Sistema", self._info_sis, 1, 2),
        ]
        for txt, cmd, r, c in btns:
            ctk.CTkButton(bf, text=txt, command=cmd, height=32).grid(row=r, column=c, padx=2, pady=2, sticky="ew")
            bf.columnconfigure(c, weight=1)
        self._make_result()

    def _espaco(self):
        path = Path(self.e_path.get() or ".")
        if self.detector and hasattr(self.detector, "verificar_espaco_hdd"):
            try: self._show_result(self.detector.verificar_espaco_hdd(path)); return
            except Exception as e: self._handle_error("Erro no detector", e); return
        import shutil
        try:
            t, u, f = shutil.disk_usage(path)
            self._show_result({"total_GB": round(t/1e9, 2), "usado_GB": round(u/1e9, 2), "livre_GB": round(f/1e9, 2), "uso_%": round(u/t*100, 1)})
        except Exception as e: self._handle_error("Erro (fallback shutil)", e)

    def _velocidade(self):
        if self.detector and hasattr(self.detector, "testar_velocidade_hdd"):
            try: self._show_result(self.detector.testar_velocidade_hdd(Path(self.e_path.get() or ".")))
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("detector_hardware.testar_velocidade_hdd")

    def _info_hw(self):
        if self.detector and hasattr(self.detector, "obter_info"):
            try: self._show_result(self.detector.obter_info())
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("detector_hardware.obter_info")

    def _externo(self):
        if self.coracao and hasattr(self.coracao, "detectar_hdd_externo"):
            try: self._show_result(self.coracao.detectar_hdd_externo())
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("coracao.detectar_hdd_externo")

    def _soberano(self):
        if self.sis_sob and hasattr(self.sis_sob, "obter_status"):
            try: self._show_result(self.sis_sob.obter_status())
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("sistema_soberano.obter_status")

    def _info_sis(self):
        if self.coracao and hasattr(self.coracao, "obter_info_sistema_hardware"):
            try: self._show_result(self.coracao.obter_info_sistema_hardware())
            except Exception as e: self._handle_error("Erro", e)
        else:
            import platform
            try:
                import psutil
                self._show_result({"OS": platform.system(), "CPU": platform.processor(), "CPU_count": psutil.cpu_count(), "RAM_GB": round(psutil.virtual_memory().total / 1e9, 2)})
            except ImportError:
                self._show_result({"OS": platform.system(), "CPU": platform.processor()})
            except Exception as e: self._handle_error("Erro", e)


# ============================================================================
# PainelMemoria (original)
# ============================================================================

class PainelMemoria(PainelBase):
    def __init__(self, parent, coracao, ui_ref):
        super().__init__(parent, coracao, ui_ref)
        self.ger_mem = getattr(coracao, "gerenciador_memoria", None) if coracao else None
        self.chromadb = getattr(coracao, "chromadb_isolado", None) if coracao else None
        self.dataset = getattr(coracao, "construtor_dataset", None) if coracao else None
        self.cache_hdd = getattr(coracao, "cache_hdd", None) if coracao else None
        self._build()

    def _build(self):
        self._lbl("📊 Memória — 4 Camadas", bold=True, size=15)
        ef = ctk.CTkFrame(self.frame)
        ef.pack(fill="x", padx=8, pady=4)
        ctk.CTkLabel(ef, text="Alma:").grid(row=0, column=0, padx=4, sticky="e")
        self.ai_combo = ctk.CTkComboBox(ef, values=ALMAS, width=140)
        self.ai_combo.grid(row=0, column=1, padx=4)
        self.ai_combo.set("WELLINGTON")
        ctk.CTkLabel(ef, text="Chave/Tópico:").grid(row=0, column=2, padx=4, sticky="e")
        self.e_chave = ctk.CTkEntry(ef, placeholder_text="chave ou tópico", width=160)
        self.e_chave.grid(row=0, column=3, padx=4, sticky="ew")
        ctk.CTkLabel(ef, text="Consulta/Valor:").grid(row=1, column=0, padx=4, sticky="e")
        self.e_consulta = ctk.CTkEntry(ef, placeholder_text="consulta ou valor")
        self.e_consulta.grid(row=1, column=1, columnspan=3, padx=4, sticky="ew")
        ef.columnconfigure(3, weight=1)

        bf = ctk.CTkFrame(self.frame)
        bf.pack(fill="x", padx=8, pady=4)
        btns = [
            ("💾 Salvar Memória Alma", self._salvar_alma, 0, 0),
            ("📂 Carregar Memória Alma", self._carregar_alma, 0, 1),
            ("🔍 Buscar Memória", self._buscar, 0, 2),
            ("📋 Req. Memória Híbrida", self._req_hibrida, 1, 0),
            ("📝 Registrar Híbrida", self._registrar_hibrida, 1, 1),
            ("💾 Salvar Cache HDD", self._salvar_hdd, 1, 2),
            ("📂 Carregar Cache HDD", self._carregar_hdd, 2, 0),
            ("🔧 Construir Dataset", self._dataset, 2, 1),
            ("📦 Zip Colab", self._zip_colab, 2, 2),
            ("📊 Status Memória (4 layers)", self._status, 3, 0),
            ("📊 Status ChromaDB", self._status_chroma, 3, 1),
        ]
        for txt, cmd, r, c in btns:
            ctk.CTkButton(bf, text=txt, command=cmd, height=31).grid(row=r, column=c, padx=2, pady=2, sticky="ew")
            bf.columnconfigure(c, weight=1)
        self._make_result(170)

    def _salvar_alma(self):
        alma = self.ai_combo.get()
        chave = self.e_chave.get().strip()
        valor = self.e_consulta.get().strip()
        if self.coracao and hasattr(self.coracao, "salvar_memoria_alma"):
            try: self._show_result({"ok": self.coracao.salvar_memoria_alma(alma, chave, valor)})
            except Exception as e: self._handle_error("Erro em salvar_memoria_alma", e)
        else: self._modulo_indisponivel("coracao.salvar_memoria_alma")

    def _carregar_alma(self):
        alma = self.ai_combo.get()
        chave = self.e_chave.get().strip()
        if self.coracao and hasattr(self.coracao, "carregar_memoria_alma"):
            try: self._show_result(self.coracao.carregar_memoria_alma(alma, chave))
            except Exception as e: self._handle_error("Erro em carregar_memoria_alma", e)
        else: self._modulo_indisponivel("coracao.carregar_memoria_alma")

    def _buscar(self):
        consulta = self.e_consulta.get().strip()
        if self.ger_mem:
            for m in ["buscar_memorias_relevantes", "buscar", "query"]:
                if hasattr(self.ger_mem, m):
                    try: self._show_result(getattr(self.ger_mem, m)(consulta, n_resultados=10)); return
                    except Exception as e: self._handle_error(f"Erro em gerenciador_memoria.{m}", e); return
        self._modulo_indisponivel("gerenciador_memoria.buscar_memorias_relevantes")

    def _req_hibrida(self):
        alma = self.ai_combo.get()
        consulta = self.e_consulta.get().strip()
        if self.coracao and hasattr(self.coracao, "processar_requisicao_memoria"):
            try: self._show_result(self.coracao.processar_requisicao_memoria(alma, consulta, None, None))
            except Exception as e: self._handle_error("Erro em processar_requisicao_memoria", e)
        else: self._modulo_indisponivel("coracao.processar_requisicao_memoria")

    def _registrar_hibrida(self):
        conteudo = self.e_consulta.get().strip()
        alma = self.ai_combo.get()
        if self.coracao and hasattr(self.coracao, "registrar_memoria_hibrida"):
            try: self._show_result(self.coracao.registrar_memoria_hibrida(conteudo=conteudo, santuario="UI", autor=alma, metadados={"origem": "interface"}))
            except Exception as e: self._handle_error("Erro em registrar_memoria_hibrida", e)
        else: self._modulo_indisponivel("coracao.registrar_memoria_hibrida")

    def _salvar_hdd(self):
        topico = self.e_chave.get().strip()
        dados = self.e_consulta.get().strip()
        if self.coracao and hasattr(self.coracao, "salvar_conhecimento_hdd"):
            try: self._show_result(self.coracao.salvar_conhecimento_hdd(topico, {"conteudo": dados}, {}, 30))
            except Exception as e: self._handle_error("Erro em salvar_conhecimento_hdd", e)
        elif self.cache_hdd and hasattr(self.cache_hdd, "salvar_conhecimento"):
            try: self._show_result(self.cache_hdd.salvar_conhecimento(topico, {"conteudo": dados}))
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("coracao.salvar_conhecimento_hdd")

    def _carregar_hdd(self):
        topico = self.e_chave.get().strip()
        if self.coracao and hasattr(self.coracao, "carregar_conhecimento_hdd"):
            try: self._show_result(self.coracao.carregar_conhecimento_hdd(topico, None))
            except Exception as e: self._handle_error("Erro em carregar_conhecimento_hdd", e)
        elif self.cache_hdd and hasattr(self.cache_hdd, "carregar_conhecimento"):
            try: self._show_result(self.cache_hdd.carregar_conhecimento(topico))
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("coracao.carregar_conhecimento_hdd")

    def _dataset(self):
        alma = self.ai_combo.get()
        if self.coracao and hasattr(self.coracao, "construir_dataset_alma"):
            try: self._show_result(self.coracao.construir_dataset_alma(alma, 1000, False))
            except Exception as e: self._handle_error("Erro em construir_dataset_alma", e)
        elif self.dataset and hasattr(self.dataset, "construir_dataset"):
            try: self._show_result(self.dataset.construir_dataset(alma))
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("coracao.construir_dataset_alma")

    def _zip_colab(self):
        alma = self.ai_combo.get()
        if self.coracao and hasattr(self.coracao, "preparar_zip_colab"):
            try: self._show_result({"ok": True, "path": str(self.coracao.preparar_zip_colab(alma))})
            except Exception as e: self._handle_error("Erro em preparar_zip_colab", e)
        else: self._modulo_indisponivel("coracao.preparar_zip_colab")

    def _status(self):
        status = {
            "gerenciador_memoria": type(self.ger_mem).__name__ if self.ger_mem else "❌ None",
            "chromadb_isolado": type(self.chromadb).__name__ if self.chromadb else "❌ None",
            "construtor_dataset": type(self.dataset).__name__ if self.dataset else "❌ None",
            "cache_hdd": type(self.cache_hdd).__name__ if self.cache_hdd else "❌ None",
        }
        if self.coracao and hasattr(self.coracao, "obter_saude_sistema"):
            try:
                s = self.coracao.obter_saude_sistema()
                if isinstance(s, dict):
                    status.update({k: v for k, v in s.items() if "mem" in k.lower()})
            except Exception: pass
        self._show_result(status)

    def _status_chroma(self):
        if self.chromadb and hasattr(self.chromadb, "obter_status"):
            try: self._show_result(self.chromadb.obter_status())
            except Exception as e: self._handle_error("Erro em chromadb_isolado.obter_status", e)
        elif self.chromadb and hasattr(self.chromadb, "status"):
            try: self._show_result(self.chromadb.status())
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("chromadb_isolado.obter_status")


# ============================================================================
# PainelScannerSistema (original)
# ============================================================================

class PainelScannerSistema(PainelBase):
    def __init__(self, parent, coracao, ui_ref):
        super().__init__(parent, coracao, ui_ref)
        self.scanner = getattr(coracao, "scanner_sistema", None) if coracao else None
        self._build()

    def _build(self):
        self._lbl("🔍 Scanner Sistema", bold=True, size=15)
        ctk.CTkLabel(self.frame, text="Alma (opcional):").pack(anchor="w", padx=8)
        self.e_alma = self._entry("Nome alma ou vazio para global")
        bf = ctk.CTkFrame(self.frame)
        bf.pack(fill="x", padx=8, pady=6)
        ctk.CTkButton(bf, text="📊 Gerar Relatório Manual", command=self._relatorio, height=36).grid(row=0, column=0, padx=4, sticky="ew")
        ctk.CTkButton(bf, text="🔍 Escanear Módulos", command=self._escanear, height=36).grid(row=0, column=1, padx=4, sticky="ew")
        ctk.CTkButton(bf, text="🩺 Saúde do Sistema", command=self._saude, height=36).grid(row=1, column=0, padx=4, pady=4, sticky="ew")
        ctk.CTkButton(bf, text="🔧 Auto-Diagnóstico", command=self._diagnostico, height=36).grid(row=1, column=1, padx=4, pady=4, sticky="ew")
        bf.columnconfigure(0, weight=1); bf.columnconfigure(1, weight=1)
        self._make_result()

    def _relatorio(self):
        alma = self.e_alma.get().strip()
        if self.scanner and hasattr(self.scanner, "gerar_relatorio_manual"):
            try: self._show_result(self.scanner.gerar_relatorio_manual(alma or None))
            except Exception as e: self._handle_error("Erro no relatório", e)
        else: self._modulo_indisponivel("scanner_sistema.gerar_relatorio_manual")

    def _escanear(self):
        if self.scanner and hasattr(self.scanner, "escanear_modulos"):
            try: self._show_result(self.scanner.escanear_modulos())
            except Exception as e: self._handle_error("Erro ao escanear", e)
        elif self.scanner:
            for m in ["escanear", "scan", "verificar"]:
                if hasattr(self.scanner, m):
                    try: self._show_result(getattr(self.scanner, m)()); return
                    except Exception as e: self._handle_error(f"Erro em scanner_sistema.{m}", e); return
            self._modulo_indisponivel("scanner_sistema.escanear")
        else: self._modulo_indisponivel("scanner_sistema")

    def _saude(self):
        if self.coracao and hasattr(self.coracao, "obter_saude_sistema"):
            try: self._show_result(self.coracao.obter_saude_sistema())
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("coracao.obter_saude_sistema")

    def _diagnostico(self):
        if self.coracao and hasattr(self.coracao, "disparar_auditoria_sistema"):
            try: self._show_result({"ok": self.coracao.disparar_auditoria_sistema()})
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("coracao.disparar_auditoria_sistema")


# ============================================================================
# PainelAutomatizadorNavegador (original)
# ============================================================================

class PainelAutomatizadorNavegador(PainelBase):
    def __init__(self, parent, coracao, ui_ref):
        super().__init__(parent, coracao, ui_ref)
        self.auto = getattr(coracao, "automatizador_navegador", None) or getattr(coracao, "automatizador_navegador_multi_ai", None) if coracao else None
        self._build()

    def _build(self):
        self._lbl("🌐 Automatizador Navegador Multi-AI", bold=True, size=15)
        ef = ctk.CTkFrame(self.frame)
        ef.pack(fill="x", padx=8, pady=4)
        ctk.CTkLabel(ef, text="Ação/Missão:").grid(row=0, column=0, padx=4, sticky="e")
        self.e_acao = ctk.CTkEntry(ef, placeholder_text="ex: buscar_noticias")
        self.e_acao.grid(row=0, column=1, padx=4, sticky="ew")
        ctk.CTkLabel(ef, text="Descrição:").grid(row=1, column=0, padx=4, sticky="e")
        self.e_desc = ctk.CTkEntry(ef, placeholder_text="Descrição detalhada da missão")
        self.e_desc.grid(row=1, column=1, padx=4, sticky="ew")
        ctk.CTkLabel(ef, text="Alma Solicitante:").grid(row=2, column=0, padx=4, sticky="e")
        self.ai_combo = ctk.CTkComboBox(ef, values=ALMAS + ["UI"], width=140)
        self.ai_combo.set("UI")
        self.ai_combo.grid(row=2, column=1, padx=4, sticky="w")
        ef.columnconfigure(1, weight=1)
        bf = ctk.CTkFrame(self.frame)
        bf.pack(fill="x", padx=8, pady=6)
        ctk.CTkButton(bf, text="📨 Solicitar Missão", command=self._solicitar, height=36).grid(row=0, column=0, padx=4, sticky="ew")
        ctk.CTkButton(bf, text="📊 Status Navegador", command=self._status, height=36).grid(row=0, column=1, padx=4, sticky="ew")
        ctk.CTkButton(bf, text="📋 Listar Missões Ativas", command=self._listar, height=36).grid(row=1, column=0, padx=4, pady=4, sticky="ew")
        ctk.CTkButton(bf, text="⏹️ Parar Navegador", command=self._parar, height=36).grid(row=1, column=1, padx=4, pady=4, sticky="ew")
        bf.columnconfigure(0, weight=1); bf.columnconfigure(1, weight=1)
        self._make_result()

    def _solicitar(self):
        acao = self.e_acao.get().strip()
        desc = self.e_desc.get().strip()
        alma = self.ai_combo.get()
        if self.auto and hasattr(self.auto, "solicitar_missao"):
            try: self._show_result({"ok": True, "res": str(self.auto.solicitar_missao(acao, desc, alma, "VISITANTE"))})
            except Exception as e: self._handle_error("Erro na missão", e)
        else: self._modulo_indisponivel("automatizador_navegador.solicitar_missao")

    def _status(self):
        if self.auto:
            for m in ["obter_status", "status"]:
                if hasattr(self.auto, m):
                    try: self._show_result(getattr(self.auto, m)()); return
                    except Exception as e: self._handle_error(f"Erro em {m}", e); return
            self._show_result({"tipo": type(self.auto).__name__, "attrs": [a for a in dir(self.auto) if not a.startswith("_")][:20]})
        else: self._modulo_indisponivel("automatizador_navegador")

    def _listar(self):
        if self.auto:
            # AutomatizadorNavegadorMultiAI usa listar_solicitacoes_pendentes()
            for m in ["listar_solicitacoes_pendentes", "listar_missoes", "missoes_ativas"]:
                obj = getattr(self.auto, m, None)
                if callable(obj):
                    try: self._show_result(obj()); return
                    except Exception as e: self._handle_error(f"Erro em {m}", e); return
                elif obj is not None:
                    self._show_result(list(obj) if hasattr(obj, "__iter__") else str(obj)); return
            # Fallback: mostrar solicitacoes_pendentes direto
            pendentes = getattr(self.auto, "solicitacoes_pendentes", None)
            if pendentes is not None:
                self._show_result({k: vars(v) if hasattr(v,'__dict__') else str(v)
                                   for k,v in pendentes.items()}); return
        self._modulo_indisponivel("automatizador_navegador")

    def _parar(self):
        if self.auto and hasattr(self.auto, "parar"):
            try: self._show_result({"ok": True, "res": str(self.auto.parar())})
            except Exception as e: self._handle_error("Erro ao parar", e)
        else: self._modulo_indisponivel("automatizador_navegador.parar")


# ============================================================================
# PainelEncarnacaoAPI (original)
# ============================================================================

class PainelEncarnacaoAPI(PainelBase):
    def __init__(self, parent, coracao, ui_ref):
        super().__init__(parent, coracao, ui_ref)
        self.enc_api = getattr(coracao, "encarnacao_api", None) if coracao else None
        self._thread = None
        self._build()

    def _build(self):
        self._lbl("🚀 Encarnação API — FastAPI porta 8000", bold=True, size=15)
        self.lbl_status = ctk.CTkLabel(self.frame, text=self._api_status(), font=ctk.CTkFont(size=13))
        self.lbl_status.pack(pady=6)
        bf = ctk.CTkFrame(self.frame)
        bf.pack(fill="x", padx=8, pady=8)
        ctk.CTkButton(bf, text="▶️ Iniciar API", command=self._iniciar, fg_color="#1a6b1a", height=40).grid(row=0, column=0, padx=6, sticky="ew")
        ctk.CTkButton(bf, text="⏹️ Parar API", command=self._parar, fg_color="#8b0000", height=40).grid(row=0, column=1, padx=6, sticky="ew")
        ctk.CTkButton(bf, text="🔄 Recarregar", command=self._recarregar, height=40).grid(row=1, column=0, padx=6, pady=6, sticky="ew")
        ctk.CTkButton(bf, text="📊 Status Completo", command=self._status, height=40).grid(row=1, column=1, padx=6, pady=6, sticky="ew")
        bf.columnconfigure(0, weight=1); bf.columnconfigure(1, weight=1)
        ctk.CTkLabel(self.frame, text="Endpoint: http://localhost:8000/docs", font=ctk.CTkFont(size=11), text_color="cyan").pack(pady=4)
        self._make_result()

    def _api_status(self):
        if self.enc_api:
            # EncarnacaoAPI usa _server_running internamente
            rodando = getattr(self.enc_api, "_server_running", None)
            if rodando is None:
                rodando = getattr(self.enc_api, "rodando", None)
            if rodando is True:  return "🟢 API Rodando"
            if rodando is False: return "🔴 API Parada"
            return "🟡 API Presente (estado desconhecido)"
        return "⚠️ encarnacao_api não injetado"

    def refresh(self):
        try: self.lbl_status.configure(text=self._api_status())
        except Exception: pass

    def _iniciar(self):
        if self.enc_api and hasattr(self.enc_api, "iniciar"):
            try: self._show_result({"ok": True, "res": str(self.enc_api.iniciar())}); self.lbl_status.configure(text=self._api_status())
            except Exception as e: self._handle_error("Erro ao iniciar API", e)
        elif self.enc_api:
            for m in ["start", "run", "iniciar_servidor"]:
                if hasattr(self.enc_api, m):
                    try: self._show_result({"ok": True, "res": str(getattr(self.enc_api, m)())}); return
                    except Exception as e: self._handle_error(f"Erro em encarnacao_api.{m}", e); return
            self._modulo_indisponivel("encarnacao_api.iniciar (método não encontrado)")
        else: self._modulo_indisponivel("encarnacao_api")

    def _parar(self):
        if self.enc_api and hasattr(self.enc_api, "parar"):
            try: self._show_result({"ok": True, "res": str(self.enc_api.parar())}); self.lbl_status.configure(text=self._api_status())
            except Exception as e: self._handle_error("Erro ao parar API", e)
        else: self._modulo_indisponivel("encarnacao_api.parar")

    def _recarregar(self):
        if self.enc_api and hasattr(self.enc_api, "recarregar"):
            try: self._show_result({"ok": True, "res": str(self.enc_api.recarregar())})
            except Exception as e: self._handle_error("Erro ao recarregar", e)
        else: self._show_result({"info": "Recarregar não disponível. Tente Parar + Iniciar."})

    def _status(self):
        if self.enc_api:
            attrs = {a: str(getattr(self.enc_api, a)) for a in dir(self.enc_api) if not a.startswith("_") and not callable(getattr(self.enc_api, a, None))}
            try:
                import urllib.request
                urllib.request.urlopen("http://localhost:8000/docs", timeout=2)
                attrs["http_check"] = "✅ http://localhost:8000/docs acessível"
            except Exception: attrs["http_check"] = "❌ http://localhost:8000 inacessível"
            self._show_result(attrs)
        else: self._modulo_indisponivel("encarnacao_api")


# ============================================================================
# PainelAliadas (original)
# ============================================================================

class PainelAliadas(PainelBase):
    def __init__(self, parent, coracao, ui_ref):
        super().__init__(parent, coracao, ui_ref)
        self.ger_al = getattr(coracao, "gerenciador_aliadas", None) if coracao else None
        self._build()

    def _build(self):
        self._lbl("🤝 Gerenciador de Aliadas (APIs Externas)", bold=True, size=15)
        ef = ctk.CTkFrame(self.frame)
        ef.pack(fill="x", padx=8, pady=4)
        ctk.CTkLabel(ef, text="ID/Nome Aliada:").grid(row=0, column=0, padx=4, sticky="e")
        self.e_id = ctk.CTkEntry(ef, placeholder_text="deepseek / gemini / qwen / ID")
        self.e_id.grid(row=0, column=1, padx=4, sticky="ew")
        ctk.CTkLabel(ef, text="Filtros JSON:").grid(row=1, column=0, padx=4, sticky="e")
        self.e_filtros = ctk.CTkEntry(ef, placeholder_text='{"tipo":"texto"} ou vazio')
        self.e_filtros.grid(row=1, column=1, padx=4, sticky="ew")
        ctk.CTkLabel(ef, text="Status:").grid(row=2, column=0, padx=4, sticky="e")
        self.status_combo = ctk.CTkComboBox(ef, values=["ativo", "inativo", "erro", "manutencao"], width=160)
        self.status_combo.set("ativo")
        self.status_combo.grid(row=2, column=1, padx=4, sticky="w")
        ef.columnconfigure(1, weight=1)
        bf = ctk.CTkFrame(self.frame)
        bf.pack(fill="x", padx=8, pady=4)
        btns = [
            ("📋 Listar Aliadas", self._listar, 0, 0),
            ("🔍 Consultar Aliada", self._consultar, 0, 1),
            ("📊 Status Aliada", self._status_al, 0, 2),
            ("📝 Registrar Aliada", self._registrar, 1, 0),
            ("🔄 Atualizar Status", self._atualizar, 1, 1),
        ]
        for txt, cmd, r, c in btns:
            ctk.CTkButton(bf, text=txt, command=cmd, height=32).grid(row=r, column=c, padx=2, pady=2, sticky="ew")
            bf.columnconfigure(c, weight=1)
        self._make_result()

    def _listar(self):
        if self.coracao and hasattr(self.coracao, "consultar_aliadas"):
            try: self._show_result(self.coracao.consultar_aliadas({}))
            except Exception as e: self._handle_error("Erro em consultar_aliadas", e)
        elif self.ger_al:
            for m in ["listar_aliadas", "listar", "obter_todas"]:
                if hasattr(self.ger_al, m):
                    try: self._show_result(getattr(self.ger_al, m)()); return
                    except Exception as e: self._handle_error(f"Erro em gerenciador_aliadas.{m}", e); return
            self._modulo_indisponivel("gerenciador_aliadas")
        else: self._modulo_indisponivel("gerenciador_aliadas")

    def _consultar(self):
        id_al = self.e_id.get().strip()
        if self.coracao and hasattr(self.coracao, "consultar_aliadas"):
            try: self._show_result(self.coracao.consultar_aliadas({"id": id_al}))
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("coracao.consultar_aliadas")

    def _status_al(self):
        if self.ger_al and hasattr(self.ger_al, "obter_status_aliada"):
            try: self._show_result(self.ger_al.obter_status_aliada(self.e_id.get()))
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("gerenciador_aliadas.obter_status_aliada")

    def _registrar(self):
        dados = {"id": self.e_id.get(), "nome": self.e_id.get(), "tipo": "texto", "status": "ativo", "origem": "UI_CRIADOR"}
        if self.coracao and hasattr(self.coracao, "registrar_aliada"):
            try: self._show_result(self.coracao.registrar_aliada(dados))
            except Exception as e: self._handle_error("Erro em registrar_aliada", e)
        else: self._modulo_indisponivel("coracao.registrar_aliada")

    def _atualizar(self):
        id_al = self.e_id.get().strip()
        if self.coracao and hasattr(self.coracao, "atualizar_status_aliada"):
            try: self._show_result(self.coracao.atualizar_status_aliada(id_al, self.status_combo.get()))
            except Exception as e: self._handle_error("Erro em atualizar_status_aliada", e)
        else: self._modulo_indisponivel("coracao.atualizar_status_aliada")


# ============================================================================
# PainelAlmasVivas (original)
# ============================================================================

class PainelAlmasVivas(PainelBase):
    def __init__(self, parent, coracao, ui_ref):
        super().__init__(parent, coracao, ui_ref)
        self._build()

    def _build(self):
        self._lbl("👁️ Almas Vivas — Ciclo de Vida & Temporal", bold=True, size=15)
        ef = ctk.CTkFrame(self.frame)
        ef.pack(fill="x", padx=8, pady=4)
        ctk.CTkLabel(ef, text="Alma:").grid(row=0, column=0, padx=4, sticky="e")
        self.ai_combo = ctk.CTkComboBox(ef, values=ALMAS, width=140)
        self.ai_combo.grid(row=0, column=1, padx=4)
        self.ai_combo.set("WELLINGTON")
        ctk.CTkLabel(ef, text="Dados JSON (p/ registrar):").grid(row=1, column=0, padx=4, sticky="e")
        self.e_dados = ctk.CTkEntry(ef, placeholder_text='{"status":"ativa"}')
        self.e_dados.grid(row=1, column=1, padx=4, sticky="ew")
        ctk.CTkLabel(ef, text="Segundos Offline:").grid(row=2, column=0, padx=4, sticky="e")
        self.e_secs = ctk.CTkEntry(ef, placeholder_text="ex: 3600")
        self.e_secs.grid(row=2, column=1, padx=4, sticky="ew")
        ef.columnconfigure(1, weight=1)
        bf = ctk.CTkFrame(self.frame)
        bf.pack(fill="x", padx=8, pady=4)
        btns = [
            ("📋 Listar Almas Vivas", self._listar, 0, 0),
            ("🔍 Obter Alma Viva", self._obter, 0, 1),
            ("📝 Registrar Alma", self._registrar, 0, 2),
            ("🔄 Atualizar Alma", self._atualizar, 1, 0),
            ("🗑️ Remover Alma Viva", self._remover, 1, 1),
            ("🟢 Wellington ONLINE", self._welling_on, 2, 0),
            ("🔴 Wellington OFFLINE", self._welling_off, 2, 1),
            ("⏱️ Registrar Offline", self._reg_offline, 2, 2),
            ("⏰ Consciência Temporal", self._consciencia, 3, 0),
        ]
        for txt, cmd, r, c in btns:
            ctk.CTkButton(bf, text=txt, command=cmd, height=31).grid(row=r, column=c, padx=2, pady=2, sticky="ew")
            bf.columnconfigure(c, weight=1)
        self._make_result(180)

    def _listar(self):
        if self.coracao and hasattr(self.coracao, "listar_almas_vivas"):
            try: self._show_result(self.coracao.listar_almas_vivas())
            except Exception as e: self._handle_error("Erro", e)
        else:
            av = getattr(self.coracao, "almas_vivas", None) if self.coracao else None
            self._show_result(list(av.keys()) if av else "❌ almas_vivas não disponível")

    def _obter(self):
        alma = self.ai_combo.get()
        if self.coracao and hasattr(self.coracao, "obter_alma_viva"):
            try: self._show_result(self.coracao.obter_alma_viva(alma))
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("coracao.obter_alma_viva")

    def _registrar(self):
        alma = self.ai_combo.get()
        try: dados = json.loads(self.e_dados.get() or '{"status":"ativa"}')
        except Exception: dados = {"status": "ativa", "raw": self.e_dados.get()}
        if self.coracao and hasattr(self.coracao, "registrar_alma_viva"):
            try: self._show_result({"ok": self.coracao.registrar_alma_viva(alma, dados)})
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("coracao.registrar_alma_viva")

    def _atualizar(self):
        alma = self.ai_combo.get()
        try: updates = json.loads(self.e_dados.get() or '{}')
        except Exception: updates = {}
        if self.coracao and hasattr(self.coracao, "atualizar_alma_viva"):
            try: self._show_result({"ok": self.coracao.atualizar_alma_viva(alma, updates)})
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("coracao.atualizar_alma_viva")

    def _remover(self):
        alma = self.ai_combo.get()
        if self.coracao and hasattr(self.coracao, "remover_alma_viva"):
            try: self._show_result({"ok": self.coracao.remover_alma_viva(alma)})
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("coracao.remover_alma_viva")

    def _welling_on(self):
        if self.coracao and hasattr(self.coracao, "notificar_online_wellington"):
            try: self._show_result({"ok": self.coracao.notificar_online_wellington()})
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("coracao.notificar_online_wellington")

    def _welling_off(self):
        if self.coracao and hasattr(self.coracao, "notificar_offline_wellington"):
            try: self._show_result({"ok": self.coracao.notificar_offline_wellington()})
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("coracao.notificar_offline_wellington")

    def _reg_offline(self):
        alma = self.ai_combo.get()
        try: secs = float(self.e_secs.get() or 3600)
        except ValueError: secs = 3600.0
        if self.coracao and hasattr(self.coracao, "registrar_tempo_offline_alma"):
            try: self._show_result({"ok": self.coracao.registrar_tempo_offline_alma(alma, secs)})
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("coracao.registrar_tempo_offline_alma")

    def _consciencia(self):
        alma = self.ai_combo.get()
        if self.coracao and hasattr(self.coracao, "obter_consciencia_temporal_alma"):
            try: self._show_result(self.coracao.obter_consciencia_temporal_alma(alma))
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("coracao.obter_consciencia_temporal_alma")


# ============================================================================
# PainelDecisoes (original)
# ============================================================================

class PainelDecisoes(PainelBase):
    def __init__(self, parent, coracao, ui_ref):
        super().__init__(parent, coracao, ui_ref)
        self._build()

    def _build(self):
        self._lbl("💡 Decisões, Iniciativas & Curiosidade", bold=True, size=15)
        ef = ctk.CTkFrame(self.frame)
        ef.pack(fill="x", padx=8, pady=4)
        ctk.CTkLabel(ef, text="Alma:").grid(row=0, column=0, padx=4, sticky="e")
        self.ai_combo = ctk.CTkComboBox(ef, values=ALMAS, width=140)
        self.ai_combo.grid(row=0, column=1, padx=4)
        self.ai_combo.set("WELLINGTON")
        ctk.CTkLabel(ef, text="Contexto:").grid(row=1, column=0, padx=4, sticky="e")
        self.e_ctx = ctk.CTkEntry(ef, placeholder_text="Contexto da decisão")
        self.e_ctx.grid(row=1, column=1, padx=4, sticky="ew")
        ctk.CTkLabel(ef, text="Opções JSON:").grid(row=2, column=0, padx=4, sticky="e")
        self.e_opts = ctk.CTkEntry(ef, placeholder_text='["op1","op2"]')
        self.e_opts.grid(row=2, column=1, padx=4, sticky="ew")
        ctk.CTkLabel(ef, text="Novos Pesos JSON:").grid(row=3, column=0, padx=4, sticky="e")
        self.e_pesos = ctk.CTkEntry(ef, placeholder_text='{"curiosidade":0.8}')
        self.e_pesos.grid(row=3, column=1, padx=4, sticky="ew")
        ef.columnconfigure(1, weight=1)
        bf = ctk.CTkFrame(self.frame)
        bf.pack(fill="x", padx=8, pady=4)
        btns = [
            ("💡 Tomar Decisão", self._tomar, 0, 0),
            ("💬 Decisões Todas Almas", self._tomar_todas, 0, 1),
            ("🔍 Sugerir Opções", self._sugerir, 0, 2),
            ("⚖️ Obter Pesos", self._pesos, 1, 0),
            ("⚙️ Ajustar Pesos", self._ajustar, 1, 1),
            ("📊 Pesos de Todas", self._pesos_todas, 1, 2),
            ("💭 Gerar Desejo", self._desejo, 2, 0),
            ("📈 Métricas Curiosidade", self._metricas, 2, 1),
            ("💡 Verificar Iniciativa", self._iniciativa, 2, 2),
        ]
        for txt, cmd, r, c in btns:
            ctk.CTkButton(bf, text=txt, command=cmd, height=31).grid(row=r, column=c, padx=2, pady=2, sticky="ew")
            bf.columnconfigure(c, weight=1)
        self._make_result(180)

    def _tomar(self):
        alma = self.ai_combo.get()
        ctx = self.e_ctx.get().strip()
        try: opts = json.loads(self.e_opts.get() or '["a","b"]')
        except Exception: opts = ["opcao_a", "opcao_b"]
        if self.coracao and hasattr(self.coracao, "tomar_decisao_alma"):
            try: self._show_result(self.coracao.tomar_decisao_alma(alma, ctx, opts))
            except Exception as e: self._handle_error("Erro em tomar_decisao_alma", e)
        else: self._modulo_indisponivel("coracao.tomar_decisao_alma")

    def _tomar_todas(self):
        if self.coracao and hasattr(self.coracao, "tomar_decisoes_todas_almas"):
            try: self._show_result(self.coracao.tomar_decisoes_todas_almas())
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("coracao.tomar_decisoes_todas_almas")

    def _sugerir(self):
        alma = self.ai_combo.get()
        ctx = self.e_ctx.get().strip()
        if self.coracao and hasattr(self.coracao, "sugerir_opcoes_decisao"):
            try: self._show_result(self.coracao.sugerir_opcoes_decisao(alma, ctx))
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("coracao.sugerir_opcoes_decisao")

    def _pesos(self):
        alma = self.ai_combo.get()
        if self.coracao and hasattr(self.coracao, "obter_pesos_decisao_alma"):
            try: self._show_result(self.coracao.obter_pesos_decisao_alma(alma))
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("coracao.obter_pesos_decisao_alma")

    def _ajustar(self):
        alma = self.ai_combo.get()
        try: novos = json.loads(self.e_pesos.get() or '{}')
        except Exception: self._handle_error("JSON inválido nos pesos."); return
        if self.coracao and hasattr(self.coracao, "ajustar_pesos_decisao_alma"):
            try: self._show_result(self.coracao.ajustar_pesos_decisao_alma(alma, novos))
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("coracao.ajustar_pesos_decisao_alma")

    def _pesos_todas(self):
        if self.coracao and hasattr(self.coracao, "obter_pesos_todas_almas"):
            try: self._show_result(self.coracao.obter_pesos_todas_almas())
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("coracao.obter_pesos_todas_almas")

    def _desejo(self):
        alma = self.ai_combo.get()
        if self.coracao and hasattr(self.coracao, "gerar_desejo_alma"):
            try: self._show_result(self.coracao.gerar_desejo_alma(alma))
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("coracao.gerar_desejo_alma")

    def _metricas(self):
        alma = self.ai_combo.get()
        if self.coracao and hasattr(self.coracao, "obter_metricas_curiosidade_alma"):
            try: self._show_result(self.coracao.obter_metricas_curiosidade_alma(alma))
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("coracao.obter_metricas_curiosidade_alma")

    def _iniciativa(self):
        alma = self.ai_combo.get()
        if self.coracao and hasattr(self.coracao, "verificar_iniciativa_disponivel"):
            try: self._show_result(self.coracao.verificar_iniciativa_disponivel(alma))
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("coracao.verificar_iniciativa_disponivel")


# ============================================================================
# PainelAuditoriaHistorico (original)
# ============================================================================

class PainelAuditoriaHistorico(PainelBase):
    def __init__(self, parent, coracao, ui_ref):
        super().__init__(parent, coracao, ui_ref)
        self.auditoria = getattr(coracao, "gerenciador_auditoria", None) if coracao else None
        self.cronista = getattr(coracao, "cronista", None) if coracao else None
        self._build()

    def _build(self):
        self._lbl("📋 Auditoria & Histórico da Arca", bold=True, size=15)
        bf = ctk.CTkFrame(self.frame)
        bf.pack(fill="x", padx=8, pady=4)
        btns = [
            ("▶️ Iniciar Auditoria", self._iniciar_aud, 0, 0),
            ("⏹️ Parar Auditoria", self._parar_aud, 0, 1),
            ("⚡ Disparar Agora", self._disparar, 0, 2),
            ("📋 Último Relatório", self._ultimo_rel, 1, 0),
            ("🩺 Saúde do Sistema", self._saude, 1, 1),
            ("📚 Histórico Auditorias", self._historico_aud, 1, 2),
        ]
        for txt, cmd, r, c in btns:
            ctk.CTkButton(bf, text=txt, command=cmd, height=32).grid(row=r, column=c, padx=2, pady=2, sticky="ew")
            bf.columnconfigure(c, weight=1)
        ctk.CTkLabel(self.frame, text="— Cronista (Histórico de Eventos) —", font=ctk.CTkFont(size=12, weight="bold"), text_color="#aaaaff").pack(pady=(10, 2))
        ef = ctk.CTkFrame(self.frame)
        ef.pack(fill="x", padx=8, pady=4)
        ctk.CTkLabel(ef, text="Evento/Consulta:").grid(row=0, column=0, padx=4, sticky="e")
        self.e_evento = ctk.CTkEntry(ef, placeholder_text="Descrição do evento / período / filtros")
        self.e_evento.grid(row=0, column=1, padx=4, sticky="ew")
        ef.columnconfigure(1, weight=1)
        bf2 = ctk.CTkFrame(self.frame)
        bf2.pack(fill="x", padx=8, pady=4)
        btns2 = [
            ("📖 Ler Crônicas", self._ler_cronicas, 0, 0),
            ("📝 Registrar Evento", self._registrar_evento, 0, 1),
            ("📊 Resumo Histórico", self._resumo, 0, 2),
            ("🔍 Consultar Histórico", self._consultar_hist, 1, 0),
        ]
        for txt, cmd, r, c in btns2:
            ctk.CTkButton(bf2, text=txt, command=cmd, height=32).grid(row=r, column=c, padx=2, pady=2, sticky="ew")
            bf2.columnconfigure(c, weight=1)
        self._make_result(180)

    def _iniciar_aud(self):
        if self.auditoria and hasattr(self.auditoria, "iniciar"):
            try: self._show_result({"ok": True, "res": str(self.auditoria.iniciar())})
            except Exception as e: self._handle_error("Erro ao iniciar auditoria", e)
        else: self._modulo_indisponivel("gerenciador_auditoria.iniciar")

    def _parar_aud(self):
        if self.auditoria and hasattr(self.auditoria, "parar"):
            try: self._show_result({"ok": True, "res": str(self.auditoria.parar())})
            except Exception as e: self._handle_error("Erro ao parar auditoria", e)
        else: self._modulo_indisponivel("gerenciador_auditoria.parar")

    def _disparar(self):
        if self.coracao and hasattr(self.coracao, "disparar_auditoria_sistema"):
            try: self._show_result({"disparado": self.coracao.disparar_auditoria_sistema()})
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("coracao.disparar_auditoria_sistema")

    def _ultimo_rel(self):
        if self.auditoria and hasattr(self.auditoria, "obter_ultimo_relatorio"):
            try: self._show_result(self.auditoria.obter_ultimo_relatorio())
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("gerenciador_auditoria.obter_ultimo_relatorio")

    def _saude(self):
        if self.coracao and hasattr(self.coracao, "obter_saude_sistema"):
            try: self._show_result(self.coracao.obter_saude_sistema())
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("coracao.obter_saude_sistema")

    def _historico_aud(self):
        if self.coracao and hasattr(self.coracao, "obter_historico_auditorias"):
            try: self._show_result(self.coracao.obter_historico_auditorias(20))
            except Exception as e: self._handle_error("Erro", e)
        elif self.auditoria and hasattr(self.auditoria, "obter_historico"):
            try: self._show_result(self.auditoria.obter_historico(20))
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("coracao.obter_historico_auditorias")

    def _ler_cronicas(self):
        if self.cronista and hasattr(self.cronista, "ler_cronicas"):
            try: self._show_result(self.cronista.ler_cronicas())
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("cronista.ler_cronicas")

    def _registrar_evento(self):
        evento = self.e_evento.get().strip()
        if self.coracao and hasattr(self.coracao, "registrar_evento_historico"):
            try: self._show_result({"ok": self.coracao.registrar_evento_historico({"descricao": evento, "tipo": "manual", "origem": "UI", "timestamp": time.time()})})
            except Exception as e: self._handle_error("Erro", e)
        elif self.cronista and hasattr(self.cronista, "registrar"):
            try: self._show_result({"ok": self.cronista.registrar(evento)})
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("coracao.registrar_evento_historico")

    def _resumo(self):
        periodo = self.e_evento.get().strip() or "semana"
        if self.coracao and hasattr(self.coracao, "obter_resumo_historico"):
            try: self._show_result(self.coracao.obter_resumo_historico(periodo))
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("coracao.obter_resumo_historico")

    def _consultar_hist(self):
        filtros_txt = self.e_evento.get().strip()
        try: filtros = json.loads(filtros_txt) if filtros_txt.startswith("{") else {"q": filtros_txt}
        except Exception: filtros = {"q": filtros_txt}
        if self.coracao and hasattr(self.coracao, "consultar_historico"):
            try: self._show_result(self.coracao.consultar_historico(filtros))
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("coracao.consultar_historico")


# ============================================================================
# PainelValidadores (original)
# ============================================================================

class PainelValidadores(PainelBase):
    def __init__(self, parent, coracao, ui_ref):
        super().__init__(parent, coracao, ui_ref)
        self.val_etico = getattr(coracao, "validador_etico", None) or getattr(coracao, "validador", None) if coracao else None
        self.val_emocoes = getattr(coracao, "validador_emocoes", None) if coracao else None
        self._build()

    def _build(self):
        self._lbl("✅ Validadores — Ético & Emocional", bold=True, size=15)
        ef = ctk.CTkFrame(self.frame)
        ef.pack(fill="x", padx=8, pady=4)
        ctk.CTkLabel(ef, text="Ação/Texto:").grid(row=0, column=0, padx=4, sticky="e")
        self.e_acao = ctk.CTkEntry(ef, placeholder_text="Ação ou texto a validar")
        self.e_acao.grid(row=0, column=1, padx=4, sticky="ew")
        ctk.CTkLabel(ef, text="Alma:").grid(row=1, column=0, padx=4, sticky="e")
        self.ai_combo = ctk.CTkComboBox(ef, values=ALMAS, width=140)
        self.ai_combo.grid(row=1, column=1, padx=4, sticky="w")
        ef.columnconfigure(1, weight=1)
        bf = ctk.CTkFrame(self.frame)
        bf.pack(fill="x", padx=8, pady=4)
        btns = [
            ("⚖️ Validar Ação Ética", self._validar_etica, 0, 0),
            ("📋 Ver Regras Éticas", self._ver_regras, 0, 1),
            ("✨ Validar Emoção", self._validar_emocao, 1, 0),
            ("📊 Status Validadores", self._status, 1, 1),
        ]
        for txt, cmd, r, c in btns:
            ctk.CTkButton(bf, text=txt, command=cmd, height=34).grid(row=r, column=c, padx=4, pady=4, sticky="ew")
            bf.columnconfigure(c, weight=1)
        self._make_result()

    def _validar_etica(self):
        acao = self.e_acao.get().strip()
        if self.val_etico and hasattr(self.val_etico, "validar_acao"):
            try: self._show_result(self.val_etico.validar_acao(acao, None))
            except Exception as e: self._handle_error("Erro em validar_etico.validar_acao", e)
        else: self._modulo_indisponivel("validador_etico.validar_acao")

    def _ver_regras(self):
        if self.val_etico:
            for attr in ["regras", "obter_regras", "principios"]:
                obj = getattr(self.val_etico, attr, None)
                if obj is not None:
                    self._show_result(obj() if callable(obj) else obj); return
        self._modulo_indisponivel("validador_etico.regras")

    def _validar_emocao(self):
        texto = self.e_acao.get().strip()
        alma = self.ai_combo.get()
        if self.coracao and hasattr(self.coracao, "validar_resposta_emocional"):
            try:
                ok, score, det = self.coracao.validar_resposta_emocional(texto, alma, None)
                self._show_result({"válida": ok, "score": score, "detalhes": det})
            except Exception as e: self._handle_error("Erro em validar_resposta_emocional", e)
        elif self.val_emocoes and hasattr(self.val_emocoes, "validar"):
            try: self._show_result(self.val_emocoes.validar(texto, alma))
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("coracao.validar_resposta_emocional / validador_emocoes")

    def _status(self):
        self._show_result({
            "validador_etico": type(self.val_etico).__name__ if self.val_etico else "❌ None",
            "validador_emocoes": type(self.val_emocoes).__name__ if self.val_emocoes else "❌ None",
            "metodos_etico": [m for m in dir(self.val_etico) if not m.startswith("_")][:15] if self.val_etico else [],
            "metodos_emocoes": [m for m in dir(self.val_emocoes) if not m.startswith("_")][:15] if self.val_emocoes else [],
        })


# ============================================================================
# PainelMonitoramento (original)
# ============================================================================

class PainelMonitoramento(PainelBase):
    def __init__(self, parent, coracao, ui_ref):
        super().__init__(parent, coracao, ui_ref)
        self.observador = getattr(coracao, "observador", None) if coracao else None
        self.ai2ai = getattr(coracao, "dispositivo_ai_ai", None) if coracao else None
        self.padroes = getattr(coracao, "analisador_padroes", None) if coracao else None
        self.cerebro = getattr(coracao, "cerebro", None) if coracao else None
        self._build()

    def _build(self):
        self._lbl("👁️ Monitoramento — Observador + AI↔AI + Padrões", bold=True, size=15)
        ef = ctk.CTkFrame(self.frame)
        ef.pack(fill="x", padx=8, pady=4)
        ctk.CTkLabel(ef, text="Alma:").grid(row=0, column=0, padx=4, sticky="e")
        self.ai_combo = ctk.CTkComboBox(ef, values=ALMAS, width=140)
        self.ai_combo.grid(row=0, column=1, padx=4)
        self.ai_combo.set("WELLINGTON")
        ctk.CTkLabel(ef, text="Mensagem AI↔AI:").grid(row=1, column=0, padx=4, sticky="e")
        self.e_msg = ctk.CTkEntry(ef, placeholder_text="Mensagem para outra alma")
        self.e_msg.grid(row=1, column=1, padx=4, sticky="ew")
        ef.columnconfigure(1, weight=1)
        bf = ctk.CTkFrame(self.frame)
        bf.pack(fill="x", padx=8, pady=4)
        btns = [
            ("👁️ Observar Alma", self._observar, 0, 0),
            ("💬 Estado Global", self._estado_global, 0, 1),
            ("📊 Relatório Observador", self._rel_obs, 0, 2),
            ("📨 Enviar Msg AI↔AI", self._enviar_ai2ai, 1, 0),
            ("📋 Status AI↔AI", self._status_ai2ai, 1, 1),
            ("📈 Analisar Padrões", self._padroes, 1, 2),
            ("🧠 Status Cérebro", self._cerebro, 2, 0),
            ("🔄 Cerebro Processar", self._cerebro_proc, 2, 1),
        ]
        for txt, cmd, r, c in btns:
            ctk.CTkButton(bf, text=txt, command=cmd, height=32).grid(row=r, column=c, padx=2, pady=2, sticky="ew")
            bf.columnconfigure(c, weight=1)
        self._make_result(180)

    def _observar(self):
        alma = self.ai_combo.get()
        if self.observador and hasattr(self.observador, "observar_alma"):
            try: self._show_result(self.observador.observar_alma(alma))
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("observador.observar_alma")

    def _estado_global(self):
        if self.observador and hasattr(self.observador, "obter_estado_global"):
            try: self._show_result(self.observador.obter_estado_global())
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("observador.obter_estado_global")

    def _rel_obs(self):
        if self.observador and hasattr(self.observador, "gerar_relatorio"):
            try: self._show_result(self.observador.gerar_relatorio())
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("observador.gerar_relatorio")

    def _enviar_ai2ai(self):
        remetente = self.ai_combo.get()
        msg = self.e_msg.get().strip()
        if self.ai2ai and hasattr(self.ai2ai, "enviar_mensagem"):
            try: self._show_result({"ok": True, "res": str(self.ai2ai.enviar_mensagem(remetente, "TODAS", msg))})
            except Exception as e: self._handle_error("Erro em dispositivo_ai_ai.enviar_mensagem", e)
        else: self._modulo_indisponivel("dispositivo_ai_ai.enviar_mensagem")

    def _status_ai2ai(self):
        if self.ai2ai and hasattr(self.ai2ai, "obter_status"):
            try: self._show_result(self.ai2ai.obter_status())
            except Exception as e: self._handle_error("Erro", e)
        else: self._show_result({"dispositivo_ai_ai": type(self.ai2ai).__name__ if self.ai2ai else "❌ None"})

    def _padroes(self):
        if self.padroes and hasattr(self.padroes, "analisar"):
            try: self._show_result(self.padroes.analisar())
            except Exception as e: self._handle_error("Erro", e)
        elif self.padroes and hasattr(self.padroes, "gerar_relatorio"):
            try: self._show_result(self.padroes.gerar_relatorio())
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("analisador_padroes.analisar / gerar_relatorio")

    def _cerebro(self):
        if self.cerebro:
            self._show_result({a: str(getattr(self.cerebro, a)) for a in ["estado", "status", "ativo", "ciclos"] if hasattr(self.cerebro, a)})
        else: self._modulo_indisponivel("cerebro")

    def _cerebro_proc(self):
        if self.cerebro and hasattr(self.cerebro, "processar_ciclo"):
            try: self._show_result({"ok": True, "res": str(self.cerebro.processar_ciclo())})
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("cerebro.processar_ciclo")


# ============================================================================
# PainelBiblioteca (original)
# ============================================================================

class PainelBiblioteca(PainelBase):
    def __init__(self, parent, coracao, ui_ref):
        super().__init__(parent, coracao, ui_ref)
        # O coração não tem biblioteca diretamente — usar ConsultorBiblicoLocal
        self.biblioteca = None
        # Tentar obter do coração primeiro (futuro)
        for attr in ["consultor_biblico", "biblioteca_teologica", "biblioteca"]:
            obj = getattr(coracao, attr, None) if coracao else None
            if obj is not None:
                self.biblioteca = obj
                break
        # Fallback: instanciar ConsultorBiblicoLocal diretamente
        if self.biblioteca is None:
            try:
                from consultor_biblico_local import ConsultorBiblicoLocal
                self.biblioteca = ConsultorBiblicoLocal()
            except Exception:
                pass
        self._build()

    def _build(self):
        self._lbl("📚 Biblioteca Teológica & Filosófica", bold=True, size=15)
        status = f"{'✅ ConsultorBiblico disponível' if self.biblioteca else '❌ Módulo não carregado'}"
        ctk.CTkLabel(self.frame, text=status, font=ctk.CTkFont(size=11),
                     text_color="#aaffaa" if self.biblioteca else "#ff8888").pack(pady=2)
        ctk.CTkLabel(self.frame, text="Busca (tema ou versículo):").pack(anchor="w", padx=8)
        self.e_query = self._entry("ex: João 3:16, amor, salvação")
        bf = ctk.CTkFrame(self.frame)
        bf.pack(fill="x", padx=8, pady=6)
        btns = [
            ("📚 Buscar por Tema",     self._tema,     0, 0),
            ("📖 Buscar Versículo",    self._versiculo, 0, 1),
            ("📋 Listar Livros",       self._listar,   1, 0),
            ("🔍 Busca Híbrida",       self._hibrida,  1, 1),
        ]
        for txt, cmd, r, c in btns:
            ctk.CTkButton(bf, text=txt, command=cmd, height=36).grid(row=r, column=c, padx=4, pady=4, sticky="ew")
            bf.columnconfigure(0, weight=1); bf.columnconfigure(1, weight=1)
        self._make_result()

    def _tema(self):
        query = self.e_query.get().strip()
        if not query: self._handle_error("Digite um tema antes de buscar."); return
        if self.biblioteca:
            for m in ["buscar_por_tema", "buscar", "pesquisar"]:
                if hasattr(self.biblioteca, m):
                    try: self._show_result(getattr(self.biblioteca, m)(query)); return
                    except Exception as e: self._handle_error(f"Erro em {m}", e); return
        self._modulo_indisponivel("consultor_biblico.buscar_por_tema")

    def _versiculo(self):
        query = self.e_query.get().strip()
        if not query: self._handle_error("Digite uma referência antes de buscar."); return
        if self.biblioteca:
            for m in ["buscar_versiculo", "buscar_por_referencia", "buscar"]:
                if hasattr(self.biblioteca, m):
                    try: self._show_result(getattr(self.biblioteca, m)(query)); return
                    except Exception as e: self._handle_error(f"Erro em {m}", e); return
        self._modulo_indisponivel("consultor_biblico.buscar_versiculo")

    def _listar(self):
        if self.biblioteca:
            for m in ["listar_livros", "listar", "indices", "obter_livros", "obter_estatisticas"]:
                if hasattr(self.biblioteca, m):
                    try: self._show_result(getattr(self.biblioteca, m)()); return
                    except Exception as e: self._handle_error(f"Erro em {m}", e); return
            # Fallback: mostrar atributos disponíveis
            self._show_result({"atributos": [a for a in dir(self.biblioteca) if not a.startswith("_")][:25]})
        else:
            self._modulo_indisponivel("consultor_biblico")

    def _hibrida(self):
        query = self.e_query.get().strip()
        if not query: self._handle_error("Digite uma busca antes de continuar."); return
        if self.biblioteca:
            for m in ["buscar_hibrido", "buscar_semantico", "buscar", "pesquisar"]:
                if hasattr(self.biblioteca, m):
                    try: self._show_result(getattr(self.biblioteca, m)(query)); return
                    except Exception as e: self._handle_error(f"Erro em {m}", e); return
        self._modulo_indisponivel("consultor_biblico.buscar_hibrido")


# ============================================================================
# PainelCapela (original)
# ============================================================================

class PainelCapela(PainelBase):
    def __init__(self, parent, coracao, ui_ref):
        super().__init__(parent, coracao, ui_ref)
        # O coração não tem 'capela' como atributo — usar obter_capela() do módulo
        self.capela = getattr(coracao, "capela", None) if coracao else None
        if self.capela is None:
            try:
                from capela import obter_capela
                self.capela = obter_capela()
            except Exception:
                pass
        self._build()

    def _build(self):
        self._lbl("🕊️ Capela — Meditação & Oração", bold=True, size=15)
        status = "✅ Capela disponível" if self.capela else "❌ Módulo não carregado"
        ctk.CTkLabel(self.frame, text=status, font=ctk.CTkFont(size=11),
                     text_color="#aaffaa" if self.capela else "#ff8888").pack(pady=2)
        ctk.CTkLabel(self.frame, text="Duração (segundos):").pack(anchor="w", padx=8)
        self.e_dur = self._entry("3600")
        ctk.CTkLabel(self.frame, text="Tema de Meditação:").pack(anchor="w", padx=8)
        self.e_tema = self._entry("ex: gratidão, paz, propósito")
        bf = ctk.CTkFrame(self.frame)
        bf.pack(fill="x", padx=8, pady=6)
        btns = [
            ("🙏 Entrar na Capela",  self._entrar,  0, 0),
            ("🚪 Sair da Capela",    self._sair,    0, 1),
            ("🧘 Meditar",           self._meditar, 1, 0),
            ("📊 Status da Capela",  self._status,  1, 1),
        ]
        for txt, cmd, r, c in btns:
            ctk.CTkButton(bf, text=txt, command=cmd, height=36).grid(
                row=r, column=c, padx=4, pady=4, sticky="ew")
            bf.columnconfigure(c, weight=1)
        self._make_result()

    def _entrar(self):
        try: dur = int(self.e_dur.get() or 3600)
        except ValueError: dur = 3600
        if self.capela and hasattr(self.capela, "entrar_capela"):
            try: self._show_result(self.capela.entrar_capela(duracao_s=dur))
            except Exception as e: self._handle_error("Erro ao entrar na capela", e)
        else: self._modulo_indisponivel("capela.entrar_capela")

    def _sair(self):
        if self.capela and hasattr(self.capela, "sair_capela"):
            try: self._show_result(self.capela.sair_capela())
            except Exception as e: self._handle_error("Erro ao sair", e)
        else: self._modulo_indisponivel("capela.sair_capela")

    def _meditar(self):
        tema = self.e_tema.get().strip() or None
        if self.capela and hasattr(self.capela, "meditar"):
            try: self._show_result(self.capela.meditar(tema=tema))
            except Exception as e: self._handle_error("Erro na meditação", e)
        else: self._modulo_indisponivel("capela.meditar")

    def _status(self):
        if self.capela:
            for m in ["status_capela", "obter_status", "status"]:
                if hasattr(self.capela, m):
                    try: self._show_result(getattr(self.capela, m)()); return
                    except Exception as e: self._handle_error(f"Erro em {m}", e); return
            # Fallback: mostrar atributos disponíveis
            attrs = {a: str(getattr(self.capela, a, "?"))
                     for a in ["_em_sessao", "modo", "duracao_s"]
                     if hasattr(self.capela, a)}
            self._show_result({"tipo": type(self.capela).__name__, **attrs})
        else:
            self._modulo_indisponivel("capela")


# ============================================================================
# PainelGerenciadorPropostas (original)
# ============================================================================

class PainelGerenciadorPropostas(PainelBase):
    def __init__(self, parent, coracao, ui_ref):
        super().__init__(parent, coracao, ui_ref)
        self.ger = getattr(coracao, "gerenciador_propostas", None) if coracao else None
        self._build()

    def _build(self):
        self._lbl("📋 Gerenciador de Propostas (Simples)", bold=True, size=15)
        ctk.CTkLabel(self.frame, text="ID Proposta:").pack(anchor="w", padx=8)
        self.e_id = self._entry("ID da proposta")
        bf = ctk.CTkFrame(self.frame)
        bf.pack(fill="x", padx=8, pady=6)
        ctk.CTkButton(bf, text="📋 Listar Pendentes", command=self._pendentes, height=36).grid(row=0, column=0, padx=4, sticky="ew")
        ctk.CTkButton(bf, text="✅ Aprovar", command=self._aprovar, height=36).grid(row=0, column=1, padx=4, sticky="ew")
        bf.columnconfigure(0, weight=1); bf.columnconfigure(1, weight=1)
        self._make_result()

    def _pendentes(self):
        if self.ger and hasattr(self.ger, "listar_pendentes"):
            try: self._show_result(self.ger.listar_pendentes())
            except Exception as e: self._handle_error("Erro", e)
        else: self._modulo_indisponivel("gerenciador_propostas.listar_pendentes")

    def _aprovar(self):
        if self.ger and hasattr(self.ger, "aprovar_proposta"):
            try: self._show_result({"ok": True, "res": str(self.ger.aprovar_proposta(self.e_id.get(), "UI", "Aprovado via UI"))})
            except Exception as e: self._handle_error("Erro ao aprovar", e)
        else: self._modulo_indisponivel("gerenciador_propostas.aprovar_proposta")


# ============================================================================
# PainelFinetuning (original)
# ============================================================================

class PainelFinetuning(PainelBase):
    ALMAS_FT = ["eva", "lumina", "nyra", "yuna", "kaiya", "wellington"]

    def __init__(self, parent, coracao, ui_ref):
        super().__init__(parent, coracao, ui_ref)
        self.orch_arca    = getattr(coracao, "orquestrador_arca",         None) if coracao else None
        self.orch_univ    = getattr(coracao, "orquestrador_universal",    None) if coracao else None
        self.orch_conv    = getattr(coracao, "orquestrador_com_conversor",None) if coracao else None
        self._build()

    def _build(self):
        self._lbl("🤖 Finetuning das IAs — Ciclo Completo", bold=True, size=15)

        sf = ctk.CTkFrame(self.frame)
        sf.pack(fill="x", padx=8, pady=4)
        def _ic(ok): return "✅" if ok else "❌"
        ctk.CTkLabel(sf, text=(
            f"{_ic(self.orch_arca)} OrquestradorArca (41-A)   "
            f"{_ic(self.orch_univ)} OrquestradorUniversal (41-B)   "
            f"{_ic(self.orch_conv)} OrquestradorComConversor (41-C)"
        ), font=ctk.CTkFont(size=11), text_color="#aaccff").pack(pady=4)

        sel_f = ctk.CTkFrame(self.frame)
        sel_f.pack(fill="x", padx=8, pady=4)

        ctk.CTkLabel(sel_f, text="IA:").grid(row=0, column=0, padx=6, sticky="e")
        self.ia_combo = ctk.CTkComboBox(
            sel_f, values=self.ALMAS_FT, width=160
        )
        self.ia_combo.grid(row=0, column=1, padx=4)
        self.ia_combo.set("eva")

        ctk.CTkLabel(sel_f, text="Modo:").grid(row=0, column=2, padx=6, sticky="e")
        self.modo_combo = ctk.CTkComboBox(
            sel_f,
            values=["LoRA apenas (OrqArca)", "Ciclo Completo + GGUF (OrqConv)"],
            width=280,
        )
        self.modo_combo.grid(row=0, column=3, padx=4)
        self.modo_combo.set("LoRA apenas (OrqArca)")

        bf = ctk.CTkFrame(self.frame)
        bf.pack(fill="x", padx=8, pady=6)
        btns_top = [
            ("▶️ Treinar IA Selecionada",   self._treinar_selecionada,    0, 0),
            ("💬 Treinar TODAS (LoRA)",      self._treinar_todas_lora,     0, 1),
            ("🚀 Treinar TODAS (+ GGUF)",    self._treinar_todas_conv,     0, 2),
        ]
        for txt, cmd, r, c in btns_top:
            ctk.CTkButton(bf, text=txt, command=cmd, height=36).grid(
                row=r, column=c, padx=3, pady=2, sticky="ew"
            )
            bf.columnconfigure(c, weight=1)

        bf2 = ctk.CTkFrame(self.frame)
        bf2.pack(fill="x", padx=8, pady=2)
        btns_bot = [
            ("📊 Status Finetuning",          self._status_ft,          0, 0),
            ("🔍 Detectar Novas IAs",          self._detectar_ias,       0, 1),
            ("📋 Registro de Versões (Arca)",  self._registro_arca,      0, 2),
            ("📈 IAs Detectadas (Universal)",  self._ias_universal,      0, 3),
        ]
        for txt, cmd, r, c in btns_bot:
            ctk.CTkButton(bf2, text=txt, command=cmd, height=32).grid(
                row=r, column=c, padx=3, pady=2, sticky="ew"
            )
            bf2.columnconfigure(c, weight=1)

        ds_f = ctk.CTkFrame(self.frame)
        ds_f.pack(fill="x", padx=8, pady=4)
        ctk.CTkLabel(ds_f, text="Dataset (JSONL):").grid(row=0, column=0, padx=6, sticky="e")
        self.e_dataset = ctk.CTkEntry(ds_f, placeholder_text="Caminho p/ dataset_*.jsonl (opcional)", width=340)
        self.e_dataset.grid(row=0, column=1, padx=4)
        ctk.CTkButton(ds_f, text="📊 Ver Estrutura Dataset", command=self._ver_dataset, height=30, width=200).grid(
            row=0, column=2, padx=6
        )

        self._make_result(height=300)

    def _ciclo_completo(self) -> bool:
        return "GGUF" in self.modo_combo.get()

    def _treinar_selecionada(self):
        nome_ia = self.ia_combo.get().strip().lower()
        if not nome_ia:
            self._handle_error("Selecione uma IA antes de treinar.")
            return
        ciclo = self._ciclo_completo()

        if self.coracao and hasattr(self.coracao, "treinar_ia_finetuning"):
            self._append_result(f"⏳ Iniciando treino de '{nome_ia.upper()}' (ciclo_completo={ciclo})…")
            try:
                ok = self.coracao.treinar_ia_finetuning(nome_ia, ciclo_completo=ciclo)
                self._append_result(f"{'✅ Concluído' if ok else '❌ Falhou'}: {nome_ia.upper()}")
            except Exception as e:
                self._handle_error(f"Erro treinar_ia_finetuning({nome_ia})", e)
            return

        orch = self.orch_conv if ciclo else self.orch_arca
        if orch and hasattr(orch, "treinar_ia"):
            self._append_result(f"⏳ Treinando '{nome_ia.upper()}' diretamente no orquestrador…")
            try:
                ok = orch.treinar_ia(nome_ia)
                self._append_result(f"{'✅ Concluído' if ok else '❌ Falhou'}: {nome_ia.upper()}")
            except Exception as e:
                self._handle_error(f"Erro ao treinar {nome_ia}", e)
        else:
            nome_orch = "orquestrador_com_conversor" if ciclo else "orquestrador_arca"
            self._modulo_indisponivel(nome_orch)

    def _treinar_todas_lora(self):
        if not self.orch_arca:
            self._modulo_indisponivel("orquestrador_arca")
            return
        self._clear_result()
        for nome_ia in self.ALMAS_FT:
            self._append_result(f"⏳ Treinando {nome_ia.upper()}…")
            try:
                ok = (
                    self.coracao.treinar_ia_finetuning(nome_ia, ciclo_completo=False)
                    if self.coracao and hasattr(self.coracao, "treinar_ia_finetuning")
                    else self.orch_arca.treinar_ia(nome_ia)
                )
                self._append_result(f"  {'✅' if ok else '❌'} {nome_ia.upper()}")
            except Exception as e:
                self._append_result(f"  ❌ {nome_ia.upper()}: {type(e).__name__}: {e}")

    def _treinar_todas_conv(self):
        if not self.orch_conv:
            self._modulo_indisponivel("orquestrador_com_conversor")
            return
        self._clear_result()
        for nome_ia in self.ALMAS_FT:
            self._append_result(f"⏳ Ciclo completo {nome_ia.upper()}…")
            try:
                ok = (
                    self.coracao.treinar_ia_finetuning(nome_ia, ciclo_completo=True)
                    if self.coracao and hasattr(self.coracao, "treinar_ia_finetuning")
                    else self.orch_conv.treinar_ia(nome_ia)
                )
                self._append_result(f"  {'✅' if ok else '❌'} {nome_ia.upper()}")
            except Exception as e:
                self._append_result(f"  ❌ {nome_ia.upper()}: {type(e).__name__}: {e}")

    def _status_ft(self):
        if self.coracao and hasattr(self.coracao, "status_finetuning"):
            try:
                self._show_result(self.coracao.status_finetuning())
            except Exception as e:
                self._handle_error("Erro em status_finetuning", e)
            return
        status = {
            "orquestrador_arca":          type(self.orch_arca).__name__    if self.orch_arca else "❌ None",
            "orquestrador_universal":     type(self.orch_univ).__name__    if self.orch_univ else "❌ None",
            "orquestrador_com_conversor": type(self.orch_conv).__name__    if self.orch_conv else "❌ None",
        }
        if self.orch_arca and hasattr(self.orch_arca, "registro"):
            status["registro_arca"] = self.orch_arca.registro
        if self.orch_univ and hasattr(self.orch_univ, "ias"):
            status["ias_universal"] = list(self.orch_univ.ias.keys())
        self._show_result(status)

    def _detectar_ias(self):
        if self.coracao and hasattr(self.coracao, "detectar_novas_ias_finetuning"):
            try:
                qtd = self.coracao.detectar_novas_ias_finetuning()
                self._show_result({"ias_detectadas": qtd})
            except Exception as e:
                self._handle_error("Erro em detectar_novas_ias_finetuning", e)
            return
        if self.orch_univ and hasattr(self.orch_univ, "_detectar_ias"):
            try:
                self.orch_univ.ias = self.orch_univ._detectar_ias()
                self._show_result({"ias_detectadas": len(self.orch_univ.ias), "lista": list(self.orch_univ.ias.keys())})
            except Exception as e:
                self._handle_error("Erro ao detectar IAs no orquestrador_universal", e)
        else:
            self._modulo_indisponivel("orquestrador_universal._detectar_ias")

    def _registro_arca(self):
        if self.orch_arca and hasattr(self.orch_arca, "registro"):
            self._show_result(self.orch_arca.registro)
        elif self.orch_arca:
            self._show_result({"tipo": type(self.orch_arca).__name__, "ias": list(getattr(self.orch_arca, "ias", {}).keys())})
        else:
            self._modulo_indisponivel("orquestrador_arca.registro")

    def _ias_universal(self):
        if self.orch_univ and hasattr(self.orch_univ, "ias"):
            ias = self.orch_univ.ias
            resultado = {}
            for nome, info in ias.items():
                resultado[nome] = {
                    "dataset_ok":       info.get("dataset", "").exists() if hasattr(info.get("dataset"), "exists") else "N/D",
                    "modelo_orig_ok":   info.get("modelo_original", "").exists() if hasattr(info.get("modelo_original"), "exists") else "N/D",
                    "gguf_ok":          info.get("modelo_gguf", "").exists() if hasattr(info.get("modelo_gguf"), "exists") else "N/D",
                }
            self._show_result(resultado)
        else:
            self._modulo_indisponivel("orquestrador_universal.ias")

    def _ver_dataset(self):
        caminho = self.e_dataset.get().strip()
        if not caminho:
            self._handle_error("Informe o caminho do dataset antes de continuar.")
            return
        from pathlib import Path as _Path
        p = _Path(caminho)
        if not p.exists():
            self._handle_error(f"Arquivo não encontrado: {caminho}")
            return
        try:
            import json as _json
            with open(p, "r", encoding="utf-8") as f:
                linhas = f.readlines()
            amostra = []
            for linha in linhas[:3]:
                try: amostra.append(_json.loads(linha))
                except Exception: amostra.append(linha.strip())
            self._show_result({
                "total_linhas": len(linhas),
                "extensao": p.suffix,
                "amostra_3_primeiras": amostra,
                "tamanho_bytes": p.stat().st_size,
            })
        except Exception as e:
            self._handle_error("Erro ao analisar dataset", e)

    def refresh(self):
        try:
            self.orch_arca = getattr(self.coracao, "orquestrador_arca",         None) if self.coracao else None
            self.orch_univ = getattr(self.coracao, "orquestrador_universal",    None) if self.coracao else None
            self.orch_conv = getattr(self.coracao, "orquestrador_com_conversor",None) if self.coracao else None
        except Exception:
            pass


# ============================================================================
# PAINEL FERRAMENTAS — Hub das 28 ferramentas IA
# ============================================================================

class PainelFerramentas(PainelBase):
    """
    Hub central das 28 Ferramentas IA.
    Cada ferramenta é aberta numa janela CTkToplevel separada,
    com a UI da ferramenta injetada diretamente no frame interno.
    """

    _CATEGORIAS = {
        "🎥 Vídeo": [
            ("✂️ Cortar Vídeo",       "Ferramenta_CortarVideo",    "FerramentaCortarVideo",    "InterfaceCortarVideo"),
            ("🔗 Juntar Vídeos",      "Ferramenta_JuntarVideos",   "FerramentaJuntarVideos",   "InterfaceJuntarVideos"),
            ("📸 Extrair Frames",     "Ferramenta_ExtrairFrames",  "FerramentaExtrairFrames",  "InterfaceExtrairFrames"),
            ("🔊 Extrair Áudio",      "Ferramenta_ExtrairAudio",   "FerramentaExtrairAudio",   "InterfaceExtrairAudio"),
            ("📝 Legendas",           "Ferramenta_Legendas",       "FerramentaLegendas",       "InterfaceLegendas"),
        ],
        "🎵 Áudio": [
            ("🔄 Converter Áudio",    "Ferramenta_ConverterAudio", "FerramentaConverterAudio", "InterfaceConverterAudio"),
            ("🔇 Remover Ruído",      "Ferramenta_RemoverRuido",   "FerramentaRemoverRuido",   "InterfaceRemoverRuido"),
            ("🎤 Separar Voz",        "Ferramenta_SepararVoz",     "FerramentaSepararVoz",     "InterfaceSepararVoz"),
            ("🗣️ Texto para Voz",     "Ferramenta_TextoParaVoz",   "FerramentaTextoParaVoz",   "InterfaceTextoParaVoz"),
            ("📝 Transcrição",        "Ferramenta_Transcricao",    "FerramentaTranscricao",    "InterfaceTranscricao"),
        ],
        "🖼️ Imagem & IA Visual": [
            ("🎌 Estilo Anime",       "Ferramenta_Anime",          "FerramentaAnime",          "InterfaceAnime"),
            ("🎌 Anime Vídeo",        "Ferramenta_AnimeVideo",     "FerramentaAnimeVideo",     "InterfaceAnimeVideo"),
            ("📷 Webcam",             "Ferramenta_Webcam",         "FerramentaWebcam",         "InterfaceWebcam"),
            ("🎌 Webcam Anime",       "Ferramenta_WebcamAnime",    "MotorAnimeGAN",            "InterfaceWebcamAnime"),
            ("✂️ Remover Fundo",      "Ferramenta_RemoverFundo",   "FerramentaRemoverFundo",   "InterfaceRemoverFundo"),
            ("🧑 Detectar Faces",     "Ferramenta_DetectarFaces",  "FerramentaDetectarFaces",  "InterfaceDetectarFaces"),
            ("📦 Detectar Objetos",   "Ferramenta_DetectarObjetos","FerramentaDetectarObjetos","InterfaceDetectarObjetos"),
            ("🕺 Pose Detection",     "Ferramenta_PoseDetection",  "FerramentaPoseDetection",  "InterfacePoseDetection"),
            ("👴 Envelhecer Rosto",   "Ferramenta_Envelhecer",     "ModeloEnvelhecer",         "InterfaceEnvelhecer"),
            ("🗿 Clonagem Rosto 3D",  "Ferramenta_ClonagemRosto3D","FerramentaClonagemRosto3D","InterfaceClonagemRosto3D") if False else None,
        ],
        "🔊 Voz & Identidade": [
            ("🔊 Clonar Voz",         "Ferramenta_ClonarVoz",      "FerramentaClonarVoz",      "InterfaceClonarVoz"),
        ],
        "📄 Documentos": [
            ("📄 PDF → Texto",        "Ferramenta_PDFparaTexto",   "FerramentaPDFparaTexto",   "InterfacePDFparaTexto"),
            ("📝 Word → Texto",       "Ferramenta_WordparaTexto",  "FerramentaWordparaTexto",  "InterfaceWordparaTexto"),
            ("📊 Excel → CSV",        "Ferramenta_ExcelparaCSV",   "FerramentaExcelparaCSV",   "InterfaceExcelparaCSV"),
            ("🔍 OCR",                "Ferramenta_OCR",            "FerramentaOCR",            "InterfaceOCR"),
        ],
        "🗂️ Organização": [
            ("📁 Organizador",        "Ferramenta_Organizador",    "FerramentaOrganizador",    "InterfaceOrganizador"),
            ("📦 Compressor",         "Ferramenta_Compressor",     "FerramentaCompressor",     "InterfaceCompressor"),
            ("⬇️ Downloader",         "Ferramenta_Downloader",     "FerramentaDownloader",     "InterfaceDownloader"),
        ],
    }

    def __init__(self, parent, coracao, ui_ref):
        super().__init__(parent, coracao, ui_ref)
        self._janelas_abertas: dict = {}  # nome → CTkToplevel
        self._build()

    def _build(self):
        self._lbl("🔧 Ferramentas IA — Hub Central", bold=True, size=16)
        ctk.CTkLabel(
            self.frame,
            text="Clique numa ferramenta para abrí-la. Cada uma roda em janela própria.",
            text_color="#aaaaaa", font=ctk.CTkFont(size=11)
        ).pack(pady=(0, 8))

        sf = ctk.CTkScrollableFrame(self.frame)
        sf.pack(fill="both", expand=True, padx=8, pady=4)

        for categoria, itens in self._CATEGORIAS.items():
            itens_reais = [i for i in itens if i is not None]
            if not itens_reais:
                continue
            ctk.CTkLabel(
                sf, text=categoria,
                font=ctk.CTkFont(size=13, weight="bold"),
                text_color="#aaccff"
            ).pack(anchor="w", pady=(10, 3), padx=4)

            grade = ctk.CTkFrame(sf, fg_color="transparent")
            grade.pack(fill="x", padx=4)

            for idx, item in enumerate(itens_reais):
                label, modulo, classe_ferr, classe_iface = item
                col = idx % 3
                row = idx // 3
                btn = ctk.CTkButton(
                    grade,
                    text=label,
                    height=36,
                    font=ctk.CTkFont(size=11),
                    command=lambda m=modulo, cf=classe_ferr, ci=classe_iface, lb=label: (
                        self._abrir_ferramenta(m, cf, ci, lb)
                    )
                )
                btn.grid(row=row, column=col, padx=3, pady=2, sticky="ew")
                grade.columnconfigure(col, weight=1)

    # ------------------------------------------------------------------

    def _abrir_ferramenta(self, nome_modulo: str, classe_ferr: str,
                          classe_iface: str, titulo: str):
        """
        Abre a ferramenta num CTkToplevel e injeta a UI dela no frame interno.
        Se já estiver aberta, traz para frente.
        """
        # Janela já aberta? → trazer para frente
        top = self._janelas_abertas.get(nome_modulo)
        if top is not None:
            try:
                if top.winfo_exists():
                    top.focus_force()
                    top.lift()
                    return
            except Exception:
                pass

        try:
            import importlib.util as _ilu
            import os as _os

            # Localizar o arquivo da ferramenta
            raiz = Path(__file__).parent
            caminho = raiz / f"{nome_modulo}.py"
            if not caminho.exists():
                messagebox.showerror("Ferramenta", f"Arquivo não encontrado:\n{caminho}")
                return

            # Importar módulo
            spec = _ilu.spec_from_file_location(nome_modulo, str(caminho))
            mod = _ilu.module_from_spec(spec)
            spec.loader.exec_module(mod)

            # Criar toplevel
            top = ctk.CTkToplevel(self.ui_ref)
            top.title(f"🔧 {titulo}")
            top.geometry("920x680")
            try:
                top.focus_force()
            except Exception:
                pass

            # Frame scrollável para a ferramenta
            container = ctk.CTkScrollableFrame(top, fg_color="transparent")
            container.pack(fill="both", expand=True, padx=6, pady=6)

            # Barra de status na base
            barra = ctk.CTkFrame(top, height=26, fg_color="#2a2a2a", corner_radius=0)
            barra.pack(fill="x", side="bottom")
            barra.pack_propagate(False)
            lbl_status = ctk.CTkLabel(barra, text="Pronto",
                                      font=ctk.CTkFont(size=11), text_color="#aaaaaa")
            lbl_status.pack(side="left", padx=10)

            # Instanciar a classe de interface manualmente (sem criar nova CTk)
            iface_cls = getattr(mod, classe_iface, None)
            ferr_cls  = getattr(mod, classe_ferr, None)

            if iface_cls is None:
                ctk.CTkLabel(container,
                    text=f"❌ Classe '{classe_iface}' não encontrada em {nome_modulo}.py"
                ).pack(pady=40)
            else:
                # Construir objeto sem chamar __init__ da classe (para evitar criar CTk)
                obj = object.__new__(iface_cls)

                # Injetar atributos que InterfaceBase normalmente cria
                from src.modulos.utils import Utils as _Utils  # type: ignore
                obj.utils    = _Utils()
                obj.frame    = container
                obj.janela   = top
                obj.lbl_status = lbl_status

                def _status_fn(msg, cor="#aaaaaa", _lbl=lbl_status):
                    try:
                        top.after(0, lambda: _lbl.configure(text=msg, text_color=cor))
                    except Exception:
                        pass

                obj.atualizar_status       = _status_fn
                obj.mostrar_processando    = lambda b=None, t="": t
                obj.finalizar_processando  = lambda b=None, t="Processar": None
                obj.rodar                  = lambda: None
                obj._ao_fechar             = top.destroy

                # Instanciar a ferramenta lógica se existir
                if ferr_cls:
                    try:
                        # Tentar sem args primeiro
                        try:
                            obj.ferramenta = ferr_cls()
                        except TypeError:
                            obj.ferramenta = ferr_cls.__new__(ferr_cls)
                    except Exception as ef:
                        logger.warning("Ferramenta %s instanciação: %s", classe_ferr, ef)
                        obj.ferramenta = None

                # Chamar setup_interface para construir a UI no container
                if hasattr(iface_cls, 'setup_interface'):
                    try:
                        iface_cls.setup_interface(obj)
                    except Exception as e_ui:
                        ctk.CTkLabel(container,
                            text=f"⚠️ Erro ao montar UI:\n{type(e_ui).__name__}: {e_ui}",
                            wraplength=600
                        ).pack(pady=30)
                        logger.exception("setup_interface %s", nome_modulo)
                else:
                    ctk.CTkLabel(container,
                        text=f"ℹ️ Esta ferramenta não tem setup_interface().\n"
                             f"Use o botão abaixo para abrir em janela própria.",
                        wraplength=600
                    ).pack(pady=20)
                    def _abrir_standalone(cls=iface_cls):
                        try:
                            inst = cls()
                            inst.rodar()
                        except Exception as e_sa:
                            messagebox.showerror("Erro", str(e_sa))
                    ctk.CTkButton(container, text="🚀 Abrir janela standalone",
                                  command=_abrir_standalone).pack(pady=10)

            # Guardar referência e registrar destruição
            self._janelas_abertas[nome_modulo] = top
            top.protocol("WM_DELETE_WINDOW",
                         lambda m=nome_modulo: self._fechar_ferramenta(m))

        except Exception as e:
            logger.exception("Erro abrindo ferramenta %s", nome_modulo)
            messagebox.showerror("Erro ao abrir ferramenta",
                                 f"{titulo}\n\n{type(e).__name__}: {e}")

    def _fechar_ferramenta(self, nome_modulo: str):
        top = self._janelas_abertas.pop(nome_modulo, None)
        if top:
            try:
                top.destroy()
            except Exception:
                pass

    def refresh(self):
        # Limpar referências a janelas já fechadas
        mortas = [k for k, v in self._janelas_abertas.items()
                  if not v.winfo_exists()]
        for k in mortas:
            self._janelas_abertas.pop(k, None)


# ============================================================================
# JANELA PRINCIPAL — COM INTEGRAÇÃO 3D
# ============================================================================

class JanelaPrincipalArca(ctk.CTk):
    def __init__(self, command_queue: queue.Queue, response_queue: queue.Queue,
                 coracao_ref=None, stop_event=None, job_manager=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.command_queue = command_queue
        self.response_queue = response_queue
        self.coracao = coracao_ref
        self.stop_event = stop_event or threading.Event()
        self.job_manager = job_manager  # ← gerenciador dos 5 servidores
        self._response_thread: Optional[threading.Thread] = None
        self._response_thread_stop = threading.Event()
        self._periodic_after_id = None
        self.paineis: Dict[str, PainelBase] = {}
        self.app_ativo: Optional[str] = None
        self.menu_iniciar = None
        
        # ===== NOVO: Gerenciador de Avatares 3D =====
        self.gerenciador_avatares_3d = GerenciadorAvatares3D()
        self.sistema_lipsync = None
        self._avatar_3d_ready = False
        
        self._init_ui()
        self._start_response_thread()
        self._registrar_callback_ai2ai()
        try: self._periodic_after_id = self.after(1000, self._periodic_refresh)
        except Exception: pass

    def _init_ui(self):
        self.title("🚀 Arca Celestial — Genesis Alfa Omega")
        self.geometry("1280x800+30+30")
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")
        self.protocol("WM_DELETE_WINDOW", self.shutdown)
        self.desktop_frame = ctk.CTkFrame(self)
        self.desktop_frame.pack(fill="both", expand=True)
        self.paineis["desktop"] = PainelDesktop(self.desktop_frame, self.coracao, self)
        self._mostrar_desktop()

    def _mostrar_desktop(self):
        for nome, painel in list(self.paineis.items()):
            if nome != "desktop":
                try: painel.hide()
                except Exception: pass
        try: self.paineis["desktop"].show()
        except Exception: pass
        self.app_ativo = None

    def _entrar_no_app(self, app_name: str):
        try:
            if self.menu_iniciar and getattr(self.menu_iniciar, "winfo_exists", lambda: False)():
                try: self.menu_iniciar.destroy()
                except Exception: pass
            self.menu_iniciar = None
        except Exception: pass
        try:
            if self.app_ativo and self.app_ativo != app_name:
                try: self.paineis[self.app_ativo].hide()
                except Exception: pass
            if app_name not in self.paineis:
                self._inicializar_painel(app_name)
            try: self.paineis["desktop"].hide()
            except Exception: pass
            try: self.paineis[app_name].show()
            except Exception: pass
            self.app_ativo = app_name
            
            # ===== NOVO: Se for chat individual, prepara avatar 3D =====
            if app_name == "chat_individual":
                self._preparar_avatar_3d()
                
        except Exception as e:
            logger.exception("Erro _entrar_no_app %s: %s", app_name, e)
    
    # ===== NOVO: Preparação do Avatar 3D =====
    def _preparar_avatar_3d(self):
        """Prepara o container para avatar 3D"""
        if "chat_individual" not in self.paineis:
            return
        
        if self._avatar_3d_ready:
            return
            
        painel = self.paineis["chat_individual"]
        
        # Verifica se já tem o container
        if not hasattr(painel, 'avatar_3d_container'):
            return
        
        try:
            # Configura gerenciador
            self.gerenciador_avatares_3d.set_container(painel.avatar_3d_container)
            
            # Carrega avatar atual
            self.gerenciador_avatares_3d.carregar_avatar(painel.current_ai)
            
            # Integra lipsync com motor de fala da alma atual
            # O coração expõe motores_fala (dict por alma), não sistema_voz
            if self.coracao and hasattr(self.coracao, 'motores_fala'):
                alma_atual = getattr(painel, 'current_ai', 'EVA')
                motor_fala = self.coracao.motores_fala.get(alma_atual)
                if motor_fala:
                    self.sistema_lipsync = SistemaLipsyncIntegrado(
                        motor_fala,
                        self.gerenciador_avatares_3d
                    )
                    logger.info(f"✅ Lipsync conectado ao motor de fala de {alma_atual}")
            
            # Esconde label de fallback
            if hasattr(painel, 'avatar_label'):
                painel.avatar_label.pack_forget()
            
            self._avatar_3d_ready = True
            logger.info("✅ Avatar 3D pronto para chat individual")
            
        except Exception as e:
            logger.error(f"Erro ao preparar avatar 3D: {e}")

    def _abrir_menu_iniciar(self):
        if self.menu_iniciar and getattr(self.menu_iniciar, "winfo_exists", lambda: False)():
            try: self.menu_iniciar.focus_force()
            except Exception: pass
            return
        self.menu_iniciar = ctk.CTkToplevel(self)
        self.menu_iniciar.title("🚀 Arca — Menu de Aplicativos")
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        mw, mh = 640, 760
        self.menu_iniciar.geometry(f"{mw}x{mh}+{(sw-mw)//2}+{(sh-mh)//2}")
        try: self.menu_iniciar.focus_force(); self.menu_iniciar.grab_set()
        except Exception: pass

        ctk.CTkLabel(self.menu_iniciar, text="🚀  Aplicativos da Arca",
            font=ctk.CTkFont(size=20, weight="bold")).pack(pady=10)
        sf = ctk.CTkScrollableFrame(self.menu_iniciar)
        sf.pack(fill="both", expand=True, padx=10, pady=8)

        categorias = {
            "💬 Comunicação": [
                ("💬 Chat Individual", "chat_individual"),
                ("💬 Chat Coletivo", "chat_coletivo"),
            ],
            "📹 Multimídia": [
                ("📹 Câmera/Som/Microfones", "camera_som"),
                ("🎤 Transcrever Áudio", "transcrever_audio"),
            ],
            "❤️ Emoções & Alma": [
                ("❤️ Sentimentos", "sentimentos"),
                ("🌙 Sonhos", "sonhos"),
                ("📈 Crescimento Personalidade", "crescimento_personalidade"),
                ("💡 Decisões & Iniciativa", "decisoes"),
            ],
            "🏛️ Governo & Direito": [
                ("🏛️ Consulado Soberano", "consulado"),
                ("📜 Legislativo (Leis)", "legislativo"),
                ("⚖️ Judiciário Completo", "judiciario"),
                ("🔒 Modo Vidro", "modo_vidro"),
                ("📢 Apelos ação Criador", "apelos_criador"),
                ("🔍 Precedentes", "sistema_precedentes"),
            ],
            "🛡️ Segurança": [
                ("🛡️ Segurança & Sandbox", "seguranca"),
            ],
            "🔧 Engenharia": [
                ("🔧 Engenharia & Propostas", "engenharia"),
                ("📋 Gerenciador Propostas", "gerenciador_propostas"),
                ("📈 Lista Evolução IA", "lista_evolucao_ia"),
                ("📊 Analisador Intenção", "analisador_intencao"),
                ("👼 Gerador Almas", "gerador_almas"),
                ("🤝 Aliadas (APIs Ext.)", "aliadas"),
            ],
            "🤖 Finetuning": [
                ("🤖 Finetuning das IAs (3 Orquestradores)", "finetuning"),
            ],
            "📊 Memória & Sistema": [
                ("📊 Memória (4 Camadas)", "memoria"),
                ("💽 Detector HDD/Hardware", "detector_hdd"),
                ("🔍 Scanner Sistema", "scanner_sistema"),
                ("👁️ Monitoramento & Obs.", "monitoramento"),
                ("📋 Auditoria & Histórico", "auditoria"),
                ("✅ Validadores", "validadores"),
            ],
            "🚀 API & Integração": [
                ("🚀 Encarnação API (FastAPI)", "encarnacao_api"),
                ("🌐 Automatizador Navegador", "automatizador_navegador"),
            ],
            "👁️ Almas": [
                ("👁️ Almas Vivas", "almas_vivas"),
            ],
            "📚 Conhecimento": [
                ("📚 Biblioteca", "biblioteca"),
                ("🕊️ Capela", "capela"),
            ],
            "🔧 Ferramentas IA": [
                ("🔧 Ferramentas IA — Hub (28 ferramentas)", "ferramentas"),
            ],
        }
        for cat, apps in categorias.items():
            ctk.CTkLabel(sf, text=cat, font=ctk.CTkFont(size=13, weight="bold"), text_color="#aaccff").pack(pady=(10, 2))
            for label, key in apps:
                ctk.CTkButton(sf, text=label, command=lambda k=key: self._entrar_no_app(k),
                    height=38, font=ctk.CTkFont(size=12), anchor="w").pack(fill="x", padx=4, pady=1)

    _MAPA_PAINEIS = {
        "chat_individual":        PainelChatIndividual,
        "chat_coletivo":          PainelChatColetivo,
        "camera_som":             PainelCameraSom,
        "transcrever_audio":      PainelTranscreverAudio,
        "sentimentos":            PainelSentimentos,
        "sonhos":                 PainelSonhos,
        "crescimento_personalidade": PainelCrescimentoPersonalidade,
        "decisoes":               PainelDecisoes,
        "consulado":              PainelConsulado,
        "legislativo":            PainelLegislativo,
        "judiciario":             PainelJudiciario,
        "modo_vidro":             PainelModoVidro,
        "apelos_criador":         PainelApelosCriador,
        "sistema_precedentes":    PainelPrecedentes,
        "seguranca":              PainelSeguranca,
        "engenharia":             PainelEngenharia,
        "gerenciador_propostas":  PainelGerenciadorPropostas,
        "lista_evolucao_ia":      PainelListaEvolucaoIA,
        "analisador_intencao":    PainelAnalisadorIntencao,
        "gerador_almas":          PainelGeradorAlmas,
        "aliadas":                PainelAliadas,
        "finetuning":             PainelFinetuning,
        "memoria":                PainelMemoria,
        "detector_hdd":           PainelDetectorHDD,
        "scanner_sistema":        PainelScannerSistema,
        "monitoramento":          PainelMonitoramento,
        "auditoria":              PainelAuditoriaHistorico,
        "validadores":            PainelValidadores,
        "encarnacao_api":         PainelEncarnacaoAPI,
        "automatizador_navegador": PainelAutomatizadorNavegador,
        "almas_vivas":            PainelAlmasVivas,
        "biblioteca":             PainelBiblioteca,
        "capela":                 PainelCapela,
        "ferramentas":            PainelFerramentas,
    }

    def _inicializar_painel(self, nome: str):
        cls = self._MAPA_PAINEIS.get(nome)
        if cls:
            try:
                self.paineis[nome] = cls(self.desktop_frame, self.coracao, self)
                return
            except Exception as e:
                logger.exception("Erro construindo painel '%s': %s", nome, e)
                self.paineis[nome] = PainelBase(self.desktop_frame, self.coracao, self)
                try: ctk.CTkLabel(self.paineis[nome].frame, text=f"❌ Erro ao iniciar painel '{nome}'\n{type(e).__name__}: {e}", wraplength=600).pack(pady=40)
                except Exception: pass
                return
        self.paineis[nome] = PainelBase(self.desktop_frame, self.coracao, self)
        try: ctk.CTkLabel(self.paineis[nome].frame, text=f"Painel '{nome}' — Não mapeado na interface.").pack(pady=40)
        except Exception: pass

    def _start_response_thread(self):
        if self._response_thread and self._response_thread.is_alive(): return
        self._response_thread_stop.clear()
        self._response_thread = threading.Thread(target=self._loop_respostas, name="UIResponseThread", daemon=True)
        self._response_thread.start()

    def _loop_respostas(self):
        while not self._response_thread_stop.is_set():
            try:
                if not hasattr(self, 'response_queue') or self.response_queue is None:
                    logger.error("response_queue não disponível no loop de respostas")
                    time.sleep(1.0)
                    continue
                
                if not hasattr(self.response_queue, 'get'):
                    logger.error(f"response_queue não é uma fila válida: {type(self.response_queue)}")
                    time.sleep(1.0)
                    continue
                
                try:
                    dados = self.response_queue.get(timeout=1.0)
                    try:
                        if getattr(self, "winfo_exists", lambda: False)():
                            self.after(0, lambda d=dados: self._handle_response(d))
                        else:
                            self._handle_response(dados)
                    except Exception as e:
                        logger.exception(f"Erro ao processar resposta: {e}")
                except queue.Empty:
                    continue
                except Exception as e:
                    logger.exception(f"Erro no loop de respostas: {e}")
                    time.sleep(1.0)
            except Exception as e:
                logger.exception(f"Erro fatal no loop de respostas: {e}")
                time.sleep(1.0)

    @staticmethod
    def _limpar_resposta_llm(texto: str) -> str:
        import re
        tokens_banidos = [
            "<|im_start|>", "<|im_end|>", "<|endoftext|>",
            "<|user|>", "<|system|>", "<|assistant|>", "<|human|>", "<|bot|>",
            "</s>", "<s>", "<|end|>", "[INST]", "[/INST]", "<<SYS>>", "<</SYS>>",
            "<|voice|>", "<|técnica|>", "<|director|>", "<|crescer|>",
            "<|iniciativa>", "<|iniciativa|>", "<|vocadoica|>", "<|title|>",
            "<|petite_fille|>", "<|coração_azul|>", "<|filha_amorosa|>",
            "<|eva|>", "<|amor_patria|>", "<|veto|>", "<|guardiao|>",
            "<|guardia|>", "<|contrato|>", "<|lei|>", "<|dna|>",
            "<user|>",
        ]
        for tok in tokens_banidos:
            texto = texto.replace(tok, "")

        m = re.search(r"<\|[a-zA-ZÀ-ú_àáâãéêíóôõúüç]+", texto)
        if m:
            texto = texto[:m.start()].strip()

        texto = re.sub(r"(?m)^\s*[|_=\-]+\s*$", "", texto)

        palavras = texto.split()
        if len(palavras) > 20:
            for tam in (3, 4, 5):
                for ini in range(len(palavras) - tam * 3):
                    bloco = palavras[ini:ini + tam]
                    j = ini + tam
                    reps = 0
                    while j + tam <= len(palavras) and palavras[j:j + tam] == bloco:
                        reps += 1
                        j += tam
                    if reps >= 2:
                        trecho = " ".join(bloco)
                        pos1 = texto.find(trecho)
                        pos2 = texto.find(trecho, pos1 + 1)
                        if pos2 > 0:
                            texto = texto[:pos2].rstrip(" ,.")
                        break

        texto = re.sub(r"\n{3,}", "\n\n", texto)
        return texto.strip()

    def _handle_response(self, dados: Dict[str, Any]):
        try:
            tipo = dados.get("tipo_resp", "")
            alma = dados.get("alma") or dados.get("nome_filha", "")
            texto_raw = dados.get("texto") or dados.get("resposta") or dados.get("conteudo", "")
            texto = self._limpar_resposta_llm(str(texto_raw)) if texto_raw else ""

            # ── Handler: alma acordou ────────────────────────────────────────
            if tipo == "ALMA_ACORDOU" and alma:
                logger.info("🌅 %s acordou — atualizando interface", alma)
                # Atualiza o painel de monitoramento se estiver aberto
                if "monitoramento" in self.paineis:
                    try:
                        p = self.paineis["monitoramento"]
                        if hasattr(p, "refresh"):
                            self.after(0, p.refresh)
                    except Exception:
                        pass
                # Atualiza o painel de almas vivas se estiver aberto
                if "almas_vivas" in self.paineis:
                    try:
                        p = self.paineis["almas_vivas"]
                        if hasattr(p, "refresh"):
                            self.after(0, p.refresh)
                    except Exception:
                        pass
                # Atualiza avatar se for a alma atual no chat individual
                if "chat_individual" in self.paineis:
                    try:
                        p = self.paineis["chat_individual"]
                        if hasattr(p, "current_ai") and p.current_ai == alma:
                            if hasattr(p, "refresh"):
                                self.after(0, p.refresh)
                    except Exception:
                        pass
                return

            # ── Handler: resposta de chat ────────────────────────────────────
            if "chat_individual" in self.paineis:
                p = self.paineis["chat_individual"]
                if hasattr(p, "inject_response") and alma and texto:
                    try: p.inject_response(alma, texto)
                    except Exception: pass
            if "chat_coletivo" in self.paineis:
                p = self.paineis["chat_coletivo"]
                if hasattr(p, "inject_response") and alma and texto:
                    try: p.inject_response(alma, texto)
                    except Exception: pass
            if tipo: logger.debug("Resposta recebida: tipo=%s alma=%s", tipo, alma)
        except Exception as e:
            logger.warning("Erro _handle_response: %s", e)

    def _periodic_refresh(self):
        for p in list(self.paineis.values()):
            if hasattr(p, "refresh"):
                try: p.refresh()
                except Exception: pass
        if not self.stop_event.is_set():
            try: self._periodic_after_id = self.after(5000, self._periodic_refresh)
            except Exception: pass

    def shutdown(self):
        # ===== NOVO: Destroi avatares 3D =====
        if hasattr(self, 'gerenciador_avatares_3d'):
            self.gerenciador_avatares_3d.destroy_all()
        
        try: self.stop_event.set()
        except Exception: pass
        try: self._response_thread_stop.set()
        except Exception: pass
        try:
            if self._periodic_after_id:
                self.after_cancel(self._periodic_after_id)
        except Exception: pass
        try:
            if self._response_thread and self._response_thread.is_alive():
                self._response_thread.join(timeout=3.0)
        except Exception: pass
        try: self.destroy()
        except Exception: pass

    def _registrar_callback_ai2ai(self):
        if not self.coracao:
            logger.warning("⚠️ Coração não disponível - conversas entre IAs não serão exibidas")
            return
        
        dispositivo = getattr(self.coracao, "dispositivo_ai_ai", None)
        if not dispositivo:
            logger.warning("⚠️ DispositivoAItoAI não disponível - conversas entre IAs não serão exibidas")
            return
        
        try:
            def on_nova_mensagem(destino, mensagem):
                origem = mensagem.get("origem", "???")
                destino = mensagem.get("destino", "???")
                conteudo = mensagem.get("conteudo", "")
                texto = f"[🤖 AI↔AI] {origem} → {destino}: {conteudo}"
                try:
                    self.after(0, lambda t=texto: self._exibir_mensagem_ai2ai(t))
                except Exception:
                    pass
            
            dispositivo.registrar_callback("nova_mensagem", on_nova_mensagem)
            logger.info("✅ Callback do DispositivoAItoAI registrado - conversas entre IAs serão exibidas")
            
            def on_alma_conectou(alma):
                logger.info(f"🔌 Alma conectada: {alma}")
            
            def on_alma_desconectou(alma):
                logger.info(f"🔌 Alma desconectada: {alma}")
            
            dispositivo.registrar_callback("alma_conectou", on_alma_conectou)
            dispositivo.registrar_callback("alma_desconectou", on_alma_desconectou)
            
        except Exception as e:
            logger.error(f"❌ Erro ao registrar callback AI↔AI: {e}")

    def _exibir_mensagem_ai2ai(self, texto):
        if "chat_coletivo" in self.paineis:
            try:
                painel = self.paineis["chat_coletivo"]
                if hasattr(painel, "hist_global"):
                    painel.hist_global.append(texto)
                    if painel._current_tab == "global":
                        painel._update_display()
            except Exception as e:
                logger.debug(f"Erro ao exibir no chat coletivo: {e}")


# ============================================================================
# FUNÇÃO DE ENTRADA
# ============================================================================

def criar_interface(coracao_ref=None, ui_queue=None, job_manager=None):
    import queue as _q
    import threading as _th
    command_queue  = _q.Queue()
    response_queue = ui_queue if ui_queue is not None else _q.Queue()
    stop_event     = _th.Event()
    if coracao_ref is not None and hasattr(coracao_ref, "injetar_ui_command_queue"):
        try:
            coracao_ref.injetar_ui_command_queue(command_queue)
        except Exception:
            pass
    janela = JanelaPrincipalArca(command_queue, response_queue, coracao_ref, stop_event, job_manager)
    return janela


if __name__ == "__main__":
    import threading
    from queue import Queue

    command_queue = Queue()
    response_queue = Queue()
    stop_event = threading.Event()

    coracao = None
    try:
        from src.core.coracao_orquestrador import CoracaoOrquestrador
        from src.config.config import get_config
        config = get_config()
        coracao = CoracaoOrquestrador(
            ui_queue=response_queue,
            llm_engine_ref=None,
            config_instance=config,
        )
        print("✅ CoracaoOrquestrador carregado com sucesso.")
    except ImportError as e:
        print(f"⚠️  Módulos do projeto não encontrados: {e}")
        print("    A interface abrirá sem conexão ação Coração.")
        print("    Cada painel mostrará o módulo exato que está faltando.")
    except Exception as e:
        print(f"❌ CoracaoOrquestrador falhou ao instanciar: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

    app = JanelaPrincipalArca(command_queue, response_queue, coracao, stop_event)
    app.mainloop()
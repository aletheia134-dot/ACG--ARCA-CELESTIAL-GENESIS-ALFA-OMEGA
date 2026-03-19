# src/encarnacao_e_interacao/avatar_panda3d.py
# -*- coding: utf-8 -*-
"""
Avatar 3D com Panda3D - Ultra-leve, embeddable no Tkinter
Consumo: ~30-50MB VRAM
"""

import logging
import math
import random
import threading
import time
from pathlib import Path
from typing import Optional, Dict, Any

logger = logging.getLogger("AvatarPanda3D")

# Import Panda3D com tratamento de erro
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
    logger.warning("Panda3D não instalado. Avatares 3D desabilitados.")


class AvatarPanda3DEmbedded:
    """
    Avatar 3D ultra-leve que renderiza DENTRO do Tkinter.
    Usa Panda3D com shader toon (cel-shading) e animações procedurais.
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
        
        if PANDA_AVAILABLE and self.modelo_path.exists():
            self._init_panda()
        else:
            self.logger.warning(f"Modelo 3D não encontrado: {self.modelo_path}")
    
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
            
            # Carrega modelo GLTF
            self._load_model()
            
            # Aplica shader toon
            self._apply_toon_shader()
            
            # Inicia animações
            self.panda_base.taskMgr.add(self._update_animation, "UpdateAnimation")
            
            self.logger.info(f"✅ Avatar 3D {self.nome_alma} inicializado")
            
        except Exception as e:
            self.logger.exception(f"Erro ao inicializar Panda3D: {e}")
            self.panda_base = None
    
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
    
    def _apply_toon_shader(self):
        """Aplica shader toon (cel-shading) para estilo anime"""
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
            
            // Cor base (azul para EVA, rosa para LUMINA, etc)
            vec3 base_color = vec3(0.4, 0.6, 1.0);  // Azul EVA
            
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
        
        shader = Shader.make(Shader.SL_GLSL, vertex_shader, fragment_shader)
        self.avatar_node.setShader(shader)
    
    def _update_animation(self, task):
        """Task de animação procedural"""
        dt = task.time
        
        # Respiração (movimento suave)
        breath = math.sin(dt * 2.0) * 0.02
        
        # Movimento de balanço
        sway_x = math.sin(dt * 1.3) * 0.01
        sway_y = math.cos(dt * 1.7) * 0.01
        
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
        valores = self.EMOCAO_BLENDSHAPE_MAP[emocao]
        
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
        if self.panda_base and self.panda_base.win:
            # Reativa a janela
            props = WindowProperties()
            props.setForeground(True)
            self.panda_base.win.requestProperties(props)
    
    def hide(self):
        """Esconde o avatar"""
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
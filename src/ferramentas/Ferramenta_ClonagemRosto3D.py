# Ferramenta: Clonagem de Rosto 3D
# Gera modelo 3D a partir de fotos, compatvel com GTX 1070 (2-3GB VRAM)

import sys
import os
import json
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent / "00_CORE"))
from src.modulos.utils import InterfaceBase, Utils
from src.config.config import PASTA_SAIDAS, PASTA_MODELOS, USAR_GPU

import cv2
import numpy as np
import torch
import torch.nn as nn
from PIL import Image, ImageTk
import customtkinter as ctk
from tkinter import filedialog, messagebox
import threading
import time
import trimesh
import open3d as o3d

# ========== módulos OPCIONAIS COM FALLBACK ==========

# Para deteco facial 3D
try:
    import mediapipe as mp
    MEDIAPIPE_AVAILABLE = True
except:
    MEDIAPIPE_AVAILABLE = False
    print("[AVISO] MediaPipe no instalado")

# Para reconstruo 3D
try:
    import face_alignment
    FA_AVAILABLE = True
except:
    FA_AVAILABLE = False
    print("[AVISO] face_alignment no instalado")

# Para rendering
try:
    from pytorch3d.structures import Meshes
    from pytorch3d.renderer import (
        PerspectiveCameras, AmbientLights, RasterizationSettings, 
        MeshRenderer, MeshRasterizer, SoftPhongShader, TexturesVertex
    )
    PYTORCH3D_AVAILABLE = True
except:
    PYTORCH3D_AVAILABLE = False
    print("[AVISO] pytorch3d no instalado (opcional para visualizao)")

class ModeloReconstrucao3D:
    """
    Modelo de reconstruo 3D facial a partir de imagens
    Usa tcnicas de deep learning para gerar malha 3D
    """
    def __init__(self, usar_gpu=True):
        self.usar_gpu = usar_gpu and torch.cuda.is_available()
        self.device = torch.device("cuda" if self.usar_gpu else "cpu")
        
        # Modelos
        self.fa = None
        self.detector_facial = None
        
        # Parmetros do modelo 3D
        self.num_vertices = 5023  # Número de vrtices do modelo base
        self.num_triangles = 9976  # Número de tringulos
        
        # Carrega modelos
        self.carregar_modelos()
        
        print(f"[OK] Reconstruo 3D inicializada na {self.device}")
    
    def carregar_modelos(self):
        """Carrega modelos necessários"""
        # Face Alignment para landmarks 3D
        if FA_AVAILABLE:
            try:
                self.fa = face_alignment.FaceAlignment(
                    face_alignment.LandmarksType._3D,
                    device=self.device,
                    flip_input=False
                )
                print("[OK] FaceAlignment 3D carregado")
            except Exception as e:
                print(f"[ERRO] Erro FaceAlignment: {e}")
        
        # MediaPipe para deteco facial
        if MEDIAPIPE_AVAILABLE:
            try:
                self.detector_facial = mp.solutions.face_detection.FaceDetection(
                    model_selection=1,
                    min_detection_confidence=0.5
                )
                print("[OK] MediaPipe FaceDetection carregado")
            except Exception as e:
                print(f"[ERRO] Erro MediaPipe: {e}")
    
    def detectar_rosto(self, imagem):
        """Detecta rosto na imagem e retorna bounding box"""
        if self.detector_facial is None:
            return None
        
        # Converte para RGB
        if isinstance(imagem, np.ndarray):
            rgb = cv2.cvtColor(imagem, cv2.COLOR_BGR2RGB)
        else:
            rgb = np.array(imagem)
        
        results = self.detector_facial.process(rgb)
        
        if results and results.detections:
            det = results.detections[0]
            bbox = det.location_data.relative_bounding_box
            h, w = rgb.shape[:2]
            
            return {
                'x': int(bbox.xmin * w),
                'y': int(bbox.ymin * h),
                'w': int(bbox.width * w),
                'h': int(bbox.height * h),
                'confianca': det.score[0]
            }
        return None
    
    def extrair_landmarks_3d(self, imagem):
        """Extrai landmarks 3D da face"""
        if self.fa is None:
            return None
        
        try:
            # Converte para RGB se necessário
            if isinstance(imagem, np.ndarray):
                if imagem.shape[2] == 3:
                    rgb = cv2.cvtColor(imagem, cv2.COLOR_BGR2RGB)
                else:
                    rgb = imagem
            else:
                rgb = np.array(imagem)
            
            # Detecta landmarks
            preds = self.fa.get_landmarks(rgb)
            
            if preds and len(preds) > 0:
                # Pega o primeiro rosto
                landmarks = preds[0]  # Shape: (68, 3)
                
                # Normaliza coordenadas
                landmarks[:, 0] /= rgb.shape[1]  # x
                landmarks[:, 1] /= rgb.shape[0]  # y
                # z j est normalizado
                
                return landmarks
            
        except Exception as e:
            print(f"Erro landmarks: {e}")
        
        return None
    
    def reconstruir_malha(self, landmarks, depth_estimate=True):
        """
        Reconstri malha 3D a partir de landmarks
        Usa interpolao para gerar malha completa
        """
        if landmarks is None:
            return None
        
        # Template base (malha mdia da face)
        vertices = self._gerar_vertices_base(landmarks)
        
        # Gera tringulos (conectividade)
        triangles = self._gerar_triangulos_base()
        
        # Estima profundidade se necessário
        if depth_estimate:
            vertices = self._estimar_profundidade(vertices, landmarks)
        
        return {
            'vertices': vertices,
            'triangles': triangles,
            'num_vertices': len(vertices),
            'num_triangles': len(triangles)
        }
    
    def _gerar_vertices_base(self, landmarks):
        """Gera vrtices base da malha"""
        # Interpola landmarks para criar malha densa
        num_landmarks = len(landmarks)
        
        # Cria grade 2D
        grid_size = 64
        x = np.linspace(0, 1, grid_size)
        y = np.linspace(0, 1, grid_size)
        xx, yy = np.meshgrid(x, y)
        
        # Interpola landmarks
        from scipy.interpolate import griddata
        points = landmarks[:, :2]
        values_z = landmarks[:, 2]
        
        # Interpola z
        zz = griddata(points, values_z, (xx, yy), method='cubic', fill_value=0)
        
        # Cria vrtices
        vertices = []
        for i in range(grid_size):
            for j in range(grid_size):
                if not np.isnan(zz[i, j]):
                    vertices.append([xx[i, j], yy[i, j], zz[i, j]])
        
        return np.array(vertices, dtype=np.float32)
    
    def _gerar_triangulos_base(self):
        """Gera conectividade dos tringulos"""
        # Grade regular
        grid_size = 64
        triangles = []
        
        for i in range(grid_size - 1):
            for j in range(grid_size - 1):
                idx = i * grid_size + j
                # Tringulo 1
                triangles.append([idx, idx + 1, idx + grid_size])
                # Tringulo 2
                triangles.append([idx + 1, idx + grid_size + 1, idx + grid_size])
        
        return np.array(triangles, dtype=np.int32)
    
    def _estimar_profundidade(self, vertices, landmarks):
        """Estima profundidade usando modelo estatstico"""
        # Ajusta profundidade baseada em landmarks
        z_mean = np.mean(landmarks[:, 2])
        z_std = np.std(landmarks[:, 2])
        
        # Normaliza profundidade
        vertices[:, 2] = (vertices[:, 2] - np.mean(vertices[:, 2])) / np.std(vertices[:, 2])
        vertices[:, 2] = vertices[:, 2] * z_std + z_mean
        
        return vertices
    
    def salvar_malha(self, malha, caminho, formato='obj'):
        """Salva malha 3D em arquivo"""
        try:
            vertices = malha['vertices']
            triangles = malha['triangles']
            
            # Cria mesh com trimesh
            mesh = trimesh.Trimesh(vertices=vertices, faces=triangles)
            
            # Salva
            if formato == 'obj':
                mesh.export(caminho)
            elif formato == 'ply':
                mesh.export(caminho)
            elif formato == 'stl':
                mesh.export(caminho)
            
            return True
        except Exception as e:
            print(f"Erro ao salvar: {e}")
            return False
    
    def gerar_textura(self, imagem, malha):
        """Gera textura UV para a malha"""
        try:
            # Projeta imagem na malha
            h, w = imagem.shape[:2]
            
            # Coordenadas UV baseadas em x,y
            vertices = malha['vertices']
            uv = vertices[:, :2].copy()
            
            # Ajusta para range 0-1
            uv[:, 0] = np.clip(uv[:, 0], 0, 1)
            uv[:, 1] = np.clip(uv[:, 1], 0, 1)
            
            return uv
        except:
            return None

class Visualizador3D:
    """Visualizador 3D simples (fallback)"""
    def __init__(self):
        self.vis = None
        self.mesh = None
    
    def criar_janela(self):
        """Cria janela de visualizao"""
        if not PYTORCH3D_AVAILABLE:
            # Usa Open3D como fallback
            self.vis = o3d.visualization.Visualizer()
            self.vis.create_window(window_name="Visualizao 3D", width=800, height=600)
    
    def mostrar_malha(self, vertices, triangles):
        """Mostra malha 3D"""
        try:
            # Converte para formato Open3D
            mesh_o3d = o3d.geometry.TriangleMesh()
            mesh_o3d.vertices = o3d.utility.Vector3dVector(vertices)
            mesh_o3d.triangles = o3d.utility.Vector3iVector(triangles)
            mesh_o3d.compute_vertex_normals()
            
            # Mostra
            o3d.visualization.draw_geometries([mesh_o3d], window_name="Rosto 3D")
            
        except Exception as e:
            print(f"Erro visualizao: {e}")
    
    def fechar(self):
        if self.vis:
            self.vis.destroy_window()

class FerramentaClonagemRosto3D:
    def __init__(self, usar_gpu=True):
        self.modelo = ModeloReconstrucao3D(usar_gpu=usar_gpu)
        self.visualizador = Visualizador3D()
        self.imagem_original = None
        self.rosto_detectado = None
        self.landmarks_3d = None
        self.malha_3d = None
        self.textura_uv = None
    
    def processar_imagem(self, caminho_imagem):
        """Processa imagem e gera modelo 3D"""
        try:
            # Carrega imagem
            self.imagem_original = cv2.imread(caminho_imagem)
            if self.imagem_original is None:
                return None, "No foi possível carregar imagem"
            
            # Detecta rosto
            self.rosto_detectado = self.modelo.detectar_rosto(self.imagem_original)
            if self.rosto_detectado is None:
                return None, "Nenhum rosto detectado na imagem"
            
            # Extrai landmarks 3D
            self.landmarks_3d = self.modelo.extrair_landmarks_3d(self.imagem_original)
            if self.landmarks_3d is None:
                return None, "No foi possível extrair landmarks 3D"
            
            # Reconstri malha
            self.malha_3d = self.modelo.reconstruir_malha(self.landmarks_3d)
            if self.malha_3d is None:
                return None, "Falha na reconstruo 3D"
            
            # Gera textura
            self.textura_uv = self.modelo.gerar_textura(self.imagem_original, self.malha_3d)
            
            return {
                'rosto': self.rosto_detectado,
                'num_landmarks': len(self.landmarks_3d),
                'vertices': self.malha_3d['num_vertices'],
                'triangles': self.malha_3d['num_triangles']
            }, "Sucesso"
            
        except Exception as e:
            return None, str(e)
    
    def salvar_modelo(self, pasta_saida, formato='obj', com_textura=True):
        """Salva modelo 3D"""
        if self.malha_3d is None:
            return None, "Nenhum modelo gerado"
        
        try:
            pasta = Path(pasta_saida)
            pasta.mkdir(exist_ok=True, parents=True)
            
            timestamp = Utils.get_timestamp()
            
            # Salva malha
            nome_malha = pasta / f"rosto_3d_{timestamp}.{formato}"
            self.modelo.salvar_malha(self.malha_3d, str(nome_malha), formato)
            
            # Salva landmarks
            nome_landmarks = pasta / f"landmarks_{timestamp}.npy"
            np.save(str(nome_landmarks), self.landmarks_3d)
            
            # Salva textura se disponível
            if com_textura and self.textura_uv is not None and self.imagem_original is not None:
                nome_textura = pasta / f"textura_{timestamp}.jpg"
                cv2.imwrite(str(nome_textura), self.imagem_original)
                
                # Salva coordenadas UV
                nome_uv = pasta / f"uv_{timestamp}.npy"
                np.save(str(nome_uv), self.textura_uv)
            
            return {
                'malha': str(nome_malha),
                'landmarks': str(nome_landmarks),
                'textura': str(nome_textura) if com_textura else None
            }, "Sucesso"
            
        except Exception as e:
            return None, str(e)
    
    def visualizar(self):
        """Visualiza modelo 3D"""
        if self.malha_3d is None:
            return False
        
        self.visualizador.mostrar_malha(
            self.malha_3d['vertices'],
            self.malha_3d['triangles']
        )
        return True

class InterfaceClonagemRosto3D(InterfaceBase):
    def __init__(self):
        super().__init__(" Clonagem de Rosto 3D", "900x700")
        self.ferramenta = FerramentaClonagemRosto3D(usar_gpu=USAR_GPU)
        self.caminho_imagem = None
        self.info_modelo = None
        self.setup_interface()
    
    def setup_interface(self):
        # Ttulo
        titulo = ctk.CTkLabel(
            self.frame,
            text=" Clonagem de Rosto 3D",
            font=("Arial", 24, "bold")
        )
        titulo.pack(pady=10)
        
        # Status GPU
        status = "[OK] GPU Ativa (3D Reconstruction)" if self.ferramenta.modelo.usar_gpu else "[AVISO] CPU (lento)"
        self.lbl_gpu = ctk.CTkLabel(self.frame, text=status)
        self.lbl_gpu.pack(pady=5)
        
        # Frame principal (2 colunas)
        self.frame_principal = ctk.CTkFrame(self.frame)
        self.frame_principal.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Coluna esquerda (imagem original)
        self.frame_original = ctk.CTkFrame(self.frame_principal)
        self.frame_original.pack(side="left", padx=5, fill="both", expand=True)
        
        ctk.CTkLabel(
            self.frame_original,
            text="Imagem Original",
            font=("Arial", 14, "bold")
        ).pack(pady=5)
        
        self.lbl_original = ctk.CTkLabel(
            self.frame_original,
            text="Nenhuma imagem",
            width=300,
            height=300
        )
        self.lbl_original.pack(expand=True)
        
        # Coluna direita (modelo 3D)
        self.frame_3d = ctk.CTkFrame(self.frame_principal)
        self.frame_3d.pack(side="right", padx=5, fill="both", expand=True)
        
        ctk.CTkLabel(
            self.frame_3d,
            text="Modelo 3D",
            font=("Arial", 14, "bold")
        ).pack(pady=5)
        
        self.lbl_3d = ctk.CTkLabel(
            self.frame_3d,
            text="Processe uma imagem",
            width=300,
            height=300
        )
        self.lbl_3d.pack(expand=True)
        
        # Controles
        self.frame_controles = ctk.CTkFrame(self.frame)
        self.frame_controles.pack(fill="x", padx=10, pady=10)
        
        # Botes principais
        self.frame_botoes = ctk.CTkFrame(self.frame_controles)
        self.frame_botoes.pack(pady=5)
        
        self.btn_imagem = ctk.CTkButton(
            self.frame_botoes,
            text=" Selecionar Imagem",
            command=self.selecionar_imagem,
            width=150
        )
        self.btn_imagem.pack(side="left", padx=5)
        
        self.btn_processar = ctk.CTkButton(
            self.frame_botoes,
            text=" Gerar Modelo 3D",
            command=self.processar,
            width=150,
            fg_color="green",
            state="disabled"
        )
        self.btn_processar.pack(side="left", padx=5)
        
        self.btn_visualizar = ctk.CTkButton(
            self.frame_botoes,
            text=" Visualizar",
            command=self.visualizar,
            width=100,
            state="disabled"
        )
        self.btn_visualizar.pack(side="left", padx=5)
        
        self.btn_salvar = ctk.CTkButton(
            self.frame_botoes,
            text=" Salvar",
            command=self.salvar,
            width=100,
            state="disabled"
        )
        self.btn_salvar.pack(side="left", padx=5)
        
        # Opes
        self.frame_opcoes = ctk.CTkFrame(self.frame_controles)
        self.frame_opcoes.pack(pady=5, fill="x")
        
        # Formato
        self.lbl_formato = ctk.CTkLabel(self.frame_opcoes, text="Formato:")
        self.lbl_formato.pack(side="left", padx=5)
        
        self.formato_var = ctk.StringVar(value="obj")
        self.formato_combo = ctk.CTkComboBox(
            self.frame_opcoes,
            values=["obj", "ply", "stl"],
            variable=self.formato_var,
            width=80
        )
        self.formato_combo.pack(side="left", padx=5)
        
        # Com textura
        self.textura_var = ctk.BooleanVar(value=True)
        self.chk_textura = ctk.CTkCheckBox(
            self.frame_opcoes,
            text="Incluir textura",
            variable=self.textura_var
        )
        self.chk_textura.pack(side="left", padx=20)
        
        # Qualidade
        self.lbl_qualidade = ctk.CTkLabel(self.frame_opcoes, text="Qualidade:")
        self.lbl_qualidade.pack(side="left", padx=5)
        
        self.qualidade_var = ctk.StringVar(value="mdia")
        self.qualidade_combo = ctk.CTkComboBox(
            self.frame_opcoes,
            values=["baixa (rpido)", "mdia", "alta (lento)"],
            variable=self.qualidade_var,
            width=120
        )
        self.qualidade_combo.pack(side="left", padx=5)
        
        # informações
        self.frame_info = ctk.CTkFrame(self.frame_controles)
        self.frame_info.pack(pady=5, fill="x")
        
        self.lbl_info = ctk.CTkLabel(
            self.frame_info,
            text="Aguardando imagem...",
            text_color="#CCCCCC"
        )
        self.lbl_info.pack()
        
        # Barra de progresso
        self.progress = ctk.CTkProgressBar(self.frame, width=400)
        self.progress.pack(pady=5)
        self.progress.set(0)
    
    def selecionar_imagem(self):
        caminho = filedialog.askopenfilename(
            title="Selecione uma imagem com rosto",
            filetypes=[("Imagens", "*.jpg *.jpeg *.png *.bmp")]
        )
        if caminho:
            self.caminho_imagem = caminho
            
            # Preview
            from PIL import Image, ImageTk
            img = Image.open(caminho)
            img.thumbnail((300, 300))
            img_tk = ImageTk.PhotoImage(img)
            self.lbl_original.configure(image=img_tk, text="")
            self.lbl_original.image = img_tk
            
            self.btn_processar.configure(state="normal")
            self.lbl_info.configure(text="Imagem carregada. Clique em 'Gerar Modelo 3D'")
    
    def processar(self):
        def processar_thread():
            self.btn_processar.configure(state="disabled", text=" Gerando modelo 3D...")
            self.progress.set(0.2)
            
            self.lbl_info.configure(text="Detectando rosto...")
            self.frame.update()
            
            resultado, msg = self.ferramenta.processar_imagem(self.caminho_imagem)
            
            self.progress.set(0.6)
            
            if resultado:
                self.info_modelo = resultado
                
                # Mostra info
                texto_info = f"[OK] Rosto detectado!\n"
                texto_info += f"Landmarks: {resultado['num_landmarks']}\n"
                texto_info += f"Vrtices: {resultado['vertices']}\n"
                texto_info += f"Tringulos: {resultado['triangles']}"
                
                self.lbl_info.configure(text=texto_info)
                
                # Preview 3D (placeholder)
                self.lbl_3d.configure(text="[OK] Modelo 3D gerado!\nClique em Visualizar")
                
                self.btn_visualizar.configure(state="normal")
                self.btn_salvar.configure(state="normal")
                
                self.utils.mostrar_info("Sucesso", "Modelo 3D gerado com sucesso!")
            else:
                self.utils.mostrar_erro("Erro", msg)
                self.lbl_info.configure(text=f"Erro: {msg}")
            
            self.progress.set(1)
            self.btn_processar.configure(state="normal", text=" Gerar Modelo 3D")
        
        threading.Thread(target=processar_thread).start()
    
    def visualizar(self):
        """Visualiza modelo 3D"""
        self.lbl_info.configure(text="Abrindo visualizador 3D...")
        self.frame.update()
        
        if self.ferramenta.visualizar():
            self.lbl_info.configure(text="Visualizador 3D aberto")
        else:
            self.utils.mostrar_erro("Erro", "No foi possível abrir visualizador")
    
    def salvar(self):
        """Salva modelo 3D"""
        pasta = filedialog.askdirectory(title="Selecione pasta para salvar")
        if pasta:
            def salvar_thread():
                self.btn_salvar.configure(state="disabled", text=" Salvando...")
                
                resultado, msg = self.ferramenta.salvar_modelo(
                    pasta,
                    formato=self.formato_var.get(),
                    com_textura=self.textura_var.get()
                )
                
                if resultado:
                    texto = "[OK] Modelo salvo!\n\n"
                    texto += f"Malha: {Path(resultado['malha']).name}\n"
                    if resultado['textura']:
                        texto += f"Textura: {Path(resultado['textura']).name}"
                    
                    self.utils.mostrar_info("Sucesso", texto)
                    self.lbl_info.configure(text="Modelo salvo com sucesso!")
                else:
                    self.utils.mostrar_erro("Erro", msg)
                
                self.btn_salvar.configure(state="normal", text=" Salvar")
            
            threading.Thread(target=salvar_thread).start()

class ModoIA_Clonagem3D:
    """Modo IA para clonagem 3D"""
    def __init__(self):
        self.ferramenta = FerramentaClonagemRosto3D(usar_gpu=USAR_GPU)
        self.utils = Utils()
    
    def descobrir(self, pasta_teste):
        """IA explora diferentes imagens"""
        resultados = []
        imagens = list(Path(pasta_teste).glob("*.jpg"))[:3]
        
        for img_path in imagens:
            resultado, msg = self.ferramenta.processar_imagem(str(img_path))
            if resultado:
                resultados.append({
                    "imagem": img_path.name,
                    "landmarks": int(resultado['num_landmarks']),
                    "vertices": int(resultado['vertices'])
                })
        
        return resultados
    
    def processar_para_ia(self, caminho_imagem, salvar=True):
        """IA processa e retorna modelo"""
        resultado, msg = self.ferramenta.processar_imagem(caminho_imagem)
        
        if resultado and salvar:
            pasta = PASTA_SAIDAS / "modelos_3d_ia"
            arquivo, _ = self.ferramenta.salvar_modelo(pasta)
            return {
                "sucesso": True,
                "arquivo": arquivo['malha'] if arquivo else None,
                "estatisticas": resultado
            }
        elif resultado:
            return {
                "sucesso": True,
                "estatisticas": resultado
            }
        else:
            return {"sucesso": False, "erro": msg}

if __name__ == "__main__":
    if len(sys.argv) > 1:
        comando = sys.argv[1]
        ia = ModoIA_Clonagem3D()
        
        if comando == "--descobrir" and len(sys.argv) > 2:
            resultados = ia.descobrir(sys.argv[2])
            print(json.dumps(resultados, indent=2, ensure_ascii=False))
        
        elif comando == "--processar" and len(sys.argv) > 2:
            resultado = ia.processar_para_ia(sys.argv[2])
            print(json.dumps(resultado, indent=2, ensure_ascii=False))
        
        else:
            print("Uso: python Ferramenta_ClonagemRosto3D.py [--descobrir PASTA | --processar IMAGEM]")
    else:
        app = InterfaceClonagemRosto3D()
        app.rodar()

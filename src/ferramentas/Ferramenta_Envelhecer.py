# Ferramenta: Envelhecer Rostos (Foto  Idoso)
# Modo 1: Manual (interface grfica)
# Modo 2: IA explorando (testar efeitos)
# Modo 3: IA a servio (pedido do usurio)

import sys
import os
import json
from pathlib import Path

# Adiciona core ação path
sys.path.append(str(Path(__file__).parent.parent / "00_CORE"))
from src.modulos.utils import InterfaceBase, Utils
from src.config.config import PASTA_SAIDAS, PASTA_MODELOS, USAR_GPU

import torch
import torch.nn as nn
import numpy as np
from PIL import Image, ImageFilter, ImageEnhance
import cv2
import customtkinter as ctk
from tkinter import filedialog, messagebox
import dlib
import requests
import zipfile
import warnings
warnings.filterwarnings('ignore')

class ModeloEnvelhecer:
    """
    Modelo para envelhecer rostos usando:
    1. Deteco facial (dlib)
    2. Filtros de envelhecimento (rugas, cabelos grisalhos)
    3. Textura de pele envelhecida
    """
    def __init__(self, usar_gpu=True):
        self.usar_gpu = usar_gpu and torch.cuda.is_available()
        self.device = torch.device("cuda" if self.usar_gpu else "cpu")
        self.detector_facial = None
        self.predictor = None
        self.carregar_modelos()
        
    def carregar_modelos(self):
        """Carrega modelos de deteco facial"""
        try:
            # Baixa modelos do dlib se no existirem
            self.baixar_modelos_dlib()
            
            # Carrega detector de faces (HOG + SVM) - 0.5GB VRAM
            self.detector_facial = dlib.get_frontal_face_detector()
            
            # Carrega predictor de landmarks (68 pontos faciais)
            predictor_path = PASTA_MODELOS / "shape_predictor_68_face_landmarks.dat"
            if predictor_path.exists():
                self.predictor = dlib.shape_predictor(str(predictor_path))
                print(f"[OK] Modelos faciais carregados (CPU)")
            else:
                print("[ERRO] Predictor no encontrado")
                self.predictor = None
                
        except Exception as e:
            print(f"[ERRO] Erro ao carregar modelos: {e}")
            self.detector_facial = None
            self.predictor = None
    
    def baixar_modelos_dlib(self):
        """Baixa modelos necessários do dlib"""
        arquivo_predictor = PASTA_MODELOS / "shape_predictor_68_face_landmarks.dat"
        
        if not arquivo_predictor.exists():
            print(" Baixando modelo de landmarks faciais (90MB)...")
            url = "http://dlib.net/files/shape_predictor_68_face_landmarks.dat.bz2"
            
            # Baixa arquivo
            response = requests.get(url, stream=True)
            bz2_path = PASTA_MODELOS / "shape_predictor_68_face_landmarks.dat.bz2"
            
            with open(bz2_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            # Extrai
            import bz2
            with bz2.open(bz2_path, 'rb') as f_in:
                with open(arquivo_predictor, 'wb') as f_out:
                    f_out.write(f_in.read())
            
            # Remove compactado
            bz2_path.unlink()
            print("[OK] Modelo baixado e extrado")
    
    def detectar_rosto(self, imagem):
        """Detecta o rosto na imagem"""
        if self.detector_facial is None:
            return None
        
        # Converte PIL para array (dlib precisa de RGB)
        img_array = np.array(imagem)
        
        # Detecta faces
        faces = self.detector_facial(img_array, 1)
        
        if len(faces) == 0:
            return None
        
        # Pega o primeiro rosto (maior)
        return faces[0]
    
    def get_landmarks(self, imagem, rosto):
        """Obtm pontos faciais"""
        if self.predictor is None:
            return None
        
        img_array = np.array(imagem)
        landmarks = self.predictor(img_array, rosto)
        
        # Converte para lista de pontos
        pontos = []
        for i in range(68):
            x = landmarks.part(i).x
            y = landmarks.part(i).y
            pontos.append((x, y))
        
        return pontos
    
    def aplicar_rugas(self, imagem, intensidade=0.5):
        """Aplica textura de rugas"""
        # Converte para array
        img_array = np.array(imagem)
        
        # Gera textura de rugas procedural
        altura, largura = img_array.shape[:2]
        
        # Cria mscara de rugas (linhas horizontais suaves)
        rugas = np.zeros((altura, largura), dtype=np.float32)
        
        # Rugas na testa
        for i in range(5):
            y = altura // 4 + i * 10
            cv2.line(rugas, (0, y), (largura, y), 0.3, 2)
        
        # Rugas ação redor dos olhos (ps de galinha)
        centro_olhos = (largura // 2, altura // 3)
        for angulo in range(0, 360, 45):
            x1 = int(centro_olhos[0] + 30 * np.cos(np.radians(angulo)))
            y1 = int(centro_olhos[1] + 20 * np.sin(np.radians(angulo)))
            x2 = int(centro_olhos[0] + 50 * np.cos(np.radians(angulo)))
            y2 = int(centro_olhos[1] + 30 * np.sin(np.radians(angulo)))
            cv2.line(rugas, (x1, y1), (x2, y2), 0.2, 1)
        
        # Rugas na bochecha
        for i in range(3):
            y = altura // 2 + i * 15
            cv2.ellipse(rugas, (largura//2, y), (50, 10), 0, 0, 360, 0.2, 2)
        
        # Suaviza a textura
        rugas = cv2.GaussianBlur(rugas, (15, 15), 0)
        
        # Aplica na imagem
        img_array = img_array.astype(np.float32)
        
        # Escurece as rugas
        rugas_expandido = np.stack([rugas] * 3, axis=2)
        img_array = img_array * (1 - rugas_expandido * intensidade * 0.3)
        
        # Limita valores
        img_array = np.clip(img_array, 0, 255).astype(np.uint8)
        
        return Image.fromarray(img_array)
    
    def aplicar_cabelos_grisalhos(self, imagem, intensidade=0.5):
        """Aplica efeito de cabelos grisalhos"""
        # Converte para array
        img_array = np.array(imagem)
        
        # Detecta regio do cabelo (parte superior da imagem)
        altura, largura = img_array.shape[:2]
        regiao_cabelo = img_array[:altura//3, :]
        
        # Aplica tom acinzentado
        cinza = cv2.cvtColor(regiao_cabelo, cv2.COLOR_RGB2GRAY)
        cinza = cv2.cvtColor(cinza, cv2.COLOR_GRAY2RGB)
        
        # Mistura com original
        mistura = cv2.addWeighted(regiao_cabelo, 1 - intensidade, cinza, intensidade, 0)
        
        # Recoloca na imagem
        img_array[:altura//3, :] = mistura
        
        return Image.fromarray(img_array)
    
    def aplicar_manchas_pele(self, imagem, intensidade=0.3):
        """Aplica manchas senis na pele"""
        img_array = np.array(imagem)
        altura, largura = img_array.shape[:2]
        
        # Cria mscara de manchas aleatrias
        manchas = np.random.rand(altura, largura) * 0.3
        manchas = cv2.GaussianBlur(manchas, (25, 25), 0)
        
        # Manchas mais escuras/marrons
        img_array = img_array.astype(np.float32)
        
        # Regies das mas do rosto e mos
        for i in range(3):
            x_centro = np.random.randint(largura//4, 3*largura//4)
            y_centro = np.random.randint(altura//3, 2*altura//3)
            
            # Desenha mancha circular
            Y, X = np.ogrid[:altura, :largura]
            dist = np.sqrt((X - x_centro)**2 + (Y - y_centro)**2)
            mascara = np.exp(-dist / 50) * intensidade * 0.5
            
            for c in range(3):
                img_array[:,:,c] -= mascara * 30  # escurece
        
        img_array = np.clip(img_array, 0, 255).astype(np.uint8)
        
        return Image.fromarray(img_array)
    
    def aplicar_olheiras(self, imagem, intensidade=0.4):
        """Aplica olheiras abaixo dos olhos"""
        if self.predictor is None:
            return imagem
        
        img_array = np.array(imagem)
        altura, largura = img_array.shape[:2]
        
        # Detecta rosto para localizar olhos
        rosto = self.detectar_rosto(imagem)
        if rosto:
            pontos = self.get_landmarks(imagem, rosto)
            if pontos:
                # Pontos dos olhos (índices 36-47 no dlib)
                olho_esquerdo = pontos[36:42]
                olho_direito = pontos[42:48]
                
                # Calcula regio abaixo dos olhos
                for olho in [olho_esquerdo, olho_direito]:
                    x_centro = sum(p[0] for p in olho) // len(olho)
                    y_centro = (sum(p[1] for p in olho) // len(olho)) + 15
                    
                    # Desenha olheira
                    Y, X = np.ogrid[:altura, :largura]
                    dist = np.sqrt((X - x_centro)**2 + (Y - y_centro)**2)
                    mascara = np.exp(-dist / 25) * intensidade * 0.7
                    
                    for c in range(3):
                        img_array[:,:,c] = img_array[:,:,c] * (1 - mascara * 0.3)
        
        return Image.fromarray(img_array)
    
    def processar(self, caminho_imagem, idade_alvo=70, intensidade=0.7):
        """
        Processa imagem envelhecendo o rosto
        
        Args:
            caminho_imagem: caminho da imagem
            idade_alvo: idade desejada (40-90)
            intensidade: fora do efeito (0.1-1.0)
        """
        try:
            # Abre imagem
            img = Image.open(caminho_imagem).convert("RGB")
            
            # Redimensiona se muito grande
            if max(img.size) > 1024:
                img.thumbnail((1024, 1024), Image.Resampling.LANCZOS)
            
            # Ajusta intensidade baseado na idade
            idade_base = 30  # assume idade base de 30 anos
            fator_idade = min(1.0, (idade_alvo - idade_base) / 60)
            intensidade_ajustada = intensidade * fator_idade
            
            # Aplica efeitos em sequncia
            img = self.aplicar_rugas(img, intensidade_ajustada * 0.8)
            img = self.aplicar_manchas_pele(img, intensidade_ajustada * 0.5)
            img = self.aplicar_olheiras(img, intensidade_ajustada * 0.6)
            img = self.aplicar_cabelos_grisalhos(img, intensidade_ajustada * 0.7)
            
            # Suaviza levemente
            img = img.filter(ImageFilter.SMOOTH_MORE)
            
            # Reduz saturao (pele mais plida)
            enhancer = ImageEnhance.Color(img)
            img = enhancer.enhance(1.0 - intensidade_ajustada * 0.3)
            
            return img, "Sucesso"
            
        except Exception as e:
            return None, str(e)

class InterfaceEnvelhecer(InterfaceBase):
    """Interface grfica (MODO 1 - Manual)"""
    def __init__(self):
        super().__init__(" Envelhecer Fotos", "750x650")
        self.ferramenta = ModeloEnvelhecer(usar_gpu=USAR_GPU)
        self.caminho_imagem = None
        self.imagem_original = None
        self.imagem_processada = None
        self.setup_interface()
    
    def setup_interface(self):
        """Cria os elementos da interface"""
        # Ttulo
        titulo = ctk.CTkLabel(
            self.frame, 
            text=" Transformar Foto: Verso Idoso",
            font=("Arial", 22, "bold")
        )
        titulo.pack(pady=10)
        
        # Status
        status = "[OK] GTX 1070 ativa" if self.ferramenta.usar_gpu else "[AVISO] CPU (mais lento)"
        self.lbl_status = ctk.CTkLabel(self.frame, text=status)
        self.lbl_status.pack(pady=5)
        
        # Frame principal (2 colunas)
        self.frame_principal = ctk.CTkFrame(self.frame)
        self.frame_principal.pack(pady=10, fill="both", expand=True)
        
        # Coluna esquerda (controles)
        self.frame_controles = ctk.CTkFrame(self.frame_principal)
        self.frame_controles.pack(side="left", padx=10, fill="y")
        
        # Coluna direita (preview)
        self.frame_preview = ctk.CTkFrame(self.frame_principal)
        self.frame_preview.pack(side="right", padx=10, fill="both", expand=True)
        
        # ===== CONTROLES =====
        # Boto selecionar imagem
        self.btn_imagem = ctk.CTkButton(
            self.frame_controles,
            text=" Selecionar Foto",
            command=self.selecionar_imagem,
            width=200,
            height=40
        )
        self.btn_imagem.pack(pady=10)
        
        # Info arquivo
        self.lbl_arquivo = ctk.CTkLabel(
            self.frame_controles, 
            text="Nenhuma foto",
            wraplength=200
        )
        self.lbl_arquivo.pack(pady=5)
        
        # Slider idade
        self.lbl_idade = ctk.CTkLabel(
            self.frame_controles,
            text="Idade alvo: 70 anos"
        )
        self.lbl_idade.pack(pady=(20, 5))
        
        self.slider_idade = ctk.CTkSlider(
            self.frame_controles,
            from_=40,
            to=90,
            number_of_steps=50,
            command=self.atualizar_label_idade
        )
        self.slider_idade.set(70)
        self.slider_idade.pack(pady=5, padx=10, fill="x")
        
        # Slider intensidade
        self.lbl_intensidade = ctk.CTkLabel(
            self.frame_controles,
            text="Intensidade: 70%"
        )
        self.lbl_intensidade.pack(pady=(20, 5))
        
        self.slider_intensidade = ctk.CTkSlider(
            self.frame_controles,
            from_=0.1,
            to=1.0,
            number_of_steps=9,
            command=self.atualizar_label_intensidade
        )
        self.slider_intensidade.set(0.7)
        self.slider_intensidade.pack(pady=5, padx=10, fill="x")
        
        # Boto processar
        self.btn_processar = ctk.CTkButton(
            self.frame_controles,
            text=" Envelhecer Foto",
            command=self.processar,
            width=200,
            height=45,
            fg_color="green",
            hover_color="darkgreen",
            state="disabled"
        )
        self.btn_processar.pack(pady=30)
        
        # Boto salvar
        self.btn_salvar = ctk.CTkButton(
            self.frame_controles,
            text=" Salvar Resultado",
            command=self.salvar_imagem,
            width=200,
            state="disabled"
        )
        self.btn_salvar.pack(pady=5)
        
        # Boto comparar
        self.btn_comparar = ctk.CTkButton(
            self.frame_controles,
            text=" Ver Original",
            command=self.alternar_preview,
            width=200,
            state="disabled"
        )
        self.btn_comparar.pack(pady=5)
        
        # ===== PREVIEW =====
        self.lbl_preview = ctk.CTkLabel(
            self.frame_preview,
            text="Pr-visualizao\n\nSelecione uma foto para comear",
            font=("Arial", 14)
        )
        self.lbl_preview.pack(expand=True)
        
        # Controle de modo preview
        self.mostrando_original = False
    
    def atualizar_label_idade(self, valor):
        self.lbl_idade.configure(text=f"Idade alvo: {int(valor)} anos")
    
    def atualizar_label_intensidade(self, valor):
        self.lbl_intensidade.configure(text=f"Intensidade: {int(valor*100)}%")
    
    def selecionar_imagem(self):
        caminho = self.utils.selecionar_arquivo(
            "Selecione uma foto",
            [("Imagens", "*.jpg *.jpeg *.png *.bmp")]
        )
        if caminho:
            self.caminho_imagem = caminho
            self.imagem_original = Image.open(caminho)
            
            # Redimensiona para preview
            self.imagem_original.thumbnail((400, 400))
            
            self.lbl_arquivo.configure(text=f"Arquivo: {Path(caminho).name}")
            self.btn_processar.configure(state="normal")
            
            # Mostra preview original
            self.mostrar_preview(self.imagem_original)
    
    def mostrar_preview(self, imagem):
        """Mostra imagem no preview"""
        # Salva temporrio
        temp_path = Path("C:/Ferramentas_IA/temp/preview.jpg")
        imagem.save(temp_path)
        
        # Carrega no CTkImage
        from PIL import ImageTk
        img_tk = ImageTk.PhotoImage(imagem)
        self.lbl_preview.configure(image=img_tk, text="")
        self.lbl_preview.image = img_tk  # mantm referncia
    
    def processar(self):
        if not self.caminho_imagem:
            return
        
        self.btn_processar.configure(text=" Processando...", state="disabled")
        self.frame.update()
        
        # Processa
        idade = int(self.slider_idade.get())
        intensidade = self.slider_intensidade.get()
        
        img_saida, msg = self.ferramenta.processar(
            self.caminho_imagem,
            idade_alvo=idade,
            intensidade=intensidade
        )
        
        if img_saida:
            self.imagem_processada = img_saida
            self.imagem_processada.thumbnail((400, 400))
            self.mostrar_preview(self.imagem_processada)
            self.btn_salvar.configure(state="normal")
            self.btn_comparar.configure(state="normal")
            self.mostrando_original = False
        else:
            self.utils.mostrar_erro("Erro", f"Falha ao processar: {msg}")
        
        self.btn_processar.configure(text=" Envelhecer Foto", state="normal")
    
    def alternar_preview(self):
        """Alterna entre original e processado"""
        if self.mostrando_original:
            self.mostrar_preview(self.imagem_processada)
            self.btn_comparar.configure(text=" Ver Original")
        else:
            self.mostrar_preview(self.imagem_original)
            self.btn_comparar.configure(text=" Ver Processado")
        
        self.mostrando_original = not self.mostrando_original
    
    def salvar_imagem(self):
        if self.imagem_processada:
            caminho = filedialog.asksaveasfilename(
                defaultextension=".jpg",
                filetypes=[("JPEG", "*.jpg"), ("PNG", "*.png")]
            )
            if caminho:
                # Salva em tamanho original
                img_original = Image.open(self.caminho_imagem)
                img_saida, _ = self.ferramenta.processar(
                    self.caminho_imagem,
                    idade_alvo=int(self.slider_idade.get()),
                    intensidade=self.slider_intensidade.get()
                )
                img_saida.save(caminho)
                self.utils.mostrar_info("Sucesso", f"Imagem salva em:\n{caminho}")

class ModoIA:
    """MODO 2 e 3 - Para IAs usarem"""
    def __init__(self):
        self.ferramenta = ModeloEnvelhecer(usar_gpu=USAR_GPU)
        self.utils = Utils()
    
    def descobrir(self, pasta_teste):
        """MODO 2: IA explorando - testa diferentes idades"""
        resultados = []
        imagens = list(Path(pasta_teste).glob("*.jpg"))[:2]
        
        idades_teste = [50, 70, 90]
        
        for img_path in imagens:
            resultados_por_idade = []
            for idade in idades_teste:
                img_saida, _ = self.ferramenta.processar(
                    str(img_path),
                    idade_alvo=idade,
                    intensidade=0.7
                )
                
                if img_saida:
                    nome_saida = self.utils.safe_filename(f"envelhecida_{idade}", "jpg")
                    caminho_saida = PASTA_SAIDAS / nome_saida
                    img_saida.save(caminho_saida)
                    resultados_por_idade.append({
                        "idade": idade,
                        "arquivo": str(caminho_saida)
                    })
            
            resultados.append({
                "imagem_original": img_path.name,
                "resultados": resultados_por_idade
            })
        
        return resultados
    
    def processar_para_ia(self, caminho_imagem, idade=70, intensidade=0.7):
        """MODO 3: IA a servio - processa e retorna caminho"""
        img_saida, msg = self.ferramenta.processar(
            caminho_imagem,
            idade_alvo=idade,
            intensidade=intensidade
        )
        
        if img_saida:
            nome_saida = self.utils.safe_filename("envelhecida_ia", "jpg")
            caminho_saida = PASTA_SAIDAS / nome_saida
            img_saida.save(caminho_saida)
            return {
                "sucesso": True,
                "arquivo": str(caminho_saida),
                "idade_aplicada": idade,
                "mensagem": f"Foto envelhecida para {idade} anos"
            }
        else:
            return {
                "sucesso": False,
                "erro": msg
            }

# ===== PONTO DE ENTRADA =====
if __name__ == "__main__":
    # Verifica modo de execução
    if len(sys.argv) > 1:
        # MODO 2 ou 3: Chamado por IA ou linha de comando
        comando = sys.argv[1]
        ia = ModoIA()
        
        if comando == "--descobrir" and len(sys.argv) > 2:
            # IA explorando
            pasta = sys.argv[2]
            resultados = ia.descobrir(pasta)
            print(json.dumps(resultados, indent=2, ensure_ascii=False))
        
        elif comando == "--processar" and len(sys.argv) > 2:
            # IA a servio
            imagem = sys.argv[2]
            idade = int(sys.argv[3]) if len(sys.argv) > 3 else 70
            resultado = ia.processar_para_ia(imagem, idade=idade)
            print(json.dumps(resultado, indent=2, ensure_ascii=False))
        
        else:
            print("Uso:")
            print("  python Ferramenta_Envelhecer.py                          # Modo manual")
            print("  python Ferramenta_Envelhecer.py --descobrir PASTA       # IA explorando")
            print("  python Ferramenta_Envelhecer.py --processar IMAGEM [IDADE] # IA servio")
    else:
        # MODO 1: Manual (interface grfica)
        app = InterfaceEnvelhecer()
        app.rodar()

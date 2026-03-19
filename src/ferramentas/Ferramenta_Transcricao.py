# Ferramenta: Transcrio de udio (udio  Texto)
# Usa Faster-Whisper (2GB VRAM)

import sys
import os
import json
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent / "00_CORE"))
from src.modulos.utils import InterfaceBase, Utils
from src.config.config import PASTA_SAIDAS, USAR_GPU

from faster_whisper import WhisperModel
import customtkinter as ctk
from tkinter import filedialog, messagebox
import threading
import time

class FerramentaTranscricao:
    def __init__(self, usar_gpu=True, modelo_tamanho="tiny"):
        self.usar_gpu = usar_gpu
        self.modelo_tamanho = modelo_tamanho  # tiny, base, small, medium, large
        self.model = None
        self.carregar_modelo()
    
    def carregar_modelo(self):
        """Carrega modelo Whisper"""
        try:
            device = "cuda" if self.usar_gpu else "cpu"
            compute_type = "float16" if self.usar_gpu else "int8"
            
            self.model = WhisperModel(
                self.modelo_tamanho,
                device=device,
                compute_type=compute_type,
                download_root=str(Path("C:/Ferramentas_IA/modelos/whisper"))
            )
            print(f"[OK] Whisper {self.modelo_tamanho} carregado (GPU: {self.usar_gpu})")
        except Exception as e:
            print(f"[ERRO] Erro ao carregar Whisper: {e}")
            self.model = None
    
    def processar(self, caminho_audio, idioma="pt", task="transcribe"):
        """Transcreve udio para texto"""
        if self.model is None:
            return None, "Modelo no carregado"
        
        try:
            segments, info = self.model.transcribe(
                caminho_audio,
                language=idioma,
                task=task,  # transcribe ou translate
                beam_size=5,
                best_of=5,
                temperature=0.0,
                vad_filter=True,  # remove silncio
                vad_parameters=dict(
                    min_silence_duration_ms=500,
                    threshold=0.5
                )
            )
            
            texto_completo = []
            for segment in segments:
                texto_completo.append(segment.text)
            
            return {
                "texto": " ".join(texto_completo),
                "idioma_detectado": info.language,
                "probabilidade": info.language_probability,
                "duracao": info.duration
            }, "Sucesso"
            
        except Exception as e:
            return None, str(e)
    
    def processar_com_timestamps(self, caminho_audio):
        """Transcreve com marcaes de tempo"""
        if self.model is None:
            return None, "Modelo no carregado"
        
        try:
            segments, info = self.model.transcribe(
                caminho_audio,
                language="pt",
                beam_size=5,
                vad_filter=True
            )
            
            resultado = []
            for segment in segments:
                resultado.append({
                    "início": segment.start,
                    "fim": segment.end,
                    "texto": segment.text
                })
            
            return resultado, "Sucesso"
            
        except Exception as e:
            return None, str(e)

class InterfaceTranscricao(InterfaceBase):
    def __init__(self):
        super().__init__(" Transcrio de udio", "700x600")
        self.ferramenta = FerramentaTranscricao(usar_gpu=USAR_GPU, modelo_tamanho="tiny")
        self.caminho_audio = None
        self.resultado_transcricao = None
        self.setup_interface()
    
    def setup_interface(self):
        # Ttulo
        titulo = ctk.CTkLabel(
            self.frame,
            text=" udio para Texto (Whisper)",
            font=("Arial", 22, "bold")
        )
        titulo.pack(pady=10)
        
        # Status GPU
        status = "[OK] GPU Ativa (GTX 1070 - 2GB)" if self.ferramenta.usar_gpu else "[AVISO] CPU"
        self.lbl_gpu = ctk.CTkLabel(self.frame, text=status)
        self.lbl_gpu.pack(pady=5)
        
        # Seleo de modelo
        self.frame_modelo = ctk.CTkFrame(self.frame)
        self.frame_modelo.pack(pady=10)
        
        self.lbl_modelo = ctk.CTkLabel(self.frame_modelo, text="Modelo:")
        self.lbl_modelo.pack(side="left", padx=5)
        
        self.modelo_var = ctk.StringVar(value="tiny")
        self.modelo_combo = ctk.CTkComboBox(
            self.frame_modelo,
            values=["tiny", "base", "small", "medium"],
            variable=self.modelo_var,
            width=100,
            command=self.trocar_modelo
        )
        self.modelo_combo.pack(side="left", padx=5)
        
        self.lbl_info = ctk.CTkLabel(
            self.frame_modelo,
            text="(tiny=1GB, base=1.5GB, small=2.5GB)"
        )
        self.lbl_info.pack(side="left", padx=5)
        
        # Seleo de arquivo
        self.btn_audio = ctk.CTkButton(
            self.frame,
            text=" Selecionar udio",
            command=self.selecionar_audio,
            width=200,
            height=40
        )
        self.btn_audio.pack(pady=10)
        
        self.lbl_arquivo = ctk.CTkLabel(
            self.frame,
            text="Nenhum arquivo selecionado",
            wraplength=500
        )
        self.lbl_arquivo.pack(pady=5)
        
        # Opes
        self.frame_opcoes = ctk.CTkFrame(self.frame)
        self.frame_opcoes.pack(pady=10, padx=10, fill="x")
        
        self.lbl_idioma = ctk.CTkLabel(self.frame_opcoes, text="Idioma:")
        self.lbl_idioma.pack(side="left", padx=5)
        
        self.idioma_var = ctk.StringVar(value="pt")
        self.idioma_combo = ctk.CTkComboBox(
            self.frame_opcoes,
            values=["pt", "en", "es", "fr", "de", "it", "ja", "zh"],
            variable=self.idioma_var,
            width=80
        )
        self.idioma_combo.pack(side="left", padx=5)
        
        self.timestamps_var = ctk.BooleanVar(value=False)
        self.chk_timestamps = ctk.CTkCheckBox(
            self.frame_opcoes,
            text="Incluir timestamps",
            variable=self.timestamps_var
        )
        self.chk_timestamps.pack(side="left", padx=20)
        
        # Boto processar
        self.btn_processar = ctk.CTkButton(
            self.frame,
            text=" Transcrever udio",
            command=self.processar,
            width=200,
            height=40,
            fg_color="green",
            state="disabled"
        )
        self.btn_processar.pack(pady=10)
        
        # Barra de progresso
        self.progress = ctk.CTkProgressBar(self.frame, width=400)
        self.progress.pack(pady=5)
        self.progress.set(0)
        
        # rea de texto resultado
        self.lbl_resultado = ctk.CTkLabel(self.frame, text="Transcrio:")
        self.lbl_resultado.pack(pady=(10,0))
        
        self.texto_resultado = ctk.CTkTextbox(self.frame, height=200)
        self.texto_resultado.pack(pady=5, padx=10, fill="both", expand=True)
        
        # Botes salvar
        self.frame_botoes = ctk.CTkFrame(self.frame)
        self.frame_botoes.pack(pady=5)
        
        self.btn_copiar = ctk.CTkButton(
            self.frame_botoes,
            text=" Copiar",
            command=self.copiar_texto,
            width=100,
            state="disabled"
        )
        self.btn_copiar.pack(side="left", padx=5)
        
        self.btn_salvar = ctk.CTkButton(
            self.frame_botoes,
            text=" Salvar TXT",
            command=self.salvar_texto,
            width=100,
            state="disabled"
        )
        self.btn_salvar.pack(side="left", padx=5)
        
        self.btn_salvar_srt = ctk.CTkButton(
            self.frame_botoes,
            text=" Salvar SRT",
            command=self.salvar_srt,
            width=100,
            state="disabled"
        )
        self.btn_salvar_srt.pack(side="left", padx=5)
    
    def trocar_modelo(self, choice):
        self.ferramenta = FerramentaTranscricao(
            usar_gpu=USAR_GPU,
            modelo_tamanho=choice
        )
    
    def selecionar_audio(self):
        caminho = self.utils.selecionar_arquivo(
            "Selecione um udio",
            [("udio", "*.mp3 *.wav *.m4a *.flac *.ogg")]
        )
        if caminho:
            self.caminho_audio = caminho
            self.lbl_arquivo.configure(text=f"Arquivo: {Path(caminho).name}")
            self.btn_processar.configure(state="normal")
    
    def processar(self):
        if not self.caminho_audio:
            return
        
        def transcrever():
            self.btn_processar.configure(state="disabled")
            self.progress.set(0.3)
            
            if self.timestamps_var.get():
                resultado, msg = self.ferramenta.processar_com_timestamps(self.caminho_audio)
            else:
                resultado, msg = self.ferramenta.processar(
                    self.caminho_audio,
                    idioma=self.idioma_var.get()
                )
            
            self.progress.set(0.8)
            
            if resultado:
                self.resultado_transcricao = resultado
                
                if self.timestamps_var.get():
                    texto_formatado = ""
                    for seg in resultado:
                        inicio = time.strftime('%H:%M:%S', time.gmtime(seg["início"]))
                        fim = time.strftime('%H:%M:%S', time.gmtime(seg["fim"]))
                        texto_formatado += f"[{início} --> {fim}] {seg['texto']}\n"
                else:
                    texto_formatado = resultado["texto"]
                    self.lbl_idioma_detectado = ctk.CTkLabel(
                        self.frame,
                        text=f"Idioma: {resultado['idioma_detectado']} ({resultado['probabilidade']:.2f})"
                    )
                    self.lbl_idioma_detectado.pack()
                
                self.texto_resultado.delete('1.0', 'end')
                self.texto_resultado.insert('1.0', texto_formatado)
                
                self.btn_copiar.configure(state="normal")
                self.btn_salvar.configure(state="normal")
                self.btn_salvar_srt.configure(state="normal")
            else:
                self.utils.mostrar_erro("Erro", msg)
            
            self.progress.set(1)
            self.btn_processar.configure(state="normal")
        
        thread = threading.Thread(target=transcrever)
        thread.start()
    
    def copiar_texto(self):
        self.frame.clipboard_clear()
        self.frame.clipboard_append(self.texto_resultado.get('1.0', 'end'))
        self.utils.mostrar_info("Copiado", "Texto copiado")
    
    def salvar_texto(self):
        caminho = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Texto", "*.txt")]
        )
        if caminho:
            with open(caminho, 'w', encoding='utf-8') as f:
                f.write(self.texto_resultado.get('1.0', 'end'))
            self.utils.mostrar_info("Sucesso", f"Salvo em:\n{caminho}")
    
    def salvar_srt(self):
        if self.timestamps_var.get() and self.resultado_transcricao:
            caminho = filedialog.asksaveasfilename(
                defaultextension=".srt",
                filetypes=[("Legendas", "*.srt")]
            )
            if caminho:
                with open(caminho, 'w', encoding='utf-8') as f:
                    for i, seg in enumerate(self.resultado_transcricao, 1):
                        inicio = time.strftime('%H:%M:%S,%f')[:-3].replace('.', ',')
                        fim = time.strftime('%H:%M:%S,%f')[:-3].replace('.', ',')
                        f.write(f"{i}\n")
                        f.write(f"{início} --> {fim}\n")
                        f.write(f"{seg['texto']}\n\n")
                self.utils.mostrar_info("Sucesso", "Legendas salvas")

class ModoIA_Transcricao:
    def __init__(self):
        self.ferramenta = FerramentaTranscricao(usar_gpu=USAR_GPU, modelo_tamanho="tiny")
        self.utils = Utils()
    
    def descobrir(self, pasta_teste):
        resultados = []
        audios = list(Path(pasta_teste).glob("*.mp3"))[:3]
        
        for audio_path in audios:
            resultado, _ = self.ferramenta.processar(str(audio_path))
            if resultado:
                resultados.append({
                    "audio": audio_path.name,
                    "texto": resultado["texto"][:100] + "..."
                })
        
        return resultados
    
    def processar_para_ia(self, caminho_audio, com_timestamps=False):
        if com_timestamps:
            resultado, msg = self.ferramenta.processar_com_timestamps(caminho_audio)
        else:
            resultado, msg = self.ferramenta.processar(caminho_audio)
        
        if resultado:
            return {
                "sucesso": True,
                "resultado": resultado
            }
        else:
            return {"sucesso": False, "erro": msg}

if __name__ == "__main__":
    if len(sys.argv) > 1:
        comando = sys.argv[1]
        ia = ModoIA_Transcricao()
        
        if comando == "--descobrir" and len(sys.argv) > 2:
            resultados = ia.descobrir(sys.argv[2])
            print(json.dumps(resultados, indent=2, ensure_ascii=False))
        
        elif comando == "--processar" and len(sys.argv) > 2:
            timestamps = len(sys.argv) > 3 and sys.argv[3] == "--timestamps"
            resultado = ia.processar_para_ia(sys.argv[2], timestamps)
            print(json.dumps(resultado, indent=2, ensure_ascii=False))
        
        else:
            print("Uso: ...")
    else:
        app = InterfaceTranscricao()
        app.rodar()

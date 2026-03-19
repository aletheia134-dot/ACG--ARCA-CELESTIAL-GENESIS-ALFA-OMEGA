# Ferramenta: Clonar Voz (RVC - Retrieval-based Voice Conversion)
# Usa RVC (2-3GB VRAM)

import sys
import os
import json
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent / "00_CORE"))
from src.modulos.utils import InterfaceBase, Utils
from src.config.config import PASTA_SAIDAS, PASTA_MODELOS, USAR_GPU

import customtkinter as ctk
from tkinter import filedialog, messagebox
import threading
import shutil
import subprocess
import requests
import zipfile

class FerramentaClonarVoz:
    def __init__(self, usar_gpu=True):
        self.usar_gpu = usar_gpu
        self.pasta_rvc = Path("C:/Ferramentas_IA/rvc")
        self.modelos_disponiveis = self._listar_modelos()
        
    def _listar_modelos(self):
        """Lista modelos de voz disponíveis"""
        modelos = []
        pasta_modelos = PASTA_MODELOS / "rvc_voices"
        if pasta_modelos.exists():
            modelos = [p.name for p in pasta_modelos.iterdir() if p.is_dir()]
        return modelos
    
    def baixar_modelo_base(self):
        """Baixa modelo base RVC do HuggingFace."""
        import logging
        logger = logging.getLogger("FerramentaClonarVoz")
        url_hubert = "https://huggingface.co/lj1995/VoiceConversionWebUI/resolve/main/hubert_base.pt"
        url_rmvpe  = "https://huggingface.co/lj1995/VoiceConversionWebUI/resolve/main/rmvpe.pt"
        destino = PASTA_MODELOS / "rvc_base"
        destino.mkdir(parents=True, exist_ok=True)
        for url, nome in [(url_hubert, "hubert_base.pt"), (url_rmvpe, "rmvpe.pt")]:
            destino_arquivo = destino / nome
            if destino_arquivo.exists():
                logger.info("Modelo já existe: %s", nome)
                continue
            try:
                logger.info("Baixando %s de %s ...", nome, url)
                r = requests.get(url, stream=True, timeout=120)
                r.raise_for_status()
                with open(destino_arquivo, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
                logger.info("[OK] %s baixado em %s", nome, destino_arquivo)
            except Exception as e:
                logger.error("[ERRO] Falha ao baixar %s: %s", nome, e)
                return False, str(e)
        return True, "Modelos base baixados"

    def clonar_voz(self, arquivo_audio, modelo_voz, arquivo_saida=None):
        """Clona voz usando RVC via subprocess (infer_cli.py ou rvc CLI)."""
        import logging
        import tempfile
        logger = logging.getLogger("FerramentaClonarVoz")
        try:
            arquivo_audio = Path(arquivo_audio)
            if not arquivo_audio.exists():
                return None, f"Arquivo de áudio não encontrado: {arquivo_audio}"

            if not arquivo_saida:
                arquivo_saida = PASTA_SAIDAS / f"voz_clonada_{Utils.get_timestamp()}.wav"
            arquivo_saida = Path(arquivo_saida)
            arquivo_saida.parent.mkdir(parents=True, exist_ok=True)

            # Tentar via rvc infer_cli.py
            infer_script = self.pasta_rvc / "infer_cli.py"
            model_path = PASTA_MODELOS / "rvc_voices" / modelo_voz / f"{modelo_voz}.pth"
            index_path = PASTA_MODELOS / "rvc_voices" / modelo_voz / f"{modelo_voz}.index"

            if infer_script.exists() and model_path.exists():
                cmd = [
                    sys.executable, str(infer_script),
                    "--input", str(arquivo_audio),
                    "--output", str(arquivo_saida),
                    "--model", str(model_path),
                    "--f0method", "rmvpe",
                ]
                if index_path.exists():
                    cmd += ["--index", str(index_path)]
                if self.usar_gpu:
                    cmd += ["--device", "cuda:0"]

                logger.info("Executando RVC: %s", " ".join(str(c) for c in cmd))
                result = subprocess.run(
                    cmd,
                    capture_output=True, text=True, timeout=300,
                    cwd=str(self.pasta_rvc)
                )
                if result.returncode == 0 and arquivo_saida.exists():
                    logger.info("[OK] Voz clonada: %s", arquivo_saida)
                    return str(arquivo_saida), "Sucesso"
                else:
                    erro = result.stderr.strip() or result.stdout.strip() or "Código de saída != 0"
                    logger.error("[ERRO] RVC falhou: %s", erro)
                    return None, f"RVC retornou erro: {erro}"

            # Tentar via servidor media (porta 5001)
            try:
                import base64
                with open(arquivo_audio, "rb") as f:
                    audio_b64 = base64.b64encode(f.read()).decode()
                resp = requests.post(
                    "http://localhost:5001/clonar_voz",
                    json={"audio_b64": audio_b64, "modelo": modelo_voz},
                    timeout=120
                )
                if resp.status_code == 200:
                    dados = resp.json()
                    resultado_b64 = dados.get("audio_b64")
                    if resultado_b64:
                        with open(arquivo_saida, "wb") as f:
                            f.write(base64.b64decode(resultado_b64))
                        return str(arquivo_saida), "Sucesso via servidor media"
                    return None, f"Servidor media retornou sem áudio: {dados}"
                return None, f"Servidor media retornou HTTP {resp.status_code}"
            except requests.exceptions.ConnectionError:
                logger.warning("Servidor media (5001) não acessível para clonagem de voz")

            return None, (
                f"RVC não encontrado em {self.pasta_rvc} e servidor media indisponível. "
                "Instale RVC em C:/Ferramentas_IA/rvc ou inicie o servidor media."
            )
        except subprocess.TimeoutExpired:
            return None, "Timeout: RVC demorou mais de 300s"
        except Exception as e:
            logger.exception("Erro em clonar_voz")
            return None, str(e)

    def treinar_modelo(self, pasta_amostras, nome_modelo):
        """Treina novo modelo de voz via RVC train CLI."""
        import logging
        logger = logging.getLogger("FerramentaClonarVoz")
        pasta_amostras = Path(pasta_amostras)
        if not pasta_amostras.exists():
            logger.error("Pasta de amostras não encontrada: %s", pasta_amostras)
            return False, f"Pasta não encontrada: {pasta_amostras}"

        train_script = self.pasta_rvc / "train_nsf_sim.py"
        if not train_script.exists():
            # Tentar via servidor media
            try:
                resp = requests.post(
                    "http://localhost:5001/treinar_voz",
                    json={"pasta_amostras": str(pasta_amostras), "nome_modelo": nome_modelo},
                    timeout=10
                )
                if resp.status_code == 200:
                    logger.info("[OK] Treinamento iniciado via servidor media: %s", resp.json())
                    return True, "Treinamento iniciado no servidor media"
                return False, f"Servidor media: HTTP {resp.status_code}"
            except requests.exceptions.ConnectionError:
                return False, (
                    f"Script de treinamento não encontrado em {train_script} "
                    "e servidor media indisponível. Instale RVC completo."
                )

        cmd = [
            sys.executable, str(train_script),
            "--trainset_dir", str(pasta_amostras),
            "--exp_dir", str(PASTA_MODELOS / "rvc_voices" / nome_modelo),
            "--sr", "40k",
            "--if_f0", "1",
            "--n_cpu", "4",
            "--gpu_ids", "0" if self.usar_gpu else "",
            "--total_epoch", "50",
            "--save_epoch", "10",
            "--batch_size", "4",
        ]
        logger.info("Iniciando treinamento RVC: %s", " ".join(str(c) for c in cmd))
        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                cwd=str(self.pasta_rvc)
            )
            # Logar saída em background
            import threading
            def _log_output():
                for line in proc.stdout:
                    logger.debug("RVC train: %s", line.rstrip())
            threading.Thread(target=_log_output, daemon=True).start()
            return True, f"Treinamento iniciado (PID {proc.pid})"
        except Exception as e:
            logger.exception("Erro ao iniciar treinamento RVC")
            return False, str(e)

class InterfaceClonarVoz(InterfaceBase):
    def __init__(self):
        super().__init__(" Clonar Voz (RVC)", "700x600")
        self.ferramenta = FerramentaClonarVoz(usar_gpu=USAR_GPU)
        self.setup_interface()
    
    def setup_interface(self):
        titulo = ctk.CTkLabel(
            self.frame,
            text=" Clonagem de Voz (RVC)",
            font=("Arial", 22, "bold")
        )
        titulo.pack(pady=10)
        
        # Status
        status = "[OK] RVC disponível" if self.ferramenta.modelos_disponiveis else "[AVISO] Nenhum modelo encontrado"
        self.lbl_status = ctk.CTkLabel(self.frame, text=status)
        self.lbl_status.pack(pady=5)
        
        # Abas
        self.tabview = ctk.CTkTabview(self.frame)
        self.tabview.pack(pady=10, padx=10, fill="both", expand=True)
        
        self.tab_clonar = self.tabview.add("Clonar Voz")
        self.tab_treinar = self.tabview.add("Treinar Modelo")
        
        # ===== ABA CLONAR =====
        # Seleo udio
        self.btn_audio_clonar = ctk.CTkButton(
            self.tab_clonar,
            text=" Selecionar udio para Clonar",
            command=self.selecionar_audio_clonar,
            width=200,
            height=40
        )
        self.btn_audio_clonar.pack(pady=10)
        
        self.lbl_audio_clonar = ctk.CTkLabel(
            self.tab_clonar,
            text="Nenhum udio selecionado"
        )
        self.lbl_audio_clonar.pack(pady=5)
        
        # Seleo modelo
        self.lbl_modelo = ctk.CTkLabel(
            self.tab_clonar,
            text="Modelo de voz alvo:"
        )
        self.lbl_modelo.pack(pady=(10,0))
        
        self.modelo_var = ctk.StringVar()
        self.modelo_combo = ctk.CTkComboBox(
            self.tab_clonar,
            values=self.ferramenta.modelos_disponiveis if self.ferramenta.modelos_disponiveis else ["Nenhum"],
            variable=self.modelo_var,
            width=200
        )
        self.modelo_combo.pack(pady=5)
        
        # Boto clonar
        self.btn_clonar = ctk.CTkButton(
            self.tab_clonar,
            text=" Clonar Voz",
            command=self.clonar_voz,
            width=200,
            height=40,
            fg_color="green",
            state="disabled"
        )
        self.btn_clonar.pack(pady=20)
        
        # ===== ABA TREINAR =====
        self.lbl_instrucao = ctk.CTkLabel(
            self.tab_treinar,
            text="Para treinar um novo modelo de voz:\n\n"
                 "1. Grave 5-10 minutos de udio limpo\n"
                 "2. Coloque em uma pasta\n"
                 "3. D um nome para o modelo",
            justify="left"
        )
        self.lbl_instrucao.pack(pady=10)
        
        self.btn_selecionar_amostras = ctk.CTkButton(
            self.tab_treinar,
            text=" Selecionar Pasta com Amostras",
            command=self.selecionar_pasta_amostras,
            width=200
        )
        self.btn_selecionar_amostras.pack(pady=10)
        
        self.lbl_amostras = ctk.CTkLabel(
            self.tab_treinar,
            text="Nenhuma pasta selecionada"
        )
        self.lbl_amostras.pack(pady=5)
        
        self.entry_nome_modelo = ctk.CTkEntry(
            self.tab_treinar,
            placeholder_text="Nome do novo modelo",
            width=200
        )
        self.entry_nome_modelo.pack(pady=10)
        
        self.btn_treinar = ctk.CTkButton(
            self.tab_treinar,
            text=" Iniciar Treinamento",
            command=self.treinar_modelo,
            width=200,
            fg_color="blue",
            state="disabled"
        )
        self.btn_treinar.pack(pady=10)
        
        # Barra de progresso
        self.progress = ctk.CTkProgressBar(self.frame, width=400)
        self.progress.pack(pady=10)
        self.progress.set(0)
        
        self.audio_para_clonar = None
        self.pasta_amostras = None
    
    def selecionar_audio_clonar(self):
        caminho = self.utils.selecionar_arquivo(
            "Selecione udio para clonar",
            [("udio", "*.mp3 *.wav *.flac")]
        )
        if caminho:
            self.audio_para_clonar = caminho
            self.lbl_audio_clonar.configure(text=f"udio: {Path(caminho).name}")
            if self.ferramenta.modelos_disponiveis:
                self.btn_clonar.configure(state="normal")
    
    def clonar_voz(self):
        def clonar_thread():
            self.btn_clonar.configure(state="disabled", text=" Clonando...")
            self.progress.set(0.3)
            
            caminho, msg = self.ferramenta.clonar_voz(
                self.audio_para_clonar,
                self.modelo_var.get()
            )
            
            self.progress.set(0.8)
            
            if caminho:
                self.utils.mostrar_info("Sucesso", f"Voz clonada:\n{caminho}")
            else:
                self.utils.mostrar_erro("Erro", msg)
            
            self.progress.set(1)
            self.btn_clonar.configure(state="normal", text=" Clonar Voz")
        
        threading.Thread(target=clonar_thread).start()
    
    def selecionar_pasta_amostras(self):
        pasta = self.utils.selecionar_pasta("Selecione pasta com amostras de udio")
        if pasta:
            self.pasta_amostras = pasta
            self.lbl_amostras.configure(text=f"Pasta: {pasta}")
            self.btn_treinar.configure(state="normal")
    
    def treinar_modelo(self):
        nome = self.entry_nome_modelo.get().strip()
        if not nome:
            self.utils.mostrar_erro("Erro", "Digite um nome para o modelo")
            return
        
        def treinar_thread():
            self.btn_treinar.configure(state="disabled", text="⏳ Treinando...")
            self.progress.set(0.2)

            sucesso, msg = self.ferramenta.treinar_modelo(self.pasta_amostras, nome)

            self.progress.set(1)
            if sucesso:
                self.utils.mostrar_info("Treinamento", f"Modelo '{nome}': {msg}")
            else:
                self.utils.mostrar_erro("Erro no Treinamento", msg)
            self.btn_treinar.configure(state="normal", text="🚀 Iniciar Treinamento")
        
        threading.Thread(target=treinar_thread).start()

if __name__ == "__main__":
    app = InterfaceClonarVoz()
    app.rodar()

# Ferramenta: Downloader de Arquivos
# Usa yt-dlp para vídeos/áudio e requests para arquivos

import sys
import os
import json
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent / "00_CORE"))
from src.utils.utils import InterfaceBase, Utils
from src.config.config import PASTA_SAIDAS

import customtkinter as ctk
from tkinter import filedialog, messagebox
import threading
import requests
from urllib.parse import urlparse
import re

try:
    import yt_dlp
    YT_DLP_AVAILABLE = True
except:
    YT_DLP_AVAILABLE = False
    print("âš ï¸ yt-dlp não instalado. Instale com: pip install yt-dlp")

class FerramentaDownloader:
    def __init__(self):
        self.pasta_downloads = PASTA_SAIDAS / "downloads"
        self.pasta_downloads.mkdir(exist_ok=True)
        self.downloads_ativos = {}
        
    def is_youtube_url(self, url):
        """Verifica se é URL do YouTube"""
        youtube_patterns = [
            r'(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/',
            r'(https?://)?(www\.)?(m\.)?(youtube|youtu)\.(com|be)/'
        ]
        for pattern in youtube_patterns:
            if re.match(pattern, url):
                return True
        return False
    
    def download_youtube(self, url, formato='mp4', qualidade='best', 
                         pasta=None, progress_callback=None):
        """Download de vídeos do YouTube"""
        if not YT_DLP_AVAILABLE:
            return None, "yt-dlp não instalado"
        
        try:
            if not pasta:
                pasta = self.pasta_downloads / "youtube"
            else:
                pasta = Path(pasta) / "youtube"
            
            pasta.mkdir(exist_ok=True, parents=True)
            
            # Configurações do yt-dlp
            ydl_opts = {
                'outtmpl': str(pasta / '%(title)s.%(ext)s'),
                'progress_hooks': [lambda d: self.progress_hook(d, progress_callback)],
                'quiet': True,
                'no_warnings': True,
            }
            
            # Configura formato
            if formato == 'mp3':
                ydl_opts.update({
                    'format': 'bestaudio/best',
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '192',
                    }],
                })
            else:  # vídeo
                if qualidade == 'melhor':
                    ydl_opts['format'] = 'bestvideo+bestaudio/best'
                elif qualidade == 'hd':
                    ydl_opts['format'] = 'bestvideo[height<=1080]+bestaudio/best'
                else:
                    ydl_opts['format'] = 'best'
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                nome_arquivo = ydl.prepare_filename(info)
                
                if formato == 'mp3':
                    nome_arquivo = nome_arquivo.rsplit('.', 1)[0] + '.mp3'
                
                return {
                    'arquivo': nome_arquivo,
                    'titulo': info.get('title', ''),
                    'duracao': info.get('duration', 0),
                    'tamanho': Path(nome_arquivo).stat().st_size if Path(nome_arquivo).exists() else 0
                }, "Sucesso"
                
        except Exception as e:
            return None, str(e)
    
    def download_arquivo(self, url, nome=None, pasta=None, progress_callback=None):
        """Download de arquivo comum"""
        try:
            if not pasta:
                pasta = self.pasta_downloads / "arquivos"
            else:
                pasta = Path(pasta) / "arquivos"
            
            pasta.mkdir(exist_ok=True, parents=True)
            
            # Obtém nome do arquivo
            if not nome:
                nome = url.split('/')[-1]
                if '?' in nome:
                    nome = nome.split('?')[0]
                if not nome:
                    nome = 'download'
            
            caminho = pasta / nome
            
            # Download com requests
            response = requests.get(url, stream=True)
            response.raise_for_status()
            
            # Tamanho total
            total_size = int(response.headers.get('content-length', 0))
            block_size = 8192
            
            with open(caminho, 'wb') as f:
                downloaded = 0
                for chunk in response.iter_content(chunk_size=block_size):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if progress_callback and total_size > 0:
                            progress = (downloaded / total_size) * 100
                            progress_callback(progress)
            
            return {
                'arquivo': str(caminho),
                'url': url,
                'tamanho': caminho.stat().st_size,
                'tipo': response.headers.get('content-type', 'desconhecido')
            }, "Sucesso"
            
        except Exception as e:
            return None, str(e)
    
    def progress_hook(self, d, callback):
        """Hook de progresso para yt-dlp"""
        if callback:
            if d['status'] == 'downloading':
                if 'total_bytes' in d:
                    progress = (d['downloaded_bytes'] / d['total_bytes']) * 100
                elif 'total_bytes_estimate' in d:
                    progress = (d['downloaded_bytes'] / d['total_bytes_estimate']) * 100
                else:
                    progress = 0
                callback(progress)
            elif d['status'] == 'finished':
                callback(100)
    
    def extrair_info(self, url):
        """Extrai informações do URL sem baixar"""
        if self.is_youtube_url(url):
            if not YT_DLP_AVAILABLE:
                return {"tipo": "youtube", "erro": "yt-dlp não instalado"}
            
            try:
                with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
                    info = ydl.extract_info(url, download=False)
                    return {
                        'tipo': 'youtube',
                        'titulo': info.get('title', ''),
                        'duracao': info.get('duration', 0),
                        'uploader': info.get('uploader', ''),
                        'views': info.get('view_count', 0),
                        'formato': info.get('ext', '')
                    }
            except Exception as e:
                return {'tipo': 'youtube', 'erro': str(e)}
        else:
            try:
                response = requests.head(url, allow_redirects=True, timeout=5)
                return {
                    'tipo': 'arquivo',
                    'tamanho': int(response.headers.get('content-length', 0)),
                    'tipo_conteudo': response.headers.get('content-type', 'desconhecido'),
                    'nome': url.split('/')[-1]
                }
            except:
                return {'tipo': 'desconhecido'}

class InterfaceDownloader(InterfaceBase):
    def __init__(self):
        super().__init__("ðŸ“¥ Downloader de Arquivos", "800x700")
        self.ferramenta = FerramentaDownloader()
        self.setup_interface()
    
    def setup_interface(self):
        titulo = ctk.CTkLabel(
            self.frame,
            text="ðŸ“¥ Downloader de Arquivos e Vídeos",
            font=("Arial", 24, "bold")
        )
        titulo.pack(pady=10)
        
        # Status yt-dlp
        status = "âœ… yt-dlp instalado" if YT_DLP_AVAILABLE else "âš ï¸ yt-dlp não instalado (YouTube não disponível)"
        self.lbl_status = ctk.CTkLabel(self.frame, text=status)
        self.lbl_status.pack(pady=5)
        
        # Abas
        self.tabview = ctk.CTkTabview(self.frame)
        self.tabview.pack(pady=10, padx=10, fill="both", expand=True)
        
        # Aba: YouTube
        self.tab_youtube = self.tabview.add("YouTube")
        self.setup_tab_youtube()
        
        # Aba: Arquivo Comum
        self.tab_arquivo = self.tabview.add("Arquivo Comum")
        self.setup_tab_arquivo()
        
        # Aba: Downloads Ativos
        self.tab_downloads = self.tabview.add("Downloads Ativos")
        self.setup_tab_downloads()
        
        # Pasta de download
        self.frame_pasta = ctk.CTkFrame(self.frame)
        self.frame_pasta.pack(pady=10, padx=10, fill="x")
        
        self.lbl_pasta = ctk.CTkLabel(self.frame_pasta, text="Pasta de downloads:")
        self.lbl_pasta.pack(side="left", padx=5)
        
        self.pasta_var = ctk.StringVar(value=str(self.ferramenta.pasta_downloads))
        self.entry_pasta = ctk.CTkEntry(
            self.frame_pasta,
            textvariable=self.pasta_var,
            width=300,
            state="disabled"
        )
        self.entry_pasta.pack(side="left", padx=5)
        
        self.btn_pasta = ctk.CTkButton(
            self.frame_pasta,
            text="ðŸ“ Alterar",
            command=self.alterar_pasta,
            width=80
        )
        self.btn_pasta.pack(side="left", padx=5)
        
        self.btn_abrir_pasta = ctk.CTkButton(
            self.frame_pasta,
            text="ðŸ“‚ Abrir",
            command=self.abrir_pasta,
            width=60
        )
        self.btn_abrir_pasta.pack(side="left", padx=5)
        
        # Barra de progresso global
        self.progress = ctk.CTkProgressBar(self.frame, width=400)
        self.progress.pack(pady=5)
        self.progress.set(0)
    
    def setup_tab_youtube(self):
        # URL
        self.frame_url = ctk.CTkFrame(self.tab_youtube)
        self.frame_url.pack(pady=10, padx=10, fill="x")
        
        self.lbl_url = ctk.CTkLabel(self.frame_url, text="URL do YouTube:")
        self.lbl_url.pack(side="left", padx=5)
        
        self.entry_url = ctk.CTkEntry(
            self.frame_url,
            placeholder_text="https://youtube.com/watch?v=...",
            width=400
        )
        self.entry_url.pack(side="left", padx=5)
        
        self.btn_info = ctk.CTkButton(
            self.frame_url,
            text="ðŸ” Info",
            command=self.extrair_info,
            width=60
        )
        self.btn_info.pack(side="left", padx=5)
        
        # Info
        self.frame_info = ctk.CTkFrame(self.tab_youtube)
        self.frame_info.pack(pady=5, padx=10, fill="x")
        
        self.lbl_info = ctk.CTkLabel(
            self.frame_info,
            text="Informações do vídeo aparecerão aqui",
            wraplength=600
        )
        self.lbl_info.pack(pady=5)
        
        # Opções
        self.frame_opcoes = ctk.CTkFrame(self.tab_youtube)
        self.frame_opcoes.pack(pady=10, padx=10, fill="x")
        
        # Formato
        self.frame_formato = ctk.CTkFrame(self.frame_opcoes)
        self.frame_formato.pack(pady=2, fill="x")
        
        self.lbl_formato = ctk.CTkLabel(self.frame_formato, text="Formato:")
        self.lbl_formato.pack(side="left", padx=5)
        
        self.formato_var = ctk.StringVar(value="mp4")
        self.radio_mp4 = ctk.CTkRadioButton(
            self.frame_formato,
            text="MP4 (Vídeo)",
            variable=self.formato_var,
            value="mp4"
        )
        self.radio_mp4.pack(side="left", padx=5)
        
        self.radio_mp3 = ctk.CTkRadioButton(
            self.frame_formato,
            text="MP3 (Íudio)",
            variable=self.formato_var,
            value="mp3"
        )
        self.radio_mp3.pack(side="left", padx=5)
        
        # Qualidade
        self.frame_qualidade = ctk.CTkFrame(self.frame_opcoes)
        self.frame_qualidade.pack(pady=2, fill="x")
        
        self.lbl_qualidade = ctk.CTkLabel(self.frame_qualidade, text="Qualidade:")
        self.lbl_qualidade.pack(side="left", padx=5)
        
        self.qualidade_var = ctk.StringVar(value="best")
        self.qualidade_combo = ctk.CTkComboBox(
            self.frame_qualidade,
            values=["melhor", "hd (1080p)", "media (720p)", "baixa (480p)"],
            variable=self.qualidade_var,
            width=150
        )
        self.qualidade_combo.pack(side="left", padx=5)
        
        # Botão download
        self.btn_download_yt = ctk.CTkButton(
            self.tab_youtube,
            text="ðŸ“¥ Download YouTube",
            command=self.download_youtube,
            width=200,
            height=40,
            fg_color="red"
        )
        self.btn_download_yt.pack(pady=20)
    
    def setup_tab_arquivo(self):
        # URL
        self.frame_url_arq = ctk.CTkFrame(self.tab_arquivo)
        self.frame_url_arq.pack(pady=10, padx=10, fill="x")
        
        self.lbl_url_arq = ctk.CTkLabel(self.frame_url_arq, text="URL do arquivo:")
        self.lbl_url_arq.pack(side="left", padx=5)
        
        self.entry_url_arq = ctk.CTkEntry(
            self.frame_url_arq,
            placeholder_text="https://...",
            width=450
        )
        self.entry_url_arq.pack(side="left", padx=5)
        
        self.btn_info_arq = ctk.CTkButton(
            self.frame_url_arq,
            text="ðŸ” Info",
            command=self.info_arquivo,
            width=60
        )
        self.btn_info_arq.pack(side="left", padx=5)
        
        # Info arquivo
        self.frame_info_arq = ctk.CTkFrame(self.tab_arquivo)
        self.frame_info_arq.pack(pady=5, padx=10, fill="x")
        
        self.lbl_info_arq = ctk.CTkLabel(
            self.frame_info_arq,
            text="Informações do arquivo",
            wraplength=600
        )
        self.lbl_info_arq.pack(pady=5)
        
        # Nome personalizado
        self.frame_nome = ctk.CTkFrame(self.tab_arquivo)
        self.frame_nome.pack(pady=10, padx=10, fill="x")
        
        self.lbl_nome = ctk.CTkLabel(self.frame_nome, text="Nome (opcional):")
        self.lbl_nome.pack(side="left", padx=5)
        
        self.entry_nome = ctk.CTkEntry(
            self.frame_nome,
            placeholder_text="Deixe em branco para usar nome original",
            width=300
        )
        self.entry_nome.pack(side="left", padx=5)
        
        # Botão download
        self.btn_download_arq = ctk.CTkButton(
            self.tab_arquivo,
            text="ðŸ“¥ Download Arquivo",
            command=self.download_arquivo,
            width=200,
            height=40,
            fg_color="blue"
        )
        self.btn_download_arq.pack(pady=20)
    
    def setup_tab_downloads(self):
        self.lbl_downloads = ctk.CTkLabel(
            self.tab_downloads,
            text="Downloads em andamento:",
            font=("Arial", 14)
        )
        self.lbl_downloads.pack(pady=5)
        
        self.frame_lista = ctk.CTkFrame(self.tab_downloads)
        self.frame_lista.pack(pady=10, padx=10, fill="both", expand=True)
        
        self.lista_downloads = ctk.CTkTextbox(self.frame_lista, height=200)
        self.lista_downloads.pack(fill="both", expand=True)
        self.lista_downloads.insert('end', "Nenhum download ativo")
    
    def alterar_pasta(self):
        pasta = filedialog.askdirectory(title="Selecione a pasta de downloads")
        if pasta:
            self.pasta_var.set(pasta)
            self.ferramenta.pasta_downloads = Path(pasta)
    
    def abrir_pasta(self):
        import subprocess
        subprocess.run(f'explorer "{self.pasta_var.get()}"')
    
    def extrair_info(self):
        url = self.entry_url.get().strip()
        if not url:
            self.utils.mostrar_erro("Erro", "Digite uma URL")
            return
        
        self.btn_info.configure(text="â³", state="disabled")
        
        def info_thread():
            info = self.ferramenta.extrair_info(url)
            
            if info.get('tipo') == 'youtube' and 'erro' not in info:
                texto = f"ðŸ“¹ {info['titulo']}\n"
                texto += f"ðŸ‘¤ {info['uploader']}\n"
                texto += f"â±ï¸ {info['duracao']//60}:{info['duracao']%60:02d}\n"
                texto += f"ðŸ‘ï¸ {info['views']:,} visualizações"
            elif info.get('tipo') == 'arquivo':
                texto = f"ðŸ“„ {info['nome']}\n"
                texto += f"ðŸ“¦ {info['tamanho']/(1024*1024):.1f} MB\n"
                texto += f"ðŸ“‹ {info['tipo_conteudo']}"
            else:
                texto = info.get('erro', 'Não foi possível obter informações')
            
            self.lbl_info.configure(text=texto)
            self.btn_info.configure(text="ðŸ” Info", state="normal")
        
        threading.Thread(target=info_thread).start()
    
    def info_arquivo(self):
        url = self.entry_url_arq.get().strip()
        if not url:
            self.utils.mostrar_erro("Erro", "Digite uma URL")
            return
        
        def info_thread():
            try:
                response = requests.head(url, allow_redirects=True, timeout=5)
                tamanho = int(response.headers.get('content-length', 0))
                tipo = response.headers.get('content-type', 'desconhecido')
                nome = url.split('/')[-1]
                
                texto = f"ðŸ“„ Nome: {nome}\n"
                texto += f"ðŸ“¦ Tamanho: {tamanho/(1024*1024):.1f} MB\n"
                texto += f"ðŸ“‹ Tipo: {tipo}"
                
                self.lbl_info_arq.configure(text=texto)
            except Exception as e:
                self.lbl_info_arq.configure(text=f"Erro: {str(e)}")
        
        threading.Thread(target=info_thread).start()
    
    def update_progress(self, valor):
        self.progress.set(valor / 100)
        self.frame.update()
    
    def download_youtube(self):
        url = self.entry_url.get().strip()
        if not url:
            self.utils.mostrar_erro("Erro", "Digite uma URL")
            return
        
        if not YT_DLP_AVAILABLE:
            self.utils.mostrar_erro("Erro", "yt-dlp não instalado")
            return
        
        self.btn_download_yt.configure(state="disabled", text="â³ Baixando...")
        self.progress.set(0)
        
        def download_thread():
            resultado, msg = self.ferramenta.download_youtube(
                url,
                formato=self.formato_var.get(),
                qualidade=self.qualidade_var.get().split()[0],
                pasta=self.pasta_var.get(),
                progress_callback=self.update_progress
            )
            
            if resultado:
                tamanho_mb = resultado['tamanho'] / (1024 * 1024)
                self.lista_downloads.insert('end', f"âœ… {Path(resultado['arquivo']).name} ({tamanho_mb:.1f} MB)\n")
                self.utils.mostrar_info("Sucesso", f"Download concluído!\n{resultado['arquivo']}")
            else:
                self.utils.mostrar_erro("Erro", msg)
            
            self.btn_download_yt.configure(state="normal", text="ðŸ“¥ Download YouTube")
            self.progress.set(0)
        
        threading.Thread(target=download_thread).start()
    
    def download_arquivo(self):
        url = self.entry_url_arq.get().strip()
        if not url:
            self.utils.mostrar_erro("Erro", "Digite uma URL")
            return
        
        nome = self.entry_nome.get().strip() or None
        
        self.btn_download_arq.configure(state="disabled", text="â³ Baixando...")
        self.progress.set(0)
        
        def download_thread():
            resultado, msg = self.ferramenta.download_arquivo(
                url,
                nome=nome,
                pasta=self.pasta_var.get(),
                progress_callback=self.update_progress
            )
            
            if resultado:
                tamanho_mb = resultado['tamanho'] / (1024 * 1024)
                self.lista_downloads.insert('end', f"âœ… {Path(resultado['arquivo']).name} ({tamanho_mb:.1f} MB)\n")
                self.utils.mostrar_info("Sucesso", f"Download concluído!\n{resultado['arquivo']}")
            else:
                self.utils.mostrar_erro("Erro", msg)
            
            self.btn_download_arq.configure(state="normal", text="ðŸ“¥ Download Arquivo")
            self.progress.set(0)
        
        threading.Thread(target=download_thread).start()

if __name__ == "__main__":
    app = InterfaceDownloader()
    app.rodar()

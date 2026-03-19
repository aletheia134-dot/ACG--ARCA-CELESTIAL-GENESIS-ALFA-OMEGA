# Ferramenta: Compressor de Arquivos (ZIP, RAR, 7z)
# Usa zipfile nativo + patool para outros formatos

import sys
import os
import json
import zipfile
import shutil
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent / "00_CORE"))
from src.modulos.utils import InterfaceBase, Utils
from src.config.config import PASTA_SAIDAS

import customtkinter as ctk
from tkinter import filedialog, messagebox
import threading

try:
    import patoolib
    PATOOL_AVAILABLE = True
except:
    PATOOL_AVAILABLE = False
    print("[AVISO] patool no instalado. Instale com: pip install patool")

class FerramentaCompressor:
    def __init__(self):
        self.formatos_suportados = {
            'zip': '.zip',
            'rar': '.rar',
            '7z': '.7z',
            'tar': '.tar',
            'gz': '.tar.gz',
            'bz2': '.tar.bz2'
        }
    
    def comprimir_arquivos(self, arquivos, nome_saida, formato='zip', 
                          nivel_compressao=9, pasta_destino=None):
        """
        Comprime arquivos/pastas
        
        Args:
            arquivos: Lista de caminhos
            nome_saida: Nome do arquivo (sem extenso)
            formato: zip, rar, 7z, tar, gz, bz2
            nivel_compressao: 0-9 (0=sem compresso, 9=máxima)
        """
        try:
            if not pasta_destino:
                pasta_destino = PASTA_SAIDAS / "compactados"
            else:
                pasta_destino = Path(pasta_destino)
            
            pasta_destino.mkdir(exist_ok=True, parents=True)
            
            extensao = self.formatos_suportados.get(formato, '.zip')
            arquivo_saida = pasta_destino / f"{nome_saida}{extensao}"
            
            # Estatsticas
            stats = {
                'total_arquivos': len(arquivos),
                'tamanho_original': 0,
                'tamanho_compactado': 0,
                'arquivos_processados': []
            }
            
            # Calcula tamanho original
            for item in arquivos:
                path = Path(item)
                if path.exists():
                    if path.is_file():
                        stats['tamanho_original'] += path.stat().st_size
                    elif path.is_dir():
                        for root, dirs, files in os.walk(path):
                            for file in files:
                                stats['tamanho_original'] += (Path(root) / file).stat().st_size
            
            # Compresso ZIP (nativo)
            if formato == 'zip':
                with zipfile.ZipFile(arquivo_saida, 'w', 
                                    zipfile.ZIP_DEFLATED, 
                                    compresslevel=nivel_compressao) as zipf:
                    
                    for item in arquivos:
                        path = Path(item)
                        if path.is_file():
                            zipf.write(path, path.name)
                            stats['arquivos_processados'].append(str(path))
                        elif path.is_dir():
                            for root, dirs, files in os.walk(path):
                                for file in files:
                                    arquivo = Path(root) / file
                                    arcname = arquivo.relative_to(path.parent)
                                    zipf.write(arquivo, arcname)
                                    stats['arquivos_processados'].append(str(arquivo))
            
            # Outros formatos (precisa de patool)
            elif PATOOL_AVAILABLE:
                patoolib.create_archive(
                    str(arquivo_saida),
                    [str(a) for a in arquivos],
                    verbosity=-1
                )
            else:
                return None, f"Formato {formato} requer patool (pip install patool)"
            
            # Tamanho compactado
            if arquivo_saida.exists():
                stats['tamanho_compactado'] = arquivo_saida.stat().st_size
                
                # Razo de compresso
                if stats['tamanho_original'] > 0:
                    stats['taxa_compressao'] = (
                        (1 - stats['tamanho_compactado'] / stats['tamanho_original']) * 100
                    )
            
            return {
                'arquivo': str(arquivo_saida),
                'stats': stats
            }, "Sucesso"
            
        except Exception as e:
            return None, str(e)
    
    def descomprimir(self, arquivo, pasta_destino=None):
        """Descomprime arquivo"""
        try:
            arquivo = Path(arquivo)
            
            if not arquivo.exists():
                return None, "Arquivo no encontrado"
            
            if not pasta_destino:
                pasta_destino = arquivo.parent / arquivo.stem
            else:
                pasta_destino = Path(pasta_destino) / arquivo.stem
            
            pasta_destino.mkdir(exist_ok=True, parents=True)
            
            # ZIP
            if arquivo.suffix.lower() == '.zip':
                with zipfile.ZipFile(arquivo, 'r') as zipf:
                    zipf.extractall(pasta_destino)
            
            # Outros formatos
            elif PATOOL_AVAILABLE:
                patoolib.extract_archive(
                    str(arquivo),
                    outdir=str(pasta_destino),
                    verbosity=-1
                )
            else:
                return None, f"Formato {arquivo.suffix} requer patool"
            
            # Lista arquivos extrados
            arquivos_extraidos = []
            for root, dirs, files in os.walk(pasta_destino):
                for file in files:
                    arquivos_extraidos.append(str(Path(root) / file))
            
            return {
                'pasta': str(pasta_destino),
                'arquivos': arquivos_extraidos,
                'total': len(arquivos_extraidos)
            }, "Sucesso"
            
        except Exception as e:
            return None, str(e)
    
    def listar_conteudo(self, arquivo):
        """Lista contedo do arquivo compactado"""
        try:
            arquivo = Path(arquivo)
            
            if not arquivo.exists():
                return None, "Arquivo no encontrado"
            
            conteudo = []
            
            # ZIP
            if arquivo.suffix.lower() == '.zip':
                with zipfile.ZipFile(arquivo, 'r') as zipf:
                    for info in zipf.infolist():
                        conteudo.append({
                            'nome': info.filename,
                            'tamanho': info.file_size,
                            'compactado': info.compress_size,
                            'taxa': (1 - info.compress_size/info.file_size)*100 if info.file_size > 0 else 0
                        })
            
            return conteudo, "Sucesso"
            
        except Exception as e:
            return None, str(e)

class InterfaceCompressor(InterfaceBase):
    def __init__(self):
        super().__init__(" Compressor de Arquivos", "800x700")
        self.ferramenta = FerramentaCompressor()
        self.arquivos_selecionados = []
        self.setup_interface()
    
    def setup_interface(self):
        titulo = ctk.CTkLabel(
            self.frame,
            text=" Compressor e Descompressor de Arquivos",
            font=("Arial", 24, "bold")
        )
        titulo.pack(pady=10)
        
        # Abas
        self.tabview = ctk.CTkTabview(self.frame)
        self.tabview.pack(pady=10, padx=10, fill="both", expand=True)
        
        # Aba: Comprimir
        self.tab_comprimir = self.tabview.add("Comprimir")
        self.setup_tab_comprimir()
        
        # Aba: Descomprimir
        self.tab_descomprimir = self.tabview.add("Descomprimir")
        self.setup_tab_descomprimir()
        
        # Aba: Listar
        self.tab_listar = self.tabview.add("Listar Contedo")
        self.setup_tab_listar()
        
        # Barra de progresso
        self.progress = ctk.CTkProgressBar(self.frame, width=400)
        self.progress.pack(pady=5)
        self.progress.set(0)
    
    def setup_tab_comprimir(self):
        # Lista de arquivos
        self.lbl_lista = ctk.CTkLabel(
            self.tab_comprimir,
            text="Arquivos para comprimir:",
            font=("Arial", 14)
        )
        self.lbl_lista.pack(pady=5)
        
        self.frame_lista = ctk.CTkFrame(self.tab_comprimir, height=150)
        self.frame_lista.pack(pady=5, padx=10, fill="x")
        
        self.lista_texto = ctk.CTkTextbox(self.frame_lista, height=120)
        self.lista_texto.pack(fill="both", expand=True)
        
        # Botes adicionar
        self.frame_botoes = ctk.CTkFrame(self.tab_comprimir)
        self.frame_botoes.pack(pady=5)
        
        self.btn_add_arquivos = ctk.CTkButton(
            self.frame_botoes,
            text=" Adicionar Arquivos",
            command=self.adicionar_arquivos,
            width=150
        )
        self.btn_add_arquivos.pack(side="left", padx=5)
        
        self.btn_add_pasta = ctk.CTkButton(
            self.frame_botoes,
            text=" Adicionar Pasta",
            command=self.adicionar_pasta,
            width=150
        )
        self.btn_add_pasta.pack(side="left", padx=5)
        
        self.btn_limpar = ctk.CTkButton(
            self.frame_botoes,
            text=" Limpar",
            command=self.limpar_lista,
            width=100
        )
        self.btn_limpar.pack(side="left", padx=5)
        
        # Opes
        self.frame_opcoes = ctk.CTkFrame(self.tab_comprimir)
        self.frame_opcoes.pack(pady=10, padx=10, fill="x")
        
        # Formato
        self.frame_formato = ctk.CTkFrame(self.frame_opcoes)
        self.frame_formato.pack(pady=2, fill="x")
        
        self.lbl_formato = ctk.CTkLabel(self.frame_formato, text="Formato:")
        self.lbl_formato.pack(side="left", padx=5)
        
        self.formato_var = ctk.StringVar(value="zip")
        formatos = ["zip", "rar", "7z", "tar", "gz", "bz2"]
        self.formato_combo = ctk.CTkComboBox(
            self.frame_formato,
            values=formatos,
            variable=self.formato_var,
            width=100
        )
        self.formato_combo.pack(side="left", padx=5)
        
        # nível compresso
        self.frame_nivel = ctk.CTkFrame(self.frame_opcoes)
        self.frame_nivel.pack(pady=2, fill="x")
        
        self.lbl_nivel = ctk.CTkLabel(self.frame_nivel, text="Compresso:")
        self.lbl_nivel.pack(side="left", padx=5)
        
        self.nivel_var = ctk.IntVar(value=9)
        self.nivel_slider = ctk.CTkSlider(
            self.frame_nivel,
            from_=0,
            to=9,
            number_of_steps=9,
            variable=self.nivel_var
        )
        self.nivel_slider.pack(side="left", padx=5, fill="x", expand=True)
        
        self.lbl_nivel_valor = ctk.CTkLabel(self.frame_nivel, text="9")
        self.lbl_nivel_valor.pack(side="left", padx=5)
        
        def atualizar_nivel(valor):
            self.lbl_nivel_valor.configure(text=str(int(valor)))
        
        self.nivel_slider.configure(command=atualizar_nivel)
        
        # Nome do arquivo
        self.frame_nome = ctk.CTkFrame(self.frame_opcoes)
        self.frame_nome.pack(pady=2, fill="x")
        
        self.lbl_nome = ctk.CTkLabel(self.frame_nome, text="Nome do arquivo:")
        self.lbl_nome.pack(side="left", padx=5)
        
        self.entry_nome = ctk.CTkEntry(
            self.frame_nome,
            placeholder_text="meu_arquivo",
            width=200
        )
        self.entry_nome.pack(side="left", padx=5)
        
        # Boto comprimir
        self.btn_comprimir = ctk.CTkButton(
            self.tab_comprimir,
            text=" Comprimir",
            command=self.comprimir,
            width=200,
            height=40,
            fg_color="green"
        )
        self.btn_comprimir.pack(pady=10)
    
    def setup_tab_descomprimir(self):
        self.frame_arquivo = ctk.CTkFrame(self.tab_descomprimir)
        self.frame_arquivo.pack(pady=20, padx=10, fill="x")
        
        self.lbl_arquivo = ctk.CTkLabel(self.frame_arquivo, text="Arquivo:")
        self.lbl_arquivo.pack(side="left", padx=5)
        
        self.arquivo_var = ctk.StringVar()
        self.entry_arquivo = ctk.CTkEntry(
            self.frame_arquivo,
            textvariable=self.arquivo_var,
            width=400
        )
        self.entry_arquivo.pack(side="left", padx=5)
        
        self.btn_selecionar = ctk.CTkButton(
            self.frame_arquivo,
            text=" Selecionar",
            command=self.selecionar_arquivo,
            width=80
        )
        self.btn_selecionar.pack(side="left", padx=5)
        
        self.frame_pasta = ctk.CTkFrame(self.tab_descomprimir)
        self.frame_pasta.pack(pady=10, padx=10, fill="x")
        
        self.lbl_pasta = ctk.CTkLabel(self.frame_pasta, text="Pasta destino:")
        self.lbl_pasta.pack(side="left", padx=5)
        
        self.pasta_destino_var = ctk.StringVar()
        self.entry_pasta = ctk.CTkEntry(
            self.frame_pasta,
            textvariable=self.pasta_destino_var,
            width=400
        )
        self.entry_pasta.pack(side="left", padx=5)
        
        self.btn_pasta = ctk.CTkButton(
            self.frame_pasta,
            text=" Selecionar",
            command=self.selecionar_pasta_destino,
            width=80
        )
        self.btn_pasta.pack(side="left", padx=5)
        
        self.btn_descomprimir = ctk.CTkButton(
            self.tab_descomprimir,
            text=" Descomprimir",
            command=self.descomprimir,
            width=200,
            height=40,
            fg_color="blue"
        )
        self.btn_descomprimir.pack(pady=20)
    
    def setup_tab_listar(self):
        self.frame_listar = ctk.CTkFrame(self.tab_listar)
        self.frame_listar.pack(pady=20, padx=10, fill="x")
        
        self.lbl_listar = ctk.CTkLabel(self.frame_listar, text="Arquivo:")
        self.lbl_listar.pack(side="left", padx=5)
        
        self.listar_var = ctk.StringVar()
        self.entry_listar = ctk.CTkEntry(
            self.frame_listar,
            textvariable=self.listar_var,
            width=400
        )
        self.entry_listar.pack(side="left", padx=5)
        
        self.btn_listar = ctk.CTkButton(
            self.frame_listar,
            text=" Listar",
            command=self.listar_conteudo,
            width=80
        )
        self.btn_listar.pack(side="left", padx=5)
        
        self.texto_lista = ctk.CTkTextbox(self.tab_listar, height=300)
        self.texto_lista.pack(pady=10, padx=10, fill="both", expand=True)
    
    def adicionar_arquivos(self):
        arquivos = filedialog.askopenfilenes()
        for arquivo in arquivos:
            if arquivo not in self.arquivos_selecionados:
                self.arquivos_selecionados.append(arquivo)
                self.lista_texto.insert('end', f" {Path(arquivo).name}\n")
    
    def adicionar_pasta(self):
        pasta = filedialog.askdirectory()
        if pasta:
            if pasta not in self.arquivos_selecionados:
                self.arquivos_selecionados.append(pasta)
                self.lista_texto.insert('end', f" {Path(pasta).name}/\n")
    
    def limpar_lista(self):
        self.arquivos_selecionados = []
        self.lista_texto.delete('1.0', 'end')
    
    def selecionar_arquivo(self):
        arquivo = filedialog.askopenfilename()
        if arquivo:
            self.arquivo_var.set(arquivo)
    
    def selecionar_pasta_destino(self):
        pasta = filedialog.askdirectory()
        if pasta:
            self.pasta_destino_var.set(pasta)
    
    def comprimir(self):
        if not self.arquivos_selecionados:
            self.utils.mostrar_erro("Erro", "Adicione arquivos para comprimir")
            return
        
        nome = self.entry_nome.get().strip()
        if not nome:
            nome = "arquivo_compactado"
        
        def comprimir_thread():
            self.btn_comprimir.configure(state="disabled", text=" Comprimindo...")
            self.progress.set(0.3)
            
            resultado, msg = self.ferramenta.comprimir_arquivos(
                self.arquivos_selecionados,
                nome,
                formato=self.formato_var.get(),
                nivel_compressao=self.nivel_var.get()
            )
            
            self.progress.set(0.8)
            
            if resultado:
                stats = resultado['stats']
                texto = f"[OK] Compactado com sucesso!\n\n"
                texto += f"Arquivo: {Path(resultado['arquivo']).name}\n"
                texto += f"Original: {stats['tamanho_original']/(1024*1024):.2f} MB\n"
                texto += f"Compactado: {stats['tamanho_compactado']/(1024*1024):.2f} MB\n"
                texto += f"Taxa: {stats['taxa_compressao']:.1f}%\n"
                
                self.texto_lista.delete('1.0', 'end')
                self.texto_lista.insert('1.0', texto)
                
                self.utils.mostrar_info("Sucesso", f"Arquivo salvo:\n{resultado['arquivo']}")
            else:
                self.utils.mostrar_erro("Erro", msg)
            
            self.progress.set(1)
            self.btn_comprimir.configure(state="normal", text=" Comprimir")
        
        threading.Thread(target=comprimir_thread).start()
    
    def descomprimir(self):
        arquivo = self.arquivo_var.get()
        if not arquivo:
            self.utils.mostrar_erro("Erro", "Selecione um arquivo")
            return
        
        pasta_destino = self.pasta_destino_var.get() or None
        
        def descomprimir_thread():
            self.btn_descomprimir.configure(state="disabled", text=" Descomprimindo...")
            self.progress.set(0.3)
            
            resultado, msg = self.ferramenta.descomprimir(arquivo, pasta_destino)
            
            self.progress.set(0.8)
            
            if resultado:
                texto = f"[OK] Descompactado com sucesso!\n\n"
                texto += f"Pasta: {resultado['pasta']}\n"
                texto += f"Arquivos: {resultado['total']}\n"
                
                self.texto_lista.delete('1.0', 'end')
                self.texto_lista.insert('1.0', texto)
                
                self.utils.mostrar_info("Sucesso", f"Arquivos extrados para:\n{resultado['pasta']}")
            else:
                self.utils.mostrar_erro("Erro", msg)
            
            self.progress.set(1)
            self.btn_descomprimir.configure(state="normal", text=" Descomprimir")
        
        threading.Thread(target=descomprimir_thread).start()
    
    def listar_conteudo(self):
        arquivo = self.listar_var.get()
        if not arquivo:
            self.utils.mostrar_erro("Erro", "Selecione um arquivo")
            return
        
        conteudo, msg = self.ferramenta.listar_conteudo(arquivo)
        
        if conteudo:
            self.texto_lista.delete('1.0', 'end')
            texto = f" Contedo de {Path(arquivo).name}:\n\n"
            
            for item in conteudo:
                texto += f" {item['nome']}\n"
                texto += f"   Tamanho: {item['tamanho']/1024:.1f} KB\n"
                texto += f"   Compactado: {item['compactado']/1024:.1f} KB\n"
                texto += f"   Taxa: {item['taxa']:.1f}%\n\n"
            
            self.texto_lista.insert('1.0', texto)
        else:
            self.utils.mostrar_erro("Erro", msg)

if __name__ == "__main__":
    app = InterfaceCompressor()
    app.rodar()

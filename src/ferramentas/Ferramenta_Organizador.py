# Ferramenta: Organizador de Arquivos por Tipo/Data
# Organiza automaticamente pastas

import sys
import os
import json
import shutil
from pathlib import Path
from datetime import datetime

sys.path.append(str(Path(__file__).parent.parent / "00_CORE"))
from src.utils.utils import InterfaceBase, Utils
from src.config.config import PASTA_SAIDAS

import customtkinter as ctk
from tkinter import filedialog, messagebox
import threading

class FerramentaOrganizador:
    def __init__(self):
        self.regras = {
            # Imagens
            'imagens': {
                'extensoes': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp', '.ico'],
                'pasta': 'Imagens'
            },
            # Vídeos
            'videos': {
                'extensoes': ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v'],
                'pasta': 'Vídeos'
            },
            # Íudio
            'audio': {
                'extensoes': ['.mp3', '.wav', '.flac', '.aac', '.ogg', '.m4a', '.wma'],
                'pasta': 'Íudio'
            },
            # Documentos
            'documentos': {
                'extensoes': ['.pdf', '.doc', '.docx', '.txt', '.rtf', '.odt', '.xls', '.xlsx', 
                             '.ppt', '.pptx', '.csv', '.md'],
                'pasta': 'Documentos'
            },
            # Compactados
            'compactados': {
                'extensoes': ['.zip', '.rar', '.7z', '.tar', '.gz', '.bz2'],
                'pasta': 'Compactados'
            },
            # Programas
            'programas': {
                'extensoes': ['.exe', '.msi', '.bat', '.sh', '.app', '.deb', '.rpm'],
                'pasta': 'Programas'
            },
            # Código
            'codigo': {
                'extensoes': ['.py', '.js', '.html', '.css', '.cpp', '.c', '.java', '.php', 
                             '.rb', '.go', '.rs', '.swift'],
                'pasta': 'Código'
            },
            # Outros
            'outros': {
                'extensoes': [],
                'pasta': 'Outros'
            }
        }
        
        self.estatisticas = {}
    
    def organizar_por_tipo(self, pasta_origem, pasta_destino=None, 
                           mover=True, criar_subpastas=True):
        """
        Organiza arquivos por tipo
        
        Args:
            pasta_origem: Pasta a ser organizada
            pasta_destino: Pasta destino (se None, usa a própria pasta)
            mover: True move, False copia
            criar_subpastas: Cria subpastas por categoria
        """
        try:
            origem = Path(pasta_origem)
            if not origem.exists():
                return None, "Pasta de origem não existe"
            
            if pasta_destino:
                destino = Path(pasta_destino)
            else:
                destino = origem
            
            # Contadores
            stats = {
                'processados': 0,
                'movidos': 0,
                'ignorados': 0,
                'erros': 0,
                'por_categoria': {}
            }
            
            # Itera pelos arquivos
            for arquivo in origem.iterdir():
                if arquivo.is_file():
                    stats['processados'] += 1
                    
                    # Determina categoria
                    extensao = arquivo.suffix.lower()
                    categoria = self._get_categoria(extensao)
                    
                    # Conta por categoria
                    if categoria not in stats['por_categoria']:
                        stats['por_categoria'][categoria] = 0
                    stats['por_categoria'][categoria] += 1
                    
                    # Define pasta destino
                    if criar_subpastas:
                        pasta_destino_final = destino / self.regras[categoria]['pasta']
                    else:
                        pasta_destino_final = destino
                    
                    pasta_destino_final.mkdir(exist_ok=True)
                    
                    # Move ou copia
                    try:
                        if mover:
                            shutil.move(str(arquivo), str(pasta_destino_final / arquivo.name))
                        else:
                            shutil.copy2(str(arquivo), str(pasta_destino_final / arquivo.name))
                        stats['movidos'] += 1
                    except Exception as e:
                        stats['erros'] += 1
                        print(f"Erro ao processar {arquivo.name}: {e}")
            
            return stats, "Sucesso"
            
        except Exception as e:
            return None, str(e)
    
    def organizar_por_data(self, pasta_origem, pasta_destino=None,
                          formato='%Y/%m', mover=True):
        """
        Organiza arquivos por data de modificação
        
        formatos:
            '%Y' - só ano
            '%Y/%m' - ano/mês
            '%Y/%m/%d' - ano/mês/dia
        """
        try:
            origem = Path(pasta_origem)
            if not origem.exists():
                return None, "Pasta de origem não existe"
            
            if pasta_destino:
                destino = Path(pasta_destino)
            else:
                destino = origem
            
            stats = {
                'processados': 0,
                'movidos': 0,
                'erros': 0,
                'por_data': {}
            }
            
            for arquivo in origem.iterdir():
                if arquivo.is_file():
                    stats['processados'] += 1
                    
                    # Obtém data de modificação
                    mod_time = arquivo.stat().st_mtime
                    data = datetime.fromtimestamp(mod_time)
                    
                    # Cria caminho baseado na data
                    if formato == '%Y':
                        pasta_data = destino / str(data.year)
                    elif formato == '%Y/%m':
                        pasta_data = destino / str(data.year) / f"{data.month:02d}"
                    elif formato == '%Y/%m/%d':
                        pasta_data = destino / str(data.year) / f"{data.month:02d}" / f"{data.day:02d}"
                    else:
                        pasta_data = destino / data.strftime(formato).replace('/', os.sep)
                    
                    pasta_data.mkdir(exist_ok=True, parents=True)
                    
                    # Contagem
                    data_str = data.strftime('%Y-%m')
                    if data_str not in stats['por_data']:
                        stats['por_data'][data_str] = 0
                    stats['por_data'][data_str] += 1
                    
                    # Move
                    try:
                        if mover:
                            shutil.move(str(arquivo), str(pasta_data / arquivo.name))
                        else:
                            shutil.copy2(str(arquivo), str(pasta_data / arquivo.name))
                        stats['movidos'] += 1
                    except:
                        stats['erros'] += 1
            
            return stats, "Sucesso"
            
        except Exception as e:
            return None, str(e)
    
    def organizar_por_tamanho(self, pasta_origem, pasta_destino=None, mover=True):
        """Organiza por tamanho (pequeno, médio, grande)"""
        try:
            origem = Path(pasta_origem)
            if not origem.exists():
                return None, "Pasta de origem não existe"
            
            if pasta_destino:
                destino = Path(pasta_destino)
            else:
                destino = origem
            
            # Cria pastas
            pequenos = destino / "Pequenos (<1MB)"
            medios = destino / "Médios (1-10MB)"
            grandes = destino / "Grandes (>10MB)"
            
            pequenos.mkdir(exist_ok=True)
            medios.mkdir(exist_ok=True)
            grandes.mkdir(exist_ok=True)
            
            stats = {
                'processados': 0,
                'pequenos': 0,
                'medios': 0,
                'grandes': 0,
                'erros': 0
            }
            
            for arquivo in origem.iterdir():
                if arquivo.is_file():
                    stats['processados'] += 1
                    
                    tamanho_kb = arquivo.stat().st_size / 1024
                    
                    if tamanho_kb < 1024:  # < 1MB
                        destino_final = pequenos
                        stats['pequenos'] += 1
                    elif tamanho_kb < 10240:  # 1-10MB
                        destino_final = medios
                        stats['medios'] += 1
                    else:  # > 10MB
                        destino_final = grandes
                        stats['grandes'] += 1
                    
                    try:
                        if mover:
                            shutil.move(str(arquivo), str(destino_final / arquivo.name))
                        else:
                            shutil.copy2(str(arquivo), str(destino_final / arquivo.name))
                    except:
                        stats['erros'] += 1
            
            return stats, "Sucesso"
            
        except Exception as e:
            return None, str(e)
    
    def organizar_por_nome(self, pasta_origem, padrao, pasta_destino=None, mover=True):
        """Organiza por padrão no nome (ex: começa com letra)"""
        try:
            origem = Path(pasta_origem)
            if not origem.exists():
                return None, "Pasta de origem não existe"
            
            if pasta_destino:
                destino = Path(pasta_destino)
            else:
                destino = origem
            
            stats = {
                'processados': 0,
                'movidos': 0,
                'erros': 0
            }
            
            for arquivo in origem.iterdir():
                if arquivo.is_file():
                    stats['processados'] += 1
                    
                    # Aplica padrão
                    if padrao == 'primeira_letra':
                        letra = arquivo.name[0].upper()
                        if not letra.isalpha():
                            letra = '#'
                        pasta_final = destino / letra
                    elif padrao == 'extensao':
                        ext = arquivo.suffix[1:].upper() if arquivo.suffix else 'SEM_EXT'
                        pasta_final = destino / ext
                    else:
                        continue
                    
                    pasta_final.mkdir(exist_ok=True)
                    
                    try:
                        if mover:
                            shutil.move(str(arquivo), str(pasta_final / arquivo.name))
                        else:
                            shutil.copy2(str(arquivo), str(pasta_final / arquivo.name))
                        stats['movidos'] += 1
                    except:
                        stats['erros'] += 1
            
            return stats, "Sucesso"
            
        except Exception as e:
            return None, str(e)
    
    def _get_categoria(self, extensao):
        """Retorna categoria baseada na extensão"""
        for categoria, dados in self.regras.items():
            if extensao in dados['extensoes']:
                return categoria
        return 'outros'
    
    def limpar_pastas_vazias(self, pasta):
        """Remove pastas vazias recursivamente"""
        try:
            removidas = 0
            for root, dirs, files in os.walk(pasta, topdown=False):
                for dir in dirs:
                    caminho = Path(root) / dir
                    if not any(caminho.iterdir()):
                        caminho.rmdir()
                        removidas += 1
            return removidas
        except Exception as e:
            return 0

class InterfaceOrganizador(InterfaceBase):
    def __init__(self):
        super().__init__("ðŸ“ Organizador de Arquivos", "800x700")
        self.ferramenta = FerramentaOrganizador()
        self.setup_interface()
    
    def setup_interface(self):
        titulo = ctk.CTkLabel(
            self.frame,
            text="ðŸ“ Organizador Automático de Arquivos",
            font=("Arial", 24, "bold")
        )
        titulo.pack(pady=10)
        
        # Seleção de pasta
        self.frame_pasta = ctk.CTkFrame(self.frame)
        self.frame_pasta.pack(pady=10, padx=10, fill="x")
        
        self.lbl_pasta = ctk.CTkLabel(self.frame_pasta, text="Pasta a organizar:")
        self.lbl_pasta.pack(side="left", padx=5)
        
        self.pasta_var = ctk.StringVar()
        self.entry_pasta = ctk.CTkEntry(
            self.frame_pasta,
            textvariable=self.pasta_var,
            width=400
        )
        self.entry_pasta.pack(side="left", padx=5)
        
        self.btn_pasta = ctk.CTkButton(
            self.frame_pasta,
            text="ðŸ“ Selecionar",
            command=self.selecionar_pasta,
            width=80
        )
        self.btn_pasta.pack(side="left", padx=5)
        
        # Opções
        self.frame_opcoes = ctk.CTkFrame(self.frame)
        self.frame_opcoes.pack(pady=10, padx=10, fill="x")
        
        self.mover_var = ctk.BooleanVar(value=True)
        self.chk_mover = ctk.CTkCheckBox(
            self.frame_opcoes,
            text="Mover arquivos (desmarcar para copiar)",
            variable=self.mover_var
        )
        self.chk_mover.pack(pady=2)
        
        # Abas de organização
        self.tabview = ctk.CTkTabview(self.frame)
        self.tabview.pack(pady=10, padx=10, fill="both", expand=True)
        
        # Aba: Por Tipo
        self.tab_tipo = self.tabview.add("Por Tipo")
        self.setup_tab_tipo()
        
        # Aba: Por Data
        self.tab_data = self.tabview.add("Por Data")
        self.setup_tab_data()
        
        # Aba: Por Tamanho
        self.tab_tamanho = self.tabview.add("Por Tamanho")
        self.setup_tab_tamanho()
        
        # Aba: Por Nome
        self.tab_nome = self.tabview.add("Por Nome")
        self.setup_tab_nome()
        
        # Írea de resultados
        self.frame_resultado = ctk.CTkFrame(self.frame)
        self.frame_resultado.pack(pady=10, padx=10, fill="both", expand=True)
        
        self.lbl_resultado = ctk.CTkLabel(
            self.frame_resultado,
            text="Resultados aparecerão aqui",
            font=("Arial", 12)
        )
        self.lbl_resultado.pack(pady=2)
        
        self.texto_resultado = ctk.CTkTextbox(self.frame_resultado, height=150)
        self.texto_resultado.pack(pady=5, padx=5, fill="both", expand=True)
        
        # Barra de progresso
        self.progress = ctk.CTkProgressBar(self.frame, width=400)
        self.progress.pack(pady=5)
        self.progress.set(0)
    
    def setup_tab_tipo(self):
        self.frame_tipo_opcoes = ctk.CTkFrame(self.tab_tipo)
        self.frame_tipo_opcoes.pack(pady=10, padx=10, fill="x")
        
        self.criar_pastas_var = ctk.BooleanVar(value=True)
        self.chk_pastas = ctk.CTkCheckBox(
            self.frame_tipo_opcoes,
            text="Criar subpastas por categoria",
            variable=self.criar_pastas_var
        )
        self.chk_pastas.pack(pady=2)
        
        self.btn_tipo = ctk.CTkButton(
            self.tab_tipo,
            text="ðŸ“ Organizar por Tipo",
            command=self.organizar_tipo,
            width=200,
            height=40,
            fg_color="green"
        )
        self.btn_tipo.pack(pady=10)
    
    def setup_tab_data(self):
        self.frame_data_opcoes = ctk.CTkFrame(self.tab_data)
        self.frame_data_opcoes.pack(pady=10, padx=10, fill="x")
        
        self.lbl_formato = ctk.CTkLabel(self.frame_data_opcoes, text="Formato:")
        self.lbl_formato.pack(side="left", padx=5)
        
        self.formato_var = ctk.StringVar(value="%Y/%m")
        self.formato_combo = ctk.CTkComboBox(
            self.frame_data_opcoes,
            values=["Apenas Ano", "Ano/Mês", "Ano/Mês/Dia"],
            variable=self.formato_var,
            width=150
        )
        self.formato_combo.pack(side="left", padx=5)
        
        self.btn_data = ctk.CTkButton(
            self.tab_data,
            text="ðŸ“… Organizar por Data",
            command=self.organizar_data,
            width=200,
            height=40,
            fg_color="blue"
        )
        self.btn_data.pack(pady=10)
    
    def setup_tab_tamanho(self):
        self.btn_tamanho = ctk.CTkButton(
            self.tab_tamanho,
            text="ðŸ“Š Organizar por Tamanho",
            command=self.organizar_tamanho,
            width=200,
            height=40,
            fg_color="orange"
        )
        self.btn_tamanho.pack(pady=10)
    
    def setup_tab_nome(self):
        self.frame_nome_opcoes = ctk.CTkFrame(self.tab_nome)
        self.frame_nome_opcoes.pack(pady=10, padx=10, fill="x")
        
        self.lbl_padrao = ctk.CTkLabel(self.frame_nome_opcoes, text="Padrão:")
        self.lbl_padrao.pack(side="left", padx=5)
        
        self.padrao_var = ctk.StringVar(value="primeira_letra")
        self.padrao_combo = ctk.CTkComboBox(
            self.frame_nome_opcoes,
            values=["Primeira Letra", "Extensão"],
            variable=self.padrao_var,
            width=150
        )
        self.padrao_combo.pack(side="left", padx=5)
        
        self.btn_nome = ctk.CTkButton(
            self.tab_nome,
            text="ðŸ”¤ Organizar por Nome",
            command=self.organizar_nome,
            width=200,
            height=40,
            fg_color="purple"
        )
        self.btn_nome.pack(pady=10)
    
    def selecionar_pasta(self):
        pasta = filedialog.askdirectory(title="Selecione a pasta para organizar")
        if pasta:
            self.pasta_var.set(pasta)
    
    def organizar_tipo(self):
        self._organizar('tipo')
    
    def organizar_data(self):
        self._organizar('data')
    
    def organizar_tamanho(self):
        self._organizar('tamanho')
    
    def organizar_nome(self):
        self._organizar('nome')
    
    def _organizar(self, metodo):
        pasta = self.pasta_var.get().strip()
        if not pasta:
            self.utils.mostrar_erro("Erro", "Selecione uma pasta primeiro")
            return
        
        def organizar_thread():
            self.btn_tipo.configure(state="disabled")
            self.progress.set(0.3)
            
            mover = self.mover_var.get()
            
            if metodo == 'tipo':
                resultado, msg = self.ferramenta.organizar_por_tipo(
                    pasta,
                    mover=mover,
                    criar_subpastas=self.criar_pastas_var.get()
                )
            elif metodo == 'data':
                formato_map = {
                    "Apenas Ano": '%Y',
                    "Ano/Mês": '%Y/%m',
                    "Ano/Mês/Dia": '%Y/%m/%d'
                }
                resultado, msg = self.ferramenta.organizar_por_data(
                    pasta,
                    formato=formato_map[self.formato_var.get()],
                    mover=mover
                )
            elif metodo == 'tamanho':
                resultado, msg = self.ferramenta.organizar_por_tamanho(
                    pasta,
                    mover=mover
                )
            elif metodo == 'nome':
                padrao_map = {
                    "Primeira Letra": 'primeira_letra',
                    "Extensão": 'extensao'
                }
                resultado, msg = self.ferramenta.organizar_por_nome(
                    pasta,
                    padrao=padrao_map[self.padrao_var.get()],
                    mover=mover
                )
            
            self.progress.set(0.8)
            
            if resultado:
                texto = f"âœ… Organização concluída!\n\n"
                texto += f"Processados: {resultado['processados']}\n"
                texto += f"Movidos: {resultado['movidos']}\n"
                
                if 'por_categoria' in resultado:
                    texto += "\nPor categoria:\n"
                    for cat, qtd in resultado['por_categoria'].items():
                        texto += f"  • {cat}: {qtd}\n"
                
                if 'por_data' in resultado:
                    texto += "\nPor data:\n"
                    for data, qtd in sorted(resultado['por_data'].items()):
                        texto += f"  • {data}: {qtd}\n"
                
                if 'pequenos' in resultado:
                    texto += f"\n  • Pequenos: {resultado['pequenos']}\n"
                    texto += f"  • Médios: {resultado['medios']}\n"
                    texto += f"  • Grandes: {resultado['grandes']}\n"
                
                if resultado['erros'] > 0:
                    texto += f"\nâŒ Erros: {resultado['erros']}"
                
                self.texto_resultado.delete('1.0', 'end')
                self.texto_resultado.insert('1.0', texto)
            else:
                self.utils.mostrar_erro("Erro", msg)
            
            self.progress.set(1)
            self.btn_tipo.configure(state="normal")
        
        threading.Thread(target=organizar_thread).start()

if __name__ == "__main__":
    app = InterfaceOrganizador()
    app.rodar()

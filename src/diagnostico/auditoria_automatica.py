import os
import ast
import json
from pathlib import Path
from typing import List, Dict, Any
from dataclasses import dataclass

@dataclass
class Problema:
    arquivo: str
    tipo: str
    gravidade: str  # 'baixa', 'media', 'alta', 'critica'
    linha: int
    descricao: str

class AuditoriaArca:
    def __init__(self, caminho_raiz: Path):
        self.caminho_raiz = Path(caminho_raiz).resolve()
        self.problemas: List[Problema] = []
        self.arquivos_python: List[str] = []
        self.arquivos_json: List[str] = []
        self.modulos_importados: Dict[str, List[str]] = {}
        self.modulos_existentes: Set[str] = set()

    def _descobrir_arquivos(self):
        """Descobre todos os arquivos Python e JSON na raiz."""
        for root, dirs, files in os.walk(self.caminho_raiz):
            for file in files:
                caminho_rel = os.path.relpath(os.path.join(root, file), self.caminho_raiz)
                if file.endswith('.py'):
                    self.arquivos_python.append(caminho_rel)
                elif file.endswith('.json'):
                    self.arquivos_json.append(caminho_rel)

    def _auditar_imports(self):
        """Audita imports em arquivos Python."""
        for arq_py in self.arquivos_python:
            caminho_completo = self.caminho_raiz / arq_py
            try:
                with open(caminho_completo, 'r', encoding='utf-8-sig') as f:
                    tree = ast.parse(f.read(), filename=str(caminho_completo))
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            if not self._modulo_existe(alias.name):
                                self.problemas.append(Problema(
                                    arquivo=arq_py,
                                    tipo='import_faltando',
                                    gravidade='media',
                                    linha=node.lineno,
                                    descricao=f"Import '{alias.name}' não encontrado."
                                ))
                    elif isinstance(node, ast.ImportFrom):
                        if node.module and not self._modulo_existe(node.module):
                            self.problemas.append(Problema(
                                arquivo=arq_py,
                                tipo='import_faltando',
                                gravidade='media',
                                linha=node.lineno,
                                descricao=f"Import from '{node.module}' não encontrado."
                            ))
            except Exception as e:
                self.problemas.append(Problema(
                    arquivo=arq_py,
                    tipo='erro_parse',
                    gravidade='alta',
                    linha=0,
                    descricao=f"Erro ao parsear arquivo: {e}"
                ))

    def _auditar_lei_zero(self):
        """Audita conformidade com 'Lei Zero' (exemplo: busca por padrões proibidos)."""
        padroes_proibidos = [r'\b(eval|exec)\s*\(', r'\b__import__\s*\(']
        for arq_py in self.arquivos_python:
            caminho_completo = self.caminho_raiz / arq_py
            try:
                with open(caminho_completo, 'r', encoding='utf-8-sig') as f:
                    conteudo = f.read()
                    for i, linha in enumerate(conteudo.splitlines(), 1):
                        for padrao in padroes_proibidos:
                            if re.search(padrao, linha):
                                self.problemas.append(Problema(
                                    arquivo=arq_py,
                                    tipo='lei_zero_violacao',
                                    gravidade='critica',
                                    linha=i,
                                    descricao=f"Padrão proibido encontrado: {padrao}"
                                ))
            except Exception as e:
                self.problemas.append(Problema(
                    arquivo=arq_py,
                    tipo='erro_leitura',
                    gravidade='alta',
                    linha=0,
                    descricao=f"Erro ao ler arquivo: {e}"
                ))

    def _auditar_jsons(self):
        """Audita arquivos JSON por validade."""
        for arq_json in self.arquivos_json:
            caminho_completo = self.caminho_raiz / arq_json
            try:
                with open(caminho_completo, 'r', encoding='utf-8-sig') as f:
                    json.load(f)
            except json.JSONDecodeError as e:
                self.problemas.append(Problema(
                    arquivo=arq_json,
                    tipo='json_invalido',
                    gravidade='alta',
                    linha=0,
                    descricao=f"JSON inválido: {e}"
                ))
            except Exception as e:
                self.problemas.append(Problema(
                    arquivo=arq_json,
                    tipo='erro_json',
                    gravidade='media',
                    linha=0,
                    descricao=f"Erro ao processar JSON: {e}"
                ))

    def _auditar_metodos_nao_implementados(self):
        """Audita métodos que podem estar declarados mas não implementados."""
        for arq_py in self.arquivos_python:
            caminho_completo = self.caminho_raiz / arq_py
            try:
                with open(caminho_completo, 'r', encoding='utf-8-sig') as f:
                    tree = ast.parse(f.read(), filename=str(caminho_completo))
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef) and node.body and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Str):
                        if 'not implemented' in node.body[0].value.s.lower() or 'todo' in node.body[0].value.s.lower():
                            self.problemas.append(Problema(
                                arquivo=arq_py,
                                tipo='metodo_nao_implementado',
                                gravidade='baixa',
                                linha=node.lineno,
                                descricao=f"Método '{node.name}' marcado como não implementado."
                            ))
            except Exception as e:
                pass  # Já tratado em outros métodos

    def _auditar_completude(self):
        """Audita completude geral (exemplo: arquivos sem conteúdo)."""
        for arq_py in self.arquivos_python:
            caminho_completo = self.caminho_raiz / arq_py
            try:
                if os.path.getsize(caminho_completo) < 100:  # Arquivo muito pequeno
                    self.problemas.append(Problema(
                        arquivo=arq_py,
                        tipo='arquivo_incompleto',
                        gravidade='baixa',
                        linha=0,
                        descricao="Arquivo parece incompleto (muito pequeno)."
                    ))
            except Exception:
                pass

    def _modulo_existe(self, nome_modulo: str) -> bool:
        """Verifica se um módulo existe (simplificado)."""
        # Esta é uma verificação básica; pode ser expandida para verificar sys.modules ou pip installs
        partes = nome_modulo.split('.')
        caminho_modulo = self.caminho_raiz
        for parte in partes:
            caminho_modulo = caminho_modulo / parte
            if not (caminho_modulo.with_suffix('.py').exists() or (caminho_modulo / '__init__.py').exists()):
                return False
        return True

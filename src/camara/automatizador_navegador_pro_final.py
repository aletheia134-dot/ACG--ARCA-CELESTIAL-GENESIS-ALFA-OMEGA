# -*- coding: utf-8 -*-
from __future__ import annotations
"""
AutomatizadorNavegadorPro Final (Ncleo da Arca para Interao IA-to-IA Web)

Integra permisses, cache, emergncia, e automao web supervisionada.Foca em navegador para chats IA (ex.: Gemini).
"""

import logging
import time
import threading
import json
import os
import shutil
import tempfile
import uuid
import hashlib
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from collections import defaultdict

logger = logging.getLogger("AutomatizadorNavegadorPro")
logger.addHandler(logging.NullHandler())

def _now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

def _atomic_write_json(path: Path, obj: Any) -> None:
    tmp_fd, tmp_path = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=2, default=str)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, str(path))
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass

TEMPLATES_TERMOS = {
    "LEITURA_DOCS": {
        "tipo_acao": "LER_ARQUIVO",
        "validade_horas": 24,
        "caminho_padrao": "./docs/*"
    },
    "ESCRITA_LOGS": {
        "tipo_acao": "ESCREVER_ARQUIVO",
        "validade_horas": 168,
        "caminho_padrao": "./logs/*"
    },
    "ACESSO_INTERNET_TEMPORARIO": {
        "tipo_acao": "ACESSAR_INTERNET",
        "validade_horas": 1,
        "justificativa_padrao": "solicitação de acesso temporrio para pesquisa."
    }
}

@dataclass
class TermoAcesso:
    id_termo: str
    solicitante: str
    tipo_acao: str
    caminho_alvo: Optional[str] = None
    timestamp_solicitacao: float = field(default_factory=time.time)
    timestamp_concessao: Optional[float] = None
    timestamp_revogacao: Optional[float] = None
    status: str = "PENDENTE"
    justificativa: str = ""
    validade_horas: Optional[float] = None

    def esta_valido(self) -> bool:
        if self.status != "CONCEDIDO":
            return False
        if self.validade_horas:
            inicio = self.timestamp_concessao or self.timestamp_solicitacao
            if time.time() - inicio > (self.validade_horas * 3600):
                self.status = "EXPIRADO"
                return False
        return True

@dataclass
class ElementoInfo:
    tipo: str
    texto: Optional[str] = None
    seletor: Optional[str] = None
    xpath: Optional[str] = None
    coordenadas: Optional[Tuple[int, int]] = None
    atributos: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

class AutomatizadorNavegadorPro:
    def __init__(self, config_instance, controlador_gui_ref=None):
        self.config = config_instance
        self.controlador_gui = controlador_gui_ref
        self.logger = logging.getLogger(self.__class__.__name__)
        self._lock = threading.RLock()

        self.configuracoes = self._carregar_configuracoes()
        self._termos_concedidos: Dict[str, TermoAcesso] = {}
        self._historico_termos: List[TermoAcesso] = []
        self._cache_permissoes: Dict[Tuple[str, str, Optional[str]], Tuple[float, bool]] = {}
        self._lock_acesso = threading.RLock()
        self._tempo_exp_permissoes = float(self.configuracoes.get('tempo_expiracao_cache_permissoes', 300.0))
        self._modo_emergencia = False
        self._hash_senha_mestre = str(self.configuracoes.get('hash_senha_mestre_emergencia', ''))
        self._habilitar_modo_emergencia = bool(self.configuracoes.get('habilitar_modo_emergencia', False))

        self.rate_limit_acessos: Dict[str, list] = defaultdict(list)
        self.max_acessos_por_hora = 20
        self.cache_respostas: Dict[str, str] = {}

        Path(self.configuracoes['caminho_historico_termos']).parent.mkdir(parents=True, exist_ok=True)
        self._carregar_historico_termos()

        logger.info("AutomatizadorNavegadorPro inicializado (enduricido).")

    def _carregar_configuracoes(self) -> Dict[str, Any]:
        cfg = {}
        try:
            cfg['timeout_padrao'] = float(self.config.get('NAVEGADOR', 'TIMEOUT_PADRAO_SECS', fallback=30.0))
            cfg['timeout_elemento'] = float(self.config.get('NAVEGADOR', 'TIMEOUT_ELEMENTO_SECS', fallback=10.0))
            cfg['headless'] = bool(self.config.get('NAVEGADOR', 'HEADLESS', fallback=False))
            cfg['navegador_preferido'] = str(self.config.get('NAVEGADOR', 'NAVEGADOR_PREFERIDO', fallback='chrome')).lower()
            cfg['user_agent'] = str(self.config.get('NAVEGADOR', 'USER_AGENT', fallback=''))
            cfg['proxy'] = self.config.get('NAVEGADOR', 'PROXY', fallback=None)
            cfg['tentar_playwright_primeiro'] = bool(self.config.get('NAVEGADOR', 'TENTAR_PLAYWRIGHT_PRIMEIRO', fallback=True))
            cfg['habilitar_gui_fallback'] = bool(self.config.get('NAVEGADOR', 'HABILITAR_GUI_FALLBACK', fallback=True))
            cfg['salvar_screenshots_erro'] = bool(self.config.get('NAVEGADOR', 'SALVAR_SCREENSHOTS_ERRO', fallback=True))
            cfg['caminho_screenshots'] = Path(self.config.get('NAVEGADOR', 'CAMINHO_SCREENSHOTS_PATH', fallback='./screenshots'))

            dirs_raw = str(self.config.get('MANIPULADOR_ARQUIVOS', 'DIRETORIOS_PERMITIDOS_CSV', fallback='./data')).split(',')
            cfg['diretorios_permitidos'] = [Path(d.strip()).resolve() for d in dirs_raw if d.strip()]
            exts_raw = str(self.config.get('MANIPULADOR_ARQUIVOS', 'EXTENSOES_PERMITIDAS_CSV', fallback='.txt,.md,.pdf,.docx,.csv')).split(',')
            cfg['extensoes_permitidas'] = {e.strip().lower() for e in exts_raw if e.strip()}
            cfg['max_tamanho_arquivo_bytes'] = int(self.config.get('MANIPULADOR_ARQUIVOS', 'MAX_TAMANHO_ARQUIVO_MB', fallback=50)) * 1024 * 1024
            cfg['caminho_historico_termos'] = Path(self.config.get('MANIPULADOR_ARQUIVOS', 'CAMINHO_HISTORICO_TERMOS', fallback='data/historico_termos_acesso.json'))

            cfg['habilitar_controle_internet'] = bool(self.config.get('ACESSO_INTERNET', 'HABILITAR_CONTROLE', fallback=True))
            cfg['acesso_internet_concedido_inicialmente'] = bool(self.config.get('ACESSO_INTERNET', 'ACESSO_CONCEDIDO_INICIALMENTE', fallback=False))
            cfg['caminho_termos_internet'] = Path(self.config.get('ACESSO_INTERNET', 'TERMOS_CAMINHO', fallback='data/termos_acesso_internet.txt'))
            cfg['caminho_estado_acesso_internet'] = Path(self.config.get('ACESSO_INTERNET', 'CAMINHO_ESTADO_ARQUIVO', fallback='data/acesso_internet_estado.json'))
            cfg['timeout_solicitacao_internet'] = float(self.config.get('ACESSO_INTERNET', 'TIMEOUT_SOLICITACAO_SECS', fallback=30.0))

            cfg['tempo_expiracao_cache_permissoes'] = float(self.config.get('CACHE_PERMISSOES', 'TEMPO_EXPIRACAO_SECS', fallback=300.0))

            cfg['habilitar_modo_emergencia'] = bool(self.config.get('MODO_EMERGENCIA', 'HABILITAR', fallback=False))
            cfg['hash_senha_mestre_emergencia'] = str(self.config.get('MODO_EMERGENCIA', 'HASH_SENHA_MESTRE', fallback=''))

            try:
                cfg['caminho_screenshots'].mkdir(parents=True, exist_ok=True)
            except Exception:
                logger.debug("Falha ao criar pasta de screenshots (ignorado).")
            try:
                cfg['caminho_historico_termos'] = Path(cfg['caminho_historico_termos'])
            except Exception:
                cfg['caminho_historico_termos'] = Path("data/historico_termos_acesso.json")
            return cfg
        except Exception:
            logger.exception("Falha ao carregar configurações; usando defaults.")
            return {
                'timeout_padrao': 30.0,
                'timeout_elemento': 10.0,
                'headless': True,
                'navegador_preferido': 'chrome',
                'user_agent': '',
                'proxy': None,
                'tentar_playwright_primeiro': True,
                'habilitar_gui_fallback': True,
                'salvar_screenshots_erro': True,
                'caminho_screenshots': Path('./screenshots'),
                'diretorios_permitidos': [Path('./data').resolve()],
                'extensoes_permitidas': {'.txt', '.md', '.pdf', '.docx', '.csv'},
                'max_tamanho_arquivo_bytes': 50 * 1024 * 1024,
                'caminho_historico_termos': Path('data/historico_termos_acesso.json'),
                'habilitar_controle_internet': True,
                'caminho_termos_internet': Path('data/termos_acesso_internet.txt'),
                'caminho_estado_acesso_internet': Path('data/acesso_internet_estado.json'),
                'timeout_solicitacao_internet': 30.0,
                'tempo_expiracao_cache_permissoes': 300.0,
                'habilitar_modo_emergencia': False,
                'hash_senha_mestre_emergencia': ''
            }

    def _carregar_historico_termos(self) -> None:
        caminho = Path(self.configuracoes['caminho_historico_termos'])
        if not caminho.exists():
            self._historico_termos = []
            logger.info("Arquivo de histórico de termos no encontrado; iniciando vazio.")
            return
        try:
            with open(caminho, 'r', encoding='utf-8') as f:
                raw = json.load(f)
            if isinstance(raw, list):
                self._historico_termos = []
                for item in raw:
                    try:
                        termo = TermoAcesso(**item)
                        self._historico_termos.append(termo)
                        if termo.status == "CONCEDIDO" and termo.esta_valido():
                            self._termos_concedidos[termo.id_termo] = termo
                    except Exception:
                        logger.debug("Registro de termo invlido no histórico (ignorado).")
                logger.info("histórico de termos carregado (%d entradas).", len(self._historico_termos))
            else:
                raise ValueError("Formato invlido do arquivo de histórico (esperado lista).")
        except Exception as e:
            logger.exception("Falha ao carregar histórico de termos: %s.Movendo para quarantine e iniciando arquivo vazio.", e)
            try:
                ts = datetime.utcnow().strftime("%Y%m%d%H%M%S")
                quarantine = caminho.with_suffix(f".corrupt_{ts}")
                shutil.move(str(caminho), str(quarantine))
                logger.warning("Arquivo de histórico corrompido movido para: %s", quarantine)
            except Exception:
                logger.debug("Falha ao mover arquivo corrompido para quarantine.")
            self._historico_termos = []
            self._termos_concedidos = {}

    def _salvar_historico_termos(self) -> None:
        caminho = Path(self.configuracoes['caminho_historico_termos'])
        try:
            dados = [asdict(t) for t in self._historico_termos]
            if len(dados) > 100:
                import gzip
                with gzip.open(caminho.with_suffix('.json.gz'), 'wt', encoding='utf-8') as f:
                    json.dump(dados, f, indent=2, ensure_ascii=False, default=str)
            else:
                _atomic_write_json(caminho, dados)
            logger.debug("histórico de termos salvo com sucesso: %s", caminho)
        except Exception:
            logger.exception("Erro ao salvar histórico de termos (ignorado).")

    def solicitar_termo_acesso(self, solicitante: str, tipo_acao: str, caminho_alvo: Optional[str] = None, justificativa: str = "", validade_horas: Optional[float] = None, template_id: Optional[str] = None) -> Tuple[bool, str]:
        if template_id and template_id in TEMPLATES_TERMOS:
            tpl = TEMPLATES_TERMOS[template_id]
            tipo_acao = tpl['tipo_acao']
            validade_horas = validade_horas or tpl.get('validade_horas')
            if caminho_alvo is None:
                caminho_alvo = tpl.get('caminho_padrao')

        chave_cache = (solicitante, tipo_acao, caminho_alvo)
        with self._lock_acesso:
            cached = self._cache_permissoes.get(chave_cache)
            if cached and time.time() < cached[0]:
                self.logger.debug("Permisso retornada do cache para %s: %s", chave_cache, cached[1])
                return cached[1], "Retornado do cache."

        with self._lock_acesso:
            for termo in self._termos_concedidos.values():
                if termo.solicitante == solicitante and termo.tipo_acao == tipo_acao and (caminho_alvo is None or termo.caminho_alvo == caminho_alvo):
                    if termo.esta_valido():
                        self._cache_permissoes[chave_cache] = (time.time() + self._tempo_exp_permissoes, True)
                        return True, f"Termo j concedido (ID: {termo.id_termo})"
                    else:
                        termo.status = "EXPIRADO"

        id_solicitacao = str(uuid.uuid4())
        novo = TermoAcesso(
            id_termo=id_solicitacao,
            solicitante=solicitante,
            tipo_acao=tipo_acao,
            caminho_alvo=caminho_alvo,
            justificativa=justificativa,
            validade_horas=validade_horas
        )
        with self._lock_acesso:
            self._historico_termos.append(novo)
            self._salvar_historico_termos()
            self._cache_permissoes[chave_cache] = (time.time() + self._tempo_exp_permissoes, False)
        self.logger.info("solicitação de termo criada: %s (pendente)", id_solicitacao)
        return False, f"solicitação registrada (ID: {id_solicitacao}). Aguardando aprovao."

    def aprovar_solicitacao_termo(self, id_solicitacao: str, autorizador: str = "Pai-Criador") -> bool:
        with self._lock_acesso:
            alvo = next((t for t in self._historico_termos if t.id_termo == id_solicitacao and t.status == "PENDENTE"), None)
            if not alvo:
                self.logger.warning("solicitação no encontrada ou j processada: %s", id_solicitacao)
                return False
            alvo.status = "CONCEDIDO"
            alvo.timestamp_concessao = time.time()
            alvo.justificativa = (alvo.justificativa or "") + f" [Aprovado por {autorizador} em {_now_iso()}]"
            self._termos_concedidos[alvo.id_termo] = alvo
            chave = (alvo.solicitante, alvo.tipo_acao, alvo.caminho_alvo)
            self._cache_permissoes[chave] = (time.time() + self._tempo_exp_permissoes, True)
            self._salvar_historico_termos()
            logger.info("Termo aprovado: %s", id_solicitacao)
            self._notificar_ui({"tipo": "TERMO_APROVADO", "id": id_solicitacao})
            return True

    def rejeitar_solicitacao_termo(self, id_solicitacao: str, autorizador: str = "Pai-Criador", motivo: str = "No especificado.") -> bool:
        with self._lock_acesso:
            alvo = next((t for t in self._historico_termos if t.id_termo == id_solicitacao and t.status == "PENDENTE"), None)
            if not alvo:
                self.logger.warning("solicitação no encontrada ou j processada: %s", id_solicitacao)
                return False
            alvo.status = "NEGADO"
            alvo.timestamp_revogacao = time.time()
            alvo.justificativa = (alvo.justificativa or "") + f" [Rejeitado por {autorizador} em {_now_iso()} - Motivo: {motivo}]"
            self._salvar_historico_termos()
            logger.info("Termo rejeitado: %s", id_solicitacao)
            self._notificar_ui({"tipo": "TERMO_RECUSADO", "id": id_solicitacao, "motivo": motivo})
            return True

    def _is_path_allowed(self, caminho: Path) -> bool:
        try:
            caminho_res = caminho.resolve()
        except Exception:
            return False
        for base in self.configuracoes['diretorios_permitidos']:
            try:
                if hasattr(caminho_res, "is_relative_to"):
                    if caminho_res.is_relative_to(base):
                        return True
                else:
                    try:
                        caminho_res.relative_to(base)
                        return True
                    except Exception:
                        pass
            except Exception:
                continue
        return False

    def _verificar_permissoes_arquivo(self, caminho: Path, operação: str) -> Tuple[bool, str]:
        try:
            caminho_absoluto = caminho.resolve()
        except Exception:
            return False, "Caminho invlido ou inacessvel."

        if not self._is_path_allowed(caminho_absoluto):
            return False, f"Caminho '{caminho_absoluto}' no permitido."

        if operação in ('ler', 'escrever'):
            ext = caminho.suffix.lower()
            if ext not in self.configuracoes['extensoes_permitidas']:
                return False, f"Extenso {ext} no permitida."

        if operação == 'ler' and caminho_absoluto.exists():
            try:
                tamanho = caminho_absoluto.stat().st_size
                if tamanho > self.configuracoes['max_tamanho_arquivo_bytes']:
                    return False, f"Tamanho do arquivo excede limite ({self.configuracoes['max_tamanho_arquivo_bytes']} bytes)."
            except Exception:
                return False, "Falha ao verificar tamanho do arquivo."

        proibidos = ['.env', 'passwd', 'shadow', 'windows/system32', '/etc/shadow', '/etc/passwd']
        low = str(caminho_absoluto).lower()
        if any(p in low for p in proibidos):
            return False, "Acesso a caminho crítico proibido."

        return True, "OK"

    def _verificar_permissoes_e_termo(self, solicitante: str, tipo_acao: str, caminho_alvo: Optional[str] = None) -> bool:
        if tipo_acao in ("LER_ARQUIVO", "ESCREVER_ARQUIVO", "LER_EMAIL") and caminho_alvo:
            caminho = Path(caminho_alvo)
            ok, motivo = self._verificar_permissoes_arquivo(caminho, 'ler' if tipo_acao.startswith('LER') else 'escrever')
            if not ok:
                self.logger.error("Permisso arquivo negada: %s", motivo)
                return False

        chave = (solicitante, tipo_acao, caminho_alvo)
        with self._lock_acesso:
            cached = self._cache_permissoes.get(chave)
            if cached and time.time() < cached[0]:
                return cached[1]

        sucesso = False
        with self._lock_acesso:
            for termo in self._termos_concedidos.values():
                if termo.solicitante == solicitante and termo.tipo_acao == tipo_acao and (caminho_alvo is None or termo.caminho_alvo == caminho_alvo) and termo.esta_valido():
                    sucesso = True
                    break
            self._cache_permissoes[chave] = (time.time() + self._tempo_exp_permissoes, sucesso)
        if sucesso:
            logger.debug("Termo vlido encontrado para %s", chave)
        else:
            logger.warning("Termo ausente/invlido para %s", chave)
        return sucesso

    def modo_emergencia(self, senha_mestre: str) -> bool:
        if not self._habilitar_modo_emergencia:
            logger.warning("Modo emergncia desabilitado nas configs.")
            return False
        try:
            senha_hash = hashlib.sha256(senha_mestre.encode()).hexdigest()
            if senha_hash == self._hash_senha_mestre:
                with self._lock_acesso:
                    self._modo_emergencia = True
                    self._cache_permissoes.clear()
                logger.critical("MODO EMERGNCIA ATIVADO.")
                return True
        except Exception:
            logger.exception("Erro verificando senha mestre para modo emergencia.")
        logger.error("Senha mestre incorreta.")
        return False

    def _verificar_modo_emergencia(self) -> bool:
        return bool(self._modo_emergencia)

    def executar_acao_via_voz(self, comando: str, solicitante: str) -> str:
        now = time.time()
        acessos_hora = [t for t in self.rate_limit_acessos[solicitante] if now - t < 3600]
        if len(acessos_hora) >= self.max_acessos_por_hora:
            return "Limite de acessos por hora excedido."
        self.rate_limit_acessos[solicitante] = acessos_hora + [now]
        
        comando_lower = comando.lower()
        if "conversa ia com" in comando_lower:
            parts = comando.split("no")
            ai_arca = parts[0].split("com")[-1].strip().upper()
            subparts = parts[1].split("sobre")
            plataforma = "gemini" if "gemini" in subparts[0] else "grok"
            url_chat = f"https://{plataforma}.google.com" if plataforma == "gemini" else f"https://{plataforma}.x.ai"
            topico = subparts[1].strip() if len(subparts) > 1 else "IA geral"
            
            if self.iniciar_conversa_ia_to_ia_web(ai_arca, plataforma, url_chat, topico):
                return f"Conversa IA-to-IA iniciada com {ai_arca} em {plataforma}."
            return "Falha ao iniciar conversa."
        
        return "Comando no reconhecido."

    def iniciar_conversa_ia_to_ia_web(self, ai_arca: str, plataforma: str, url_chat: str, topico: str) -> bool:
        if not getattr(self, "chat_supervisionado_ativo", False):
            return False
        
        now = time.time()
        msgs_hora = [t for t in self.rate_limit_acessos.get(ai_arca, []) if now - t < 3600]
        if len(msgs_hora) >= self.max_msgs_por_hora:
            return False
        self.rate_limit_acessos[ai_arca] = msgs_hora + [now]
        
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=False)
                page = browser.new_page()
                page.goto(url_chat)
                time.sleep(10)
                
                for _ in range(5):
                    prompt_arca = f"Como {ai_arca}, responda sobre {topico}."
                    page.fill("textarea", prompt_arca)
                    page.press("textarea", "Enter")
                    time.sleep(5)
                    resposta_externa = page.text_content(".response")
                    if resposta_externa:
                        logger.info("Resposta externa: %s", resposta_externa[:200])
                browser.close()
            return True
        except Exception:
            return False

    def _notificar_ui(self, payload: dict):
        if self.controlador_gui:
            try:
                self.controlador_gui.put_ui_message(payload)
            except Exception:
                logger.debug("UI indisponível para notificao.")
        else:
            logger.debug("Controlador GUI no definido; notificao ignorada.")

    def shutdown(self):
        logger.info("Shutdown do AutomatizadorNavegadorPro iniciado.")
        try:
            if hasattr(self, '_selenium_driver') and self._selenium_driver:
                self._selenium_driver.quit()
        except Exception:
            logger.debug("Erro ao fechar drivers (ignorado).")
        logger.info("Shutdown completo.")

# Adicionado: Classe AutomatizadorNavegadorMultiAI (alias para resolver import)
AutomatizadorNavegadorMultiAI = AutomatizadorNavegadorPro

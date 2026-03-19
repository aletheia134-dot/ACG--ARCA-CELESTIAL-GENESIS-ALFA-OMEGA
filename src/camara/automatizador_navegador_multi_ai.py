import logging
import threading
import time
import uuid
from typing import Dict, Any, Optional, List
from pathlib import Path

logger = logging.getLogger(__name__)

class SolicitacaoTermo:
    def __init__(self, acao: str, descricao: str, autor: str, nivel_acesso: str, kwargs: Dict[str, Any]):
        self.id = str(uuid.uuid4())
        self.acao = acao
        self.descricao = descricao
        self.autor = autor
        self.nivel_acesso = nivel_acesso
        self.kwargs = kwargs
        self.aprovada = None  # None: pendente, True: aprovada, False: rejeitada
        self.timestamp = time.time()

class AutomatizadorNavegadorMultiAI:
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.solicitacoes_pendentes: Dict[str, SolicitacaoTermo] = {}
        self.modo_emergencia_ativo = False
        self.senha_mestre = "senha_mestre_padrao"  # Mudar para algo seguro
        self.lock = threading.Lock()
        logger.info("AutomatizadorNavegadorMultiAI inicializado")

    def solicitar_missao(self, acao: str, descricao: str, autor: str, nivel_acesso: str, **kwargs) -> Dict[str, Any]:
        """
        Solicita uma misso para automao de navegador.
        """
        solicitacao = SolicitacaoTermo(acao, descricao, autor, nivel_acesso, kwargs)
        with self.lock:
            self.solicitacoes_pendentes[solicitacao.id] = solicitacao
        logger.info(f"Misso solicitada: {acao} por {autor} (ID: {solicitacao.id})")
        return {"status": "solicitado", "id": solicitacao.id, "mensagem": "Aguardando aprovao."}

    def aprovar_solicitacao_termo(self, id_solicitacao: str) -> bool:
        """
        Aprova uma solicitação pendente.
        """
        with self.lock:
            if id_solicitacao in self.solicitacoes_pendentes:
                solicitacao = self.solicitacoes_pendentes[id_solicitacao]
                if solicitacao.aprovada is None:
                    solicitacao.aprovada = True
                    logger.info(f"solicitação aprovada: {id_solicitacao}")
                    self._executar_missao_aprovada(solicitacao)
                    return True
        logger.warning(f"solicitação no encontrada ou j processada: {id_solicitacao}")
        return False

    def rejeitar_solicitacao_termo(self, id_solicitacao: str) -> bool:
        """
        Rejeita uma solicitação pendente.
        """
        with self.lock:
            if id_solicitacao in self.solicitacoes_pendentes:
                solicitacao = self.solicitacoes_pendentes[id_solicitacao]
                if solicitacao.aprovada is None:
                    solicitacao.aprovada = False
                    logger.info(f"solicitação rejeitada: {id_solicitacao}")
                    return True
        logger.warning(f"solicitação no encontrada ou j processada: {id_solicitacao}")
        return False

    def _executar_missao_aprovada(self, solicitacao: SolicitacaoTermo):
        """Executa a missão aprovada via Playwright ou servidor web (porta 5003)."""
        logger.info(f"Executando missão: {solicitacao.acao} - {solicitacao.descricao}")
        threading.Thread(
            target=self._executar_real,
            args=(solicitacao,),
            daemon=True
        ).start()

    def _executar_real(self, solicitacao: SolicitacaoTermo):
        """Executa missão real: tenta Playwright, fallback para servidor_web (5003)."""
        import json as _json

        acao = solicitacao.acao
        descricao = solicitacao.descricao

        # Tentativa 1: usar servidor_web na porta 5003
        try:
            import requests as _req
            payload = {
                "acao": acao,
                "descricao": descricao,
                "autor": solicitacao.autor,
                "id": solicitacao.id,
            }
            resp = _req.post(
                "http://localhost:5003/executar_missao",
                json=payload,
                timeout=30
            )
            if resp.status_code == 200:
                logger.info(
                    "Missão %s executada via servidor_web: %s",
                    solicitacao.id, resp.json()
                )
                return
            logger.warning(
                "servidor_web retornou HTTP %d para missão %s",
                resp.status_code, solicitacao.id
            )
        except _req.exceptions.ConnectionError:
            logger.warning("Servidor web (5003) indisponível, tentando Playwright direto...")
        except Exception as e:
            logger.warning("Erro ao chamar servidor_web: %s", e)

        # Tentativa 2: Playwright direto
        if acao == "LER_ARQUIVO":
            logger.info("LER_ARQUIVO: operação local — não requer navegador.")
            return

        if acao == "CONVERSA_IA":
            try:
                from playwright.sync_api import sync_playwright
                with sync_playwright() as pw:
                    browser = pw.chromium.launch(headless=False)
                    page = browser.new_page()
                    # Extrair URL da descrição se disponível
                    url = "https://chat.openai.com"
                    for parte in descricao.split():
                        if parte.startswith("http"):
                            url = parte
                            break
                    page.goto(url, timeout=30000)
                    logger.info(
                        "Missão %s: navegador aberto em %s",
                        solicitacao.id, url
                    )
                    page.wait_for_timeout(5000)
                    browser.close()
                return
            except ImportError:
                logger.error(
                    "playwright não instalado. "
                    "Instale com: venvs\\web\\Scripts\\pip install playwright && playwright install"
                )
            except Exception as e:
                logger.error("Erro ao executar missão via Playwright: %s", e)

        logger.warning(
            "Missão %s (%s) não pôde ser executada: servidor_web offline e Playwright indisponível.",
            solicitacao.id, acao
        )

    def executar_acao_via_voz(self, comando: str, autor: str) -> Dict[str, Any]:
        """
        Executa ação baseada em comando de voz.
        """
        logger.info(f"Executando comando de voz: '{comando}' por {autor}")
        # Exemplo simples: Parse do comando
        if "conversa" in comando.lower() and "gemini" in comando.lower():
            return self.iniciar_conversa_ia_to_ia_web("WELLINGTON", "gemini", "https://gemini.google.com", "IA geral")
        else:
            return {"status": "executado", "mensagem": f"Comando '{comando}' processado."}

    def iniciar_conversa_ia_to_ia_web(self, ai_arca: str, plataforma: str, url_chat: str, topico: str) -> bool:
        """
        Inicia conversa entre IA da Arca e plataforma externa via Playwright ou servidor_web.
        """
        logger.info(f"Iniciando conversa: {ai_arca} com {plataforma} em {url_chat} sobre '{topico}'")

        # Tentativa 1: delegar ao servidor_web (5003)
        try:
            import requests as _req
            resp = _req.post(
                "http://localhost:5003/navegador",
                json={"url": url_chat, "ação": "abrir", "topico": topico, "ai": ai_arca},
                timeout=15
            )
            if resp.status_code == 200:
                logger.info("[OK] Conversa iniciada via servidor_web: %s", resp.json())
                return True
            logger.warning("servidor_web retornou HTTP %d", resp.status_code)
        except _req.exceptions.ConnectionError:
            logger.warning("Servidor web (5003) offline, tentando Playwright direto...")
        except Exception as e:
            logger.warning("Erro ao chamar servidor_web: %s", e)

        # Tentativa 2: Playwright direto
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as pw:
                browser = pw.chromium.launch(headless=False)
                page = browser.new_page()
                page.goto(url_chat, timeout=30000)
                logger.info("[OK] Navegador aberto em %s para conversa %s↔%s", url_chat, ai_arca, plataforma)
                page.wait_for_timeout(3000)
                browser.close()
            return True
        except ImportError:
            logger.error(
                "playwright não instalado. "
                "Execute: venvs\\web\\Scripts\\pip install playwright && playwright install chromium"
            )
            return False
        except Exception as e:
            logger.error("Erro ao abrir navegador via Playwright: %s", e)
            return False

    def modo_emergencia(self, senha: str) -> bool:
        """
        Ativa modo emergncia com senha mestre.
        """
        if senha == self.senha_mestre:
            self.modo_emergencia_ativo = True
            logger.warning("MODO EMERGNCIA ATIVADO!")
            # Aqui pode implementar ações de emergncia, como fechar navegadores, limpar cache, etc.
            return True
        else:
            logger.error("Senha mestre incorreta para modo emergncia.")
            return False

    def listar_solicitacoes_pendentes(self) -> List[Dict[str, Any]]:
        """
        Lista solicitações pendentes.
        """
        with self.lock:
            return [{"id": s.id, "acao": s.acao, "autor": s.autor, "timestamp": s.timestamp} for s in self.solicitacoes_pendentes.values() if s.aprovada is None]

# Instncia global
automatizador_navegador_multi_ai = AutomatizadorNavegadorMultiAI()

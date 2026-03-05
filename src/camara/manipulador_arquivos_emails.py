import imaplib
import email
from email.header import decode_header
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

class ManipuladorArquivosEmails:
    def __init__(self, servidor_imap: str = "imap.gmail.com", porta: int = 993, usuario: str = None, senha: str = None):
        self.servidor_imap = servidor_imap
        self.porta = porta
        self.usuario = usuario
        self.senha = senha
        self.mail = None

        if not self.usuario or not self.senha:
            logger.warning("Credenciais de email não fornecidas. Configure no config.")

    def conectar(self) -> bool:
        try:
            self.mail = imaplib.IMAP4_SSL(self.servidor_imap, self.porta)
            self.mail.login(self.usuario, self.senha)
            logger.info("âœ… Conectado ao servidor IMAP")
            return True
        except Exception as e:
            logger.exception(f"Erro ao conectar IMAP: {e}")
            return False

    def desconectar(self):
        if self.mail:
            self.mail.logout()
            self.mail = None
            logger.info("âœ… Desconectado do IMAP")

    def ler_emails(self, caixa: str = "INBOX", limite: int = 10) -> List[Dict[str, str]]:
        if not self.mail:
            if not self.conectar():
                return []

        try:
            self.mail.select(caixa)
            status, mensagens = self.mail.search(None, "ALL")
            if status != "OK":
                return []

            ids_emails = mensagens[0].split()[-limite:]
            emails_lidos = []

            for email_id in ids_emails:
                status, dados = self.mail.fetch(email_id, "(RFC822)")
                if status != "OK":
                    continue

                msg = email.message_from_bytes(dados[0][1])
                assunto = self._decodificar_header(msg["Subject"])
                de = self._decodificar_header(msg["From"])
                data = msg["Date"]
                corpo = self._extrair_corpo(msg)

                emails_lidos.append({
                    "id": email_id.decode(),
                    "assunto": assunto,
                    "de": de,
                    "data": data,
                    "corpo": corpo[:500] + "..." if len(corpo) > 500 else corpo
                })

            return emails_lidos
        except Exception as e:
            logger.exception(f"Erro ao ler emails: {e}")
            return []

    def _decodificar_header(self, header: str) -> str:
        decoded, encoding = decode_header(header)[0]
        if isinstance(decoded, bytes):
            return decoded.decode(encoding or 'utf-8')
        return decoded

    def _extrair_corpo(self, msg) -> str:
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    return part.get_payload(decode=True).decode('utf-8', errors='ignore')
        else:
            return msg.get_payload(decode=True).decode('utf-8', errors='ignore')
        return ""

    def obter_status_caixa(self, caixa: str = "INBOX") -> Dict[str, int]:
        if not self.mail:
            return {}

        try:
            status, resposta = self.mail.status(caixa, "(MESSAGES RECENT)")
            return {"total_emails": int(resposta[0].split()[2]), "recentes": int(resposta[0].split()[4])}
        except Exception as e:
            logger.exception(f"Erro ao obter status da caixa: {e}")
            return {}

# Adicionado: Classe TermoAcesso (stub para resolver import)
class TermoAcesso:
    def __init__(self, config=None):
        self.config = config
        # Implementar lógica básica se necessário (ex.: termos de acesso a arquivos/emails)

# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import logging
import uuid
import os
import hmac
import base64
import hashlib
import time
import tempfile  # Adicionado: estava faltando
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple, Type, TypeVar
from enum import Enum
import threading
from dataclasses import dataclass, field

try:
    import PyPDF2
except:
    logging.getLogger(__name__).warning("[AVISO] PyPDF2 no disponível")
    PyPDF2 = None
    logging.getLogger(__name__).warning("PyPDF2 no instalado; suporte a PDF limitado.")

logger = logging.getLogger("CamaraLegislativa")
logger.addHandler(logging.NullHandler())

TEnum = TypeVar("TEnum", bound=Enum)

# Adicionado: Enums necessários para Lei
class TipoLei(Enum):
    OPERACIONAL = "operacional"
    # Adicione outros tipos se necessário

class StatusLei(Enum):
    ATIVA = "ativa"
    REVOGADA = "revogada"
    AGUARDANDO_CRIADOR = "aguardando_criador"
    EM_DELIBERACAO = "em_deliberacao"
    # Adicione outros status se necessário

def parse_enum(enum_cls: Type[TEnum], value: Any, default: TEnum) -> TEnum:
    if value is None:
        return default
    if isinstance(value, enum_cls):
        return value
    v = str(value).strip()
    if not v:
        return default
    for member in enum_cls:
        if member.value.lower() == v.lower():
            return member
    try:
        return enum_cls[v.upper()]
    except Exception:
        return default

def _safe_datetime_from_iso(s: Optional[str]) -> datetime:
    if not s:
        return datetime.now()
    try:
        return datetime.fromisoformat(s)
    except Exception:
        try:
            return datetime.fromisoformat(s.replace("Z", "+00:00"))
        except Exception:
            return datetime.now()

def _atomic_write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp_", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=2, default=str)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, str(path))
    except Exception:
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except Exception:
            pass
        raise

def _safe_load_json(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        logger.exception("Falha ao ler JSON %s", path)
        return None

def _now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"

@dataclass
class Lei:
    id: str
    titulo: str
    tipo: TipoLei
    categoria: str
    numero_protocolo: str
    principio: str
    instrucao_base: str
    detalhes: Dict[str, Any]
    referencia_biblica: str
    autor_criador: str
    data_criacao: datetime
    status: StatusLei
    versao: int = 1
    leis_relacionadas: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "titulo": self.titulo,
            "tipo": self.tipo.value,
            "categoria": self.categoria,
            "numero_protocolo": self.numero_protocolo,
            "principio": self.principio,
            "instrucao_base": self.instrucao_base,
            "detalhes": self.detalhes,
            "referencia_biblica": self.referencia_biblica,
            "autor_criador": self.autor_criador,
            "data_criacao": self.data_criacao.isoformat(),
            "status": self.status.value,
            "versao": self.versao,
            "leis_relacionadas": self.leis_relacionadas,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Lei":
        tipo_default = TipoLei.OPERACIONAL
        status_default = StatusLei.ATIVA
        data_criacao_raw = data.get("data_criacao")
        try:
            if isinstance(data_criacao_raw, str):
                data_criacao = datetime.fromisoformat(data_criacao_raw)
            else:
                data_criacao = datetime.now()
        except Exception:
            data_criacao = datetime.now()

        return cls(
            id=str(data.get("id", str(uuid.uuid4()))),
            titulo=str(data.get("titulo", "")),
            tipo=parse_enum(TipoLei, data.get("tipo"), tipo_default),
            categoria=str(data.get("categoria", "")),
            numero_protocolo=str(data.get("numero_protocolo", "")),
            principio=str(data.get("principio", "")),
            instrucao_base=str(data.get("instrucao_base", "")),
            detalhes=data.get("detalhes", {}),
            referencia_biblica=str(data.get("referencia_biblica", "")),
            autor_criador=str(data.get("autor_criador", "")),
            data_criacao=data_criacao,
            status=parse_enum(StatusLei, data.get("status"), status_default),
            versao=int(data.get("versao", 1)),
            leis_relacionadas=[str(l) for l in data.get("leis_relacionadas", [])] if data.get("leis_relacionadas") else [],
        )

@dataclass
class PropostaLei:
    id: str
    titulo_proposto: str
    justificativa: str
    necessidade: str
    fundamento_biblico: str
    detalhes_propostos: Dict[str, Any]
    autor_proponente: str
    data_proposta: datetime
    status: str
    votos_favor: int = 0
    votos_contra: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "titulo_proposto": self.titulo_proposto,
            "justificativa": self.justificativa,
            "necessidade": self.necessidade,
            "fundamento_biblico": self.fundamento_biblico,
            "detalhes_propostos": self.detalhes_propostos,
            "autor_proponente": self.autor_proponente,
            "data_proposta": self.data_proposta.isoformat(),
            "status": self.status,
            "votos_favor": self.votos_favor,
            "votos_contra": self.votos_contra,
        }

class AuthManager:
    def __init__(self, users_file: Path, secret: str, token_ttl_seconds: int = 3600):
        self.users_file = users_file
        self.secret = secret.encode("utf-8")
        self.token_ttl_seconds = token_ttl_seconds
        self._lock = threading.RLock()
        self.users = self._load_users()

    def _load_users(self) -> Dict[str, Any]:
        if not self.users_file.exists():
            return {}
        try:
            with open(self.users_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            logger.exception("Falha ao carregar users.json")
            return {}

    def _save_users(self):
        self.users_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.users_file, "w", encoding="utf-8") as f:
            json.dump(self.users, f, ensure_ascii=False, indent=2)

    def _hash_password(self, password: str, salt: bytes) -> str:
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
        return dk.hex()

    def create_user(self, username: str, password: str, roles: List[str]):
        with self._lock:
            salt = os.urandom(16)
            self.users[username] = {
                "salt": base64.b64encode(salt).decode("ascii"),
                "hash": self._hash_password(password, salt),
                "roles": roles,
            }
            self._save_users()

    def verify_password(self, username: str, password: str) -> bool:
        u = self.users.get(username)
        if not u:
            return False
        salt = base64.b64decode(u["salt"].encode("ascii"))
        return hmac.compare_digest(u["hash"], self._hash_password(password, salt))

    def generate_token(self, username: str) -> str:
        expiry = int(time.time()) + self.token_ttl_seconds
        payload = f"{username}:{expiry}".encode("utf-8")
        sig = hmac.new(self.secret, payload, hashlib.sha256).digest()
        token = base64.urlsafe_b64encode(payload + b"." + sig).decode("ascii")
        return token

    def verify_token(self, token: str) -> Optional[str]:
        try:
            raw = base64.urlsafe_b64decode(token.encode("ascii"))
            payload, sig = raw.split(b".", 1)
            expected = hmac.new(self.secret, payload, hashlib.sha256).digest()
            if not hmac.compare_digest(expected, sig):
                return None
            username, expiry_s = payload.decode("utf-8").split(":")
            if int(expiry_s) < int(time.time()):
                return None
            if username not in self.users:
                return None
            return username
        except Exception:
            return None

    def has_role(self, username: str, role: str) -> bool:
        u = self.users.get(username)
        if not u:
            return False
        return role in u.get("roles", [])

def generate_protocolo(counter_file: Path, prefix: str = "PF", width: int = 3, retries: int = 5, retry_delay: float = 0.05) -> str:
    counter_file.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(retries):
        try:
            if counter_file.exists():
                with counter_file.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                n = int(data.get("counter", 0)) + 1
            else:
                n = 1
            payload = {"counter": n, "last_updated": datetime.utcnow().isoformat()}
            _atomic_write_json(counter_file, payload)
            return f"{prefix}-{n:0{width}d}"
        except Exception:
            time.sleep(retry_delay)
    return f"{prefix}-{uuid.uuid4().hex[:8].upper()}"

class ConsultorBibliaLegislativa:
    def __init__(self, caminho_biblia: Path):
        self.caminho_biblia = caminho_biblia
        self.biblia: Dict[str, Any] = self._carregar_biblia()

    def _carregar_biblia(self) -> Dict[str, Any]:
        try:
            if not self.caminho_biblia or not self.caminho_biblia.exists():
                logger.warning("Caminho da Bblia no encontrado: %s", self.caminho_biblia)
                return {}
            suffix = self.caminho_biblia.suffix.lower()
            if suffix == ".pdf" and PyPDF2:
                try:
                    with self.caminho_biblia.open("rb") as f:
                        reader = PyPDF2.PdfReader(f)
                        parts: List[str] = []
                        for p in reader.pages:
                            try:
                                parts.append(p.extract_text() or "")
                            except Exception:
                                parts.append("")
                        return {"texto_completo": "\n".join(parts)}
                except Exception:
                    logger.exception("Falha lendo PDF da Bblia")
        except Exception:
            logger.exception("Erro ao carregar Bblia")
        return {}

    def consultar_fundamento_biblico(self, tema: str) -> Dict[str, Any]:
        resultado = self.buscar_por_tema(tema, limite=3)
        return {"tema": tema, "versiculos_encontrados": resultado, "timestamp": datetime.now().isoformat()}

    def buscar_por_tema(self, tema: str, limite: int = 10) -> List[Dict[str, Any]]:
        resultados: List[Dict[str, Any]] = []
        try:
            termo = str(tema or "").lower().strip()
            if not termo:
                return resultados
            if isinstance(self.biblia, dict) and any(isinstance(v, dict) for v in self.biblia.values()):
                for _, v in self.biblia.items():
                    if isinstance(v, dict):
                        texto = str(v.get("texto", "")).lower()
                        if termo in texto:
                            resultados.append(v)
                            if len(resultados) >= limite:
                                break
            else:
                texto = str(self.biblia.get("texto_completo", "")).lower()
                if termo in texto:
                    for linha in texto.splitlines():
                        if termo in linha:
                            resultados.append({"trecho": linha.strip()})
                            if len(resultados) >= limite:
                                break
        except Exception:
            logger.exception("Erro ao buscar na Bblia")
        return resultados

class LivroDaLei:
    def __init__(self, caminho_livro: Path):
        self.caminho_livro = Path(caminho_livro)
        self.leis: Dict[str, Lei] = {}
        self._lock = threading.RLock()
        self._carregar_livro()

    def _carregar_livro(self):
        try:
            if self.caminho_livro.exists():
                with self.caminho_livro.open("r", encoding="utf-8") as f:
                    dados = json.load(f)
                with self._lock:
                    for item in dados:
                        try:
                            lei = Lei.from_dict(item)
                            if any(existing.numero_protocolo == lei.numero_protocolo for existing in self.leis.values()):
                                logger.warning("Protocolo duplicado ignorado: %s", lei.numero_protocolo)
                                continue
                            self.leis[lei.id] = lei
                        except Exception:
                            logger.exception("Item invlido no Livro da Lei: %s", item)
                logger.info("Livro da Lei carregado: %d leis", len(self.leis))
            else:
                logger.warning("Arquivo do Livro da Lei no encontrado: %s", self.caminho_livro)
        except Exception:
            logger.exception("Erro ao carregar Livro da Lei")

    def salvar_livro(self):
        try:
            with self._lock:
                dados = [lei.to_dict() for lei in self.leis.values()]
            _atomic_write_json(self.caminho_livro, dados)
            logger.info("Livro da Lei salvo")
        except Exception:
            logger.exception("Erro ao salvar Livro da Lei")

    def adicionar_lei(self, lei: Lei):
        with self._lock:
            if any(existing.numero_protocolo == lei.numero_protocolo for existing in self.leis.values()):
                raise ValueError(f"Protocolo j existente: {lei.numero_protocolo}")
            self.leis[lei.id] = lei
        self.salvar_livro()

    def buscar_leis_por_categoria(self, categoria: str) -> List[Lei]:
        with self._lock:
            return [lei for lei in self.leis.values() if lei.categoria.upper() == categoria.upper()]

    def buscar_lei_por_protocolo(self, protocolo: str) -> Optional[Lei]:
        with self._lock:
            for lei in self.leis.values():
                if lei.numero_protocolo.upper() == protocolo.upper():
                    return lei
        return None

    def buscar_leis_aplicaveis(self, descricao_caso: str) -> List[Lei]:
        descricao_lower = str(descricao_caso or "").lower()
        aplicaveis: List[Lei] = []
        with self._lock:
            for lei in self.leis.values():
                try:
                    if lei.status == StatusLei.ATIVA and (
                        (lei.principio and lei.principio.lower() in descricao_lower)
                        or any(word for word in lei.instrucao_base.lower().split() if word and word in descricao_lower)
                    ):
                        aplicaveis.append(lei)
                except Exception:
                    logger.debug("Erro avaliando lei %s", lei.id, exc_info=True)
        return aplicaveis[:10]

class ArquivoNovasLeis:
    def __init__(self, caminho_novas_leis: Path):
        self.caminho_novas_leis = caminho_novas_leis
        self.novas_leis: Dict[str, Lei] = {}
        self._lock = threading.RLock()
        self._carregar_novas_leis()

    def _carregar_novas_leis(self):
        try:
            if self.caminho_novas_leis.exists():
                with self.caminho_novas_leis.open("r", encoding="utf-8") as f:
                    dados = json.load(f)
                with self._lock:
                    for item in dados:
                        try:
                            lei = Lei.from_dict(item)
                            self.novas_leis[lei.id] = lei
                        except Exception:
                            logger.exception("Item invlido em novas_leis: %s", item)
                logger.info("Novas leis carregadas: %d aguardando aprovao", len(self.novas_leis))
        except Exception:
            logger.exception("Erro ao carregar novas leis")

    def salvar_novas_leis(self):
        try:
            with self._lock:
                dados = [lei.to_dict() for lei in self.novas_leis.values()]
            _atomic_write_json(self.caminho_novas_leis, dados)
            logger.info("Novas leis salvas")
        except Exception:
            logger.exception("Erro ao salvar novas leis")

    def adicionar_lei_aprovada_ais(self, lei: Lei):
        lei.status = StatusLei.AGUARDANDO_CRIADOR
        with self._lock:
            self.novas_leis[lei.id] = lei
        self.salvar_novas_leis()
        logger.info("Lei adicionada para aprovao do Criador: %s", lei.titulo)

    def remover_lei(self, id_lei: str):
        with self._lock:
            if id_lei in self.novas_leis:
                del self.novas_leis[id_lei]
        self.salvar_novas_leis()

class CamaraLegislativa:
    def __init__(
        self,
        config: Any = None,
        coracao_ref: Any = None,
        sistema_julgamento_ref: Any = None,
        sistema_precedentes_ref: Any = None,
    ):
        self.config = config or {}
        self.coracao = coracao_ref
        self.sistema_julgamento = sistema_julgamento_ref
        self.sistema_precedentes = sistema_precedentes_ref

        self.logger = logging.getLogger(self.__class__.__name__)
        self._lock = threading.RLock()

        repo_root = Path(self.config.get("repo_root")) if self.config.get("repo_root") else Path.cwd()

        self.caminho_livro_lei = Path(self.config.get("caminho_livro_lei", repo_root / "Santuarios/legislativo/leis_fundamentais.json"))
        self.caminho_biblia = Path(self.config.get("caminho_biblia", repo_root / "datasets_fine_tuning/novos_documentos_jw/Biblia.txt"))
        self.caminho_novas_leis = Path(self.config.get("caminho_novas_leis", repo_root / "Santuarios/legislativo/novas_leis.json"))
        self.caminho_categorias = Path(self.config.get("caminho_categorias", repo_root / "Santuarios/legislativo/leis_aceitas"))
        self.caminho_protocol_counter = Path(self.config.get("caminho_protocol_counter", repo_root / "Santuarios/legislativo/protocol_counter.json"))
        self.caminho_users = Path(self.config.get("caminho_users", repo_root / "Santuarios/legislativo/users.json"))
        self.auth_secret = self.config.get("auth_secret", "change-this-secret")

        self.livro_da_lei = LivroDaLei(self.caminho_livro_lei)
        self.consultor_biblia = ConsultorBibliaLegislativa(self.caminho_biblia)
        self.arquivo_novas_leis = ArquivoNovasLeis(self.caminho_novas_leis)

        self.auth = AuthManager(self.caminho_users, secret=self.auth_secret)

        self.categorias_classificadas: Dict[str, List[Dict[str, Any]]] = {}
        self._carregar_categorias()

        self.propostas_leis: Dict[str, PropostaLei] = {}
        self.membros_legislativos = list(self.config.get("MEMBROS_LEGISLATIVOS", ["EVA", "LUMINA", "NYRA", "YUNA", "KAIYA", "WELLINGTON"]))

        self.audit_path = self.config.get("audit_path", repo_root / "Santuarios/legislativo/audit.log")
        Path(self.audit_path).parent.mkdir(parents=True, exist_ok=True)

        self.logger.info("[OK] Cmara Legislativa inicializada with %d leis", len(self.livro_da_lei.leis))

    def _carregar_categorias(self):
        try:
            self.categorias_classificadas = {}
            if self.caminho_categorias.exists() and self.caminho_categorias.is_dir():
                for arquivo in self.caminho_categorias.glob("leis_*.json"):
                    try:
                        cat = arquivo.stem.replace("leis_", "")
                        with arquivo.open("r", encoding="utf-8") as f:
                            self.categorias_classificadas[cat] = json.load(f)
                    except Exception:
                        logger.exception("Erro carregando categoria: %s", arquivo)
        except Exception:
            logger.exception("Erro carregando categorias")

    def buscar_em_categoria(self, categoria: str, query: str = "") -> List[Dict]:
        if categoria not in self.categorias_classificadas:
            return []
        leis = self.categorias_classificadas[categoria]
        if query:
            q = query.lower()
            leis = [lei for lei in leis if q in json.dumps(lei, ensure_ascii=False).lower()]
        return leis[:10]

    def consultar_lei_por_protocolo(self, protocolo: str) -> Optional[Lei]:
        return self.livro_da_lei.buscar_lei_por_protocolo(protocolo)

    def consultar_biblia_para_lei(self, tema: str) -> Dict[str, Any]:
        return self.consultor_biblia.consultar_fundamento_biblico(tema)

    def buscar_leis_aplicaveis(self, descricao_caso: str) -> List[Lei]:
        leis = self.livro_da_lei.buscar_leis_aplicaveis(descricao_caso)
        if not leis:
            try:
                self.notificar_falta_lei(descricao_caso)
            except Exception:
                logger.debug("Erro notificando falta de lei (no crítico).")
        return leis

    def notificar_falta_lei(self, descricao_caso: str):
        logger.warning("Falta lei aplicvel para caso: %s", descricao_caso)
        if self.sistema_julgamento:
            try:
                self.sistema_julgamento.notificar_falta_lei_legislativa(descricao_caso)
            except Exception:
                logger.exception("Erro ao notificar sistema judicial")

    def propor_nova_lei(self, token: str, titulo: str, justificativa: str, necessidade: str, fundamento_biblico: str, detalhes: Dict[str, Any]) -> Tuple[bool, str]:
        username = self.auth.verify_token(token)
        if not username:
            return False, "Token invlido ou expirado"
        if not (self.auth.has_role(username, "legislativo") or username == "SISTEMA_LEGISLATIVO"):
            return False, "Usurio no autorizado"
        if not necessidade or len(str(necessidade).strip()) < 50:
            return False, "Necessidade deve explicar por que as leis existentes no bastam (mn.50 caracteres)"
        if not isinstance(detalhes, dict):
            return False, "Detalhes deve ser um objeto/dicionrio"
        id_proposta = str(uuid.uuid4())
        proposta = PropostaLei(
            id=id_proposta,
            titulo_proposto=str(titulo),
            justificativa=str(justificativa),
            necessidade=str(necessidade),
            fundamento_biblico=str(fundamento_biblico),
            detalhes_propostos=detalhes or {},
            autor_proponente=username,
            data_proposta=datetime.now(),
            status="EM_ANALISE",
        )
        with self._lock:
            self.propostas_leis[id_proposta] = proposta
            self._audit("propor_nova_lei", username, {"proposta_id": id_proposta, "titulo": titulo})
        if self.coracao and hasattr(self.coracao, "sistema_propostas"):
            try:
                self.coracao.sistema_propostas.registrar_proposta_legislativa(username, proposta.to_dict())
            except Exception:
                logger.debug("Erro ao notificar sistema de propostas (no crítico).")
        self.logger.info(" Nova lei proposta por %s: %s", username, titulo)
        return True, id_proposta

    def votar_proposta_lei(self, token: str, id_proposta: str, voto: bool) -> bool:
        username = self.auth.verify_token(token)
        if not username:
            return False
        if not (self.auth.has_role(username, "legislativo") or username in self.membros_legislativos):
            return False
        with self._lock:
            proposta = self.propostas_leis.get(id_proposta)
            if not proposta:
                return False
            if voto:
                proposta.votos_favor += 1
            else:
                proposta.votos_contra += 1
            total_votos = proposta.votos_favor + proposta.votos_contra
            quorum = max(1, len(self.membros_legislativos) or 6)
            if total_votos >= quorum:
                self._decidir_proposta(proposta)
            self._audit("votar_proposta", username, {"proposta_id": id_proposta, "voto": voto})
        return True

    def _decidir_proposta(self, proposta: PropostaLei):
        if proposta.votos_favor > proposta.votos_contra:
            lei = self._criar_lei_da_proposta(proposta)
            self.arquivo_novas_leis.adicionar_lei_aprovada_ais(lei)
            proposta.status = "APROVADA_AGUARDANDO_CRIADOR"
            self.logger.info(" Lei aprovada pelas AIs, aguardando Criador: %s", proposta.titulo_proposto)
        else:
            proposta.status = "REJEITADA"
            self.logger.info(" Lei rejeitada pelas AIs: %s", proposta.titulo_proposto)

    def _criar_lei_da_proposta(self, proposta: PropostaLei) -> Lei:
        protocolo = generate_protocolo(self.caminho_protocol_counter, prefix="PF", width=3)
        id_lei = str(uuid.uuid4())
        lei = Lei(
            id=id_lei,
            titulo=proposta.titulo_proposto,
            tipo=TipoLei.OPERACIONAL,
            categoria="NOVA",
            numero_protocolo=protocolo,
            principio=proposta.justificativa[:200],
            instrucao_base=proposta.justificativa,
            detalhes=proposta.detalhes_propostos or {},
            referencia_biblica=proposta.fundamento_biblico or "",
            autor_criador=proposta.autor_proponente or "",
            data_criacao=datetime.now(),
            status=StatusLei.AGUARDANDO_CRIADOR,
        )
        return lei

    def voto_final_criador(self, token: str, id_lei: str, aprovado: bool, motivo: str = "") -> bool:
        username = self.auth.verify_token(token)
        if not username:
            return False
        if not (username == "CRIADOR" or self.auth.has_role(username, "criador")):
            return False
        lei = self.arquivo_novas_leis.novas_leis.get(id_lei)
        if not lei:
            return False
        try:
            if aprovado:
                lei.status = StatusLei.ATIVA
                self.livro_da_lei.adicionar_lei(lei)
                try:
                    self.arquivo_novas_leis.remover_lei(id_lei)
                except Exception:
                    logger.debug("Erro ao remover lei das novas_leis aps aprovao (no crítico).")
                if self.sistema_precedentes and hasattr(self.sistema_precedentes, "registrar_precedente"):
                    try:
                        self.sistema_precedentes.registrar_precedente(
                            id_decisao_judicial=f"CRIADOR-APROVACAO-{id_lei}",
                            descricao_caso=lei.instrucao_base,
                            decisão="LEI_APROVADA_CRIADOR",
                            justificativa=motivo,
                            leis_aplicaveis=[lei.numero_protocolo],
                            autor_julgador="CRIADOR",
                        )
                    except Exception:
                        logger.debug("Erro ao registrar precedente (no crítico).")
                self.logger.critical(" Lei aprovada pelo Criador e entrou em vigor: %s", lei.titulo)
            else:
                lei.status = StatusLei.EM_DELIBERACAO
                try:
                    self.arquivo_novas_leis.remover_lei(id_lei)
                except Exception:
                    logger.debug("Erro ao remover lei das novas_leis aps rejeio (no crítico).")
                with self._lock:
                    proposta_rejeitada = PropostaLei(
                        id=str(uuid.uuid4()),
                        titulo_proposto=lei.titulo,
                        justificativa=lei.instrucao_base,
                        necessidade=f"Rejeitada pelo Criador: {motivo}",
                        fundamento_biblico=lei.referencia_biblica,
                        detalhes_propostos=lei.detalhes or {},
                        autor_proponente=lei.autor_criador or "",
                        data_proposta=datetime.now(),
                        status="REJEITADA_CRIADOR",
                    )
                    self.propostas_leis[proposta_rejeitada.id] = proposta_rejeitada
                self.logger.critical(" Lei rejeitada pelo Criador, voltou para legislativo: %s", lei.titulo)
            self._audit("voto_final_criador", username, {"id_lei": id_lei, "aprovado": aprovado})
            return True
        except Exception:
            logger.exception("Erro no processamento do voto final do Criador")
            return False

    def fornecer_leis_para_judiciario(self, descricao_caso: str) -> List[Dict[str, Any]]:
        leis = self.buscar_leis_aplicaveis(descricao_caso)
        return [lei.to_dict() for lei in leis]

    def revogar_lei(self, token: str, id_lei: str, motivo: str) -> bool:
        username = self.auth.verify_token(token)
        if not username:
            return False
        if not (self.auth.has_role(username, "legislativo") or self.auth.has_role(username, "criador")):
            return False
        lei = self.livro_da_lei.leis.get(id_lei)
        if not lei:
            return False
        try:
            lei.status = StatusLei.REVOGADA
            self.livro_da_lei.salvar_livro()
            if self.sistema_precedentes:
                try:
                    self.sistema_precedentes.registrar_precedente(
                        id_decisao_judicial=f"REVOGACAO-{id_lei}",
                        descricao_caso=motivo,
                        decisão="LEI_REVOGADA",
                        justificativa=motivo,
                        leis_aplicaveis=[lei.numero_protocolo],
                        autor_julgador="CAMARA_LEGISLATIVA",
                    )
                except Exception:
                    logger.debug("Erro ao registrar precedente")
            self._audit("revogar_lei", username, {"id_lei": id_lei, "motivo": motivo})
            self.logger.info(" Lei revogada: %s", lei.titulo)
            return True
        except Exception:
            logger.exception("Erro ao revogar lei")
            return False

    def obter_estatisticas_legislacao(self) -> Dict[str, Any]:
        try:
            total_leis = len(self.livro_da_lei.leis)
            leis_ativas = len([l for l in self.livro_da_lei.leis.values() if l.status == StatusLei.ATIVA])
            propostas_pendentes = len([p for p in self.propostas_leis.values() if p.status == "EM_ANALISE"])
            aguardando_criador = len(self.arquivo_novas_leis.novas_leis)
            return {
                "total_leis": total_leis,
                "leis_ativas": leis_ativas,
                "leis_revogadas": total_leis - leis_ativas,
                "propostas_pendentes": propostas_pendentes,
                "aguardando_criador": aguardando_criador,
                "membros_legislativos": self.membros_legislativos,
                "categorias_classificadas": list(self.categorias_classificadas.keys()),
            }
        except Exception:
            logger.exception("Erro ao compilar estatsticas")
            return {}

    def shutdown(self):
        try:
            self.livro_da_lei.salvar_livro()
        except Exception:
            logger.debug("Erro ao salvar Livro da Lei no shutdown (no crítico).")
        try:
            self.arquivo_novas_leis.salvar_novas_leis()
        except Exception:
            logger.debug("Erro ao salvar Novas Leis no shutdown (no crítico).")
        self.logger.info("Cmara Legislativa desligada")

class CamaraExecutiva:
    """
    Câmara Executiva — responsável por executar ações decididas pelo sistema judiciário/deliberativo.
    Gerencia fila de execução, rastreio de status e modo silêncio.
    """

    STATUS_PENDENTE   = "PENDENTE"
    STATUS_EXECUTANDO = "EXECUTANDO"
    STATUS_CONCLUIDO  = "CONCLUIDO"
    STATUS_FALHOU     = "FALHOU"
    STATUS_CANCELADO  = "CANCELADO"

    def __init__(self, config=None, coracao_ref=None, camara_judiciaria_ref=None):
        self.config               = config
        self.coracao_ref          = coracao_ref
        self.camara_judiciaria_ref = camara_judiciaria_ref
        self.ui_queue             = None
        self.consulado            = None
        self.modo_silencio_ativo  = False
        self._lock                = threading.Lock()
        self._acoes: Dict[str, Dict[str, Any]] = {}   # id_acao → registro
        self.logger = logging.getLogger("CamaraExecutiva")
        self.logger.info("[OK] CamaraExecutiva inicializada")

    # -----------------------------------------------------------------------
    # Injeção de dependências
    # -----------------------------------------------------------------------
    def injetar_ui_queue(self, queue: Any) -> None:
        """Injeta a fila de UI para envio de eventos."""
        self.ui_queue = queue

    def injetar_consulado(self, consulado: Any) -> None:
        """Injeta a referência ao Consulado Soberano."""
        self.consulado = consulado

    # -----------------------------------------------------------------------
    # Execução de ações
    # -----------------------------------------------------------------------
    def executar_acao(self, acao: Dict[str, Any]) -> Dict[str, Any]:
        """
        Registra e executa uma ação ordenada pelo judiciário/deliberativo.
        Retorna dict com id_acao e status.
        """
        if not isinstance(acao, dict):
            return {"erro": "acao deve ser um dicionário", "status": self.STATUS_FALHOU}

        id_acao = acao.get("id") or str(uuid.uuid4())
        tipo    = acao.get("tipo", "DESCONHECIDO")
        alvo    = acao.get("alvo", "")
        dados   = acao.get("dados", {})

        registro: Dict[str, Any] = {
            "id":          id_acao,
            "tipo":        tipo,
            "alvo":        alvo,
            "dados":       dados,
            "status":      self.STATUS_PENDENTE,
            "início":      datetime.utcnow().isoformat(),
            "fim":         None,
            "resultado":   None,
            "erro":        None,
        }

        with self._lock:
            self._acoes[id_acao] = registro

        self.logger.info("[EXEC] Iniciando ação id=%s tipo=%s alvo=%s", id_acao, tipo, alvo)

        # Se estiver em modo silêncio, bloqueia ações de voz/fala
        if self.modo_silencio_ativo and tipo in ("FALAR", "VOZ", "ANUNCIO"):
            registro["status"]    = self.STATUS_CANCELADO
            registro["resultado"] = "Bloqueado por modo silêncio"
            registro["fim"]       = datetime.utcnow().isoformat()
            self.logger.info("[EXEC] Ação %s cancelada: modo silêncio ativo", id_acao)
            self._notificar_ui(registro)
            return {"id_acao": id_acao, "status": self.STATUS_CANCELADO, "resultado": registro["resultado"]}

        # Executa a ação conforme tipo
        try:
            registro["status"] = self.STATUS_EXECUTANDO
            resultado = self._despachar_acao(tipo, alvo, dados, id_acao)
            registro["status"]    = self.STATUS_CONCLUIDO
            registro["resultado"] = resultado
        except Exception as exc:
            registro["status"] = self.STATUS_FALHOU
            registro["erro"]   = str(exc)
            self.logger.exception("[EXEC] Falha na ação id=%s: %s", id_acao, exc)
        finally:
            registro["fim"] = datetime.utcnow().isoformat()
            self._notificar_ui(registro)

        self.logger.info("[EXEC] Ação id=%s finalizada com status=%s", id_acao, registro["status"])
        return {
            "id_acao":   id_acao,
            "status":    registro["status"],
            "resultado": registro.get("resultado"),
            "erro":      registro.get("erro"),
        }

    def _despachar_acao(self, tipo: str, alvo: str, dados: Dict[str, Any], id_acao: str) -> Any:
        """Despacha a ação para o módulo correto conforme tipo."""
        tipo_upper = tipo.upper()

        if tipo_upper in ("MODO_SILENCIO", "SILENCIO"):
            self.ativar_modo_silencio()
            return "Modo silêncio ativado"

        if tipo_upper in ("DESATIVAR_SILENCIO",):
            self.desativar_modo_silencio()
            return "Modo silêncio desativado"

        if tipo_upper in ("NOTIFICAR_UI", "UI"):
            if self.ui_queue:
                try:
                    self.ui_queue.put_nowait({"tipo": "ACAO_EXECUTIVA", "dados": dados, "alvo": alvo})
                except Exception:
                    pass
            return "Notificação UI enviada"

        if tipo_upper in ("CONSULADO", "CONSULADO_ACAO"):
            if self.consulado and hasattr(self.consulado, "processar_acao_executiva"):
                return self.consulado.processar_acao_executiva(alvo, dados)
            return "Consulado indisponível para ação executiva"

        if tipo_upper in ("CORACAO", "CORACAO_ACAO"):
            if self.coracao_ref and hasattr(self.coracao_ref, "executar_comando_interno"):
                return self.coracao_ref.executar_comando_interno(alvo, dados)
            return "Coração indisponível para ação executiva"

        # Tipo genérico — registra e retorna aviso
        self.logger.debug("[EXEC] Tipo de ação '%s' sem handler dedicado; registrado apenas.", tipo)
        return f"Ação '{tipo}' registrada (sem handler dedicado)"

    def _notificar_ui(self, registro: Dict[str, Any]) -> None:
        """Envia evento de atualização para a UI via fila."""
        if not self.ui_queue:
            return
        try:
            self.ui_queue.put_nowait({
                "tipo":     "STATUS_ACAO_EXECUTIVA",
                "id_acao":  registro["id"],
                "status":   registro["status"],
                "tipo_acao": registro.get("tipo"),
                "fim":      registro.get("fim"),
            })
        except Exception:
            pass

    # -----------------------------------------------------------------------
    # Consulta de status
    # -----------------------------------------------------------------------
    def obter_status_execucao(self, id_acao: str) -> Dict[str, Any]:
        """Retorna o status atual de uma ação pelo seu id."""
        with self._lock:
            registro = self._acoes.get(id_acao)
        if not registro:
            return {"erro": f"Ação '{id_acao}' não encontrada", "status": None}
        return {
            "id_acao":   registro["id"],
            "tipo":      registro["tipo"],
            "alvo":      registro["alvo"],
            "status":    registro["status"],
            "início":    registro["início"],
            "fim":       registro["fim"],
            "resultado": registro["resultado"],
            "erro":      registro["erro"],
        }

    def listar_acoes(self, filtro_status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Lista todas as ações, opcionalmente filtradas por status."""
        with self._lock:
            acoes = list(self._acoes.values())
        if filtro_status:
            acoes = [a for a in acoes if a["status"] == filtro_status]
        return acoes

    # -----------------------------------------------------------------------
    # Modo silêncio
    # -----------------------------------------------------------------------
    def ativar_modo_silencio(self) -> None:
        """Ativa modo silêncio: bloqueia execução de ações de voz/anúncio."""
        with self._lock:
            self.modo_silencio_ativo = True
        self.logger.info("[EXEC] Modo silêncio ATIVADO")

    def desativar_modo_silencio(self) -> None:
        """Desativa modo silêncio."""
        with self._lock:
            self.modo_silencio_ativo = False
        self.logger.info("[EXEC] Modo silêncio DESATIVADO")

    # -----------------------------------------------------------------------
    # Status geral
    # -----------------------------------------------------------------------
    def obter_status(self) -> Dict[str, Any]:
        with self._lock:
            total     = len(self._acoes)
            pendentes = sum(1 for a in self._acoes.values() if a["status"] == self.STATUS_PENDENTE)
            concluidos = sum(1 for a in self._acoes.values() if a["status"] == self.STATUS_CONCLUIDO)
            falhos    = sum(1 for a in self._acoes.values() if a["status"] == self.STATUS_FALHOU)
        return {
            "operacional":        True,
            "modo_silencio":      self.modo_silencio_ativo,
            "total_acoes":        total,
            "acoes_pendentes":    pendentes,
            "acoes_concluidas":   concluidos,
            "acoes_falhas":       falhos,
        }

    def shutdown(self) -> None:
        self.logger.info("[OK] CamaraExecutiva desligada (%d ações registradas)", len(self._acoes))

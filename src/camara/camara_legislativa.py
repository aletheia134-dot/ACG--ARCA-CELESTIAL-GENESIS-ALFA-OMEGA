from __future__ import annotations

import json
import logging
import uuid
import os
import hmac
import base64
import hashlib
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from enum import Enum
import threading
from dataclasses import dataclass, field

try:
    import PyPDF2
except:
    logging.getLogger(__name__).warning("[AVISO] PyPDF2 no disponível")
    PyPDF2 = None

logger = logging.getLogger("CamaraLegislativa")
logger.addHandler(logging.NullHandler())

class StatusLei(Enum):
    ATIVA = "ativa"
    REVOGADA = "revogada"
    PROPOSTA = "proposta"
    EM_DELIBERACAO = "em_deliberacao"
    AGUARDANDO_CRIADOR = "aguardando_criador"

class TipoLei(Enum):
    FUNDAMENTAL = "fundamental"
    SOBERANIA = "soberania"
    OPERACIONAL = "operacional"
    TEMPORARIA = "temporaria"

def parse_enum(enum_cls, value, default):
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
    import tempfile
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
    def from_dict(cls, d: Dict[str, Any]) -> "Lei":
        tipo = parse_enum(TipoLei, d.get("tipo"), TipoLei.OPERACIONAL)
        status = parse_enum(StatusLei, d.get("status"), StatusLei.ATIVA)
        data_criacao = _safe_datetime_from_iso(d.get("data_criacao"))
        return cls(
            id=str(d.get("id", str(uuid.uuid4()))),
            titulo=str(d.get("titulo", "") or ""),
            tipo=tipo,
            categoria=str(d.get("categoria", "") or ""),
            numero_protocolo=str(d.get("numero_protocolo", "") or ""),
            principio=str(d.get("principio", "") or ""),
            instrucao_base=str(d.get("instrucao_base", "") or ""),
            detalhes=d.get("detalhes", {}) or {},
            referencia_biblica=str(d.get("referencia_biblica", "") or ""),
            autor_criador=str(d.get("autor_criador", "") or ""),
            data_criacao=data_criacao,
            status=status,
            versao=int(d.get("versao", 1)),
            leis_relacionadas=[str(x) for x in (d.get("leis_relacionadas") or [])],
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

class ConsultorBibliaLegislativa:
    def __init__(self, caminho_biblia: Path):
        self.caminho_biblia = Path(caminho_biblia)
        self.biblia = self._carregar_biblia()

    def _carregar_biblia(self) -> Dict[str, Any]:
        try:
            if not self.caminho_biblia.exists():
                logger.warning("Arquivo da Bblia no encontrado: %s", self.caminho_biblia)
                return {}
            suffix = self.caminho_biblia.suffix.lower()
            if suffix == ".json":
                with self.caminho_biblia.open("r", encoding="utf-8") as f:
                    return json.load(f)
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
            if not self.caminho_livro.exists():
                logger.warning("Arquivo do Livro da Lei no encontrado: %s", self.caminho_livro)
                return
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
            return [lei for lei in self.leis.values() if str(lei.categoria).upper() == str(categoria).upper()]

    def buscar_lei_por_protocolo(self, protocolo: str) -> Optional[Lei]:
        with self._lock:
            for lei in self.leis.values():
                if str(lei.numero_protocolo).upper() == str(protocolo).upper():
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
                        or (lei.instrucao_base and any(p in descricao_lower for p in lei.instrucao_base.lower().split()))
                    ):
                        aplicaveis.append(lei)
                except Exception:
                    logger.debug("Erro avaliando lei %s", lei.id, exc_info=True)
        return aplicaveis[:10]

class ArquivoNovasLeis:
    def __init__(self, caminho_novas_leis: Path):
        self.caminho_novas_leis = Path(caminho_novas_leis)
        self.novas_leis: Dict[str, Lei] = {}
        self._lock = threading.RLock()
        self._carregar_novas_leis()

    def _carregar_novas_leis(self):
        try:
            if not self.caminho_novas_leis.exists():
                return
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

        # CORREÇÃO: usar diretorio_raiz do config.ini
        repo_root = Path(self.config.get("PATHS", "diretorio_raiz", Path.cwd()))

        # CORREÇÃO: usar caminho_leis_fundamentais (config.ini) em vez de caminho_livro_lei
        self.caminho_livro_lei = Path(self.config.get("LEGISLATIVO", "caminho_leis_fundamentais", str(repo_root / "Santuarios/legislativo/leis_fundamentais.json")))
        self.caminho_biblia = Path(self.config.get("LEGISLATIVO", "caminho_biblia", str(repo_root / "datasets_fine_tuning/novos_documentos_jw/Biblia.json")))
        self.caminho_novas_leis = Path(self.config.get("LEGISLATIVO", "caminho_novas_leis", str(repo_root / "Santuarios/legislativo/novas_leis.json")))
        self.caminho_categorias = Path(self.config.get("LEGISLATIVO", "caminho_categorias", str(repo_root / "Santuarios/legislativo/leis_aceitas")))
        self.caminho_protocol_counter = Path(self.config.get("LEGISLATIVO", "caminho_protocol_counter", str(repo_root / "Santuarios/legislativo/protocol_counter.json")))
        self.caminho_users = Path(self.config.get("LEGISLATIVO", "caminho_users", str(repo_root / "Santuarios/legislativo/users.json")))
        # auth_secret: garantir que nunca seja None independente do tipo de config
        _raw_secret = self.config.get("LEGISLATIVO", "auth_secret", "change-this-secret")
        self.auth_secret = str(_raw_secret) if _raw_secret else "change-this-secret"

        self.livro_da_lei = LivroDaLei(self.caminho_livro_lei)
        self.consultor_biblia = ConsultorBibliaLegislativa(self.caminho_biblia)
        self.arquivo_novas_leis = ArquivoNovasLeis(self.caminho_novas_leis)

        self.auth = AuthManager(self.caminho_users, secret=self.auth_secret)

        self.categorias_classificadas: Dict[str, List[Dict[str, Any]]] = {}
        self._carregar_categorias()

        self.propostas_leis: Dict[str, PropostaLei] = {}
        self.membros_legislativos = list(self.config.get("ALMAS", "lista_almas_votantes_csv", ["EVA", "LUMINA", "NYRA", "YUNA", "KAIYA", "WELLINGTON"]))

        audit_path_str = self.config.get("LEGISLATIVO", "audit_path", str(repo_root / "Santuarios/legislativo/audit.log"))
        self.audit_path = Path(audit_path_str)
        self.audit_path.parent.mkdir(parents=True, exist_ok=True)

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

    def _audit(self, action: str, actor: str, payload: Dict[str, Any]):
        entry = {"ts": _now_iso(), "action": action, "actor": actor, "payload": payload}
        try:
            with open(self.audit_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception:
            logger.exception("Erro escrevendo audit")

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
        if self.sistema_julgamento and hasattr(self.sistema_julgamento, "notificar_falta_lei_legislativa"):
            try:
                self.sistema_julgamento.notificar_falta_lei_legislativa(descricao_caso)
            except Exception:
                logger.exception("Erro ao notificar judicial sobre falta de lei")

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
            try:
                self.arquivo_novas_leis.adicionar_lei_aprovada_ais(lei)
            except Exception:
                logger.exception("Erro ao persistir nova lei aguardando Criador")
            proposta.status = "APROVADA_AGUARDANDO_CRIADOR"
            self.logger.info(" Lei aprovada pelas AIs, aguardando Criador: %s", proposta.titulo_proposto)
        else:
            proposta.status = "REJEITADA"
            self.logger.info(" Lei rejeitada pelas AIs: %s", proposta.titulo_proposto)

    def _criar_lei_da_proposta(self, proposta: PropostaLei) -> Lei:
        counter_file = self.caminho_protocol_counter
        attempts = 5
        for _ in range(attempts):
            try:
                if counter_file.exists():
                    with counter_file.open("r", encoding="utf-8") as f:
                        data = json.load(f)
                    n = int(data.get("counter", 0)) + 1
                else:
                    n = 1
                payload = {"counter": n, "last_updated": datetime.utcnow().isoformat()}
                _atomic_write_json(counter_file, payload)
                numero_protocolo = f"PF-{n:03d}"
                break
            except Exception:
                time.sleep(0.05)
        else:
            numero_protocolo = f"PF-{uuid.uuid4().hex[:8].upper()}"

        lei = Lei(
            id=str(uuid.uuid4()),
            titulo=proposta.titulo_proposto,
            tipo=TipoLei.OPERACIONAL,
            categoria="NOVA",
            numero_protocolo=numero_protocolo,
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
                            leis_aplicaveis=[],
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
            self.logger.info("Lei revogada: %s", lei.titulo)
            return True
        except Exception:
            logger.exception("Erro ao revogar lei")
            return False

    def fornecer_leis_para_judiciario(self, descricao_caso: str) -> List[Dict[str, Any]]:
        leis = self.buscar_leis_aplicaveis(descricao_caso)
        return [lei.to_dict() for lei in leis]

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
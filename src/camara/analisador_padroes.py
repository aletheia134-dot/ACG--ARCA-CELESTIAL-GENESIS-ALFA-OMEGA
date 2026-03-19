from collections import Counter, defaultdict
import re
from typing import List, Dict, Any, Tuple

def hierarquia_valores(items: List[str]) -> List[Tuple[str, int]]:
    if not items:
        return []
    cnt = Counter(items)
    return cnt.most_common()

def mapear_associacoes_semanticas(text: str, window: int = 4) -> Dict[str, List[str]]:
    if not text:
        return {}
    tokens = re.findall(r'\\w+', text.lower())
    assoc = defaultdict(Counter)
    for i, t in enumerate(tokens):
        start = max(0, i - window)
        end = min(len(tokens), i + window + 1)
        for j in range(start, end):
            if j == i:
                continue
            assoc[t][tokens[j]] += 1
    return {k: [x for x, _ in v.most_common(5)] for k, v in assoc.items()}

def perfil_aprendizado(history: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not history:
        return {"total": 0, "by_tag": {}, "success_rate": 0.0}
    total = len(history)
    by_tag = defaultdict(lambda: {"ok": 0, "total": 0})
    ok_count = 0
    for ev in history:
        tag = ev.get("tag", "default")
        success = bool(ev.get("success"))
        by_tag[tag]["total"] += 1
        if success:
            by_tag[tag]["ok"] += 1
            ok_count += 1
    for t, v in by_tag.items():
        v["rate"] = v["ok"] / v["total"] if v["total"] else 0.0
    return {"total": total, "by_tag": dict(by_tag), "success_rate": ok_count / total}

# Adicionado: Classe AnalisadorDePadroes (para resolver import)
class AnalisadorDePadroes:
    def __init__(self, config=None, memoria_ref=None, cerebro_ref=None):
        self.config = config
        self.memoria_ref = memoria_ref
        self.cerebro_ref = cerebro_ref
        # Implementar lógica básica se necessário, usando as funções acima

    def hierarquia_valores(self, items: List[str]) -> List[Tuple[str, int]]:
        return hierarquia_valores(items)

    def mapear_associacoes_semanticas(self, text: str, window: int = 4) -> Dict[str, List[str]]:
        return mapear_associacoes_semanticas(text, window)

    def perfil_aprendizado(self, history: List[Dict[str, Any]]) -> Dict[str, Any]:
        return perfil_aprendizado(history)


# ─────────────────────────────────────────────────────────────────────────────
# PerfilComportamental — dataclass de perfil de alma para geração de artefatos
# (Aqui para centralizar o import, evitando dependência circular com gerador_almas)
# ─────────────────────────────────────────────────────────────────────────────
from dataclasses import dataclass, field
from typing import Optional as _Opt

@dataclass
class PerfilComportamental:
    """Perfil comportamental de uma alma — usado pelo GeradorDeAlmas e câmaras."""
    nome_alma_destino: str = "ALMA"
    descricao_alma_externa: str = ""
    estilo_comunicacao: str = "claro"
    nivel_formalidade: str = "moderado"
    valores_principais: List[str] = field(default_factory=list)
    areas_interesse: List[str] = field(default_factory=list)
    assinaturas_linguisticas: List[str] = field(default_factory=list)
    padrao_racional_preferido: str = "pragmatico"
    nivel_seguranca: str = "padrao"
    nivel_abertura: str = "moderado"
    humor_base: str = "sereno"
    tracos_personalidade: List[str] = field(default_factory=list)
    restricoes_tematicas: List[str] = field(default_factory=list)
    idioma_principal: str = "pt"
    metadados: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        from dataclasses import asdict
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "PerfilComportamental":
        valid = {k: v for k, v in d.items() if k in cls.__dataclass_fields__}
        return cls(**valid)

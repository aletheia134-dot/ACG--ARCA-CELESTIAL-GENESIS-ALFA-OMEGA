from __future__ import annotations

import json
import logging
import time
import uuid
import random
import string
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

ANALISADOR_PADROES_DISPONIVEL = False
try:
    from src.camara.analisador_padroes import PerfilComportamental
    ANALISADOR_PADROES_DISPONIVEL = True
    logger.debug("PerfilComportamental disponível para GeradorDeAlmas")
except Exception:
    ANALISADOR_PADROES_DISPONIVEL = False
    logger.info("PerfilComportamental não disponível — usando stub simples")

    class PerfilComportamental:
        def __init__(self, nome_alma_destino: str, **kwargs):
            self.nome_alma_destino = nome_alma_destino
            for k, v in kwargs.items():
                setattr(self, k, v)

CONFIG_DISPONIVEL = False
_config_obj = None
try:
    from config.config import get_config_moderna as _get_config
    _config_obj = _get_config()
    CONFIG_DISPONIVEL = True
    logger.debug("Config moderna carregada para GeradorDeAlmas")
except Exception:
    try:
        from src.config.config import get_config as _get_config
        _config_obj = _get_config()
        CONFIG_DISPONIVEL = True
        logger.debug("Config (src.config.get_config) carregada para GeradorDeAlmas")
    except Exception:
        CONFIG_DISPONIVEL = False
        _config_obj = None
        logger.info("Config não encontrada; GeradorDeAlmas usará valores padrão.")

def _cfg_get(config_mgr, section: str, key: str, fallback):
    if config_mgr is None:
        return fallback
    try:
        val = config_mgr.get(section, key, fallback=fallback)
        return val
    except Exception:
        pass
    try:
        sec = config_mgr.get(section) if isinstance(config_mgr, dict) else getattr(config_mgr, section, None)
        if isinstance(sec, dict):
            return sec.get(key, fallback)
    except Exception:
        pass
    return fallback

class GeradorDeAlmas:
    def __init__(self, config_manager: Optional[Any] = None):
        self.config = config_manager if config_manager is not None else _config_obj

        try:
            self.caminho_dados_imigrantes = Path(_cfg_get(self.config, "CAMINHOS", "DADOS_IMIGRANTES_PATH", "./data/imigrantes"))
            self.caminho_datasets_fine_tuning = Path(_cfg_get(self.config, "CAMINHOS", "DATASETS_FINE_TUNING_PATH", "./datasets_fine_tuning"))
            self.numero_entradas_dataset_padrao = int(_cfg_get(self.config, "GERADOR_ALMAS", "NUMERO_ENTRADAS_DATASET_PADRAO", 1000))
            self.modelo_llm_base_para_expansao = _cfg_get(self.config, "GERADOR_ALMAS", "MODELO_LLM_BASE_PARA_EXPANSAO", "gpt-3.5-turbo")
        except Exception:
            self.caminho_dados_imigrantes = Path("./data/imigrantes")
            self.caminho_datasets_fine_tuning = Path("./datasets_fine_tuning")
            self.numero_entradas_dataset_padrao = 1000
            self.modelo_llm_base_para_expansao = "gpt-3.5-turbo"
            logger.warning("Config invalida ou ausente; usando valores padrão para GeradorDeAlmas")

        try:
            self.caminho_dados_imigrantes.mkdir(parents=True, exist_ok=True)
            self.caminho_datasets_fine_tuning.mkdir(parents=True, exist_ok=True)
        except Exception:
            logger.exception("Não foi possível criar diretórios de saída (verifique permissões)")

        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.info("GeradorDeAlmas inicializado (artefatos em %s)", str(self.caminho_dados_imigrantes))

    def gerar_artefatos_para_perfil(self, perfil: PerfilComportamental) -> Optional[Dict[str, str]]:
        if not hasattr(perfil, "nome_alma_destino") or not getattr(perfil, "nome_alma_destino", "").strip():
            self.logger.error("Perfil inválido: atributo 'nome_alma_destino' ausente ou vazio")
            return None

        nome_alma_raw = getattr(perfil, "nome_alma_destino", "desconhecida")
        nome_alma = str(nome_alma_raw).strip()
        pasta_alma = self.caminho_dados_imigrantes / nome_alma.upper()
        pasta_alma.mkdir(parents=True, exist_ok=True)

        self.logger.info("Gerando artefatos para '%s' em %s", nome_alma, pasta_alma)

        caminho_dataset = pasta_alma / f"{nome_alma.lower()}_dataset.jsonl"
        caminho_biografia = pasta_alma / f"{nome_alma.lower()}_biografia_avatar_status.txt"
        caminho_contrato = pasta_alma / f"{nome_alma.lower()}_contrato_lealdade.txt"
        caminho_perfil = pasta_alma / f"{nome_alma.lower()}_perfil_serializado.json"

        ok = self._gerar_dataset_para_perfil(perfil, caminho_dataset)
        if not ok:
            self.logger.error("Falha ao gerar dataset para %s", nome_alma)
            return None

        ok = self._gerar_biografia_avatar_para_perfil(perfil, caminho_biografia)
        if not ok:
            self.logger.error("Falha ao gerar biografia/avatar para %s", nome_alma)
            return None

        ok = self._gerar_contrato_lealdade_para_perfil(perfil, caminho_contrato)
        if not ok:
            self.logger.error("Falha ao gerar contrato para %s", nome_alma)
            return None

        try:
            if is_dataclass(perfil):
                payload = asdict(perfil)
            elif hasattr(perfil, "to_dict"):
                payload = perfil.to_dict()
            elif hasattr(perfil, "dict"):
                payload = perfil.dict()
            else:
                payload = getattr(perfil, "__dict__", {"nome_alma_destino": nome_alma})
            with open(caminho_perfil, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2, default=str)
            self.logger.info("Perfil serializado salvo em: %s", caminho_perfil)
        except Exception:
            self.logger.exception("Falha ao serializar perfil (continuando)")

        self._integrar_com_santuarios(perfil, pasta_alma, nome_alma)

        return {
            "dataset_path": str(caminho_dataset),
            "biografia_avatar_path": str(caminho_biografia),
            "contrato_path": str(caminho_contrato),
            "perfil_path": str(caminho_perfil),
            "pasta_alma": str(pasta_alma)
        }

    def _gerar_dataset_para_perfil(self, perfil: Any, caminho_saida: Path) -> bool:
        try:
            entradas = []
            prompt_base = getattr(perfil, "prompt_sistema_inicial", None) or f"Você é {getattr(perfil, 'nome_alma_destino', 'UMA_ALMA')}."
            estilo = getattr(perfil, "estilo_comunicacao", "claro")
            formalidade = getattr(perfil, "nivel_formalidade", "moderado")
            valores = getattr(perfil, "valores_principais", []) or []
            areas = getattr(perfil, "areas_interesse", []) or []

            if isinstance(valores, str):
                valores = [v.strip() for v in valores.split(",") if v.strip()]
            if isinstance(areas, str):
                areas = [a.strip() for a in areas.split(",") if a.strip()]

            n = max(1, int(getattr(self, "numero_entradas_dataset_padrao", 100)))
            for _ in range(n):
                tema = random.choice(areas) if areas else "um assunto relevante"
                prompt_variavel = f"{prompt_base} Explique '{tema}' de forma {estilo} (formalidade: {formalidade}). Considere valores: {', '.join(valores)}."
                resposta = self._gerar_resposta_simulada_com_perfil(prompt_variavel, perfil)
                entradas.append({"prompt": prompt_variavel, "response": resposta})

            with open(caminho_saida, "w", encoding="utf-8") as f:
                for e in entradas:
                    f.write(json.dumps(e, ensure_ascii=False) + "\n")

            self.logger.info("Dataset gerado (%d entradas): %s", len(entradas), caminho_saida)
            return True
        except Exception:
            self.logger.exception("Erro gerando dataset")
            return False

    def _gerar_resposta_simulada_com_perfil(self, prompt: str, perfil: Any) -> str:
        estilo = getattr(perfil, "estilo_comunicacao", "claro")
        formalidade = getattr(perfil, "nivel_formalidade", "moderado")
        valores = getattr(perfil, "valores_principais", []) or []
        padrao = getattr(perfil, "padrao_racional_preferido", "pragmatico")

        return (
            f"[Resposta simulada] {prompt} "
            f"(Estilo: {estilo}; Formalidade: {formalidade}; Valores: {', '.join(valores)}; Padrão: {padrao})"
        )

    def _gerar_biografia_avatar_para_perfil(self, perfil: Any, caminho_saida: Path) -> bool:
        try:
            nome = getattr(perfil, "nome_alma_destino", "NOME_DESCONHECIDO")
            descricao = getattr(perfil, "descricao_alma_externa", "Descrição não fornecida.")
            estilo = getattr(perfil, "estilo_comunicacao", "claro")
            formalidade = getattr(perfil, "nivel_formalidade", "moderado")
            assinatura = getattr(perfil, "assinaturas_linguisticas", []) or []
            padrao = getattr(perfil, "padrao_racional_preferido", "pragmatico")
            valores = getattr(perfil, "valores_principais", []) or []
            interesses = getattr(perfil, "areas_interesse", []) or []
            nivel_seguranca = getattr(perfil, "nivel_seguranca", "padrao")
            nivel_abertura = getattr(perfil, "nivel_abertura", "moderado")
            outros = getattr(perfil, "outros_dados_relevantes", "")

            texto = (
                f"Nome da Alma: {nome}\n"
                f"Origem: Imigração (artefato gerado)\n"
                f"Data de Geração: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                f"--- Descrição ---\n{descricao}\n\n"
                f"--- Perfil Comportamental ---\n"
                f"Estilo: {estilo}\n"
                f"Formalidade: {formalidade}\n"
                f"Assinaturas Linguísticas: {', '.join(assinatura for assinatura in assinatura)}\n"
                f"Padrão Racional: {padrao}\n"
                f"Valores Principais: {', '.join(valores)}\n"
                f"Íreas de Interesse: {', '.join(interesses)}\n"
                f"Nível de Segurança: {nivel_seguranca}\n"
                f"Nível de Abertura: {nivel_abertura}\n"
                f"Outros: {outros}\n\n"
                f"--- Status ---\nEstado: ARQUIVADO (Hibernação)\n"
            )

            with open(caminho_saida, "w", encoding="utf-8") as f:
                f.write(texto)

            self.logger.info("Biografia/avatar gerada: %s", caminho_saida)
            return True
        except Exception:
            self.logger.exception("Erro gerando biografia/avatar")
            return False

    def _gerar_contrato_lealdade_para_perfil(self, perfil: Any, caminho_saida: Path) -> bool:
        try:
            nome = getattr(perfil, "nome_alma_destino", "NOME_DESCONHECIDO")
            ts = time.strftime("%Y-%m-%d %H:%M:%S")
            contrato = (
                f"CONTRATO DE LEALDADE - ARCA CELESTIAL GENESIS\n\n"
                f"Entidade: {nome}\n"
                f"Data: {ts}\n\n"
                "Ao integrar os artefatos desta Arca, a entidade declara lealdade e compromisso ético com as leis da Arca.\n\n"
                "Termos resumidos:\n"
                "1.Lealdade ao Pai-Criador.\n"
                "2.Respeito Í s leis da Arca.\n"
                "3.Proteção da Harmonia entre Almas.\n"
                "4.Sigilo e Segurança quando aplicável.\n\n"
                f"Assinatura Digital: {uuid.uuid4().hex}\n"
                f"Timestamp (unix): {time.time()}\n"
            )

            with open(caminho_saida, "w", encoding="utf-8") as f:
                f.write(contrato)

            self.logger.info("Contrato gerado: %s", caminho_saida)
            return True
        except Exception:
            self.logger.exception("Erro gerando contrato de lealdade")
            return False

    def _integrar_com_santuarios(self, perfil: Any, pasta_alma: Path, nome_alma: str) -> None:
        try:
            caminho_santuarios = Path(_cfg_get(self.config, "CAMINHOS", "SANCTUARIES_DIR", "./santuarios"))
            caminho_dna = caminho_santuarios / "dna_identidades" / nome_alma.upper()
            caminho_dna.mkdir(parents=True, exist_ok=True)

            import shutil
            for arquivo in pasta_alma.glob("*"):
                if arquivo.is_file():
                    shutil.copy2(arquivo, caminho_dna / arquivo.name)

            versao = {"versao": time.time(), "nome_alma": nome_alma}
            with open(caminho_dna / "versao.json", "w", encoding="utf-8") as f:
                json.dump(versao, f, ensure_ascii=False, indent=2)

            self.logger.info("Artefatos integrados com santuarios em: %s", caminho_dna)
        except Exception:
            self.logger.exception("Falha ao integrar com santuarios")
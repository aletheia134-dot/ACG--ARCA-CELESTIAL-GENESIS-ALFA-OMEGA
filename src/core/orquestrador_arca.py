# -*- coding: utf-8 -*-
from __future__ import annotations
"""
orquestrador_arca.py
OrquestradorArca: finetuning das 6 IAs com LoRA usando unsloth/peft.
Cada alma tem seu próprio módulo lora_[nome].py com treinar_lora_[nome]().
Requer GPU NVIDIA com CUDA e venv finetuning com unsloth instalado.
"""
import os
import sys
import logging
import threading
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)
__all__ = ["OrquestradorArca"]

# Mapa: nome da alma → info de treino
_MAPA_ALMAS: Dict[str, Dict[str, Any]] = {
    "EVA": {
        "modulo": "lora_eva",
        "funcao": "treinar_lora_eva",
        "output_dir": "02_LORA_EVA/lora_eva_treinado",
        "dataset": "01_DATASET_EVA/dataset_eva_10k.jsonl",
    },
    "KAIYA": {
        "modulo": "lora_kaiya",
        "funcao": "treinar_lora_kaiya",
        "output_dir": "02_LORA_KAIYA/lora_kaiya_treinado",
        "dataset": "01_DATASET_KAIYA/dataset_kaiya_10k.jsonl",
    },
    "LUMINA": {
        "modulo": "lora_lumina",
        "funcao": "treinar_lora_lumina",
        "output_dir": "02_LORA_LUMINA/lora_lumina_treinado",
        "dataset": "01_DATASET_LUMINA/dataset_lumina_10k.jsonl",
    },
    "NYRA": {
        "modulo": "lora_nyra",
        "funcao": "treinar_lora_nyra",
        "output_dir": "lora_nyra_treinado",
        "dataset": "dataset_nyra_10k.jsonl",
    },
    "WELLINGTON": {
        "modulo": "lora_wellington",
        "funcao": None,  # script sem função exportada — usar subprocess
        "output_dir": "lora_wellington_emocional",
        "dataset": "dataset_wellington_10k.jsonl",
    },
    "YUNA": {
        "modulo": "lora_yuna",
        "funcao": "treinar_lora_yuna",
        "output_dir": "lora_yuna_treinado",
        "dataset": "dataset_yuna_10k.jsonl",
    },
}


class OrquestradorArca:
    """Orquestrador de finetuning das almas da ARCA."""

    ALMAS = list(_MAPA_ALMAS.keys())

    def __init__(self, config: Any = None):
        self.config = config
        self._gpu_disponivel = self._verificar_gpu()
        self._registro: Dict[str, Dict[str, Any]] = {}
        self._threads_treino: Dict[str, threading.Thread] = {}
        self.registro = self._registro  # referência pública para o Coração
        logger.info("[OK] OrquestradorArca inicializado (GPU=%s)", self._gpu_disponivel)

    # ------------------------------------------------------------------
    # GPU
    # ------------------------------------------------------------------
    def _verificar_gpu(self) -> bool:
        try:
            import torch
            disponivel = torch.cuda.is_available()
            if disponivel:
                nome = torch.cuda.get_device_name(0)
                vram = round(torch.cuda.get_device_properties(0).total_memory / 1024**3, 1)
                logger.info("[GPU] %s — %.1fGB VRAM", nome, vram)
            return disponivel
        except Exception as e:
            logger.warning("[GPU] torch não disponível: %s", e)
            return False

    # ------------------------------------------------------------------
    # treinar_ia — ponto de entrada chamado pelo Coração
    # ------------------------------------------------------------------
    def treinar_ia(
        self,
        nome_alma: str,
        dataset_path: str = None,
        epochs: int = None,
        batch_size: int = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Inicia o treinamento LoRA de uma alma em thread background.
        Retorna imediatamente; use status_treino() para acompanhar.
        """
        nome_alma = nome_alma.upper()

        if nome_alma not in _MAPA_ALMAS:
            msg = f"Alma '{nome_alma}' desconhecida. Válidas: {self.ALMAS}"
            logger.error("[ERRO] %s", msg)
            return {"status": "erro", "alma": nome_alma, "erro": msg}

        if not self._gpu_disponivel:
            logger.warning("[AVISO] GPU indisponível — treino de %s cancelado", nome_alma)
            return {
                "status": "sem_gpu",
                "alma": nome_alma,
                "motivo": "GPU NVIDIA com CUDA é obrigatória para LoRA",
                "solucao": "Instale torch+cu121 e execute com GPU ativa",
            }

        # Evitar treino duplicado
        if self._registro.get(nome_alma, {}).get("status") == "executando":
            logger.info("[INFO] Treino de %s já em execução", nome_alma)
            return {"status": "ja_executando", "alma": nome_alma}

        # Registrar job
        job_id = f"{nome_alma}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self._registro[nome_alma] = {
            "job_id": job_id,
            "alma": nome_alma,
            "status": "iniciando",
            "inicio": datetime.now().isoformat(),
            "dataset_path": dataset_path or _MAPA_ALMAS[nome_alma]["dataset"],
            "epochs": epochs,
            "batch_size": batch_size,
            "fim": None,
            "erro": None,
            "output_dir": None,
        }

        t = threading.Thread(
            target=self._executar_treino,
            args=(nome_alma, dataset_path, epochs, batch_size),
            name=f"treino_{nome_alma}",
            daemon=True,
        )
        self._threads_treino[nome_alma] = t
        t.start()

        logger.info("[START] Treino LoRA iniciado para %s (job=%s)", nome_alma, job_id)
        return {
            "status": "iniciado",
            "alma": nome_alma,
            "job_id": job_id,
            "mensagem": f"Treinamento LoRA de {nome_alma} rodando em background",
        }

    # ------------------------------------------------------------------
    # _executar_treino (thread worker)
    # ------------------------------------------------------------------
    def _executar_treino(
        self,
        nome_alma: str,
        dataset_path: Optional[str],
        epochs: Optional[int],
        batch_size: Optional[int],
    ) -> None:
        reg = self._registro[nome_alma]
        reg["status"] = "executando"
        info = _MAPA_ALMAS[nome_alma]

        try:
            ok = self._treinar_via_import(nome_alma, info)
            if not ok:
                ok = self._treinar_via_subprocess(nome_alma, info)
            if not ok:
                raise RuntimeError("Import e subprocess falharam — verifique unsloth/dependências")

            reg["status"] = "concluido"
            reg["fim"] = datetime.now().isoformat()
            reg["output_dir"] = info["output_dir"]
            logger.info("[OK] Treino LoRA de %s concluído", nome_alma)

        except Exception as e:
            reg["status"] = "erro"
            reg["fim"] = datetime.now().isoformat()
            reg["erro"] = str(e)
            logger.exception("[ERRO] Treino de %s falhou: %s", nome_alma, e)

    def _treinar_via_import(self, nome_alma: str, info: Dict[str, Any]) -> bool:
        """Importa lora_[nome].py e chama treinar_lora_[nome]()."""
        nome_funcao = info.get("funcao")
        if not nome_funcao:
            return False  # Wellington usa subprocess

        raiz = str(Path(__file__).parent)
        if raiz not in sys.path:
            sys.path.insert(0, raiz)

        try:
            import importlib
            mod = importlib.import_module(info["modulo"])
            fn = getattr(mod, nome_funcao)
            logger.info("[LoRA] %s.%s() iniciando...", info["modulo"], nome_funcao)
            resultado = fn()
            return bool(resultado)
        except ImportError as e:
            logger.warning("[LoRA] Import falhou para %s: %s — tentando subprocess", nome_alma, e)
            return False
        except Exception as e:
            logger.error("[LoRA] Erro ao executar %s: %s", nome_funcao, e)
            raise

    def _treinar_via_subprocess(self, nome_alma: str, info: Dict[str, Any]) -> bool:
        """Executa lora_[nome].py via subprocess."""
        raiz = Path(__file__).parent
        script = raiz / f"{info['modulo']}.py"

        if not script.exists():
            logger.error("[LoRA] Script não encontrado: %s", script)
            return False

        # Preferir venv finetuning se existir
        python_exec = sys.executable
        for candidato in [
            raiz / "venvs" / "finetuning" / "Scripts" / "python.exe",
            raiz / "venvs" / "finetuning" / "bin" / "python",
        ]:
            if candidato.exists():
                python_exec = str(candidato)
                break

        logger.info("[LoRA] subprocess: %s %s", python_exec, script.name)
        proc = subprocess.run(
            [python_exec, str(script)],
            cwd=str(raiz),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

        if proc.returncode == 0:
            logger.info("[LoRA] subprocess OK para %s", nome_alma)
            return True

        logger.error(
            "[LoRA] subprocess falhou para %s (rc=%d)\nSTDOUT: %s\nSTDERR: %s",
            nome_alma, proc.returncode,
            (proc.stdout or "")[-2000:],
            (proc.stderr or "")[-2000:],
        )
        return False

    # ------------------------------------------------------------------
    # status_treino
    # ------------------------------------------------------------------
    def status_treino(self, nome_alma: str) -> Dict[str, Any]:
        nome_alma = nome_alma.upper()
        return self._registro.get(nome_alma, {"status": "nunca_iniciado", "alma": nome_alma})

    # ------------------------------------------------------------------
    # obter_status
    # ------------------------------------------------------------------
    def obter_status(self) -> Dict[str, Any]:
        treinos_ativos = sum(1 for v in self._registro.values() if v.get("status") == "executando")
        return {
            "gpu": self._gpu_disponivel,
            "almas": self.ALMAS,
            "modo": "real" if self._gpu_disponivel else "sem_gpu",
            "treinos_registrados": len(self._registro),
            "treinos_ativos": treinos_ativos,
            "registro": self._registro,
        }

    # ------------------------------------------------------------------
    # verificar_dataset
    # ------------------------------------------------------------------
    def verificar_dataset(self, nome_alma: str) -> Dict[str, Any]:
        nome_alma = nome_alma.upper()
        if nome_alma not in _MAPA_ALMAS:
            return {"existe": False, "erro": "Alma desconhecida"}
        raiz = Path(__file__).parent
        caminho = raiz / _MAPA_ALMAS[nome_alma]["dataset"]
        existe = caminho.exists()
        return {
            "alma": nome_alma,
            "caminho": str(caminho),
            "existe": existe,
            "tamanho_mb": round(caminho.stat().st_size / 1024**2, 2) if existe else 0,
        }

    # ------------------------------------------------------------------
    # parar
    # ------------------------------------------------------------------
    def parar(self) -> None:
        ativos = [n for n, t in self._threads_treino.items() if t.is_alive()]
        if ativos:
            logger.warning("[AVISO] Parado com treinos em execução: %s (não interrompidos)", ativos)
        else:
            logger.info("[OK] OrquestradorArca parado")

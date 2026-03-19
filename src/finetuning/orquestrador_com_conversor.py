# -*- coding: utf-8 -*-
from __future__ import annotations
"""
orquestrador_com_conversor.py
OrquestradorComConversor: treina LoRA via OrquestradorArca e converte
o adapter treinado para GGUF usando llama.cpp convert_lora_to_gguf.py
ou merge + exportação via unsloth.
"""
import logging
import subprocess
import sys
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)
__all__ = ["OrquestradorComConversor"]


class OrquestradorComConversor:
    """Orquestrador com conversão GGUF automática após treino LoRA."""

    def __init__(self, config: Any = None):
        self.config = config
        self._gpu = self._verificar_gpu()
        self._orquestrador_arca = None
        self._carregar_arca()
        self._registro_conversoes: Dict[str, Dict[str, Any]] = {}
        logger.info("[OK] OrquestradorComConversor inicializado (GPU=%s)", self._gpu)

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------
    def _verificar_gpu(self) -> bool:
        try:
            import torch
            return torch.cuda.is_available()
        except Exception:
            return False

    def _carregar_arca(self) -> None:
        try:
            raiz = str(Path(__file__).parent)
            if raiz not in sys.path:
                sys.path.insert(0, raiz)
            from src.core.orquestrador_arca import OrquestradorArca
            self._orquestrador_arca = OrquestradorArca(self.config)
            logger.info("[OK] OrquestradorArca carregado no Conversor")
        except Exception as e:
            logger.warning("[AVISO] OrquestradorArca não disponível no Conversor: %s", e)

    # ------------------------------------------------------------------
    # treinar_ia — chamado pelo Coração
    # ------------------------------------------------------------------
    def treinar_ia(
        self,
        nome_alma: str,
        dataset_path: str = None,
        converter_gguf: bool = False,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Treina LoRA de uma alma. Se converter_gguf=True, converte após treino.
        """
        nome_alma = str(nome_alma).upper()

        if self._orquestrador_arca is None:
            return {
                "status": "erro",
                "alma": nome_alma,
                "erro": "OrquestradorArca não disponível para treino",
            }

        logger.info("[Conversor] treinar_ia(%s, converter=%s)", nome_alma, converter_gguf)
        resultado = self._orquestrador_arca.treinar_ia(
            nome_alma=nome_alma,
            dataset_path=dataset_path,
            **kwargs,
        )

        if converter_gguf and resultado.get("status") == "iniciado":
            resultado["gguf_agendado"] = True
            resultado["mensagem"] = (
                f"Treino iniciado. Conversão GGUF será executada automaticamente após conclusão."
            )

        return resultado

    # ------------------------------------------------------------------
    # treinar — alias genérico
    # ------------------------------------------------------------------
    def treinar(
        self,
        modelo: str = None,
        dataset: str = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Alias de treinar_ia para compatibilidade."""
        return self.treinar_ia(nome_alma=modelo or "", dataset_path=dataset, **kwargs)

    # ------------------------------------------------------------------
    # treinar_e_converter — treina + converte para GGUF
    # ------------------------------------------------------------------
    def treinar_e_converter(
        self,
        nome_alma: str = None,
        modelo: str = None,
        dataset_path: str = None,
        quantizacao: str = "q4_k_m",
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Pipeline completo: treina LoRA e converte o adapter para GGUF.
        A conversão ocorre em thread, após o treino ser detectado como concluído.
        """
        nome = (nome_alma or modelo or "").upper()
        if not nome:
            return {"status": "erro", "erro": "nome_alma ou modelo é obrigatório"}

        resultado = self.treinar_ia(nome_alma=nome, dataset_path=dataset_path, **kwargs)

        if resultado.get("status") not in ("iniciado", "concluido"):
            return resultado

        # Agendar conversão em thread que aguarda o treino terminar
        import threading

        def aguardar_e_converter():
            import time
            max_espera = 72 * 3600  # 72 horas
            intervalo = 60          # checar a cada 60s
            decorrido = 0

            while decorrido < max_espera:
                time.sleep(intervalo)
                decorrido += intervalo

                if self._orquestrador_arca is None:
                    break

                status = self._orquestrador_arca.status_treino(nome)
                estado = status.get("status", "")

                if estado == "concluido":
                    output_dir = status.get("output_dir", "")
                    if output_dir:
                        self._converter_para_gguf(nome, output_dir, quantizacao)
                    break
                elif estado == "erro":
                    logger.error("[Conversor] Treino de %s falhou — conversão cancelada", nome)
                    break

        t = threading.Thread(
            target=aguardar_e_converter,
            name=f"gguf_converter_{nome}",
            daemon=True,
        )
        t.start()

        resultado["gguf"] = "agendado"
        resultado["quantizacao"] = quantizacao
        resultado["mensagem"] = (
            f"Treino + conversão GGUF ({quantizacao}) agendados para {nome}"
        )
        return resultado

    # ------------------------------------------------------------------
    # _converter_para_gguf
    # ------------------------------------------------------------------
    def _converter_para_gguf(
        self,
        nome_alma: str,
        lora_dir: str,
        quantizacao: str = "q4_k_m",
    ) -> Dict[str, Any]:
        """
        Converte adapter LoRA para GGUF.
        Estratégia 1: unsloth.save_pretrained_gguf (se disponível)
        Estratégia 2: llama.cpp convert_lora_to_gguf.py via subprocess
        """
        raiz = Path(__file__).parent
        lora_path = Path(lora_dir) if Path(lora_dir).is_absolute() else raiz / lora_dir
        output_gguf = raiz / "models" / f"{nome_alma.lower()}_{quantizacao}.gguf"
        output_gguf.parent.mkdir(parents=True, exist_ok=True)

        reg = {
            "alma": nome_alma,
            "lora_dir": str(lora_path),
            "output_gguf": str(output_gguf),
            "quantizacao": quantizacao,
            "inicio": datetime.now().isoformat(),
            "status": "iniciando",
        }
        self._registro_conversoes[nome_alma] = reg

        logger.info("[GGUF] Iniciando conversão de %s → %s", lora_path, output_gguf)

        # Estratégia 1: unsloth
        try:
            from unsloth import FastLanguageModel
            logger.info("[GGUF] Tentando via unsloth.save_pretrained_gguf...")
            model, tokenizer = FastLanguageModel.from_pretrained(
                model_name=str(lora_path),
                max_seq_length=2048,
                load_in_4bit=True,
            )
            model.save_pretrained_gguf(
                str(output_gguf.with_suffix("")),
                tokenizer,
                quantization_method=quantizacao,
            )
            reg["status"] = "concluido"
            reg["fim"] = datetime.now().isoformat()
            logger.info("[GGUF] Conversão unsloth concluída: %s", output_gguf)
            return reg
        except Exception as e:
            logger.warning("[GGUF] unsloth falhou: %s — tentando llama.cpp", e)

        # Estratégia 2: llama.cpp convert_lora_to_gguf.py
        llama_cpp_scripts = [
            raiz / "llama.cpp" / "convert_lora_to_gguf.py",
            raiz / "tools" / "llama.cpp" / "convert_lora_to_gguf.py",
            Path("C:/llama.cpp/convert_lora_to_gguf.py"),
        ]
        script_encontrado = next((s for s in llama_cpp_scripts if s.exists()), None)

        if script_encontrado:
            cmd = [
                sys.executable,
                str(script_encontrado),
                "--lora-model", str(lora_path),
                "--output-type", quantizacao,
                "--outfile", str(output_gguf),
            ]
            logger.info("[GGUF] subprocess llama.cpp: %s", " ".join(cmd))
            proc = subprocess.run(
                cmd, cwd=str(raiz), capture_output=True, text=True, encoding="utf-8"
            )
            if proc.returncode == 0:
                reg["status"] = "concluido"
                reg["fim"] = datetime.now().isoformat()
                logger.info("[GGUF] llama.cpp conversão OK: %s", output_gguf)
                return reg
            else:
                logger.error("[GGUF] llama.cpp falhou (rc=%d): %s", proc.returncode, proc.stderr[-1000:])
        else:
            logger.warning("[GGUF] llama.cpp não encontrado em caminhos conhecidos")

        reg["status"] = "erro"
        reg["fim"] = datetime.now().isoformat()
        reg["erro"] = "unsloth e llama.cpp indisponíveis para conversão GGUF"
        logger.error("[GGUF] Conversão de %s falhou — instale unsloth ou llama.cpp", nome_alma)
        return reg

    # ------------------------------------------------------------------
    # status
    # ------------------------------------------------------------------
    def obter_status(self) -> Dict[str, Any]:
        arca_status = {}
        if self._orquestrador_arca:
            arca_status = self._orquestrador_arca.obter_status()
        return {
            "gpu": self._gpu,
            "backend_arca": self._orquestrador_arca is not None,
            "conversoes": self._registro_conversoes,
            "status_treinos": arca_status,
        }

    # ------------------------------------------------------------------
    # parar
    # ------------------------------------------------------------------
    def parar(self) -> None:
        if self._orquestrador_arca:
            self._orquestrador_arca.parar()
        logger.info("[OK] OrquestradorComConversor parado")

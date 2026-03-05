# -*- coding: utf-8 -*-
"""
ARCA CELESTIAL GENESIS - CARREGADOR SISTÍŠMICO (AUTODESCOBERTA)
Local: src/core/carregador_sistemico.py

Função: Escanear diretórios autorizados, importar módulos dinamicamente e registrar no Coração.Melhorias adicionadas:
- CLI para execução independente.
- Filtros custom (override ignores).
- Cache de estado para reloads rápidos.
- Integração com validador_etico.
- Relatório de estatísticas.
"""
from __future__ import annotations
import sys
import os
import logging
import importlib.util
import traceback
import json
from pathlib import Path
from typing import Dict, Any, Optional, List, Set
import argparse

logger = logging.getLogger("CarregadorSistemico")


class CarregadorSistemico:
    DEFAULT_DIRS = [
        Path("src/modules"),
        Path("src/agentes"),
        Path("src/encarnacao_e_interacao"),
        Path("src/memoria"),
    ]

    DEFAULT_IGNORE_PARTS: Set[str] = {
        ".git", "__pycache__", "venv", ".venv", "env", ".env", "node_modules", "tests", "test", "dist", "build"
    }

    def __init__(self, coracao_ref: Any, diretorios_alvo: Optional[List[str]] = None, custom_ignore: Optional[Set[str]] = None):
        self.coracao = coracao_ref
        self.modulos_carregados: Dict[str, Any] = {}
        # allow override via constructor
        if diretorios_alvo:
            self.diretorios_alvo = [Path(p) for p in diretorios_alvo]
        else:
            self.diretorios_alvo = list(self.DEFAULT_DIRS)

        self.ignore_parts = custom_ignore if custom_ignore else self.DEFAULT_IGNORE_PARTS.copy()

        # garante que coracao possui dicionário de módulos
        if not hasattr(self.coracao, "modulos") or not isinstance(getattr(self.coracao, "modulos"), dict):
            try:
                setattr(self.coracao, "modulos", {})
            except Exception:
                logger.warning("CarregadorSistemico: não foi possível inicializar coracao.modulos; registro local apenas.")
        self._registro_coracao = getattr(self.coracao, "modulos", self.modulos_carregados)

        # Cache de estado
        self.cache_file = Path("data/carregador_cache.json")
        self._carregar_cache()

    def _carregar_cache(self):
        """Carrega estado cacheado."""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    cache = json.load(f)
                self.modulos_carregados = {k: v for k, v in cache.get("modulos", {}).items() if k in sys.modules}
                logger.debug("Cache carregado: %d módulos", len(self.modulos_carregados))
            except Exception:
                logger.debug("Falha ao carregar cache; iniciando vazio.")

    def _salvar_cache(self):
        """Salva estado atual."""
        try:
            cache = {"modulos": list(self.modulos_carregados.keys())}
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(cache, f)
        except Exception:
            logger.debug("Falha ao salvar cache.")

    def _validar_modulo_etico(self, caminho_arquivo: Path) -> bool:
        """Integração com validador_etico se disponível."""
        try:
            validador = getattr(self.coracao, "validador_etico", None)
            if validador:
                return validador.validar_modulo(caminho_arquivo)
        except Exception:
            pass
        return True  # assume ok se não disponível

    def escanear_e_conectar(self) -> int:
        """
        Varre os diretórios autorizados e carrega módulos registráveis.Retorna o número de módulos carregados com sucesso.
        """
        logger.info("ðŸ” Iniciando varredura sistêmica em %d setores...", len(self.diretorios_alvo))

        total_carregados = 0
        stats = {"tentados": 0, "carregados": 0, "erros": 0, "ignorados": 0}

        for diretorio in self.diretorios_alvo:
            path_obj = Path(diretorio)
            if not path_obj.exists():
                logger.debug("Diretório alvo não existe, ignorando: %s", str(path_obj))
                continue

            for arquivo in path_obj.rglob("*.py"):
                stats["tentados"] += 1
                # Ignorar arquivos e diretórios óbvios
                if arquivo.name.startswith("__"):
                    stats["ignorados"] += 1
                    continue
                if any(part in arquivo.parts for part in self.ignore_parts):
                    logger.debug("Ignorando (parte ignorada encontrada): %s", arquivo)
                    stats["ignorados"] += 1
                    continue
                if "utils" in arquivo.parts or arquivo.match("**/utils/**"):
                    logger.debug("Ignorando utilitário: %s", arquivo)
                    stats["ignorados"] += 1
                    continue

                # Validação ética
                if not self._validar_modulo_etico(arquivo):
                    logger.warning("Módulo rejeitado por validação ética: %s", arquivo)
                    stats["ignorados"] += 1
                    continue

                ok = self._carregar_modulo(arquivo)
                if ok:
                    stats["carregados"] += 1
                    total_carregados += 1
                else:
                    stats["erros"] += 1

        self._salvar_cache()
        logger.info("ðŸ”— CONEXÍO MASSIVA CONCLUÍDA: %d módulos carregados.", total_carregados)
        logger.info("ðŸ“Š Estatísticas: %s", stats)
        return total_carregados

    def _qualificar_nome_modulo(self, caminho_arquivo: Path) -> str:
        """Constrói nome qualificado."""
        try:
            rel = caminho_arquivo.relative_to(Path.cwd())
        except Exception:
            rel = caminho_arquivo
        parts = list(rel.with_suffix("").parts)
        parts = [p for p in parts if p not in (".", "")]
        nome = "arca.autodiscover." + ".".join(parts)
        nome = nome.replace("-", "_")
        return nome

    def _carregar_modulo(self, caminho_arquivo: Path) -> bool:
        """Importa módulo com segurança."""
        caminho_arquivo = caminho_arquivo.resolve()
        nome_qualificado = self._qualificar_nome_modulo(caminho_arquivo)

        if nome_qualificado in self.modulos_carregados:
            logger.debug("Módulo já carregado (pulando): %s", nome_qualificado)
            try:
                self._registro_coracao[nome_qualificado] = self.modulos_carregados[nome_qualificado]
            except Exception:
                pass
            return False

        try:
            spec = importlib.util.spec_from_file_location(nome_qualificado, str(caminho_arquivo))
            if spec is None or spec.loader is None:
                logger.error("Spec inválido para %s (ignorado)", caminho_arquivo)
                return False

            module = importlib.util.module_from_spec(spec)
            prior = sys.modules.get(nome_qualificado)
            sys.modules[nome_qualificado] = module
            try:
                spec.loader.exec_module(module)  # type: ignore
            except Exception as e:
                logger.error("Falha ao executar módulo %s: %s\n%s", caminho_arquivo, e, traceback.format_exc())
                if prior is None:
                    try:
                        del sys.modules[nome_qualificado]
                    except Exception:
                        pass
                return False

            self.modulos_carregados[nome_qualificado] = module
            try:
                self._registro_coracao[nome_qualificado] = module
            except Exception:
                logger.debug("Não foi possível registrar módulo no coracao.modulos; mantendo registro local.")

            logger.info("   -> Módulo carregado: %s (%s)", nome_qualificado, caminho_arquivo)
            return True

        except Exception as e:
            logger.error("âŒ Erro ao carregar módulo %s: %s\n%s", caminho_arquivo, e, traceback.format_exc())
            try:
                if nome_qualificado in sys.modules:
                    del sys.modules[nome_qualificado]
            except Exception:
                pass
            return False

    def listar_modulos_carregados(self) -> List[str]:
        """Retorna lista de nomes qualificados."""
        return list(self.modulos_carregados.keys())

    def obter_modulo(self, nome_qualificado: str) -> Optional[Any]:
        """Retorna objeto do módulo."""
        return self.modulos_carregados.get(nome_qualificado)

    def descarregar_modulo(self, nome_qualificado: str) -> bool:
        """Remove módulo do registro."""
        try:
            if nome_qualificado in self.modulos_carregados:
                del self.modulos_carregados[nome_qualificado]
            if nome_qualificado in self._registro_coracao:
                try:
                    del self._registro_coracao[nome_qualificado]
                except Exception:
                    pass
            if nome_qualificado in sys.modules:
                try:
                    del sys.modules[nome_qualificado]
                except Exception:
                    pass
            self._salvar_cache()
            logger.info("Módulo descarregado: %s", nome_qualificado)
            return True
        except Exception as e:
            logger.error("Falha ao descarregar módulo %s: %s", nome_qualificado, e, exc_info=True)
            return False

    def relatorio_carregamento(self) -> Dict[str, Any]:
        """Gera relatório de carregamento."""
        total = len(self.modulos_carregados)
        return {
            "total_carregados": total,
            "modulos": list(self.modulos_carregados.keys()),
            "diretorios_varridos": [str(d) for d in self.diretorios_alvo]
        }


def main():
    """CLI para execução independente."""
    parser = argparse.ArgumentParser(description="Carregador Sistêmico - Autodescoberta de Módulos")
    parser.add_argument("--dirs", nargs="*", help="Diretórios para varrer (padrão: src/modules, src/agentes, etc.)")
    parser.add_argument("--ignore", nargs="*", help="Partes adicionais para ignorar")
    parser.add_argument("--no-cache", action="store_true", help="Não usar cache")
    parser.add_argument("--report", action="store_true", help="Mostrar relatório final")

    args = parser.parse_args()

    # Simular coracao para CLI
    class MockCoracao:
        def __init__(self):
            self.modulos = {}

    coracao = MockCoracao()
    ignore_custom = set(args.ignore) if args.ignore else None
    carregador = CarregadorSistemico(coracao, args.dirs, ignore_custom)
    if args.no_cache:
        carregador.cache_file = None

    count = carregador.scan_and_connect()
    print(f"Módulos carregados: {count}")

    if args.report:
        report = carregador.relatorio_carregamento()
        print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()



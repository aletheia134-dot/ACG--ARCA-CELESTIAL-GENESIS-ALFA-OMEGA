#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime
import logging
import py_compile
import re
import shutil
import sys
import queue
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger("inicializador_sistema")
logging.basicConfig(level=logging.INFO)

SRC = Path("src")

def remove_md_blocks(text: str) -> (str, bool):
    changed = False
    pattern = re.compile(r'^[ \t]*```.*\n.*?^[ \t]*```.*\n', flags=re.M | re.S)
    new_text, n = pattern.subn('', text)
    if n > 0:
        changed = True
        text = new_text
    new_text2, n2 = re.subn(r'^[ \t]*```.*\n', '', text, flags=re.M)
    if n2 > 0:
        changed = True
        text = new_text2
    return text, changed

def move_future_imports(lines):
    future_lines = []
    new_lines = []
    for ln in lines:
        if re.match(r'^\s*from\s+__future__\s+import\s+', ln):
            future_lines.append(ln.rstrip('\n'))
        else:
            new_lines.append(ln)
    if not future_lines:
        return lines, False
    idx = 0
    n = len(new_lines)
    if idx < n and new_lines[idx].startswith('#!'):
        idx += 1
    if idx < n and re.match(r'^\s*#.*coding[:=]\s*[-\w]+', new_lines[idx]):
        idx += 1
    if idx < n and re.match(r'^\s*(?:r|u|ur)?("""|\'\'\')', new_lines[idx], flags=re.I):
        quote = re.match(r'^\s*(?:r|u|ur)?("""|\'\'\')', new_lines[idx], flags=re.I).group(1)
        idx += 1
        while idx < n and quote not in new_lines[idx]:
            idx += 1
        if idx < n:
            idx += 1
    insertion = [ln + "\n" for ln in future_lines]
    new = new_lines[:idx] + insertion + new_lines[idx:]
    return new, True

def process_file_remove_md(p: Path, timestamp: str, backups: list, modified: list):
    text = p.read_text(encoding="utf-8", errors="replace")
    new_text, removed = remove_md_blocks(text)
    changed = removed
    txt_before = new_text
    new_text = re.sub(
        r'(from\s+src\.memoria\.dispositivo_ai_to_ai\s+import\s+DispositivoAItoAI)\s+(_AI2AI_OK\s*=)',
        r'\1\n\2',
        new_text,
    )
    if new_text != txt_before:
        changed = True
    if 'from __future__ import' in new_text:
        lines = new_text.splitlines(keepends=True)
        new_lines, moved = move_future_imports(lines)
        if moved:
            new_text = ''.join(new_lines)
            changed = True
    if changed:
        bak = p.with_name(p.name + f".bak.{timestamp}")
        shutil.copy2(p, bak)
        backups.append((p, bak))
        p.write_text(new_text, encoding="utf-8")
        modified.append(str(p))

def remove_markdown_blocks_main(dry_run: bool = False) -> int:
    if not SRC.exists():
        print("ERRO: diretÃƒÂ³rio src/ nÃƒÂ£o encontrado.Rode na raiz do projeto.")
        return 1
    timestamp = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    backups = []
    modified = []
    py_files = list(SRC.rglob("*.py"))
    if not py_files:
        print("Nenhum arquivo.py encontrado em src/. Nada a fazer.")
        return 0
    for f in py_files:
        try:
            if dry_run:
                text = f.read_text(encoding="utf-8", errors="replace")
                _, removed = remove_md_blocks(text)
                if removed:
                    print("SUPOSTA ALTERAÃƒâ€¡ÃƒÆ’O:", f)
                continue
            process_file_remove_md(f, timestamp, backups, modified)
        except Exception as e:
            print("Erro processando", f, ":", e)
    if not modified:
        print("Nenhuma alteraÃƒÂ§ÃƒÂ£o necessÃƒÂ¡ria (nenhum bloco Markdown encontrado).")
        return 0
    print("Arquivos alterados (backups criados):")
    for m in modified:
        print(" -", m)
    print("\nTestando compilaÃƒÂ§ÃƒÂ£o de todos os.py em src/ ...")
    failed = False
    errors = []
    for f in py_files:
        try:
            py_compile.compile(str(f), doraise=True)
        except Exception as e:
            failed = True
            errors.append((f, e))
    if failed:
        print("\nCOMPILAÃƒâ€¡ÃƒÆ’O FALHOU.Restaurando backups...")
        for orig, bak in backups:
            try:
                orig.write_bytes(bak.read_bytes())
                print("Restaurado:", orig)
            except Exception as e:
                print("Falha ao restaurar", orig, ":", e)
        print("\nErros de compilaÃƒÂ§ÃƒÂ£o:")
        for f, e in errors:
            print(" -", f, ":", e)
        print("\nArquivos restaurados.Abra os arquivos listados e remova manualmente os blocos Markdown problemÃƒÂ¡ticos.")
        return 1
    print("\nCompilaÃƒÂ§ÃƒÂ£o OK apÃƒÂ³s remoÃƒÂ§ÃƒÂ£o de bloc Markdown.")
    return 0

try:
    from src.core.coracao_orquestrador import CoracaoOrquestrador as Coracao
    from src.memoria.sistema_memoria import SistemaMemoriaHibrido
    from src.core.cerebro_familia import CerebroFamilia
    from src.core.dispositivo_ai_to_ai import DispositivoAItoAI
    from src.memoria.construtor_dataset import ConstrutorDataset
    from src.sentidos.validador_emocoes_real import ValidadorEmocoesReal
    from src.sentidos.gerenciador_segredos_real import GerenciadorSegredosReal
    from src.core.base_dados_arca import BaseDadosArca, obter_base_dados_arca
    from src.sentidos.sentidos_humanos import SistemaVozReal, SistemaAudicaoReal
    SISTEMA_ARCA_DISPONIVEL = True
    logger.info("Componentes principais do sistema Arca importados.")
except Exception as e:
    raise RuntimeError(f"Componentes principais obrigatÃƒÂ³rios falharam: {e}")

try:
    from src.consulado.consulado_soberano import ConsuladoSoberano
    CONSULADO_DISPONIVEL = True
except Exception:
    raise RuntimeError("ConsuladoSoberano obrigatÃƒÂ³rio nÃƒÂ£o disponÃƒÂ­vel.")

try:
    from src.sentidos.gerador_almas import GeradorDeAlmas
    GERADOR_DE_ALMAS_DISPONIVEL = True
except Exception:
    raise RuntimeError("GeradorDeAlmas obrigatÃƒÂ³rio nÃƒÂ£o disponÃƒÂ­vel.")

try:
    from src.core.ciclo_de_vida import CicloDeVida
    CICLO_DE_VIDA_DISPONIVEL = True
except Exception:
    raise RuntimeError("CicloDeVida obrigatÃƒÂ³rio nÃƒÂ£o disponÃƒÂ­vel.")

get_config = None
try:
    from src.config.config import get_config_moderna as get_config
    CONFIG_DISPONIVEL = True
except Exception:
    raise RuntimeError("get_config obrigatÃƒÂ³rio nÃƒÂ£o encontrado.")

def _obter_config() -> Dict[str, Any]:
    if CONFIG_DISPONIVEL and callable(get_config):
        try:
            cfg = get_config()
            if isinstance(cfg, dict):
                return cfg
            if hasattr(cfg, "get") and hasattr(cfg.get, "__code__"):
                return cfg
            return {}
        except Exception:
            raise RuntimeError("Erro ao obter configuraÃƒÂ§ÃƒÂ£o via get_config().")
    raise RuntimeError("ConfiguraÃƒÂ§ÃƒÂ£o obrigatÃƒÂ³ria nÃƒÂ£o obtida.")

def inicializar_sistema_completo() -> Dict[str, Any]:
    logger.info("Ã°Å¸Å¡â‚¬ Iniciando inicializaÃƒÂ§ÃƒÂ£o do sistema completo...")
    config = _obter_config()
    if not isinstance(config, dict):
        try:
            config = dict(config)
        except Exception:
            config = {}
    config.setdefault("MODELOS_DIR", "./infraestrutura/LLM_Models")
    config.setdefault("PATHS", {})
    config.setdefault("AIS", [])
    ui_queue: "queue.Queue" = queue.Queue()
    llm_engine = None
    try:
        from src.core.parallel_llm_engine import ParallelLLMEngine
        llm_engine = ParallelLLMEngine(config)
        if hasattr(llm_engine, "carregar_modelos"):
            success = llm_engine.carregar_modelos()
            if not success:
                raise RuntimeError("Falha ao carregar modelos LLM.")
        logger.info(" -> ParallelLLMEngine inicializado.")
    except Exception:
        raise RuntimeError(f"ParallelLLMEngine obrigatÃƒÂ³rio falhou: {e}")
    
    gerenciador_memoria = SistemaMemoriaHibrido(config=config)
    logger.info(" -> Sistema de MemÃƒÂ³ria Hibrida inicializado.")
    
    cerebro = CerebroFamilia(memoria=gerenciador_memoria, config=config, llm_engine=llm_engine)
    logger.info(" -> CÃƒÂ©rebro FamÃƒÂ­lia inicializado.")
    
    dispositivo_ai_ai = DispositivoAItoAI(config=config)
    logger.info(" -> Dispositivo AIÃ¢â€ â€AI inicializado.")
    
    construtor_dataset = ConstrutorDataset(memoria=gerenciador_memoria, config=config)
    logger.info(" -> Construtor de Dataset inicializado.")
    
    validador_etico = ValidadorEmocoesReal(config_manager=config)
    logger.info(" -> Validador Ãƒâ€°tico inicializado.")
    
    gerenciador_secrets = GerenciadorSegredosReal()
    logger.info(" -> Gerenciador de Segredos inicializado.")
    
    try:
        base_path = Path(config.get("PATHS", {}).get("BASE_DADOS_PATH", "./data/base_dados.json"))
        fallback_path = Path(config.get("PATHS", {}).get("BASE_DADOS_FALLBACK_PATH", "./data/base_dados_fallback.json"))
        base_dados_arca = obter_base_dados_arca(base_path, fallback_path, config)
        logger.info(" -> Base de Dados Arca inicializada.")
    except Exception:
        raise RuntimeError(f"Base de Dados Arca obrigatÃƒÂ³ria falhou: {e}")
    
    sistema_voz = SistemaVozReal(config=config)
    sistema_audicao = SistemaAudicaoReal(config=config)
    logger.info(" -> Sentidos Humanos inicializados.")
    
    consulado_soberano = ConsuladoSoberano(
        config=config,
        gerenciador_memoria=gerenciador_memoria,
        cerebro_ref=cerebro,
    )
    logger.info(" -> Consulado Soberano inicializado.")
    
    gerador_almas = GeradorDeAlmas(
        gerenciador_memoria_ref=gerenciador_memoria,
        cerebro_ref=cerebro,
        llm_engine_ref=llm_engine,
    )
    logger.info(" -> Gerador de Almas inicializado.")
    
    ciclos_de_vida: Dict[str, Any] = {}
    nomes_almas_csv = config.get("ALMAS", {}).get("LISTA_ALMAS_VOTANTES_CSV", "eva,lumina,nyra,yuna,kaiya,wellington")
    nomes_almas_lista = [a.strip() for a in nomes_almas_csv.split(",") if a.strip()]
    for nome in nomes_almas_lista:
        ciclo = CicloDeVida(
            nome=nome,
            config_instance=config,
            gerenciador_memoria_ref=gerenciador_memoria,
            cerebro_ref=cerebro,
            llm_engine_ref=llm_engine,
            sistema_voz_global_ref=sistema_voz,
            validador_etico_ref=validador_etico,
            ui_queue_ref=ui_queue,
        )
        ciclos_de_vida[nome] = ciclo
        logger.info(" -> Ciclo de Vida criado para %s", nome)
    
    try:
        from src.consulado.analisador_intencao import AnalisadorIntencao
        analisador_intencao = AnalisadorIntencao(config_instance=config)
        ANALISADOR_INTENCAO_DISPONIVEL = True
        logger.info(" -> Analisador de IntenÃƒÂ§ÃƒÂµes inicializado.")
    except Exception:
        raise RuntimeError(f"Analisador de IntenÃƒÂ§ÃƒÂµes obrigatÃƒÂ³rio falhou: {e}")
    
    try:
        from src.encarnacao_e_interacao.encarnacao_api import EncarnacaoAPI
        coracao_stub = {"almas_vivas": {}, "rodando": True, "command_queue": ui_queue}
        api_encarnacao = EncarnacaoAPI(coracao_ref=coracao_stub)
        api_encarnacao.start()
        API_ENCARNACAO_DISPONIVEL = True
        logger.info(" -> API de Encarnacao inicializada.")
    except Exception:
        raise RuntimeError(f"API de Encarnacao obrigatÃƒÂ³ria falhou: {e}")
    
    logger.info("InicializaÃƒÂ§ÃƒÂ£o concluÃƒÂ­da. Retornando instÃƒÂ¢ncias.")
    return {
        "config": config,
        "llm_engine": llm_engine,
        "ui_queue": ui_queue,
        "gerenciador_memoria": gerenciador_memoria,
        "cerebro": cerebro,
        "dispositivo_ai_ai": dispositivo_ai_ai,
        "construtor_dataset": construtor_dataset,
        "validador_etico": validador_etico,
        "gerenciador_secrets": gerenciador_secrets,
        "base_dados_arca": base_dados_arca,
        "sistema_voz": sistema_voz,
        "sistema_audicao": sistema_audicao,
        "consulado_soberano": consulado_soberano,
        "gerador_almas": gerador_almas,
        "ciclos_de_vida": ciclos_de_vida,
        "analisador_intencao": analisador_intencao,
        "api_encarnacao": api_encarnacao,
        "flags": {
            "SISTEMA_ARCA_DISPONIVEL": SISTEMA_ARCA_DISPONIVEL,
            "CONFIG_DISPONIVEL": CONFIG_DISPONIVEL,
            "CONSULADO_DISPONIVEL": CONSULADO_DISPONIVEL,
            "GERADOR_DE_ALMAS_DISPONIVEL": GERADOR_DE_ALMAS_DISPONIVEL,
            "CICLO_DE_VIDA_DISPONIVEL": CICLO_DE_VIDA_DISPONIVEL,
            "ANALISADOR_INTENCAO_DISPONIVEL": ANALISADOR_INTENCAO_DISPONIVEL,
            "API_ENCARNACAO_DISPONIVEL": API_ENCARNACAO_DISPONIVEL,
        },
    }

def main():
    ap = argparse.ArgumentParser(description="inicializador_sistema: remove-md + inicializador")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p_rm = sub.add_parser("remove-md", help="Remover blocos Markdown em src/")
    p_rm.add_argument("--dry-run", action="store_true", help="Listar arquivos que seriam alterados")
    p_init = sub.add_parser("init", help="Executar inicializar_sistema_completo()")
    p_show = sub.add_parser("show", help="Imprimir estado/flags para inspeÃƒÂ§ÃƒÂ£o")
    args = ap.parse_args()
    if args.cmd == "remove-md":
        return_code = remove_markdown_blocks_main(dry_run=args.dry_run)
        sys.exit(return_code)
    elif args.cmd == "init":
        inst = inicializar_sistema_completo()
        print("InicializaÃƒÂ§ÃƒÂ£o retornou chaves:", ", ".join(sorted(inst.keys())))
        sys.exit(0)
    elif args.cmd == "show":
        print("Arquivo inicializador_sistema.py carregado.SRC=", SRC)
        print("Flags:", {
            "SISTEMA_ARCA_DISPONIVEL": SISTEMA_ARCA_DISPONIVEL,
            "CONFIG_DISPONIVEL": CONFIG_DISPONIVEL,
            "CONSULADO_DISPONIVEL": CONSULADO_DISPONIVEL,
            "GERADOR_DE_ALMAS_DISPONIVEL": GERADOR_DE_ALMAS_DISPONIVEL,
            "CICLO_DE_VIDA_DISPONIVEL": CICLO_DE_VIDA_DISPONIVEL,
            "ANALISADOR_INTENCAO_DISPONIVEL": ANALISADOR_INTENCAO_DISPONIVEL,
            "API_ENCARNACAO_DISPONIVEL": API_ENCARNACAO_DISPONIVEL,
        })
        sys.exit(0)

if __name__ == "__main__":
    main()


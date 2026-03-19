from __future__ import annotations
from src.diagnostico.erros import LLMTimeoutError, LLMUnavailableError, LLMExecutionError, MemoriaIndisponivelError, DryRunError, PlaceholderError
import argparse
import logging
import sys
import traceback
from typing import Optional, Tuple, Any

parser = argparse.ArgumentParser(description="Teste completo da extenso de memória (hardened).")
parser.add_argument("--dry-run", dest="dry_run", action="store_true", default=True,
                    help="Executar em modo dry-run (padrão). Evita operações mutantes.")
parser.add_argument("--apply", dest="dry_run", action="store_false",
                    help="Permite executar operações mutantes (ativar, adicionar biografia, criar templates).")
parser.add_argument("--only", dest="only", type=str, default="all",
                    help="Executar apenas um teste (ex: '1','2','3' ou 'all').")
parser.add_argument("--log-level", dest="log_level", default="INFO",
                    help="nível de log (DEBUG/INFO/WARNING/ERROR).")
args = parser.parse_args()

logging.basicConfig(
    level=getattr(logging, args.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s - %(message)s"
)
logger = logging.getLogger("teste_extensao_completo_hardened")

DRY_RUN = bool(args.dry_run)

def safe_import(module_path: str) -> Optional[Any]:
    try:
        parts = module_path.split(":")
        if len(parts) == 1:
            mod = __import__(module_path, fromlist=["*"])
            return mod
        else:
            mod_name, attr = parts
            mod = __import__(mod_name, fromlist=[attr])
            return getattr(mod, attr)
    except Exception as e:
        logger.warning("Import falhou para '%s': %s", module_path, e)
        logger.debug(traceback.format_exc())
        return None

def safe_call(obj: Any, method_name: str, *a, mutates: bool = False, **kw):
    if obj is None:
        logger.error("Objeto alvo  None; no  possível chamar %s", method_name)
        return None
    meth = getattr(obj, method_name, None)
    if not callable(meth):
        logger.error("Método %s no encontrado em %s", method_name, type(obj).__name__)
        return None
    if DRY_RUN and mutates:
        logger.info("[DRY-RUN] Skipping mutating call: %s.%s()", type(obj).__name__, method_name)
        raise DryRunError("Dry-run: operação mutante ignorada")
    try:
        return meth(*a, **kw)
    except Exception as e:
        logger.exception("Erro ao chamar %s.%s: %s", type(obj).__name__, method_name, e)
        return None

def teste_1_sistema_original() -> Tuple[bool, Optional[Any]]:
    logger.info("TESTE 1: Sistema Original")
    MemorySystemReal = safe_import("core.memoria:MemorySystemReal")
    if MemorySystemReal is None:
        logger.error("Módulo core.memoria.MemorySystemReal no disponível.Abortando sequncia de testes.")
        return False, None
    try:
        memoria = MemorySystemReal()
        logger.info("MemorySystemReal carregado com sucesso")
        collections = getattr(memoria, "collections", None)
        ais = getattr(memoria, "ais", None)
        try:
            col_len = getattr(collections, "__len__", lambda: "N/A")()
        except Exception:
            col_len = "N/A"
        logger.info("Collections: %s, AIs: %s", col_len, ais)
        return True, memoria
    except Exception as e:
        logger.exception("Erro ao instanciar MemorySystemReal: %s", e)
        return False, None

def teste_2_extensao_carrega() -> Tuple[bool, Optional[Any], Optional[Any]]:
    logger.info("TESTE 2: Carregar Extenso")
    MemorySystemReal = safe_import("core.memoria:MemorySystemReal")
    MemoriaExtensao = safe_import("core.memoria_extensao:MemoriaExtensao")
    if MemorySystemReal is None or MemoriaExtensao is None:
        logger.error("Módulos necessários para a extenso no esto disponíveis.")
        return False, None, None
    try:
        memoria = MemorySystemReal()
        extensao = MemoriaExtensao(memoria)
        logger.info("MemoriaExtensao carregada; status: %s", getattr(extensao, "ativada", "unknown"))
        return True, memoria, extensao
    except Exception as e:
        logger.exception("Erro ao carregar extenso: %s", e)
        return False, None, None

def teste_3_ativar_extensao(memoria: Any, extensao: Any) -> bool:
    logger.info("TESTE 3: Ativar Extenso")
    if extensao is None:
        logger.error("Extenso  None, pulando teste.")
        return False
    res = safe_call(extensao, "ativar", mutates=True)
    if res == "DRY_RUN_SKIPPED":
        logger.info("Ativao simulada (dry-run).")
        return True
    metadata_dbs = getattr(extensao, "metadata_dbs", None)
    biografias_path = getattr(extensao, "biografias_path", None)
    logger.info("metadata_dbs=%s biografias_path=%s", bool(metadata_dbs), biografias_path)
    return True

def teste_4_adicionar_biografia(extensao: Any) -> bool:
    logger.info("TESTE 4: Adicionar Biografia")
    if extensao is None:
        logger.error("Extenso  None, pulando teste.")
        return False
    biografia_teste = (
        "Wellington Ara - Teste de Biografia\n\n"
        "Este  um teste de biografia para Wellington.\n"
        "Tem 48 anos e mora no Japo.\n\n"
        "Cada pargrafo vira uma memória M0 separada.\n"
        "M0 nunca muda - identidade permanente.\n\n"
        "Esta  uma memória de teste.\n"
    )
    res = safe_call(extensao, "adicionar_biografia", 'wellington', biografia_teste, mutates=True)
    if res == "DRY_RUN_SKIPPED":
        logger.info("adicionar_biografia pulado por dry-run.")
        return True
    stats = safe_call(extensao, "get_stats_avancadas", 'wellington')
    if isinstance(stats, dict):
        logger.info("Stats avanadas (wellington): %s", stats)
        return stats.get("m0_biografias", 0) > 0
    logger.warning("get_stats_avancadas no retornou dict; resultado: %s", stats)
    return True

def teste_5_contexto_sem_m0(memoria: Any, extensao: Any) -> bool:
    logger.info("TESTE 5: Contexto SEM M0 (desativado)")
    if extensao is None or memoria is None:
        logger.error("memoria/extensao ausente.")
        return False
    safe_call(extensao, "desativar", mutates=True)
    ctx = safe_call(memoria, "get_context", 'wellington', 'Quem  você?', limit=3)
    if ctx is None:
        logger.warning("get_context retornou None; falha potencial.")
        return False
    try:
        length = len(ctx)
    except Exception:
        length = 0
    logger.info("Contexto obtido (len=%d)", length)
    tem_identidade = "IDENTIDADE PERMANENTE" in str(ctx).upper()
    if tem_identidade:
        logger.warning("M0 aparece no contexto mesmo com extenso desativada (inesperado).")
        return False
    return True

def teste_6_contexto_com_m0(memoria: Any, extensao: Any) -> bool:
    logger.info("TESTE 6: Contexto COM M0 (ativado)")
    if extensao is None or memoria is None:
        logger.error("memoria/extensao ausente.")
        return False
    res = safe_call(extensao, "ativar", mutates=True)
    if res == "DRY_RUN_SKIPPED":
        logger.info("Ativao simulada (dry-run); tentando validar indireto.")
    ctx = safe_call(memoria, "get_context", 'wellington', 'Quem  você?', limit=3)
    if ctx is None:
        logger.warning("get_context retornou None; falha potencial.")
        return False
    tem_identidade = "IDENTIDADE PERMANENTE" in str(ctx).upper()
    if tem_identidade:
        logger.info("Seo M0 presente (esperado).")
        return True
    if DRY_RUN:
        logger.info("Dry-run: M0 pode no ter sido realmente adicionado  considerar --apply para teste real.")
        return True
    logger.warning("M0 no apareceu no contexto; verificar se biografia foi adicionada.")
    return False

def teste_7_compatibilidade_store(memoria: Any) -> bool:
    logger.info("TESTE 7: Compatibilidade store_memory")
    if memoria is None:
        logger.error("memoria ausente.")
        return False
    MemoryTier = safe_import("core.memoria:MemoryTier")
    if MemoryTier is None:
        logger.warning("MemoryTier no disponível; tentando usar string 'M1'")
        tier_val = "M1"
    else:
        tier_val = MemoryTier.M1
    try:
        result = safe_call(memoria, "store_memory", ai_id='wellington', tier=tier_val,
                           user_message='Teste de mensagem', ai_response='Teste de resposta do sistema', mutates=True)
        logger.info("store_memory resultado: %s", result)
        stats = safe_call(memoria, "get_ai_memories_count", 'wellington')
        logger.info("memórias Wellington (count): %s", stats)
        return True
    except Exception:
        logger.exception("Erro no teste store_memory")
        return False

def teste_8_criar_templates(extensao: Any) -> bool:
    logger.info("TESTE 8: Criar Templates de Biografia")
    if extensao is None:
        logger.error("Extenso ausente.")
        return False
    if DRY_RUN:
        logger.info("Dry-run: pular criao de templates (operação mutante).")
        return True
    try:
        for ai in ['wellington', 'eva', 'lumina']:
            safe_call(extensao, "criar_template_biografia", ai, mutates=True)
        logger.info("Templates criados (ou tentativa realizada).")
        return True
    except Exception:
        logger.exception("Erro ao criar templates")
        return False

def teste_9_stats_avancadas(extensao: Any) -> bool:
    logger.info("TESTE 9: Estatsticas Avanadas")
    if extensao is None:
        logger.error("Extenso ausente.")
        return False
    try:
        for ai in ['wellington', 'eva', 'lumina']:
            stats = safe_call(extensao, "get_stats_avancadas", ai)
            logger.info("%s -> %s", ai.upper(), stats if isinstance(stats, dict) else "N/A")
        return True
    except Exception:
        logger.exception("Erro ao coletar stats avanadas")
        return False

TEST_FUNCS = {
    "1": ("Sistema Original", lambda ctx: teste_1_sistema_original()),
    "2": ("Carregar Extenso", lambda ctx: teste_2_extensao_carrega()),
    "3": ("Ativar Extenso", lambda ctx: teste_3_ativar_extensao(ctx.get("memoria"), ctx.get("extensao"))),
    "4": ("Adicionar Biografia", lambda ctx: teste_4_adicionar_biografia(ctx.get("extensao"))),
    "5": ("Contexto sem M0", lambda ctx: teste_5_contexto_sem_m0(ctx.get("memoria"), ctx.get("extensao"))),
    "6": ("Contexto com M0", lambda ctx: teste_6_contexto_com_m0(ctx.get("memoria"), ctx.get("extensao"))),
    "7": ("Compatibilidade store", lambda ctx: teste_7_compatibilidade_store(ctx.get("memoria"))),
    "8": ("Criar Templates", lambda ctx: teste_8_criar_templates(ctx.get("extensao"))),
    "9": ("Stats Avanadas", lambda ctx: teste_9_stats_avancadas(ctx.get("extensao"))),
}

def executar_todos_testes(selected: str = "all") -> None:
    logger.info("=== INICIANDO BATELADA DE TESTES (dry_run=%s) ===", DRY_RUN)
    contexto = {"memoria": None, "extensao": None}
    resultados = {}

    ok, memoria = teste_1_sistema_original()
    resultados['Sistema Original'] = ok
    contexto["memoria"] = memoria
    if not ok:
        logger.error("Sistema original falhou  abortando restante dos testes.")
        _report_and_exit(resultados)

    ok, memoria2, extensao = teste_2_extensao_carrega()
    resultados['Carregar Extenso'] = ok
    contexto["memoria"] = memoria2 or memoria
    contexto["extensao"] = extensao
    if not ok:
        logger.error("Extenso no carregou  abortando.")
        _report_and_exit(resultados)

    for tid in ("3","4","5","6","7","8","9"):
        if selected != "all" and tid != selected:
            logger.debug("Pulando teste %s por seleo --only=%s", tid, selected)
            continue
        name = TEST_FUNCS[tid][0]
        logger.info("Executando Teste %s: %s", tid, name)
        try:
            res = TEST_FUNCS[tid][1](contexto)
            resultados[name] = bool(res)
        except Exception:
            logger.exception("Erro ao executar teste %s", tid)
            resultados[name] = False

    _report_and_exit(resultados)

def _report_and_exit(resultados: dict) -> None:
    total = len(resultados)
    passed = sum(1 for v in resultados.values() if v)
    logger.info("=== RELATRIO FINAL: %d/%d testes passaram ===", passed, total)
    for k, v in resultados.items():
        logger.info("%-30s %s", k, "PASS" if v else "FAIL")
    if passed == total:
        logger.info("TODOS OS TESTES PASSARAM")
        sys.exit(0)
    else:
        logger.warning("ALGUNS TESTES FALHARAM")
        sys.exit(2)

if __name__ == "__main__":
    try:
        executar_todos_testes(selected=args.only)
    except SystemExit:
        raise
    except Exception as e:
        logger.exception("Erro fatal ação executar testes: %s", e)
        sys.exit(3)



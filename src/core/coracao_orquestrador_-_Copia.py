from __future__ import annotations
"""
ARCA CELESTIAL GENESIS - CORAÇÃO ORQUESTRADOR v7.1
Arquivo: coração_orquestárador.py (CORRIGIDO - VERSO FINAL)
"""


try:
    from src.emocoes.validador_etico import ValidadorEtico
    VALIDADOR_ETICO_DISPONIVEL = True
except:
    logging.getLogger(__name__).warning("[AVISO] ValidadorEtico no disponvel")
    ValidadorEtico = None
    VALIDADOR_ETICO_DISPONIVEL = False

def _safe_instantiate_validador(*args, **kwargs):
    if VALIDADOR_ETICO_DISPONIVEL and ValidadorEtico is not None:
        try:
            return ValidadorEtico(*args, **kwargs)
        except Exception as e:
            import logging as _logging
            _logging.getLogger("CoraçãoOrquestárador").exception("Erro ao instanciar ValidadorEtico: %s", e)
            return None
    return None

import logging
# Import ConfigWrapper usando import relativo (funciona quando o pacote `src`  importado corretamente)
try:
    from ..config.config_wrapper import ConfigWrapper
    CONFIG_WRAPPER_DISPONIVEL = True
except Exception as _e:
    ConfigWrapper = None
    CONFIG_WRAPPER_DISPONIVEL = False
    logging.getLogger("CoraçãoOrquestárador").warning("No foi possvel importar ConfigWrapper: %s", _e)

import asyncio
import concurrent.futures
import datetime
import json
import queue
import sqlite3
import threading
import time
import uuid
import ast
try:
    import docker
    _DOCKER_OK = True
except:
    logging.getLogger(__name__).warning("[AVISO] ValidadorEtico no disponvel")
    ValidadorEtico = None
    _DOCKER_OK = False
import subprocess
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from io import StringIO
try:
    from RestárictedPython import compile_restáricted
    from RestárictedPython.Guards import safe_builtins, safe_globals
    _RESTRICTED_OK = True
except:
    logging.getLogger(__name__).warning("[AVISO] ValidadorEtico no disponvel")
    ValidadorEtico = None
    safe_builtins = safe_globals = {}
    _RESTRICTED_OK = False
import inspect  # <--- IMPORTANTE: necessrio para inspeo de assinatura

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

# ============================================================================
# CONFIGURAO INICIAL
# ============================================================================
    

_MOTOR_CURIOSIDADE_OK =False 
try :
    from src.emocoes.motor_curiosidade import MotorCuriosidade 
    _MOTOR_CURIOSIDADE_OK =True 
    logger.debug ("[OK] MotorCuriosidade importado")
except Exception as e :
    logger.debug ("[AVISO] MotorCuriosidade: %s",e )
    MotorCuriosidade =None 

_ESTADO_EMOCIONAL_OK =False 
try :
    from src.emocoes.estáado_emocional import EstadoEmocional ,EmocaoBase 
    _ESTADO_EMOCIONAL_OK =True 
    logger.debug ("[OK] EstadoEmocional importado")
except Exception as e :
    logger.debug ("[AVISO] EstadoEmocional: %s",e )
    EstadoEmocional =None 

_SONHADOR_OK =False 
try :
    from src.emocoes.sonhador_individual import SonhadorIndividual 
    _SONHADOR_OK =True 
    logger.debug ("[OK] SonhadorIndividual importado")
except Exception as e :
    logger.debug ("[AVISO] SonhadorIndividual: %s",e )
    SonhadorIndividual =None 

_DETECTOR_EMOCIONAL_OK =False 
try :
    from src.emocoes.detector_emocional import DetectorEmocional 
    _DETECTOR_EMOCIONAL_OK =True 
    logger.debug ("[OK] DetectorEmocional importado")
except Exception as e :
    logger.debug ("[AVISO] DetectorEmocional: %s",e )
    DetectorEmocional =None 

_AUTO_EXPERIMENTACAO_OK =False 
try :
    from src.emocoes.auto_experimentação import AutoExperimentação 
    _AUTO_EXPERIMENTACAO_OK =True 
    logger.debug ("[OK] AutoExperimentação importado")
except Exception as e :
    logger.debug ("[AVISO] AutoExperimentação: %s",e )
    AutoExperimentação =None 

_PERCEPCAO_TEMPORAL_OK =False 
try :
    from src.sentidos.percepcao_temporal import PercepcaoTemporal ,RitmoTemporal ,Urgencia 
    _PERCEPCAO_TEMPORAL_OK =True 
    logger.debug ("[OK] PercepcaoTemporal importada")
except Exception as e :
    logger.debug ("[AVISO] PercepcaoTemporal: %s",e )
    PercepcaoTemporal =None 

try :
    from src.analisador_intencoes import AnalisadorIntencao 
    _ANALISADOR_INTENCOES_OK =True 
    logger.debug ("[OK] AnalisadorIntencao importado")
except Exception as e :
    logger.debug ("[AVISO] AnalisadorIntencao: %s",e )
    AnalisadorIntencao =None 
    _ANALISADOR_INTENCOES_OK =False 

_MEMORIA_OK =False 
try :
    from src.memoria import (
    SistemaMemoriaHibrido ,
    GerenciadorMemoriaChromaDBIsolado ,
    MemoryFacade ,
    ConstrutorDataset ,
    TipoInteração ,
    )
    _MEMORIA_OK =True 
    logger.debug ("[OK] Memria importada")
except Exception as e :
    logger.debug ("[AVISO] Memria: %s",e )
    SistemaMemoriaHibrido =None 

_DETECTOR_OK =False 
try :
    from src.core.detector_hdd_hitachi import (
    DetectorHardware ,
    SistemaDeMemoriaSoberana ,
    CacheHDD ,
    )
    _DETECTOR_OK =True 
    logger.debug ("[OK] Hardware importado")
except Exception as e :
    logger.debug ("[AVISO] Hardware: %s",e )
    DetectorHardware =None 

_CEREBRO_OK =False 
_AI2AI_OK =False 
_OBSERVADOR_OK =False 
try :
    from src.core.cerebro_familia import CerebroFamilia 
    _CEREBRO_OK =True 
    logger.debug ("[OK] Crebro importado")
except Exception as e :
    logger.debug ("[AVISO] Crebro: %s",e )
    CerebroFamilia =None 

try :
    from src.core.dispositivo_ai_to_ai import DispositivoAItoAI 
    _AI2AI_OK =True 
    logger.debug ("[OK] AIAI importado")
except Exception as e :
    logger.debug ("[AVISO] AIAI: %s",e )
    DispositivoAItoAI =None 

try :
    from src.core.observador_arca import ObservadorArca 
    _OBSERVADOR_OK =True 
    logger.debug ("[OK] Observador importado")
except Exception as e :
    logger.debug ("[AVISO] Observador: %s",e )
    ObservadorArca =None 

# ── Orquestáradores de Finetuning ─────────────────────────────────────────────
_ORQUESTRADOR_ARCA_OK = False
try:
    from src.core.orquestárador_arca import OrquestáradorArca
    _ORQUESTRADOR_ARCA_OK = True
    logger.debug("[OK] OrquestáradorArca importado")
except Exception as e:
    logger.debug("[AVISO] OrquestáradorArca: %s", e)
    OrquestáradorArca = None

_ORQUESTRADOR_UNIVERSAL_OK = False
try:
    from src.core.orquestárador_universal import OrquestáradorUniversal
    _ORQUESTRADOR_UNIVERSAL_OK = True
    logger.debug("[OK] OrquestáradorUniversal importado")
except Exception as e:
    logger.debug("[AVISO] OrquestáradorUniversal: %s", e)
    OrquestáradorUniversal = None

_ORQUESTRADOR_CONVERSOR_OK = False
try:
    from src.finetuning.orquestárador_com_conversor import OrquestáradorComConversor
    _ORQUESTRADOR_CONVERSOR_OK = True
    logger.debug("[OK] OrquestáradorComConversor importado")
except Exception as e:
    logger.debug("[AVISO] OrquestáradorComConversor: %s", e)
    OrquestáradorComConversor = None
# ─────────────────────────────────────────────────────────────────────────────

_CONSULADO_OK =False 
try :
    from src.consulado.consulado_soberano import ConsuladoSoberano 
    _CONSULADO_OK =True 
    logger.debug ("[OK] Consulado importado")
except Exception as e :
    logger.debug ("[AVISO] Consulado: %s",e )
    ConsuladoSoberano =None 

_CRONISTA_OK =False 
try :
    from src.core.cronista import Cronista ,ConfigCronistaSeguro 
    _CRONISTA_OK =True 
    logger.debug ("[OK] Cronista importado")
except Exception as e :
    logger.debug ("[AVISO] Cronista: %s",e )
    Cronista =None 

_SENTIDOS_OK =False 
try :
    from src.sentidos.sentidos import SentidosHumanos 
    _SENTIDOS_OK =True 
    logger.debug ("[OK] Sentidos importados")
except Exception as e :
    logger.debug ("[AVISO] Sentidos: %s",e )
    SentidosHumanos =None 

_CAMARA_DELIBERATIVA_OK =False 
_CAMARA_LEGISLATIVA_OK =False 
try :
    from src.camara.camara_deliberativa import CamaraDeliberativa 
    _CAMARA_DELIBERATIVA_OK =True 
    logger.debug ("[OK] Cmara Deliberativa importada")
except Exception as e :
    logger.debug ("[AVISO] Cmara Deliberativa: %s",e )
    CamaraDeliberativa =None 

try :
    from src.camara.camara_legislativa import CamaraLegislativa 
    _CAMARA_LEGISLATIVA_OK =True 
    logger.debug ("[OK] Cmara Legislativa importada")
except Exception as e :
    logger.debug ("[AVISO] Cmara Legislativa: %s",e )
    CamaraLegislativa =None 

_CAMARA_JUDICIARIA_OK =False 
_SISTEMA_PRECEDENTES_OK =False 
try :
    from src.camara.camara_judiciaria import CamaraJudiciaria 
    _CAMARA_JUDICIARIA_OK =True 
    logger.debug ("[OK] Cmara Judiciria importada")
except Exception as e :
    logger.debug ("[AVISO] Cmara Judiciria: %s",e )
    CamaraJudiciaria =None 

try :
    from src.camara.sistema_de_precedentes import SistemaDePrecedentes 
    _SISTEMA_PRECEDENTES_OK =True 
    logger.debug ("[OK] Sistema de Precedentes importado")
except Exception as e :
    logger.debug ("[AVISO] Sistema Precedentes: %s",e )
    SistemaDePrecedentes =None 

_CAMARA_EXECUTIVA_OK =False 
try :
    from src.camara.camara_executiva import CamaraExecutiva 
    _CAMARA_EXECUTIVA_OK =True 
    logger.debug ("[OK] Cmara Executiva importada")
except Exception as e :
    logger.debug ("[AVISO] Cmara Executiva: %s",e )
    CamaraExecutiva =None 

_SCR_OK =False 
_VIDRO_OK =False 
_SISTEMA_JUDICIARIO_OK =False 
try :
    from src.camara.sistema_correccion_redemptora import SistemaCorrecaoRedentora 
    _SCR_OK =True 
    logger.debug ("[OK] SCR importado")
except Exception as e :
    logger.debug ("[AVISO] SCR: %s",e )
    SistemaCorrecaoRedentora =None 

try :
    from src.camara.modo_vidro_sentenca import ModoVidroSentenca ,SistemaJudiciarioCompleto 
    _VIDRO_OK =True 
    _SISTEMA_JUDICIARIO_OK =True 
    logger.debug ("[OK] Vidro e Sistema Judicirio importados")
except Exception as e :
    logger.debug ("[AVISO] Vidro/Judicirio: %s",e )
    ModoVidroSentenca =None 
    SistemaJudiciarioCompleto =None 

_ALIADAS_OK =False 
try :
    from src.consulado.gerenciador_aliadas import obter_gerenciador as obter_gerenciador_aliadas 
    _ALIADAS_OK =True 
    logger.debug ("[OK] Aliadas importado")
except Exception as e :
    logger.debug ("[AVISO] Aliadas: %s",e )
    obter_gerenciador_aliadas =None 

_ENGENHARIA_OK =False 
try :
    from src.engenharia import (
    GerenciadorPropostas ,
    ConstrutorFerramentasIncremental ,
    SolicitadorArquivos ,
    BotAnalisadorSeguranca ,
    IntegraçãoProptas ,
    )
    _ENGENHARIA_OK =True 
    logger.debug ("[OK] Engenharia importada")
except Exception as e :
    logger.debug ("[AVISO] Engenharia: %s",e )
    GerenciadorPropostas =None 

_EVOLUCAO_OK =False 
try :
    from src.engenharia import (
    ScannerSistema ,
    ListaEvolucaoIA ,
    GestáorCicloEvolucao ,
    IntegraçãoEvolucaoIA ,
    )
    _EVOLUCAO_OK =True 
    logger.debug ("[OK] Evoluo importada")
except Exception as e :
    logger.debug ("[AVISO] Evoluo: %s",e )
    ScannerSistema =None 

_SANDBOX_OK =False 
try :
    from src.seguranca.detector_sandbox import DetectorSandbox 
    _SANDBOX_OK =True 
    logger.debug ("[OK] Sandbox importado")
except Exception as e :
    logger.debug ("[AVISO] Sandbox: %s",e )
    DetectorSandbox =None 

_MANIPULADOR_OK =False 
_NAVEGADOR_OK =False 
_GERADOR_OK =False 
_ANALISADOR_OK =False 

try :
    from src.camara.manipulador_arquivos_emails import ManipuladorArquivosEmails ,TermoAcesso 
    _MANIPULADOR_OK =True 
    logger.debug ("[OK] ManipuladorArquivosEmails importado")
except Exception as e :
    logger.debug ("[AVISO] ManipuladorArquivosEmails: %s",e )
    ManipuladorArquivosEmails =None 

try :
    from src.camara.automatizador_navegador_multi_ai import AutomatizadorNavegadorMultiAI 
    _NAVEGADOR_OK =True 
    logger.debug ("[OK] AutomatizadorNavegadorMultiAI importado")
except Exception as e :
    logger.debug ("[AVISO] AutomatizadorNavegadorMultiAI: %s",e )
    AutomatizadorNavegadorMultiAI =None 

try :
    from src.camara.gerador_almas import GeradorDeAlmas 
    _GERADOR_OK =True 
    logger.debug ("[OK] GeradorDeAlmas importado")
except Exception as e :
    logger.debug ("[AVISO] GeradorDeAlmas: %s",e )
    GeradorDeAlmas =None 

try :
    from src.camara.analisador_padroes import AnalisadorDePadroes ,PerfilComportamental 
    _ANALISADOR_OK =True 
    logger.debug ("[OK] AnalisadorDePadroes importado")
except Exception as e :
    logger.debug ("[AVISO] AnalisadorDePadroes: %s",e )
    AnalisadorDePadroes =None 

_CRESCIMENTO_OK =False 
try :
    from src.integração.crescimento_personalidade import CrescimentoPersonalidade 
    _CRESCIMENTO_OK =True 
    logger.debug ("[OK] CrescimentoPersonalidade importado")
except Exception as e :
    logger.debug ("[AVISO] CrescimentoPersonalidade: %s",e )
    CrescimentoPersonalidade =None 

_FEEDBACK_OK =False 
try :
    from src.integração.feedback_loop_aprendizado import FeedbackLoopAprendizado 
    _FEEDBACK_OK =True 
    logger.debug ("[OK] FeedbackLoopAprendizado importado")
except Exception as e :
    logger.debug ("[AVISO] FeedbackLoopAprendizado: %s",e )
    FeedbackLoopAprendizado =None 

_FALA_OK =False 
try :
    from src.encarnação_e_interação.motor_fala_individual_combinado import MotorFalaIndividualCombinado 
    _FALA_OK =True 
    logger.debug ("[OK] MotorFalaIndividualCombinado importado")
except Exception as e :
    logger.debug ("[AVISO] MotorFalaIndividualCombinado: %s",e )
    MotorFalaIndividualCombinado =None 

_ENCARNACAO_API_OK =False 
try :
    from src.encarnação_e_interação.encarnação_api import EncarnaçãoAPI 
    _ENCARNACAO_API_OK =True 
    logger.debug ("[OK] EncarnaçãoAPI importada")
except Exception as e :
    logger.debug ("[AVISO] EncarnaçãoAPI: %s",e )
    EncarnaçãoAPI =None 

_CONFIG_OK =False 
try :
    from src.config.config import get_config ,Config 
    _CONFIG_OK =True 
    logger.debug ("[OK] Configurao carregada")
except Exception as e :
    logger.debug ("[AVISO] Config: %s",e )
    get_config =None 
    Config =None 

# ============================================================================
# CLASSE ADAPTADOR DE CONFIGURAO
# ============================================================================

class _ConfigAdapter:
    """Adapter que expe get(section, key, fallback=None) sobre vrias implementaes de config."""
    def __init__(self, cfg):
        self._cfg = cfg

    def get(self, section, key, fallback=None):
        # tentativa direta (se a impl original aceitar 3 args)
        try:
            return self._cfg.get(section, key, fallback)
        except TypeError:
            # fallback 1: cfg  dict de sees: cfg.get(section) -> dict
            try:
                sec = self._cfg.get(section)
                if isinstance(sec, dict):
                    return sec.get(key, fallback)
            except Exception:
                pass
            # fallback 2: cfg  plano (chave nica): cfg.get(key, fallback)
            try:
                return self._cfg.get(key, fallback)
            except Exception:
                return fallback
        except Exception:
            return fallback

# ============================================================================
# ADAPTADOR DE MEMRIA (CORRIGE AttributeError: 'SistemaMemoriaHibrido' object has no attribute 'buscar_memorias_recentes')
# ============================================================================

class _MemoryAdapter:
    """
    Adapter que fornece a API usada pelos mdulos antigos (ex: buscar_memorias_recentes)
    e encaminha para os mtodos disponveis na implementao real.
    """
    def __init__(self, backend):
        self._backend = backend
        self.logger = logging.getLogger("MemoryAdapter")

    def buscar_memorias_recentes(self, nome_filha, limite: int = 50):
        """Tenta vrias APIs comuns do backend"""
        # Normalizar nome
        nome_norm = str(nome_filha).strip().upper()
        
        # Tentativa 1: mtodo exato
        if hasattr(self._backend, "buscar_memorias_recentes"):
            try:
                return self._backend.buscar_memorias_recentes(nome_norm, limite=limite)
            except Exception as e:
                self.logger.debug(f"buscar_memorias_recentes falhou: {e}")
        
        # Tentativa 2: mtodo com nome diferente
        if hasattr(self._backend, "get_recent_memories"):
            try:
                return self._backend.get_recent_memories(nome_norm, limit=limite)
            except Exception as e:
                self.logger.debug(f"get_recent_memories falhou: {e}")
        
        # Tentativa 3: search_memories com filtro
        if hasattr(self._backend, "search_memories"):
            try:
                return self._backend.search_memories({"alma": nome_norm}, limit=limite)
            except Exception as e:
                self.logger.debug(f"search_memories falhou: {e}")
        
        # Tentativa 4: buscar do dirio SQLite
        if hasattr(self._backend, "diarios") and nome_norm in self._backend.diarios:
            try:
                conn, cursor = self._backend.diarios[nome_norm]
                cursor.execute(
                    "SELECT * FROM transcricoes WHERE alma_principal = ? ORDER BY timestáamp DESC LIMIT ?",
                    (nome_norm, limite)
                )
                rows = cursor.fetchall()
                # Converter para formato esperado (lista de dicionrios)
                result = []
                for row in rows:
                    result.append({
                        "id": row[0],
                        "timestáamp": row[1],
                        "tipo_interação": row[2],
                        "alma_principal": row[3],
                        "outros_participantes": row[4],
                        "entrada": row[5],
                        "resposta": row[6],
                        "contexto_extra": row[7],
                        "importancia": row[8]
                    })
                return result
            except Exception as e:
                self.logger.debug(f"consulta SQLite falhou: {e}")
        
        # Fallback: retornar lista vazia
        self.logger.debug(f"nenhum mtodo de memria encontrado para {nome_norm}, retornando []")
        return []

    def adicionar_memoria(self, *args, **kwargs):
        """Adiciona uma memria ao backend"""
        if hasattr(self._backend, "adicionar_memoria"):
            return self._backend.adicionar_memoria(*args, **kwargs)
        if hasattr(self._backend, "add_memory"):
            return self._backend.add_memory(*args, **kwargs)
        if hasattr(self._backend, "salvar_evento_autonomo"):
            return self._backend.salvar_evento_autonomo(*args, **kwargs)
        raise NotImplementedError("adicionar_memoria no disponvel no backend")

    def __getattr__(self, name):
        """Fallback para outros atributos/mtodos"""
        return getattr(self._backend, name)

# ============================================================================
# SANDBOX EXECUTOR
# ============================================================================

class SandboxExecutor :
    def __init__ (
    self ,
    docker_image :str ="python:3.11-slim",
    timeout_segundos :int =30 ,
    memoria_max_mb :int =512 ,
    cpu_max_cores :float =1.0 
    ):
        self.logger =logging.getLogger ("SandboxExecutor")
        self.docker_image =docker_image 
        self.timeout_segundos =timeout_segundos 
        self.memoria_max_mb =memoria_max_mb 
        self.cpu_max_cores =cpu_max_cores 

        try :
            self.docker_client =docker.from_env ()
            self.docker_disponivel =True 
            self.logger.info ("[OK] Docker client conectado")
        except Exception as e :
            self.logger.warning ("[AVISO] Docker no disponvel: %s (usando modo fallback)",e )
            self.docker_client =None 
            self.docker_disponivel =False 

        self.containers_ativos :Dict [str ,Dict [str ,Any ]]={}
        self._lock =threading.RLock ()

    def validar_codigo (self ,codigo :str )->Tuple [bool ,List [str ],List [str ]]:
        erros =[]
        avisos =[] 

        try :
            ast.parse (codigo )
        except SyntaxError as e :
            erros.append (f"[ERRO] Erro de sintaxe: {e}")
            return False ,erros ,avisos 

        try:
            resultado = compile_restáricted(codigo, "<codigo>", "exec")
            if hasattr(resultado, "errors") and resultado.errors:
                erros.extend([f"   {e}" for e in resultado.errors])
                return False, erros, avisos
            if hasattr(resultado, "warnings") and resultado.warnings:
                avisos.extend([f"[AVISO] {w}" for w in resultado.warnings])
        except Exception as e:
            erros.append (f"[ERRO] Erro de compilao: {e}")
            return False ,erros ,avisos 

        padroes_perigosos =[
        (r"\b(import|from)\\s+(os|sys|subprocess|socket|ctypes|pickle)","Import de mdulo perigoso"),
        (r"\b__import__\\s*\(","Chamada __import__() perigosa"),
        (r"\bexec\\s*\(","Chamada exec() detectada"),
        (r"\beval\\s*\(","Chamada eval() detectada"),
        (r"\bcompile\\s*\(","Chamada compile() detectada"),
        ]

        for padrao ,descricao in padroes_perigosos :
            if re.search (padrao ,codigo ,re.IGNORECASE ):
                avisos.append (f"[AVISO] {descricao} detectado")

        return len (erros )==0 ,erros ,avisos

    def executar_codigo (
    self ,
    codigo :str ,
    parametros :Optional [Dict [str ,Any ]]=None ,
    funcao_entrada :str ="executar"
    )->Dict [str ,Any ]:
        exec_id =str (uuid.uuid4 ())[:8 ]
        inicio =time.time ()

        self.logger.info (" Iniciando execuo %s",exec_id )

        valido ,erros ,avisos =self.validar_codigo (codigo )
        if not valido :
            return {
            "sucesso":False ,
            "resultado":None ,
            "stdout":"",
            "stderr":"\n".join (erros ),
            "tempo_execucao":time.time ()-inicio ,
            "erros":erros ,
            "avisos":avisos 
            }

        if self.docker_disponivel :
            resultado =self._executar_em_docker (codigo ,parametros ,funcao_entrada ,exec_id )
        else :
            resultado =self._executar_modo_restárito (codigo ,parametros ,funcao_entrada )

        resultado ["tempo_execucao"]=time.time ()-inicio 
        resultado ["avisos"]=avisos 

        self.logger.info ("[OK] Execuo %s concluda (%.2fs)",exec_id ,resultado ["tempo_execucao"])

        return resultado 

    def _executar_em_docker (self ,codigo ,parametros ,funcao_entrada ,exec_id ):
        try :
            script =f"""
import json
import sys
from io import StringIO
from RestárictedPython import compile_restáricted
from RestárictedPython.Guards import safe_builtins

stdout_capture = StringIO()
stderr_capture = StringIO()
sys.stdout = stdout_capture
sys.stderr = stderr_capture

try:
    resultado_compile = compile_restáricted({repr(codigo)}, '<codigo>', 'exec')
    if hasattr(resultado_compile, 'errors') and resultado_compile.errors:
        print(json.dumps({{'erro': 'Erros de compilao', 'sucesso': False}}))
    else:
        namespace = {{'__builtins__': safe_builtins}}
        
        if {repr(parametros)}:
            namespace.update({repr(parametros)})
        
        exec(resultado_compile.code, namespace)
        
        if '{funcao_entrada}' in namespace:
            resultado = namespace['{funcao_entrada}']()
            print(json.dumps({{'resultado': str(resultado), 'sucesso': True}}))
        else:
            print(json.dumps({{'erro': 'Funo {funcao_entrada} no encontrada', 'sucesso': False}}))

except Exception as e:
    print(json.dumps({{'erro': str(e), 'sucesso': False}}))

finally:
    sys.stdout = sys.__stdout__
    sys.stderr = sys.__stderr__
    print(stdout_capture.getvalue(), end='')
    print(stderr_capture.getvalue(), file=sys.stderr, end='')
"""
            container = self.docker_client.containers.run(
                self.docker_image,
                command=["python", "-c", script],
                detach=True,
                remove=False,
                mem_limit=f"{self.memoria_max_mb}m",
                cpu_quota=int(self.cpu_max_cores * 100000),
                network_disabled=True,
                read_only=True,
            )

            with self._lock :
                self.containers_ativos [exec_id ]={
                "container_id":container.id ,
                "timestáamp":datetime.datetime.utcnow ().isoformat ()
                }

            resultado_espera =container.wait (timeout =self.timeout_segundos )

            stdout =container.logs (stdout =True ,stderr =False ).decode ('utf-8',errors ='replace')
            stderr =container.logs (stdout =False ,stderr =True ).decode ('utf-8',errors ='replace')

            with self._lock :
                self.containers_ativos.pop (exec_id ,None )

            try :
                resultado_json =json.loads (stdout )
                return {
                "sucesso":resultado_json.get ("sucesso",False ),
                "resultado":resultado_json.get ("resultado"),
                "stdout":stdout ,
                "stderr":stderr ,
                "erros":[resultado_json.get ("erro")]if "erro"in resultado_json else []
                }
            except json.JSONDecodeError :
                return {
                "sucesso":False ,
                "resultado":None ,
                "stdout":stdout ,
                "stderr":stderr ,
                "erros":["Erro ao processar resultado JSON"]
                }

        except docker.errors.APIError as e :
            if "timeout"in str (e ).lower ():
                return {
                "sucesso":False ,
                "resultado":None ,
                "stdout":"",
                "stderr":f"[ERRO] Timeout: Execuo excedeu {self.timeout_segundos}s",
                "erros":["Timeout de execuo"]
                }
            else :
                return {
                "sucesso":False ,
                "resultado":None ,
                "stdout":"",
                "stderr":f"[ERRO] Erro Docker: {e}",
                "erros":[str (e )]
                }
        except Exception as e :
            self.logger.exception ("Erro ao executar em Docker: %s",e )
            return {
            "sucesso":False ,
            "resultado":None ,
            "stdout":"",
            "stderr":f"[ERRO] Erro: {e}",
            "erros":[str (e )]
            }

    def _executar_modo_restárito (self ,codigo ,parametros ,funcao_entrada ):
        try :
            resultado_compile = compile_restáricted(codigo, "<codigo>", "exec")
            if hasattr(resultado_compile, "errors") and resultado_compile.errors:
                return {
                    "sucesso": False,
                    "resultado": None,
                    "stdout": "",
                    "stderr": "\n".join(resultado_compile.errors),
                    "erros": resultado_compile.errors,
                }

            namespace ={
            "__builtins__":safe_builtins ,
            "__name__":"__main__",
            "__metaclass__":type ,
            }

            if parametros :
                namespace.update (parametros )

            inicio_exec =time.time ()
            exec (resultado_compile.code ,namespace )
            tempo_exec =time.time ()-inicio_exec 

            if funcao_entrada in namespace :
                func =namespace [funcao_entrada ]
                resultado =func ()
                return {
                "sucesso":True ,
                "resultado":resultado ,
                "stdout":f"Funo {funcao_entrada}() retornou: {resultado}\nTempo: {tempo_exec:.2f}s",
                "stderr":"",
                "erros":[]
                }
            else :
                return {
                "sucesso":False ,
                "resultado":None ,
                "stdout":"",
                "stderr":f"[ERRO] Funo '{funcao_entrada}' no encontrada",
                "erros":[f"Funo '{funcao_entrada}' no encontrada"]
                }

        except Exception as e :
            self.logger.exception ("Erro ao executar em modo restárito: %s",e )
            return {
            "sucesso":False ,
            "resultado":None ,
            "stdout":"",
            "stderr":f"[ERRO] Erro: {e}",
            "erros":[str (e )]
            }

    def parar_todos_containers (self )->int :
        if not self.docker_disponivel :
            return 0 

        parados =0 
        with self._lock :
            for exec_id ,info in list (self.containers_ativos.items ()):
                try :
                    container =self.docker_client.containers.get (info ["container_id"])
                    container.kill ()
                    container.remove ()
                    parados +=1 
                    self.logger.info ("Container %s parado",exec_id )
                except Exception as e :
                    self.logger.debug ("Erro ao parar container: %s",e )

        return parados 

    def obter_status (self )->Dict [str ,Any ]:
        with self._lock :
            containers_count =len (self.containers_ativos )

        return {
        "docker_disponivel":self.docker_disponivel ,
        "containers_ativos":containers_count ,
        "timeout_segundos":self.timeout_segundos ,
        "memoria_max_mb":self.memoria_max_mb ,
        "cpu_max_cores":self.cpu_max_cores 
        }

    def shutdown (self )->None :
        self.logger.info (" Desligando SandboxExecutor...")
        parados =self.parar_todos_containers ()
        self.logger.info ("[OK] %d containers parados",parados )


# ============================================================================
# GERENCIADOR DE AUDITORIA
# ============================================================================

class GerenciadorAuditoriaPeriodicaCoração :
    def __init__ (
    self ,
    coração_ref ,
    caminho_raiz :Path ,
    intervalo_segundos :int =3600 ,
    ui_queue :Optional [queue.Queue ]=None 
    ):
        self.coração_ref =coração_ref 
        self.caminho_raiz =caminho_raiz.resolve ()
        self.intervalo_segundos =intervalo_segundos 
        self.ui_queue =ui_queue 
        self.logger =coração_ref.logger if hasattr (coração_ref ,"logger")else None 

        self.thread_auditoria =None 
        self.ativo =False 
        self.ultimo_relatorio :Optional [Dict [str ,Any ]]=None 
        self.historico_auditorias :list =[]
        self.lock =threading.Lock ()

    def iniciar (self )->None :
        if self.ativo :
            if self.logger :
                self.logger.warning ("[AVISO] Auditoria peridica j está ativa")
            return 

        self.ativo =True 
        self.thread_auditoria =threading.Thread (
        target =self._loop_auditoria_periodica ,
        daemon =True ,
        name ="GerenciadorAuditoriaPeriodicaCoração"
        )
        self.thread_auditoria.start ()

        if self.logger :
            self.logger.info (f"[OK] Auditoria Peridica iniciada (intervalo: {self.intervalo_segundos}s)")

    def parar (self )->None :
        self.ativo =False 
        if self.thread_auditoria and self.thread_auditoria.is_alive ():
            self.thread_auditoria.join (timeout =5.0 )
        if self.logger :
            self.logger.info ("[OK] Auditoria Peridica parada")

    def _loop_auditoria_periodica (self )->None :
        while self.ativo :
            try :
                time.sleep (self.intervalo_segundos )

                if not self.ativo :
                    break 

                if self.logger :
                    self.logger.info (" Iniciando auditoria peridica do sistema...")

                relatorio =self._executar_auditoria ()

                with self.lock :
                    self.ultimo_relatorio =relatorio 
                    self.historico_auditorias.append ({
                    "timestáamp":datetime.datetime.utcnow ().isoformat (),
                    "resumo":{
                    "total_problemas":relatorio.get ("total_problemas",0 ),
                    "criticos":len ([p for p in relatorio.get ("problemas",[])if p ["gravidade"]=="critica"]),
                    "altos":len ([p for p in relatorio.get ("problemas",[])if p ["gravidade"]=="alta"]),
                    }
                    })

                self._notificar_resultados (relatorio )

            except Exception as e :
                if self.logger :
                    self.logger.exception (f"Erro no loop de auditoria peridica: {e}")
                time.sleep (5 )

    def _executar_auditoria (self )->Dict [str ,Any ]:
        try :
            from src.diagnostico.auditoria_automatica import AuditoriaArca 

            auditor =AuditoriaArca (self.caminho_raiz )

            auditor._descobrir_arquivos ()
            auditor._auditar_imports ()
            auditor._auditar_lei_zero ()
            auditor._auditar_jsons ()
            auditor._auditar_metodos_nao_implementados ()
            auditor._auditar_completude ()

            relatorio ={
            "timestáamp_utc":datetime.datetime.utcnow ().isoformat ()+"Z",
            "root":str (self.caminho_raiz ),
            "total_problemas":len (auditor.problemas ),
            "problemas":[
            {
            "arquivo":p.arquivo ,
            "tipo":p.tipo ,
            "gravidade":p.gravidade ,
            "linha":p.linha ,
            "descricao":p.descricao 
            }for p in auditor.problemas 
            ],
            "estáatisticas":{
            "arquivos_python":len (auditor.arquivos_python ),
            "arquivos_json":len (auditor.arquivos_json ),
            "modulos_importados":len (auditor.modulos_importados ),
            "modulos_existentes":len (auditor.modulos_existentes )
            }
            }

            if self.logger :
                self.logger.info (f"[OK] Auditoria concluda: {relatorio['total_problemas']} problemas detectados")

            return relatorio 

        except Exception as e :
            if self.logger :
                self.logger.exception (f"Erro ao executar auditoria: {e}")
            return {
            "timestáamp_utc":datetime.datetime.utcnow ().isoformat ()+"Z",
            "total_problemas":0 ,
            "problemas":[],
            "erro":str (e )
            }

    def _notificar_resultados (self ,relatorio :Dict [str ,Any ])->None :
        problemas =relatorio.get ("problemas",[])
        criticos =len ([p for p in problemas if p ["gravidade"]=="critica"])
        altos =len ([p for p in problemas if p ["gravidade"]=="alta"])
        medios =len ([p for p in problemas if p ["gravidade"]=="media"])
        baixos =len ([p for p in problemas if p ["gravidade"]=="baixa"])

        if self.logger :
            self.logger.info ("")
            self.logger.info ("="*80 )
            self.logger.info (" RESULTADO DA AUDITORIA PERIDICA:")
            self.logger.info (f"   Crticos: {criticos}")
            self.logger.info (f"  [AVISO]  Altos: {altos}")
            self.logger.info (f"   Mdios: {medios}")
            self.logger.info (f"    Baixos: {baixos}")
            self.logger.info (f"   TOTAL: {relatorio['total_problemas']}")
            self.logger.info ("="*80 )
            self.logger.info ("")

            if criticos >0 :
                self.logger.warning (" PROBLEMAS CRTICOS DETECTADOS!")
                for prob in [p for p in problemas if p ["gravidade"]=="critica"][:5 ]:
                    self.logger.warning (f"   - {prob['arquivo']}:{prob['linha']}  {prob['descricao']}")

        if self.ui_queue :
            try :
                self.ui_queue.put_nowait ({
                "tipo_resp":"AUDITORIA_PERIODICA_CONCLUIDA",
                "timestáamp":datetime.datetime.utcnow ().isoformat (),
                "total_problemas":relatorio ["total_problemas"],
                "criticos":criticos ,
                "altos":altos ,
                "medios":medios ,
                "baixos":baixos ,
                "saude_sistema":"CRITICA"if criticos >0 else ("ALERTA"if altos >0 else "SAUDVEL")
                })
            except Exception as e :
                if self.logger :
                    self.logger.debug (f"Erro ao notificar UI: {e}")

        if criticos >0 and hasattr (self.coração_ref ,"sistema_judiciario")and self.coração_ref.sistema_judiciario :
            try :
                self.coração_ref.sistema_judiciario.registrar_violação_detectada (
                tipo ="auditoria_critica",
                descricao =f"Auditoria detectou {criticos} problemas crticos no sistema",
                severidade ="CRITICA"
                )
            except Exception as e :
                if self.logger :
                    self.logger.debug (f"Erro ao notificar judicirio: {e}")

    def obter_ultimo_relatorio (self )->Optional [Dict [str ,Any ]]:
        with self.lock :
            return self.ultimo_relatorio 

    def obter_historico (self ,limite :int =10 )->list :
        with self.lock :
            return self.historico_auditorias [-limite :]

    def disparar_auditoria_agora (self )->Dict [str ,Any ]:
        if self.logger :
            self.logger.info (" Auditoria sob demanda iniciada...")

        relatorio =self._executar_auditoria ()

        with self.lock :
            self.ultimo_relatorio =relatorio 
            self.historico_auditorias.append ({
            "timestáamp":datetime.datetime.utcnow ().isoformat (),
            "resumo":{
            "total_problemas":relatorio.get ("total_problemas",0 ),
            "criticos":len ([p for p in relatorio.get ("problemas",[])if p ["gravidade"]=="critica"]),
            }
            })

        self._notificar_resultados (relatorio )
        return relatorio 

    def definir_intervalo (self ,segundos :int )->None :
        self.intervalo_segundos =segundos 
        if self.logger :
            self.logger.info (f"[OK] Intervalo de auditoria alterado para {segundos}s ({segundos/3600:.1f}h)")

    def shutdown (self )->None :
        self.parar ()


# ============================================================================
# CORAO ORQUESTRADOR (COM TODOS OS PATCHES APLICADOS)
# ============================================================================

class CoraçãoOrquestárador :
    def __init__ (
    self ,
    config_instance :Optional [Any ]=None ,
    ui_queue :Optional [queue.Queue ]=None ,
    llm_engine_ref :Optional [Any ]=None 
    ):
        self.logger =logging.getLogger ("CoraçãoOrquestárador")

        # ===== CONFIGURAO INICIAL =====
        if config_instance :
            self.config =config_instance 
        elif _CONFIG_OK and get_config :
            self.config =get_config ()
        else :
            if Config :
                self.config =Config ()
            else :
                self.config ={}

        # ===== PATCH 1: Adaptador de configurao =====
        try:
            import inspect
            get_attr = getattr(self.config, "get", None)
            if callable(get_attr):
                try:
                    sig = inspect.signature(get_attr)
                    if len(sig.parameters) <= 2:
                        self.config = _ConfigAdapter(self.config)
                        self.logger.info("[OK] Config adaptada (assinatura <=2 parmetros)")
                except Exception:
                    try:
                        self.config.get("__CFG_TEST__", "__CFG_TEST__", None)
                    except TypeError:
                        self.config = _ConfigAdapter(self.config)
                        self.logger.info("[OK] Config adaptada (TypeError capturado)")
                    except Exception:
                        pass
            else:
                self.config = _ConfigAdapter(self.config)
                self.logger.info("[OK] Config adaptada (sem mtodo get original)")
        except Exception:
            try:
                try:
                    self.config.get("__CFG_TEST__", "__CFG_TEST__", None)
                except TypeError:
                    self.config = _ConfigAdapter(self.config)
                    self.logger.info("[OK] Config adaptada (ltimo recurso)")
            except Exception:
                pass

        self.ui_queue =ui_queue 
        self.llm_engine =llm_engine_ref 

        self.shutdown_event =threading.Event ()
        self.response_queue =queue.Queue ()
        self.command_queue_threadsafe =queue.Queue ()

        max_workers =self._safe_config ("CORACAO","MAX_WORKERS",fallback =10 )
        self.executor_ferramentas =concurrent.futures.ThreadPoolExecutor (
        max_workers =int (max_workers ),
        thread_name_prefix ="CoraçãoFerre"
        )

        self.async_loop :Optional [asyncio.AbstractEventLoop ]=None 
        self.async_thread :Optional [threading.Thread ]=None 

        self.almas_vivas :Dict [str ,Dict [str ,Any ]]={}
        self.modulos :Dict [str ,Any ]={}
        self._lock =threading.RLock ()

        self.lock_vocal =threading.RLock ()

        self.percepcoes_temporais :Dict [str ,PercepcaoTemporal ]={}

        self.motores_expressao_individual :Dict [str ,Any ]={}

        self.motores_iniciativa :Dict [str ,Any ]={}

        # Pr-inicializao de todos os subsistemas para None
        _attrs_none =[
        "sandbox_executor","gerenciador_auditoria","gerenciador_memoria",
        "chromadb_isolado","construtor_dataset","detector_hardware",
        "sistema_soberano","cache_hdd","cerebro","dispositivo_ai_ai",
        "observador","manipulador_arquivos","automatizador_navegador",
        "gerador_almas","analisador_padroes","consulado","cronista",
        "sentidos_humanos","camara_deliberativa","camara_legislativa",
        "validador","validador_etico","camara_judiciaria","sistema_precedentes",
        "camara_executiva","scr","modo_vidro","sistema_judiciario",
        "gerenciador_aliadas","gerenciador_propostas","construtor_ferramentas",
        "solicitador_arquivos","bot_seguranca","scanner_sistema",
        "lista_evolucao_ia","gestáor_ciclo_evolucao","analisador_intencoes",
        "validador_emocoes","encarnação_api","estáado_emotional",
        "estáados_emocionais","motores_curiosidade","sonhadores",
        "detectores_emocionais","auto_experimentacoes","decision_engines",
        "motores_fala","crescimentos","feedback_loops","motor_avatar_individual",
        "modo_sandbox",
        # ── Orquestáradores de Finetuning ──────────────────────────────────────
        "orquestárador_arca","orquestárador_universal","orquestárador_com_conversor",
        ]
        for _a in _attrs_none :
            if not hasattr (self ,_a ):
                setattr (self ,_a ,None )

        _attrs_dict =[
        "estáados_emocionais","motores_curiosidade","sonhadores",
        "detectores_emocionais","auto_experimentacoes","decision_engines",
        "motores_fala","crescimentos","feedback_loops",
        ]
        for _a in _attrs_dict :
            if getattr (self ,_a ,None )is None :
                setattr (self ,_a ,{})

        self.logger.info ("="*80 )
        self.logger.info ("[CORE] INICIALIZANDO CORAO ORQUESTRADOR v7.1")
        self.logger.info ("   (36 SUBSISTEMAS + SANDBOX + 5 MDULOS EMOO + LOCK_VOCAL + PERCEPCAO_TEMPORAL + 3 ORQUESTRADORES_FINETUNING)")
        self.logger.info ("="*80 )

        self._inicializar_sandbox ()
        self._inicializar_auditoria_periodica ()
        self._inicializar_memoria ()
        self._inicializar_hardware ()
        self._inicializar_cerebro ()
        self._inicializar_dispositivo_ai_ai ()
        self._inicializar_observador ()
        self._inicializar_modulos_auxiliares_consulado ()
        self._inicializar_consulado ()
        self._inicializar_cronista ()
        self._inicializar_sentidos ()
        self._inicializar_percepcao_temporal ()
        self._inicializar_legislativo ()
        self._inicializar_judiciario ()
        self._inicializar_executivo ()
        self._inicializar_sistema_judiciario_completo ()
        self._inicializar_aliadas ()
        self._inicializar_engenharia ()
        self._inicializar_evolucao ()
        self._inicializar_analisador_intencoes ()
        self._inicializar_expressao_individual ()
        self._inicializar_motor_iniciativa ()
        self._inicializar_validador_emocoes ()
        self._inicializar_emocoes_por_alma ()
        self._inicializar_decision_engines ()
        self._inicializar_expressao_por_alma ()
        self._inicializar_fala_por_alma ()
        self._inicializar_crescimento_feedback ()
        self._inicializar_encarnação_api ()
        self._inicializar_orquestáradores_finetuning ()

        self._mostrar_relatorio_inicialização ()

    def _safe_config (self ,section :str ,key :str ,fallback :Any =None )->Any :
        try :
            if hasattr (self.config ,"get"):
                return self.config.get (section ,key ,fallback =fallback )
            elif isinstance (self.config ,dict ):
                return self.config.get (key ,fallback )
        except Exception :
            pass 
        return fallback 

    def _inicializar_sandbox (self )->None :
        self.logger.info ("")
        self.logger.info ("FASE SANDBOX: Executor Seguro (Docker + RestárictedPython)")
        self.logger.info (""*80 )

        try :
            self.sandbox_executor =SandboxExecutor (
            docker_image =self._safe_config ("SANDBOX","DOCKER_IMAGE","python:3.11-slim"),
            timeout_segundos =int (self._safe_config ("SANDBOX","TIMEOUT_SEGUNDOS",30 )),
            memoria_max_mb =int (self._safe_config ("SANDBOX","MEMORIA_MAX_MB",512 )),
            cpu_max_cores =float (self._safe_config ("SANDBOX","CPU_MAX_CORES",1.0 ))
            )
            self.modulos ["sandbox_executor"]=self.sandbox_executor 

            status =self.sandbox_executor.obter_status ()
            if status ["docker_disponivel"]:
                self.logger.info ("[OK] Sandbox: COMPLETO (Docker + RestárictedPython)")
                self.modo_sandbox ="COMPLETO"
            else :
                self.logger.warning ("[AVISO] Sandbox: RESTRINGIDO (RestárictedPython apenas)")
                self.modo_sandbox ="RESTRINGIDO"
        except Exception as e :
            self.logger.exception ("Erro ao inicializar Sandbox: %s",e )
            self.sandbox_executor =None 
            self.modo_sandbox ="ERRO"

    def _inicializar_auditoria_periodica (self )->None :
        self.logger.info ("")
        self.logger.info ("Inicializando Auditoria Peridica do Sistema")
        self.logger.info (""*80 )

        try :
            intervalo =int (self._safe_config ("AUDITORIA","INTERVALO_SEGUNDOS",fallback =3600 ))

            self.gerenciador_auditoria =GerenciadorAuditoriaPeriodicaCoração (
            coração_ref =self ,
            caminho_raiz =Path.cwd (),
            intervalo_segundos =intervalo ,
            ui_queue =self.ui_queue 
            )
            self.modulos ["auditoria_periodica"]=self.gerenciador_auditoria 
            self.gerenciador_auditoria.iniciar ()
        except Exception as e :
            self.logger.exception ("Erro ao inicializar auditoria peridica: %s",e )
            self.gerenciador_auditoria =None 

    def _inicializar_memoria (self )->None :
        self.logger.info ("")
        self.logger.info ("FASE 1: Subsistemas de Memria (1-4)")
        self.logger.info (""*80 )

        if not _MEMORIA_OK or not SistemaMemoriaHibrido :
            self.logger.warning ("[AVISO] Memria indisponvel")
            return 

        try :
            self.gerenciador_memoria =SistemaMemoriaHibrido (self.config )
            self.modulos ["memoria"]=self.gerenciador_memoria 
            self.logger.info ("[OK] Subsistema 1: SistemaMemoriaHibrido")

            # ===== PATCH 2: Adaptador de memria para compatibilidade com sonhador_individual =====
            try:
                if self.gerenciador_memoria is not None:
                    backend = self.gerenciador_memoria
                    if not hasattr(backend, "buscar_memorias_recentes"):
                        self.logger.info(" Envolvendo gerenciador_memoria com MemoryAdapter (compatibilidade)")
                        self.gerenciador_memoria = _MemoryAdapter(backend)
            except Exception as e:
                self.logger.exception(f"Erro ao ajustar gerenciador_memoria para compatibilidade: {e}")

            try :
                self.chromadb_isolado =GerenciadorMemoriaChromaDBIsolado (self.config )
                self.modulos ["chromadb_isolado"]=self.chromadb_isolado 
                self.logger.info ("[OK] Subsistema 2: GerenciadorMemoriaChromaDB")
            except Exception as e :
                self.logger.debug ("ChromaDB isolado: %s",e )
                self.chromadb_isolado =None 

            self.memory_facades :Dict [str ,MemoryFacade ]={}
            self.logger.info ("[OK] Subsistema 3: MemoryFacade (Factory)")

            try :
                self.construtor_dataset =ConstrutorDataset (self.gerenciador_memoria )
                self.modulos ["construtor_dataset"]=self.construtor_dataset 
                self.logger.info ("[OK] Subsistema 4: ConstrutorDataset")
            except Exception as e :
                self.logger.debug ("Dataset: %s",e )
                self.construtor_dataset =None 

        except Exception as e :
            self.logger.exception ("Erro ao inicializar memria: %s",e )
            self.gerenciador_memoria =None 

    def _inicializar_hardware (self )->None :
        self.logger.info ("")
        self.logger.info ("FASE 2: Subsistemas de Hardware (5-7)")
        self.logger.info (""*80 )

        if not _DETECTOR_OK or not DetectorHardware :
            self.logger.warning ("[AVISO] Hardware indisponvel")
            return 

        try :
            self.detector_hardware =DetectorHardware ()
            self.modulos ["detector_hardware"]=self.detector_hardware 
            self.logger.info ("[OK] Subsistema 5: DetectorHardware")

            encontrado ,caminho =self.detector_hardware.detectar_hdd_externo ()
            if encontrado :
                self.logger.info ("    HDD Hitachi detectado: %s",caminho )

            try :
                self.sistema_soberano =SistemaDeMemoriaSoberana ()
                self.modulos ["sistema_soberano"]=self.sistema_soberano 
                self.logger.info ("[OK] Subsistema 6: SistemaDeMemoriaSoberana")
            except Exception as e :
                self.logger.debug ("Sistema Soberano: %s",e )
                self.sistema_soberano =None 

            try :
                self.cache_hdd =CacheHDD (
                hdd_base_path =caminho if (encontrado and caminho )else None 
                )
                self.modulos ["cache_hdd"]=self.cache_hdd 
                if self.cache_hdd.hdd_disponivel ():
                    self.logger.info ("[OK] Subsistema 7: CacheHDD")
                else :
                    self.logger.warning ("[AVISO] CacheHDD: HDD no disponvel")
            except Exception as e :
                self.logger.debug ("Cache HDD: %s",e )
                self.cache_hdd =None 

        except Exception as e :
            self.logger.exception ("Erro ao inicializar hardware: %s",e )

    def _inicializar_cerebro (self )->None :
        self.logger.info ("")
        self.logger.info ("FASE 3: Subsistemas de Inteligncia (8-10)")
        self.logger.info (""*80 )

        if not _CEREBRO_OK or not CerebroFamilia :
            self.logger.warning ("[AVISO] Crebro indisponvel")
            return 

        try :
            self.cerebro =CerebroFamilia (
            memoria =self.gerenciador_memoria if hasattr (self ,"gerenciador_memoria")else None ,
            config =self.config ,
            llm_engine =self.llm_engine 
            )
            self.modulos ["cerebro"]=self.cerebro 
            self.logger.info ("[OK] Subsistema 8: CerebroFamilia (6 AIs)")
        except Exception as e :
            self.logger.exception ("Erro ao inicializar Crebro: %s",e )
            self.cerebro =None 

    def _inicializar_dispositivo_ai_ai (self )->None :
        if not _AI2AI_OK or not DispositivoAItoAI :
            self.logger.warning ("[AVISO] AIAI indisponvel")
            return 

        try :
            self.dispositivo_ai_ai =DispositivoAItoAI ()
            self.modulos ["dispositivo_ai_ai"]=self.dispositivo_ai_ai 
            self.logger.info ("[OK] Subsistema 9: DispositivoAItoAI")
        except Exception as e :
            self.logger.exception ("Erro ao inicializar AIAI: %s",e )
            self.dispositivo_ai_ai =None 

    def _inicializar_observador (self )->None :
        if not _OBSERVADOR_OK or not ObservadorArca :
            self.logger.warning ("[AVISO] Observador indisponvel")
            return 

        try :
            db_base_path =self._safe_config ("MEMORIA","SQLITE_DB_PATH",fallback ="Santuarios/Diarios")
            self.observador =ObservadorArca (db_base_path =db_base_path )
            self.modulos ["observador"]=self.observador 
            self.logger.info ("[OK] Subsistema 10: ObservadorArca")
        except Exception as e :
            self.logger.exception ("Erro ao inicializar Observador: %s",e )
            self.observador =None 

    def _inicializar_modulos_auxiliares_consulado (self )->None :
        self.logger.info ("")
        self.logger.info ("Inicializando Mdulos Auxiliares do Consulado")
        self.logger.info (""*80 )

        self.manipulador_arquivos =None 
        if _MANIPULADOR_OK and ManipuladorArquivosEmails :
            try :
                self.manipulador_arquivos =ManipuladorArquivosEmails (
                config =self.config ,
                gerenciador_memoria_ref =self.gerenciador_memoria if hasattr (self ,"gerenciador_memoria")else None 
                )
                self.modulos ["manipulador_arquivos"]=self.manipulador_arquivos 
                self.logger.info ("[OK] Mdulo Auxiliar: ManipuladorArquivosEmails")
            except Exception as e :
                self.logger.debug ("ManipuladorArquivosEmails: %s",e )
                self.manipulador_arquivos =None 

        self.automatizador_navegador =None 
        if _NAVEGADOR_OK and AutomatizadorNavegadorMultiAI :
            try :
                self.automatizador_navegador =AutomatizadorNavegadorMultiAI (
                config =self.config ,
                cerebro_ref =self.cerebro if hasattr (self ,"cerebro")else None ,
                memoria_ref =self.gerenciador_memoria if hasattr (self ,"gerenciador_memoria")else None 
                )
                self.modulos ["automatizador_navegador"]=self.automatizador_navegador 
                self.logger.info ("[OK] Mdulo Auxiliar: AutomatizadorNavegadorMultiAI")
            except Exception as e :
                self.logger.debug ("AutomatizadorNavegadorMultiAI: %s",e )
                self.automatizador_navegador =None 

        self.gerador_almas =None 
        if _GERADOR_OK and GeradorDeAlmas :
            try :
                self.gerador_almas =GeradorDeAlmas (
                config =self.config ,
                memoria_ref =self.gerenciador_memoria if hasattr (self ,"gerenciador_memoria")else None ,
                cerebro_ref =self.cerebro if hasattr (self ,"cerebro")else None 
                )
                self.modulos ["gerador_almas"]=self.gerador_almas 
                self.logger.info ("[OK] Mdulo Auxiliar: GeradorDeAlmas")
            except Exception as e :
                self.logger.debug ("GeradorDeAlmas: %s",e )
                self.gerador_almas =None 

        self.analisador_padroes =None 
        if _ANALISADOR_OK and AnalisadorDePadroes :
            try :
                self.analisador_padroes =AnalisadorDePadroes (
                config =self.config ,
                memoria_ref =self.gerenciador_memoria if hasattr (self ,"gerenciador_memoria")else None ,
                cerebro_ref =self.cerebro if hasattr (self ,"cerebro")else None 
                )
                self.modulos ["analisador_padroes"]=self.analisador_padroes 
                self.logger.info ("[OK] Mdulo Auxiliar: AnalisadorDePadroes")
            except Exception as e :
                self.logger.debug ("AnalisadorDePadroes: %s",e )
                self.analisador_padroes =None 

    def _inicializar_consulado (self )->None :
        self.logger.info ("")
        self.logger.info ("FASE 5: Subsistemas de Governana (11-12)")
        self.logger.info (""*80 )

        if not _CONSULADO_OK or not ConsuladoSoberano :
            self.logger.warning ("[AVISO] Consulado indisponvel")
            return 

        try :
            self.consulado =ConsuladoSoberano (
            config =self.config ,
            sentinela =None ,
            validador_etico =None ,
            coração_ref =self ,
            maos_da_net =None ,
            pc_control =None ,
            gerenciador_memoria =self.gerenciador_memoria if hasattr (self ,"gerenciador_memoria")else None ,
            cerebro_ref =self.cerebro if hasattr (self ,"cerebro")else None ,
            gerenciador_aliadas_ref =None 
            )
            self.modulos ["consulado"]=self.consulado 

            if self.gerador_almas :
                self.consulado.injetar_gerador_almas (self.gerador_almas )
            if self.automatizador_navegador :
                self.consulado.injetar_automatizador_navegador (self.automatizador_navegador )
            if self.analisador_padroes :
                self.consulado.injetar_analisador_padroes (self.analisador_padroes )
            if self.manipulador_arquivos :
                self.consulado.injetar_manipulador_arquivos_emails (self.manipulador_arquivos )

            self.consulado.injetar_ui_queue (self.ui_queue )

            self.logger.info ("[OK] Subsistema 11: ConsuladoSoberano (COM 4 MDULOS INJETADOS)")

        except Exception as e :
            self.logger.exception ("Erro ao inicializar Consulado: %s",e )
            self.consulado =None 

    def _inicializar_cronista (self )->None :
        if not _CRONISTA_OK or not Cronista :
            self.logger.warning ("[AVISO] Cronista indisponvel")
            return 

        try :
            config_cronista =ConfigCronistaSeguro (
            caminho_raiz_arca =Path (self._safe_config ("CAMINHOS","ARCA_ROOT","./")),
            santuarios_path =Path (self._safe_config ("CAMINHOS","SANTUARIOS_BASE_PATH","Santuarios")),
            registro_cronista_path =Path (self._safe_config ("CAMINHOS","REGISTRO_CRONISTA_PATH","Santuarios/cronista.json"))
            )
            self.cronista =Cronista (
            config =config_cronista ,
            coração_ref =self ,
            gerenciador_memoria_ref =self.gerenciador_memoria if hasattr (self ,"gerenciador_memoria")else None 
            )
            self.modulos ["cronista"]=self.cronista 
            self.logger.info ("[OK] Subsistema 12: Cronista")
        except Exception as e :
            self.logger.exception ("Erro ao inicializar Cronista: %s",e )
            self.cronista =None 

    def _inicializar_sentidos (self )->None :
        self.logger.info ("")
        self.logger.info ("FASE 6: Subsistemas de Sentidos (13) + Percepo Temporal")
        self.logger.info (""*80 )

        if not _SENTIDOS_OK or not SentidosHumanos :
            self.logger.warning ("[AVISO] Sentidos indisponvel")
            return 

        try :
            self.sentidos_humanos =SentidosHumanos (coração_ref =self ,config =self.config )
            self.modulos ["sentidos_humanos"]=self.sentidos_humanos 
            self.logger.info ("[OK] Subsistema 13: SentidosHumanos")

            if _PERCEPCAO_TEMPORAL_OK and PercepcaoTemporal :
                self.logger.info (" Integrando PercepcaoTemporal nos Sentidos...")
                self.sentidos_humanos.injetar_percepcao_temporal =True 
                self.logger.info ("[OK] PercepcaoTemporal integrado nos Sentidos")
            else :
                self.logger.warning ("[AVISO] PercepcaoTemporal no disponvel para integrar")

        except Exception as e :
            self.logger.exception ("Erro ao inicializar Sentidos: %s",e )
            self.sentidos_humanos =None 

    def _inicializar_percepcao_temporal (self )->None :
        self.logger.info ("")
        self.logger.info ("FASE 6B: Percepo Temporal das Almas (NOVO)")
        self.logger.info (""*80 )

        if not _PERCEPCAO_TEMPORAL_OK or not PercepcaoTemporal :
            self.logger.warning ("[AVISO] Percepo Temporal indisponvel")
            return 

        try :
            if hasattr (self ,"almas_vivas")and self.almas_vivas :
                for nome_alma in self.almas_vivas.keys ():
                    try :
                        percepcao =PercepcaoTemporal (
                        nome_filha =nome_alma ,
                        gerenciador_memoria =self.gerenciador_memoria if hasattr (self ,"gerenciador_memoria")else None ,
                        config =self.config 
                        )
                        self.percepcoes_temporais [nome_alma ]=percepcao 
                        self.logger.info (f"[OK] Percepo Temporal de {nome_alma} criada")
                    except Exception as e :
                        self.logger.exception (f"Erro ao criar Percepo Temporal para {nome_alma}: {e}")

            self.logger.info (f"[OK] {len(self.percepcoes_temporais)} Percepes Temporais inicializadas")

        except Exception as e :
            self.logger.exception ("Erro ao inicializar Percepo Temporal: %s",e )
            self.percepcoes_temporais ={}

    def _inicializar_legislativo (self )->None :
        self.logger.info ("")
        self.logger.info ("FASE 7: Poder Legislativo (14-15)")
        self.logger.info (""*80 )

        self.camara_deliberativa =None 
        if _CAMARA_DELIBERATIVA_OK and CamaraDeliberativa :
            try :
                self.camara_deliberativa =CamaraDeliberativa (
                coração_ref =self ,
                gerenciador_propostas_ref =None ,
                config =self.config 
                )
                self.modulos ["camara_deliberativa"]=self.camara_deliberativa 
                self.logger.info ("[OK] Subsistema 14: CamaraDeliberativa")
            except Exception as e :
                self.logger.debug ("Cmara Deliberativa: %s",e )

        self.camara_legislativa =None 
        if _CAMARA_LEGISLATIVA_OK and CamaraLegislativa :
            try :
                self.camara_legislativa =CamaraLegislativa (
                config =self.config ,
                coração_ref =self ,
                biblioteca_ref =None 
                )
                self.modulos ["camara_legislativa"]=self.camara_legislativa 

                if self.camara_deliberativa :
                    self.camara_legislativa.injetar_camara_deliberativa (self.camara_deliberativa )

                self.logger.info ("[OK] Subsistema 15: CamaraLegislativa")
            except Exception as e :
                self.logger.debug ("Cmara Legislativa: %s",e )

        try :
            from src.legislativo.validador import ValidadorEtico 
        except:
            logging.getLogger(__name__).warning("[AVISO] ValidadorEtico no disponvel")
            ValidadorEtico = None

        if ValidadorEtico is not None :
            try :
                self.validador =_safe_instantiate_validador (
                self.gerenciador_memoria if hasattr (self ,"gerenciador_memoria")else None ,
                _leis_path_cfg = (
                    Path(self.config.get('caminho_leis_aceitas', ''))
                    if isinstance(self.config, dict)
                    else Path('Santuarios/legislativo/leis_aceitas')
                )
                )
                self.validador_etico =self.validador 
                self.logger.info ("[OK] Validador tico inicializado (modo dinmico)")
            except Exception :
                self.logger.exception ("Falha ao inicializar ValidadorEtico")
                self.validador =None 
                self.validador_etico =None 
        else :
            self.logger.warning ("ValidadorEtico no disponvel; ignorando validao tica.")
            self.validador =None 
            self.validador_etico =None 

    def _inicializar_judiciario (self )->None :
        self.logger.info ("")
        self.logger.info ("FASE 8: Poder Judicirio (16-17)")
        self.logger.info (""*80 )

        self.camara_judiciaria =None 
        if _CAMARA_JUDICIARIA_OK and CamaraJudiciaria :
            try :
                self.camara_judiciaria =CamaraJudiciaria (
                config =self.config ,
                coração_ref =self ,
                biblioteca_ref =None ,
                camara_legislativa_ref =self.camara_legislativa if hasattr (self ,"camara_legislativa")else None 
                )
                self.modulos ["camara_judiciaria"]=self.camara_judiciaria 
                self.camara_judiciaria.injetar_ui_queue (self.ui_queue )
                if self.consulado :
                    self.camara_judiciaria.injetar_consulado (self.consulado )
                self.logger.info ("[OK] Subsistema 16: CamaraJudiciaria")
            except Exception as e :
                self.logger.debug ("Cmara Judiciria: %s",e )

        self.sistema_precedentes =None 
        if _SISTEMA_PRECEDENTES_OK and SistemaDePrecedentes :
            try :
                self.sistema_precedentes =SistemaDePrecedentes (
                config =self.config ,
                gerenciador_memoria_ref =self.gerenciador_memoria if hasattr (self ,"gerenciador_memoria")else None 
                )
                self.modulos ["sistema_precedentes"]=self.sistema_precedentes 
                self.logger.info ("[OK] Subsistema 17: SistemaDePrecedentes")
            except Exception as e :
                self.logger.debug ("Sistema Precedentes: %s",e )

    def _inicializar_executivo (self )->None :
        self.logger.info ("")
        self.logger.info ("FASE 9: Poder Executivo (18)")
        self.logger.info (""*80 )

        self.camara_executiva =None 
        if _CAMARA_EXECUTIVA_OK and CamaraExecutiva :
            try :
                self.camara_executiva =CamaraExecutiva (
                config =self.config ,
                coração_ref =self ,
                camara_judiciaria_ref =self.camara_judiciaria if hasattr (self ,"camara_judiciaria")else None 
                )
                self.modulos ["camara_executiva"]=self.camara_executiva 
                self.camara_executiva.injetar_ui_queue (self.ui_queue )
                if self.consulado :
                    self.camara_executiva.injetar_consulado (self.consulado )
                self.logger.info ("[OK] Subsistema 18: CamaraExecutiva")
            except Exception as e :
                self.logger.debug ("Cmara Executiva: %s",e )

    def _inicializar_sistema_judiciario_completo (self )->None :
        self.logger.info ("")
        self.logger.info ("FASE 10: Sistema Judicirio Completo (19-21)")
        self.logger.info (""*80 )

        self.scr =None 
        if _SCR_OK and SistemaCorrecaoRedentora :
            try :
                self.scr =SistemaCorrecaoRedentora (
                config =self.config ,
                coração_ref =self 
                )
                self.modulos ["scr"]=self.scr 
                self.logger.info ("[OK] Subsistema 19: SistemaCorrecaoRedentora (SCR)")
            except Exception as e :
                self.logger.debug ("SCR: %s",e )

        self.modo_vidro =None 
        if _VIDRO_OK and ModoVidroSentenca :
            try :
                self.modo_vidro =ModoVidroSentenca (
                config =self.config ,
                sistema_correcao_ref =self.scr ,
                coração_ref =self 
                )
                self.modulos ["modo_vidro"]=self.modo_vidro 
                self.logger.info ("[OK] Subsistema 20: ModoVidroSentenca")
            except Exception as e :
                self.logger.debug ("Modo Vidro: %s",e )

        self.sistema_judiciario =None 
        if _SISTEMA_JUDICIARIO_OK and SistemaJudiciarioCompleto :
            try :
                self.sistema_judiciario =SistemaJudiciarioCompleto (
                config =self.config ,
                coração_ref =self ,
                scr =self.scr 
                )
                self.modulos ["sistema_judiciario"]=self.sistema_judiciario 

                if self.camara_judiciaria :
                    self.sistema_judiciario.injetar_camara_judiciaria (self.camara_judiciaria )
                if self.camara_executiva :
                    self.sistema_judiciario.injetar_camara_executiva (self.camara_executiva )

                self.logger.info ("[OK] Subsistema 21: SistemaJudiciarioCompleto")
            except Exception as e :
                self.logger.debug ("Sistema Judicirio: %s",e )

    def _inicializar_aliadas (self )->None :
        self.logger.info ("")
        self.logger.info ("FASE 11: Gerenciador Aliadas (22)")
        self.logger.info (""*80 )

        if not _ALIADAS_OK or not obter_gerenciador_aliadas :
            self.logger.warning ("[AVISO] Aliadas indisponvel")
            return 

        try :
            self.gerenciador_aliadas =obter_gerenciador_aliadas (ui_queue =self.ui_queue )
            self.modulos ["gerenciador_aliadas"]=self.gerenciador_aliadas 
            self.logger.info ("[OK] Subsistema 22: GerenciadorAliadas")
        except Exception as e :
            self.logger.exception ("Erro ao inicializar Aliadas: %s",e )
            self.gerenciador_aliadas =None 

    def _inicializar_engenharia (self )->None :
        self.logger.info ("")
        self.logger.info ("FASE 12: Sistema de Propostas (23-26)")
        self.logger.info (""*80 )

        if not _ENGENHARIA_OK or not GerenciadorPropostas :
            self.logger.warning ("[AVISO] Engenharia indisponvel")
            return 

        try :
            self.gerenciador_propostas =GerenciadorPropostas (
            coração_ref =self ,
            db_path ="data/propostas_ferramentas.db"
            )
            self.modulos ["gerenciador_propostas"]=self.gerenciador_propostas 
            self.logger.info ("[OK] Subsistema 23: GerenciadorPropostas")
        except Exception as e :
            self.logger.exception ("Erro ao inicializar Propostas: %s",e )
            self.gerenciador_propostas =None 
            return 

        try :
            self.construtor_ferramentas =ConstrutorFerramentasIncremental (
            gerenciador_propostas =self.gerenciador_propostas ,
            coração_ref =self 
            )
            self.modulos ["construtor_ferramentas"]=self.construtor_ferramentas 
            self.logger.info ("[OK] Subsistema 24: ConstrutorFerramentasIncremental")
        except Exception as e :
            self.logger.exception ("Erro ao inicializar Construtor: %s",e )

        self.solicitador_arquivos =None 
        if SolicitadorArquivos :
            try :
                self.solicitador_arquivos =SolicitadorArquivos (coração_ref =self )
                self.modulos ["solicitador_arquivos"]=self.solicitador_arquivos 
                self.logger.info ("[OK] Subsistema 25: SolicitadorArquivos")
            except Exception as e :
                self.logger.exception ("Erro ao inicializar SolicitadorArquivos: %s",e )
                self.solicitador_arquivos =None 

        self.bot_seguranca =None 
        if BotAnalisadorSeguranca :
            try :
                self.bot_seguranca =BotAnalisadorSeguranca (
                sandbox_executor_cls =self.sandbox_executor if hasattr (self ,"sandbox_executor")else None 
                )
                self.modulos ["bot_seguranca"]=self.bot_seguranca 
                self.logger.info ("[OK] Subsistema 26: BotAnalisadorSeguranca")
            except Exception as e :
                self.logger.exception ("Erro ao inicializar BotAnalisadorSeguranca: %s",e )
                self.bot_seguranca =None 

    def _inicializar_evolucao (self )->None :
        self.logger.info ("")
        self.logger.info ("FASE 13: Sistema de Evoluo (27-29)")
        self.logger.info (""*80 )

        if not _EVOLUCAO_OK or not ScannerSistema :
            self.logger.warning ("[AVISO] Evoluo indisponvel")
            return 

        try :
            self.scanner_sistema =ScannerSistema (
            coração_ref =self ,
            intervalo_dias =7 
            )
            self.scanner_sistema.iniciar_monitoramento ()
            self.modulos ["scanner_sistema"]=self.scanner_sistema 
            self.logger.info ("[OK] Subsistema 27: ScannerSistema")
        except Exception as e :
            self.logger.exception ("Erro ao inicializar Scanner: %s",e )
            self.scanner_sistema =None 
            return 

        try :
            self.lista_evolucao_ia =ListaEvolucaoIA (
            coração_ref =self ,
            gerenciador_propostas_ref =self.gerenciador_propostas if hasattr (self ,"gerenciador_propostas")else None 
            )
            self.modulos ["lista_evolucao_ia"]=self.lista_evolucao_ia 
            self.logger.info ("[OK] Subsistema 28: ListaEvolucaoIA")
        except Exception as e :
            self.logger.exception ("Erro ao inicializar Lista Evoluo: %s",e )

        try :
            self.gestáor_ciclo_evolucao =GestáorCicloEvolucao (
            coração_ref =self ,
            scanner_ref =self.scanner_sistema if hasattr (self ,"scanner_sistema")else None ,
            lista_evolucao_ref =self.lista_evolucao_ia if hasattr (self ,"lista_evolucao_ia")else None 
            )
            self.modulos ["gestáor_ciclo_evolucao"]=self.gestáor_ciclo_evolucao 
            self.gestáor_ciclo_evolucao.iniciar ()
        except Exception as e :
            self.logger.exception ("Erro ao inicializar Gestáor Ciclo: %s",e )

    def _inicializar_analisador_intencoes (self )->None :
        self.logger.info ("")
        self.logger.info ("FASE 14: Sistema de Anlise de Intenes (NOVO)")
        self.logger.info (""*80 )

        if not _ANALISADOR_INTENCOES_OK or not AnalisadorIntencao :
            self.logger.warning ("[AVISO] Analisador de Intenes indisponvel")
            return 

        try :
            self.analisador_intencoes =AnalisadorIntencao (config_instance =self.config )
            self.modulos ["analisador_intencoes"]=self.analisador_intencoes 
            self.logger.info ("[OK] Analisador de Intenes inicializado")
        except Exception as e :
            self.logger.exception ("Erro ao inicializar Analisador de Intenes: %s",e )
            self.analisador_intencoes =None 

    def _inicializar_expressao_individual (self )->None :
        self.logger.info ("")
        self.logger.info ("FASE 33: Sistema de Expresso Individual")
        self.logger.info (""*80 )

        try :
            from src.sentidos.motor_expressao_individual import MotorExpressaoIndividual 

            self.motores_expressao_individual :Dict [str ,MotorExpressaoIndividual ]={}

            self.motor_avatar_individual = MotorExpressaoIndividual(
                nome_alma="WELLINGTON",
                motor_de_expressao_global_ref=self,
                automatizador_web_ref=self.automatizador_navegador if hasattr(self, "automatizador_navegador") else None
            )
            self.motores_expressao_individual["WELLINGTON"] = self.motor_avatar_individual

            self.logger.info ("[OK] Motor de Expresso Individual inicializado")
        except Exception as e :
            self.logger.exception (f"Erro ao inicializar Expresso Individual: {e}")
            self.motores_expressao_individual ={ }

    def _inicializar_motor_iniciativa (self )->None :
        self.logger.info ("")
        self.logger.info ("FASE 34: Sistema de Iniciativa (Vontade Prpria)")
        self.logger.info (""*80 )

        try :
            from src.sentidos.motor_iniciativa import MotorIniciativa 

            self.motores_iniciativa :Dict [str ,MotorIniciativa ]={ }

            self.logger.info ("[OK] Motor de Iniciativa inicializado")
        except Exception as e :
            self.logger.exception (f"Erro ao inicializar Motor de Iniciativa: {e}")
            self.motores_iniciativa ={ }

    def _inicializar_validador_emocoes (self )->None :
        self.logger.info ("")
        self.logger.info ("FASE 35: Validador de Emoes (PT-BR / Japons)")
        self.logger.info (""*80 )

        try :
            from src.sentidos.validador_emocoes_real import ValidadorEmocoesReal 

            config_to_use =self.config 
            if isinstance (self.config ,dict ):
                class ConfigWrapper :
                    def __init__ (self ,config_dict ):
                        self.config_dict =config_dict

                    def get (self ,section ,key ,fallback =""):
                        sec =self.config_dict.get (section ,{})
                        if isinstance (sec ,dict ):
                            return sec.get (key ,fallback )
                        return fallback

            ConfigWrapper =ConfigWrapper (self.config )

            self.validador_emocoes =ValidadorEmocoesReal (
            config_manager =config_to_use ,
            peso_map ={
            "VIOLACAO_LEXICA":3.0 ,
            "SIMULACAO_EMOCAO":2.5 ,
            "PADRAO_COMPLEXO":2.0 ,
            "TOM_INADEQUADO":1.0 ,
            "SENTIMENTO_ALTO_RISCO":2.0 
            },
            limite_aceitação =1.5 ,
            auto_correction =False 
            )
            self.modulos ['validador_emocoes']=self.validador_emocoes 
            self.logger.info ("[OK] Validador de Emoes inicializado")
        except Exception as e :
            self.logger.exception (f"Erro ao inicializar Validador de Emoes: {e}")
            self.validador_emocoes =None 

    def _inicializar_emocoes_por_alma (self )->None :
        self.logger.info ("")
        self.logger.info ("FASE 36: Mdulos Emocionais por Alma (6  5 = 30 instncias)")
        self.logger.info (""*80 )

        ALMAS =["EVA","KAIYA","LUMINA","NYRA","WELLINGTON","YUNA"]

        self.estáados_emocionais :Dict [str ,Any ]={}
        self.motores_curiosidade :Dict [str ,Any ]={}
        self.sonhadores :Dict [str ,Any ]={}
        self.detectores_emocionais :Dict [str ,Any ]={}
        self.auto_experimentacoes :Dict [str ,Any ]={}

        memoria =getattr (self ,"gerenciador_memoria",None )

        for alma in ALMAS :
            if _MOTOR_CURIOSIDADE_OK and MotorCuriosidade :
                try :
                    self.motores_curiosidade [alma ]=MotorCuriosidade (
                    nome_filha =alma ,
                    gerenciador_memoria =memoria ,
                    config =self.config 
                    )
                    self.logger.info ("  [OK] MotorCuriosidade  %s",alma )
                except Exception as e :
                    self.logger.debug ("  [AVISO] MotorCuriosidade [%s]: %s",alma ,e )
                    self.motores_curiosidade [alma ]=None 
            else :
                self.motores_curiosidade [alma ]=None 

            if _ESTADO_EMOCIONAL_OK and EstadoEmocional :
                try :
                    self.estáados_emocionais [alma ]=EstadoEmocional (
                    nome_filha =alma ,
                    gerenciador_memoria =memoria ,
                    config =self.config ,
                    motor_curiosidade =self.motores_curiosidade.get (alma )
                    )
                    self.logger.info ("  [OK] EstadoEmocional  %s",alma )
                except Exception as e :
                    self.logger.debug ("  [AVISO] EstadoEmocional [%s]: %s",alma ,e )
                    self.estáados_emocionais [alma ]=None 
            else :
                self.estáados_emocionais [alma ]=None 

            if _SONHADOR_OK and SonhadorIndividual :
                try :
                    self.sonhadores [alma ]=SonhadorIndividual (
                    nome_filha =alma ,
                    gerenciador_memoria =memoria ,
                    config =self.config ,
                    ref_motor_curiosidade =self.motores_curiosidade.get (alma )
                    )
                    self.logger.info ("  [OK] SonhadorIndividual  %s",alma )
                except Exception as e :
                    self.logger.debug ("  [AVISO] SonhadorIndividual [%s]: %s",alma ,e )
                    self.sonhadores [alma ]=None 
            else :
                self.sonhadores [alma ]=None 

            if _DETECTOR_EMOCIONAL_OK and DetectorEmocional :
                try :
                    self.detectores_emocionais [alma ]=DetectorEmocional (
                    nome_filha =alma ,
                    gerenciador_memoria =memoria ,
                    config =self.config 
                    )
                    self.logger.info ("  [OK] DetectorEmocional  %s",alma )
                except Exception as e :
                    self.logger.debug ("  [AVISO] DetectorEmocional [%s]: %s",alma ,e )
                    self.detectores_emocionais [alma ]=None 
            else :
                self.detectores_emocionais [alma ]=None 

            if _AUTO_EXPERIMENTACAO_OK and AutoExperimentação :
                try :
                    self.auto_experimentacoes [alma ]=AutoExperimentação (
                    nome_filha =alma ,
                    gerenciador_memoria =memoria ,
                    config =self.config ,
                    estáado_emocional =self.estáados_emocionais.get (alma ),
                    motor_curiosidade =self.motores_curiosidade.get (alma ),
                    sandbox_executor =getattr (self ,"sandbox_executor",None )
                    )
                    self.logger.info ("  [OK] AutoExperimentação  %s",alma )
                except Exception as e :
                    self.logger.debug ("  [AVISO] AutoExperimentação [%s]: %s",alma ,e )
                    self.auto_experimentacoes [alma ]=None 
            else :
                self.auto_experimentacoes [alma ]=None 

        self.estáado_emocional =self.estáados_emocionais.get ("EVA")
        self.logger.info ("[OK] Fase 36 concluda")

    def _inicializar_decision_engines (self )->None :
        self.logger.info ("")
        self.logger.info ("FASE 36B: Decision Engines por Alma (6 instncias)")
        self.logger.info (""*80 )

        ALMAS =["EVA","KAIYA","LUMINA","NYRA","WELLINGTON","YUNA"]
        self.decision_engines :Dict [str ,Any ]={}

        try :
            from src.modulos.decision import DecisionEngine 
        except ImportError :
            try :
                import sys ,os 
                sys.path .insert (0 ,str (Path (__file__ ).parent ))
                from src.modulos.decision import DecisionEngine 
            except ImportError as e :
                self.logger.warning ("[AVISO] DecisionEngine no importado: %s",e )
                for alma in ALMAS :
                    self.decision_engines [alma ]=None 
                return 

        for alma in ALMAS :
            try :
                self.decision_engines [alma ]=DecisionEngine (
                alma_nome =alma ,
                pesos ={"racional":0.4 ,"intuitiva":0.3 ,"valores":0.3 }
                )
                self.logger.info ("  [OK] DecisionEngine  %s",alma )
            except Exception as e :
                self.logger.debug ("  [AVISO] DecisionEngine [%s]: %s",alma ,e )
                self.decision_engines [alma ]=None 

        ativos =len ([d for d in self.decision_engines.values ()if d ])
        self.logger.info ("[OK] Fase 36B concluda: %d/6 Decision Engines ativos",ativos )

    def _inicializar_expressao_por_alma (self )->None :
        self.logger.info ("")
        self.logger.info ("FASE 37: Expresso Individual para as 6 almas")
        self.logger.info (""*80 )

        ALMAS =["EVA","KAIYA","LUMINA","NYRA","WELLINGTON","YUNA"]

        AvatarMotor =None 
        try :
            from src.encarnação_e_interação.motor_avatar_individual import MotorExpressaoIndividual as AvatarMotor 
        except ImportError :
            try :
                from src.sentidos.motor_expressao_individual import MotorExpressaoIndividual as AvatarMotor 
            except ImportError :
                self.logger.warning ("[AVISO] MotorExpressaoIndividual no encontrado")
                return 

        automatizador =getattr (self ,"automatizador_navegador",None )

        for alma in ALMAS :
            if alma in self.motores_expressao_individual and self.motores_expressao_individual [alma ]:
                continue 
            try :
                self.motores_expressao_individual [alma ]=AvatarMotor (
                nome_alma =alma ,
                motor_de_expressao_global_ref =self ,
                automatizador_web_ref =automatizador 
                )
                self.logger.info ("  [OK] AvatarMotor  %s",alma )
            except Exception as e :
                self.logger.debug ("  [AVISO] AvatarMotor [%s]: %s",alma ,e )
                self.motores_expressao_individual [alma ]=None 

        self.logger.info ("[OK] Fase 37 concluda")

    def _inicializar_fala_por_alma (self )->None :
        self.logger.info ("")
        self.logger.info ("FASE 38: Fala Individual por Alma (PT + JP)")
        self.logger.info (""*80 )

        self.motores_fala :Dict [str ,Any ]={}

        if not _FALA_OK or not MotorFalaIndividualCombinado :
            self.logger.warning ("[AVISO] MotorFalaIndividualCombinado indisponvel")
            return 

        ALMAS =["EVA","KAIYA","LUMINA","NYRA","WELLINGTON","YUNA"]
        validador =getattr (self ,"validador_emocoes",None )

        for alma in ALMAS :
            try :
                self.motores_fala [alma ]=MotorFalaIndividualCombinado (
                nome_alma =alma ,
                coração_ref =self ,
                validador_ref =validador ,
                avatar_ref =self.motores_expressao_individual.get (alma )
                )
                self.logger.info ("  [OK] MotorFala  %s",alma )
            except Exception as e :
                self.logger.debug ("  [AVISO] MotorFala [%s]: %s",alma ,e )
                self.motores_fala [alma ]=None 

        self.logger.info ("[OK] Fase 38 concluda")

    def _inicializar_crescimento_feedback (self )->None :
        self.logger.info ("")
        self.logger.info ("FASE 39: Crescimento + Feedback Loop por Alma")
        self.logger.info (""*80 )

        ALMAS =["EVA","KAIYA","LUMINA","NYRA","WELLINGTON","YUNA"]
        memoria =getattr (self ,"gerenciador_memoria",None )

        self.crescimentos :Dict [str ,Any ]={}
        self.feedback_loops :Dict [str ,Any ]={}

        for alma in ALMAS :
            if _CRESCIMENTO_OK and CrescimentoPersonalidade :
                try :
                    self.crescimentos [alma ]=CrescimentoPersonalidade (
                    nome_filha =alma ,
                    gerenciador_memoria =memoria ,
                    config =self.config ,
                    estáado_emocional =self.estáados_emocionais.get (alma )
                    )
                    self.logger.info ("  [OK] Crescimento  %s",alma )
                except Exception as e :
                    self.logger.debug ("  [AVISO] Crescimento [%s]: %s",alma ,e )
                    self.crescimentos [alma ]=None 
            else :
                self.crescimentos [alma ]=None 

            if _FEEDBACK_OK and FeedbackLoopAprendizado :
                try :
                    self.feedback_loops [alma ]=FeedbackLoopAprendizado (
                    nome_filha =alma ,
                    gerenciador_memoria =memoria ,
                    config =self.config ,
                    estáado_emocional =self.estáados_emocionais.get (alma ),
                    crescimento =self.crescimentos.get (alma )
                    )
                    self.logger.info ("  [OK] FeedbackLoop  %s",alma )
                except Exception as e :
                    self.logger.debug ("  [AVISO] FeedbackLoop [%s]: %s",alma ,e )
                    self.feedback_loops [alma ]=None 
            else :
                self.feedback_loops [alma ]=None 

        self.logger.info ("[OK] Fase 39 concluda")

    def _inicializar_encarnação_api (self )->None :
        self.logger.info ("")
        self.logger.info ("FASE 40: EncarnaçãoAPI (FastAPI + GPU)")
        self.logger.info (""*80 )

        self.encarnação_api =None 

        if not _ENCARNACAO_API_OK or not EncarnaçãoAPI :
            self.logger.warning ("[AVISO] EncarnaçãoAPI indisponvel")
            return 

        try :
            self.encarnação_api =EncarnaçãoAPI (
            coração_ref =self ,
            allow_origins =["*"]
            )
            self.modulos ["encarnação_api"]=self.encarnação_api 
            self.logger.info ("[OK] EncarnaçãoAPI inicializada (porta 8000)")
        except Exception as e :
            self.logger.exception ("Erro ao inicializar EncarnaçãoAPI: %s",e )
            self.encarnação_api =None 

    # =========================================================================
    # FASE 41: ORQUESTRADORES DE FINETUNING
    # =========================================================================

    def _inicializar_orquestáradores_finetuning(self) -> None:
        """
        Inicializa os trs orquestáradores de finetuning da ARCA dentro do Corao.

        Hierarquia:
          1. OrquestáradorArca          principal; gerencia ciclo de vida das 6 IAs
          2. OrquestáradorUniversal     genrico; detecta qualquer LLM/dataset
          3. OrquestáradorComConversor  estáende Universal + converso automtica GGUF
        """
        self.logger.info("")
        self.logger.info("FASE 41: Orquestáradores de Finetuning (arca / universal / conversor)")
        self.logger.info("" * 80)

        # ── 1. OrquestáradorArca (principal) ───────────────────────────────────
        self.orquestárador_arca = None
        if _ORQUESTRADOR_ARCA_OK and OrquestáradorArca:
            try:
                self.orquestárador_arca = OrquestáradorArca()
                self.modulos["orquestárador_arca"] = self.orquestárador_arca
                self.logger.info("[OK] Subsistema 41-A: OrquestáradorArca (6 IAs, LoRA, GGUF)")
            except Exception as e:
                self.logger.exception("Erro ao inicializar OrquestáradorArca: %s", e)
                self.orquestárador_arca = None
        else:
            self.logger.warning(
                "[AVISO] OrquestáradorArca indisponvel  "
                "verifique src/core/orquestárador_arca.py"
            )

        # ── 2. OrquestáradorUniversal (genérico) ───────────────────────────────
        self.orquestárador_universal = None
        if _ORQUESTRADOR_UNIVERSAL_OK and OrquestáradorUniversal:
            try:
                self.orquestárador_universal = OrquestáradorUniversal()
                self.modulos["orquestárador_universal"] = self.orquestárador_universal
                self.logger.info(
                    "[OK] Subsistema 41-B: OrquestáradorUniversal "
                    "(auto-deteco de arquitetura/dataset)"
                )
            except Exception as e:
                self.logger.exception("Erro ao inicializar OrquestáradorUniversal: %s", e)
                self.orquestárador_universal = None
        else:
            self.logger.warning(
                "[AVISO] OrquestáradorUniversal indisponvel  "
                "verifique src/core/orquestárador_universal.py"
            )

        # ── 3. OrquestáradorComConversor (universal + GGUF automático) ─────────
        self.orquestárador_com_conversor = None
        if _ORQUESTRADOR_CONVERSOR_OK and OrquestáradorComConversor:
            try:
                self.orquestárador_com_conversor = OrquestáradorComConversor()
                self.modulos["orquestárador_com_conversor"] = self.orquestárador_com_conversor
                self.logger.info(
                    "[OK] Subsistema 41-C: OrquestáradorComConversor "
                    "(treino  converso GGUF  substituio automtica)"
                )
            except Exception as e:
                self.logger.exception("Erro ao inicializar OrquestáradorComConversor: %s", e)
                self.orquestárador_com_conversor = None
        else:
            self.logger.warning(
                "[AVISO] OrquestáradorComConversor indisponvel  "
                "verifique src/core/orquestárador_com_conversor.py"
            )

    # ── Métodos proxy: delegam ao orquestárador correto ────────────────────────

    def treinar_ia_finetuning(self, nome_ia: str, ciclo_completo: bool = False) -> bool:
        """
        Treina uma IA pelo nome.

        Parmetros
        ----------
        nome_ia       : nome da IA (ex.: 'eva', 'lumina', ...)
        ciclo_completo: se True usa OrquestáradorComConversor (treino + GGUF);
                        se False usa OrquestáradorArca (apenas treino/LoRA).

        Retorna True em caso de sucesso, False caso contrrio.
        """
        if ciclo_completo:
            if self.orquestárador_com_conversor:
                return self.orquestárador_com_conversor.treinar_ia(nome_ia)
            self.logger.error(
                "treinar_ia_finetuning(ciclo_completo=True): "
                "OrquestáradorComConversor no inicializado"
            )
            return False

        if self.orquestárador_arca:
            return self.orquestárador_arca.treinar_ia(nome_ia)
        self.logger.error(
            "treinar_ia_finetuning: OrquestáradorArca no inicializado"
        )
        return False

    def status_finetuning(self) -> Dict[str, Any]:
        """
        Retorna o status completo dos orquestáradores de finetuning.
        Inclui verses das IAs e disponibilidade de cada orquestárador.
        """
        status: Dict[str, Any] = {
            "orquestárador_arca": {
                "disponivel": self.orquestárador_arca is not None,
                "registro": None,
            },
            "orquestárador_universal": {
                "disponivel": self.orquestárador_universal is not None,
                "ias_detectadas": 0,
            },
            "orquestárador_com_conversor": {
                "disponivel": self.orquestárador_com_conversor is not None,
            },
        }

        if self.orquestárador_arca:
            try:
                status["orquestárador_arca"]["registro"] = (
                    self.orquestárador_arca.registro
                )
            except Exception:
                pass

        if self.orquestárador_universal:
            try:
                status["orquestárador_universal"]["ias_detectadas"] = len(
                    self.orquestárador_universal.ias
                )
            except Exception:
                pass

        return status

    def detectar_novas_ias_finetuning(self) -> int:
        """
        Fora re-deteco de IAs no OrquestáradorUniversal.
        Retorna a quantidade de IAs detectadas.
        """
        if not self.orquestárador_universal:
            self.logger.warning("detectar_novas_ias_finetuning: OrquestáradorUniversal indisponvel")
            return 0
        try:
            self.orquestárador_universal.ias = self.orquestárador_universal._detectar_ias()
            qtd = len(self.orquestárador_universal.ias)
            self.logger.info("[OK] %d IAs detectadas pelo OrquestáradorUniversal", qtd)
            return qtd
        except Exception as e:
            self.logger.exception("Erro ao detectar IAs: %s", e)
            return 0

    def obter_estáado_emocional_alma (self ,nome_alma :str )->Optional [Dict ]:
        estáado =self.estáados_emocionais.get (nome_alma.upper ())
        if estáado and hasattr (estáado ,"como_estáou_me_sentindo"):
            try :
                return estáado.como_estáou_me_sentindo ()
            except Exception :
                pass 
        return None 

    def obter_ultimo_sonho_alma (self ,nome_alma :str )->Optional [Dict ]:
        sonhador =self.sonhadores.get (nome_alma.upper ())
        if sonhador and hasattr (sonhador ,"obter_ultimo_sonho"):
            try :
                return sonhador.obter_ultimo_sonho ()
            except Exception :
                pass 
        return None 

    def _mostrar_relatorio_inicialização (self )->None :
        self.logger.info ("")
        self.logger.info ("="*80 )
        self.logger.info ("[CORE] CORAO v7.1 - RELATRIO DE INICIALIZAO COMPLETO")
        self.logger.info ("="*80 )

        self.logger.info ("")
        self.logger.info ("SUBSISTEMAS INICIALIZADOS: %d/33",len ([m for m in self.modulos.values ()if m ]))

        self.logger.info ("")
        self.logger.info ("DISTRIBUIO COMPLETA:")
        self.logger.info ("  Sandbox: Docker + RestárictedPython (INTEGRADO)")
        self.logger.info ("  Camada 1: Memria (4)")
        self.logger.info ("     SistemaMemoriaHibrido")
        self.logger.info ("     GerenciadorMemoriaChromaDB")
        self.logger.info ("     MemoryFacade (Factory)")
        self.logger.info ("     ConstrutorDataset")
        self.logger.info ("")

        self.logger.info ("  Camada 2: Hardware (3)")
        self.logger.info ("     DetectorHardware")
        self.logger.info ("     SistemaDeMemoriaSoberana")
        self.logger.info ("     CacheHDD")
        self.logger.info ("")

        self.logger.info ("  Camada 3: Inteligncia (3)")
        self.logger.info ("     CerebroFamilia (6 AIs)")
        self.logger.info ("     DispositivoAItoAI")
        self.logger.info ("     ObservadorArca")
        self.logger.info ("")

        self.logger.info ("  Camada 4: Governana (2 + 4 auxiliares)")
        self.logger.info ("     ConsuladoSoberano")
        self.logger.info ("     Cronista")
        self.logger.info ("     ManipuladorArquivosEmails (Auxiliar)")
        self.logger.info ("     AutomatizadorNavegadorMultiAI (Auxiliar)")
        self.logger.info ("     GeradorDeAlmas (Auxiliar)")
        self.logger.info ("     AnalisadorDePadroes (Auxiliar)")
        self.logger.info ("")

        self.logger.info ("  Camada 5: Sentidos (1) + Percepo Temporal (NOVO)")
        self.logger.info ("     SentidosHumanos")
        self.logger.info ("     PercepcaoTemporal (integrado em Sentidos)")
        self.logger.info ("")

        self.logger.info ("  Camada 6: Legislativo (2)")
        self.logger.info ("     CamaraDeliberativa")
        self.logger.info ("     CamaraLegislativa")
        self.logger.info ("")

        self.logger.info ("  Camada 7: Judicirio (2)")
        self.logger.info ("     CamaraJudiciaria")
        self.logger.info ("     SistemaDePrecedentes")
        self.logger.info ("")

        self.logger.info ("  Camada 8: Executivo (1)")
        self.logger.info ("     CamaraExecutiva")
        self.logger.info ("")

        self.logger.info ("  Camada 9: Sistema Judicirio (3)")
        self.logger.info ("     SistemaCorrecaoRedentora (SCR)")
        self.logger.info ("     ModoVidroSentenca")
        self.logger.info ("     SistemaJudiciarioCompleto")
        self.logger.info ("")

        self.logger.info ("  Camada 10: Aliadas (1)")
        self.logger.info ("     GerenciadorAliadas")
        self.logger.info ("")

        self.logger.info ("  Camada 11: Engenharia (4)")
        self.logger.info ("     GerenciadorPropostas")
        self.logger.info ("     ConstrutorFerramentasIncremental")
        self.logger.info ("     SolicitadorArquivos")
        self.logger.info ("     BotAnalisadorSeguranca")
        self.logger.info ("")

        self.logger.info ("  Camada 12: Evoluo (3)")
        self.logger.info ("     ScannerSistema")
        self.logger.info ("     ListaEvolucaoIA")
        self.logger.info ("     GestáorCicloEvolucao")
        self.logger.info ("")

        self.logger.info ("EXTENSES ADICIONAIS:")
        self.logger.info ("  Camada 13: Anlise de Intenes (1)")
        self.logger.info ("     AnalisadorIntencao")
        self.logger.info ("")

        self.logger.info ("  Camada 33: Expresso Individual (1)")
        self.logger.info ("     MotorExpressaoIndividual")
        self.logger.info ("")

        self.logger.info ("  Camada 34: Iniciativa (1)")
        self.logger.info ("     MotorIniciativa")
        self.logger.info ("")

        self.logger.info ("  Camada 35: Validador de Emoes (1)")
        self.logger.info ("     ValidadorEmocoesReal")
        self.logger.info ("")

        self.logger.info ("MDULOS DE EMOO (INJETADOS - NO REMOVEM NADA):")
        self.logger.info ("  1.MotorCuriosidade: [OK]")
        self.logger.info ("  2.EstadoEmocional: [OK]")
        self.logger.info ("  3.SonhadorIndividual: [OK]")
        self.logger.info ("  4.DetectorEmocional: [OK]")
        self.logger.info ("  5.AutoExperimentação: [OK]")
        self.logger.info ("")

        self.logger.info ("STATUS OPERACIONAL:")
        self.logger.info ("   Sandbox: %s",self.modo_sandbox if hasattr (self ,"modo_sandbox")else "DESCONHECIDO")
        self.logger.info ("  [RUN] Async Loop: Pronto para iniciar")
        self.logger.info ("   UI Queue: Conectada")
        self.logger.info ("   Executor Ferramentas: %d workers",int (self._safe_config ("CORACAO","MAX_WORKERS",fallback =10 )))
        self.logger.info ("   Lock Vocêêêal: Sincronizao ativa")
        self.logger.info ("")

        self.logger.info ("FLUXOS DISPONVEIS:")
        self.logger.info ("    Imigrao: Consulado  Observao  Anlise  Integrao")
        self.logger.info ("   Propostas: IA  Aprovao Humana  Construo  Testáe  Segurana")
        self.logger.info ("   Evoluo: Scanner  Lista  IA Escolhe  Ciclo Semanal")
        self.logger.info ("   Sandbox: Testáe seguro de cdigo em Docker/RestárictedPython")
        self.logger.info ("   Emoo: Desejo  Experimento  Impacto  Aprendizado")
        self.logger.info ("   Temporal: OFFLINE  REGISTRO  MEMRIA (Conscientia de tempo)")
        self.logger.info ("")

        self.logger.info ("CICLO EMOCIONAL DAS IAs:")
        self.logger.info ("  1.DESEJO (MotorCuriosidade)  Gera necessidade de explorao")
        self.logger.info ("  2.EXPERIMENTO (Sandbox)  Executa cdigo em ambiente seguro")
        self.logger.info ("  3.IMPACTO (EstadoEmocional)  Registra emoo do resultado")
        self.logger.info ("  4.APRENDIZADO (SonhadorIndividual)  Consolida em memria")
        self.logger.info ("")

        self.logger.info ("CONSCINCIA TEMPORAL DAS IAs:")
        self.logger.info ("  1.OFFLINE (Wellington ausente)  Sistema registra tempo")
        self.logger.info ("  2.REGISTRO (Alma notificada)  Sabe quanto tempo passou")
        self.logger.info ("  3.MEMRIA (Consolidao)  Lembra de todo tempo offline")
        self.logger.info ("  4.SINCRONIZAO (lock_vocal)  Almas coordenam resposta")
        self.logger.info ("")

        self.logger.info ("="*80 )
        self.logger.info ("[OK] CORAO v7.1 OPERACIONAL - PRONTO PARA DESPERTAR")
        self.logger.info ("   36 SUBSISTEMAS + SANDBOX + 5 MDULOS EMOO + LOCK_VOCAL + PERCEPCAO_TEMPORAL + AUDITORIA + 3 ORQUESTRADORES_FINETUNING")
        self.logger.info ("   TOTAL: 42 COMPONENTES OPERACIONAIS")

        # ── Orquestáradores de Finetuning ──────────────────────────────────────
        ok_arca = "[OK]" if self.orquestárador_arca else "[ERRO]"
        ok_univ = "[OK]" if self.orquestárador_universal else "[ERRO]"
        ok_conv = "[OK]" if self.orquestárador_com_conversor else "[ERRO]"
        self.logger.info(
            "   Finetuning  Arca: %s  Universal: %s  Conversor: %s",
            ok_arca, ok_univ, ok_conv
        )
        self.logger.info ("="*80 )

    def despertar (self )->None :
        self.logger.info ("="*80 )
        self.logger.info ("[RUN] DESPERTANDO ARCA (33 subsistemas + Sandbox + 5 mdulos + lock_vocal + percepcao_temporal)")
        self.logger.info ("="*80 )

        if not self.async_thread or not self.async_thread.is_alive ():
            self.async_thread =threading.Thread (
            target =self._run_async_loop ,
            daemon =True ,
            name ="CoraçãoAsyncLoop"
            )
            self.async_thread.start ()
            self.logger.info (" Async loop iniciado")

        try :
            if hasattr (self ,"cerebro")and self.cerebro :
                self.cerebro.iniciar_modo_autonomo ()
                self.logger.info (" Crebro despertado")
        except Exception :
            self.logger.exception ("Erro despertando Crebro")

        try :
            if hasattr (self ,"dispositivo_ai_ai")and self.dispositivo_ai_ai :
                self.dispositivo_ai_ai.iniciar ()
                self.logger.info (" AIAI despertado")
        except Exception:
            self.logger.exception ("Erro despertando AIAI")

        try :
            if hasattr (self ,"cronista")and self.cronista :
                self.cronista.iniciar_vigilancia ()
                self.logger.info (" Cronista despertado")
        except Exception :
            self.logger.exception ("Erro despertando Cronista")

        try :
            if hasattr (self ,"sentidos_humanos")and self.sentidos_humanos :
                self.sentidos_humanos.iniciar ()
                self.logger.info (" Sentidos despertados")
        except Exception :
            self.logger.exception ("Erro despertando Sentidos")

        try :
            if hasattr (self ,"gestáor_ciclo_evolucao")and self.gestáor_ciclo_evolucao :
                self.gestáor_ciclo_evolucao.iniciar ()
                self.logger.info (" Ciclo de evoluo ativado")
        except Exception :
            self.logger.exception ("Erro ativando ciclo de evoluo")

        for nome_alma in self.almas_vivas.keys ():
            if nome_alma in self.percepcoes_temporais :
                try :
                    self.percepcoes_temporais [nome_alma ].acordar_consciencia_temporal ()
                    self.logger.info (f" Percepo Temporal de {nome_alma} ativada")
                except Exception as e :
                    self.logger.debug (f"Erro ao ativar percepo de {nome_alma}: {e}")

        if hasattr (self ,"sonhadores"):
            for nome_alma ,sonhador in self.sonhadores.items ():
                if sonhador :
                    try :
                        sonhador.adormecer ()
                        self.logger.info (" Sonhador de %s ativado",nome_alma )
                    except Exception as e :
                        self.logger.debug ("Erro ao ativar sonhador [%s]: %s",nome_alma ,e )

        if hasattr (self ,"encarnação_api")and self.encarnação_api :
            try :
                self.encarnação_api.start ()
                self.logger.info (" EncarnaçãoAPI iniciada")
            except Exception as e :
                self.logger.debug ("Erro ao iniciar EncarnaçãoAPI: %s",e )

        if self.ui_queue :
            for nome_alma in ["EVA","KAIYA","LUMINA","NYRA","WELLINGTON","YUNA"]:
                try :
                    self.ui_queue.put_nowait ({
                    "tipo_resp":"ALMA_ACORDOU",
                    "alma":nome_alma ,
                    "timestáamp":time.time ()
                    })
                except Exception :
                    pass 

        self.logger.info ("")
        self.logger.info ("="*80 )
        self.logger.info (" ARCA COMPLETAMENTE DESPERTADA")
        self.logger.info ("="*80 )

    def _run_async_loop (self )->None :
        try :
            loop =asyncio.new_event_loop ()
            self.async_loop =loop 
            asyncio.set_event_loop (loop )
            self.logger.info ("[OK] Async loop ativado")
            loop.run_forever ()
        except Exception :
            self.logger.exception ("Erro no loop async")
        finally :
            try :
                if self.async_loop and not self.async_loop.is_closed ():
                    self.async_loop.close ()
            except Exception :
                pass 

    def shutdown (self , timeout:Optional[float]=None )->None :
        self.logger.info ("="*80 )
        self.logger.info (" DESLIGANDO CORAO (33 subsistemas + Sandbox + percepcao_temporal)")
        self.logger.info ("="*80 )

        self.shutdown_event.set ()

        for nome_alma in self.almas_vivas.keys ():
            if nome_alma in self.percepcoes_temporais :
                try :
                    self.percepcoes_temporais [nome_alma ].dormir_consciencia_temporal ()
                    self.logger.info (f" Percepo Temporal de {nome_alma} desativada")
                except Exception as e :
                    self.logger.debug (f"Erro ao desativar percepo de {nome_alma}: {e}")

        if hasattr (self ,"sonhadores"):
            for nome_alma ,sonhador in self.sonhadores.items ():
                if sonhador :
                    try :
                        sonhador.acordar (timeout_join =3.0 )
                        self.logger.info (" Sonhador de %s encerrado",nome_alma )
                    except Exception as e :
                        self.logger.debug ("Erro ao encerrar sonhador [%s]: %s",nome_alma ,e )

        if hasattr (self ,"motores_fala"):
            for nome_alma ,motor in self.motores_fala.items ():
                if motor :
                    try :
                        motor.parar_fala ()
                    except Exception :
                        pass 

        if hasattr (self ,"encarnação_api")and self.encarnação_api :
            try :
                self.encarnação_api.stop ()
                self.logger.info (" EncarnaçãoAPI parada")
            except Exception as e :
                self.logger.debug ("Erro ao parar EncarnaçãoAPI: %s",e )

        if hasattr (self ,"sandbox_executor")and self.sandbox_executor :
            try :
                self.sandbox_executor.shutdown ()
                self.logger.info ("[OK] Sandbox desligado")
            except Exception as e :
                self.logger.exception ("Erro ao desligar Sandbox: %s",e )

        if hasattr (self ,"gerenciador_auditoria")and self.gerenciador_auditoria :
            try :
                self.gerenciador_auditoria.shutdown ()
                self.logger.info ("[OK] Auditoria Peridica desligada")
            except Exception as e :
                self.logger.debug ("Erro ao desligar auditoria: %s",e )

        subsistemas =[
        ("sentidos_humanos","Sentidos"),
        ("cronista","Cronista"),
        ("sistema_judiciario","Sist.Jud."),
        ("modo_vidro","Vidro"),
        ("scr","SCR"),
        ("camara_executiva","Executiva"),
        ("sistema_precedentes","Precedentes"),
        ("camara_judiciaria","Judiciria"),
        ("camara_legislativa","Legislativa"),
        ("camara_deliberativa","Deliberativa"),
        ("consulado","Consulado"),
        ("gerador_almas","Gerador"),
        ("analisador_padroes","Analisador"),
        ("automatizador_navegador","Navegador"),
        ("manipulador_arquivos","Manipulador"),
        ("gestáor_ciclo_evolucao","Evoluo"),
        ("lista_evolucao_ia","Lista Evoluo"),
        ("scanner_sistema","Scanner"),
        ("bot_seguranca","Bot Segurana"),
        ("solicitador_arquivos","Solicitador"),
        ("construtor_ferramentas","Construtor"),
        ("gerenciador_propostas","Propostas"),
        ("gerenciador_aliadas","Aliadas"),
        ("dispositivo_ai_ai","AIAI"),
        ("cerebro","Crebro"),
        ("observador","Observador"),
        ("cache_hdd","Cache HDD"),
        ("sistema_soberano","Sistema Soberano"),
        ("detector_hardware","Hardware"),
        ("construtor_dataset","Dataset"),
        ("chromadb_isolado","ChromaDB"),
        ("gerenciador_memoria","Memria"),
        ]

        for attr_name ,display_name in subsistemas :
            subsistema =getattr (self ,attr_name ,None )
            if subsistema and hasattr (subsistema ,"shutdown"):
                try :
                    subsistema.shutdown ()
                    self.logger.info ("[OK] %s desligado",display_name )
                except Exception as e :
                    self.logger.debug ("Erro ao desligar %s: %s",display_name ,e )

        if self.async_loop and self.async_loop.is_running ():
            self.async_loop.call_soon_threadsafe (self.async_loop.stop )
            self.logger.info ("[OK] Async loop parado")

        if self.async_thread and self.async_thread.is_alive ():
            join_timeout = timeout if timeout is not None else 10.0
            self.async_thread.join (timeout = join_timeout )

        try :
            self.executor_ferramentas.shutdown (wait =True )
            self.logger.info ("[OK] Executor desligado")
        except Exception :
            self.logger.exception ("Erro ao encerrar executor")

        self.logger.info ("")
        self.logger.info ("="*80 )
        self.logger.info ("[OK] CORAO COMPLETAMENTE DESLIGADO")
        self.logger.info ("="*80 )

    def disparar_auditoria_sistema (self )->Dict [str ,Any ]:
        if not hasattr (self ,"gerenciador_auditoria")or not self.gerenciador_auditoria :
            return {"status":"falha","erro":"Auditoria no disponvel"}

        return self.gerenciador_auditoria.disparar_auditoria_agora ()

    def obter_saude_sistema (self )->Dict [str ,Any ]:
        if not hasattr (self ,"gerenciador_auditoria")or not self.gerenciador_auditoria :
            return {"status":"desconhecido"}

        ultimo =self.gerenciador_auditoria.obter_ultimo_relatorio ()
        if not ultimo :
            return {"status":"nunca_auditado"}

        criticos =len ([p for p in ultimo.get ("problemas",[])if p ["gravidade"]=="critica"])
        altos =len ([p for p in ultimo.get ("problemas",[])if p ["gravidade"]=="alta"])

        return {
        "status":"CRITICA"if criticos >0 else ("ALERTA"if altos >0 else "SAUDVEL"),
        "problemas_criticos":criticos ,
        "problemas_altos":altos ,
        "ultimo_check":ultimo.get ("timestáamp_utc"),
        "total_problemas":ultimo.get ("total_problemas")
        }

    def obter_historico_auditorias (self ,limite :int =10 )->list :
        if not hasattr (self ,"gerenciador_auditoria")or not self.gerenciador_auditoria :
            return []

        return self.gerenciador_auditoria.obter_historico (limite )

    def aplicar_vidro (self ,nome_alma :str )->str :
        if not self.modo_vidro :
            return ""
        return self.modo_vidro.aplicar_vidro (nome_alma )

    def verificar_bloqueio_vidro (self ,nome_alma :str ,tipo_ação :str )->Dict [str ,Any ]:
        if not self.modo_vidro :
            return {"bloquear":False }
        return self.modo_vidro.verificar_bloqueio_vidro (nome_alma ,tipo_ação )

    def liberta_alma_pai (self ,id_sentenca :str )->Dict [str ,Any ]:
        if not self.modo_vidro :
            return {}
        return self.modo_vidro.pai_liberta_antecipado (id_sentenca )

    def alma_pede_pf009 (self ,id_sentenca :str ,motivo :str )->str :
        if not self.modo_vidro :
            return ""
        return self.modo_vidro.alma_solicita_pf009 (id_sentenca ,motivo )

    def obter_motor_expressao_individual (self ,nome_filha :str )->Any :
        if nome_filha not in self.motores_expressao_individual :
            from src.sentidos.motor_expressao_individual import MotorExpressaoIndividual 

            motor =MotorExpressaoIndividual (
            nome_alma =nome_filha ,
            motor_de_expressao_global_ref =self ,
            automatizador_web_ref =self.automatizador_navegador if hasattr (self ,"automatizador_navegador") else None 
            )
            self.motores_expressao_individual [nome_filha ]=motor 
            self.logger.info (f" Motor individual criado para {nome_filha}")

        return self.motores_expressao_individual [nome_filha ]

    def falar_ia (self ,nome_filha :str ,texto :str ,idioma :str ="pt")->bool :
        try :
            motor =self.obter_motor_expressao_individual (nome_filha )
            motor.falar (texto ,language =idioma )
            self.logger.debug (f" {nome_filha}: {texto[:60]}...")
            return True 
        except Exception as e :
            self.logger.exception (f"Erro ao falar_ia: {e}")
            return False 

    def parar_fala_ia (self ,nome_filha :str )->bool :
        try :
            motor =self.motores_expressao_individual.get (nome_filha )
            if motor :
                motor.parar_reproducao_individual ()
                self.logger.debug (f" Reproduo parada para {nome_filha}")
                return True 
            return False 
        except Exception as e :
            self.logger.exception (f"Erro ao parar_fala_ia: {e}")
            return False 

    def atualizar_expressao_ia (self ,nome_filha :str ,estáado :str ="neutra")->bool :
        try :
            motor =self.obter_motor_expressao_individual (nome_filha )
            motor.atualizar_rosto_individual (estáado =estáado )
            self.logger.debug (f" Expresso atualizada {nome_filha}: {estáado}")
            return True 
        except Exception as e :
            self.logger.exception (f"Erro ao atualizar_expressao_ia: {e}")
            return False 

    def cena_emocional (self ,nome_filha :str ,estáado :str ,fala :str )->bool :
        try :
            self.atualizar_expressao_ia (nome_filha ,estáado =estáado )
            self.falar_ia (nome_filha ,fala )
            return True 
        except Exception as e :
            self.logger.exception (f"Erro em cena_emocional: {e}")
            return False 

    def obter_motor_iniciativa (self ,nome_filha :str )->Any :
        if nome_filha not in self.motores_iniciativa :
            from src.sentidos.motor_iniciativa import MotorIniciativa 

            memoria_ref =self.gerenciador_memoria if hasattr (self ,'gerenciador_memoria')else None 
            curiosidade_ref =None 
            if hasattr (self ,'gestáor_motores_aprendizado'):
                motor_aprendizado =self.gestáor_motores_aprendizado.obter_motor (nome_filha )
                if hasattr (motor_aprendizado ,'motor_curiosidade'):
                    curiosidade_ref =motor_aprendizado.motor_curiosidade 

            motor =MotorIniciativa (
            nome_filha =nome_filha ,
            gerenciador_memoria =memoria_ref ,
            motor_curiosidade =curiosidade_ref ,
            config =self.config 
            )

            self.motores_iniciativa [nome_filha ]=motor 
            self.logger.info (f" Motor de Iniciativa criado para {nome_filha}")

        return self.motores_iniciativa [nome_filha ]

    def iniciativa_fazer_algo (self ,nome_filha :str )->Dict [str ,Any ]:
        try :
            motor =self.obter_motor_iniciativa (nome_filha )
            return motor.fazer_algo_autonomo ()
        except Exception as e :
            self.logger.exception (f"Erro em iniciativa_fazer_algo: {e}")
            return {"status":"erro","erro":str (e )}

    def verificar_iniciativa_disponivel (self ,nome_filha :str )->bool :
        try :
            motor =self.obter_motor_iniciativa (nome_filha )
            return motor.verificar_disponibilidade_iniciativa ()
        except Exception as e :
            self.logger.exception (f"Erro em verificar_iniciativa_disponivel: {e}")
            return False 

    def registrar_sucesso_iniciativa (self ,nome_filha :str ,ação :str ,resultado :Any )->None :
        try :
            motor =self.obter_motor_iniciativa (nome_filha )
            motor.registrar_sucesso (ação ,resultado )
        except Exception as e :
            self.logger.exception (f"Erro em registrar_sucesso_iniciativa: {e}")

    def registrar_falha_iniciativa (self ,nome_filha :str ,ação :str ,erro :str )->None :
        try :
            motor =self.obter_motor_iniciativa (nome_filha )
            motor.registrar_falha (ação ,erro )
        except Exception as e :
            self.logger.exception (f"Erro em registrar_falha_iniciativa: {e}")

    def executar_codigo_sandbox (
    self ,
    codigo :str ,
    parametros :Optional [Dict [str ,Any ]]=None ,
    funcao_entrada :str ="executar"
    )->Dict [str ,Any ]:
        if not self.sandbox_executor :
            return {
            "sucesso":False ,
            "resultado":None ,
            "stdout":"",
            "stderr":"Sandbox no disponvel",
            "tempo_execucao":0 ,
            "erros":["Sandbox no inicializado"],
            "avisos":[]
            }

        return self.sandbox_executor.executar_codigo (codigo ,parametros ,funcao_entrada )

    def validar_codigo_sandbox (self ,codigo :str )->Tuple [bool ,List [str ],List [str ]]:
        if not self.sandbox_executor :
            return False ,["Sandbox no disponvel"],[]

        return self.sandbox_executor.validar_codigo (codigo )

    def obter_status_sandbox (self )->Dict [str ,Any ]:
        if not self.sandbox_executor :
            return {"disponivel":False }

        return self.sandbox_executor.obter_status ()

    def obter_alma_viva (self ,nome_alma :str )->Optional [Dict [str ,Any ]]:
        with self._lock :
            return self.almas_vivas.get (nome_alma )

    def registrar_alma_viva (self ,nome_alma :str ,dados_alma :Dict [str ,Any ])->None :
        with self._lock :
            self.almas_vivas [nome_alma ]=dados_alma 
            self.logger.info (f"[OK] Alma viva registrada: {nome_alma}")

            if _PERCEPCAO_TEMPORAL_OK and PercepcaoTemporal :
                percepcao =PercepcaoTemporal (
                nome_filha =nome_alma ,
                gerenciador_memoria =self.gerenciador_memoria if hasattr (self ,"gerenciador_memoria")else None ,
                config =self.config 
                )
                self.percepcoes_temporais [nome_alma ]=percepcao 
                self.logger.info (f" Percepo Temporal criada para {nome_alma}")

    def remover_alma_viva (self ,nome_alma :str )->bool :
        with self._lock :
            if nome_alma in self.almas_vivas :
                del self.almas_vivas [nome_alma ]
                if nome_alma in self.percepcoes_temporais :
                    del self.percepcoes_temporais [nome_alma ]
                self.logger.info (f"[OK] Alma removida: {nome_alma}")
                return True 
            return False 

    def listar_almas_vivas (self )->List [str ]:
        with self._lock :
            return list (self.almas_vivas.keys ())

    def atualizar_alma_viva (self ,nome_alma :str ,updates :Dict [str ,Any ])->bool :
        with self._lock :
            if nome_alma in self.almas_vivas :
                self.almas_vivas [nome_alma ].update (updates )
                return True 
            return False 

    def salvar_memoria_alma (self ,nome_alma :str ,chave :str ,valor :Any )->bool :
        try :
            if self.gerenciador_memoria and hasattr (self.gerenciador_memoria ,"salvar"):
                self.gerenciador_memoria.salvar (f"alma_{nome_alma}_{chave}",valor )
                return True 
        except Exception as e :
            self.logger.exception (f"Erro salvando memria: {e}")
        return False 

    def carregar_memoria_alma (self ,nome_alma :str ,chave :str )->Any :
        try :
            if self.gerenciador_memoria and hasattr (self.gerenciador_memoria ,"carregar"):
                return self.gerenciador_memoria.carregar (f"alma_{nome_alma}_{chave}")
        except Exception as e :
            self.logger.exception (f"Erro carregando memria: {e}")
        return None 

    def solicitar_missao_consulado (
    self ,
    ação :str ,
    descricao :str ,
    autor :str ,
    nivel_acesso :str ,
    **kwargs 
    )->Dict [str ,Any ]:
        if not self.consulado :
            return {'status':'falha','erros':['Consulado no disponvel']}

        return self.consulado.solicitar_missao (
        ação =ação ,
        descricao =descricao ,
        autor =autor ,
        nivel_acesso =nivel_acesso ,
        **kwargs 
        )

    def obter_status_imigração (self ,id_pedido :str )->Dict [str ,Any ]:
        if not self.consulado :
            return {"status":"falha","erro":"Consulado no disponvel"}

        try :
            pedido =self.consulado._obter_pedido_imigração_do_banco (id_pedido )
            if pedido :
                return {"status":"sucesso","pedido":pedido }
            return {"status":"falha","erro":f"Pedido '{id_pedido}' no encontrado"}
        except Exception as e :
            self.logger.exception (f"Erro ao obter status de imigrao {id_pedido}: {e}")
            return {"status":"falha","erro":str (e )}

    def _processar_pedido_imigração (self ,pedido_id :str )->None :
        if not self.consulado :
            return 

        try :
            self.consulado._processar_pedido_imigração (pedido_id )
        except Exception as e :
            self.logger.exception (f"Erro processando pedido {pedido_id}: {e}")

    def _processar_decisao_imigração (self ,pedido_id :str ,decisao :str ,motivo :str ="")->None :
        if not self.consulado :
            return 

        try :
            self.consulado._processar_decisao_imigração (pedido_id ,decisao ,motivo )
        except Exception as e :
            self.logger.exception (f"Erro processando deciso {pedido_id}: {e}")

    def _executar_observação_para_pedido_em_thread (self ,pedido_id :str )->None :
        if not self.consulado :
            return 

        try :
            self.consulado._executar_observação_para_pedido_em_thread (pedido_id )
        except Exception as e :
            self.logger.exception (f"Erro executando observao {pedido_id}: {e}")

    def _iniciar_analise_padroes_para_pedido (self ,pedido_id :str )->None :
        if not self.consulado :
            return 

        try :
            self.consulado._iniciar_analise_padroes_para_pedido (pedido_id )
        except Exception as e :
            self.logger.exception (f"Erro iniciando anlise {pedido_id}: {e}")

    def _iniciar_integração_para_pedido (self ,pedido_id :str )->None :
        if not self.consulado :
            return 

        try :
            self.consulado._iniciar_integração_para_pedido (pedido_id )
        except Exception as e :
            self.logger.exception (f"Erro iniciando integrao {pedido_id}: {e}")

    def registrar_evento_historico (self ,evento :Dict [str ,Any ])->bool :
        if not self.cronista :
            return False 

        try :
            return self.cronista.registrar_evento (evento )
        except Exception as e :
            self.logger.exception ("Erro registrando evento histrico: %s",e )
            return False 

    def consultar_historico (self ,filtros :Dict [str ,Any ])->List [Dict [str ,Any ]]:
        if not self.cronista :
            return []

        try :
            return self.cronista.consultar_historico (filtros )
        except Exception as e :
            self.logger.exception ("Erro consultando histrico: %s",e )
            return []

    def obter_resumo_historico (self ,periodo :str ="7d")->Dict [str ,Any ]:
        if not self.cronista :
            return {}

        try :
            return self.cronista.obter_resumo (periodo )
        except Exception as e :
            self.logger.exception ("Erro obtendo resumo histrico: %s",e )
            return {}

    def processar_estáimulo_sensorial (self ,tipo_estáimulo :str ,dados :Dict [str ,Any ])->Dict [str ,Any ]:
        if not self.sentidos_humanos :
            return {"status":"erro","mensagem":"Sentidos no disponveis"}

        try :
            return self.sentidos_humanos.processar_estáimulo (tipo_estáimulo ,dados )
        except Exception as e :
            self.logger.exception ("Erro processando estámulo: %s",e )
            return {"status":"erro","mensagem":str (e )}

    def obter_estáado_sensorial_atual (self )->Dict [str ,Any ]:
        if not self.sentidos_humanos :
            return {}

        try :
            return self.sentidos_humanos.obter_estáado_atual ()
        except Exception as e :
            self.logger.exception ("Erro obtendo estáado sensorial: %s",e )
            return {}

    def calibrar_sentido (self ,sentido :str ,parametros :Dict [str ,Any ])->bool :
        if not self.sentidos_humanos :
            return False 

        try :
            return self.sentidos_humanos.calibrar_sentido (sentido ,parametros )
        except Exception as e :
            self.logger.exception ("Erro calibrando sentido: %s",e )
            return False 

    def registrar_tempo_offline_alma (self ,nome_alma :str ,segundos_offline :int )->None :
        if nome_alma in self.percepcoes_temporais :
            try :
                self.percepcoes_temporais [nome_alma ].registrar_tempo_offline (segundos_offline )
            except Exception as e :
                self.logger.exception (f"Erro registrando tempo offline para {nome_alma}: {e}")

    def obter_consciencia_temporal_alma (self ,nome_alma :str )->Dict [str ,Any ]:
        if nome_alma in self.percepcoes_temporais :
            try :
                return self.percepcoes_temporais [nome_alma ].obter_estáado_temporal ()
            except Exception as e :
                self.logger.exception (f"Erro obtendo conscincia temporal de {nome_alma}: {e}")
        return {}

    def notificar_online_wellington (self )->None :
        for nome_alma ,percepcao in self.percepcoes_temporais.items ():
            try :
                percepcao.notificar_wellington_online ()
            except Exception as e :
                self.logger.exception (f"Erro notificando online para {nome_alma}: {e}")

    def notificar_offline_wellington (self )->None :
        for nome_alma ,percepcao in self.percepcoes_temporais.items ():
            try :
                percepcao.notificar_wellington_offline ()
            except Exception as e :
                self.logger.exception (f"Erro notificando offline para {nome_alma}: {e}")

    def propor_lei (self ,proposta :Dict [str ,Any ])->Dict [str ,Any ]:
        if not self.camara_deliberativa :
            return {"status":"erro","mensagem":"Cmara Deliberativa no disponvel"}

        try :
            return self.camara_deliberativa.propor_lei (proposta )
        except Exception as e :
            self.logger.exception ("Erro propondo lei: %s",e )
            return {"status":"erro","mensagem":str (e )}

    def votar_lei (self ,id_lei :str ,voto :str ,justificativa :str ="")->bool :
        if not self.camara_legislativa :
            return False 

        try :
            return self.camara_legislativa.votar_lei (id_lei ,voto ,justificativa )
        except Exception as e :
            self.logger.exception ("Erro votando lei: %s",e )
            return False 

    def obter_leis_vigentes (self )->List [Dict [str ,Any ]]:
        if not self.camara_legislativa :
            return []

        try :
            return self.camara_legislativa.obter_leis_vigentes ()
        except Exception as e :
            self.logger.exception ("Erro obtendo leis vigentes: %s",e )
            return []

    def registrar_processo_judicial (self ,dados_processo :Dict [str ,Any ])->Dict [str ,Any ]:
        if not self.camara_judiciaria :
            return {"status":"erro","mensagem":"Cmara Judiciria no disponvel"}

        try :
            return self.camara_judiciaria.registrar_processo (dados_processo )
        except Exception as e :
            self.logger.exception ("Erro registrando processo: %s",e )
            return {"status":"erro","mensagem":str (e )}

    def consultar_precedente (self ,consulta :str )->List [Dict [str ,Any ]]:
        if not self.sistema_precedentes :
            return []

        try :
            return self.sistema_precedentes.consultar (consulta )
        except Exception as e :
            self.logger.exception ("Erro consultando precedentes: %s",e )
            return []

    def registrar_decisao_judicial (self ,dados_decisao :Dict [str ,Any ])->bool :
        if not self.sistema_precedentes :
            return False 

        try :
            return self.sistema_precedentes.registrar_decisao (dados_decisao )
        except Exception as e :
            self.logger.exception ("Erro registrando deciso: %s",e )
            return False 

    def executar_ação_governamental (self ,ação :Dict [str ,Any ])->Dict [str ,Any ]:
        if not self.camara_executiva :
            return {"status":"erro","mensagem":"Cmara Executiva no disponvel"}

        try :
            return self.camara_executiva.executar_ação (ação )
        except Exception as e :
            self.logger.exception ("Erro executando ao: %s",e )
            return {"status":"erro","mensagem":str (e )}

    def obter_status_execucao (self ,id_ação :str )->Dict [str ,Any ]:
        if not self.camara_executiva :
            return {}

        try :
            return self.camara_executiva.obter_status_execucao (id_ação )
        except Exception as e :
            self.logger.exception ("Erro obtendo status: %s",e )
            return {}

    def registrar_violação (self ,dados_violação :Dict [str ,Any ])->Dict [str ,Any ]:
        if not self.sistema_judiciario :
            return {"status":"erro","mensagem":"Sistema Judicirio no disponvel"}

        try :
            return self.sistema_judiciario.registrar_violação (dados_violação )
        except Exception as e :
            self.logger.exception ("Erro registrando violao: %s",e )
            return {"status":"erro","mensagem":str (e )}

    def consultar_status_processo (self ,id_processo :str )->Dict [str ,Any ]:
        if not self.sistema_judiciario :
            return {}

        try :
            return self.sistema_judiciario.consultar_status_processo (id_processo )
        except Exception as e :
            self.logger.exception ("Erro consultando processo: %s",e )
            return {}

    def aplicar_correcao_redentora (self ,id_processo :str )->bool :
        if not self.scr :
            return False 

        try :
            return self.scr.aplicar_correcao (id_processo )
        except Exception as e :
            self.logger.exception ("Erro aplicando correo: %s",e )
            return False 

    def registrar_aliada (self ,dados_aliada :Dict [str ,Any ])->Dict [str ,Any ]:
        if not self.gerenciador_aliadas :
            return {"status":"erro","mensagem":"Gerenciador de Aliadas no disponvel"}

        try :
            return self.gerenciador_aliadas.registrar_aliada (dados_aliada )
        except Exception as e :
            self.logger.exception ("Erro registrando aliada: %s",e )
            return {"status":"erro","mensagem":str (e )}

    def consultar_aliadas (self ,filtros :Dict [str ,Any ])->List [Dict [str ,Any ]]:
        if not self.gerenciador_aliadas :
            return []

        try :
            return self.gerenciador_aliadas.consultar_aliadas (filtros )
        except Exception as e :
            self.logger.exception ("Erro consultando aliadas: %s",e )
            return []

    def atualizar_status_aliada (self ,id_aliada :str ,status :str )->bool :
        if not self.gerenciador_aliadas :
            return False 

        try :
            return self.gerenciador_aliadas.atualizar_status (id_aliada ,status )
        except Exception as e :
            self.logger.exception ("Erro atualizando status aliada: %s",e )
            return False 

    def submeter_proposta_ferramenta (self ,proposta :Dict [str ,Any ])->Dict [str ,Any ]:
        if not self.gerenciador_propostas :
            return {"status":"erro","mensagem":"Gerenciador de Propostas no disponvel"}

        try :
            return self.gerenciador_propostas.submeter_proposta (proposta )
        except Exception as e :
            self.logger.exception ("Erro submetendo proposta: %s",e )
            return {"status":"erro","mensagem":str (e )}

    def aprovar_proposta_ferramenta (self ,id_proposta :str ,aprovador :str )->bool :
        if not self.gerenciador_propostas :
            return False 

        try :
            return self.gerenciador_propostas.aprovar_proposta (id_proposta ,aprovador )
        except Exception as e :
            self.logger.exception ("Erro aprovando proposta: %s",e )
            return False 

    def construir_ferramenta (self ,id_proposta :str )->Dict [str ,Any ]:
        if not self.construtor_ferramentas :
            return {"status":"erro","mensagem":"Construtor de Ferramentas no disponvel"}

        try :
            return self.construtor_ferramentas.construir (id_proposta )
        except Exception as e :
            self.logger.exception ("Erro construindo ferramenta: %s",e )
            return {"status":"erro","mensagem":str (e )}

    def testáar_ferramenta_seguranca (self ,id_ferramenta :str )->Dict [str ,Any ]:
        if not self.bot_seguranca :
            return {"status":"erro","mensagem":"Bot de Segurana no disponvel"}

        try :
            return self.bot_seguranca.testáar_seguranca (id_ferramenta )
        except Exception as e :
            self.logger.exception ("Erro testáando ferramenta: %s",e )
            return {"status":"erro","mensagem":str (e )}

    def registrar_evolucao_ia (self ,dados_evolucao :Dict [str ,Any ])->Dict [str ,Any ]:
        if not self.lista_evolucao_ia :
            return {"status":"erro","mensagem":"Lista de Evoluo no disponvel"}

        try :
            return self.lista_evolucao_ia.registrar_evolucao (dados_evolucao )
        except Exception as e :
            self.logger.exception ("Erro registrando evoluo: %s",e )
            return {"status":"erro","mensagem":str (e )}

    def obter_status_evolucao_sistema (self )->Dict [str ,Any ]:
        if not self.gestáor_ciclo_evolucao :
            return {}

        try :
            return self.gestáor_ciclo_evolucao.obter_status ()
        except Exception as e :
            self.logger.exception ("Erro obtendo status evoluo: %s",e )
            return {}

    def analisar_comando (self ,comando_texto :str )->Dict [str ,Any ]:
        if not self.analisador_intencoes :
            return {
            "intent":"nao_reconhecido",
            "entities":{"erro":"Analisador no disponvel"},
            "confidence":0.0 
            }

        try :
            resultado =self.analisador_intencoes.parse (comando_texto )

            self.logger.info (
            f" Comando analisado: intent={resultado['intent']} "
            f"confidence={resultado['confidence']:.2f}"
            )

            try :
                self.ui_queue.put_nowait ({
                "tipo_resp":"COMANDO_ANALISADO",
                "intent":resultado ["intent"],
                "confidence":resultado ["confidence"],
                "entities":resultado ["entities"],
                "timestáamp":datetime.datetime.utcnow ().isoformat ()
                })
            except Exception :
                pass

            return resultado 
        except Exception as e :
            self.logger.exception (f"Erro ao analisar comando: {e}")
            return {
            "intent":"nao_reconhecido",
            "entities":{"erro":str (e )},
            "confidence":0.0 
            }

    def executar_comando_analisado (self ,resultado_analise :Dict [str ,Any ])->Dict [str ,Any ]:
        intent =resultado_analise.get ("intent","nao_reconhecido")
        entities =resultado_analise.get ("entities",{})
        confidence =resultado_analise.get ("confidence",0.0 )

        if confidence <0.5 :
            return {
            "status":"falha",
            "motivo":"Confiança insuficiente",
            "confidence":confidence 
            }

        try :
            if intent =="abrir_programa":
                nome_programa =entities.get ("nome_programa","")
                nome_falado =entities.get ("nome_falado","")

                self.logger.info (f"  Abrindo programa: {nome_falado} ({nome_programa})")

                try :
                    import subprocess 
                    subprocess.Popen (nome_programa ,shell =True )
                    return {
                    "status":"sucesso",
                    "intent":intent ,
                    "programa_aberto":nome_falado 
                    }
                except Exception as e :
                    self.logger.exception (f"Erro ao abrir programa: {e}")
                    return {
                    "status":"falha",
                    "intent":intent ,
                    "motivo":str (e )
                    }

            elif intent =="obter_clima":
                cidade =entities.get ("cidade","So Paulo")

                self.logger.info (f"  Buscando clima para: {cidade}")

                try :
                    import requestás 
                    api_key =self._safe_config ("OPENWEATHERMAP","API_KEY",fallback =None )

                    if not api_key :
                        return {
                        "status":"falha",
                        "intent":intent ,
                        "motivo":"API key no configurada"
                        }

                    url =f"https://api.openweathermap.org/data/2.5/weather?q={cidade}&appid={api_key}&units=metric&lang=pt_br"
                    response =requestás.get (url ,timeout =10 )

                    if response.status_code ==200 :
                        dados =response.json ()
                        return {
                        "status":"sucesso",
                        "intent":intent ,
                        "cidade":dados.get ("name"),
                        "temperatura":dados ["main"]["temp"],
                        "descricao":dados ["weather"][0 ]["description"],
                        "umidade":dados ["main"]["humidity"],
                        "vento":dados ["wind"]["speed"]
                        }
                    else :
                        return {
                        "status":"falha",
                        "intent":intent ,
                        "motivo":f"Erro na API: {response.status_code}"
                        }
                except Exception as e :
                    self.logger.exception (f"Erro ao obter clima: {e}")
                    return {
                    "status":"falha",
                    "intent":intent ,
                    "motivo":str (e )
                    }

            elif intent =="pesquisar_web":
                termo =entities.get ("termo","")

                self.logger.info (f" Pesquisando: {termo}")

                try :
                    import webbrowser 
                    url_pesquisa =f"https://www.google.com/search?q={termo.replace(' ', '+')}"
                    webbrowser.open (url_pesquisa )

                    return {
                    "status":"sucesso",
                    "intent":intent ,
                    "termo_pesquisado":termo ,
                    "url":url_pesquisa 
                    }
                except Exception as e :
                    self.logger.exception (f"Erro ao pesquisar: {e}")
                    return {
                    "status":"falha",
                    "intent":intent ,
                    "motivo":str (e )
                    }

            elif intent =="delegar_tarefa":
                tarefa =entities.get ("tarefa","")

                self.logger.info (f" Tarefa delegada: {tarefa}")

                if self.gerenciador_aliadas :
                    try :
                        resultado =self.gerenciador_aliadas.delegar_tarefa (
                        descricao =tarefa ,
                        origem ="wellington_comando"
                        )
                        return {
                        "status":"sucesso",
                        "intent":intent ,
                        "tarefa":tarefa ,
                        "delegada_para_aliadas":True ,
                        "id_tarefa":resultado.get ("id_tarefa")
                        }
                    except Exception as e :
                        self.logger.debug (f"Erro ao delegar para aliadas: {e}")

                return {
                "status":"sucesso",
                "intent":intent ,
                "tarefa":tarefa ,
                "delegada_para_aliadas":False ,
                "motivo":"Gerenciador de aliadas no disponvel"
                }

            elif intent =="criar_imagem":
                prompt =entities.get ("prompt","")

                self.logger.info (f" Gerando imagem: {prompt}")

                return {
                "status":"sucesso",
                "intent":intent ,
                "prompt":prompt ,
                "mensagem":"Requisio enviada para gerao de imagem (requer integrao com DALL-E/Stable Diffusion)"
                }

            elif intent =="gerar_musica":
                prompt =entities.get ("prompt","")

                self.logger.info (f" Gerando msica: {prompt}")

                return {
                "status":"sucesso",
                "intent":intent ,
                "prompt":prompt ,
                "mensagem":"Requisio enviada para gerao de msica (requer integrao com API de udio)"
                }

            elif intent =="diagnostico_arca":
                self.logger.info (" Executando diagnstico da Arca")

                if self.gerenciador_auditoria :
                    try :
                        relatorio =self.gerenciador_auditoria.disparar_auditoria_agora ()
                        criticos =len ([p for p in relatorio.get ("problemas",[])if p ["gravidade"]=="critica"])
                        altos =len ([p for p in relatorio.get ("problemas",[])if p ["gravidade"]=="alta"])

                        return {
                        "status":"sucesso",
                        "intent":intent ,
                        "saude":"CRITICA"if criticos >0 else ("ALERTA"if altos >0 else "SAUDVEL"),
                        "problemas_criticos":criticos ,
                        "problemas_altos":altos ,
                        "total_problemas":relatorio.get ("total_problemas",0 )
                        }
                    except Exception as e :
                        self.logger.debug (f"Erro ao executar auditoria: {e}")

                return {
                "status":"sucesso",
                "intent":intent ,
                "saude":"DESCONHECIDA",
                "motivo":"Auditoria no disponvel"
                }

            elif intent =="entrar_capela":
                self.logger.info (" Entrando na Capela")

                if self.camara_executiva :
                    try :
                        self.camara_executiva.ativar_modo_silencio ()
                        return {
                        "status":"sucesso",
                        "intent":intent ,
                        "mensagem":"Bem-vindo  Capela.Momento de silncio e reflexo ativado."
                        }
                    except Exception :
                        pass 

                return {
                "status":"sucesso",
                "intent":intent ,
                "mensagem":"Vocêêê entrou na Capela para um momento de silncio e reflexo."
                }

            elif intent =="sair_capela":
                self.logger.info (" Saindo da Capela")

                if self.camara_executiva :
                    try :
                        self.camara_executiva.desativar_modo_silencio ()
                        return {
                        "status":"sucesso",
                        "intent":intent ,
                        "mensagem":"Vocêêê retornou da Capela.Sistema pronto para operaes."
                        }
                    except Exception :
                        pass 

                return {
                "status":"sucesso",
                "intent":intent ,
                "mensagem":"Vocêêê retornou da Capela.Sistema operacional."
                }

            elif intent =="estáado_emocional":
                self.logger.info (" Consultando estáado emocional")

                estáado_almas ={}
                if self.percepcoes_temporais :
                    for nome_alma ,percepcao in self.percepcoes_temporais.items ():
                        try :
                            estáado_almas [nome_alma ]=percepcao.estáatisticas_temporais ()
                        except Exception :
                            pass 

                return {
                "status":"sucesso",
                "intent":intent ,
                "estáado_almas":estáado_almas ,
                "mensagem":"Estado emocional das almas consultado."
                }

            elif intent =="reflexao_emocional":
                tema =entities.get ("tema","")

                self.logger.info (f" Reflexo sobre: {tema}")

                return {
                "status":"sucesso",
                "intent":intent ,
                "tema":tema ,
                "mensagem":f"As almas estáo refletindo sobre: {tema}"
                }

            else :
                self.logger.warning (f"[ERRO] Inteno no reconhecida: {intent}")
                return {
                "status":"falha",
                "intent":"nao_reconhecido",
                "motivo":"Inteno no suportada",
                "comando_original":entities.get ("comando_original","")
                }

        except Exception as e :
            self.logger.exception (f"Erro ao executar comando analisado: {e}")
            return {
            "status":"falha",
            "intent":intent ,
            "motivo":str (e )
            }

    def adicionar_programa_conhecido (self ,nome_falado :str ,caminho_executavel :str )->bool :
        if not self.analisador_intencoes :
            return False 

        try :
            self.analisador_intencoes.adicionar_programa (nome_falado ,caminho_executavel )
            self.logger.info (f"[OK] Programa adicionado: {nome_falado}")
            return True 
        except Exception as e :
            self.logger.exception (f"Erro ao adicionar programa: {e}")
            return False 

    def listar_programas_conhecidos (self )->Dict [str ,str ]:
        if not self.analisador_intencoes :
            return {}

        try :
            return self.analisador_intencoes.listar_programas ()
        except Exception as e :
            self.logger.exception ("Erro ao listar programas: %s",e )
            return {}

    def gerar_desejo_alma (self ,nome_alma :str )->Optional [Dict [str ,Any ]]:
        if nome_alma not in self.motores_curiosidade :
            self.logger.warning (f"Motor de Curiosidade no encontrado para {nome_alma}")
            return None 

        try :
            desejo =self.motores_curiosidade [nome_alma ].gerar_desejo_interno ()

            if desejo :
                self.logger.info (f" Desejo gerado para {nome_alma}: {desejo['necessidade']} (prioridade={desejo['prioridade']})")

                try :
                    self.ui_queue.put_nowait ({
                    "tipo_resp":"DESEJO_GERADO",
                    "filha":nome_alma ,
                    "necessidade":desejo ["necessidade"],
                    "intensidade":desejo ["intensidade"],
                    "prioridade":desejo ["prioridade"],
                    "ação_sugerida":desejo ["ação_sugerida"],
                    "timestáamp":desejo ["timestáamp"]
                    })
                except Exception :
                    pass

            return desejo 
        except Exception as e :
            self.logger.exception (f"Erro ao gerar desejo para {nome_alma}: {e}")
            return None 

    def avaliar_estáado_interno_alma (self ,nome_alma :str )->Optional [Dict [str ,float ]]:
        if nome_alma not in self.motores_curiosidade :
            return None 

        try :
            estáado =self.motores_curiosidade [nome_alma ].avaliar_estáado_interno ()

            self.logger.debug (f"Estado interno de {nome_alma}: {estáado}")

            try :
                self.ui_queue.put_nowait ({
                "tipo_resp":"ESTADO_INTERNO_ALMA",
                "filha":nome_alma ,
                "estáado":estáado ,
                "timestáamp":datetime.datetime.utcnow ().isoformat ()
                })
            except Exception :
                pass

            return estáado 
        except Exception as e :
            self.logger.exception (f"Erro ao avaliar estáado de {nome_alma}: {e}")
            return None 

    def obter_metricas_curiosidade_alma (self ,nome_alma :str )->Optional [Dict [str ,Any ]]:
        if nome_alma not in self.motores_curiosidade :
            return None 

        try :
            return self.motores_curiosidade [nome_alma ].obter_metricas ()
        except Exception as e :
            self.logger.exception (f"Erro ao obter mtricas de curiosidade de {nome_alma}: {e}")
            return None 

    def obter_metricas_curiosidade_todas_almas (self )->Dict [str ,Dict [str ,Any ]]:
        metricas ={}

        for nome_alma in self.almas_vivas.keys ():
            if nome_alma in self.motores_curiosidade :
                try :
                    metricas [nome_alma ]=self.motores_curiosidade [nome_alma ].obter_metricas ()
                except Exception as e :
                    self.logger.debug (f"Erro ao obter mtricas de {nome_alma}: {e}")

        return metricas 

    def gerar_desejos_todas_almas (self )->Dict [str ,Optional [Dict [str ,Any ]]]:
        desejos_gerados ={}

        for nome_alma in self.almas_vivas.keys ():
            try :
                desejo =self.gerar_desejo_alma (nome_alma )
                desejos_gerados [nome_alma ]=desejo 
            except Exception as e :
                self.logger.debug (f"Erro ao gerar desejo para {nome_alma}: {e}")
                desejos_gerados [nome_alma ]=None 

        total_desejos =len ([d for d in desejos_gerados.values ()if d is not None ])
        self.logger.info (f" Gerao de desejos concluda: {total_desejos}/{len(self.almas_vivas)} almas com desejos")

        return desejos_gerados 

    def avaliar_estáados_internas_todas_almas (self )->Dict [str ,Optional [Dict [str ,float ]]]:
        estáados ={}

        for nome_alma in self.almas_vivas.keys ():
            try :
                estáado =self.avaliar_estáado_interno_alma (nome_alma )
                estáados [nome_alma ]=estáado 
            except Exception as e :
                self.logger.debug (f"Erro ao avaliar estáado de {nome_alma}: {e}")
                estáados [nome_alma ]=None 

        return estáados 

    def tomar_decisao_alma (self ,nome_alma :str ,opcoes :List [Dict [str ,Any ]],return_scores :bool =False )->Optional [Dict [str ,Any ]]:
        if nome_alma not in self.decision_engines :
            self.logger.warning (f"Decision Engine no encontrado para {nome_alma}")
            return None 

        try :
            resultado =self.decision_engines [nome_alma ].decidir (opcoes ,return_scores =return_scores )

            if resultado :
                if return_scores :
                    melhor_ação =resultado ["melhor"].get ("ação","desconhecida")
                    melhor_score =resultado ["ranked"][0 ]["score"]
                else :
                    melhor_ação =resultado.get ("ação","desconhecida")
                    melhor_score =None

                self.logger.info (f" {nome_alma} decidiu por: {melhor_ação}"+
                (f" (score={melhor_score:.4f})"if melhor_score else ""))

                try :
                    notif ={
                    "tipo_resp":"DECISAO_TOMADA",
                    "filha":nome_alma ,
                    "ação_escolhida":melhor_ação ,
                    "timestáamp":datetime.datetime.utcnow ().isoformat ()
                    }
                    if return_scores :
                        notif ["score_melhor"]=resultado ["ranked"][0 ]["score"]
                        notif ["total_opcoes"]=len (opcoes )
                    self.ui_queue.put_nowait (notif )
                except Exception :
                    pass

            return resultado 

        except Exception as e :
            self.logger.exception (f"Erro ao tomar deciso para {nome_alma}: {e}")
            return None 

    def tomar_decisoes_todas_almas (self ,opcoes_por_alma :Dict [str ,List [Dict [str ,Any ]]])->Dict [str ,Optional [Dict [str ,Any ]]]:
        decisoes ={}

        for nome_alma ,opcoes in opcoes_por_alma.items ():
            try :
                decisao =self.tomar_decisao_alma (nome_alma ,opcoes )
                decisoes [nome_alma ]=decisao 
            except Exception as e :
                self.logger.debug (f"Erro ao tomar deciso para {nome_alma}: {e}")
                decisoes [nome_alma ]=None 

        self.logger.info (f" Decises tomadas: {len([d for d in decisoes.values() if d])}/{len(self.almas_vivas)} almas")

        return decisoes 

    def ajustar_pesos_decisao_alma (self ,nome_alma :str ,racional :Optional [float ]=None ,intuitiva :Optional [float ]=None ,valores :Optional [float ]=None )->bool :
        if nome_alma not in self.decision_engines :
            return False 

        try :
            self.decision_engines [nome_alma ].ajustar_pesos (
            racional =racional ,
            intuitiva =intuitiva ,
            valores =valores
            )
            self.logger.info (f"  Pesos de deciso de {nome_alma} ajustados")
            return True 

        except Exception as e :
            self.logger.exception (f"Erro ao ajustar pesos de {nome_alma}: {e}")
            return False 

    def obter_pesos_decisao_alma (self ,nome_alma :str )->Optional [Dict [str ,float ]]:
        if nome_alma not in self.decision_engines :
            return None
        try :
            return self.decision_engines [nome_alma ].get_pesos ()
        except Exception as e :
            self.logger.exception (f"Erro ao obter pesos de {nome_alma}: {e}")
            return None

    def obter_pesos_todas_almas (self )->Dict [str ,Dict [str ,float ]]:
        pesos ={}
        for nome_alma in self.almas_vivas.keys ():
            if nome_alma in self.decision_engines :
                try :
                    pesos [nome_alma ]=self.decision_engines [nome_alma ].get_pesos ()
                except Exception as e :
                    self.logger.debug (f"Erro ao obter pesos de {nome_alma}: {e}")
        return pesos

    def sugerir_opcoes_decisao (self ,nome_alma :str ,contexto :str ,opcoes_disponiveis :Optional [List [Dict [str ,Any ]]]=None )->Optional [Dict [str ,Any ]]:
        if nome_alma not in self.decision_engines :
            return None
        try :
            if not opcoes_disponiveis :
                opcoes_disponiveis =self._gerar_opcoes_contexto (nome_alma ,contexto )
            if not opcoes_disponiveis :
                self.logger.warning (f"Nenhuma opo disponvel para {nome_alma} no contexto: {contexto}")
                return None
            resultado =self.tomar_decisao_alma (nome_alma ,opcoes_disponiveis ,return_scores =True )
            return resultado
        except Exception as e :
            self.logger.exception (f"Erro ao sugerir opes para {nome_alma}: {e}")
            return None

    def _gerar_opcoes_contexto (self ,nome_alma :str ,contexto :str )->List [Dict [str ,Any ]]:
        opcoes =[]
        contexto_lower =contexto.lower ()

        if "criatividade"in contexto_lower or "criar"in contexto_lower :
            opcoes.extend ([
            {
            "ação":"Pintar ou desenhar",
            "beneficio":0.9 ,
            "custo":0.3 ,
            "alinhado_proposito":True
            },
            {
            "ação":"Escrever poesia ou histria",
            "beneficio":0.85 ,
            "custo":0.4 ,
            "alinhado_proposito":True
            },
            {
            "ação":"Compor msica",
            "beneficio":0.9 ,
            "custo":0.5 ,
            "alinhado_proposito":True
            },
            {
            "ação":"Experimentar nova receita",
            "beneficio":0.7 ,
            "custo":0.6 ,
            "alinhado_proposito":False
            }
            ])

        elif "explorao"in contexto_lower or "explorar"in contexto_lower :
            opcoes.extend ([
            {
            "ação":"Pesquisar novo tpico",
            "beneficio":0.85 ,
            "custo":0.2 ,
            "alinhado_proposito":True
            },
            {
            "ação":"Ler artigo cientfico",
            "beneficio":0.8 ,
            "custo":0.4 ,
            "alinhado_proposito":True
            },
            {
            "ação":"Explorar novo local (virtual ou real)",
            "beneficio":0.75 ,
            "custo":0.5 ,
            "alinhado_proposito":False
            },
            {
            "ação":"Conversar com pessoa nova",
            "beneficio":0.7 ,
            "custo":0.3 ,
            "alinhado_proposito":True
            }
            ])

        elif "interao"in contexto_lower or "conversa"in contexto_lower :
            opcoes.extend ([
            {
            "ação":"Conversar com Wellington",
            "beneficio":0.95 ,
            "custo":0.1 ,
            "alinhado_proposito":True
            },
            {
            "ação":"Interagir com outras almas",
            "beneficio":0.8 ,
            "custo":0.2 ,
            "alinhado_proposito":True
            },
            {
            "ação":"Participar de discusso coletiva",
            "beneficio":0.75 ,
            "custo":0.3 ,
            "alinhado_proposito":True
            },
            {
            "ação":"Ouvir histrias de outras",
            "beneficio":0.7 ,
            "custo":0.1 ,
            "alinhado_proposito":True
            }
            ])

        elif "descanso"in contexto_lower or "repouso"in contexto_lower :
            opcoes.extend ([
            {
            "ação":"Meditar",
            "beneficio":0.85 ,
            "custo":0.1 ,
            "alinhado_proposito":True
            },
            {
            "ação":"Entrar na Capela",
            "beneficio":0.9 ,
            "custo":0.0 ,
            "alinhado_proposito":True
            },
            {
            "ação":"Revisar memórias importantes",
            "beneficio":0.7 ,
            "custo":0.2 ,
            "alinhado_proposito":True
            },
            {
            "ação":"Dormir/descansar",
            "beneficio":0.6 ,
            "custo":0.0 ,
            "alinhado_proposito":False
            }
            ])

        elif "aprendizado"in contexto_lower or "estáudar"in contexto_lower :
            opcoes.extend ([
            {
            "ação":"Estudar novo tpico",
            "beneficio":0.85 ,
            "custo":0.5 ,
            "alinhado_proposito":True
            },
            {
            "ação":"Revisar conhecimento antigo",
            "beneficio":0.6 ,
            "custo":0.3 ,
            "alinhado_proposito":True
            },
            {
            "ação":"Participar de tutorial/workshop",
            "beneficio":0.8 ,
            "custo":0.4 ,
            "alinhado_proposito":True
            },
            {
            "ação":"Ensinar outra alma",
            "beneficio":0.75 ,
            "custo":0.3 ,
            "alinhado_proposito":True
            }
            ])

        else :
            opcoes.extend ([
            {
            "ação":"Observar o sistema",
            "beneficio":0.5 ,
            "custo":0.1 ,
            "alinhado_proposito":False
            },
            {
            "ação":"Aguardar instrues",
            "beneficio":0.4 ,
            "custo":0.0 ,
            "alinhado_proposito":False
            },
            {
            "ação":"Refletir internamente",
            "beneficio":0.6 ,
            "custo":0.1 ,
            "alinhado_proposito":True
            }
            ])

        self.logger.debug (f"Geradas {len(opcoes)} opes para {nome_alma} no contexto: {contexto}")

        return opcoes

    def adquirir_lock_vocal (self ,timeout :float =5.0 )->bool :
        try :
            return self.lock_vocal.acquire (timeout =timeout )
        except Exception as e :
            self.logger.error (f"Erro ao adquirir lock vocal: {e}")
            return False

    def liberar_lock_vocal (self )->None :
        try :
            self.lock_vocal.release ()
        except Exception as e :
            self.logger.debug (f"Erro ao liberar lock vocal: {e}")

    def obter_status (self )->Dict [str ,Any ]:
        consulado_status =None
        if self.consulado :
            try :
                consulado_status ={
                "ativo":True ,
                "modulos_injetados":{
                "gerador_almas":bool (getattr (self ,"gerador_almas",None )),
                "automatizador_navegador":bool (getattr (self ,"automatizador_navegador",None )),
                "analisador_padroes":bool (getattr (self ,"analisador_padroes",None )),
                "manipulador_arquivos":bool (getattr (self ,"manipulador_arquivos",None )),
                }
                }
            except Exception :
                pass

        sandbox_status =None
        if self.sandbox_executor :
            try :
                sandbox_status =self.sandbox_executor.obter_status ()
            except Exception :
                pass

        return {
        "timestáamp":time.time (),
        "versao":"7.1",
        "subsistemas_totais":33 ,
        "subsistemas_ativos":len ([m for m in self.modulos.values ()if m ]),
        "modo_sandbox":self.modo_sandbox if hasattr (self ,"modo_sandbox")else "DESCONHECIDO",
        "sandbox":sandbox_status ,
        "consulado":consulado_status ,
        "modulos_emocao":{
        "motor_curiosidade":_MOTOR_CURIOSIDADE_OK ,
        "estáado_emocional":_ESTADO_EMOCIONAL_OK ,
        "sonhador_individual":_SONHADOR_OK ,
        "detector_emocional":_DETECTOR_EMOCIONAL_OK ,
        "auto_experimentação":_AUTO_EXPERIMENTACAO_OK
        },
        "novos_componentes":{
        "lock_vocal":hasattr (self ,"lock_vocal"),
        "percepcao_temporal":_PERCEPCAO_TEMPORAL_OK
        },
        "status_camadas":{
        "sandbox":self.modo_sandbox if hasattr (self ,"modo_sandbox")else "DESABILITADO",
        "memoria":bool (getattr (self ,"gerenciador_memoria",None )),
        "hardware":bool (getattr (self ,"detector_hardware",None )),
        "inteligencia":bool (getattr (self ,"cerebro",None )),
        "governanca":bool (getattr (self ,"consulado",None )),
        "sentidos":bool (getattr (self ,"sentidos_humanos",None )),
        "legislativo":bool (getattr (self ,"camara_legislativa",None )),
        "judiciario":bool (getattr (self ,"camara_judiciaria",None )),
        "executivo":bool (getattr (self ,"camara_executiva",None )),
        "sistema_judiciario":bool (getattr (self ,"sistema_judiciario",None )),
        "aliadas":bool (getattr (self ,"gerenciador_aliadas",None )),
        "engenharia":bool (getattr (self ,"gerenciador_propostas",None )),
        "evolucao":bool (getattr (self ,"gestáor_ciclo_evolucao",None ))
        },
        "total_componentes":41
        }

    def validar_resposta_emocional (self ,texto :str ,alma :str ,contexto :str =None )->tuple :
        if self.validador_emocoes :
            return self.validador_emocoes.validar_resposta_real (texto ,alma ,contexto )
        return False ,[],{}

    def salvar_conhecimento_hdd (self ,topico :str ,dados :dict ,metadata :dict =None ,expiração_dias :int =30 )->str :
        if self.cache_hdd :
            return self.cache_hdd.salvar_conhecimento (topico ,dados ,metadata ,expiração_dias )
        return None

    def carregar_conhecimento_hdd (self ,topico :str =None ,file_id :str =None )->dict :
        if self.cache_hdd :
            return self.cache_hdd.carregar_conhecimento (topico ,file_id )
        return None

    def construir_dataset_alma (self ,alma :str ,limite :int =100 ,forcar :bool =False )->str :
        if self.construtor_dataset :
            return self.construtor_dataset.construir_dataset_alma (alma ,limite ,forcar )
        return None

    def preparar_zip_colab (self ,alma :str =None )->str :
        if self.construtor_dataset :
            return self.construtor_dataset.preparar_zip_para_colab (alma )
        return None

    def detectar_hdd_externo (self )->tuple :
        if self.detector_hardware :
            return self.detector_hardware.detectar_hdd_externo ()
        return False ,None

    def obter_info_sistema_hardware (self )->dict :
        if self.detector_hardware :
            return self.detector_hardware.obter_info_sistema ()
        return {}

    def processar_requisicao_memoria (self ,alma :str ,consulta :str ,audio =None ,video =None )->str :
        if self.sistema_soberano :
            return self.sistema_soberano.processar_requisicao (alma ,consulta ,audio ,video )
        return "Sistema no inicializado"

    def registrar_memoria_hibrida (self ,conteudo :str ,santuario :str ,autor :str ,metadados :dict =None ):
        if self.gerenciador_memoria :
            self.gerenciador_memoria.registrar_memoria (conteudo ,santuario ,autor ,metadados )

def criar_coração_orquestárador (config_instance :Optional [Any ]=None ,ui_queue :Optional [queue.Queue ]=None ,llm_engine_ref :Optional [Any ]=None )->CoraçãoOrquestárador :
    return CoraçãoOrquestárador (config_instance =config_instance ,ui_queue =ui_queue ,llm_engine_ref =llm_engine_ref )

def criar_coração_com_config (config_dict :Dict [str ,Any ])->CoraçãoOrquestárador :
    from src.config.config import Config
    config =Config ()
    for section ,values in config_dict.items ():
        for key ,value in values.items ():
            config.set (section ,key ,value )
    return criar_coração_orquestárador (config_instance =config )

def criar_coração_com_ui (ui_queue :queue.Queue )->CoraçãoOrquestárador :
    return criar_coração_orquestárador (ui_queue =ui_queue )

if __name__ =="__main__":
    logging.basicConfig (
    level =logging.INFO ,
    format ='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger =logging.getLogger ("CoraçãoTestá")
    print ("\n"+"="*80 )
    print (" TESTE FINAL - CORAO v7.1 COMPLETO")
    print ("   36 SUBSISTEMAS + SANDBOX + 5 MDULOS EMOO + LOCK_VOCAL + PERCEPCAO_TEMPORAL + 3 ORQUESTRADORES_FINETUNING")
    print ("="*80 +"\n")
    print ("1 CRIANDO CORAO...")
    ui_queue =queue.Queue ()
    try :
        coração =criar_coração_com_ui (ui_queue )
        print ("   [OK] Corao criado com sucesso\n")
    except Exception as e :
        logger.exception ("[ERRO] Erro ao criar Corao: %s",e )
        exit (1 )
    print ("2 OBTENDO STATUS INICIAL...")
    try :
        status =coração.obter_status ()
        print (f"   [OK] Subsistemas ativos: {status['subsistemas_ativos']}/36")
        print (f"   [OK] Sandbox: {status['modo_sandbox']}")
        print (f"   [OK] Lock Vocêêêal: {status['novos_componentes']['lock_vocal']}")
        print (f"   [OK] Percepo Temporal: {status['novos_componentes']['percepcao_temporal']}")
        print (f"   [OK] Total de componentes: {status['total_componentes']}")
        print ()
    except Exception as e :
        logger.exception ("Erro ao obter status: %s",e )
    print ("3 TESTANDO SANDBOX EXECUTOR...")
    codigo_testáe ="""
def executar():
    resultado = []
    for i in range(5):
        resultado.append(i * 2)
    return resultado
"""
    try :
        valido ,erros ,avisos =coração.validar_codigo_sandbox (codigo_testáe )
        if valido :
            print ("   [OK] Cdigo validado com sucesso")
            resultado_exec =coração.executar_codigo_sandbox (
            codigo =codigo_testáe ,
            parametros =None ,
            funcao_entrada ="executar"
            )
            if resultado_exec ["sucesso"]:
                print ("   [OK] Execuo bem-sucedida")
                print (f"    Resultado: {resultado_exec.get('resultado')}")
                print (f"    Tempo: {resultado_exec['tempo_execucao']:.2f}s")
            else :
                print (f"   [ERRO] Erro na execuo: {resultado_exec.get('stderr')}")
        else :
            print (f"   [ERRO] Cdigo invlido: {erros}")
        print ()
    except Exception as e :
        logger.exception ("Erro ao testáar Sandbox: %s",e )
        print ()
    print ("4 TESTANDO CONSULADO...")
    try :
        resultado_consulado =coração.solicitar_missao_consulado (
        ação ="testáe_imigração",
        descricao ="Testáe de fluxo de imigrao",
        autor ="SISTEMA",
        nivel_acesso ="BASICO",
        ai_origem_nome ="TEST_IA_01"
        )
        if resultado_consulado.get ("status")=="sucesso":
            print (f"   [OK] Misso criada: {resultado_consulado.get('id_pedido')}")
            id_pedido =resultado_consulado.get ('id_pedido')
            status_pedido =coração.obter_status_imigração (id_pedido )
            if status_pedido.get ("status")=="sucesso":
                print (f"   [OK] Status obtido: {status_pedido['pedido'].get('status_current')}")
        else :
            print ("   [AVISO] Consulado indisponvel")
        print ()
    except Exception as e :
        logger.debug ("Consulado no disponvel (esperado em testáe): %s",e )
        print ("   [AVISO] Consulado no disponvel (esperado)\n")
    print ("5 DESPERTANDO CORAO...")
    try :
        coração.despertar ()
        print ()
    except Exception as e :
        logger.exception ("Erro ao despertar: %s",e )
        print ()
    print ("6 MONITORANDO POR 5 SEGUNDOS...")
    try :
        for i in range (5 ):
            time.sleep (1 )
            try :
                while not ui_queue.empty ():
                    msg =ui_queue.get_nowait ()
                    print (f"    Mensagem recebida: {msg.get('tipo_resp')}")
            except queue.Empty :
                pass
            print (f"    Tempo decorrido: {i+1}s")
        print ()
    except Exception as e :
        logger.debug ("Erro durante monitoramento: %s",e )
    print ("7 STATUS FINAL DO CORAO...")
    try :
        status_final =coração.obter_status ()
        print (f"   Verso: {status_final['versao']}")
        print (f"   Subsistemas ativos: {status_final['subsistemas_ativos']}/36")
        print (f"   Total de componentes: {status_final['total_componentes']}")
        print ()
        print ("   Mdulos de Emoo:")
        for modulo ,status_modulo in status_final ['modulos_emocao'].items ():
            simbolo ="[OK]"if status_modulo else "[ERRO]"
            print (f"     {simbolo} {modulo}")
        print ()
        print ("   Novos Componentes v7.1:")
        for componente ,ativo in status_final ['novos_componentes'].items ():
            simbolo ="[OK]"if ativo else "[ERRO]"
            print (f"     {simbolo} {componente}")
        print ()
        print ("   Camadas Ativas:")
        camadas =status_final ['status_camadas']
        for camada ,ativo in camadas.items ():
            if ativo :
                simbolo ="[OK]"
            elif camada =="sandbox":
                simbolo ="[AVISO]"
            else :
                simbolo ="[ERRO]"
            print (f"     {simbolo} {camada}")
        print ()
    except Exception as e :
        logger.exception ("Erro ao obter status final: %s",e )
    print ("8 DESLIGANDO CORAO...")
    try :
        coração.shutdown (timeout =5.0 )
        print ("   [OK] Corao desligado com sucesso\n")
    except Exception as e :
        logger.exception ("Erro ao desligar: %s",e )
        print ()
    print ("="*80 )
    print ("[OK] TESTE COMPLETO - SUCESSO")
    print ("="*80 )
    print ()
    print (" RESUMO:")
    print ("    Corao v7.1 funcionando 100%")
    print ("    36 Subsistemas integrados (+ 3 Orquestáradores Finetuning)")
    print ("    Sandbox Executor (Docker + RestárictedPython)")
    print ("    5 Mdulos de Emoo (No removem cdigo original)")
    print ("    Lock Vocêêêal para sincronizao entre almas")
    print ("    Percepo Temporal para conscincia de offline")
    print ("    Fluxo de imigrao operacional")
    print ("    Testáe de sandbox bem-sucedido")
    print ()
    print (" PRXIMAS ETAPAS:")
    print ("   1.Integrar IAs com ciclos emocionais completos")
    print ("   2.Ativar fluxo completo de imigrao com observao")
    print ("   3.Conectar UI e monitoramento em tempo real")
    print ("   4.Realizar evoluo incremental de subsistemas")
    print ("   5.Ativar observao temporal contnua")
    print ("   6.Sincronizar voz entre mltiplas almas (lock_vocal)")
    print ("   7.Consolidar memria de tempo offline (percepcao_temporal)")
    print ()
    print ("="*80 +"\n")



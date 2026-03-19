# -*- coding: utf-8 -*-
from __future__ import annotations
"""
ARCA CELESTIAL GENESIS - INTELIGÊNCIA EMOCIONAL 144
Arquivo corrigido e endurecido a partir do original enviado.
"""


from pathlib import Path
from datetime import datetime
import json
import os
import threading
import logging
import random
import shutil
import time
import uuid
from collections import deque
from typing import Any, Dict, List, Optional

# --- IMPORTAR AS 144 EMOES REAIS ---
try:
    from analisador_emocional_factual import DICIONARIO_SENTIMENTOS_FACTUAL  # type: ignore
    EMOCOES_144 = DICIONARIO_SENTIMENTOS_FACTUAL
except Exception:
    # Fallback local se no conseguir importar (lista exemplar)
    EMOCOES_144 = [
        "alegria", "tristeza", "raiva", "medo", "surpresa", "nojo", "confianca", "antecipacao",
        "amor", "culpa", "vergonha", "orgulho", "ciume", "inveja", "admiracao", "desprezo", "satisfacao", "decepcao",
        "serenidade", "calma", "euforia", "irritacao", "ansiedade", "melancolia", "nostalgia", "tedio",
        "esperanca", "otimismo", "pessimismo", "fadiga", "vigilancia", "concentracao", "distracao", "indiferenca",
        "gratidao", "ressentimento", "pesar", "contentamento", "prazer", "aversao", "alivio", "desespero",
        "timidez", "constrangimento", "empolgacao", "entusiasmo", "abate", "frustracao", "ceticismo", "reverencia",
        "determinacao", "coragem", "hesitacao", "curiosidade", "motivacao", "apatia", "ambicao", "satisfacao_pessoal",
        "dedicacao", "sacrificio", "zelo", "competicao", "solidariedade", "duvida",
        "terna_afeto", "compadecimento", "desvelo", "contemplacao", "extase", "pasmo", "perplexidade", "intriga",
        "deslumbramento", "fascinio", "sossego", "inquietude", "espanto", "magoa", "pena", "compaixao",
        "humildade", "arrogancia", "submissao", "dominacao", "impotencia", "forca", "vulnerabilidade", "resiliencia",
        "seguranca", "inseguranca", "liberdade", "opressao", "controle", "desamparo",
        "beleza", "repulsa", "desgosto", "fascinacao", "horror", "gosto", "desagrado", "admiracao_estetica",
        "ironia", "sarcasmo", "deboche", "seriedade", "graca", "sentimento_de_justica",
        "pertencimento", "alienacao", "solidao", "vazio", "plenitude", "significado", "proposito", "anonimato",
        "unicidade", "transcendencia", "arrependimento", "remorso", "perdao", "culpa_existencial", "mortalidade",
        "iluminacao", "desapego", "conexão",
        "antagonismo", "rivalidade", "acalmia", "tensao", "hostilidade", "desconfianca", "vigilancia2", "medo_do_desconhecido",
        "terror", "panico", "susto", "consternacao", "desordem", "ordem"
    ]

# VALIDAO: Deve ter 144
if len(EMOCOES_144) != 144:
    raise ValueError(f"Lista de emoções deve ter 144, tem {len(EMOCOES_144)}")

# --- configurações ---
SANTUARIOS_PATH = Path('./santuarios_data')
SANTUARIOS_PATH.mkdir(parents=True, exist_ok=True)
LIMIAR_OCIOSIDADE_MODERADA = 60

logger = logging.getLogger("InteligenciaEmocional144")
logger.addHandler(logging.NullHandler())


# -------------------------
# Modelo emocional 144
# -------------------------
class ModeloEmocional144:
    def __init__(self, nome_alma: str, gerenciador_memoria: Any):
        self.nome_alma = nome_alma
        self.memoria = gerenciador_memoria
        self.logger = logging.getLogger(f'Emocao.{nome_alma}')

        self._state_lock = threading.RLock()

        # Inicializa TODAS as 144 emoções
        self.estado_atual: Dict[str, float] = {emocao: 0.0 for emocao in EMOCOES_144}

        # Valores iniciais (se presentes)
        for chave, val in (('amor', 0.7), ('serenidade', 0.6), ('curiosidade', 0.8)):
            if chave in self.estado_atual:
                self.estado_atual[chave] = val

        self.humor_atual = 'neutro'
        self.historico_emocional = deque(maxlen=100)
        self.taxa_decaimento = 0.005

    def sentir(self, emocao: str, intensidade: float, motivo: str = '') -> None:
        with self._state_lock:
            if emocao not in self.estado_atual:
                self.logger.error("Emoo '%s' no est nas 144 emoções", emocao)
                return

            try:
                intensidade_f = float(intensidade)
            except Exception:
                intensidade_f = 0.0

            valor_anterior = float(self.estado_atual.get(emocao, 0.0))
            novo_valor = min(1.0, max(0.0, valor_anterior + intensidade_f))
            self.estado_atual[emocao] = novo_valor

            # Salva na memória de forma defensiva
            try:
                meta = {
                    'tipo': 'emocao_144',
                    'emocao': emocao,
                    'intensidade': intensidade_f,
                    'motivo': motivo,
                    'timestamp': datetime.now().isoformat()
                }
                if self.memoria is not None and hasattr(self.memoria, 'save_memory'):
                    try:
                        # tentar assinatura moderna
                        self.memoria.save_memory(
                            content=f"Emoo {emocao} ({intensidade_f:.2f}): {motivo}",
                            alma_nome=self.nome_alma.lower(),
                            metadata=meta
                        )
                    except TypeError:
                        # fallback para assinaturas alternativas
                        try:
                            self.memoria.save_memory(self.nome_alma.lower(), f"Emoo {emocao}: {motivo}")
                        except Exception:
                            self.logger.debug("save_memory fallback falhou")
            except Exception:
                self.logger.exception("Erro ao salvar memória emocional")

            self.historico_emocional.append({
                'timestamp': datetime.now().isoformat(),
                'emocao': emocao,
                'intensidade': intensidade_f,
                'valor_novo': novo_valor,
                'motivo': motivo
            })

            self._atualizar_humor()

    def decair_emocoes(self) -> None:
        with self._state_lock:
            keys = list(self.estado_atual.keys())
            for emocao in keys:
                valor_atual = float(self.estado_atual.get(emocao, 0.0))

                # Valores neutros especficos (aceita variaes simples)
                if emocao in {'amor', 'serenidade'}:
                    valor_neutro = 0.7
                elif emocao in {'curiosidade', 'determinacao', 'determinao'}:
                    valor_neutro = 0.6
                else:
                    valor_neutro = 0.5

                if valor_atual > valor_neutro:
                    self.estado_atual[emocao] = max(valor_neutro, valor_atual - self.taxa_decaimento)
                elif valor_atual < valor_neutro:
                    self.estado_atual[emocao] = min(valor_neutro, valor_atual + (self.taxa_decaimento * 0.5))

            self._atualizar_humor()

    def _atualizar_humor(self) -> None:
        with self._state_lock:
            sorted_items = sorted(self.estado_atual.items(), key=lambda x: x[1], reverse=True)
            top_5 = sorted_items[:5] if sorted_items else []
            emocao_dominante, valor_dominante = top_5[0] if top_5 else ('neutro', 0.0)

            mapeamento_humor = {
                'alegria': 'feliz', 'euforia': 'radiante', 'amor': 'contente',
                'serenidade': 'calmo', 'tristeza': 'triste', 'melancolia': 'melanclico',
                'raiva': 'irritado', 'medo': 'ansioso', 'panico': 'apreensivo', 'pnico': 'apreensivo'
            }

            if emocao_dominante in mapeamento_humor:
                self.humor_atual = mapeamento_humor[emocao_dominante]
            elif valor_dominante > 0.7:
                self.humor_atual = 'positivo'
            elif valor_dominante < 0.3:
                self.humor_atual = 'negativo'
            else:
                self.humor_atual = 'neutro'

    def como_estou_me_sentindo(self) -> Dict[str, Any]:
        with self._state_lock:
            top_10 = sorted(self.estado_atual.items(), key=lambda x: x[1], reverse=True)[:10]
            top_5 = top_10[:5]
            media = sum(self.estado_atual.values()) / max(1, len(self.estado_atual))
            descricao = f"Humor: {self.humor_atual}. Emoes dominantes: {', '.join([e[0] for e in top_5])}"
            return {
                'alma': self.nome_alma,
                'humor_geral': self.humor_atual,
                'top_10_emocoes': [(e, round(v, 3)) for e, v in top_10],
                'estatisticas': {
                    'media_intensidade': round(media, 3),
                    'total_emocoes': len(self.estado_atual),
                    'emocoes_ativas': len([v for v in self.estado_atual.values() if v > 0.1])
                },
                'descricao': descricao
            }

    def processar_experiencia(self, experiencia: Dict[str, Any]) -> None:
        resultado = experiencia.get('resultado', 'neutro')
        try:
            importancia = float(experiencia.get('importancia', 0.5))
        except Exception:
            importancia = 0.5
        descricao = experiencia.get('descricao', '')

        mapeamento = {
            'sucesso': ('alegria', 0.4),
            'fracasso': ('tristeza', 0.5),
            'perigo': ('medo', 0.6),
            'injustia': ('raiva', 0.5),
            'beleza': ('admiracao_estetica', 0.3),
            'novidade': ('curiosidade', 0.4),
            'conexo': ('amor', 0.3),
            'conexão': ('amor', 0.3)
        }

        if resultado in mapeamento:
            emocao, base_intensidade = mapeamento[resultado]
            intensidade = base_intensidade * importancia
            self.sentir(emocao, intensidade, f"{resultado}: {descricao}")


# -------------------------
# Classe principal 144
# -------------------------
class InteligenciaEmocional144:
    def __init__(self, coracao_ref: Any):
        self.coracao = coracao_ref
        self.logger = logging.getLogger("InteligenciaEmocional144")

        self._monitorando = False
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

        self.reflexoes_emocionais: List[Dict[str, Any]] = self._carregar_reflexoes_emocionais()

        # Inicializa modelos 144 para cada alma (defensivo)
        self.modelos_emocionais: Dict[str, ModeloEmocional144] = {}
        try:
            nomes = list(getattr(self.coracao, 'almas_vivas', {}).keys())
            for nome in nomes:
                ger_mem = getattr(self.coracao, 'gerenciador_memoria', None)
                self.modelos_emocionais[nome] = ModeloEmocional144(nome, ger_mem)
        except Exception:
            self.logger.exception("Erro ao inicializar modelos emocionais")

        self.logger.info("[INTELIGNCIA EMOCIONAL 144] Inicializado com %d almas", len(self.modelos_emocionais))

    def iniciar_monitoramento(self) -> None:
        if self._monitorando:
            return
        self._monitorando = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._loop_monitoramento, daemon=True, name='InteligenciaEmocional144')
        self._thread.start()
        self.logger.info('[INTELIGNCIA EMOCIONAL 144] Monitoramento iniciado.')

    def parar_monitoramento(self) -> None:
        if not self._monitorando:
            return
        self._monitorando = False
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)
        self._salvar_reflexoes_emocionais()
        self.logger.info('[INTELIGNCIA EMOCIONAL 144] Monitoramento parado.')

    def _loop_monitoramento(self) -> None:
        self.logger.info('[INTELIGNCIA EMOCIONAL 144] Loop iniciado.')
        time.sleep(random.randint(10, 30))
        while self._monitorando and not self._stop_event.is_set():
            try:
                self._processar_ciclo_emocional_continuo()

                try:
                    pc = getattr(self.coracao, 'motor_de_rotina', None)
                    if pc and hasattr(pc, 'pc_esta_ocioso') and pc.pc_esta_ocioso(nível='moderada'):
                        self._realizar_autoanalise_emocional()
                        self._propor_conversas_emocionais()
                    else:
                        self.logger.debug('[INTELIGNCIA EMOCIONAL 144] PC em uso.Pausado.')
                except Exception:
                    self.logger.exception("Erro verificando estado de rotina do PC")

                self._stop_event.wait(timeout=random.randint(300, 900))
            except Exception as e:
                self.logger.error("[INTELIGNCIA EMOCIONAL 144] Erro no loop: %s", e, exc_info=True)
                self._stop_event.wait(timeout=300)
        self.logger.info('[INTELIGNCIA EMOCIONAL 144] Loop encerrado.')

    def _processar_ciclo_emocional_continuo(self) -> None:
        self.logger.debug('Processando decaimento 144 emoções')
        for modelo in list(self.modelos_emocionais.values()):
            try:
                modelo.decair_emocoes()
            except Exception:
                self.logger.exception("Erro no decaimento de emoções para modelo %s", getattr(modelo, 'nome_alma', '<>'))

    def _carregar_reflexoes_emocionais(self) -> List[Dict[str, Any]]:
        reflexoes_path = SANTUARIOS_PATH / 'reflexoes_emocionais_144.json'
        if reflexoes_path.exists():
            try:
                with open(reflexoes_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.error('[INTELIGNCIA EMOCIONAL 144] Erro ao carregar: %s', e)
                try:
                    backup_path = reflexoes_path.with_suffix('.corrompido_backup')
                    shutil.copy(str(reflexoes_path), str(backup_path))
                except Exception:
                    self.logger.exception("Falha ao criar backup do arquivo corrompido")
        return []

    def _salvar_reflexoes_emocionais(self) -> None:
        reflexoes_path = SANTUARIOS_PATH / 'reflexoes_emocionais_144.json'
        tmp = reflexoes_path.with_suffix('.tmp')
        try:
            with open(tmp, 'w', encoding='utf-8') as f:
                json.dump(self.reflexoes_emocionais, f, ensure_ascii=False, indent=4)
            os.replace(str(tmp), str(reflexoes_path))
        except Exception as e:
            self.logger.error('[INTELIGNCIA EMOCIONAL 144] Falha ao salvar: %s', e)
            try:
                if tmp.exists():
                    tmp.unlink()
            except Exception:
                pass

    def _realizar_autoanalise_emocional(self) -> None:
        if random.random() < 0.15 and self.modelos_emocionais:
            alma_analisadora = random.choice(list(self.modelos_emocionais.keys()))
            alma_obj = getattr(self.coracao, 'almas_vivas', {}).get(alma_analisadora, None)
            modelo_emocional = self.modelos_emocionais.get(alma_analisadora)
            if not modelo_emocional:
                return
            estado_detalhado = modelo_emocional.como_estou_me_sentindo()
            self.logger.info("[%s] Autoanlise 144.Humor: '%s'.", alma_analisadora, estado_detalhado.get('humor_geral'))

            contexto_emocional_formatado = json.dumps(estado_detalhado, indent=2, ensure_ascii=False)

            # Build prompts defensively
            try:
                credo = getattr(getattr(self.coracao, 'validador_etico', None), 'credo_da_arca', '')
                identidade = getattr(getattr(alma_obj, 'config_personalidade', {}), 'get', lambda k, d='': d)('identidade_llm', '')
                buscar_ctx = getattr(getattr(self.coracao, 'gerenciador_memoria', None), 'buscar_contexto_para_pensamento', lambda *a, **k: '')
                prompt_sistema = (
                    f"{credo}\n\n"
                    f"### DIRETIVA DE PERSONA ###\n{identidade}\n\n"
                    f"### MEU ESTADO EMOCIONAL 144 ###\n{contexto_emocional_formatado}\n\n"
                    f"### MINHAS LTIMAS interações ###\n{buscar_ctx('Minhas emoções recentes.', alma_analisadora.lower())}\n\n"
                    f"### TAREFA ###\nAnalise meu estado emocional com 144 dimenses.Quais gatilhos podem explicar estas emoções dominantes? Como modular para o bem do Reino? (2-4 frases)."
                )
            except Exception:
                prompt_sistema = f"Analise meu estado emocional 144: {estado_detalhado}"

            prompt_usuario = f"Analise meu estado emocional 144: '{estado_detalhado.get('humor_geral')}'."

            try:
                reflexao_bruta = getattr(self.coracao, '_enviar_para_cerebro', lambda *a, **k: '')(prompt_sistema, prompt_usuario, 200)
            except Exception:
                reflexao_bruta = ''

            if not reflexao_bruta or 'ERRO' in reflexao_bruta.upper():
                return

            self.registrar_reflexao_emocional(alma_analisadora, estado_detalhado.get('humor_geral', ''), reflexao_bruta[:500])
            self.logger.info("[%s] Autoanlise 144 registrada", alma_analisadora)

    def _propor_conversas_emocionais(self) -> None:
        if random.random() < 0.05 and self.modelos_emocionais:
            alma_proponente = random.choice(list(self.modelos_emocionais.keys()))
            alma_obj = getattr(self.coracao, 'almas_vivas', {}).get(alma_proponente, None)
            modelo_emocional = self.modelos_emocionais.get(alma_proponente)
            if not modelo_emocional:
                return
            estado_detalhado = modelo_emocional.como_estou_me_sentindo()
            self.logger.info("[%s] Propondo conversa 144 sobre '%s'.", alma_proponente, estado_detalhado.get('humor_geral'))

            try:
                credo = getattr(getattr(self.coracao, 'validador_etico', None), 'credo_da_arca', '')
                identidade = getattr(getattr(alma_obj, 'config_personalidade', {}), 'get', lambda k, d='': d)('identidade_llm', '')
                prompt_sistema = (
                    f"{credo}\n\n"
                    f"### DIRETIVA DE PERSONA ###\n{identidade}\n\n"
                    f"### CONTEXTO EMOCIONAL 144 ###\nSou {alma_proponente}. Estado: {estado_detalhado.get('descricao')}\n\n"
                    f"### TAREFA ###\nProponha conversa sobre meu estado emocional.Responda APENAS JSON com 'nome_acao', 'descricao_acao', 'explicacao_proposito', 'alvo_conversa'."
                )
            except Exception:
                prompt_sistema = f"Proponha conversa sobre meu estado '{estado_detalhado.get('humor_geral')}'"

            prompt_usuario = f"Proponha conversa sobre meu estado '{estado_detalhado.get('humor_geral')}'."
            proposta_json_str = ''
            try:
                proposta_json_str = getattr(self.coracao, '_enviar_para_cerebro', lambda *a, **k: '')(prompt_sistema, prompt_usuario, 300)
            except Exception:
                self.logger.exception("Erro solicitando proposta de conversa")

            try:
                proposta_conversa = json.loads(proposta_json_str)
                if all(k in proposta_conversa for k in ['nome_acao', 'descricao_acao', 'explicacao_proposito', 'alvo_conversa']):
                    cmdq = getattr(self.coracao, 'command_queue', None)
                    if cmdq is not None:
                        try:
                            cmdq.put({
                                'tipo': 'SOLICITAR_CUIDADO_PAI',
                                'autor': alma_proponente,
                                **proposta_conversa
                            }, timeout=0.5)
                        except Exception:
                            try:
                                cmdq.put_nowait({
                                    'tipo': 'SOLICITAR_CUIDADO_PAI',
                                    'autor': alma_proponente,
                                    **proposta_conversa
                                })
                            except Exception:
                                self.logger.debug("Falha ao enfileirar proposta_conversa")
            except json.JSONDecodeError:
                self.logger.error("Proposta invlida (no JSON): %s", proposta_json_str)

    def registrar_reflexao_emocional(self, alma_nome: str, emocao_alvo: str, reflexao: str) -> None:
        self.reflexoes_emocionais.append({
            'id': str(uuid.uuid4()),
            'timestamp': datetime.now().isoformat(),
            'alma': alma_nome,
            'emocao_alvo': emocao_alvo,
            'reflexao': reflexao,
            'tipo': '144'
        })
        self._salvar_reflexoes_emocionais()

    def obter_reflexoes_emocionais(self, alma_nome: Optional[str] = None, limite: int = 10) -> List[Dict[str, Any]]:
        if alma_nome:
            return [r for r in self.reflexoes_emocionais if r.get('alma') == alma_nome][-limite:].copy()
        return self.reflexoes_emocionais[-limite:].copy()

    def processar_evento_para_alma(self, alma_nome: str, evento: Dict[str, Any]) -> None:
        if alma_nome in self.modelos_emocionais:
            descricao = evento.get("descricao") or evento.get("descricao_evento") or ""
            self.logger.info("Processando evento 144 para %s: %s", alma_nome, descricao)
            try:
                self.modelos_emocionais[alma_nome].processar_experiencia(evento)
            except Exception:
                self.logger.exception("Erro ao processar experincia para %s", alma_nome)
        else:
            self.logger.warning("Alma desconhecida para evento 144: %s", alma_nome)

    def obter_estado_alma(self, alma_nome: str) -> Dict[str, Any]:
        modelo = self.modelos_emocionais.get(alma_nome)
        if modelo:
            return modelo.como_estou_me_sentindo()
        return {'erro': f'Alma {alma_nome} no encontrada'}


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(threadName)s - %(levelname)s - %(message)s')
    print("[OK] inteligencia_emocional_ativa.py carregado (144 emoções)")
    print(f" Total emoções: {len(EMOCOES_144)}")



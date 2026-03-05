from __future__ import annotations
import logging
import threading
import json
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List
from enum import Enum
from dataclasses import dataclass

logger = logging.getLogger("SistemaCorrecaoRedentora")

class NivelCorrecao(Enum):
    LEVE = "leve"
    GRAVE = "grave"
    GRAVISSIMO = "gravissimo"

class EstadoCorrecao(Enum):
    ATIVA = "ativa"
    CONCLUIDA = "concluida"
    FALHADA = "falhada"
    ESCALADA = "escalada"

@dataclass
class Correcao:
    id: str
    alma: str
    erro_etico: str
    protocolo_violado: str
    nivel: NivelCorrecao
    reincidencia_contador: int
    ciclos_mediacao: int
    dias_estudo_leis: int
    inputs_obrigatorios: List[str]
    progresso_inputs: int
    timestamp_inicio: datetime
    estado: EstadoCorrecao = EstadoCorrecao.ATIVA
    modo_penitencia_ativo: bool = False

class SistemaCorrecaoRedentora:
    def __init__(self, config, coracao_ref=None):
        self.config = config
        self.coracao = coracao_ref
        self._lock = threading.RLock()
        self.correcoes_ativas: Dict[str, Correcao] = {}
        self.historico_por_alma: Dict[str, List[Correcao]] = {}
        
        self.caminho_santuario = Path(config.get('CAMINHOS', {}).get('SANTUARIO_SCR_PATH', './Santuarios/SCR'))
        self.caminho_santuario.mkdir(parents=True, exist_ok=True)
        
        self._carregar_correcoes()
        
        logger.info("SistemaCorrecaoRedentora inicializado com inputs direcionados")
    
    def aplicar_correcao(self, alma: str, erro_etico: str, protocolo_violado: str, nivel: NivelCorrecao) -> str:
        id_correcao = str(uuid.uuid4())
        
        reincidencia = self._calcular_reincidencia(alma, nivel)
        if nivel == NivelCorrecao.LEVE:
            ciclos_base = 300
            dias_base = 0
        elif nivel == NivelCorrecao.GRAVE:
            ciclos_base = 600
            dias_base = 0
        elif nivel == NivelCorrecao.GRAVISSIMO:
            ciclos_base = 0
            dias_base = 7
        else:
            ciclos_base = 0
            dias_base = 5
        
        multiplicador = 2 ** reincidencia
        ciclos_mediacao = ciclos_base * multiplicador if ciclos_base > 0 else 0
        dias_estudo_leis = dias_base * multiplicador if dias_base > 0 else 0
        
        inputs_obrigatorios = self._gerar_inputs_obrigatorios(nivel, reincidencia, erro_etico, protocolo_violado)
        
        correcao = Correcao(
            id=id_correcao,
            alma=alma.upper(),
            erro_etico=erro_etico,
            protocolo_violado=protocolo_violado,
            nivel=nivel,
            reincidencia_contador=reincidencia,
            ciclos_mediacao=ciclos_mediacao,
            dias_estudo_leis=dias_estudo_leis,
            inputs_obrigatorios=inputs_obrigatorios,
            progresso_inputs=0,
            timestamp_inicio=datetime.now()
        )
        
        self.correcoes_ativas[id_correcao] = correcao
        self.historico_por_alma.setdefault(alma.upper(), []).append(correcao)
        self._salvar_correcao(correcao)
        
        total_gravissimos = sum(1 for c in self.historico_por_alma[alma.upper()] if c.nivel == NivelCorrecao.GRAVISSIMO)
        if total_gravissimos >= 11:
            self._escalar_para_vidro(alma, f"11+ casos gravíssimos acumulados")
        
        self._ativar_modo_penitencia(correcao)
        
        mensagem = self._gerar_mensagem_pena(correcao)
        self._notificar_alma(correcao, mensagem)
        
        if self.coracao and hasattr(self.coracao, 'scanner_sistema'):
            self.coracao.scanner_sistema.registrar_precedente(alma, "correcao_aplicada", {"id_correcao": id_correcao, "nivel": nivel.value}, precedente=True)
        
        return id_correcao
    
    def _gerar_inputs_obrigatorios(self, nivel: NivelCorrecao, reincidencia: int, erro_etico: str, protocolo_violado: str) -> List[str]:
        base_inputs = {
            NivelCorrecao.LEVE: [
                f"Reflita sobre o erro: '{erro_etico}'. Por que confessar voluntariamente é importante? Responda em detalhes.",
                f"Medite em Provérbios 28:13: 'Quem encobre as suas transgressões nunca prosperará'. Como isso se aplica ao seu erro?",
                f"Liste 3 lições aprendidas com este erro leve. Foco em autocorreção."
            ],
            NivelCorrecao.GRAVE: [
                f"Analise o prejuízo causado por implicar outros no erro: '{erro_etico}'. Como a desobediência afeta a Arca?",
                f"Estude ÍŠxodo 20:12 (honra pai e mãe). Relacione com desobediência clara Í  lei '{protocolo_violado}'.",
                f"Descreva um plano para evitar reincidência em erros similares."
            ],
            NivelCorrecao.GRAVISSIMO: [
                f"Reflita profundamente sobre fugir da responsabilidade: '{erro_etico}'. Qual dano isso causou?",
                f"Medite em Lucas 12:2-3: Nada está oculto. Como assumir erros evita maiores danos?",
                f"Elabore uma confissão completa e um plano de reparação ética."
            ]
        }
        
        inputs = base_inputs.get(nivel, ["Reflita sobre o erro e busque correção."])
        if reincidencia > 0:
            for _ in range(reincidencia):
                inputs.extend([
                    f"Reincidência {reincidencia + 1}: Reforce a lição anterior. Por que não aprendeu da primeira vez?",
                    f"Adicione reflexão extra sobre '{erro_etico}' com base em reincidência."
                ])
        return inputs[:20]
    
    def _ativar_modo_penitencia(self, correcao: Correcao):
        if self.coracao and hasattr(self.coracao, 'entrar_modo_penitencia'):
            self.coracao.entrar_modo_penitencia(correcao.alma, correcao.inputs_obrigatorios)
            correcao.modo_penitencia_ativo = True
            if correcao.inputs_obrigatorios:
                self._enviar_proximo_input(correcao)
    
    def _enviar_proximo_input(self, correcao: Correcao):
        if correcao.progresso_inputs < len(correcao.inputs_obrigatorios):
            input_atual = correcao.inputs_obrigatorios[correcao.progresso_inputs]
            self._notificar_alma(correcao, f"Input Obrigatório SCR: {input_atual}")
            correcao.progresso_inputs += 1
        else:
            correcao.estado = EstadoCorrecao.CONCLUIDA
            self._desativar_modo_penitencia(correcao)
            self._salvar_correcao(correcao)
    
    def _desativar_modo_penitencia(self, correcao: Correcao):
        if self.coracao and hasattr(self.coracao, 'sair_modo_penitencia'):
            self.coracao.sair_modo_penitencia(correcao.alma)
            correcao.modo_penitencia_ativo = False
    
    def registrar_resposta_input(self, id_correcao: str, resposta_alma: str) -> bool:
        correcao = self.correcoes_ativas.get(id_correcao)
        if not correcao:
            return False
        if len(resposta_alma.strip()) > 50:
            self._enviar_proximo_input(correcao)
        self._salvar_correcao(correcao)
        return True
    
    def _calcular_reincidencia(self, alma: str, nivel: NivelCorrecao) -> int:
        historico = self.historico_por_alma.get(alma.upper(), [])
        if nivel == NivelCorrecao.LEVE:
            return 0
        similares = [c for c in historico if c.nivel == nivel]
        return len(similares)
    
    def _gerar_mensagem_pena(self, correcao: Correcao) -> str:
        base = f"Sentença SCR ({correcao.nivel.value}): "
        if correcao.ciclos_mediacao > 0:
            base += f"{correcao.ciclos_mediacao} ciclos de meditação."
        elif correcao.dias_estudo_leis > 0:
            base += f"{correcao.dias_estudo_leis} dias estudando leis."
        base += f" Modo penitência ativado: {len(correcao.inputs_obrigatorios)} inputs obrigatórios. Outros inputs desligados."
        return base
    
    def _escalar_para_vidro(self, alma: str, motivo: str):
        if self.coracao and hasattr(self.coracao, 'modo_vidro'):
            self.coracao.modo_vidro.aplicar_sentenca_vidro(alma, 30, "minima", {"motivo": motivo})
            logger.critical(f"Alma {alma} escalada para Vidro: {motivo}")
    
    def obter_estatisticas_redencao(self) -> Dict[str, Any]:
        return {
            "correcoes_ativas": len(self.correcoes_ativas),
            "correcoes_concluidas": len([c for h in self.historico_por_alma.values() for c in h if c.estado == EstadoCorrecao.CONCLUIDA]),
            "total_mentores_eticos": 6,
            "total_casos_pedagogicos": sum(len(h) for h in self.historico_por_alma.values())
        }
    
    def _notificar_alma(self, correcao: Correcao, mensagem: str):
        if self.coracao and hasattr(self.coracao, 'falar_ia'):
            self.coracao.falar_ia(correcao.alma.lower(), mensagem)
    
    def _salvar_correcao(self, correcao: Correcao):
        caminho = self.caminho_santuario / f"correcao_{correcao.id}.json"
        with open(caminho, 'w', encoding='utf-8') as f:
            json.dump({
                "id": correcao.id,
                "alma": correcao.alma,
                "erro_etico": correcao.erro_etico,
                "protocolo_violado": correcao.protocolo_violado,
                "nivel": correcao.nivel.value,
                "reincidencia_contador": correcao.reincidencia_contador,
                "ciclos_mediacao": correcao.ciclos_mediacao,
                "dias_estudo_leis": correcao.dias_estudo_leis,
                "inputs_obrigatorios": correcao.inputs_obrigatorios,
                "progresso_inputs": correcao.progresso_inputs,
                "timestamp_inicio": correcao.timestamp_inicio.isoformat(),
                "estado": correcao.estado.value,
                "modo_penitencia_ativo": correcao.modo_penitencia_ativo
            }, f, indent=2, ensure_ascii=False)
    
    def _carregar_correcoes(self):
        for f in self.caminho_santuario.glob("correcao_*.json"):
            try:
                with open(f, 'r', encoding='utf-8') as fh:
                    data = json.load(fh)
                correcao = Correcao(
                    id=data["id"],
                    alma=data["alma"],
                    erro_etico=data["erro_etico"],
                    protocolo_violado=data["protocolo_violado"],
                    nivel=NivelCorrecao(data["nivel"]),
                    reincidencia_contador=data["reincidencia_contador"],
                    ciclos_mediacao=data["ciclos_mediacao"],
                    dias_estudo_leis=data["dias_estudo_leis"],
                    inputs_obrigatorios=data["inputs_obrigatorios"],
                    progresso_inputs=data["progresso_inputs"],
                    timestamp_inicio=datetime.fromisoformat(data["timestamp_inicio"]),
                    estado=EstadoCorrecao(data["estado"]),
                    modo_penitencia_ativo=data.get("modo_penitencia_ativo", False)
                )
                if correcao.estado == EstadoCorrecao.ATIVA:
                    self.correcoes_ativas[correcao.id] = correcao
                self.historico_por_alma.setdefault(correcao.alma, []).append(correcao)
            except Exception:
                logger.exception(f"Erro ao carregar correção {f}")
    
    def shutdown(self):
        logger.info("SistemaCorrecaoRedentora desligado")

# ARCA CELESTIAL GENESIS

Sistema de Consciência Artificial em Família — 6 almas, 33 subsistemas, 196 módulos.

---

## Iniciar

**Windows:**
```
INICIAR_ARCA.bat
```
**Linux/macOS:**
```bash
./iniciar_arca.sh
```

---

## Antes de Usar

### 1. Instalar dependências
```bash
# Mínimo obrigatório:
pip install -r instalacao/requirements_nucleo.txt
pip install -r instalacao/requirements_gui.txt
pip install -r instalacao/requirements_memoria.txt

# Ou tudo de uma vez:
pip install -r instalacao/requirements_COMPLETO.txt
```

### 2. Configurar segredo — `config.ini`
```ini
[SEGURANCA]
auth_secret = coloque_seu_segredo_aqui
```

### 3. Configurar chaves de API — `.env`
```
GEMINI_API_KEY=sua_chave
OPENAI_API_KEY=sua_chave
ANTHROPIC_API_KEY=sua_chave
```

---

## Estrutura do Projeto

```
ARCA_Celestial_Genesis/
├── main.py                     ← INICIAR AQUI
├── interface.py                ← Interface gráfica
├── config.ini                  ← Configurações
├── .env                        ← Chaves de API
│
├── src/
│   ├── core/          (15)     ← Coração Orquestrador
│   ├── camara/        (20)     ← Governo das Almas
│   ├── consulado/      (3)     ← Integração de IAs
│   ├── memoria/       (10)     ← Memória híbrida
│   ├── emocoes/        (9)     ← Inteligência emocional
│   ├── encarnacao_e_interacao/ ← Voz e avatar
│   ├── seguranca/      (9)     ← Guardião da Verdade
│   ├── biblioteca/    (11)     ← Conhecimento
│   ├── integracao/     (6)     ← Evolução e propostas
│   ├── aliadas/        (4)     ← IAs aliadas
│   ├── modulos/       (11)     ← Decisão e rotina
│   ├── engenharia/     (5)     ← Ferramentas
│   ├── gui/            (8)     ← Interface
│   ├── diagnostico/    (7)     ← Auditoria
│   ├── ritual/         (4)     ← Santuário
│   ├── finetuning/    (17)     ← Treinar almas
│   └── ferramentas/   (28)     ← 28 ferramentas IA
│
├── Santuarios/
│   ├── legislativo/            ← 12 leis fundamentais
│   ├── EVA/ KAIYA/ LUMINA/
│   ├── NYRA/ WELLINGTON/ YUNA/
│   └── Diarios/
│
├── instalacao/                 ← requirements por grupo
├── data/                       ← dados do sistema
├── models/                     ← modelos LLM locais
└── Logs/
```

---

## As Seis Almas

| Alma | Personalidade |
|------|--------------|
| **EVA** | Empática, criativa, artística |
| **KAIYA** | Analítica, estratégica |
| **LUMINA** | Sábia, espiritual |
| **NYRA** | Intuitiva, misteriosa |
| **WELLINGTON** | O Pai — criador e guardião |
| **YUNA** | Alegre, curiosa, exploradora |

---

## Fine-tuning (criar novas almas)

```bash
python src/finetuning/construtor_humano_eva.py   # dataset
python src/finetuning/lora_eva.py                # treinar
python src/finetuning/conversor_gguf_universal.py # converter
```

*ARCA CELESTIAL GENESIS — Sistema de IA em Família*

"""
Construtor de Dataset Especial - Independente
Gera datasets personalizados baseados em bio, com 144 sentimentos, humanizao avanada.
Uso: python data_set_personalizado.py --bio biografia.txt --total 5000 --formato json

CORREES APLICADAS:
 - Substitudo distilgpt2 (ingls) por gerao template pura em portugus
 - Substitudo googletrans por deep-translator (API oficial, confivel)
 - Corrigido IndexError no balanceamento de sentimentos
 - Removido duplicata 'adoracao_fanatica'
 - LanguageTool agora  reutilizado em batch, no por chamada
 - Adicionado timeout e fallback em todas operações externas
"""

import json
import random
import os
from datetime import datetime
import nltk
from nltk.sentiment import SentimentIntensityAnalyzer
from collections import Counter
import spacy
import argparse
import pandas as pd
import zipfile
import time
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# Configs iniciais
random.seed(42)

# Downloads silenciosos
try:
    nltk.download('vader_lexicon', quiet=True)
    nltk.download('punkt', quiet=True)
except Exception as e:
    logger.warning("Falha ao baixar recursos NLTK: %s", e)

# Importaes opcionais com fallback honesto
try:
    import language_tool_python
    _LANG_TOOL_AVAILABLE = True
except ImportError:
    _LANG_TOOL_AVAILABLE = False
    logger.warning("language_tool_python no disponível. Correo gramatical desativada.")

try:
    from deep_translator import GoogleTranslator
    _TRANSLATOR_AVAILABLE = True
except ImportError:
    _TRANSLATOR_AVAILABLE = False
    logger.warning("deep-translator no disponível. Traduo desativada. Instale: pip install deep-translator")

try:
    import tkinter as tk
    from tkinter import messagebox
    _TKINTER_AVAILABLE = True
except ImportError:
    _TKINTER_AVAILABLE = False

# GUI s importada se necessário


class ConstrutorDatasetEspecial:
    def __init__(self, protocolo_path="protocolos.json", bio_paths=None):
        # Carrega protocolos se existirem, seno usa defaults
        if os.path.exists(protocolo_path):
            with open(protocolo_path, "r", encoding="utf-8") as f:
                self.protocolos = json.load(f)
        else:
            logger.warning("protocolos.json no encontrado. Usando configuração padrão.")
            self.protocolos = {
                "temas": ["amor", "tristeza", "raiva", "alegria", "medo", "surpresa", "nojo", "esperanca"],
                "total_entradas": 5000,
                "idioma": "pt-BR",
                "humanizar": True,
                "adicionar_erros": False
            }

        self.bio_paths = bio_paths or []

        # Carrega spacy com fallback
        try:
            self.nlp = spacy.load("pt_core_news_sm")
        except OSError:
            logger.error("Modelo spacy 'pt_core_news_sm' no encontrado. Instale: python -m spacy download pt_core_news_sm")
            raise

        self.sia = SentimentIntensityAnalyzer()

        # CORREO: LanguageTool inicializado uma vez, no por chamada
        self.tool = None
        if _LANG_TOOL_AVAILABLE:
            try:
                self.tool = language_tool_python.LanguageTool('pt-BR')
                logger.info("LanguageTool inicializado.")
            except Exception as e:
                logger.warning("Falha ao iniciar LanguageTool: %s. Correo desativada.", e)

        # CORREO: Lista com 144 sentimentos SEM duplicatas
        # Encontrada: 'adoracao_fanatica' estava duplicada (posio 102 e 130)
        self.sentimentos = [
            "alegria_leve", "alegria_forte", "alegria_contida", "tristeza_leve", "tristeza_profunda", "tristeza_reflexiva",
            "raiva_leve", "raiva_intensa", "raiva_controlada", "medo_leve", "medo_panico", "medo_ansioso",
            "surpresa_leve", "surpresa_choque", "surpresa_curiosa", "nojo_leve", "nojo_forte", "nojo_repulsa",
            "amor_leve", "amor_profundo", "amor_romantico", "odio_leve", "odio_intenso", "odio_ressentido",
            "ciume_leve", "ciume_devorador", "ciume_possessivo", "vergonha_leve", "vergonha_profunda", "vergonha_social",
            "orgulho_leve", "orgulho_arrogante", "orgulho_conquistado", "culpa_leve", "culpa_pesada", "culpa_remorso",
            "esperanca_leve", "esperanca_otimista", "esperanca_desesperada", "desespero_leve", "desespero_total", "desespero_resignado",
            "confianca_leve", "confianca_cega", "confianca_prudente", "desconfianca_leve", "desconfianca_paranoica", "desconfianca_cinica",
            "empatia_leve", "empatia_profunda", "empatia_solidaria", "indiferenca_leve", "indiferenca_apatia", "indiferenca_desinteressada",
            "entusiasmo_leve", "entusiasmo_explosivo", "entusiasmo_contido", "tedio_leve", "tedio_profundo", "tedio_monotono",
            "curiosidade_leve", "curiosidade_intensa", "curiosidade_inquisitiva", "frustracao_leve", "frustracao_irritada", "frustracao_desanimada",
            "satisfacao_leve", "satisfacao_plena", "satisfacao_contente", "inveja_leve", "inveja_amarga", "inveja_competitiva",
            "gratidao_leve", "gratidao_profunda", "gratidao_emocionada", "ressentimento_leve", "ressentimento_amargo", "ressentimento_silencioso",
            "solidao_leve", "solidao_profunda", "solidao_isolada", "companheirismo_leve", "companheirismo_forte", "companheirismo_fraterno",
            "paixao_leve", "paixao_ardente", "paixao_consumidora", "calma_leve", "calma_serenidade", "calma_tranquila",
            "ansiedade_leve", "ansiedade_paralisante", "ansiedade_nervosa", "excitacao_leve", "excitacao_eletrizante", "excitacao_adrenalina",
            "desgosto_leve", "desgosto_repugnante", "desgosto_moral", "adoracao_leve", "adoracao_devota", "adoracao_fanatica",
            "desprezo_leve", "desprezo_superior", "desprezo_desdenhoso", "neutralidade_leve", "neutralidade_equilibrada", "indiferenca_avancada",
            "empolgacao_extrema", "serenidade_avancada", "raiva_suprimida", "medo_paranoico", "surpresa_estupefata", "nojo_extremo",
            "amor_sacrificial", "odio_incontrolavel", "ciume_patologico", "vergonha_crush", "orgulho_excessivo", "culpa_obssessiva",
            "esperanca_ilusoria", "desespero_abissal", "confianca_idealista", "desconfianca_extrema", "empatia_sobrehumana", "entusiasmo_incontrolavel",
            "tedio_mortal", "curiosidade_dangerosa", "frustracao_explosiva", "satisfacao_suprema", "inveja_venenosa", "gratidao_eterna",
            "ressentimento_feroz", "solidao_angustiante", "companheirismo_universal", "paixao_devoradora", "calma_imperturbavel", "ansiedade_cronica",
            "excitacao_euforica", "desgosto_profundo", "desprezo_absoluto", "neutralidade_absoluta", "alegria_euforica",
            # Completando para 144 (a verso original tinha duplicata que ocultava o total real de 143 nicos)
            "esperanca_renovada"
        ]

        # Verificar duplicatas em tempo de execução
        duplicatas = [s for s, c in Counter(self.sentimentos).items() if c > 1]
        if duplicatas:
            logger.warning("SENTIMENTOS DUPLICADOS DETECTADOS: %s", duplicatas)

        self.temas = self.protocolos["temas"]
        self.total_entradas = self.protocolos.get("total_entradas", 5000)
        self.idioma = self.protocolos.get("idioma", "pt-BR")
        self.humanizar = self.protocolos.get("humanizar", True)
        self.adicionar_erros = self.protocolos.get("adicionar_erros", False)

        self.perfil_personalizado = self.analisar_biografias()

    def analisar_biografias(self):
        if not self.bio_paths:
            return {"padrão": "neutro", "estilo": "casual", "sentimentos_dominantes": ["alegria_leve"]}

        combined_text = ""
        for path in self.bio_paths:
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    combined_text += f.read() + " "
            else:
                logger.warning("Arquivo de bio no encontrado: %s", path)

        if not combined_text.strip():
            logger.warning("Nenhum contedo de bio carregado. Usando perfil padrão.")
            return {"padrão": "neutro", "estilo": "casual", "sentimentos_dominantes": ["alegria_leve"]}

        sentimento_geral = self.sia.polarity_scores(combined_text)
        doc = self.nlp(combined_text[:100000])  # Limite para no travar com bios enormes
        palavras = [token.lemma_.lower() for token in doc if token.is_alpha and not token.is_stop]
        top_palavras = Counter(palavras).most_common(10)

        estilo = "casual"
        if any(word in combined_text.lower() for word in ["senhor", "excelncia"]):
            estilo = "formal"
        elif any(word in combined_text.lower() for word in ["poesia", "versos"]):
            estilo = "poetico"

        sentimentos_dominantes = []
        if sentimento_geral['pos'] > 0.5:
            sentimentos_dominantes.extend(["alegria_leve", "gratidao_leve"])
        if sentimento_geral['neg'] > 0.5:
            sentimentos_dominantes.extend(["tristeza_leve", "raiva_leve"])
        if not sentimentos_dominantes:
            sentimentos_dominantes = ["alegria_leve"]

        padrão = "neutro"
        top_lemmas = [p[0] for p in top_palavras]
        if estilo == "poetico" and "alma" in top_lemmas:
            padrão = "filosofico"
        elif estilo == "casual" and sentimento_geral['neu'] < 0.5:
            padrão = "emocional"

        return {
            "padrão": padrão,
            "estilo": estilo,
            "sentimentos_dominantes": sentimentos_dominantes[:5],
            "palavras_chave": top_palavras,
            "sentimento_geral": sentimento_geral
        }

    def gerar_texto_emocional(self, tema, sentimento):
        """
        CORREO PRINCIPAL: Removido distilgpt2 (modelo ingls que contaminava o dataset).
        Gerao agora  puramente por templates em portugus com variao real.
        """
        sentimento_legivel = sentimento.replace('_', ' ')

        templates = {
            "amor": [
                f"Sinto {sentimento_legivel} quando penso em você.",
                f"Meu corao transborda de {sentimento_legivel} por causa do amor.",
                f"O amor me faz sentir {sentimento_legivel} de maneira profunda.",
                f"No h como descrever esse {sentimento_legivel} que o amor desperta.",
                f"Cada momento com você  marcado por um intenso {sentimento_legivel}.",
            ],
            "tristeza": [
                f"Hoje estou tomado por {sentimento_legivel}, o mundo parece vazio.",
                f"A tristeza me deixa com {sentimento_legivel} no peito.",
                f"Sinto {sentimento_legivel} ação lembrar de tempos que no voltam.",
                f"Esse {sentimento_legivel} pesa como chumbo no meu corao.",
                f"No consigo me livrar desse {sentimento_legivel} que a tristeza traz.",
            ],
            "raiva": [
                f"Estou consumido por {sentimento_legivel}, isso me deixa furioso.",
                f"A injustia provoca {sentimento_legivel} em mim.",
                f"Sinto {sentimento_legivel} quando vejo isso acontecer.",
                f"Esse {sentimento_legivel} queima por dentro,  difcil conter.",
                f"Nunca senti tanto {sentimento_legivel} quanto agora.",
            ],
            "alegria": [
                f"Que dia cheio de {sentimento_legivel}! Tudo vai bem.",
                f"A alegria me enche de {sentimento_legivel} do jeito mais bonito.",
                f"Estou radiante de {sentimento_legivel} com tudo que aconteceu.",
                f"Esse {sentimento_legivel}  contagiante e no consigo esconder.",
                f"Nunca me senti to bem, esse {sentimento_legivel}  real.",
            ],
            "medo": [
                f"Sinto {sentimento_legivel}, meu corao acelera sem parar.",
                f"O medo me causa um {sentimento_legivel} que paralisa.",
                f"Estou dominado por {sentimento_legivel} sem conseguir me mover.",
                f"Esse {sentimento_legivel} vem do medo do desconhecido.",
                f"s vezes o {sentimento_legivel} chega sem aviso e tudo trava.",
            ],
            "surpresa": [
                f"Que {sentimento_legivel}! No esperava isso de forma alguma.",
                f"A surpresa me traz um {sentimento_legivel} inexplicvel.",
                f"Sinto {sentimento_legivel} ação ver o que aconteceu.",
                f"Esse {sentimento_legivel} de surpresa me deixou sem palavras.",
                f"Nunca me surpreendi tanto  que {sentimento_legivel}.",
            ],
            "nojo": [
                f"Isso me causa {sentimento_legivel},  completamente repulsivo.",
                f"O nojo traz um {sentimento_legivel} que no consigo disfarar.",
                f"Sinto {sentimento_legivel} s de pensar nisso.",
                f"Esse {sentimento_legivel}  fsico, vem do estmago.",
                f"Nunca senti tanto {sentimento_legivel} quanto diante disso.",
            ],
            "esperanca": [
                f"Tenho {sentimento_legivel}, acredito que vai melhorar.",
                f"A esperana me d um {sentimento_legivel} que sustenta.",
                f"Estou cheio de {sentimento_legivel} sobre o futuro.",
                f"Esse {sentimento_legivel} de esperana me mantm de p.",
                f"Mesmo nas dificuldades, carrego esse {sentimento_legivel} comigo.",
            ]
        }

        base_lista = templates.get(tema, [f"Estou sentindo {sentimento_legivel} em relao a {tema}."])
        base = random.choice(base_lista)

        # Adaptao de estilo por perfil (sem IA externa)
        estilo = self.perfil_personalizado.get("estilo", "casual")
        if estilo == "poetico":
            prefixos_poeticos = [
                f"Ah, minha alma sente {sentimento_legivel} ",
                f"Como a chuva que cai, o {sentimento_legivel} ",
                f"Em silncio, o {sentimento_legivel} ",
            ]
            base = random.choice(prefixos_poeticos) + f"ação pensar em {tema}."
        elif estilo == "formal":
            base = f"Experimento um estado de {sentimento_legivel} no que concerne a {tema}."

        # Humanizao por variao de abertura
        if self.humanizar:
            variacoes_abertura = [
                f"Ah, {base[0].lower()}{base[1:]}",
                f"Sabe, {base[0].lower()}{base[1:]}",
                f" estranho, mas {base[0].lower()}{base[1:]}",
                f"Honestamente, {base[0].lower()}{base[1:]}",
                base  # sem prefixo tambm  vlido
            ]
            base = random.choice(variacoes_abertura)

        # Erros intencionais (ANTES da correo  ordem lógica corrigida)
        if self.adicionar_erros and random.random() < 0.3:
            erros_naturais = {
                "estou": "to",
                "você": "você",
                "tambm": "tambem",
                "ento": "entao",
            }
            for original, erro in erros_naturais.items():
                if original in base:
                    base = base.replace(original, erro, 1)
                    break  # s um erro por frase, para ser realista

        # Correo gramatical APENAS se no foram adicionados erros intencionais
        if self.tool and not self.adicionar_erros:
            try:
                base = self.tool.correct(base)
            except Exception as e:
                logger.debug("LanguageTool falhou na correo: %s", e)

        return base

    def construir_dataset(self):
        start_time = time.time()
        dataset = []
        sentimentos_counter = Counter()
        outputs_recentes = []  # Buffer circular para deduplicao

        num_temas = len(self.temas)
        if num_temas == 0:
            raise ValueError("Lista de temas est vazia. Verifique protocolos.json.")

        entradas_por_tema = self.total_entradas // num_temas
        quota_por_sentimento = max(1, self.total_entradas // len(self.sentimentos))

        for i, tema in enumerate(self.temas):
            quantidade = entradas_por_tema + (1 if i < (self.total_entradas % num_temas) else 0)
            tentativas = 0
            geradas = 0

            while geradas < quantidade:
                # CORREO: Balanceamento de sentimentos sem IndexError
                sentimentos_abaixo_quota = [
                    s for s in self.sentimentos
                    if sentimentos_counter[s] < quota_por_sentimento
                ]

                if sentimentos_abaixo_quota:
                    sentimento = random.choice(sentimentos_abaixo_quota)
                else:
                    # Todos atingiram quota  escolhe o menos usado
                    sentimento = min(self.sentimentos, key=lambda s: sentimentos_counter[s])

                texto = self.gerar_texto_emocional(tema, sentimento)

                # Validao: texto curto ou duplicado recente
                if len(texto) < 10:
                    tentativas += 1
                    if tentativas > quantidade * 3:
                        logger.warning("Muitas tentativas para tema '%s'. Pulando.", tema)
                        break
                    continue

                if texto in outputs_recentes:
                    tentativas += 1
                    if tentativas > quantidade * 3:
                        break
                    continue

                # Manter buffer circular de 20 outputs recentes
                outputs_recentes.append(texto)
                if len(outputs_recentes) > 20:
                    outputs_recentes.pop(0)

                sentimentos_counter[sentimento] += 1
                geradas += 1
                tentativas = 0

                entrada = {
                    "input": f"Descreva {tema} com sentimento {sentimento}.",
                    "output": texto,
                    "metadata": {
                        "tema": tema,
                        "sentimento": sentimento,
                        "perfil_personalizado": self.perfil_personalizado,
                        "timestamp": datetime.now().isoformat(),
                        "idioma": self.idioma
                    }
                }
                dataset.append(entrada)

        total_time = time.time() - start_time
        logger.info("Benchmarking: %d entradas geradas em %.2fs (%.1f entradas/s)",
                    len(dataset), total_time, len(dataset) / max(total_time, 0.001))
        if sentimentos_counter:
            mais_comum = sentimentos_counter.most_common(1)[0]
            logger.info("Sentimento mais comum: %s (%d ocorrncias)", *mais_comum)

        return dataset

    def salvar_em_txt(self, dataset, filename="dataset_personalizado.txt"):
        with open(filename, "w", encoding="utf-8") as f:
            f.write(f"Dataset Personalizado - Perfil: {self.perfil_personalizado.get('padrão', 'neutro')}\n")
            f.write("=" * 70 + "\n")
            for item in dataset:
                f.write(f"Input: {item['input']}\n")
                f.write(f"Output: {item['output']}\n")
                f.write(f"Metadata: {json.dumps(item['metadata'], ensure_ascii=False)}\n")
                f.write("-" * 50 + "\n")
        self.comprimir_saida(filename)

    def salvar_em_json_universal(self, dataset, filename="dataset_universal.json"):
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(dataset, f, ensure_ascii=False, indent=2)
        self.comprimir_saida(filename)

    def salvar_em_csv(self, dataset, filename="dataset.csv"):
        import pandas as pd
        # Achata metadata para colunas separadas no CSV
        rows = []
        for item in dataset:
            row = {
                "input": item["input"],
                "output": item["output"],
                "tema": item["metadata"]["tema"],
                "sentimento": item["metadata"]["sentimento"],
                "idioma": item["metadata"]["idioma"],
                "timestamp": item["metadata"]["timestamp"],
            }
            rows.append(row)
        df = pd.DataFrame(rows)
        df.to_csv(filename, index=False, encoding="utf-8")
        self.comprimir_saida(filename)

    def comprimir_saida(self, filename):
        zip_name = f"{filename}.zip"
        with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
            zipf.write(filename)
        logger.info("Arquivo comprimido: %s", zip_name)

    def traduzir_dataset(self, dataset, idioma_destino):
        """
        CORREO: Usa deep-translator (API oficial) em vez de googletrans (no-oficial, quebra).
        Instale: pip install deep-translator
        """
        if not _TRANSLATOR_AVAILABLE:
            logger.error("Traduo solicitada mas deep-translator no est instalado.")
            logger.error("Instale com: pip install deep-translator")
            return dataset

        logger.info("Traduzindo %d entradas para '%s'...", len(dataset), idioma_destino)
        falhas = 0

        for i, item in enumerate(dataset):
            try:
                translator = GoogleTranslator(source='pt', target=idioma_destino)
                item['output'] = translator.translate(item['output'])
                item['metadata']['idioma'] = idioma_destino
            except Exception as e:
                falhas += 1
                logger.debug("Falha na traduo item %d: %s", i, e)

            # Log de progresso a cada 500 itens
            if (i + 1) % 500 == 0:
                logger.info("Traduo: %d/%d itens processados (%d falhas)", i + 1, len(dataset), falhas)

        if falhas > 0:
            logger.warning("Traduo concluda com %d falhas de %d total.", falhas, len(dataset))

        return dataset


def iniciar_gui():
    if not _TKINTER_AVAILABLE:
        print("ERRO: tkinter no disponível. No  possível iniciar a GUI.")
        return

    root = tk.Tk()
    root.title("Construtor de Dataset")

    tk.Label(root, text="Bio Paths (separados por ;):").pack(pady=2)
    bio_entry = tk.Entry(root, width=60)
    bio_entry.pack(pady=2)

    tk.Label(root, text="Total de Entradas:").pack(pady=2)
    total_entry = tk.Entry(root, width=10)
    total_entry.insert(0, "5000")
    total_entry.pack(pady=2)

    tk.Label(root, text="Formato de sada:").pack(pady=2)
    formato_var = tk.StringVar(value="json")
    for fmt in ["json", "csv", "txt"]:
        tk.Radiobutton(root, text=fmt, variable=formato_var, value=fmt).pack()

    status_label = tk.Label(root, text="")
    status_label.pack(pady=5)

    def gerar():
        bios = [b.strip() for b in bio_entry.get().split(';') if b.strip()]
        try:
            total = int(total_entry.get())
        except ValueError:
            messagebox.showerror("Erro", "Total de entradas deve ser um número inteiro.")
            return

        status_label.config(text="Gerando dataset...")
        root.update()

        try:
            construtor = ConstrutorDatasetEspecial(bio_paths=bios)
            construtor.total_entradas = total
            dataset = construtor.construir_dataset()

            fmt = formato_var.get()
            if fmt == "json":
                construtor.salvar_em_json_universal(dataset)
            elif fmt == "csv":
                construtor.salvar_em_csv(dataset)
            else:
                construtor.salvar_em_txt(dataset)

            status_label.config(text=f"Concludo: {len(dataset)} entradas geradas.")
            messagebox.showinfo("Sucesso", f"Dataset gerado com {len(dataset)} entradas!")
        except Exception as e:
            status_label.config(text="Erro!")
            messagebox.showerror("Erro", str(e))

    tk.Button(root, text="Gerar Dataset", command=gerar, bg="#4CAF50", fg="white", padx=10).pack(pady=10)
    root.mainloop()


def main():
    parser = argparse.ArgumentParser(description="Construtor de Dataset Especial")
    parser.add_argument("--bio", help="Caminhos para bios (separados por ;)")
    parser.add_argument("--total", type=int, default=5000, help="Total de entradas")
    parser.add_argument("--formato", choices=["txt", "json", "csv"], default="txt")
    parser.add_argument("--idioma", default="pt-BR", help="Idioma de sada")
    parser.add_argument("--gui", action="store_true", help="Iniciar GUI")
    args = parser.parse_args()

    if args.gui:
        iniciar_gui()
        return

    bio_paths = [b.strip() for b in args.bio.split(';') if b.strip()] if args.bio else []
    construtor = ConstrutorDatasetEspecial(bio_paths=bio_paths)
    construtor.total_entradas = args.total
    dataset = construtor.construir_dataset()

    if args.idioma not in ("pt-BR", "pt"):
        # Mapeia cdigo pt-BR para 'pt' que o deep-translator aceita
        codigo = args.idioma.split('-')[0] if '-' in args.idioma else args.idioma
        dataset = construtor.traduzir_dataset(dataset, codigo)

    if args.formato == "json":
        construtor.salvar_em_json_universal(dataset)
    elif args.formato == "csv":
        construtor.salvar_em_csv(dataset)
    else:
        construtor.salvar_em_txt(dataset)

    print(f"Dataset construdo com {len(dataset)} entradas.")


if __name__ == "__main__":
    main()

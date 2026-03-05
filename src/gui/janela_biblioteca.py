# -*- coding: utf-8 -*-
"""
ARCA CELESTIAL GENESIS - JANELA/ABA BIBLIOTECA TEOLÓGICA (UI)
Interface gráfica para consulta Í  biblioteca teológica.
"""
import logging
import tkinter as tk
from tkinter import messagebox
from pathlib import Path
from typing import Dict, Any, Optional

import customtkinter as ctk

# --- IMPORTS LOCAIS ---
from src.biblioteca.interface_biblioteca import BibliotecaJWOtimizada
from src.biblioteca.biblioteca_para_almas import BibliotecaParaAlmas

logger = logging.getLogger("JanelaBiblioteca")


class JanelaBiblioteca(ctk.CTkFrame):
    """
    Frame da UI para consulta Í  biblioteca teológica.
    Pode ser uma aba em uma janela principal ou um frame dentro dela.
    """
    def __init__(
        self,
        parent: ctk.CTk,
        biblioteca_principal: BibliotecaJWOtimizada,
        # Exemplos de injeção de dependências da UI principal
        # coracao: Optional[CoracaoOrquestrador] = None,
        # memoria: Optional[SistemaMemoriaHibrido] = None,
        **kwargs
    ):
        super().__init__(parent, **kwargs)
        self.biblioteca_principal = biblioteca_principal
        self._ultimo_resultado: Optional[Dict[str, Any]] = None

        self.setup_ui()

    def setup_ui(self):
        """Configura os elementos da interface."""
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)  # A área de resultados ocupa o espaço restante

        # --- 1.Título ---
        lbl_titulo = ctk.CTkLabel(self, text="ðŸ” Consulta Í  Biblioteca Teológica",
                                  font=ctk.CTkFont(size=16, weight="bold"))
        lbl_titulo.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

        # --- 2.Frame de Entrada ---
        frame_entrada = ctk.CTkFrame(self)
        frame_entrada.grid(row=1, column=0, padx=10, pady=5, sticky="ew")
        frame_entrada.grid_columnconfigure(1, weight=1)

        lbl_pergunta = ctk.CTkLabel(frame_entrada, text="Pergunta:")
        lbl_pergunta.grid(row=0, column=0, padx=(0, 5), pady=5, sticky="w")
        self.entry_pergunta = ctk.CTkEntry(frame_entrada, placeholder_text="Digite sua pergunta (ex: João 3:16 ou o que a Bíblia diz sobre fé?)")
        self.entry_pergunta.grid(row=0, column=1, padx=5, pady=5, sticky="ew", columnspan=3)

        lbl_fonte = ctk.CTkLabel(frame_entrada, text="Fonte:")
        lbl_fonte.grid(row=1, column=0, padx=(0, 5), pady=5, sticky="w")
        self.optionmenu_fonte = ctk.CTkOptionMenu(frame_entrada, values=["tudo", "biblia", "sentinela", "despertai", "livros"])
        self.optionmenu_fonte.set("tudo")
        self.optionmenu_fonte.grid(row=1, column=1, padx=5, pady=5, sticky="w")

        lbl_n_resultados = ctk.CTkLabel(frame_entrada, text="Resultados:")
        lbl_n_resultados.grid(row=1, column=2, padx=(10, 5), pady=5, sticky="w")
        self.spinbox_n_resultados = ctk.CTkEntry(frame_entrada, width=60)
        self.spinbox_n_resultados.insert(0, "5")  # Valor padrão
        self.spinbox_n_resultados.grid(row=1, column=3, padx=5, pady=5, sticky="w")

        # Botão de Consulta
        btn_consultar = ctk.CTkButton(frame_entrada, text="ðŸ” Consultar", command=self.on_consultar_click)
        btn_consultar.grid(row=0, column=4, rowspan=2, padx=10, pady=5, sticky="ns")

        # --- 3. Írea de Resultados ---
        # Usaremos o CTkScrollableFrame para conter widgets de resultado
        self.frame_resultados_scroll = ctk.CTkScrollableFrame(self)
        self.frame_resultados_scroll.grid(row=2, column=0, padx=10, pady=5, sticky="nsew")

        self.lbl_resultados_placeholder = ctk.CTkLabel(self.frame_resultados_scroll, text="Resultados aparecerão aqui após a consulta.", justify="left")
        self.lbl_resultados_placeholder.pack(fill="both", expand=True, padx=5, pady=5)

        # --- 4.Frame de Controles (Exportar, Estatísticas) ---
        frame_controles = ctk.CTkFrame(self)
        frame_controles.grid(row=3, column=0, padx=10, pady=5, sticky="ew")
        frame_controles.grid_columnconfigure(2, weight=1)

        btn_exportar_md = ctk.CTkButton(frame_controles, text="Exportar (.md)", command=lambda: self.on_exportar_click("markdown"))
        btn_exportar_md.grid(row=0, column=0, padx=5, pady=5)

        btn_exportar_json = ctk.CTkButton(frame_controles, text="Exportar (.json)", command=lambda: self.on_exportar_click("json"))
        btn_exportar_json.grid(row=0, column=1, padx=5, pady=5)

        btn_estatisticas = ctk.CTkButton(frame_controles, text="Estatísticas", command=self.on_estatisticas_click)
        btn_estatisticas.grid(row=0, column=2, padx=5, pady=5, sticky="e")

    def on_consultar_click(self):
        """Manipulador do clique no botão 'Consultar'."""
        pergunta = self.entry_pergunta.get().strip()
        if not pergunta:
            messagebox.showwarning("Aviso", "Por favor, digite uma pergunta.")
            return

        fonte = self.optionmenu_fonte.get()
        try:
            n_resultados = int(self.spinbox_n_resultados.get())
        except ValueError:
            messagebox.showerror("Erro", "Número de resultados deve ser um número inteiro.")
            return

        logger.info(f"Solicitando consulta via UI: '{pergunta}' (Fonte: {fonte}, N: {n_resultados})")

        # Limpar resultados anteriores
        for widget in self.frame_resultados_scroll.winfo_children():
            widget.destroy()

        # Mostrar mensagem de carregamento
        lbl_loading = ctk.CTkLabel(self.frame_resultados_scroll, text="ðŸ” Buscando...", font=ctk.CTkFont(slant="italic"))
        lbl_loading.pack(pady=10)

        # Atualizar a UI antes de chamar a função bloqueante
        self.update_idletasks()

        try:
            # Chamar a função de consulta (em uma thread separada se for bloqueante por muito tempo)
            # Por enquanto, chamamos diretamente. Se travar a UI, usar threading.
            resultado = self.biblioteca_principal.consultar(
                pergunta=pergunta,
                fonte_preferida=fonte,
                n_resultados=n_resultados
            )

            # armazenar último resultado para exportação
            self._ultimo_resultado = resultado

            # Atualizar UI com resultados
            self._atualizar_resultados_ui(resultado)

        except Exception as e:
            logger.error(f"Erro na consulta via UI: {e}")
            messagebox.showerror("Erro", f"Erro ao realizar consulta: {e}")

    def _atualizar_resultados_ui(self, resultado: Dict[str, Any]):
        """Atualiza a área de resultados com os dados da consulta."""
        # Limpar área de resultados
        for widget in self.frame_resultados_scroll.winfo_children():
            widget.destroy()

        # Exibir tempo total
        tempo_total = resultado.get('tempo_total_ms', 'N/A')
        lbl_tempo = ctk.CTkLabel(self.frame_resultados_scroll, text=f"â±ï¸ Tempo total: {tempo_total} ms", font=ctk.CTkFont(weight="bold"))
        lbl_tempo.pack(anchor="w", padx=5, pady=(0, 5))

        # Exibir análise de contexto (se houver)
        analise = resultado.get('analise_contexto', {})
        if analise:
            tipo_busca = analise.get('tipo_busca', 'N/A')
            palavras_chave = ', '.join(analise.get('palavras_chave', []))
            lbl_analise = ctk.CTkLabel(self.frame_resultados_scroll, text=f"ðŸ§  Análise: Tipo='{tipo_busca}', Palavras-chave='{palavras_chave}'", font=ctk.CTkFont(size=12))
            lbl_analise.pack(anchor="w", padx=5, pady=(0, 5))

        # Exibir resultados
        resultados_lista = resultado.get('resultados', [])
        previews_lista = resultado.get('previews', [])
        if not resultados_lista:
            lbl_sem_result = ctk.CTkLabel(self.frame_resultados_scroll, text="âŒ Nenhum resultado encontrado.", text_color="gray")
            lbl_sem_result.pack(pady=10)
            return

        for i, (res, prev) in enumerate(zip(resultados_lista, previews_lista)):
            frame_result_item = ctk.CTkFrame(self.frame_resultados_scroll)
            frame_result_item.pack(fill="x", padx=5, pady=2, expand=True)

            # Cabeçalho do resultado
            fonte = res.get('fonte', 'Desconhecida')
            similaridade = res.get('similaridade', 'N/A')
            try:
                sim_str = f"{similaridade:.2f}"
            except Exception:
                sim_str = str(similaridade)
            lbl_header = ctk.CTkLabel(frame_result_item, text=f"ðŸ“„ {i+1}. Fonte: {fonte} (Sim.: {sim_str})", font=ctk.CTkFont(weight="bold"))
            lbl_header.pack(anchor="w", padx=5, pady=(2, 0))

            # Conteúdo/Preview
            preview_text = prev.get('preview', res.get('conteudo', 'N/A'))  # Usa preview gerado, se disponível, senão o conteúdo bruto
            lbl_content = ctk.CTkLabel(frame_result_item, text=preview_text, wraplength=700, justify="left")
            lbl_content.pack(anchor="w", padx=10, pady=(0, 5), fill="x", expand=True)

    def on_exportar_click(self, formato: str):
        """Manipulador do clique em botões de exportação."""
        if hasattr(self, '_ultimo_resultado') and self._ultimo_resultado:
            try:
                caminho_exportado = self.biblioteca_principal.exportador.exportar(self._ultimo_resultado, formato=formato)
                messagebox.showinfo("Sucesso", f"Resultado exportado para:\n{caminho_exportado}")
            except Exception as e:
                logger.error(f"Erro ao exportar via UI: {e}")
                messagebox.showerror("Erro", f"Erro ao exportar resultado: {e}")
        else:
            messagebox.showwarning("Aviso", "Nenhum resultado recente para exportar. Faça uma consulta primeiro.")

    def on_estatisticas_click(self):
        """Manipulador do clique no botão 'Estatísticas'."""
        try:
            estatisticas = self.biblioteca_principal.obter_estatisticas()
            # Exibir estatísticas em uma messagebox ou em uma nova janela/aba
            stats_text = "\n".join([f"{k}: {v}" for k, v in estatisticas.items()])
            messagebox.showinfo("Estatísticas da Biblioteca", stats_text)
        except Exception as e:
            logger.error(f"Erro ao obter estatísticas via UI: {e}")
            messagebox.showerror("Erro", f"Erro ao obter estatísticas: {e}")


# --- Fim do arquivo src/biblioteca/janela_biblioteca.py ---

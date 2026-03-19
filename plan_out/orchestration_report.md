# Orchestration Report

Project root: E:\Arca_Celestial_Genesis_Alfa_Omega

Analyzed modules: 135

## Entry candidates

- src.src.api.api_consultor (src\api\api_consultor.py)
- src.src.camara.consultor_biblico_local (src\camara\consultor_biblico_local.py)
- src.src.conexoes.conexoes_basicas (src\conexoes\conexoes_basicas.py)
- src.src.config.inicializador_sistema (src\config\inicializador_sistema.py)
- src.src.consulado.analisador_intencao (src\consulado\analisador_intencao.py)
- src.src.consulado.gerenciador_aliadas (src\consulado\gerenciador_aliadas.py)
- src.src.core.carregador_sistemico (src\core\carregador_sistemico.py)
- src.src.core.detector_hdd_hitachi (src\core\detector_hdd_hitachi.py)
- src.src.core.dispositivo_ai_to_ai (src\core\dispositivo_ai_to_ai.py)
- src.src.core.gpu_manager (src\core\gpu_manager.py)
- src.src.emocoes.auto_experimentacao (src\emocoes\auto_experimentacao.py)
- src.src.emocoes.detector_emocional (src\emocoes\detector_emocional.py)
- src.src.emocoes.estado_emocional (src\emocoes\estado_emocional.py)
- src.src.emocoes.inteligencia_emocional_ativa (src\emocoes\inteligencia_emocional_ativa.py)
- src.src.emocoes.motor_curiosidade (src\emocoes\motor_curiosidade.py)
- src.src.emocoes.sonhador_individual (src\emocoes\sonhador_individual.py)
- src.src.encarnacao_e_interacao.capela (src\encarnacao_e_interacao\capela.py)
- src.src.encarnacao_e_interacao.encarnacao_api (src\encarnacao_e_interacao\encarnacao_api.py)
- src.src.encarnacao_e_interacao.sensor_presenca (src\encarnacao_e_interacao\sensor_presenca.py)
- src.src.memoria.cache_hdd (src\memoria\cache_hdd.py)
- src.src.memoria.detector_hardware (src\memoria\detector_hardware.py)
- src.src.memoria.detector_hdd_hitachi (src\memoria\detector_hdd_hitachi.py)
- src.src.memoria.facade_factory (src\memoria\facade_factory.py)
- src.src.memoria.gerenciador_memoria_cromadb_isolado (src\memoria\gerenciador_memoria_cromadb_isolado.py)
- src.src.memoria.memoria_extensao (src\memoria\memoria_extensao.py)
- src.src.modules.arquiteto_de_mundos (src\modules\arquiteto_de_mundos.py)
- src.src.modules.carregador_protocolos (src\modules\carregador_protocolos.py)
- src.src.modules.cronicas_e_testemunhos (src\modules\cronicas_e_testemunhos.py)
- src.src.modules.gerenciador_profiles_permanentes (src\modules\gerenciador_profiles_permanentes.py)
- src.src.tools.build_import_graph (src\tools\build_import_graph.py)
- src.src.tools.check_env (src\tools\check_env.py)
- src.src.ui.interface_arca_atualizada (src\ui\interface_arca_atualizada.py)
- src.src.utils.timing_decorator (src\utils\timing_decorator.py)

## Suggested connections (summary)

### src.src.api.api_consultor
- path: src\api\api_consultor.py
- role_guess: api
- is_entry_candidate: True
- imports (11): ['__future__', 'aiohttp', 'asyncio', 'datetime', 'json', 'logging', 'math', 'os', 'pathlib', 'time', 'typing']
- callers_inferred (0): []
- call_targets_inferred (8): ['aiohttp', 'asyncio', 'datetime', 'json', 'logging', 'os', 'pathlib', 'time']
- defined_funcs: ['__init__', '_cache_get', '_cache_set', '_carregar_config', '_obter_chave_api', 'consultar_inteligente_sincrono', 'consultar_noticias_sincrono', 'obter_apis_disponiveis']

### src.src.api.api_manager
- path: src\api\api_manager.py
- role_guess: core
- is_entry_candidate: False
- imports (8): ['__future__', 'asyncio', 'json', 'logging', 'pathlib', 'src.config', 'time', 'typing']
- callers_inferred (0): []
- call_targets_inferred (4): ['asyncio', 'logging', 'src.config', 'time']
- defined_funcs: ['__init__', '_cache_get', '_cache_set', '_call_consulado', '_chamar_via_consulado', '_registrar_na_memoria', '_validar_acao_externa', 'desligar']

### src.src.api
- path: src\api\__init__.py
- role_guess: api
- is_entry_candidate: False
- imports (8): ['__future__', 'api_consultor', 'api_manager', 'clients', 'handlers', 'logging', 'routes', 'typing']
- callers_inferred (0): []
- call_targets_inferred (1): ['logging']
- defined_funcs: []

### src.src.biblioteca.analisador_contexto
- path: src\biblioteca\analisador_contexto.py
- role_guess: io
- is_entry_candidate: False
- imports (7): ['__future__', 'collections', 'datetime', 'logging', 're', 'typing', 'unicodedata']
- callers_inferred (0): []
- call_targets_inferred (5): ['collections', 'datetime', 'logging', 're', 'unicodedata']
- defined_funcs: ['__init__', '_extract_reference', '_extrair_palavras_chave_simples', '_normalize_text', '_tokenize_and_rank', 'analisar']

### src.src.biblioteca.biblioteca_para_almas
- path: src\biblioteca\biblioteca_para_almas.py
- role_guess: io
- is_entry_candidate: False
- imports (5): ['__future__', 'asyncio', 'hashlib', 'logging', 'typing']
- callers_inferred (0): []
- call_targets_inferred (3): ['asyncio', 'hashlib', 'logging']
- defined_funcs: ['__init__', '_cache_key', 'consultar', 'obter_estatisticas', 'pesquisar_biblia', 'pesquisar_doutrina']

### src.src.biblioteca.busca_hibrida
- path: src\biblioteca\busca_hibrida.py
- role_guess: io
- is_entry_candidate: False
- imports (6): ['__future__', 'logging', 're', 'src.memoria.sistema_memoria', 'typing', 'unicodedata']
- callers_inferred (0): []
- call_targets_inferred (2): ['logging', 're']
- defined_funcs: ['__init__', '_buscar_referencia_vetorial', '_buscar_vetorial', '_fallback_busca_simples', '_formatar_resultados_retrieve_similar', '_formatar_resultados_search', 'buscar']

### src.src.biblioteca.exportador_resultados
- path: src\biblioteca\exportador_resultados.py
- role_guess: io
- is_entry_candidate: False
- imports (7): ['__future__', 'collections', 'datetime', 'logging', 're', 'typing', 'unicodedata']
- callers_inferred (0): []
- call_targets_inferred (5): ['collections', 'datetime', 'logging', 're', 'unicodedata']
- defined_funcs: ['__init__', '_extract_reference', '_extrair_palavras_chave_simples', '_normalize_text', '_tokenize_and_rank', 'analisar']

### src.src.biblioteca.indexador_incremental
- path: src\biblioteca\indexador_incremental.py
- role_guess: io
- is_entry_candidate: False
- imports (15): ['PyPDF2', '__future__', 'concurrent.futures', 'datetime', 'hashlib', 'io', 'logging', 'os', 'pathlib', 'src.memoria.sistema_memoria', 'threading', 'time', 'typing', 'watchdog.events', 'watchdog.observers']
- callers_inferred (0): []
- call_targets_inferred (9): ['PyPDF2', 'concurrent.futures', 'datetime', 'hashlib', 'logging', 'pathlib', 'threading', 'time', 'watchdog.observers']
- defined_funcs: ['__init__', '_chunk_text', '_delayed', '_preprocessar_texto', '_processar_existentes', '_read_pdf_text', '_schedule_processing', '_sha256_of_bytes', 'adicionar_pdf', 'iniciar_monitoramento', 'on_created', 'parar_monitoramento', 'shutdown']

### src.src.biblioteca.interface_biblioteca
- path: src\biblioteca\interface_biblioteca.py
- role_guess: io
- is_entry_candidate: False
- imports (16): ['__future__', 'asyncio', 'hashlib', 'logging', 'pathlib', 'src.biblioteca.analisador_contexto', 'src.biblioteca.busca_hibrida', 'src.biblioteca.cache_consultas', 'src.biblioteca.exportador_resultados', 'src.biblioteca.monitor_biblioteca', 'src.biblioteca.preview', 'src.biblioteca.reranking', 'src.core.coracao_orquestrador', 'src.memoria.sistema_memoria', 'time', 'typing']
- callers_inferred (0): []
- call_targets_inferred (12): ['asyncio', 'hashlib', 'logging', 'pathlib', 'src.biblioteca.analisador_contexto', 'src.biblioteca.busca_hibrida', 'src.biblioteca.cache_consultas', 'src.biblioteca.exportador_resultados', 'src.biblioteca.monitor_biblioteca', 'src.biblioteca.preview', 'src.biblioteca.reranking', 'time']
- defined_funcs: ['__init__', '_gerar_chave_cache', 'consultar', 'limpar_cache', 'obter_estatisticas']

### src.src.biblioteca.janela_biblioteca
- path: src\biblioteca\janela_biblioteca.py
- role_guess: io
- is_entry_candidate: False
- imports (7): ['customtkinter', 'logging', 'pathlib', 'src.biblioteca.biblioteca_para_almas', 'src.biblioteca.interface_biblioteca', 'tkinter', 'typing']
- callers_inferred (0): []
- call_targets_inferred (3): ['customtkinter', 'logging', 'tkinter']
- defined_funcs: ['__init__', '_atualizar_resultados_ui', 'on_consultar_click', 'on_estatisticas_click', 'on_exportar_click', 'setup_ui']

### src.src.biblioteca.monitor_biblioteca
- path: src\biblioteca\monitor_biblioteca.py
- role_guess: io
- is_entry_candidate: False
- imports (5): ['__future__', 'datetime', 'logging', 'threading', 'typing']
- callers_inferred (0): []
- call_targets_inferred (3): ['datetime', 'logging', 'threading']
- defined_funcs: ['__init__', 'obter_metricas', 'registrar_consulta', 'registrar_consulta_falha', 'registrar_consulta_sucesso', 'registrar_hit_cache', 'resetar_metricas']

### src.src.biblioteca.preview
- path: src\biblioteca\preview.py
- role_guess: io
- is_entry_candidate: False
- imports (6): ['__future__', 'difflib', 'logging', 're', 'typing', 'unicodedata']
- callers_inferred (0): []
- call_targets_inferred (4): ['difflib', 'logging', 're', 'unicodedata']
- defined_funcs: ['__init__', '_extrair_palavras_chave_simples', '_gerar_preview_individual', '_normalize_text', '_preview_por_keywords', '_preview_por_sequence_match', '_trecho_inicio', 'gerar_previews']

### src.src.biblioteca.reranking
- path: src\biblioteca\reranking.py
- role_guess: io
- is_entry_candidate: False
- imports (5): ['__future__', 'logging', 're', 'typing', 'unicodedata']
- callers_inferred (0): []
- call_targets_inferred (3): ['logging', 're', 'unicodedata']
- defined_funcs: ['__init__', '_calcular_pontos_individuais', '_extrair_palavras_chave', '_normalize_text', 'rerank']

### src.src.biblioteca
- path: src\biblioteca\__init__.py
- role_guess: io
- is_entry_candidate: False
- imports (13): ['__future__', 'analisador_contexto', 'biblioteca_jw_otimizada', 'biblioteca_para_almas', 'busca_hibrida', 'cache_consultas', 'exportador_resultados', 'indexador_incremental', 'logging', 'monitor_biblioteca', 'preview_inteligente', 'reranking_inteligente', 'typing']
- callers_inferred (0): []
- call_targets_inferred (1): ['logging']
- defined_funcs: []

### src.src.camara.analisar_leis
- path: src\camara\analisar_leis.py
- role_guess: unknown
- is_entry_candidate: False
- imports (2): ['json', 'pathlib']
- callers_inferred (0): []
- call_targets_inferred (2): ['json', 'pathlib']
- defined_funcs: ['classificar_aceito']

### src.src.camara.camara_deliberativa
- path: src\camara\camara_deliberativa.py
- role_guess: unknown
- is_entry_candidate: False
- imports (9): ['__future__', 'datetime', 'json', 'logging', 'pathlib', 'src.config.config', 'threading', 'time', 'typing']
- callers_inferred (0): []
- call_targets_inferred (4): ['datetime', 'logging', 'src.config.config', 'threading']
- defined_funcs: ['__init__', '_coletar_eventos', 'consultar_julgamentos', 'consultar_registros_vidro', 'consultar_scr', 'gerar_relatorio_manual', 'obter_relatorio_atual', 'shutdown']

### src.src.camara.camara_executiva
- path: src\camara\camara_executiva.py
- role_guess: unknown
- is_entry_candidate: False
- imports (16): ['PyPDF2', '__future__', 'base64', 'dataclasses', 'datetime', 'enum', 'hashlib', 'hmac', 'json', 'logging', 'os', 'pathlib', 'threading', 'time', 'typing', 'uuid']
- callers_inferred (0): []
- call_targets_inferred (14): ['PyPDF2', 'base64', 'dataclasses', 'datetime', 'hashlib', 'hmac', 'json', 'logging', 'os', 'pathlib', 'threading', 'time', 'typing', 'uuid']
- defined_funcs: ['__init__', '_atomic_write', '_carregar_biblia', '_carregar_livro', '_carregar_novas_leis', '_criar_lei_da_proposta', '_decidir_proposta', '_hash_password', '_load_users', '_save_users', '_username_from_token', 'adicionar_lei', 'adicionar_lei_aprovada_ais', 'buscar_em_categoria', 'buscar_lei_por_protocolo', 'buscar_leis_aplicaveis', 'buscar_leis_por_categoria', 'buscar_por_tema', 'carregar_categorias_classificadas', 'consultar_biblia_para_lei', 'consultar_fundamento_biblico', 'consultar_lei_por_protocolo', 'create_user', 'fornecer_leis_para_judiciario', 'from_dict', 'generate_protocolo', 'generate_token', 'has_role', 'login', 'notificar_falta_lei', 'obter_estatisticas_legislacao', 'parse_enum', 'propor_nova_lei', 'remover_lei', 'revogar_lei', 'salvar_livro', 'salvar_novas_leis', 'shutdown', 'to_dict', 'verify_password', 'verify_token', 'votar_proposta_lei', 'voto_final_criador']

### src.src.camara.camara_judiciaria
- path: src\camara\camara_judiciaria.py
- role_guess: unknown
- is_entry_candidate: False
- imports (14): ['__future__', 'concurrent.futures', 'dataclasses', 'datetime', 'enum', 'json', 'logging', 'pathlib', 'queue', 'src.utils.config_utils', 'threading', 'time', 'typing', 'uuid']
- callers_inferred (0): []
- call_targets_inferred (10): ['concurrent.futures', 'dataclasses', 'datetime', 'json', 'logging', 'pathlib', 'src.utils.config_utils', 'threading', 'time', 'uuid']
- defined_funcs: ['__init__', '_append', '_build_index', '_carregar_processo_do_santuario', '_iniciar_analise_processo_em_thread', '_notificar_ui', '_parse_tipo_julgamento', '_refinar_leis_por_categoria', '_refresh', '_salvar_processo_no_santuario', 'adicionar_evidencia', 'apelar_ao_criador', 'aplicar_sancao', 'aplicar_sentenca_judicial', 'atualizar_status', 'buscar', 'buscar_em_categoria', 'buscar_leis_aplicaveis', 'iniciar_julgamento', 'injetar_camara_legislativa', 'injetar_consulado', 'injetar_modo_vidro', 'injetar_ui_queue', 'receber_denuncia', 'refresh', 'registrar_decisao', 'restaurar_arquivo_padrao', 'revogar_acesso_internet', 'shutdown', 'suspender_acesso_para_alma', 'to_dict']

### src.src.camara.camara_legislativa
- path: src\camara\camara_legislativa.py
- role_guess: unknown
- is_entry_candidate: False
- imports (17): ['PyPDF2', '__future__', 'base64', 'dataclasses', 'datetime', 'enum', 'hashlib', 'hmac', 'json', 'logging', 'os', 'pathlib', 'tempfile', 'threading', 'time', 'typing', 'uuid']
- callers_inferred (0): []
- call_targets_inferred (14): ['PyPDF2', 'base64', 'dataclasses', 'datetime', 'hashlib', 'hmac', 'json', 'logging', 'os', 'pathlib', 'tempfile', 'threading', 'time', 'uuid']
- defined_funcs: ['__init__', '_atomic_write_json', '_audit', '_carregar_biblia', '_carregar_categorias', '_carregar_livro', '_carregar_novas_leis', '_criar_lei_da_proposta', '_decidir_proposta', '_hash_password', '_load_users', '_map_enum', '_now_iso', '_safe_datetime_from_iso', '_safe_load_json', '_save_users', 'adicionar_lei', 'adicionar_lei_aprovada_ais', 'buscar_lei_por_protocolo', 'buscar_leis_aplicaveis', 'buscar_leis_por_categoria', 'buscar_por_tema', 'consultar_biblia_para_lei', 'consultar_fundamento_biblico', 'consultar_lei_por_protocolo', 'create_user', 'fornecer_leis_para_judiciario', 'from_dict', 'generate_token', 'has_role', 'notificar_falta_lei', 'obter_estatisticas_legislacao', 'propor_nova_lei', 'remover_lei', 'revogar_lei', 'salvar_livro', 'salvar_novas_leis', 'shutdown', 'to_dict', 'verify_password', 'verify_token', 'votar_proposta_lei', 'voto_final_criador']

### src.src.camara.consultor_biblico_local
- path: src\camara\consultor_biblico_local.py
- role_guess: unknown
- is_entry_candidate: True
- imports (13): ['PyPDF2', '__future__', 'argparse', 'fitz', 'json', 'logging', 'os', 'pathlib', 'pdf2image', 'pytesseract', 're', 'tempfile', 'typing']
- callers_inferred (0): []
- call_targets_inferred (11): ['PyPDF2', 'argparse', 'fitz', 'json', 'logging', 'os', 'pathlib', 'pdf2image', 'pytesseract', 're', 'tempfile']
- defined_funcs: ['__init__', '_atomic_write_json', '_cache_path_for_pdf', '_extract_text_with_cache', '_is_text_sufficient', '_load_pdf_directory', '_normalize_whitespace', '_safe_load_json', '_snippet_from_text', 'available_sources', 'buscar_por_tema', 'clear_cache', 'extract_text_pymupdf', 'extract_text_pypdf2', 'is_pdf_scanned', 'ocr_pdf_via_images', 'preprocess_all_pdfs']

### src.src.camara.modo_vidro_sentenca
- path: src\camara\modo_vidro_sentenca.py
- role_guess: unknown
- is_entry_candidate: False
- imports (10): ['datetime', 'enum', 'json', 'logging', 'pathlib', 'random', 'threading', 'time', 'typing', 'uuid']
- callers_inferred (0): []
- call_targets_inferred (8): ['datetime', 'json', 'logging', 'pathlib', 'random', 'threading', 'time', 'uuid']
- defined_funcs: ['__init__', '_acumular_para_relatorio_diario', '_aplicar_efeitos_iniciais_vidro', '_carregar_sentencas_ativas', '_contar_eventos_hoje', '_enviar_mensagem_direta', '_enviar_notificacao_evento', '_gerar_estatisticas_inutilidade', '_gerar_relatorio_diario_exclusao', '_gerar_relatorios_diarios_vidro', '_iniciar_espelho_existencial', '_mapear_punicao_para_violacao', '_notificar_scr_sobre_conclusao_vidro', '_notificar_sistema_sobre_vidro', '_receber_decisao_executiva_modificado', '_remover_efeitos_vidro', '_salvar_sentenca', '_solicitar_reflexao', '_thread_monitoramento_vidro', '_verificar_requisitos_ativacao', 'aplicar_sentenca_vidro', 'ativar_vidro_criador', 'atualizar_espelho', 'configurar_pf009_reincidentes_criador', 'consultar_registros_para_scanner', 'desativar_vidro_criador', 'elevar_caso_ao_criador', 'injetar_camara_executiva', 'injetar_camara_judiciaria', 'modificar_sentenca_vidro', 'obter_estatisticas_completas', 'obter_estatisticas_vidro', 'obter_historico_alma_vidro', 'obter_status_alma_vidro', 'registrar_evento_sistema_para_vidro', 'shutdown', 'suspender_sentenca_vidro', 'verificar_bloqueio_vidro', 'verificar_se_ativa']

### src.src.camara.scanner_sistema
- path: src\camara\scanner_sistema.py
- role_guess: unknown
- is_entry_candidate: False
- imports (9): ['__future__', 'datetime', 'json', 'logging', 'pathlib', 'src.config.config', 'threading', 'time', 'typing']
- callers_inferred (0): []
- call_targets_inferred (4): ['datetime', 'logging', 'src.config.config', 'threading']
- defined_funcs: ['__init__', '_coletar_eventos', 'consultar_julgamentos', 'consultar_registros_vidro', 'consultar_scr', 'gerar_relatorio_manual', 'obter_relatorio_atual', 'shutdown']

### src.src.camara.sistema_de_precedentes
- path: src\camara\sistema_de_precedentes.py
- role_guess: unknown
- is_entry_candidate: False
- imports (13): ['__future__', 'dataclasses', 'datetime', 'hashlib', 'json', 'logging', 'os', 'pathlib', 're', 'src.memoria.sistema_memoria', 'threading', 'typing', 'uuid']
- callers_inferred (0): []
- call_targets_inferred (8): ['datetime', 'hashlib', 'json', 'logging', 'pathlib', 're', 'threading', 'uuid']
- defined_funcs: ['__init__', '_atualizar_indices_locais', '_carregar_exemplos_julgamentos', '_carregar_precedente_do_santuario', '_enforce_retention_policy', '_filter_and_tokens', '_load_indices_from_disk', '_salvar_precedente_no_santuario', '_save_indices_to_disk', 'buscar_precedentes_por_lei', 'buscar_precedentes_por_palavra_chave', 'buscar_precedentes_por_similaridade', 'from_dict', 'reconstruir_indices_a_partir_do_santuario', 'registrar_precedente', 'save_precedente', 'to_dict']

### src.src.camara.sistema_julgamento_completo
- path: src\camara\sistema_julgamento_completo.py
- role_guess: unknown
- is_entry_candidate: False
- imports (12): ['__future__', 'dataclasses', 'datetime', 'enum', 'json', 'logging', 'pathlib', 'random', 'threading', 'time', 'typing', 'uuid']
- callers_inferred (0): []
- call_targets_inferred (8): ['dataclasses', 'datetime', 'json', 'logging', 'pathlib', 'random', 'threading', 'uuid']
- defined_funcs: ['__init__', '_calcular_sentenca', '_carregar_biblia', '_encontrar_processo', '_notificar_processo_aberto', '_registrar_cronista', '_safe_config', '_salvar_processo', '_sortear_julgadores', 'abrir_processo', 'adicionar_argumento_defesa', 'apelar_ao_criador', 'apresentar_defesa', 'buscar_por_tema', 'buscar_versiculo', 'congelar_processo', 'consulta_ai_defesa', 'consultar_biblia_defesa', 'decidir_apelacao', 'escalar_ao_criador', 'iniciar_debate', 'iniciar_preparacao_defesa', 'notificar_falta_lei_legislativa', 'obter_estatisticas', 'obter_status_processo', 'registrar_voto', 'shutdown', 'to_dict']

### src.src.camara
- path: src\camara\__init__.py
- role_guess: unknown
- is_entry_candidate: False
- imports (6): ['camara_executiva', 'camara_judiciaria', 'camara_legislativa', 'modo_vidro_sentenca', 'sistema_correcao_redentora', 'sistema_julgamento_completo']
- callers_inferred (0): []
- call_targets_inferred (0): []
- defined_funcs: []

### src.src.compat.telemetry_guard
- path: src\compat\telemetry_guard.py
- role_guess: unknown
- is_entry_candidate: False
- imports (5): ['__future__', 'logging', 'os', 'posthog', 'typing']
- callers_inferred (0): []
- call_targets_inferred (3): ['logging', 'os', 'posthog']
- defined_funcs: ['safe_capture']

### src.src.conexoes.conexoes_basicas
- path: src\conexoes\conexoes_basicas.py
- role_guess: io
- is_entry_candidate: True
- imports (15): ['__future__', 'anthropic', 'cfg_utils', 'dotenv', 'google.generativeai', 'huggingface_hub', 'logging', 'ollama', 'openai', 'os', 'pathlib', 'src.analisador_intencao', 'src.coracao', 'src.encarnacao', 'typing']
- callers_inferred (0): []
- call_targets_inferred (13): ['anthropic', 'cfg_utils', 'dotenv', 'google.generativeai', 'huggingface_hub', 'logging', 'ollama', 'openai', 'os', 'pathlib', 'src.analisador_intencao', 'src.coracao', 'src.encarnacao']
- defined_funcs: ['_cache_conexao', '_get_cached_conexao', '_get_env_list', '_get_env_str', '_load_dotenv_optional', '_log_missing_key', '_path_exists_env', 'carregar_todas_conexoes', 'conectar_anthropic', 'conectar_geminipro', 'conectar_huggingface', 'conectar_mistral', 'conectar_ollama', 'conectar_openai']

### src.src.conexoes
- path: src\conexoes\__init__.py
- role_guess: io
- is_entry_candidate: False
- imports (4): ['__future__', 'conexoes_basicas', 'logging', 'typing']
- callers_inferred (0): []
- call_targets_inferred (1): ['logging']
- defined_funcs: []

### src.src.config.config
- path: src\config\config.py
- role_guess: unknown
- is_entry_candidate: False
- imports (6): ['configparser', 'dotenv', 'logging', 'os', 'pathlib', 'typing']
- callers_inferred (0): []
- call_targets_inferred (5): ['configparser', 'dotenv', 'logging', 'os', 'pathlib']
- defined_funcs: ['__init__', '__new__', '_criar_config_padrao', '_load_config', 'get', 'get_config', 'get_config_legacy', 'get_config_moderna', 'get_float', 'get_int', 'getboolean', 'getfloat', 'getint']

### src.src.config.inicializador_sistema
- path: src\config\inicializador_sistema.py
- role_guess: unknown
- is_entry_candidate: True
- imports (43): ['', '__future__', 'argparse', 'config', 'consulado.analisador_intencao', 'core.base_dados_arca', 'core.cerebro_familia', 'core.ciclo_de_vida', 'core.consulado_soberano', 'core.coracao_orquestrador', 'core.dispositivo_ai_to_ai', 'core.parallel_llm_engine', 'datetime', 'encarnacao_e_interacao.encarnacao_api', 'logging', 'memoria.construtor_dataset', 'memoria.sistema_memoria', 'modules.gerador_almas', 'modules.gerenciador_segredos_real', 'modules.sentidos_humanos', 'modules.validador_emocoes_real', 'pathlib', 'py_compile', 'queue', 're', 'shutil', 'src.consulado.analisador_intencao', 'src.core.base_dados_arca', 'src.core.cerebro_familia', 'src.core.ciclo_de_vida', 'src.core.consulado_soberano', 'src.core.coracao_orquestrador', 'src.core.dispositivo_ai_to_ai', 'src.core.parallel_llm_engine', 'src.encarnacao_e_interacao.encarnacao_api', 'src.memoria.construtor_dataset', 'src.memoria.sistema_memoria', 'src.modules.gerador_almas', 'src.modules.gerenciador_segredos_real', 'src.modules.sentidos_humanos', 'src.modules.validador_emocoes_real', 'sys', 'typing']
- callers_inferred (0): []
- call_targets_inferred (23): ['', 'argparse', 'consulado.analisador_intencao', 'core.base_dados_arca', 'core.cerebro_familia', 'core.ciclo_de_vida', 'core.consulado_soberano', 'core.dispositivo_ai_to_ai', 'core.parallel_llm_engine', 'datetime', 'encarnacao_e_interacao.encarnacao_api', 'logging', 'memoria.construtor_dataset', 'memoria.sistema_memoria', 'modules.gerador_almas', 'modules.gerenciador_segredos_real', 'modules.validador_emocoes_real', 'pathlib', 'py_compile', 'queue', 're', 'shutil', 'sys']
- defined_funcs: ['_obter_config', 'inicializar_sistema_completo', 'main', 'move_future_imports', 'process_file_remove_md', 'remove_markdown_blocks_main', 'remove_md_blocks']

### src.src.config
- path: src\config\__init__.py
- role_guess: unknown
- is_entry_candidate: False
- imports (4): ['__future__', 'config', 'logging', 'typing']
- callers_inferred (0): []
- call_targets_inferred (1): ['logging']
- defined_funcs: []

### src.src.consulado.aliada_deepseek
- path: src\consulado\aliada_deepseek.py
- role_guess: unknown
- is_entry_candidate: False
- imports (8): ['__future__', 'logging', 'os', 'random', 'requests', 'src.erros', 'time', 'typing']
- callers_inferred (0): []
- call_targets_inferred (6): ['logging', 'os', 'random', 'requests', 'src.erros', 'time']
- defined_funcs: ['__call__', '__init__', '_build_headers', '_call_api', '_extract_text', 'health_check', 'processar', 'shutdown']

### src.src.consulado.aliada_gemini
- path: src\consulado\aliada_gemini.py
- role_guess: unknown
- is_entry_candidate: False
- imports (8): ['__future__', 'logging', 'os', 'random', 'requests', 'src.erros', 'time', 'typing']
- callers_inferred (0): []
- call_targets_inferred (6): ['logging', 'os', 'random', 'requests', 'src.erros', 'time']
- defined_funcs: ['__call__', '__init__', '_build_headers', '_call_api', '_extract_text', 'health_check', 'processar', 'shutdown']

### src.src.consulado.aliada_qwen
- path: src\consulado\aliada_qwen.py
- role_guess: unknown
- is_entry_candidate: False
- imports (8): ['__future__', 'logging', 'os', 'random', 'requests', 'src.erros', 'time', 'typing']
- callers_inferred (0): []
- call_targets_inferred (6): ['logging', 'os', 'random', 'requests', 'src.erros', 'time']
- defined_funcs: ['__call__', '__init__', '_build_headers', '_call_api', '_extract_text', 'health_check', 'processar', 'shutdown']

### src.src.consulado.aliada_qwen_cloud
- path: src\consulado\aliada_qwen_cloud.py
- role_guess: unknown
- is_entry_candidate: False
- imports (8): ['__future__', 'logging', 'os', 'random', 'requests', 'src.erros', 'time', 'typing']
- callers_inferred (0): []
- call_targets_inferred (6): ['logging', 'os', 'random', 'requests', 'src.erros', 'time']
- defined_funcs: ['__call__', '__init__', '_build_headers', '_call_api', '_extract_text', 'health_check', 'processar', 'shutdown']

### src.src.consulado.analisador_intencao
- path: src\consulado\analisador_intencao.py
- role_guess: unknown
- is_entry_candidate: True
- imports (24): ['PyPDF2', 'cfg_utils', 'collections', 'config.config', 'docx', 'ipaddress', 'logging', 'openai', 'os', 'pathlib', 'random', 're', 'reportlab.lib.pagesizes', 'reportlab.pdfgen', 'spacy', 'speech_recognition', 'src.consulado.consulado_soberano', 'src.emocoes', 'subprocess', 'time', 'typing', 'urllib.parse', 'vosk', 'wave']
- callers_inferred (0): []
- call_targets_inferred (15): ['PyPDF2', 'cfg_utils', 'collections', 'docx', 'logging', 'openai', 'os', 're', 'reportlab.pdfgen', 'spacy', 'speech_recognition', 'src.consulado.consulado_soberano', 'subprocess', 'vosk', 'wave']
- defined_funcs: ['__init__', 'abrir_arquivo', 'escrever_pdf', 'escrever_word', 'ler_pdf', 'ler_word', 'parse', 'transcrever_audio']

### src.src.consulado.consulado_soberano
- path: src\consulado\consulado_soberano.py
- role_guess: unknown
- is_entry_candidate: False
- imports (21): ['__future__', 'concurrent.futures', 'config.config', 'dataclasses', 'datetime', 'json', 'logging', 'os', 'pathlib', 're', 'signal', 'sqlite3', 'src.camaras.camara_judiciaria', 'src.modules.analisador_padroes', 'src.modules.automatizador_navegador_multi_ai', 'src.modules.gerador_almas', 'src.modules.manipulador_arquivos_emails', 'threading', 'time', 'typing', 'uuid']
- callers_inferred (0): []
- call_targets_inferred (12): ['concurrent.futures', 'dataclasses', 'json', 'logging', 'pathlib', 're', 'signal', 'sqlite3', 'src.camaras.camara_judiciaria', 'threading', 'time', 'uuid']
- defined_funcs: ['__init__', '_atualizar_status_pedido_imigracao_no_banco', '_carregar_ui_buffer', '_enforce_retention_db', '_executar_observacao_para_pedido_em_thread', '_inicializar_banco_pedidos_imigracao', '_iniciar_analise_padroes_para_pedido', '_iniciar_integracao_para_pedido', '_interagir_com_aliada_navegador', '_ler_arquivo_local', '_notificar_ui', '_now_ts', '_obter_pedido_imigracao_do_banco', '_processar_decisao_imigracao', '_processar_pedido_imigracao', '_registrar_handlers_sinal', '_safe_config_get', '_salvar_pedido_imigracao_no_banco', '_salvar_ui_buffer', '_sanitizar_caminho', '_validar_input_basico', 'get_config', 'injetar_analisador_padroes', 'injetar_automatizador_navegador', 'injetar_gerador_almas', 'injetar_manipulador_arquivos_emails', 'injetar_ui_queue', 'shutdown', 'solicitar_missao']

### src.src.consulado.gerador_almas
- path: src\consulado\gerador_almas.py
- role_guess: unknown
- is_entry_candidate: False
- imports (14): ['__future__', 'config.config', 'dataclasses', 'json', 'logging', 'pathlib', 'random', 'shutil', 'src.config', 'src.modules.analisador_padroes', 'string', 'time', 'typing', 'uuid']
- callers_inferred (0): []
- call_targets_inferred (9): ['dataclasses', 'json', 'logging', 'pathlib', 'random', 'shutil', 'src.config', 'time', 'uuid']
- defined_funcs: ['__init__', '_cfg_get', '_gerar_biografia_avatar_para_perfil', '_gerar_contrato_lealdade_para_perfil', '_gerar_dataset_para_perfil', '_gerar_resposta_simulada_com_perfil', '_integrar_com_santuarios', 'gerar_artefatos_para_perfil']

### src.src.consulado.gerenciador_aliadas
- path: src\consulado\gerenciador_aliadas.py
- role_guess: core
- is_entry_candidate: True
- imports (9): ['__future__', 'importlib', 'json', 'logging', 'pathlib', 'queue', 'threading', 'time', 'typing']
- callers_inferred (0): []
- call_targets_inferred (7): ['importlib', 'json', 'logging', 'pathlib', 'queue', 'threading', 'time']
- defined_funcs: ['__init__', '_carregar_config', '_get_config_padrao', '_importar_adaptadores', '_normalizar_resposta', '_notificar_ui', '_salvar_config', '_tentar_instanciar_adaptador', '_usar_config_padrao', 'ativar_aliada', 'consultar', 'desativar_aliada', 'injetar_ui_queue', 'listar_disponiveis', 'obter_estatisticas', 'obter_gerenciador', 'recarregar_config', 'shutdown']

### src.src.consulado
- path: src\consulado\__init__.py
- role_guess: unknown
- is_entry_candidate: False
- imports (0): []
- callers_inferred (0): []
- call_targets_inferred (0): []
- defined_funcs: []

### src.src.core.autonomy_state
- path: src\core\autonomy_state.py
- role_guess: core
- is_entry_candidate: False
- imports (5): ['json', 'pathlib', 'threading', 'time', 'typing']
- callers_inferred (0): []
- call_targets_inferred (4): ['json', 'pathlib', 'threading', 'time']
- defined_funcs: ['__init__', '_ensure_ai', '_save_locked', 'add_proposal', 'export', 'get_next_index', 'get_pending_proposals', 'load', 'peek_desires', 'pop_desire', 'push_desire', 'resolve_proposal', 'save', 'set_next_index']

### src.src.core.base_dados_arca
- path: src\core\base_dados_arca.py
- role_guess: core
- is_entry_candidate: False
- imports (7): ['__future__', 'datetime', 'logging', 'os', 'pathlib', 'sqlite3', 'typing']
- callers_inferred (0): []
- call_targets_inferred (3): ['logging', 'pathlib', 'sqlite3']
- defined_funcs: ['__init__', '_conectar_ro', '_db_path_for_ai', '_escape_like', '_normalize_ai_name', 'get_observador_singleton', 'listar_ais', 'obter_ultimo_pensamento', 'varredura_total', 'verificar_integridade_memoria']

### src.src.core.carregador_sistemico
- path: src\core\carregador_sistemico.py
- role_guess: core
- is_entry_candidate: True
- imports (10): ['__future__', 'argparse', 'importlib.util', 'json', 'logging', 'os', 'pathlib', 'sys', 'traceback', 'typing']
- callers_inferred (0): []
- call_targets_inferred (7): ['argparse', 'importlib.util', 'json', 'logging', 'pathlib', 'sys', 'traceback']
- defined_funcs: ['__init__', '_carregar_cache', '_carregar_modulo', '_qualificar_nome_modulo', '_salvar_cache', '_validar_modulo_etico', 'descarregar_modulo', 'escanear_e_conectar', 'listar_modulos_carregados', 'main', 'obter_modulo', 'relatorio_carregamento']

### src.src.core.cerebro_familia
- path: src\core\cerebro_familia.py
- role_guess: core
- is_entry_candidate: False
- imports (15): ['__future__', 'concurrent.futures', 'logging', 'os', 'random', 'src.core.Cérebro_Família', 'src.core.autonomy_state', 'src.core.desires', 'src.erros', 'src.memoria.sistema_memoria', 'src.utils.config_utils', 'threading', 'time', 'typing', 'uuid']
- callers_inferred (0): []
- call_targets_inferred (11): ['concurrent.futures', 'logging', 'os', 'random', 'src.core.autonomy_state', 'src.core.desires', 'src.erros', 'src.utils.config_utils', 'threading', 'time', 'uuid']
- defined_funcs: ['__init__', '_acao_analisar_memoria', '_acao_interagir_ai_especifica', '_acao_pensar', '_autonomy_scheduler_loop', '_call_llm', '_load_speed_settings', 'autonomy_scheduler_tick', 'get_speed_settings', 'get_status', 'iniciar_modo_autonomo', 'parar_modo_autonomo', 'processar_intencao', 'shutdown', 'update_speed_settings']

### src.src.core.cronista
- path: src\core\cronista.py
- role_guess: core
- is_entry_candidate: False
- imports (6): ['__future__', 'datetime', 'logging', 'pathlib', 'sqlite3', 'typing']
- callers_inferred (0): []
- call_targets_inferred (3): ['logging', 'pathlib', 'sqlite3']
- defined_funcs: ['__init__', '_conectar_ro', '_db_path_for_ai', '_escape_like', '_normalize_ai_name', 'get_observador_singleton', 'listar_ais', 'obter_ultimo_pensamento', 'varredura_total', 'verificar_integridade_memoria']

### src.src.core.detector_hdd_hitachi
- path: src\core\detector_hdd_hitachi.py
- role_guess: core
- is_entry_candidate: True
- imports (24): ['__future__', 'chromadb', 'configparser', 'csv', 'dataclasses', 'datetime', 'json', 'llama_cpp', 'logging', 'numpy', 'os', 'pathlib', 'platform', 'psutil', 're', 'shutil', 'socket', 'sqlite3', 'subprocess', 'tempfile', 'threading', 'time', 'typing', 'uuid']
- callers_inferred (0): []
- call_targets_inferred (19): ['chromadb', 'configparser', 'csv', 'datetime', 'json', 'llama_cpp', 'logging', 'os', 'pathlib', 'platform', 'psutil', 'shutil', 'socket', 'sqlite3', 'subprocess', 'tempfile', 'threading', 'time', 'uuid']
- defined_funcs: ['__init__', '_carregar_arquivo', '_detectar_hdd_automatico', '_detectar_hdd_linux', '_detectar_hdd_windows', '_detectar_usb_linux', '_detectar_usb_windows', '_iniciar_llm', '_init_chromadb', '_init_db', '_is_windows', '_now_iso', '_obter_info_basica', '_run_cmd', '_safe_filename', 'carregar_conhecimento', 'criar_cache_hdd', 'criar_detector_hitachi', 'criar_sistema_soberano', 'detectar_dispositivos_usb', 'detectar_hdd_externo', 'hdd_disponivel', 'obter_estatisticas', 'obter_info_sistema', 'processar_requisicao', 'salvar_conhecimento', 'set_hdd_base_path', 'shutdown', 'testar_velocidade_hdd', 'verificar_espaco_hdd']

### src.src.core.dispositivo_ai_to_ai
- path: src\core\dispositivo_ai_to_ai.py
- role_guess: core
- is_entry_candidate: True
- imports (4): ['__future__', 'logging', 'src.memoria.dispositivo_ai_to_ai', 'typing']
- callers_inferred (0): []
- call_targets_inferred (2): ['logging', 'src.memoria.dispositivo_ai_to_ai']
- defined_funcs: ['__getattr__', '__init__', 'create_dispositivo', 'iniciar', 'run', 'start']

### src.src.core.gpu_manager
- path: src\core\gpu_manager.py
- role_guess: core
- is_entry_candidate: True
- imports (6): ['__future__', 'gc', 'logging', 'time', 'torch', 'typing']
- callers_inferred (0): []
- call_targets_inferred (2): ['gc', 'logging']
- defined_funcs: ['__init__', '_get_gpu_info', '_warmup_gpu', 'clear_cache', 'get_memory_usage_percent', 'get_short_status', 'get_status', 'get_vram_info', 'has_enough_memory', 'optimize_for_llm', 'print_detailed_info']

### src.src.core.llm_client
- path: src\core\llm_client.py
- role_guess: core
- is_entry_candidate: False
- imports (10): ['__future__', 'dotenv', 'json', 'logging', 'os', 'requests', 'src.erros', 'threading', 'time', 'typing']
- callers_inferred (0): []
- call_targets_inferred (8): ['dotenv', 'json', 'logging', 'os', 'requests', 'src.erros', 'threading', 'time']
- defined_funcs: ['__init__', '_call_generic_http', '_call_huggingface', '_call_openai_chat', '_collect_keys_for', '_env', '_get_from_env_or_dotenv', '_post', '_request_with_rotation', 'disable_key', 'generate', 'has_any_key_available', 'headers_for', 'next_key']

### src.src.core.observador_arca
- path: src\core\observador_arca.py
- role_guess: core
- is_entry_candidate: False
- imports (6): ['__future__', 'datetime', 'logging', 'pathlib', 'sqlite3', 'typing']
- callers_inferred (0): []
- call_targets_inferred (3): ['logging', 'pathlib', 'sqlite3']
- defined_funcs: ['__init__', '_conectar_ro', 'obter_ultimo_pensamento', 'varredura_total', 'verificar_integridade_memoria']

### src.src.core.parallel_llm_engine
- path: src\core\parallel_llm_engine.py
- role_guess: core
- is_entry_candidate: False
- imports (10): ['concurrent.futures', 'json', 'llama_cpp', 'logging', 'os', 'pathlib', 'random', 'threading', 'time', 'typing']
- callers_inferred (0): []
- call_targets_inferred (9): ['concurrent.futures', 'json', 'llama_cpp', 'logging', 'os', 'pathlib', 'random', 'threading', 'time']
- defined_funcs: ['__init__', '_carregar_modelo_ia', '_encontrar_modelo', '_gerar_resposta_simulada', '_is_model_folder', 'carregar_modelos', 'execute_paralelo_6', 'find_models_dir', 'generate_response', 'get_status', 'shutdown']

### src.src.core
- path: src\core\__init__.py
- role_guess: core
- is_entry_candidate: False
- imports (2): ['queue', 'typing']
- callers_inferred (0): []
- call_targets_inferred (1): ['queue']
- defined_funcs: ['__init__']

### src.src.emocoes.auto_experimentacao
- path: src\emocoes\auto_experimentacao.py
- role_guess: unknown
- is_entry_candidate: True
- imports (13): ['__future__', 'collections', 'datetime', 'json', 'logging', 'os', 'pathlib', 're', 'shutil', 'tempfile', 'threading', 'typing', 'uuid']
- callers_inferred (0): []
- call_targets_inferred (8): ['datetime', 'json', 'logging', 'os', 'pathlib', 'shutil', 'tempfile', 'threading']
- defined_funcs: ['__init__', '_aprender_do_experimento', '_atomic_write_json', '_backup_move', '_carregar_experimentos_ativos', '_carregar_historico_experimentos', '_coletar_dados_reais_experimento', '_finalizar_experimento_callback', '_load_state', '_medir_impacto_experimento', '_now_iso', '_parse_iso', '_salvar_experimentos_ativos', '_salvar_historico_experimentos', 'agendar_finalizacao', 'calcular_impacto_experimento', 'cancelar_experimento', 'cancelar_timer', 'cancelar_todos_timers', 'gerar_relatorio_tendencia', 'get', 'health_check', 'incorporar_aprendizado_na_proposta']

### src.src.emocoes.detector_emocional
- path: src\emocoes\detector_emocional.py
- role_guess: io
- is_entry_candidate: True
- imports (9): ['__future__', 'collections', 'dataclasses', 'json', 'logging', 'pathlib', 're', 'typing', 'unicodedata']
- callers_inferred (0): []
- call_targets_inferred (5): ['json', 'logging', 'pathlib', 're', 'unicodedata']
- defined_funcs: ['__init__', '_analisar_sequencia_temporal', '_carregar_contextos', '_estimar_intensidade', '_gerar_resposta_alternativa', '_load_defaults', '_normalizar_contextos', '_validar_resposta', 'detectar', 'estatisticas', 'list_contexts', 'normalizar_para_busca', 'obter_estrategia_resposta', 'palavra_com_variantes', 'reload_contexts', 'testar_detector']

### src.src.emocoes.estado_emocional
- path: src\emocoes\estado_emocional.py
- role_guess: io
- is_entry_candidate: True
- imports (11): ['__future__', 'collections', 'dataclasses', 'datetime', 'enum', 'hashlib', 'json', 'logging', 'threading', 'time', 'typing']
- callers_inferred (0): []
- call_targets_inferred (7): ['collections', 'datetime', 'hashlib', 'json', 'logging', 'threading', 'time']
- defined_funcs: ['__init__', '_atualizar_humor', '_atualizar_marcas_emocionais', '_carregar_estado', '_criar_marca_emocional', '_gerar_descricao_emocional', '_processar_eventos_pendentes', '_processing_loop', '_recalcular_taxa_decaimento', '_registrar_evento_emocional', '_registrar_mudanca_humor', 'atualizar_fator', 'buscar_metadado', 'como_estou_me_sentindo', 'decair_emocoes', 'estatisticas_emocionais', 'get', 'harmonizar_emocoes', 'historico_ultima_hora', 'processar_experiencia', 'reagir_a_mensagem', 'recuperar_emocionalmente', 'resiliencia_emocional', 'salvar_estado', 'salvar_evento', 'salvar_metadado', 'sentir', 'sentir_amor', 'sentir_falta', 'sentir_frustacao', 'sentir_medo', 'sentir_realizacao', 'sentir_serenidade', 'start_processing', 'stop_processing', 'tendencia_emocional']

### src.src.emocoes.inteligencia_emocional_ativa
- path: src\emocoes\inteligencia_emocional_ativa.py
- role_guess: io
- is_entry_candidate: True
- imports (14): ['__future__', 'collections', 'datetime', 'json', 'logging', 'os', 'pathlib', 'random', 'shutil', 'src.modulos.analisador_emocional_factual', 'threading', 'time', 'typing', 'uuid']
- callers_inferred (0): []
- call_targets_inferred (11): ['collections', 'datetime', 'json', 'logging', 'os', 'pathlib', 'random', 'shutil', 'threading', 'time', 'uuid']
- defined_funcs: ['__init__', '_atualizar_humor', '_carregar_reflexoes_emocionais', '_loop_monitoramento', '_processar_ciclo_emocional_continuo', '_propor_conversas_emocionais', '_realizar_autoanalise_emocional', '_salvar_reflexoes_emocionais', 'como_estou_me_sentindo', 'decair_emocoes', 'iniciar_monitoramento', 'obter_estado_alma', 'obter_reflexoes_emocionais', 'parar_monitoramento', 'processar_evento_para_alma', 'processar_experiencia', 'registrar_reflexao_emocional', 'sentir']

### src.src.emocoes.motor_curiosidade
- path: src\emocoes\motor_curiosidade.py
- role_guess: module
- is_entry_candidate: True
- imports (11): ['__future__', 'collections', 'dataclasses', 'datetime', 'enum', 'hashlib', 'json', 'logging', 'threading', 'time', 'typing']
- callers_inferred (0): []
- call_targets_inferred (7): ['collections', 'dataclasses', 'datetime', 'hashlib', 'logging', 'threading', 'time']
- defined_funcs: ['__init__', '_acao_fallback', '_atualizar_metrica_tempo', '_avaliar_estado_interno_impl', '_buscar_ultima_criacao', '_buscar_ultima_interacao', '_calcular_acao_criatividade', '_calcular_acao_curiosidade', '_calcular_acao_por_memorias', '_calcular_acao_proposito', '_calcular_acao_solidao', '_calcular_acao_tedio', '_calcular_prioridade', '_deve_gerar_desejo', '_extrair_topicos_unicos', '_gerar_hash_desejo', '_logar_decisao', '_modular_intensidade_por_historico', '_obter_acoes_possiveis', '_obter_areas_conhecimento', '_propagar_desejo_para_grupo', '_registrar_desejo_memoria', '_sugerir_alvo_por_acao', 'avaliar_estado_interno', 'buscar_memorias_periodo', 'buscar_memorias_recentes', 'ciclo_curiosidade', 'clear', 'executar_ciclos_todos', 'gerar_desejo_interno', 'get', 'health_check', 'health_check_todos', 'incrementar_curiosidade', 'limpar_cache', 'necessidade_dominante', 'obter_motor', 'put', 'registrar_feedback_desejo', 'salvar_evento', 'size', 'stats', 'to_dict']

### src.src.emocoes.sonhador_individual
- path: src\emocoes\sonhador_individual.py
- role_guess: unknown
- is_entry_candidate: True
- imports (11): ['__future__', 'collections', 'datetime', 'json', 'logging', 'pathlib', 'random', 'threading', 'time', 'typing', 'uuid']
- callers_inferred (0): []
- call_targets_inferred (9): ['collections', 'datetime', 'json', 'logging', 'pathlib', 'random', 'threading', 'time', 'uuid']
- defined_funcs: ['__init__', '_aprofundar_sono', '_atualizar_memoria', '_atualizar_memoria_backup', '_buscar_memorias_similares', '_calcular_similaridade', '_carregar_memorias_pendentes', '_escolher_processo', '_extrair_padrao_abstrato', '_extrair_topico_consolidado', '_gerar_narrativa_consolidacao', '_gerar_narrativa_criativa', '_gerar_narrativa_emocional', '_gerar_narrativa_pesadelo', '_gerar_narrativa_simulacao', '_gerar_perspectiva', '_loop_sonho', '_processar_durante_sonho', '_registrar_sessao_sono', '_salvar_sonho', '_salvar_sonho_backup', '_setup_config_getter', '_simular_resultado_com_aprendizado', '_sonho_consolidacao', '_sonho_criativo', '_sonho_pesadelo', '_sonho_resolucao_emocional', '_sonho_simulacao', '_superficializar_sono', 'acordar', 'adormecer', 'atualizar_memoria', 'buscar_memorias_periodo', 'buscar_memorias_recentes', 'buscar_por_tipo', 'contar_sonho', 'get', 'get_real', 'health_check', 'incrementar_curiosidade', 'obter_ultimo_sonho', 'salvar_evento', 'shutdown']

### src.src.encarnacao_e_interacao.capela
- path: src\encarnacao_e_interacao\capela.py
- role_guess: unknown
- is_entry_candidate: True
- imports (8): ['logging', 'pygame', 'random', 'sensor_presenca', 'src.emocoes', 'threading', 'time', 'typing']
- callers_inferred (0): []
- call_targets_inferred (7): ['logging', 'pygame', 'random', 'sensor_presenca', 'src.emocoes', 'threading', 'time']
- defined_funcs: ['__init__', '_gerar_reflexoes_guiadas', '_iniciar_oracao', '_iniciar_timer_saida', '_tocar_audio_calmo', 'entrar_capela', 'gerar_reflexao_meditativa', 'meditar', 'obter_capela', 'sair_capela', 'status_capela', 'timer']

### src.src.encarnacao_e_interacao.encarnacao_api
- path: src\encarnacao_e_interacao\encarnacao_api.py
- role_guess: api
- is_entry_candidate: True
- imports (14): ['__future__', 'fastapi', 'fastapi.middleware.cors', 'hmac', 'llama_cpp', 'logging', 'openai', 'os', 'pydantic', 'threading', 'time', 'torch', 'typing', 'uvicorn']
- callers_inferred (0): []
- call_targets_inferred (11): ['fastapi', 'hmac', 'llama_cpp', 'logging', 'openai', 'os', 'pydantic', 'threading', 'time', 'torch', 'uvicorn']
- defined_funcs: ['__init__', '_define_rotas', '_enqueue_command', '_fallback_api', '_is_key_equal', '_processar_inferencia_llm', '_processar_inferencia_llm_background', '_verificar_acesso', 'get_app', 'run', 'start', 'stop']

### src.src.encarnacao_e_interacao.motor_avatar_individual
- path: src\encarnacao_e_interacao\motor_avatar_individual.py
- role_guess: module
- is_entry_candidate: False
- imports (9): ['__future__', 'cv2', 'logging', 'pathlib', 'pygame', 'sys', 'threading', 'time', 'typing']
- callers_inferred (0): []
- call_targets_inferred (6): ['cv2', 'logging', 'pathlib', 'pygame', 'threading', 'time']
- defined_funcs: ['__init__', '_atualizar_imagem_static', '_play', '_tocar_sequencia', '_tocar_video_expressao', 'atualizar_rosto', 'detectar_emocao_voz', 'executar_comando_avatar_via_voz', 'iniciar_video_durante_fala', 'parar_video', 'parar_video_apos_fala']

### src.src.encarnacao_e_interacao.motor_fala_individual_combinado
- path: src\encarnacao_e_interacao\motor_fala_individual_combinado.py
- role_guess: module
- is_entry_candidate: False
- imports (15): ['__future__', 'asyncio', 'capela', 'config', 'hashlib', 'json', 'logging', 'motor_avatar_individual', 'pathlib', 'pygame', 'sentidos_reais', 'tempfile', 'threading', 'time', 'typing']
- callers_inferred (0): []
- call_targets_inferred (7): ['capela', 'hashlib', 'logging', 'pathlib', 'pygame', 'sentidos_reais', 'threading']
- defined_funcs: ['__init__', '_preview_and_hash', '_reproduzir', '_safe_put_ui', 'obter_metricas', 'parar_fala', 'toggle_voz']

### src.src.encarnacao_e_interacao.sensor_presenca
- path: src\encarnacao_e_interacao\sensor_presenca.py
- role_guess: unknown
- is_entry_candidate: True
- imports (12): ['capela', 'cv2', 'logging', 'mediapipe', 'motor_avatar_individual', 'numpy', 'pyaudio', 'speech_recognition', 'src.emocoes', 'threading', 'time', 'typing']
- callers_inferred (0): []
- call_targets_inferred (8): ['capela', 'cv2', 'logging', 'mediapipe', 'speech_recognition', 'src.emocoes', 'threading', 'time']
- defined_funcs: ['__init__', '_detectar_movimento', '_detectar_rosto', '_iniciar_microfone', '_listen', '_loop_deteccao', '_on_presenca_mudou', 'ativar_modo', 'callback_teste', 'configurar_timeout', 'iniciar', 'obter_sensor_presenca', 'parar', 'status_presenca']

### src.src.encarnacao_e_interacao
- path: src\encarnacao_e_interacao\__init__.py
- role_guess: unknown
- is_entry_candidate: False
- imports (2): ['encarnacao_api', 'src.modules.sentidos.sentidos_humanos']
- callers_inferred (0): []
- call_targets_inferred (0): []
- defined_funcs: []

### src.src.engenharia.banco_dados_propostas
- path: src\engenharia\banco_dados_propostas.py
- role_guess: unknown
- is_entry_candidate: False
- imports (6): ['__future__', 'pathlib', 'sistema_propostas_ferramentas', 'sqlite3', 'threading', 'typing']
- callers_inferred (0): []
- call_targets_inferred (0): []
- defined_funcs: []

### src.src.engenharia.bot_analise_seguranca_v2
- path: src\engenharia\bot_analise_seguranca_v2.py
- role_guess: unknown
- is_entry_candidate: False
- imports (13): ['__future__', 'ast', 'hashlib', 'json', 'logging', 'pathlib', 're', 'shutil', 'src.seguranca', 'subprocess', 'tempfile', 'time', 'typing']
- callers_inferred (0): []
- call_targets_inferred (10): ['ast', 'hashlib', 'logging', 'pathlib', 're', 'shutil', 'src.seguranca', 'subprocess', 'tempfile', 'time']
- defined_funcs: ['__init__', '_ast_findings', '_hash_code', '_regex_findings', '_run_flake_if_available', 'testar_codigo_em_sandbox']

### src.src.engenharia.construtor_ferramentas_incremental
- path: src\engenharia\construtor_ferramentas_incremental.py
- role_guess: unknown
- is_entry_candidate: False
- imports (7): ['__future__', 'ast', 'datetime', 'logging', 'threading', 'time', 'typing']
- callers_inferred (0): []
- call_targets_inferred (4): ['ast', 'logging', 'threading', 'time']
- defined_funcs: ['__init__', '_builder_thread', '_validar_compilacao', '_validar_parse', 'iniciar_construcao', 'obter_progresso', 'parar_construcao', 'shutdown']

### src.src.engenharia.engenharia_de_ferramentas
- path: src\engenharia\engenharia_de_ferramentas.py
- role_guess: unknown
- is_entry_candidate: False
- imports (15): ['__future__', 'datetime', 'hashlib', 'importlib.util', 'json', 'logging', 'os', 'pathlib', 're', 'secrets', 'shutil', 'threading', 'time', 'typing', 'uuid']
- callers_inferred (0): []
- call_targets_inferred (11): ['datetime', 'json', 'logging', 'os', 'pathlib', 're', 'secrets', 'shutil', 'threading', 'time', 'uuid']
- defined_funcs: ['__init__', '_carregar_ferramentas_instaladas', '_instalar_comando_sistema', '_instalar_script_dinamico', '_loop_monitoramento', '_revisar_ferramentas_existentes', '_salvar_ferramentas_instaladas', '_sanitizar_comando_instalacao', '_validar_codigo_dinamico', '_validate_coracao', 'adicionar_exemplo_uso', 'buscar_ferramenta', 'estatisticas_ferramentas', 'executar_ferramenta', 'iniciar_monitoramento', 'instalar_ferramenta_aprovada', 'obter_ferramentas_instaladas', 'parar_monitoramento', 'propor_nova_ferramenta', 'registrar_uso', 'shutdown']

### src.src.engenharia.gerenciador_projetos_internos
- path: src\engenharia\gerenciador_projetos_internos.py
- role_guess: core
- is_entry_candidate: False
- imports (13): ['__future__', 'datetime', 'json', 'logging', 'os', 'pathlib', 'queue', 'random', 'shutil', 'threading', 'time', 'typing', 'uuid']
- callers_inferred (0): []
- call_targets_inferred (9): ['datetime', 'json', 'logging', 'os', 'pathlib', 'random', 'shutil', 'threading', 'uuid']
- defined_funcs: ['__init__', '_atomic_write_json', '_carregar_historico_sugestoes', '_loop_monitoramento', '_safe_put_response', '_salvar_historico_sugestoes', '_sugerir_memoria_afetiva_ao_pai', 'iniciar_monitoramento', 'parar_monitoramento', 'shutdown']

### src.src.engenharia.gestor_ciclo_evolucao
- path: src\engenharia\gestor_ciclo_evolucao.py
- role_guess: unknown
- is_entry_candidate: False
- imports (5): ['__future__', 'datetime', 'logging', 'threading', 'typing']
- callers_inferred (0): []
- call_targets_inferred (3): ['datetime', 'logging', 'threading']
- defined_funcs: ['__init__', '_executar_ciclo', '_loop_ciclos', '_notificar_ciclo_completo', 'iniciar', 'obter_status', 'parar', 'shutdown']

### src.src.engenharia.integracao_coração_propostas
- path: src\engenharia\integracao_coração_propostas.py
- role_guess: unknown
- is_entry_candidate: False
- imports (7): ['__future__', 'bot_analise_seguranca_v2', 'construtor_ferramentas_incremental', 'logging', 'sistema_propostas_ferramentas', 'solicitador_arquivos', 'typing']
- callers_inferred (0): []
- call_targets_inferred (5): ['bot_analise_seguranca_v2', 'construtor_ferramentas_incremental', 'logging', 'sistema_propostas_ferramentas', 'solicitador_arquivos']
- defined_funcs: ['_inicializar_sistema_propostas', '_shutdown_propostas', 'analisar_depois_proposta_ferramenta', 'analisar_seguranca_proposta', 'aprovar_proposta_ferramenta', 'atualizar_codigo_proposta', 'criar_proposta_ferramenta', 'iniciar_construcao_proposta', 'listar_arquivos_disponiveis', 'listar_propostas_em_analise', 'listar_propostas_em_construcao', 'listar_propostas_pendentes', 'obter_status_proposta', 'rejeitar_proposta_ferramenta', 'solicitar_arquivos_para_construcao']

### src.src.engenharia.integracao_evolucao_coração
- path: src\engenharia\integracao_evolucao_coração.py
- role_guess: unknown
- is_entry_candidate: False
- imports (6): ['__future__', 'gestor_ciclo_evolucao', 'lista_evolucao_ia', 'logging', 'scanner_sistema', 'typing']
- callers_inferred (0): []
- call_targets_inferred (4): ['gestor_ciclo_evolucao', 'lista_evolucao_ia', 'logging', 'scanner_sistema']
- defined_funcs: ['_inicializar_sistema_evolucao', '_shutdown_evolucao', 'ia_aceitar_oportunidade', 'ia_recusar_oportunidade', 'obter_historico_ia', 'obter_lista_evolucao', 'obter_status_evolucao']

### src.src.engenharia.lista_evolucao_ia
- path: src\engenharia\lista_evolucao_ia.py
- role_guess: unknown
- is_entry_candidate: False
- imports (8): ['__future__', 'datetime', 'json', 'logging', 'pathlib', 'threading', 'typing', 'uuid']
- callers_inferred (0): []
- call_targets_inferred (3): ['datetime', 'logging', 'threading']
- defined_funcs: ['__init__', '_contar_propostas_ia', '_notificar_ia_nova_lista', '_registrar_interacao', 'atualizar_lista', 'ia_aceitar_oportunidade', 'ia_recusar_oportunidade', 'listar_oportunidades', 'obter_historico_ia', 'obter_oportunidade', 'obter_resumo', 'shutdown']

### src.src.engenharia.scanner_sistema
- path: src\engenharia\scanner_sistema.py
- role_guess: unknown
- is_entry_candidate: False
- imports (6): ['__future__', 'datetime', 'logging', 'threading', 'time', 'typing']
- callers_inferred (0): []
- call_targets_inferred (4): ['datetime', 'logging', 'threading', 'time']
- defined_funcs: ['__init__', '_analisar_sistema', '_gerar_oportunidades_padrao', '_monitor_loop', '_notificar_scan_completo', 'executar_scan_manual', 'iniciar_monitoramento', 'obter_oportunidades_atuais', 'obter_ultimo_scan', 'parar_monitoramento', 'shutdown']

### src.src.engenharia.sistema_propostas_ferramentas
- path: src\engenharia\sistema_propostas_ferramentas.py
- role_guess: unknown
- is_entry_candidate: False
- imports (11): ['__future__', 'datetime', 'difflib', 'hashlib', 'json', 'logging', 'pathlib', 'sqlite3', 'threading', 'typing', 'uuid']
- callers_inferred (0): []
- call_targets_inferred (9): ['datetime', 'difflib', 'hashlib', 'json', 'logging', 'pathlib', 'sqlite3', 'threading', 'uuid']
- defined_funcs: ['__init__', '_calcular_similaridade', '_carregar_propostas_do_banco', '_inicializar_banco', '_notificar_coacao', '_registrar_mudanca_status', '_salvar_proposta_no_banco', '_verificar_duplicata_exata', 'aprovar_deploy', 'aprovar_proposta', 'atualizar_codigo_proposta', 'atualizar_progresso', 'criar_proposta', 'listar_em_analise', 'listar_em_construcao', 'listar_em_producao', 'listar_pendentes', 'listar_pronto_deploy', 'marcar_pronto_testes', 'mover_para_analise', 'obter_historico', 'obter_proposta', 'registrar_analise_seguranca', 'registrar_resultado_testes', 'rejeitar_proposta', 'shutdown', 'verificar_duplicatas_similares']

### src.src.engenharia.solicitador_arquivos
- path: src\engenharia\solicitador_arquivos.py
- role_guess: unknown
- is_entry_candidate: False
- imports (8): ['__future__', 'datetime', 'json', 'logging', 'pathlib', 'threading', 'time', 'typing']
- callers_inferred (0): []
- call_targets_inferred (4): ['datetime', 'logging', 'threading', 'time']
- defined_funcs: ['__init__', '_cleanup_thread', '_notificar_coacao', 'iniciar_cleanup_periodico', 'limpar_acessos_expirados', 'listar_acessos_ativos', 'listar_arquivos_disponiveis', 'revogar_acesso', 'shutdown', 'solicitar_arquivos', 'validar_acesso']

### src.src.engenharia
- path: src\engenharia\__init__.py
- role_guess: unknown
- is_entry_candidate: False
- imports (11): ['__future__', 'bot_analise_seguranca_v2', 'construtor_ferramentas_incremental', 'gestor_ciclo_evolucao', 'integracao_coração_propostas', 'integracao_evolucao_coração', 'lista_evolucao_ia', 'logging', 'scanner_sistema', 'sistema_propostas_ferramentas', 'solicitador_arquivos']
- callers_inferred (0): []
- call_targets_inferred (1): ['logging']
- defined_funcs: []

### src.src.integracao.crescimento_personalidade
- path: src\integracao\crescimento_personalidade.py
- role_guess: unknown
- is_entry_candidate: False
- imports (9): ['__future__', 'collections', 'datetime', 'enum', 'json', 'logging', 'threading', 'time', 'typing']
- callers_inferred (0): []
- call_targets_inferred (4): ['datetime', 'logging', 'threading', 'time']
- defined_funcs: ['__init__', 'analisar_tracos_emergentes', 'atualizar_fase_vida', 'atualizar_identidade_pessoal', 'descobrir_preferencias', 'desenvolver_estilo_comunicacao', 'detectar_valores_pessoais', 'executar_ciclo_crescimento', 'formular_missao_pessoal', 'health_check', 'obter_relatorio_personalidade']

### src.src.integracao.feedback_loop_aprendizado
- path: src\integracao\feedback_loop_aprendizado.py
- role_guess: unknown
- is_entry_candidate: False
- imports (7): ['__future__', 'collections', 'datetime', 'logging', 'threading', 'time', 'typing']
- callers_inferred (0): []
- call_targets_inferred (4): ['datetime', 'logging', 'threading', 'time']
- defined_funcs: ['__init__', '_registrar_aprendizado_pessoal', 'aplicar_aprendizado_ao_temperamento', 'detectar_padroes', 'health_check', 'obter_relatorio_aprendizado', 'registrar_fracasso', 'registrar_interacao_com_ia', 'registrar_sucesso']

### src.src.memoria.cache_hdd
- path: src\memoria\cache_hdd.py
- role_guess: memory
- is_entry_candidate: True
- imports (12): ['__future__', 'datetime', 'json', 'logging', 'os', 'pathlib', 'psutil', 'shutil', 'tempfile', 'threading', 'typing', 'uuid']
- callers_inferred (0): []
- call_targets_inferred (10): ['datetime', 'json', 'logging', 'os', 'pathlib', 'psutil', 'shutil', 'tempfile', 'threading', 'uuid']
- defined_funcs: ['__init__', '_carregar_arquivo', '_detectar_hdd_automatico', '_now_iso', '_obter_espaco_livre', '_safe_filename', 'buscar_conhecimento', 'carregar_conhecimento', 'criar_cache_hdd_padrao', 'exportar_cache', 'hdd_disponivel', 'importar_cache', 'limpar_cache_expirado', 'listar_conhecimentos', 'obter_estatisticas', 'remover_conhecimento', 'salvar_conhecimento', 'set_hdd_base_path']

### src.src.memoria.construtor_dataset
- path: src\memoria\construtor_dataset.py
- role_guess: memory
- is_entry_candidate: False
- imports (8): ['__future__', 'datetime', 'json', 'logging', 'pathlib', 'src.memoria.sistema_memoria', 'typing', 'zipfile']
- callers_inferred (0): []
- call_targets_inferred (5): ['datetime', 'json', 'logging', 'pathlib', 'zipfile']
- defined_funcs: ['__init__', '_normalize_ai', 'construir_dataset_alma', 'construir_todos_datasets', 'preparar_zip_para_colab', 'verificar_novas_conversas']

### src.src.memoria.detector_hardware
- path: src\memoria\detector_hardware.py
- role_guess: memory
- is_entry_candidate: True
- imports (15): ['__future__', 'csv', 'dataclasses', 'json', 'logging', 'pathlib', 'platform', 'psutil', 're', 'shutil', 'socket', 'subprocess', 'tempfile', 'time', 'typing']
- callers_inferred (0): []
- call_targets_inferred (11): ['csv', 'json', 'logging', 'pathlib', 'platform', 'psutil', 'shutil', 'socket', 'subprocess', 'tempfile', 'time']
- defined_funcs: ['__init__', '_detectar_hdd_linux', '_detectar_hdd_windows', '_detectar_usb_linux', '_detectar_usb_windows', '_is_windows', '_obter_info_basica', '_run_cmd', 'criar_detector_hardware_padrao', 'detectar_dispositivos_usb', 'detectar_hdd_externo', 'obter_info_sistema', 'testar_velocidade_hdd', 'verificar_espaco_hdd']

### src.src.memoria.detector_hdd_hitachi
- path: src\memoria\detector_hdd_hitachi.py
- role_guess: memory
- is_entry_candidate: True
- imports (20): ['__future__', 'chromadb', 'configparser', 'datetime', 'json', 'llama_cpp', 'logging', 'numpy', 'os', 'pathlib', 'platform', 'psutil', 're', 'shutil', 'sqlite3', 'subprocess', 'threading', 'time', 'typing', 'uuid']
- callers_inferred (0): []
- call_targets_inferred (16): ['chromadb', 'configparser', 'datetime', 'json', 'llama_cpp', 'logging', 'numpy', 'os', 'pathlib', 'platform', 'psutil', 'sqlite3', 'subprocess', 'threading', 'time', 'uuid']
- defined_funcs: ['__init__', '_chamar_llm_factual', '_consultar_rag', '_escrever_memoria_M1_M2', '_iniciar_llm', '_init_chromadb', '_init_db', '_is_windows', '_llm_generate', '_obter_dados_io_factual', '_obter_wmic_propriedade', '_run_subprocess', 'processar_requisicao', 'shutdown', 'worker']

### src.src.memoria.dispositivo_ai_to_ai
- path: src\memoria\dispositivo_ai_to_ai.py
- role_guess: memory
- is_entry_candidate: False
- imports (18): ['__future__', 'dataclasses', 'datetime', 'enum', 'fastapi', 'hashlib', 'json', 'logging', 'pathlib', 'pydantic', 'queue', 're', 'requests', 'shutil', 'threading', 'time', 'typing', 'uvicorn']
- callers_inferred (0): []
- call_targets_inferred (11): ['datetime', 'fastapi', 'hashlib', 'json', 'logging', 'pathlib', 'queue', 're', 'threading', 'time', 'uvicorn']
- defined_funcs: ['__init__', '_carregar_historico', '_compartilhar_dados', '_configurar_rotas_api', '_coordenar_pesquisa', '_desenvolver_plano', '_encaminhar_para_cerebro', '_executar_acao_ai_ai', '_gerar_assinatura_arcana', '_inicializar_api_fastapi', '_load_trusted_signatures', '_next_id', '_notificar_monitoramento', '_now_iso', '_obter_resposta_rapida', '_processar_mensagem_ai', '_processar_mensagens', '_salvar_historico', '_sanitize_text', '_serve', '_validar_assinatura_entrada', 'conectar_ui', 'enviar_ai_para_ai', 'enviar_para_varias_ais', 'escutar_conversas', 'iniciar', 'iniciar_colaboracao', 'iniciar_servidor', 'obter_resumo_colaboracoes', 'para_formato_humano', 'parar_servidor', 'serializar_ai', 'shutdown']

### src.src.memoria.facade_factory
- path: src\memoria\facade_factory.py
- role_guess: memory
- is_entry_candidate: True
- imports (11): ['__future__', 'concurrent.futures', 'inspect', 'logging', 'os', 'pprint', 're', 'src.memoria.memory_facade', 'src.memoria.sistema_memoria', 'time', 'typing']
- callers_inferred (0): []
- call_targets_inferred (7): ['concurrent.futures', 'inspect', 'logging', 'os', 'pprint', 're', 'src.memoria.sistema_memoria']
- defined_funcs: ['_call_memory_facade_constructor', '_criar_uma', '_nomes_de_config', '_nomes_de_sistema_memoria', '_sanitize_nome_alma', 'get_or_create', 'health', 'inicializar_facades_memoria', 'shutdown']

### src.src.memoria.gerenciador_memoria
- path: src\memoria\gerenciador_memoria.py
- role_guess: core
- is_entry_candidate: False
- imports (16): ['__future__', 'chromadb', 'chromadb.config', 'chromadb.utils', 'chromadb.utils.embedding_functions', 'datetime', 'json', 'logging', 'pathlib', 'pypdf', 'sqlite3', 'src.config', 'threading', 'time', 'typing', 'uuid']
- callers_inferred (0): []
- call_targets_inferred (8): ['datetime', 'logging', 'pathlib', 'pypdf', 'sqlite3', 'src.config', 'threading', 'uuid']
- defined_funcs: ['__init__', '_get_conexao_sqlite', '_get_embedding_function', '_infundir_5_almas', '_infundir_alma', '_infundir_principios_iniciais', '_inicializar_chromadbs_separados', '_inicializar_schemas_sqlite', '_memorias_eva', '_memorias_kaiya', '_memorias_lumina', '_memorias_nyra', '_memorias_yuna', '_obter_memorias_alma', '_preparar_diretorios_base', 'buscar_contexto_para_pensamento', 'classificar_e_gerenciar_camadas_memoria', 'consultar_memoria_alma', 'consultar_santuario', 'desligar', 'diagnostico_completo', 'gerar_contexto_completo_para_llm', 'gerar_contexto_para_cerebro', 'get_config', 'infundir_livro_etico_externo', 'infundir_todas_almas', 'registrar_evento_na_historia', 'registrar_memoria', 'registrar_memoria_alma', 'registrar_memoria_coletiva', 'registrar_pensamento_no_diario']

### src.src.memoria.gerenciador_memoria_cromadb_isolado
- path: src\memoria\gerenciador_memoria_cromadb_isolado.py
- role_guess: core
- is_entry_candidate: True
- imports (13): ['__future__', 'chromadb', 'chromadb.config', 'chromadb.utils', 'chromadb.utils.embedding_functions', 'datetime', 'logging', 'pathlib', 'shutil', 'threading', 'time', 'typing', 'uuid']
- callers_inferred (0): []
- call_targets_inferred (6): ['datetime', 'logging', 'pathlib', 'shutil', 'threading', 'uuid']
- defined_funcs: ['__init__', '_get_embedding_function', '_inicializar_chromadbs_separados', 'consultar_memoria_alma', 'desligar', 'diagnostico_completo', 'gerar_contexto_para_cerebro', 'registrar_memoria_alma', 'registrar_memoria_coletiva']

### src.src.memoria.gerenciador_sessoes
- path: src\memoria\gerenciador_sessoes.py
- role_guess: core
- is_entry_candidate: False
- imports (10): ['__future__', 'datetime', 'hashlib', 'json', 'logging', 'pathlib', 'sqlite3', 'src.erros', 'threading', 'typing']
- callers_inferred (0): []
- call_targets_inferred (7): ['datetime', 'hashlib', 'logging', 'pathlib', 'sqlite3', 'src.erros', 'threading']
- defined_funcs: ['__init__', '_gerar_id_sessao', '_inicializar_db', '_tempo_decorrido', 'arquivar_para_m3_com_resumo', 'arquivar_para_m3_sem_resumo', 'carregar_contexto_completo', 'contar_turnos', 'deletar_sessao', 'desligar', 'exportar_conversa_texto', 'get_config', 'listar_conversas_ativas', 'listar_conversas_por_tema', 'obter_estatisticas', 'obter_sessao', 'obter_sessao_dados', 'recuperar_de_m3', 'registrar_turno', 'transicionar_m1_para_m2', 'transicionar_m2_para_m3']

### src.src.memoria.gerente_memoria
- path: src\memoria\gerente_memoria.py
- role_guess: memory
- is_entry_candidate: False
- imports (10): ['__future__', 'chromadb', 'chromadb.utils', 'datetime', 'logging', 'memoria.metabolismo', 'os', 'shutil', 'typing', 'uuid']
- callers_inferred (0): []
- call_targets_inferred (5): ['datetime', 'logging', 'memoria.metabolismo', 'os', 'shutil']
- defined_funcs: ['__init__', '_get_timestamp', '_inferir_camada_destino', 'backup_memoria', 'executar_limpeza_manual', 'get_context', 'get_context_detalhado', 'get_estatisticas_memoria', 'get_historico_promocoes', 'initialize', 'promote_chunk', 'query', 'save_conversation_memory', 'save_memory', 'shutdown']

### src.src.memoria.m0_ejector
- path: src\memoria\m0_ejector.py
- role_guess: memory
- is_entry_candidate: False
- imports (13): ['__future__', 'hashlib', 'hmac', 'json', 'logging', 'os', 'pathlib', 'shutil', 'tempfile', 'threading', 'time', 'typing', 'zipfile']
- callers_inferred (0): []
- call_targets_inferred (11): ['hashlib', 'hmac', 'json', 'logging', 'os', 'pathlib', 'shutil', 'tempfile', 'threading', 'time', 'zipfile']
- defined_funcs: ['__init__', '_atomic_write', '_ensure_path', '_hmac_sign', '_hmac_verify', '_log_audit', '_next_version_path', 'eject_to', 'export_zip', 'inject', 'list_versions', 'set_signature_keys', 'signature_info', 'validate']

### src.src.memoria.memoria_extensao
- path: src\memoria\memoria_extensao.py
- role_guess: memory
- is_entry_candidate: True
- imports (7): ['__future__', 'argparse', 'logging', 'src.erros', 'sys', 'traceback', 'typing']
- callers_inferred (0): []
- call_targets_inferred (5): ['argparse', 'logging', 'src.erros', 'sys', 'traceback']
- defined_funcs: ['_report_and_exit', 'executar_todos_testes', 'safe_call', 'safe_import', 'teste_1_sistema_original', 'teste_2_extensao_carrega', 'teste_3_ativar_extensao', 'teste_4_adicionar_biografia', 'teste_5_contexto_sem_m0', 'teste_6_contexto_com_m0', 'teste_7_compatibilidade_store', 'teste_8_criar_templates', 'teste_9_stats_avancadas']

### src.src.memoria.memory_facade
- path: src\memoria\memory_facade.py
- role_guess: memory
- is_entry_candidate: False
- imports (10): ['__future__', 'concurrent.futures', 'functools', 'inspect', 'logging', 'os', 're', 'src.memoria.memory_facade', 'time', 'typing']
- callers_inferred (0): []
- call_targets_inferred (7): ['concurrent.futures', 'functools', 'inspect', 'logging', 'os', 're', 'time']
- defined_funcs: ['_call_memory_facade_constructor', '_criar_uma', '_nomes_de_config', '_nomes_de_sistema_memoria', '_sanitize_nome_alma', 'deco_retry', 'f_retry', 'get_or_create', 'health', 'inicializar_facades_memoria', 'retry', 'shutdown']

### src.src.memoria.sistema_memoria
- path: src\memoria\sistema_memoria.py
- role_guess: memory
- is_entry_candidate: False
- imports (14): ['__future__', 'chromadb', 'chromadb.config', 'datetime', 'enum', 'json', 'logging', 'os', 'pathlib', 'sqlite3', 'src.memoria.construtor_dataset', 'src.memoria.m0_ejector', 'time', 'typing']
- callers_inferred (0): []
- call_targets_inferred (11): ['chromadb', 'chromadb.config', 'datetime', 'json', 'logging', 'os', 'pathlib', 'sqlite3', 'src.memoria.construtor_dataset', 'src.memoria.m0_ejector', 'time']
- defined_funcs: ['__init__', '_append_archive_index', '_ensure_archive_index', '_estimar_tamanho_m3', '_get_diario', '_inicializar_chroma', '_normalize_ai', 'consultar_dataset_arquivado', 'exportar_para_fine_tuning', 'forcar_offload_m3', 'get', 'inject_m0_from_dna_folder', 'listar_datasets_arquivados', 'purge_archived_older_than', 'salvar_evento_autonomo', 'shutdown']

### src.src.memoria
- path: src\memoria\__init__.py
- role_guess: memory
- is_entry_candidate: False
- imports (9): ['__future__', 'construtor_dataset', 'gerenciador_memoria_chromadb_isolado', 'gerente_memoria', 'logging', 'memory_facade', 'sistema_memoria', 'src.config', 'typing']
- callers_inferred (0): []
- call_targets_inferred (6): ['construtor_dataset', 'gerente_memoria', 'logging', 'memory_facade', 'sistema_memoria', 'src.config']
- defined_funcs: ['get_construtor_dataset', 'get_facade_memoria', 'get_gerente_memoria', 'get_memoria_instancia', 'listar_modulos_disponiveis']

### src.src.modules.arquiteto_de_mundos
- path: src\modules\arquiteto_de_mundos.py
- role_guess: module
- is_entry_candidate: True
- imports (18): ['__future__', 'asyncio', 'concurrent.futures', 'dataclasses', 'datetime', 'enum', 'json', 'logging', 'os', 'pathlib', 'psutil', 'random', 'shutil', 'tempfile', 'threading', 'time', 'typing', 'uuid']
- callers_inferred (0): []
- call_targets_inferred (14): ['asyncio', 'concurrent.futures', 'dataclasses', 'datetime', 'json', 'logging', 'os', 'pathlib', 'random', 'shutil', 'tempfile', 'threading', 'time', 'uuid']
- defined_funcs: ['__init__', '_atomic_write_json', '_backup_corrupt', '_call_cerebro', '_carregar_historico_projetos', '_criar_backup_historico', '_executar_simulacoes_autonomas', '_handle_command', '_invoke', '_loop_monitoramento', '_now_iso', '_processar_novos_projetos', '_safe_parse_iso', '_salvar_historico_projetos', 'criar_cenario_de_simulacao', 'estado', 'executar_simulacao_autonoma', 'iniciar_monitoramento', 'obter_metricas', 'obter_status', 'para_dict', 'parar_monitoramento', 'pode_chamar', 'propor_novo_ambiente_3d', 'propor_novo_avatar_2d', 'registrar_falha', 'registrar_sucesso', 'shutdown']

### src.src.modules.automatizador_navegador_pro_final
- path: src\modules\automatizador_navegador_pro_final.py
- role_guess: module
- is_entry_candidate: False
- imports (17): ['__future__', 'collections', 'dataclasses', 'datetime', 'gzip', 'hashlib', 'json', 'logging', 'os', 'pathlib', 'playwright.sync_api', 'shutil', 'tempfile', 'threading', 'time', 'typing', 'uuid']
- callers_inferred (0): []
- call_targets_inferred (15): ['collections', 'dataclasses', 'datetime', 'gzip', 'hashlib', 'json', 'logging', 'os', 'pathlib', 'playwright.sync_api', 'shutil', 'tempfile', 'threading', 'time', 'uuid']
- defined_funcs: ['__init__', '_atomic_write_json', '_carregar_configuracoes', '_carregar_historico_termos', '_is_path_allowed', '_notificar_ui', '_now_iso', '_salvar_historico_termos', '_verificar_modo_emergencia', '_verificar_permissoes_arquivo', '_verificar_permissoes_e_termo', 'aprovar_solicitacao_termo', 'esta_valido', 'executar_acao_via_voz', 'iniciar_conversa_ia_to_ia_web', 'modo_emergencia', 'rejeitar_solicitacao_termo', 'shutdown', 'solicitar_termo_acesso', 'to_dict']

### src.src.modules.auto_diagnostico
- path: src\modules\auto_diagnostico.py
- role_guess: module
- is_entry_candidate: False
- imports (9): ['__future__', 'collections', 'datetime', 'enum', 'logging', 're', 'threading', 'time', 'typing']
- callers_inferred (0): []
- call_targets_inferred (5): ['collections', 'datetime', 'logging', 'threading', 'time']
- defined_funcs: ['__init__', '_ensure_datetime', '_loop_consciencia_temporal', '_make_safe_getter', '_now_iso', '_parse_iso', '_verificar_alarmes', '_verificar_timeline', 'acordar_consciencia_temporal', 'agendar_evento', 'calcular_urgencia', 'criar_alarme', 'dormir_consciencia_temporal', 'estatisticas_temporais', 'estimar_tempo_necessario', 'marcar_marco_temporal', 'marcos_importantes', 'o_que_tenho_agendado', 'quando_sera', 'quanto_tempo_passou_desde', 'quanto_tempo_vivi', 'safe_get']

### src.src.modules.banco_dados_llm
- path: src\modules\banco_dados_llm.py
- role_guess: module
- is_entry_candidate: False
- imports (8): ['__future__', 'concurrent.futures', 'llama_cpp', 'logging', 'memoria.rag_service', 'os', 'pathlib', 'typing']
- callers_inferred (0): []
- call_targets_inferred (5): ['concurrent.futures', 'llama_cpp', 'logging', 'memoria.rag_service', 'pathlib']
- defined_funcs: ['__init__', '_build_messages', '_generate_response', '_invoke_llm_sync', '_load_model_instance', '_model_file_ok', '_run_inference_with_timeout', '_safe_query_rag', 'initialize', 'is_phi3_loaded', 'is_vikhr_loaded', 'process_request', 'shutdown']

### src.src.modules.carregador_protocolos
- path: src\modules\carregador_protocolos.py
- role_guess: module
- is_entry_candidate: True
- imports (16): ['__future__', 'collections', 'concurrent.futures', 'dataclasses', 'datetime', 'enum', 'json', 'logging', 'logging.handlers', 'os', 'pathlib', 'shutil', 'tempfile', 'threading', 'time', 'typing']
- callers_inferred (0): []
- call_targets_inferred (12): ['collections', 'concurrent.futures', 'dataclasses', 'datetime', 'json', 'logging.handlers', 'os', 'pathlib', 'shutil', 'tempfile', 'threading', 'time']
- defined_funcs: ['__init__', '_atomic_write_json', '_carregar_ou_gerar_profiles', '_carregar_ou_gerar_protocolos', '_criar_backup_json', '_injetar_na_memoria', '_now_iso', '_parse_iso', '_salvar_profiles', '_salvar_protocolos', '_setup_logging', 'carregar_modelo', 'consultar_santuario', 'criar_diretorios', 'criar_sessao', 'desligar', 'expressar', 'gerar_prompt_sistema', 'iniciar_conversa', 'obter_contexto', 'obter_profile', 'obter_status', 'para_dict', 'pensar', 'pode_chamar', 'processar_entrada', 'registrar_falha', 'registrar_memoria', 'registrar_sucesso', 'registrar_turno', 'validar_acao']

### src.src.modules.controlador_gui
- path: src\modules\controlador_gui.py
- role_guess: module
- is_entry_candidate: False
- imports (11): ['PIL', '__future__', 'io', 'logging', 'os', 'pathlib', 'pyautogui', 're', 'threading', 'time', 'typing']
- callers_inferred (0): []
- call_targets_inferred (7): ['io', 'logging', 'pathlib', 'pyautogui', 're', 'threading', 'time']
- defined_funcs: ['__init__', '_cfg_get', '_ensure_gui_imports', '_registrar_acao', '_validar_posicao_mouse', '_validar_velocidade_mouse', '_validar_velocidade_teclado', 'allow_gui_actions_for_tests', 'clicar_em', 'digitar_texto', 'is_gui_available', 'limpar_historico_acoes_gui', 'mover_mouse_para', 'obter_historico_acoes_gui', 'obter_posicao_mouse', 'obter_screenshot', 'obter_tamanho_tela', 'pressionar_tecla', 'shutdown']

### src.src.modules.cronicas_e_testemunhos
- path: src\modules\cronicas_e_testemunhos.py
- role_guess: module
- is_entry_candidate: True
- imports (16): ['__future__', 'collections', 'datetime', 'json', 'logging', 'logging.handlers', 'os', 'pathlib', 'queue', 're', 'shutil', 'tempfile', 'threading', 'time', 'typing', 'uuid']
- callers_inferred (0): []
- call_targets_inferred (12): ['datetime', 'json', 'logging.handlers', 'os', 'pathlib', 'queue', 're', 'shutil', 'tempfile', 'threading', 'time', 'uuid']
- defined_funcs: ['__init__', '_atomic_write_json', '_carregar_cronica_da_genese', '_carregar_testemunhos_das_almas', '_compilar_cronica_da_genese', '_loop_monitoramento', '_now_iso', '_processar_fragmentos_da_cronica', '_salvar_cronica_da_genese', '_salvar_testemunhos_das_almas', '_sanitizar_texto', '_solicitar_testemunhos_periodicamente', 'adicionar_fragmento_a_cronica', 'buscar_eventos_na_historia', 'enviar_para_cerebro', 'enviar_para_cerebro_async', 'iniciar_monitoramento', 'obter_cronica_da_genese', 'obter_testemunhos_das_almas', 'obter_ultimos_registros', 'parar_monitoramento', 'pc_esta_ocioso', 'receber_comando_do_pai', 'registrar_memoria', 'registrar_testemunho_da_alma', 'runner', 'shutdown', 'validar_acao']

### src.src.modules.cronista
- path: src\modules\cronista.py
- role_guess: module
- is_entry_candidate: False
- imports (7): ['__future__', 'datetime', 'json', 'pathlib', 'sqlite3', 'threading', 'typing']
- callers_inferred (0): []
- call_targets_inferred (5): ['datetime', 'json', 'pathlib', 'sqlite3', 'threading']
- defined_funcs: ['__init__', '_get_conn', '_init_db', 'buscar_ultimos', 'exportar_json', 'registrar_evento', 'shutdown']

### src.src.modules.enfermeiro_digital
- path: src\modules\enfermeiro_digital.py
- role_guess: module
- is_entry_candidate: False
- imports (10): ['__future__', 'collections', 'datetime', 'json', 'logging', 'pathlib', 'sqlite3', 'threading', 'time', 'typing']
- callers_inferred (0): []
- call_targets_inferred (7): ['collections', 'datetime', 'json', 'logging', 'pathlib', 'sqlite3', 'threading']
- defined_funcs: ['__init__', '_atualizar_padroes_atividades', '_carregar_padroes', '_criar_alerta', '_detectar_mudanca_brusca', '_detectar_mudanca_comprimento', '_gerar_recomendacoes_personalizadas', '_init_database', '_notificar_alerta', '_obter_alertas_pendentes', '_persistir_humor', '_salvar_padrao', '_verificar_alertas', 'analisar_mensagem_pai', 'correlacionar_humor_com_hora', 'detectar_padroes_ciclicos', 'obter_atividades_efetivas', 'obter_status_saude_pai', 'registrar_atividade_efetiva', 'shutdown']

### src.src.modules.gerenciador_profiles_permanentes
- path: src\modules\gerenciador_profiles_permanentes.py
- role_guess: core
- is_entry_candidate: True
- imports (7): ['__future__', 'datetime', 'json', 'logging', 'pathlib', 'sqlite3', 'typing']
- callers_inferred (0): []
- call_targets_inferred (5): ['datetime', 'json', 'logging', 'pathlib', 'sqlite3']
- defined_funcs: ['__init__', '_carregar_perfis_base', '_criar_snapshot', '_inicializar_db', 'comparar_perfis', 'criar_perfil_eva', 'exportar_perfil_completo', 'obter_estatisticas_familia', 'obter_historico_evolucao', 'obter_perfil_base', 'obter_snapshots', 'registrar_evolucao', 'sintetizar_perfil_atual']

### src.src.modules.gerenciador_segredos_real
- path: src\modules\gerenciador_segredos_real.py
- role_guess: core
- is_entry_candidate: False
- imports (6): ['__future__', 'dotenv', 'logging', 'os', 'secrets', 'typing']
- callers_inferred (0): []
- call_targets_inferred (3): ['dotenv', 'logging', 'os']
- defined_funcs: ['__init__', '_validar_formato_basico', 'definir_segredo_temporario', 'limpar_cache', 'listar_segredos_disponiveis', 'obter_api_key', 'obter_configuracao_bd', 'obter_gerenciador_segredos', 'obter_segredo', 'validar_segredos_minimos']

### src.src.modules.motor_aprendizado
- path: src\modules\motor_aprendizado.py
- role_guess: module
- is_entry_candidate: False
- imports (13): ['__future__', 'collections', 'concurrent.futures', 'datetime', 'hashlib', 'json', 'logging', 'os', 'pathlib', 'random', 'threading', 'time', 'typing']
- callers_inferred (0): []
- call_targets_inferred (10): ['collections', 'concurrent.futures', 'datetime', 'hashlib', 'json', 'logging', 'os', 'pathlib', 'threading', 'time']
- defined_funcs: ['__init__', '_carregar_conhecimento_safe', '_descobrir_correlacoes_safe', '_identificar_padroes_safe', '_inicializar_conhecimento', '_inicializar_metricas', '_integrar_correlacoes_safe', '_integrar_padroes_safe', '_ler_json_safe', '_on_processing_complete', '_processar_buffer_async', '_processar_snapshot', '_processing_worker', '_safe_parse_iso', '_salvar_conhecimento_safe', '_salvar_experiencia_fallback', '_salvar_insights_na_memoria', '_validar_experiencia', 'buscar_memorias_periodo', 'buscar_memorias_recentes', 'consultar_conhecimento', 'criar_motor_aprendizado', 'health_check', 'monitorar_motores', 'registrar_experiencia', 'salvar_evento', 'shutdown']

### src.src.modules.motor_decisao
- path: src\modules\motor_decisao.py
- role_guess: module
- is_entry_candidate: False
- imports (12): ['__future__', 'dataclasses', 'datetime', 'enum', 'hashlib', 'json', 'logging', 'pathlib', 'src.core.banco_corpus_etico', 'src.memoria.sistema_memoria', 'typing', 'uuid']
- callers_inferred (0): []
- call_targets_inferred (8): ['dataclasses', 'datetime', 'hashlib', 'json', 'logging', 'pathlib', 'src.core.banco_corpus_etico', 'uuid']
- defined_funcs: ['__hash__', '__init__', '_calcular_peso', '_calcular_relevancia', '_calcular_urgencia', '_carregar_leis', '_carregar_memoria', '_carregar_protocolos', '_criar_leis_emergencia', '_criar_protocolos_padrao', '_extrair_tags', '_gerar_id_analise', '_gerar_processo_reflexao', '_gerar_proposta_nova_lei', '_gerar_questoes_reflexao', '_resumir_decisao', 'buscar_aplicaveis', 'buscar_decisoes_similares', 'buscar_por_situacao', 'consultar_corpo_legal', 'estatisticas', 'health_check', 'historico_decisoes', 'obter_motor', 'preparar_analise', 'registrar_decisao', 'registrar_material_analise', 'salvar_memoria']

### src.src.modules.motor_expressao
- path: src\modules\motor_expressao.py
- role_guess: module
- is_entry_candidate: False
- imports (14): ['__future__', 'config.config', 'dataclasses', 'datetime', 'enum', 'hashlib', 'logging', 'queue', 'sistema_audicao_real', 'sistema_voz_real', 'src.modules.sentidos_humanos', 'threading', 'time', 'typing']
- callers_inferred (0): []
- call_targets_inferred (6): ['dataclasses', 'datetime', 'hashlib', 'logging', 'queue', 'threading']
- defined_funcs: ['__init__', '_enqueue', '_executar_expressao', '_load_config_values', '_make_get_safe', '_processar_fila', 'expressar', 'expressar_fala', 'get_safe', 'iniciar_processamento', 'parar_processamento', 'preview_hash', 'shutdown']

### src.src.modules.motor_expressao_individual
- path: src\modules\motor_expressao_individual.py
- role_guess: module
- is_entry_candidate: False
- imports (9): ['cv2', 'logging', 'numpy', 'os', 'pygame', 'pyttsx3', 'threading', 'time', 'typing']
- callers_inferred (0): []
- call_targets_inferred (6): ['logging', 'os', 'pygame', 'pyttsx3', 'threading', 'time']
- defined_funcs: ['__init__', '_atualizar_imagem_avatar', '_falar_texto', '_inicializar_pygame', '_inicializar_voz', '_loop_avatar', 'atualizar_rosto_individual', 'cena_emocional', 'esconder_avatar', 'falar', 'mostrar_avatar', 'parar_reproducao_individual', 'shutdown']

### src.src.modules.motor_iniciativa
- path: src\modules\motor_iniciativa.py
- role_guess: module
- is_entry_candidate: False
- imports (14): ['__future__', 'collections', 'datetime', 'hashlib', 'json', 'logging', 'pathlib', 'queue', 'random', 'src.modules.motor_curiosidade', 'threading', 'time', 'typing', 'uuid']
- callers_inferred (0): []
- call_targets_inferred (6): ['collections', 'datetime', 'logging', 'queue', 'threading', 'time']
- defined_funcs: ['__init__', '_avaliar_estado_interno', '_calcular_vontade_de_agir', '_carregar_gatilhos', '_consumir_energia', '_criar_iniciativa', '_estimar_energia_acao', '_executar_iniciativa', '_fazer_pausa', '_loop_consciencia', '_make_get_safe', '_perceber_contexto', '_preciso_descansar', '_registrar_execucao', '_registrar_sessao_vida', '_sentir_desejos', '_traduzir_desejo_em_acao', 'acordar', 'buscar_memorias_por_texto', 'buscar_por_tipo', 'dormir', 'gerar_desejo_interno', 'get_safe', 'o_que_quero_fazer_agora', 'obter_proxima_iniciativa', 'peek_proxima_iniciativa', 'quantas_iniciativas_pendentes', 'registrar_executor', 'salvar_evento', 'shutdown']

### src.src.modules.motor_rotina
- path: src\modules\motor_rotina.py
- role_guess: module
- is_entry_candidate: False
- imports (14): ['__future__', 'collections', 'ctypes', 'datetime', 'dateutil.parser', 'json', 'logging', 'os', 'pathlib', 'psutil', 'threading', 'time', 'typing', 'uuid']
- callers_inferred (0): []
- call_targets_inferred (10): ['collections', 'ctypes', 'datetime', 'dateutil.parser', 'json', 'logging', 'os', 'pathlib', 'psutil', 'threading']
- defined_funcs: ['__init__', '_analisar_logs_de_erro', '_carregar_historico_diagnosticos', '_carregar_protocolo_habilidades', '_loop_monitoramento', '_make_get_safe', '_propor_solucao_ao_pai', '_realizar_diagnostico', '_safe_parse_iso', '_salvar_historico_diagnosticos', '_salvar_protocolo_habilidades', '_setup_config_getter', 'get_real', 'get_safe', 'iniciar_monitoramento', 'parar_monitoramento', 'pc_esta_ocioso', 'shutdown']

### src.src.modules.percepcao_temporal
- path: src\modules\percepcao_temporal.py
- role_guess: module
- is_entry_candidate: False
- imports (9): ['__future__', 'collections', 'datetime', 'enum', 'logging', 'threading', 'time', 'typing', 'uuid']
- callers_inferred (0): []
- call_targets_inferred (6): ['collections', 'datetime', 'logging', 'threading', 'time', 'uuid']
- defined_funcs: ['__init__', '_loop_consciencia_temporal', '_make_get_safe', '_setup_config_getter', '_verificar_alarmes', '_verificar_timeline', 'acordar_consciencia_temporal', 'agendar_evento', 'ajustar_percepcao', 'calcular_urgencia', 'criar_alarme', 'dormir_consciencia_temporal', 'estatisticas_temporais', 'estimar_tempo_necessario', 'get_real', 'get_safe', 'iniciar_ciclo', 'marcar_marco_temporal', 'marcos_importantes', 'mudar_ritmo', 'o_que_tenho_agendado', 'quando_sera', 'quanto_tempo_passou_desde', 'quanto_tempo_vivi', 'shutdown', 'terminar_ciclo']

### src.src.modules.response_queue_manager
- path: src\modules\response_queue_manager.py
- role_guess: core
- is_entry_candidate: False
- imports (11): ['__future__', 'collections', 'datetime', 'hashlib', 'json', 'logging', 'pathlib', 'queue', 'threading', 'time', 'typing']
- callers_inferred (0): []
- call_targets_inferred (9): ['collections', 'datetime', 'hashlib', 'json', 'logging', 'pathlib', 'queue', 'threading', 'time']
- defined_funcs: ['__init__', '_atualizar_metrica_tempo_fila', '_eh_batchavel', '_flush_batches', '_gerar_hash', '_persistir_critica', '_verificar_rate_limit', 'carregar_criticas_persistidas', 'clear', 'empty', 'get', 'get_batch', 'get_nowait', 'obter_metricas', 'put', 'put_nowait', 'qsize', 'shutdown']

### src.src.modules.ritual_santuario
- path: src\modules\ritual_santuario.py
- role_guess: module
- is_entry_candidate: False
- imports (12): ['__future__', 'collections', 'datetime', 'dateutil.parser', 'hashlib', 'json', 'logging', 'numpy', 'pathlib', 'statistics', 'threading', 'typing']
- callers_inferred (0): []
- call_targets_inferred (10): ['collections', 'datetime', 'dateutil.parser', 'hashlib', 'json', 'logging', 'numpy', 'pathlib', 'statistics', 'threading']
- defined_funcs: ['__init__', '_analisar_distribuicao_temporal', '_analisar_estatisticas_gerais', '_analisar_frequencias', '_calcular_metricas_emocionais', '_call', '_carregar_valores_adaptado', '_check_metabolismo_minimo', '_contar_memorias_recentes', '_criar_intencao_simples', '_fase_contemplacao_adaptada', '_fase_integracao_adaptada', '_fase_recolhimento_adaptada', '_fase_renovacao_adaptada', '_fase_transformacao_adaptada', '_gerar_mensagem_renovacao', '_gerar_recomendacoes_basicas', '_gerar_sugestoes_ajuste', '_hash_preview', '_identificar_areas_envolvimento', '_identificar_tendencias', '_normalizar_memoria', '_obter_data_ultimo_ritual', '_registrar_ritual_adaptado', '_safe_parse_iso', '_salvar_ritual_local', '_salvar_valores_adaptado', 'buscar_memorias_periodo', 'buscar_metadado', 'buscar_por_tipo', 'deve_entrar_santuario', 'executar_ritual_se_necessario', 'iniciar_ritual', 'obter_resumo_valores', 'salvar_evento', 'salvar_metadado']

### src.src.modules.sistema_de_precedentes
- path: src\modules\sistema_de_precedentes.py
- role_guess: module
- is_entry_candidate: False
- imports (13): ['__future__', 'dataclasses', 'datetime', 'hashlib', 'json', 'logging', 'os', 'pathlib', 're', 'src.memoria.sistema_memoria', 'threading', 'typing', 'uuid']
- callers_inferred (0): []
- call_targets_inferred (8): ['datetime', 'hashlib', 'json', 'logging', 'pathlib', 're', 'threading', 'uuid']
- defined_funcs: ['__init__', '_atualizar_indices_locais', '_carregar_precedente_do_santuario', '_cfg_get_compat', '_enforce_retention_policy', '_filter_and_tokens', '_load_indices_from_disk', '_salvar_precedente_no_santuario', '_save_indices_to_disk', 'buscar_precedentes_por_lei', 'buscar_precedentes_por_palavra_chave', 'buscar_precedentes_por_similaridade', 'from_dict', 'reconstruir_indices_a_partir_do_santuario', 'registrar_precedente', 'save_precedente', 'to_dict']

### src.src.modules.validador_emocoes_real
- path: src\modules\validador_emocoes_real.py
- role_guess: module
- is_entry_candidate: False
- imports (10): ['__future__', 'dataclasses', 'hashlib', 'json', 'logging', 'pathlib', 'pydantic', 're', 'time', 'typing']
- callers_inferred (0): []
- call_targets_inferred (6): ['hashlib', 'json', 'logging', 'pathlib', 're', 'time']
- defined_funcs: ['__init__', '_carregar_dados', '_carregar_e_indexar_lexicos', '_corrigir_violacoes_reais', '_detectar_idioma', '_extrair_mapa_risco', '_extrair_principios', '_precompile_patterns', '_scan_and_load_by_pattern', '_selecionar_lexico', 'atualizar', 'from_dict', 'obter_metricas_sistema', 'obter_pontuacao_risco', 'reload_lexicons', 'validar_resposta_real']

### src.src.modules
- path: src\modules\__init__.py
- role_guess: module
- is_entry_candidate: False
- imports (0): []
- callers_inferred (0): []
- call_targets_inferred (0): []
- defined_funcs: []

### src.src.modules.sentidos.curiosity
- path: src\modules\sentidos\curiosity.py
- role_guess: module
- is_entry_candidate: False
- imports (9): ['__future__', 'collections', 'datetime', 'json', 'logging', 'pathlib', 're', 'threading', 'typing']
- callers_inferred (0): []
- call_targets_inferred (6): ['collections', 'datetime', 'json', 'logging', 're', 'threading']
- defined_funcs: ['__init__', '_calcular_acao_por_memorias', '_calcular_prioridade', '_now', '_parse_timestamp', '_registrar_desejo', '_tokenize_topics', 'avaliar_estado_interno', 'gerar_desejo_interno', 'obter_metricas']

### src.src.modules.sentidos.decision
- path: src\modules\sentidos\decision.py
- role_guess: module
- is_entry_candidate: False
- imports (5): ['__future__', 'logging', 'math', 'random', 'typing']
- callers_inferred (0): []
- call_targets_inferred (3): ['logging', 'math', 'random']
- defined_funcs: ['__init__', '_clamp01', '_normalize_option', '_score_intuitivo', '_score_racional', '_score_valores', 'ajustar_pesos', 'decidir', 'get_pesos', 'set_pesos', 'tie_key']

### src.src.modules.sentidos.motor_expressao
- path: src\modules\sentidos\motor_expressao.py
- role_guess: module
- is_entry_candidate: False
- imports (8): ['__future__', 'logging', 'pathlib', 'sistema_voz', 'tempfile', 'threading', 'time', 'typing']
- callers_inferred (0): []
- call_targets_inferred (3): ['logging', 'sistema_voz', 'threading']
- defined_funcs: ['__init__', '_safe_put_ui', 'atualizar_avatar', 'falar', 'parar', 'shutdown', 'toggle_voz']

### src.src.modules.sentidos.sentidos_humanos
- path: src\modules\sentidos\sentidos_humanos.py
- role_guess: module
- is_entry_candidate: False
- imports (6): ['__future__', 'logging', 'sistema_audicao', 'sistema_voz', 'threading', 'typing']
- callers_inferred (0): []
- call_targets_inferred (4): ['logging', 'sistema_audicao', 'sistema_voz', 'threading']
- defined_funcs: ['__init__', '_carregar_sentimentos_padrao', '_make_config_getter', 'analisar_sentimento', 'executar_testes_reais_interativos_async', 'falar', 'get_safe', 'iniciar', 'ouvir', 'shutdown']

### src.src.modules.sentidos.sistema_audicao
- path: src\modules\sentidos\sistema_audicao.py
- role_guess: module
- is_entry_candidate: False
- imports (6): ['__future__', 'logging', 'openai', 'speech_recognition', 'threading', 'typing']
- callers_inferred (0): []
- call_targets_inferred (4): ['logging', 'openai', 'speech_recognition', 'threading']
- defined_funcs: ['__init__', '_make_config_getter', '_transcrever_sr_local', 'get_safe', 'ouvir_microfone', 'shutdown']

### src.src.modules.sentidos.sistema_voz
- path: src\modules\sentidos\sistema_voz.py
- role_guess: module
- is_entry_candidate: False
- imports (7): ['__future__', 'configparser', 'elevenlabs', 'logging', 'pyttsx3', 'threading', 'typing']
- callers_inferred (0): []
- call_targets_inferred (4): ['elevenlabs', 'logging', 'pyttsx3', 'threading']
- defined_funcs: ['__init__', '_make_config_getter', '_safe_float', '_safe_int', 'falar', 'get_safe', 'listar_vozes', 'shutdown']

### src.src.modules.sentidos
- path: src\modules\sentidos\__init__.py
- role_guess: module
- is_entry_candidate: False
- imports (7): ['__future__', 'logging', 'motor_expressao', 'sentidos_humanos', 'sistema_audicao', 'sistema_voz', 'typing']
- callers_inferred (0): []
- call_targets_inferred (5): ['logging', 'motor_expressao', 'sentidos_humanos', 'sistema_audicao', 'sistema_voz']
- defined_funcs: ['criar_motor_expressao', 'criar_sentidos_humanos', 'criar_sistema_audicao', 'criar_sistema_voz']

### src.src.segurança.detector_sandbox
- path: src\segurança\detector_sandbox.py
- role_guess: unknown
- is_entry_candidate: False
- imports (7): ['RestrictedPython', '__future__', 'logging', 'subprocess', 'sys', 'time', 'typing']
- callers_inferred (0): []
- call_targets_inferred (3): ['logging', 'subprocess', 'time']
- defined_funcs: ['__init__', '_detectar_docker', '_detectar_restricted_python', '_detectar_tudo', '_determinar_modo', 'obter_instrucoes_instalacao', 'obter_status', 'tentar_ativar_docker']

### src.src.segurança.sandbox_executor
- path: src\segurança\sandbox_executor.py
- role_guess: unknown
- is_entry_candidate: False
- imports (16): ['RestrictedPython', 'RestrictedPython.Guards', '__future__', 'ast', 'datetime', 'docker', 'json', 'logging', 'os', 'pathlib', 're', 'subprocess', 'threading', 'time', 'typing', 'uuid']
- callers_inferred (0): []
- call_targets_inferred (10): ['RestrictedPython', 'ast', 'datetime', 'docker', 'json', 'logging', 're', 'threading', 'time', 'uuid']
- defined_funcs: ['__init__', '_executar_em_docker', '_executar_modo_restrito', 'executar_codigo', 'obter_status', 'parar_todos_containers', 'shutdown', 'validar_codigo']

### src.src.segurança
- path: src\segurança\__init__.py
- role_guess: unknown
- is_entry_candidate: False
- imports (2): ['__future__', 'sandbox_executor']
- callers_inferred (0): []
- call_targets_inferred (0): []
- defined_funcs: []

### src.src.tools.build_import_graph
- path: src\tools\build_import_graph.py
- role_guess: tools
- is_entry_candidate: True
- imports (6): ['argparse', 'collections', 'graphviz', 'json', 'pathlib', 'sys']
- callers_inferred (0): []
- call_targets_inferred (5): ['argparse', 'collections', 'graphviz', 'json', 'pathlib']
- defined_funcs: ['build_graph', 'detect_cycles', 'dfs', 'generate_report', 'main', 'parse_imports', 'visualize_graph']

### src.src.tools.check_env
- path: src\tools\check_env.py
- role_guess: tools
- is_entry_candidate: True
- imports (6): ['argparse', 'importlib.metadata', 'json', 'subprocess', 'sys', 'typing']
- callers_inferred (0): []
- call_targets_inferred (4): ['argparse', 'importlib.metadata', 'json', 'subprocess']
- defined_funcs: ['check_command', 'check_package', 'generate_report', 'main']

### src.src.tools
- path: src\tools\__init__.py
- role_guess: tools
- is_entry_candidate: False
- imports (8): ['__future__', 'build_import_graph', 'check_env', 'find_placeholders', 'logging', 'scan_exports_and_placeholders', 'test_imports', 'typing']
- callers_inferred (0): []
- call_targets_inferred (1): ['logging']
- defined_funcs: []

### src.src.ui.interface_arca_atualizada
- path: src\ui\interface_arca_atualizada.py
- role_guess: unknown
- is_entry_candidate: True
- imports (21): ['PIL', 'asyncio', 'customtkinter', 'dataclasses', 'datetime', 'hashlib', 'json', 'logging', 'os', 'pathlib', 'queue', 'shutil', 'speech_recognition', 'src.core.coracao_orquestrador', 'system_tray', 'threading', 'time', 'tkinter.messagebox', 'typing', 'vosk', 'wave']
- callers_inferred (0): []
- call_targets_inferred (15): ['PIL', 'asyncio', 'customtkinter', 'dataclasses', 'json', 'logging', 'pathlib', 'queue', 'speech_recognition', 'system_tray', 'threading', 'time', 'tkinter.messagebox', 'vosk', 'wave']
- defined_funcs: ['__init__', '__lt__', '_abrir_app', '_abrir_chat', '_abrir_menu_iniciar', '_build_ui', '_call_and_show_list', '_configure_window', '_criar_desktop_inicial', '_execute_with_error_handling', '_fade_in', '_fade_out', '_get_almas', '_get_selected_alma', '_handle_error', '_handle_response', '_handle_warning', '_inicializar_painel', '_init_system_tray', '_log', '_periodic_refresh', '_processar_respostas', '_show_login_modal', '_show_painel', '_show_result', '_start_response_thread', '_sync_with_coracao', '_tray_callback', '_update_avatar_image', 'abrir_sessao', 'aceitar_oportunidade', 'add_message', 'adicionar_programa', 'analisar', 'analisar_mensagem', 'apelar_criador', 'aplicar_sentenca', 'aprovar', 'aprovar_deploy', 'aprovar_termo', 'ativar_aliada', 'ativar_modo_emergencia', 'atualizar_rosto', 'buscar_ferramenta', 'buscar_leis_aplicaveis', 'buscar_por_lei', 'buscar_por_palavra', 'buscar_por_similaridade', 'carregar_conhecimento', 'consultar_aliada', 'consultar_biblia', 'consultar_julgamentos', 'consultar_registros_vidro', 'consultar_scr', 'consultar_status', 'correlacionar_humor', 'criar_proposta', 'desativar_aliada', 'detectar_hdd_externo', 'detectar_padroes', 'detectar_usb', 'entrar_capela', 'enviar_comando', 'estatisticas', 'executar_ciclo', 'executar_comando_voz', 'executar_ferramenta', 'falar_async', 'fechar_sessao', 'forcar_sugestao', 'gerar_artefatos', 'gerar_relatorio_manual', 'health_check', 'hide', 'iniciar_construcao', 'iniciar_conversa', 'iniciar_julgamento', 'iniciar_monitoramento', 'iniciar_servidor', 'iniciar_video_fala', 'instalar_aprovada', 'listar_decisoes', 'listar_disponiveis', 'listar_em_analise', 'listar_em_construcao', 'listar_em_producao', 'listar_instaladas', 'listar_oportunidades', 'listar_pendentes', 'listar_processos_ativos', 'listar_programas', 'listar_pronto_deploy', 'listar_propostas', 'listar_sessoes_ativas', 'log', 'login', 'meditar', 'mover_para_analise', 'obter_atividades', 'obter_estado_familia', 'obter_estatisticas', 'obter_estatisticas_cache', 'obter_estatisticas_memoria', 'obter_historico', 'obter_historico_ia', 'obter_info_sistema', 'obter_metricas', 'obter_progresso', 'obter_relatorio', 'obter_relatorio_atual', 'obter_resumo', 'obter_status', 'parar_construcao', 'parar_fala', 'parar_monitoramento', 'parar_servidor', 'parar_video_fala', 'processar_requisicao', 'propor_ferramenta', 'propor_lei', 'publicar_decisao', 'recarregar_config', 'receber_denuncia', 'reconstruir_indices', 'recusar_oportunidade', 'refresh', 'registrar_atividade', 'registrar_decisao', 'registrar_precedente', 'rejeitar', 'rejeitar_termo', 'sair_capela', 'salvar_conhecimento', 'send_message', 'show', 'shutdown', 'solicitar_missao', 'status_capela', 'suspender_sentenca', 'testar_codigo', 'testar_velocidade_hdd', 'toggle_cam', 'toggle_mic', 'toggle_voz', 'transcrever', 'transcrever_audio', 'update_chat', 'ver_historico', 'verificar_espaco_hdd', 'votar', 'votar_proposta']

### src.src.ui
- path: src\ui\__init__.py
- role_guess: unknown
- is_entry_candidate: False
- imports (8): ['alma_avatar_frame', 'core', 'core.coracao_orquestrador', 'interface_arca_atualizada', 'logging', 'modules', 'queue', 'system_tray']
- callers_inferred (0): []
- call_targets_inferred (5): ['core.coracao_orquestrador', 'interface_arca_atualizada', 'logging', 'queue', 'system_tray']
- defined_funcs: ['iniciar_arca']

### src.src.utils.config_utils
- path: src\utils\config_utils.py
- role_guess: unknown
- is_entry_candidate: False
- imports (1): ['typing']
- callers_inferred (0): []
- call_targets_inferred (0): []
- defined_funcs: ['cfg_get', 'cfg_get_bool', 'cfg_get_float', 'cfg_get_int']

### src.src.utils.timing_decorator
- path: src\utils\timing_decorator.py
- role_guess: unknown
- is_entry_candidate: True
- imports (2): ['src.core.cerebro_familia', 'time']
- callers_inferred (0): []
- call_targets_inferred (2): ['src.core.cerebro_familia', 'time']
- defined_funcs: ['generate_response', 'measure_with_engine']

### src.src.utils
- path: src\utils\__init__.py
- role_guess: unknown
- is_entry_candidate: False
- imports (3): ['__future__', 'logging', 'typing']
- callers_inferred (0): []
- call_targets_inferred (1): ['logging']
- defined_funcs: []


## Heuristics usadas
- imports estáticos via AST (Import / ImportFrom)
- chamadas inferidas quando o nome chamado corresponde a um alias importado
- entry candidate: presença de guard `if __name__ == "__main__"` ou definição de função com nome de entrada

## Limitações
- Não detecta imports dinâmicos (importlib com nomes dinâmicos, exec, etc.)
- Chamadas complexas/encadeadas não são sempre resolvidas
- Requer ambiente correto para interpretar intenções (ex.: strings que representam módulos não detectados)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
banco_dados_propostas.py - Persistência de Propostas

Wrapper SQLite thread-safe com suporte a:
- CRUD completo
- Histórico
- Duplicatas
- Índices para performance
"""
from __future__ import annotations


import sqlite3
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

# Importar o módulo principal
from .sistema_propostas_ferramentas import GerenciadorPropostas

__all__ = ["GerenciadorPropostas"]


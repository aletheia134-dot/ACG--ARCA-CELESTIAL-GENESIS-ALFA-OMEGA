#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
"""
banco_dados_propostas.py - Persistncia de Propostas

Wrapper SQLite thread-safe com suporte a:
- CRUD completo
- histórico
- Duplicatas
- índices para performance
"""


import sqlite3
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

# Importar o módulo principal
from .sistema_propostas_ferramentas import GerenciadorPropostas

__all__ = ["GerenciadorPropostas"]


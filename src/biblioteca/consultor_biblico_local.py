#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path
from typing import List, Dict, Any, Optional
import json
import logging
import re
import os
import tempfile

logger = logging.getLogger("LocalConsultorBiblia")
logger.addHandler(logging.NullHandler())

try:
    import fitz
except:
    logging.getLogger(__name__).warning("âš ï¸ fitz não disponível")
    fitz = None

try:
    from pdf2image import convert_from_path  # type: ignore
except:
    logging.getLogger(__name__).warning("âš ï¸ fitz não disponível")
    fitz = None

try:
    import pytesseract
except:
    logging.getLogger(__name__).warning("âš ï¸ fitz não disponível")
    fitz = None

try:
    from PyPDF2 import PdfReader  # type: ignore
except:
    logging.getLogger(__name__).warning("âš ï¸ fitz não disponível")
    fitz = None


def _atomic_write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp_", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=2)
        os.replace(tmp, str(path))
    except Exception:
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except Exception:
            pass
        raise


def _safe_load_json(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        logger.exception("Falha ao ler JSON %s", path)
        return None


def _normalize_whitespace(s: str) -> str:
    return " ".join(s.split())


def _is_text_sufficient(t: Optional[str], min_chars: int = 120) -> bool:
    if not t:
        return False
    return len(t.strip()) >= min_chars


def extract_text_pymupdf(pdf_path: Path) -> str:
    if fitz is None:
        raise RuntimeError("PyMuPDF (fitz) não disponível")
    parts: List[str] = []
    try:
        doc = fitz.open(str(pdf_path))
        for page in doc:
            try:
                txt = page.get_text("text") or ""
            except Exception:
                txt = ""
            parts.append(txt)
    except Exception:
        logger.exception("PyMuPDF falhou ao processar %s", pdf_path)
        return ""
    return "\n".join(parts).strip()


def extract_text_pypdf2(pdf_path: Path) -> str:
    if PdfReader is None:
        raise RuntimeError("PyPDF2 não disponível")
    parts: List[str] = []
    try:
        reader = PdfReader(str(pdf_path))
        for page in reader.pages:
            try:
                txt = page.extract_text() or ""
            except Exception:
                txt = ""
            parts.append(txt)
    except Exception:
        logger.exception("PyPDF2 falhou ao processar %s", pdf_path)
        return ""
    return "\n".join(parts).strip()


def ocr_pdf_via_images(pdf_path: Path, poppler_path: Optional[str] = None, ocr_lang: str = "por") -> str:
    if convert_from_path is None:
        raise RuntimeError("pdf2image não disponível")
    if pytesseract is None:
        raise RuntimeError("pytesseract não disponível")
    try:
        images = convert_from_path(str(pdf_path), dpi=300, poppler_path=poppler_path) if poppler_path else convert_from_path(str(pdf_path), dpi=300)
    except Exception:
        logger.exception("pdf2image falhou ao renderizar %s (poppler_path=%s)", pdf_path, poppler_path)
        return ""
    parts: List[str] = []
    for img in images:
        try:
            txt = pytesseract.image_to_string(img, lang=ocr_lang) if ocr_lang else pytesseract.image_to_string(img)
        except Exception:
            try:
                txt = pytesseract.image_to_string(img)
            except Exception:
                txt = ""
        parts.append(txt)
    return "\n".join(parts).strip()


class LocalConsultorBiblia:
    def __init__(self, caminho: Optional[Path], pdf_cache: bool = True, poppler_path: Optional[str] = None, tesseract_cmd: Optional[str] = None, ocr_lang: str = "por"):
        self.caminho = Path(caminho) if caminho else None
        self.pdf_cache = bool(pdf_cache)
        self.poppler_path = str(poppler_path) if poppler_path else None
        self.ocr_lang = str(ocr_lang) if ocr_lang else ""
        if tesseract_cmd:
            try:
                pytesseract.pytesseract.tesseract_cmd = str(tesseract_cmd)
            except Exception:
                logger.debug("Não foi possível definir tesseract_cmd para pytesseract")
        self._structured: Dict[str, Any] = {}
        self._pdf_texts: Dict[str, str] = {}
        if not self.caminho:
            logger.warning("LocalConsultorBiblia inicializado sem caminho (caminho=None).")
            return
        try:
            if self.caminho.is_file() and self.caminho.suffix.lower() == ".json":
                data = _safe_load_json(self.caminho)
                if isinstance(data, dict):
                    self._structured = data
            elif self.caminho.is_dir():
                self._load_pdf_directory(self.caminho)
            elif self.caminho.is_file() and self.caminho.suffix.lower() == ".pdf":
                text = self._extract_text_with_cache(self.caminho)
                if text:
                    self._pdf_texts[str(self.caminho)] = text
        except Exception:
            logger.exception("Erro inicializando LocalConsultorBiblia para %s", self.caminho)

    def _load_pdf_directory(self, dirpath: Path) -> None:
        for pdf in sorted(dirpath.glob("*.pdf")):
            try:
                text = self._extract_text_with_cache(pdf)
                if text:
                    self._pdf_texts[str(pdf)] = text
            except Exception:
                logger.exception("Erro ao processar PDF %s", pdf)

    def _cache_path_for_pdf(self, pdf_path: Path) -> Path:
        return pdf_path.with_suffix(pdf_path.suffix + ".json")

    def _extract_text_with_cache(self, pdf_path: Path) -> str:
        cache_path = self._cache_path_for_pdf(pdf_path)
        if self.pdf_cache and cache_path.exists():
            try:
                data = _safe_load_json(cache_path)
                txt = data.get("texto_completo") if isinstance(data, dict) else None
                if txt:
                    return str(txt)
            except Exception:
                logger.debug("Falha lendo cache %s; reprocessando", cache_path)
        full_text = ""
        if fitz is not None:
            try:
                full_text = extract_text_pymupdf(pdf_path)
            except Exception:
                full_text = ""
        if not _is_text_sufficient(full_text) and PdfReader is not None:
            try:
                fallback_text = extract_text_pypdf2(pdf_path)
                if _is_text_sufficient(fallback_text) and len(fallback_text) > len(full_text):
                    full_text = fallback_text
            except Exception:
                pass
        if not _is_text_sufficient(full_text):
            logger.info("Texto insuficiente em %s; tentando OCR", pdf_path)
            try:
                ocr_text = ocr_pdf_via_images(pdf_path, poppler_path=self.poppler_path, ocr_lang=self.ocr_lang)
                if _is_text_sufficient(ocr_text):
                    full_text = ocr_text
            except Exception:
                logger.exception("OCR falhou para %s", pdf_path)
        full_text = _normalize_whitespace(full_text)
        if self.pdf_cache and full_text:
            try:
                _atomic_write_json(self._cache_path_for_pdf(pdf_path), {"texto_completo": full_text})
            except Exception:
                logger.debug("Falha ao gravar cache para %s", pdf_path)
        return full_text

    def is_pdf_scanned(self, pdf_path: Path) -> bool:
        try:
            text = ""
            if fitz is not None:
                doc = fitz.open(str(pdf_path))
                for i, page in enumerate(doc):
                    if i >= 3:
                        break
                    txt = page.get_text("text") or ""
                    text += txt
            elif PdfReader is not None:
                reader = PdfReader(str(pdf_path))
                for i, page in enumerate(reader.pages):
                    if i >= 3:
                        break
                    try:
                        text += (page.extract_text() or "")
                    except Exception:
                        pass
            else:
                return True
            return not _is_text_sufficient(text, min_chars=80)
        except Exception:
            return True

    def buscar_por_tema(self, tema: str, limite: int = 3, contexto_chars: int = 200) -> List[Dict[str, Any]]:
        if not tema or not str(tema).strip():
            return []
        termo = str(tema).strip().casefold()
        results: List[Dict[str, Any]] = []
        try:
            if isinstance(self._structured, dict) and self._structured:
                for key, entry in self._structured.items():
                    if isinstance(entry, dict):
                        txt = str(entry.get("texto", "")).casefold()
                        if termo in txt:
                            snippet = self._snippet_from_text(entry.get("texto", ""), termo, contexto_chars)
                            results.append({"fonte": str(key), "trecho": snippet, "original": entry})
                            if len(results) >= limite:
                                return results
                    else:
                        txt = str(entry).casefold()
                        if termo in txt:
                            snippet = self._snippet_from_text(str(entry), termo, contexto_chars)
                            results.append({"fonte": str(key), "trecho": snippet, "original": entry})
                            if len(results) >= limite:
                                return results
        except Exception:
            logger.exception("Erro ao buscar em JSON estruturado")
        try:
            if self.caminho and self.caminho.is_dir() and not self._pdf_texts:
                self._load_pdf_directory(self.caminho)
            for path_str, full_text in self._pdf_texts.items():
                low = full_text.casefold()
                for m in re.finditer(re.escape(termo), low):
                    start = max(0, m.start() - contexto_chars)
                    end = min(len(full_text), m.end() + contexto_chars)
                    trecho = full_text[start:end].strip()
                    trecho = _normalize_whitespace(trecho)
                    results.append({"fonte": path_str, "trecho": trecho, "context_range": (start, end)})
                    if len(results) >= limite:
                        return results
            if self.caminho and self.caminho.is_dir():
                for pdf in sorted(self.caminho.glob("*.pdf")):
                    pstr = str(pdf)
                    if pstr in self._pdf_texts:
                        continue
                    txt = self._extract_text_with_cache(pdf)
                    if not txt:
                        continue
                    self._pdf_texts[pstr] = txt
                    low = txt.casefold()
                    for m in re.finditer(re.escape(termo), low):
                        start = max(0, m.start() - contexto_chars)
                        end = min(len(txt), m.end() + contexto_chars)
                        trecho = _normalize_whitespace(txt[start:end])
                        results.append({"fonte": pstr, "trecho": trecho, "context_range": (start, end)})
                        if len(results) >= limite:
                            return results
        except Exception:
            logger.exception("Erro ao buscar em PDFs")
        return results

    def _snippet_from_text(self, text: Optional[str], termo_casefold: str, contexto_chars: int) -> str:
        if not text:
            return ""
        low = str(text).casefold()
        m = re.search(re.escape(termo_casefold), low)
        if not m:
            return _normalize_whitespace(text[:contexto_chars])
        start = max(0, m.start() - contexto_chars)
        end = min(len(text), m.end() + contexto_chars)
        trecho = text[start:end].strip()
        return _normalize_whitespace(trecho)

    def preprocess_all_pdfs(self, force_reextract: bool = False) -> int:
        if not self.caminho or not self.caminho.is_dir():
            return 0
        processed = 0
        for pdf in sorted(self.caminho.glob("*.pdf")):
            cache_path = self._cache_path_for_pdf(pdf)
            if cache_path.exists() and not force_reextract:
                data = _safe_load_json(cache_path) or {}
                txt = data.get("texto_completo", "")
                if txt:
                    self._pdf_texts[str(pdf)] = txt
                    processed += 1
                    continue
            try:
                txt = self._extract_text_with_cache(pdf)
                if txt:
                    self._pdf_texts[str(pdf)] = txt
                processed += 1
            except Exception:
                logger.exception("Erro processando PDF %s", pdf)
        return processed

    def clear_cache(self) -> None:
        if not self.caminho or not self.caminho.is_dir():
            return
        for pdf in sorted(self.caminho.glob("*.pdf")):
            cache_path = self._cache_path_for_pdf(pdf)
            try:
                if cache_path.exists():
                    cache_path.unlink()
            except Exception:
                logger.debug("Falha ao remover cache %s", cache_path)

    def available_sources(self) -> Dict[str, Any]:
        return {"json_keys": list(self._structured.keys())[:20], "pdf_count": len(self._pdf_texts), "pdf_paths": list(self._pdf_texts.keys())[:10]}


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("path", nargs="?", help="Path to JSON file or directory of PDFs")
    p.add_argument("--term", default="amor")
    p.add_argument("--poppler", default=None)
    p.add_argument("--tesseract", default=None)
    p.add_argument("--ocr-lang", default="por")
    args = p.parse_args()
    path = Path(args.path) if args.path else None
    consul = LocalConsultorBiblia(path, pdf_cache=True, poppler_path=args.poppler, tesseract_cmd=args.tesseract, ocr_lang=args.ocr_lang)
    print("Sources:", consul.available_sources())
    hits = consul.buscar_por_tema(args.term, limite=5, contexto_chars=200)
    print("Hits:", json.dumps(hits, ensure_ascii=False, indent=2))

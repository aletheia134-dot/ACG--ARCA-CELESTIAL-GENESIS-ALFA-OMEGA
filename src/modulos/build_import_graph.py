#!/usr/bin/env python3
# tools/build_import_graph.py
# Constrói grafo leve de imports (arquivos -> módulos importados) para achar padrões e ciclos.
# Melhorias: detecção de ciclos, visualização graphviz, filtragem builtins, relatórios, CLI.import ast
import json
import sys
from pathlib import Path
from collections import defaultdict, deque
import argparse

# Builtins padrão para filtrar (opcional)
BUILTINS = {
    "sys", "os", "json", "pathlib", "typing", "logging", "threading", "asyncio",
    "datetime", "time", "math", "random", "collections", "functools", "itertools"
}

def parse_imports(code: str) -> set[str]:
    """Extrai imports do código usando AST."""
    try:
        tree = ast.parse(code)
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for n in node.names:
                    imports.add(n.name)
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                if node.level and mod == "":
                    imports.add(f"relative:{'.'*node.level}")
                else:
                    imports.add(mod)
        return imports
    except Exception:
        return set()

def build_graph(src_path: Path, filter_builtins: bool = True) -> dict[str, list[str]]:
    """Constrói grafo de arquivos -> módulos importados."""
    files = list(src_path.rglob("*.py"))
    graph = {}
    for p in files:
        try:
            code = p.read_text(encoding="utf-8", errors="ignore")
            imports = parse_imports(code)
            if filter_builtins:
                imports = {i for i in imports if i not in BUILTINS and not i.startswith("builtins")}
            graph[str(p)] = sorted(imports)
        except Exception as e:
            graph[str(p)] = [f"error: {str(e)}"]
    return graph

def detect_cycles(graph: dict[str, list[str]]) -> list[list[str]]:
    """Detecta ciclos no grafo usando DFS."""
    cycles = []
    visited = set()
    rec_stack = set()

    def dfs(node: str, path: list[str]):
        visited.add(node)
        rec_stack.add(node)
        path.append(node)

        for neighbor in graph.get(node, []):
            if neighbor not in graph:
                continue  # módulo externo, ignora
            if neighbor not in visited:
                if dfs(neighbor, path):
                    return True
            elif neighbor in rec_stack:
                # ciclo encontrado
                cycle_start = path.index(neighbor)
                cycles.append(path[cycle_start:] + [neighbor])
                return True

        path.pop()
        rec_stack.remove(node)
        return False

    for node in graph:
        if node not in visited:
            dfs(node, [])

    return cycles

def generate_report(graph: dict[str, list[str]]) -> dict[str, any]:
    """Gera relatório com estatísticas."""
    import_counts = defaultdict(int)
    file_counts = defaultdict(int)

    for file, imports in graph.items():
        file_counts[len(imports)] += 1
        for imp in imports:
            import_counts[imp] += 1

    top_imports = sorted(import_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    return {
        "total_files": len(graph),
        "imports_por_arquivo": dict(file_counts),
        "top_imports": top_imports,
        "total_imports_unicos": len(import_counts)
    }

def visualize_graph(graph: dict[str, list[str]], output_file: Path):
    """Gera visualização com graphviz (se instalado)."""
    try:
        from graphviz import Digraph  # type: ignore
        dot = Digraph(comment="Import Graph")
        for file, imports in graph.items():
            short_file = Path(file).relative_to(Path("src")).as_posix()
            dot.node(short_file)
            for imp in imports[:5]:  # limita para legibilidade
                dot.edge(short_file, imp)
        dot.render(output_file.with_suffix(""), format="png", cleanup=True)
        print(f"Visualização salva em {output_file.with_suffix('.png')}")
    except ImportError:
        print("graphviz não instalado; pule visualização.")
    except Exception as e:
        print(f"Erro na visualização: {e}")

def main():
    parser = argparse.ArgumentParser(description="Constrói grafo de imports.")
    parser.add_argument("--src", type=Path, default=Path("src"), help="Diretório src")
    parser.add_argument("--output", type=Path, default=None, help="Arquivo JSON de saída")
    parser.add_argument("--no-filter", action="store_true", help="Não filtrar builtins")
    parser.add_argument("--visualize", type=Path, default=None, help="Arquivo para visualização (requer graphviz)")
    parser.add_argument("--report", action="store_true", help="Incluir relatório")

    args = parser.parse_args()

    graph = build_graph(args.src, filter_builtins=not args.no_filter)
    output = {"graph": graph}

    cycles = detect_cycles(graph)
    if cycles:
        output["cycles"] = cycles
        print(f"Ciclos detectados: {len(cycles)}")

    if args.report:
        report = generate_report(graph)
        output["report"] = report
        print(f"Relatório: {report['total_files']} arquivos, {report['total_imports_unicos']} imports únicos")

    if args.visualize:
        visualize_graph(graph, args.visualize)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        print(f"Grafo salvo em {args.output}")
    else:
        print(json.dumps(output, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()



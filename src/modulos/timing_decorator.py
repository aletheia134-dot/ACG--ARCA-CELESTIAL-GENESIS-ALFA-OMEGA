#!/usr/bin/env python3
import time
from src.core.cerebro_familia import CerebroFamilia

class DummyLLM:
    def generate_response(self, request):
        time.sleep(0.15)  # simula 150ms
        return "<|assistant|>OK dummy"

def measure_with_engine(engine, n=50):
    c = CerebroFamilia(memoria=None, config={}, llm_engine=engine)
    times = []
    for _ in range(n):
        t0 = time.perf_counter()
        c.processar_intencao("EVA", "Ol, medio")
        times.append(time.perf_counter() - t0)
    times.sort()
    print("N", n, "min", times[0], "p50", times[n//2], "p90", times[int(n*0.9)], "max", times[-1], "avg", sum(times)/n)
    # paralelo
    t0 = time.perf_counter()
    c.executar_paralelo_6("Mensagem de grupo")
    print("executar_paralelo_6 total:", time.perf_counter() - t0)

if __name__ == '__main__':
    print("Medindo DummyLLM")
    measure_with_engine(DummyLLM(), n=50)
    # Para medir com engine real: instancie e passe a instncia real

"""A4, versão 3: ordem trocada no produtor, permitindo deadlock.

Autor: Leunam Sousa de Jesus. Parâmetros: N = 6 e 20.000 amostras.
vazio começa em N, cheio em zero e mutex em um. O produtor adquire
mutex antes de vazio; o consumidor adquire cheio antes de mutex.
O sleep(0) entre leitura e escrita do contador permanece dentro da
região protegida, para comparar a proteção com a versão 1.
A supervisão de 1 s é mantida. Aquisições bloqueantes com timeout curto
permitem observar o pedido de parada, sem corrigir o algoritmo em curso.

Execução, a partir da raiz: python3 ponderada/codigo/versao3.py
"""

import threading
import time


N = 6
TOTAL_AMOSTRAS = 20_000
LIMITE_SEM_CONSUMO = 1.0
ESPERA_SEMAFORO = 0.05


def criar_estado() -> dict:
    """Prepara o buffer, os semáforos e os dados de uma execução.

    Parâmetros: nenhum.
    Retorno: dicionário com buffer, semáforos, índices e dados de supervisão.
    """
    return {
        "vazio": threading.Semaphore(N),
        "cheio": threading.Semaphore(0),
        "mutex": threading.Semaphore(1),
        "buffer": [None] * N,
        "escrita": 0,
        "leitura": 0,
        "ocupadas": 0,
        "produzidas": 0,
        "recebidas": [],
        "invalidas": 0,
        "ultimo_consumo": time.monotonic(),
        "parar": False,
        "erros": [],
    }


def adquirir(semaforo: threading.Semaphore, estado: dict) -> bool:
    """Aguarda uma permissão sem impedir o encerramento supervisionado.

    Parâmetros:
        semaforo: semáforo cuja permissão deve ser adquirida.
        estado: dados compartilhados, incluindo o sinal parar.
    Retorno: True se adquiriu; False se a execução foi encerrada.
    Cada espera é bloqueante. O timeout só permite consultar o sinal de parada.
    """
    while not estado["parar"]:
        if semaforo.acquire(timeout=ESPERA_SEMAFORO):
            if estado["parar"]:
                semaforo.release()
                return False
            return True
    return False


def adquirir_par(
    primeiro: threading.Semaphore, segundo: threading.Semaphore, estado: dict,
) -> bool:
    """Adquire duas permissões na ordem recebida.

    Parâmetros:
        primeiro: primeiro semáforo a adquirir.
        segundo: segundo semáforo a adquirir, mantendo o primeiro.
        estado: dados compartilhados, incluindo o sinal de encerramento.
    Retorno: True com ambos adquiridos; False quando a supervisão encerra.
    A primeira permissão só é devolvida sem obter a segunda após a parada;
    não há recuperação que libere recursos e continue silenciosamente.
    """
    if not adquirir(primeiro, estado):
        return False
    if not adquirir(segundo, estado):
        primeiro.release()
        return False
    return True


def produtor(estado: dict) -> None:
    """Adquire mutex antes da vaga, podendo impedir o avanço do consumidor.

    Parâmetros: estado, dicionário com buffer, semáforos e supervisão.
    Retorno: None. Atualiza o buffer, índice e contador e sinaliza um item.
    """
    try:
        for amostra_id in range(TOTAL_AMOSTRAS):
            if not adquirir_par(estado["mutex"], estado["vazio"], estado):
                return

            try:
                estado["buffer"][estado["escrita"]] = amostra_id
                estado["escrita"] = (estado["escrita"] + 1) % N
                ocupacao_anterior = estado["ocupadas"]
                time.sleep(0)
                estado["ocupadas"] = ocupacao_anterior + 1
                estado["produzidas"] += 1
            finally:
                estado["mutex"].release()

            estado["cheio"].release()
    except Exception as erro:
        estado["erros"].append(f"Produtor: {type(erro).__name__}: {erro}")
        estado["parar"] = True


def consumidor(estado: dict) -> None:
    """Reserva um item e o retira na região protegida por mutex.

    Parâmetros: estado, dicionário com buffer, semáforos e supervisão.
    Retorno: None. Registra recebimentos, atualiza o estado e libera uma vaga.
    """
    try:
        for _ in range(TOTAL_AMOSTRAS):
            if not adquirir_par(estado["cheio"], estado["mutex"], estado):
                return

            try:
                amostra_id = estado["buffer"][estado["leitura"]]
                estado["leitura"] = (estado["leitura"] + 1) % N
                # A disponibilidade é controlada por cheio/vazio; o valor
                # anterior pode continuar fisicamente no slot após a retirada.
                ocupacao_anterior = estado["ocupadas"]
                time.sleep(0)
                estado["ocupadas"] = ocupacao_anterior - 1
            finally:
                estado["mutex"].release()

            estado["vazio"].release()
            if isinstance(amostra_id, int) and 0 <= amostra_id < TOTAL_AMOSTRAS:
                estado["recebidas"].append(amostra_id)
                estado["ultimo_consumo"] = time.monotonic()
            else:
                estado["invalidas"] += 1
    except Exception as erro:
        estado["erros"].append(f"Consumidor: {type(erro).__name__}: {erro}")
        estado["parar"] = True


def calcular_metricas(
    recebidas: list[int], produzidas: int, invalidas: int,
    total: int = TOTAL_AMOSTRAS,
) -> dict:
    """Conta recebimentos, duplicações e IDs esperados que não chegaram.

    Parâmetros:
        recebidas: sequência dos IDs válidos recebidos, com repetições.
        produzidas: quantidade de IDs emitidos, em ordem a partir de zero.
        invalidas: quantidade de retiradas sem um ID válido.
        total: quantidade esperada de amostras; padrão de 20.000.
    Retorno: dicionário com as métricas, distinguindo não geradas de perdas.
    """
    diferentes = set(recebidas)
    return {
        "produzidas": produzidas,
        "consumidas": len(recebidas),
        "diferentes": len(diferentes),
        "duplicadas": len(recebidas) - len(diferentes),
        "nao_entregues": total - len(diferentes),
        "produzidas_nao_recebidas": len(set(range(produzidas)) - diferentes),
        "nao_geradas": total - produzidas,
        "invalidas": invalidas,
    }


def executar_experimento() -> dict:
    """Executa as duas threads e supervisiona a ausência de consumo válido.

    Parâmetros: nenhum.
    Retorno: dicionário com métricas, duração e motivo do encerramento.
    O sinal parar serve somente ao encerramento, sem proteger a região crítica.
    """
    estado = criar_estado()
    threads = [
        threading.Thread(target=produtor, args=(estado,), name="sensor", daemon=True),
        threading.Thread(target=consumidor, args=(estado,), name="motor", daemon=True),
    ]
    travou = False
    interrompida = False
    inicio = time.monotonic()
    for thread in threads:
        thread.start()

    try:
        while any(thread.is_alive() for thread in threads):
            if estado["erros"]:
                break
            if time.monotonic() - estado["ultimo_consumo"] >= LIMITE_SEM_CONSUMO:
                travou = True
                break
            for thread in threads:
                thread.join(timeout=0.01)
    except KeyboardInterrupt:
        interrompida = True
    finally:
        estado["parar"] = True
        for thread in threads:
            thread.join(timeout=1.0)

    if any(thread.is_alive() for thread in threads):
        estado["erros"].append("Uma thread não confirmou encerramento; dados parciais.")

    resultado = calcular_metricas(
        list(estado["recebidas"]), estado["produzidas"], estado["invalidas"],
    )
    resultado.update({
        "travou": travou,
        "interrompida": interrompida,
        "duracao": time.monotonic() - inicio,
        "ocupadas_final": estado["ocupadas"],
        "erros": list(estado["erros"]),
    })
    return resultado


def main() -> int:
    """Executa uma rodada e imprime a configuração e os resultados reais.

    Parâmetros: nenhum.
    Retorno: 0 para rodada registrada, 1 para erro ou 130 para interrupção.
    Travamento observado é um resultado do experimento, não erro do relatório.
    """
    resultado = executar_experimento()
    print("VERSÃO 3 — ORDEM TROCADA")
    print(f"Configuração: N={N}; esperadas={TOTAL_AMOSTRAS}; IDs=0..{TOTAL_AMOSTRAS - 1}")
    print(f"Produzidas: {resultado['produzidas']}")
    print(f"Consumidas (IDs válidos, com repetições): {resultado['consumidas']}")
    print(f"IDs diferentes recebidos: {resultado['diferentes']}")
    print(f"Perdidas/não entregues do total esperado: {resultado['nao_entregues']}")
    print(f"Duplicadas: {resultado['duplicadas']}")
    print(f"Leituras inválidas: {resultado['invalidas']}")
    print(f"Produzidas e não recebidas: {resultado['produzidas_nao_recebidas']}")
    print(f"Ainda não geradas: {resultado['nao_geradas']}")
    print(f"Travou (1 s sem consumo válido): {'Sim' if resultado['travou'] else 'Não'}")
    print(f"Contador de ocupação final: {resultado['ocupadas_final']}")
    print(f"Duração: {resultado['duracao']:.3f} s")
    if resultado["interrompida"]:
        print("Execução interrompida pelo usuário.")
    for erro in resultado["erros"]:
        print(f"Erro: {erro}")
    return 130 if resultado["interrompida"] else int(bool(resultado["erros"]))


if __name__ == "__main__":
    raise SystemExit(main())

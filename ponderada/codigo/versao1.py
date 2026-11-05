"""A4, versão 1: produtor e consumidor sem sincronização do buffer.

Autor: Leunam Sousa de Jesus. Parâmetros: N = 6 e 20.000 amostras.
As threads usam espera ocupada e cedem a execução entre ler e escrever
o contador compartilhado, com time.sleep(0), conforme o enunciado.
O programa é intencionalmente incorreto: o relatório mede seus efeitos.
A supervisão pede encerramento após 1 s sem consumo válido; ela não
corrige o contador nem protege a região crítica.

Execução, a partir da raiz: python3 ponderada/codigo/versao1.py
"""

import threading
import time


N = 6
TOTAL_AMOSTRAS = 20_000
LIMITE_SEM_CONSUMO = 1.0


def criar_estado() -> dict:
    """Prepara o buffer e os dados compartilhados de uma execução.

    Parâmetros: nenhum.
    Retorno: dicionário com buffer, índices, contador e dados de supervisão.
    """
    return {
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


def produtor(estado: dict) -> None:
    """Insere IDs em ordem, sem proteger o buffer ou seu contador.

    Parâmetros: estado, dicionário compartilhado criado por criar_estado.
    Retorno: None. Atualiza o buffer, índice de escrita e contadores.
    """
    try:
        for amostra_id in range(TOTAL_AMOSTRAS):
            while estado["ocupadas"] >= N:
                if estado["parar"]:
                    return
                # Espera ocupada: continua verificando, sem bloqueio por vaga.

            if estado["parar"]:
                return

            estado["buffer"][estado["escrita"]] = amostra_id
            estado["escrita"] = (estado["escrita"] + 1) % N

            # A cópia local pode ficar antiga enquanto a outra thread avança.
            ocupacao_anterior = estado["ocupadas"]
            time.sleep(0)
            estado["ocupadas"] = ocupacao_anterior + 1
            estado["produzidas"] += 1
    except Exception as erro:
        estado["erros"].append(f"Produtor: {type(erro).__name__}: {erro}")
        estado["parar"] = True


def consumidor(estado: dict) -> None:
    """Faz até 20.000 retiradas, registrando IDs e leituras inválidas.

    Parâmetros: estado, dicionário compartilhado criado por criar_estado.
    Retorno: None. Atualiza o índice de leitura, contador e recebimentos.
    """
    try:
        for _ in range(TOTAL_AMOSTRAS):
            while estado["ocupadas"] <= 0:
                if estado["parar"]:
                    return
                # Espera ocupada: continua verificando, sem bloqueio por item.

            if estado["parar"]:
                return

            amostra_id = estado["buffer"][estado["leitura"]]
            estado["leitura"] = (estado["leitura"] + 1) % N
            # A retirada libera a posição logicamente. O valor antigo fica
            # na lista; a ocupação é que deveria controlar sua validade.
            ocupacao_anterior = estado["ocupadas"]
            time.sleep(0)
            estado["ocupadas"] = ocupacao_anterior - 1

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
    print("VERSÃO 1 — SEM SINCRONIZAÇÃO")
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

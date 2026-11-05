# Ponderada CC08: Tato

**Autor:** Leunam Sousa de Jesus

Aplicação de arquitetura de computadores, memória, pipeline, processos, threads, semáforos e deadlock à análise de uma pulseira sensorial para pessoas com deficiência visual.

## Tecnologia utilizada

Os experimentos da questão A4 usam Python 3.9 ou superior e o módulo `threading` da biblioteca padrão. Foram executados com Python 3.11.13.

## Organização

- `ponderada/ponderada-tato.md`: análise técnica e memorando com a decisão do CTO.
- `ponderada/codigo/`: código das três versões do experimento da A4.
- `ponderada/img/`: prints das caches do computador e das execuções dos programas.

## Instruções de execução

Execute a partir da raiz do repositório, com Python 3.9 ou superior e sem dependências externas.

### Versão 1: Sem sincronização

```bash
python3 ponderada/codigo/versao1.py
```

Cada comando executa uma rodada com buffer de seis posições e 20.000 amostras esperadas. O programa imprime a configuração, as métricas e se houve um segundo sem consumo válido. A espera ocupada pode tornar a execução demorada; os resultados variam conforme o escalonamento das threads.

A contagem de perdidas/não entregues considera os IDs esperados que não chegaram, incluindo IDs ainda não gerados em uma parada precoce. O relatório também distingue esses casos e mostra leituras inválidas.

### Versão 2: Com semáforos

```bash
python3 ponderada/codigo/versao2.py
```

Usa os semáforos `vazio=6`, `cheio=0` e `mutex=1`, com as mesmas amostras e métricas da versão 1. As esperas por permissões são bloqueantes. O `sleep(0)` permanece dentro da região protegida por mutex.

### Versão 3: Ordem de aquisição trocada

```bash
python3 ponderada/codigo/versao3.py
```

Preserva a versão 2, mas o produtor adquire `mutex` antes de `vazio`. Essa ordem pode causar deadlock quando o buffer enche. A supervisão encerra o teste após um segundo sem consumo e imprime os resultados, sem corrigir o algoritmo para continuar.

Para a coleta da A4, execute cada versão três vezes, uma rodada por vez, e salve os prints da configuração e dos resultados em `ponderada/img/`.

# Ponderada CC08 — Tato

**Autor:** Leunam Sousa de Jesus

Aplicação de arquitetura de computadores, memória, pipeline, processos, threads, semáforos e deadlock à análise de uma pulseira sensorial para pessoas com deficiência visual.

## Tecnologia utilizada

Os experimentos da questão A4 serão implementados em **Python 3**, utilizando o módulo `threading` da biblioteca padrão.

## Organização

- `ponderada/ponderada-tato.md`: análise técnica e memorando com a decisão do CTO.
- `ponderada/codigo/`: código das três versões do experimento da A4.
- `ponderada/img/`: prints das caches do computador e das execuções dos programas.

## Instruções de execução

**Pendente:** os comandos serão adicionados após a implementação e a verificação das três versões:

1. **Versão 1:** buffer circular sem sincronização, com contador compartilhado e espera ocupada.
2. **Versão 2:** buffer circular sincronizado com os semáforos `vazio`, `cheio` e `mutex`.
3. **Versão 3:** alteração na ordem de aquisição dos semáforos do produtor para investigar a possibilidade de deadlock.

Cada versão deverá executar com um único comando, que será documentado nesta seção.
# Guia do Operador — PineTrading Suite 0.2

**Produto:** Market Map v0.2 + Execution v0.2  
**Perfil recomendado:** PADRÃO  
**Uso:** apoio gráfico à decisão discricionária em criptomoedas

Este guia explica o que a Suite 0.2 mostra no TradingView e, principalmente, o que cada estado **significa e não significa**.

A suíte não envia ordens, não conhece sua posição real na corretora e não substitui sua decisão. Ela organiza contexto estrutural, oportunidade, timing e gestão de tese em dois indicadores:

1. **Market Map** — overlay no gráfico e painel principal.
2. **Execution** — painel inferior de timing, com uma linha-resumo compacta.

O Decision Panel faz parte do Market Map. Não existe um terceiro indicador obrigatório.

---

## 1. Como ler a suíte em poucos segundos

A ordem prática é:

1. **CENÁRIO** — em que ambiente o mercado está.
2. **OPORTUNIDADE** — que tipo de setup, se algum, está presente.
3. **LADO** — direção técnica relevante.
4. **AÇÃO** — maturidade do timing agora.
5. **ALVO** — destinos técnicos disponíveis.
6. **GESTÃO** — estado de uma tese já confirmada anteriormente.
7. **INVALIDA** — nível estrutural que quebra a tese.
8. **CORREÇÃO** — zona provável de reação quando ela é relevante.

A linha do Execution deve ser lida como confirmação compacta do mesmo estado operacional. Ela não precisa repetir todo o painel do Market Map, mas não pode contradizê-lo.

---

## 2. CENÁRIO

### ALTA

O regime/estrutura predominante é altista.

Não significa:
- compra imediata;
- fundo garantido;
- que toda correção deve ser comprada.

O timing continua dependendo de OPORTUNIDADE + AÇÃO.

### BAIXA

O regime/estrutura predominante é baixista.

Em spot, normalmente serve para:
- proteger posição;
- reduzir exposição;
- evitar compra prematura;
- esperar nova estrutura.

Em ambiente bidirecional, também pode contextualizar SHORT.

### TRANSIÇÃO ↑ / TRANSIÇÃO ↓

O mercado está mudando de estado estrutural, mas ainda não apresenta a mesma maturidade de um regime consolidado.

A seta mostra a direção da transição.

Transição não é sinônimo de reversão confirmada.

### MISTO / CONFLITO

Regime e estrutura relevante não estão plenamente alinhados.

Tratamento prático:
- evitar forçar interpretação;
- dar mais peso a AGUARDAR/OBSERVAR;
- não transformar um conflito estrutural em sinal por opinião.

### RANGE

Há um contexto de faixa lateral suficientemente coerente para o motor tratar rotação entre extremos.

RANGE não significa que o preço ficará preso na faixa indefinidamente.

### MACRO / CICLO

No 1M, a suíte atua como consciência macro/cíclica, não como motor de execução.

### MACRO ALTA / MACRO BAIXA / MACRO NEUTRO / MACRO —

Nos horizontes altos suportados, o Market Map pode acrescentar contexto mensal confirmado.

- **MACRO ALTA**: contexto mensal direcional positivo.
- **MACRO BAIXA**: contexto mensal direcional negativo.
- **MACRO NEUTRO**: contexto mensal disponível, sem direção forte.
- **MACRO —**: o contexto mensal requerido ainda não está disponível.

O macro mensal é contexto. Ele não bloqueia automaticamente uma oportunidade válida de 3D/1W.

---

## 3. OPORTUNIDADE

### NENHUMA

Não há uma classe de oportunidade ativa que o motor considere relevante agora.

Isso não quer dizer que:
- o ativo esteja “ruim”;
- não exista tendência;
- o preço não possa subir ou cair.

Significa somente que o motor não identificou um setup operacional ativo naquele momento.

### CORREÇÃO

O preço está em uma correção estrutural relevante dentro da tese atual.

É um contexto de localização, não uma compra automática.

### RETESTE / RECLAIM

O mercado está testando/reivindicando uma região estrutural já reconhecida.

É uma das famílias preservadas do comportamento aceito da Suite 0.1.

### BREAKOUT

Há uma oportunidade de expansão após rompimento estrutural que passou pelos critérios aceitos do Opportunity Engine.

BREAKOUT não é “qualquer candle acima da resistência”.

### REACELERAÇÃO

Uma tendência já estabelecida volta a ganhar impulso após desaceleração/compressão, sem exigir necessariamente um pullback clássico.

### REVERSÃO

A mudança de regime já atingiu o nível de coerência exigido pelo motor.

O primeiro sinal bruto de transição não é tratado como reversão operável.

### ROTAÇÃO DE RANGE

O preço rejeitou uma borda de faixa estrutural e o motor encontrou evidência suficiente para uma tentativa de rotação em direção ao outro lado.

Não é um convite a fazer mean reversion em qualquer lateralização.

---

## 4. LADO

### COMPRA / LONG

A direção técnica da tese/oportunidade é positiva.

No spot:
- procurar compra, manutenção ou adição **somente quando o timing justificar**.

Em ambiente bidirecional:
- também é contexto para LONG.

### VENDA / SHORT

A direção técnica da tese/oportunidade é negativa.

No spot:
- pode significar vender/reduzir/proteger;
- pode significar simplesmente não comprar ainda.

Em ambiente bidirecional:
- também pode ser usado como contexto para SHORT.

### —

Não existe direção operacional suficientemente definida.

---

## 5. AÇÃO

AÇÃO é o campo de timing mais importante para saber **quão madura está a ideia**.

### AGUARDAR

Não há readiness operacional ativa.

É o estado neutro.

### OBSERVAR

Existe contexto/oportunidade/localização relevante, mas ainda não há preparação operacional suficiente.

Diferença prática:
- AGUARDAR = nada operacional ativo.
- OBSERVAR = existe algo para acompanhar, mas ainda não para preparar entrada.

### PREPARANDO LONG / PREPARANDO SHORT

O setup começou a reunir condições de timing, mas ainda está incompleto.

Não é confirmação.

Serve para:
- aumentar atenção;
- preparar plano;
- revisar alvo/invalidação;
- evitar entrar atrasado caso evolua.

### ARMADO LONG / ARMADO SHORT

O setup atingiu um estágio mais avançado de prontidão.

Ainda não é o mesmo que CONFIRMA.

No PADRÃO, o motor continua esperando a confirmação definida para aquela oportunidade.

### CONFIRMA LONG / CONFIRMA SHORT

O estado PADRÃO confirmou a oportunidade no fechamento da barra.

É o evento mais forte de entrada/timing da suíte.

Mesmo assim, não significa:
- garantia de lucro;
- ordem automática;
- tamanho de posição;
- obrigação de operar.

A confirmação é uma condição técnica de mercado. A decisão continua humana.

### ALINHADO LONG / ALINHADO SHORT

A confirmação já ocorreu e o estado continua coerente na direção da tese.

ALINHADO não é uma nova entrada por si só.

### CONFLITO

Dois caminhos internos ativos apontam direções opostas.

Regra da suíte:
- conflito não gera CONFIRMA unificado.

### ANTECIPADO • ARMADO ...

Quando o perfil ANTECIPADO está ativo e o setup pertence ao escopo validado, a suíte pode expor uma postura antecipada.

Isso é **postura antecipada**, não uma CONFIRMA PADRÃO falsificada.

---

## 6. Perfil PADRÃO

PADRÃO é a configuração global recomendada.

Ele:
- usa a prontidão confirmada aceita pelo projeto;
- funciona em todos os horizontes suportados;
- é a referência principal de gestão;
- é o único perfil que inicia Thesis Management após CONFIRMA.

Para uso normal, comece por PADRÃO.

---

## 7. Perfil ANTECIPADO

ANTECIPADO não deixa “tudo mais agressivo”.

Ele só atua quando **todas** as condições de escopo são atendidas:

- timeframe: 15m, 1H, 4H, 1D ou 3D;
- caminho: TREND_OPPORTUNITY_V2;
- oportunidade: BREAKOUT ou REACELERAÇÃO;
- readiness entrando em ARMADO;
- sem conflito.

Continuam com comportamento PADRÃO mesmo que ANTECIPADO esteja selecionado:

- CORREÇÃO;
- RETESTE / RECLAIM;
- ROTAÇÃO DE RANGE;
- REVERSÃO;
- 1W;
- 1M.

ANTECIPADO:
- não cria CONFIRMA PADRÃO;
- não inicia GESTÃO;
- não reescreve histórico;
- não significa usar mais risco ou alavancagem.

Se o gráfico atual não tiver um setup TREND elegível, PADRÃO e ANTECIPADO podem parecer exatamente iguais. Isso é esperado.

---

## 8. GESTÃO

GESTÃO descreve o estado de uma **tese de mercado iniciada por uma CONFIRMA PADRÃO anterior**.

A suíte não sabe se você realmente entrou na operação.

Por isso, leia GESTÃO como qualidade/condição da tese, não como ordem sobre sua carteira.

### CONTINUIDADE

A tese confirmada continua tecnicamente válida sem alerta de proteção mais forte.

### PROTEGER

Há deterioração ou proximidade de invalidação suficiente para elevar a necessidade de proteção.

Exemplos de interpretação:
- spot comprado: revisar risco, stop discricionário, parcial ou exposição;
- sem posição: evitar perseguir movimento;
- SHORT: interpretação espelhada.

### REALIZAÇÃO

A tese amadureceu a ponto de surgir risco de realização/reação.

Pode ocorrer por:
- proximidade do alvo;
- progresso relevante da trajetória;
- perda de força/exaustão.

Não significa “feche tudo agora”.

Em horizontes altos, REALIZAÇÃO pode representar maturidade/proteção de lucro e não um topo/fundo iminente.

### CONCLUÍDA

O alvo congelado da tese foi atingido.

### INVALIDADA

O fechamento confirmou quebra da invalidação estrutural congelada.

### AMBÍGUA

Alvo e invalidação foram tocados dentro da mesma barra de forma que OHLC não permite provar a ordem intrabar.

A suíte não inventa qual aconteceu primeiro.

### —

Não há uma tese de gestão ativa.

Importante: é perfeitamente possível ver **AÇÃO = AGUARDAR** com **GESTÃO = CONTINUIDADE**. Isso significa:

- não há nova entrada sendo preparada agora;
- uma tese confirmada anteriormente ainda está viva.

---

## 9. ALVO

ALVO mostra destinos técnicos disponíveis para a tese/contexto.

Podem aparecer referências como:
- SWING;
- PDH/PWH;
- níveis estruturais relevantes;
- borda oposta de RANGE.

O alvo é uma referência técnica, não uma promessa de preço.

Quando a Gestão inicia, o motor congela apenas os anchors honestamente disponíveis naquele momento.

Se um alvo estrutural válido não existir, ele fica ausente. A suíte não fabrica um.

---

## 10. INVALIDA

INVALIDA mostra o nível estrutural cuja quebra confirmada elimina a tese.

Não confunda INVALIDA com:
- stop obrigatório da corretora;
- stop de tamanho de posição;
- perda máxima aceitável da conta.

É uma invalidação **técnica da tese**.

A gestão só usa um anchor de invalidação quando ele é estruturalmente válido e está do lado correto em relação ao preço de confirmação.

---

## 11. CORREÇÃO

CORREÇÃO aparece apenas quando a zona é relevante.

Formato típico:

`84.500 – 83.900 ★★★`

A faixa é a zona primária de reação.

As estrelas representam confluência/evidência estrutural agregada.

Elas **não são probabilidade de acerto**.

Mais estrelas significam mais confluências reconhecidas pelo motor, não “90% de chance”.

---

## 12. Execution — como ler o painel inferior

O Execution mantém o histograma de momentum/timing e uma linha-resumo no canto.

A linha pode mostrar, por exemplo:

- `AGUARDAR`
- `PREPARANDO LONG`
- `ARMADO SHORT`
- `CONFIRMA LONG • BREAKOUT`
- `AGUARDAR • CONTINUIDADE`
- `PREPARANDO LONG • MACRO NEUTRO`

Ela é propositalmente compacta.

Regra de paridade:
- a semântica precisa concordar com o Market Map;
- o texto não precisa ter o mesmo layout.

---

## 13. Horizontes de uso

### 15m / 1H

Uso principal:
- trades mais curtos;
- precisão de entrada;
- leitura tática.

Suportam:
- PADRÃO;
- ANTECIPADO para BREAKOUT/REACELERAÇÃO;
- Thesis Management.

### 4H / 1D

Horizontes swing principais da suíte.

São a referência preferencial para a maior parte das decisões de swing.

Suportam:
- PADRÃO;
- ANTECIPADO no escopo TREND;
- gestão completa.

### 3D

Horizonte ativo de médio/longo prazo.

Usa contexto mensal confirmado quando disponível.

Suporta:
- PADRÃO;
- ANTECIPADO no escopo TREND;
- gestão.

### 1W

Horizonte alto válido, mas com eventos naturalmente mais raros.

Política:
- PADRÃO somente;
- gestão aceita, porém esparsa;
- não afrouxar critérios para “fabricar” sinais.

Mesmo que o seletor esteja em ANTECIPADO, o 1W mantém comportamento PADRÃO.

### 1M

Uso:
- macro/ciclo.

Não é um horizonte de execução standalone da Suite 0.2.

Não inicia Thesis Management.

---

## 14. Spot versus LONG/SHORT

A análise é direcional e independente da corretora.

### Em spot

Direção positiva:
- contexto para comprar/manter/adicionar conforme o timing.

Direção negativa:
- contexto para proteger/reduzir/vender;
- evitar nova compra;
- esperar melhor estrutura.

Você não precisa shortar só porque o painel mostra VENDA / SHORT.

### Em ambiente bidirecional

A mesma direção negativa pode ser usada para avaliar SHORT.

A suíte não possui um “motor especial de short”. A tese técnica é a mesma; muda a forma como o operador executa no veículo escolhido.

---

## 15. O que significam 0, ∅, — e eventos ausentes

Na interface normal, a suíte prioriza texto. Na Janela de Dados/diagnósticos aparecem códigos numéricos.

### 0

O significado depende do campo.

Casos comuns:
- direção 0 = sem direção;
- evento 0 = evento não ocorreu nesta barra;
- estado/código 0 = estado neutro/base daquela enumeração.

Não interprete todo zero como “erro” ou “sinal ruim”.

### ∅ / NA / vazio

Significa que aquele dado não está disponível/aplicável.

Exemplos:
- nenhum alvo estrutural honesto;
- nenhuma invalidação utilizável;
- macro mensal ainda indisponível;
- caminho de oportunidade não ativo.

Ausência é propositalmente diferente de um valor sintético.

### —

No painel normal significa “não há valor relevante para mostrar agora”.

### Evento ausente

Um campo de evento é normalmente pulsado apenas na barra em que a transição acontece.

Por exemplo:
- CONFIRMA event = 1 somente na barra de confirmação;
- nas barras seguintes, o estado pode continuar ALINHADO, enquanto o evento volta a 0.

Não confunda “evento 0” com “estado perdido”.

---

## 16. Exemplos práticos

### Exemplo A — tendência, mas sem entrada

```text
CENÁRIO      ALTA
OPORTUNIDADE NENHUMA
LADO         —
AÇÃO         AGUARDAR
GESTÃO       —
```

Leitura:
- mercado estruturalmente forte;
- nenhum setup operacional ativo;
- não comprar apenas porque o cenário é ALTA.

### Exemplo B — preparação de compra

```text
CENÁRIO      ALTA
LADO         COMPRA / LONG
AÇÃO         PREPARANDO LONG
```

Leitura:
- direção definida;
- timing ainda incompleto;
- preparar plano, não tratar como CONFIRMA.

### Exemplo C — setup armado

```text
OPORTUNIDADE RETESTE / RECLAIM
LADO         COMPRA / LONG
AÇÃO         ARMADO LONG
```

Leitura:
- o setup está avançado;
- ainda não equivale automaticamente a confirmação PADRÃO.

### Exemplo D — nenhuma nova entrada, mas tese antiga viva

```text
AÇÃO         AGUARDAR
GESTÃO       CONTINUIDADE
```

Leitura:
- não existe nova readiness operacional;
- uma tese confirmada anteriormente continua válida.

### Exemplo E — conflito

```text
CENÁRIO      MISTO / CONFLITO
OPORTUNIDADE NENHUMA
AÇÃO         AGUARDAR
```

Leitura:
- motores estruturais não estão alinhados;
- não resolver o conflito “na opinião”.

### Exemplo F — ANTECIPADO sem oportunidade elegível

```text
PERFIL       ANTECIPADO
OPORTUNIDADE NENHUMA
AÇÃO         AGUARDAR
```

Leitura:
- comportamento correto;
- ANTECIPADO não força um sinal onde o escopo não permite.

---

## 17. O que a suíte não sabe

A Suite 0.2 não sabe:

- seu preço médio;
- se você está comprado ou vendido;
- tamanho da posição;
- alavancagem;
- saldo da conta;
- tolerância pessoal a risco;
- notícias ainda não refletidas no gráfico;
- intenção de curto versus longo prazo fora do timeframe escolhido.

Por isso:
- GESTÃO descreve a tese;
- LADO descreve direção;
- AÇÃO descreve timing;
- **a decisão e o risco continuam com o operador**.

---

## 18. Rotina recomendada

Fluxo simples:

1. escolha o timeframe compatível com o horizonte da operação;
2. mantenha PADRÃO salvo como referência principal;
3. leia CENÁRIO → OPORTUNIDADE → LADO → AÇÃO;
4. confirme ALVO e INVALIDA antes de agir;
5. se houver CORREÇÃO, use a zona como localização, não como ordem automática;
6. após uma CONFIRMA PADRÃO, acompanhe GESTÃO;
7. use ANTECIPADO apenas quando você deseja explicitamente a postura TREND mais cedo que foi validada;
8. nunca aumente risco apenas porque o perfil é ANTECIPADO.

---

## 19. Regra final

A suíte foi construída para reduzir o trabalho de interpretar vários indicadores separados.

Ela deve responder:

> **Qual é o cenário, existe oportunidade, para que lado, quão madura está, onde está o alvo, onde invalida e como a tese está evoluindo?**

Ela não deve responder:

> **“Compre/venda obrigatoriamente agora.”**

A decisão final permanece discricionária.

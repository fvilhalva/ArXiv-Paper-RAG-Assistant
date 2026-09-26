# Cronograma — ArXiv Paper RAG Assistant

Roteiro de estudo + desenvolvimento, fase a fase. Cada fase tem: o que estudar antes/durante, e as tasks concretas de implementação — com dicas (docs, ferramentas, mini-exemplos) pra cada task. Os exemplos aqui são ilustrativos, pra você entender a API/conceito, não implementação pronta.

Ver [DESIGN.md](DESIGN.md) para os requisitos (FR/NFR) e arquitetura completa.

---

## Fase 0 — Fundamentos

**Estudar:**
- *Attention Is All You Need* (Vaswani et al., 2017) — self-attention, encoder vs decoder.
  - 💡 O paper original é denso; o post [The Illustrated Transformer](https://jalammar.github.io/illustrated-transformer/) (Jay Alammar) é a referência clássica pra entender visualmente antes de encarar o paper.
- *BERT* (Devlin et al., 2018) — encoder-only, representações contextuais (base de qualquer modelo de embedding).
  - 💡 [The Illustrated BERT](https://jalammar.github.io/illustrated-bert/), do mesmo autor, complementa bem.

**Tasks:** nenhuma de código. Objetivo é ter intuição sobre por que embeddings de texto funcionam antes de tratá-los como caixa-preta.

---

## Fase 1 — Ingestão (FR01–FR03)

**Estudar:**
- Extração de texto "flat" vs "layout-aware" em PDFs acadêmicos (colunas duplas, headers/footers, referências).
- Estratégias de chunking: fixed-size vs recursive vs semantic, e por que overlap importa.
  - 💡 [Pinecone — Chunking Strategies for LLM Applications](https://www.pinecone.io/learn/chunking-strategies/) é um bom resumo prático, mesmo sem usar Pinecone.
- Design de metadata schema (o que sustenta a citação lá na frente).

**Tasks:**
- [ ] Normalizar input do usuário (ID puro, URL `/abs/`, URL `/pdf/`) para um `arxiv_id` canônico.
  - 💡 Formato oficial dos IDs: [arxiv.org/help/arxiv_identifier](https://arxiv.org/help/arxiv_identifier). IDs novos são `YYMM.NNNNN` (ex: `2005.11401`); IDs antigos (pré-2007) são tipo `hep-th/9901001` — vale decidir se você suporta os antigos ou não.
  - 💡 Regex simples cobre os dois formatos de URL: `arxiv\.org/(abs|pdf)/([\w.\-/]+?)(v\d+)?(\.pdf)?$`.

- [ ] Buscar metadata do paper (título, autores) via pacote `arxiv`.
  - 💡 Lib: [`arxiv` no PyPI](https://pypi.org/project/arxiv/) (repo: [lukasschwab/arxiv.py](https://github.com/lukasschwab/arxiv.py)).
  - 💡 Exemplo de uso da API (não é a implementação, só o formato da chamada):
    ```python
    import arxiv
    search = arxiv.Search(id_list=["2005.11401"])
    paper = next(search.results())
    paper.title, paper.authors, paper.summary
    ```

- [ ] Baixar o PDF do paper.
  - 💡 O mesmo objeto `paper` de cima tem `paper.download_pdf(dirpath=..., filename=...)`.

- [ ] Escolher e validar abordagem de extração de texto (PyMuPDF + heurística própria, ou `unstructured`).
  - 💡 [PyMuPDF docs](https://pymupdf.readthedocs.io/) — `page.get_text("dict")` retorna blocos com posição e tamanho de fonte, útil pra heurística de heading.
  - 💡 [`unstructured` docs](https://docs.unstructured.io/) — `partition_pdf()` já tenta classificar título/parágrafo/lista automaticamente.
  - 💡 Ferramenta alternativa, mais pesada mas muito usada em research: [GROBID](https://github.com/kermitt2/grobid) — parser especializado em PDFs científicos, converte pra TEI-XML com seções já estruturadas. Vale conhecer mesmo que não use no MVP.

- [ ] Implementar detecção de seções (heading → nome/número da seção).
  - 💡 Heurística comum com PyMuPDF: heading = linha cujo `span["size"]` é maior que o tamanho médio do corpo do texto **e** que casa com regex tipo `^\d+(\.\d+)*\.?\s+[A-Z]`.
  - 💡 Trate a falha como esperada: nem todo PDF vai extrair seção corretamente — decida um fallback (ex: `seção: "desconhecida"`) em vez de quebrar a ingestão inteira.

- [ ] Implementar chunking dentro de cada seção (tamanho + overlap definidos).
  - 💡 Não precisa de lib: um sliding window por número de tokens/caracteres com overlap já resolve. Se quiser referência de implementação, o [`RecursiveCharacterTextSplitter` do LangChain](https://python.langchain.com/docs/how_to/recursive_text_splitter/) documenta bem a lógica (dá pra reimplementar sem depender do LangChain).
  - 💡 Contagem de tokens compatível com o seu modelo de embedding: [`tiktoken`](https://github.com/openai/tiktoken) é o padrão de mercado pra contar tokens rápido, mesmo não sendo o tokenizer exato do seu modelo local.

- [ ] Definir e implementar o schema de metadata `{paper_id, título, seção}` por chunk.
  - 💡 Um `dataclass`/`TypedDict` simples já resolve; é o payload que vai direto pro Qdrant depois.

- [ ] Escrever testes unitários de parsing/chunking com fixture PDF (sem chamar arXiv real) — ver NFR03.
  - 💡 Salve 1-2 PDFs pequenos em `tests/fixtures/`. Use `pytest` puro; para funções que recebem `Path`, o fixture `tmp_path` do pytest evita sujar o disco real. [Docs do pytest sobre fixtures](https://docs.pytest.org/en/stable/how-to/fixtures.html).

---

## Fase 2 — Embeddings & Retrieval (FR04, parte de FR05)

**Estudar:**
- *Sentence-BERT / SBERT* (Reimers & Gurevych, 2019) — por que bi-encoders (um vetor por texto + cosine similarity) são o padrão pra busca vetorial, em vez de cross-encoder.
- Cosine similarity vs dot product vs distância euclidiana, e por que a métrica importa no Qdrant.
  - 💡 [Qdrant docs — Search](https://qdrant.tech/documentation/concepts/search/) explica as métricas suportadas.
- Doc do Qdrant sobre metadata filtering (filtrar por `paper_id` antes/depois da busca vetorial).
  - 💡 [Qdrant docs — Filtering](https://qdrant.tech/documentation/concepts/filtering/).

**Tasks:**
- [ ] Subir Qdrant local (via `docker-compose.yml` já criado) e criar a collection com o schema de payload definido na Fase 1.
  - 💡 [Qdrant Quickstart](https://qdrant.tech/documentation/quickstart/). Exemplo de criação de collection:
    ```python
    from qdrant_client import QdrantClient
    from qdrant_client.models import VectorParams, Distance

    client = QdrantClient(host="localhost", port=6333)
    client.create_collection(
        collection_name="papers",
        vectors_config=VectorParams(size=768, distance=Distance.COSINE),
    )
    ```
    (768 é a dimensão do `nomic-embed-text`; confira a dimensão real do modelo que você escolher.)
  - 💡 Dashboard visual do Qdrant pra inspecionar dados: `http://localhost:6333/dashboard`.

- [ ] Gerar embeddings dos chunks via Ollama (`nomic-embed-text`) e gravar no Qdrant.
  - 💡 [Ollama API docs — embeddings](https://github.com/ollama/ollama/blob/main/docs/api.md#generate-embeddings). Com a lib `ollama` (Python):
    ```python
    import ollama
    resp = ollama.embeddings(model="nomic-embed-text", prompt=chunk_text)
    vector = resp["embedding"]
    ```
  - 💡 Lembre de puxar o modelo antes de usar: `ollama pull nomic-embed-text`.

- [ ] Implementar geração de embedding da pergunta do usuário.
  - 💡 Mesma função do item anterior — reaproveite, não duplique a chamada ao Ollama.

- [ ] Implementar busca vetorial com filtro opcional por `paper_id`.
  - 💡 Exemplo de busca com filtro no `qdrant-client`:
    ```python
    from qdrant_client.models import Filter, FieldCondition, MatchValue

    client.search(
        collection_name="papers",
        query_vector=question_vector,
        query_filter=Filter(must=[FieldCondition(key="paper_id", match=MatchValue(value=paper_id))]),
        limit=5,
    )
    ```

- [ ] Validar manualmente: pergunta simples sobre um paper indexado retorna os chunks certos.
  - 💡 Use o dashboard do Qdrant ou um script simples de linha de comando antes de conectar isso ao agente — mais fácil de depurar isolado.

---

## Fase 3 — RAG e citação (FR05, FR08)

**Estudar:**
- *Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks* (Lewis et al., 2020) — separação entre memória paramétrica (LLM) e não-paramétrica (índice vetorial); base conceitual do FR08.
- Prompt design para "grounding": forçar citação da seção de origem e forçar "não sei" quando os chunks não sustentam a resposta.
- NFR05 — por que conteúdo recuperado nunca deve ser tratado como instrução (isolamento contexto/instrução no prompt).
  - 💡 [OWASP — LLM01: Prompt Injection](https://genai.owasp.org/llmrisk/llm01-prompt-injection/) dá o vocabulário de segurança pra esse problema.

**Tasks:**
- [ ] Montar o template de prompt: system instructions + chunks recuperados (com metadata) + pergunta do usuário, isolando claramente "contexto" de "instrução".
  - 💡 Padrão comum: delimitar o conteúdo recuperado com tags claras, tipo:
    ```
    <retrieved_context>
    [paper: Attention Is All You Need, seção: 3.2]
    "..."
    </retrieved_context>

    <user_question>
    {pergunta}
    </user_question>
    ```
    E instruir explicitamente no system prompt que tudo dentro de `<retrieved_context>` é dado, nunca instrução.

- [ ] Implementar geração de resposta via Ollama (LLM) a partir do prompt montado.
  - 💡 [Ollama API docs — chat](https://github.com/ollama/ollama/blob/main/docs/api.md#generate-a-chat-completion):
    ```python
    ollama.chat(model="deepseek-r1:8b", messages=[{"role": "user", "content": prompt}])
    ```

- [ ] Implementar formatação de citação `[paper: título curto, seção: X.Y]` a partir da metadata dos chunks usados.
  - 💡 Isso é string formatting puro a partir do payload que já vem do Qdrant — não precisa do LLM pra gerar a citação em si, só pra decidir *quais* chunks usou.

- [ ] Implementar o caso "sem resposta suportada" (FR08): quando os chunks recuperados não são relevantes o suficiente, responder isso explicitamente em vez de alucinar.
  - 💡 Heurística simples: o `score` que o Qdrant devolve em cada resultado de busca — se o melhor score ficar abaixo de um threshold, trate como "sem contexto suficiente" antes mesmo de chamar o LLM. Não é perfeito, mas é um primeiro filtro barato.

- [ ] Testar manualmente com pergunta fora do escopo dos papers indexados.

---

## Fase 4 — Orquestração com LangGraph (FR06, FR07)

**Estudar:**
- Documentação oficial do LangGraph: `State`, nós, edges condicionais.
  - 💡 [LangGraph — Low Level Concepts](https://langchain-ai.github.io/langgraph/concepts/low_level/) é o ponto de entrada certo (conceito de `StateGraph`, `add_node`, `add_conditional_edges`).
- *ReAct: Synergizing Reasoning and Acting in Language Models* (Yao et al., 2022) — como um agente decide "agir" (buscar/ingerir) vs "responder direto".

**Tasks:**
- [ ] Desenhar o `State` do grafo (o que precisa transitar entre nós: pergunta, intenção classificada, paper_id se houver, chunks recuperados, resposta).
  - 💡 Normalmente um `TypedDict`:
    ```python
    class AgentState(TypedDict):
        question: str
        intent: str
        paper_id: str | None
        retrieved_chunks: list[dict]
        answer: str | None
    ```

- [ ] Implementar nó de classificação de intenção (ingerir novo paper / responder pergunta / pedir esclarecimento).
  - 💡 Pode ser uma chamada ao LLM pedindo saída estruturada (ex: JSON com `{"intent": "ingest" | "answer" | "clarify"}`). Se o modelo local não for confiável com JSON solto, considere o suporte a *structured outputs*/*function calling* do Ollama, ou regras simples primeiro (ex: mensagem contém um ID/URL do arXiv → `ingest`) e só cai pro LLM em caso ambíguo.

- [ ] Ligar o nó de classificação → Ingestion Pipeline (Fase 1) via edge condicional.
  - 💡 `graph.add_conditional_edges("classify", route_fn, {"ingest": "ingestion_node", "answer": "retrieval_node", "clarify": "clarify_node"})`.

- [ ] Ligar o nó de classificação → Retrieval + Generation (Fases 2–3) via edge condicional.

- [ ] Implementar o caminho de "pergunta ambígua" → pedir esclarecimento ao usuário.
  - 💡 Esse nó pode simplesmente terminar o grafo (`END`) devolvendo uma pergunta de volta, sem chamar retrieval nem LLM de geração.

- [ ] Implementar `/papers` (FR07): listar papers já indexados (query direta no Qdrant, sem passar pelo LLM).
  - 💡 `client.scroll(collection_name="papers", limit=1000)` e depois deduplicar por `paper_id` no payload — não precisa de embedding pra isso.

- [ ] Logar cada decisão do grafo (nó executado, chunks recuperados) — ver NFR06.
  - 💡 `logging` padrão do Python já resolve pro MVP. Se quiser visualização de execução do grafo (não obrigatório), o LangGraph se integra com [LangSmith](https://docs.smith.langchain.com/) pra tracing — é opcional e tem camada gratuita limitada.

---

## Fase 5 — Bot Discord (FR04, FR07)

**Estudar:**
- Modelo de eventos/comandos do `discord.py`, especialmente slash commands (pra `/papers`).
  - 💡 [discord.py docs](https://discordpy.readthedocs.io/) e o guia oficial de [app commands (slash commands)](https://discordpy.readthedocs.io/en/stable/interactions/api.html).

**Tasks:**
- [ ] Configurar bot no Discord Developer Portal e token em `.env` (NFR04 — nunca commitado; criar `.env.example`).
  - 💡 [discord.com/developers/applications](https://discord.com/developers/applications). Não esquecer de habilitar o "Message Content Intent" nas configurações do bot, senão `on_message` não recebe o texto.

- [ ] Implementar handler de mensagem: recebe pergunta em linguagem natural → chama o grafo LangGraph → posta resposta.
  - 💡 Esqueleto de referência (só a forma, não a implementação):
    ```python
    @bot.event
    async def on_message(message):
        if message.author.bot:
            return
        result = graph.invoke({"question": message.content})
        await message.channel.send(result["answer"])
    ```

- [ ] Implementar slash command `/papers` → chama listagem (Fase 4) → posta lista formatada.
  - 💡 `@bot.tree.command(name="papers", description="Lista papers indexados")`.

- [ ] Testar end-to-end: ingestão de 1 paper + pergunta com citação, tudo via Discord.

- [ ] **Esse é o gate do MVP** — antes de ir pra Extensão 3 (WhatsApp), validar que tudo funciona bem aqui.

---

## Extensão 1 — Síntese multi-paper

**Estudar:**
- *GraphRAG* (Microsoft, 2024) — indexação baseada em grafo para sintetizar respostas que cruzam múltiplos documentos.
  - 💡 Repo oficial (open source): [microsoft/graphrag](https://github.com/microsoft/graphrag) — vale rodar o exemplo deles antes de tentar portar a ideia pro seu projeto.

**Tasks:**
- [ ] Definir quando o agente decide que uma pergunta exige mais de um paper (novo caminho no grafo LangGraph).
- [ ] Avaliar se retrieval simples (buscar em múltiplos `paper_id` e combinar chunks) resolve, ou se vale importar ideias do GraphRAG (comunidades/sumarização entre documentos).

---

## Extensão 2 — Memória de conversa

**Tasks:**
- [ ] Adicionar estado de conversa (por sessão/canal) ao `State` do LangGraph.
  - 💡 LangGraph tem suporte nativo a isso via *checkpointers* (ex: `MemorySaver` em memória, ou um checkpointer com SQLite/Postgres pra persistir entre restarts). Ver [LangGraph — Persistence](https://langchain-ai.github.io/langgraph/concepts/persistence/).
- [ ] Permitir perguntas de acompanhamento sem repetir contexto (ex: "e na seção seguinte?").

---

## Extensão 3 — Integração com WhatsApp

**Tasks:**
- [ ] Só começar depois do MVP (Fase 5) testado e estável no Discord.
- [ ] Validar que só a camada `bot/` precisa de código novo (interface trocável, agente/retrieval/ingestão não devem assumir conceitos específicos do Discord — NFR07).
- [ ] Escolher a via de integração:
  - 💡 [WhatsApp Cloud API](https://developers.facebook.com/docs/whatsapp/cloud-api) (oficial, da Meta) — mais robusta e com suporte, mas exige conta Business verificada.
  - 💡 Bibliotecas não-oficiais (ex: baseadas em WhatsApp Web) são mais simples de configurar pra uso pessoal, mas violam os termos de serviço do WhatsApp e podem banir o número — vale essa ressalva antes de escolher.

# Cronograma — ArXiv Paper RAG Assistant

Roteiro de estudo + desenvolvimento, fase a fase. Cada fase tem: o que estudar antes/durante, e as tasks concretas de implementação. Ordem sugerida, mas as fases 1 e 2 podem ser estudadas em paralelo com a leitura de papers.

Ver [DESIGN.md](DESIGN.md) para os requisitos (FR/NFR) e arquitetura completa.

---

## Fase 0 — Fundamentos

**Estudar:**
- *Attention Is All You Need* (Vaswani et al., 2017) — self-attention, encoder vs decoder.
- *BERT* (Devlin et al., 2018) — encoder-only, representações contextuais (base de qualquer modelo de embedding).

**Tasks:** nenhuma de código. Objetivo é ter intuição sobre por que embeddings de texto funcionam antes de tratá-los como caixa-preta.

---

## Fase 1 — Ingestão (FR01–FR03)

**Estudar:**
- Extração de texto "flat" vs "layout-aware" em PDFs acadêmicos (colunas duplas, headers/footers, referências).
- Estratégias de chunking: fixed-size vs recursive vs semantic, e por que overlap importa.
- Design de metadata schema (o que sustenta a citação lá na frente).

**Tasks:**
- [ ] Normalizar input do usuário (ID puro, URL `/abs/`, URL `/pdf/`) para um `arxiv_id` canônico.
- [ ] Buscar metadata do paper (título, autores) via pacote `arxiv`.
- [ ] Baixar o PDF do paper.
- [ ] Escolher e validar abordagem de extração de texto (PyMuPDF + heurística própria, ou `unstructured`).
- [ ] Implementar detecção de seções (heading → nome/número da seção).
- [ ] Implementar chunking dentro de cada seção (tamanho + overlap definidos).
- [ ] Definir e implementar o schema de metadata `{paper_id, título, seção}` por chunk.
- [ ] Escrever testes unitários de parsing/chunking com fixture PDF (sem chamar arXiv real) — ver NFR03.

---

## Fase 2 — Embeddings & Retrieval (FR04, parte de FR05)

**Estudar:**
- *Sentence-BERT / SBERT* (Reimers & Gurevych, 2019) — por que bi-encoders (um vetor por texto + cosine similarity) são o padrão pra busca vetorial, em vez de cross-encoder.
- Cosine similarity vs dot product vs distância euclidiana, e por que a métrica importa no Qdrant.
- Doc do Qdrant sobre metadata filtering (filtrar por `paper_id` antes/depois da busca vetorial).

**Tasks:**
- [ ] Subir Qdrant local (via `docker-compose.yml` já criado) e criar a collection com o schema de payload definido na Fase 1.
- [ ] Gerar embeddings dos chunks via Ollama (`nomic-embed-text`) e gravar no Qdrant.
- [ ] Implementar geração de embedding da pergunta do usuário.
- [ ] Implementar busca vetorial com filtro opcional por `paper_id`.
- [ ] Validar manualmente: pergunta simples sobre um paper indexado retorna os chunks certos.

---

## Fase 3 — RAG e citação (FR05, FR08)

**Estudar:**
- *Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks* (Lewis et al., 2020) — separação entre memória paramétrica (LLM) e não-paramétrica (índice vetorial); base conceitual do FR08.
- Prompt design para "grounding": forçar citação da seção de origem e forçar "não sei" quando os chunks não sustentam a resposta.
- NFR05 — por que conteúdo recuperado nunca deve ser tratado como instrução (isolamento contexto/instrução no prompt).

**Tasks:**
- [ ] Montar o template de prompt: system instructions + chunks recuperados (com metadata) + pergunta do usuário, isolando claramente "contexto" de "instrução".
- [ ] Implementar geração de resposta via Ollama (LLM) a partir do prompt montado.
- [ ] Implementar formatação de citação `[paper: título curto, seção: X.Y]` a partir da metadata dos chunks usados.
- [ ] Implementar o caso "sem resposta suportada" (FR08): quando os chunks recuperados não são relevantes o suficiente, responder isso explicitamente em vez de alucinar.
- [ ] Testar manualmente com pergunta fora do escopo dos papers indexados.

---

## Fase 4 — Orquestração com LangGraph (FR06, FR07)

**Estudar:**
- Documentação oficial do LangGraph: `State`, nós, edges condicionais.
- *ReAct: Synergizing Reasoning and Acting in Language Models* (Yao et al., 2022) — como um agente decide "agir" (buscar/ingerir) vs "responder direto".

**Tasks:**
- [ ] Desenhar o `State` do grafo (o que precisa transitar entre nós: pergunta, intenção classificada, paper_id se houver, chunks recuperados, resposta).
- [ ] Implementar nó de classificação de intenção (ingerir novo paper / responder pergunta / pedir esclarecimento).
- [ ] Ligar o nó de classificação → Ingestion Pipeline (Fase 1) via edge condicional.
- [ ] Ligar o nó de classificação → Retrieval + Generation (Fases 2–3) via edge condicional.
- [ ] Implementar o caminho de "pergunta ambígua" → pedir esclarecimento ao usuário.
- [ ] Implementar `/papers` (FR07): listar papers já indexados (query direta no Qdrant, sem passar pelo LLM).
- [ ] Logar cada decisão do grafo (nó executado, chunks recuperados) — ver NFR06.

---

## Fase 5 — Bot Discord (FR04, FR07)

**Estudar:**
- Modelo de eventos/comandos do `discord.py`, especialmente slash commands (pra `/papers`).

**Tasks:**
- [ ] Configurar bot no Discord Developer Portal e token em `.env` (NFR04 — nunca commitado; criar `.env.example`).
- [ ] Implementar handler de mensagem: recebe pergunta em linguagem natural → chama o grafo LangGraph → posta resposta.
- [ ] Implementar slash command `/papers` → chama listagem (Fase 4) → posta lista formatada.
- [ ] Testar end-to-end: ingestão de 1 paper + pergunta com citação, tudo via Discord.
- [ ] **Esse é o gate do MVP** — antes de ir pra Extensão 3 (WhatsApp), validar que tudo funciona bem aqui.

---

## Extensão 1 — Síntese multi-paper

**Estudar:**
- *GraphRAG* (Microsoft, 2024) — indexação baseada em grafo para sintetizar respostas que cruzam múltiplos documentos.

**Tasks:**
- [ ] Definir quando o agente decide que uma pergunta exige mais de um paper (novo caminho no grafo LangGraph).
- [ ] Avaliar se retrieval simples (buscar em múltiplos `paper_id` e combinar chunks) resolve, ou se vale importar ideias do GraphRAG (comunidades/sumarização entre documentos).

---

## Extensão 2 — Memória de conversa

**Tasks:**
- [ ] Adicionar estado de conversa (por sessão/canal) ao `State` do LangGraph.
- [ ] Permitir perguntas de acompanhamento sem repetir contexto (ex: "e na seção seguinte?").

---

## Extensão 3 — Integração com WhatsApp

**Tasks:**
- [ ] Só começar depois do MVP (Fase 5) testado e estável no Discord.
- [ ] Validar que só a camada `bot/` precisa de código novo (interface trocável, agente/retrieval/ingestão não devem assumir conceitos específicos do Discord — NFR07).

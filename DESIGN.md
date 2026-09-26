# Design Doc — ArXiv Paper RAG Assistant

## 1. Objetivo e Escopo

**O que é:** um assistente conversacional (bot) que busca papers de IA no arXiv (Attention Is All You Need, RAG, LoRA etc.), indexa seu conteúdo em um vector store, e responde perguntas técnicas citando o paper e a seção exata de onde veio a resposta. O projeto existe para praticar dois pontos específicos: (1) orquestração de agentes com LangGraph — decidir quando buscar um paper novo, quando responder direto do índice, quando pedir esclarecimento — e (2) RAG com granularidade de citação (não só "chunk relevante", mas seção identificável do documento original).

**O que NÃO é:** não é um RAG genérico de upload de PDF (isso já existe no [DocuTalk](https://github.com/fvilhalva/DocuTalk-RAG-Assistant)) — não haverá upload manual de arquivos arbitrários, só ingestão via arXiv API. Não é um produto multiusuário, não tem autenticação de usuários finais, não tem fine-tuning de modelo, e não busca ser um "assistente de pesquisa completo" (sem sumarização de múltiplos papers, sem geração de literature review). Escopo é deliberadamente estreito: 1 usuário (você), papers que você escolhe, respostas com citação verificável.

## 2. Requisitos Funcionais

- **FR01** — Usuário pode fornecer um ID/URL do arXiv (ex: `2005.11401` ou link) e o sistema baixa o PDF automaticamente.
- **FR02** — Sistema extrai texto do PDF preservando estrutura de seções (título, abstract, introdução, seções numeradas, referências).
- **FR03** — Sistema faz chunking e indexação vetorial associando cada chunk a metadata `{paper_id, título, seção}`.
- **FR04** — Usuário faz perguntas em linguagem natural via bot (Discord) e recebe resposta em texto.
- **FR05** — Toda resposta inclui citação no formato `[paper: título curto, seção: X.Y]` referenciando de onde veio a informação.
- **FR06** — Agente (LangGraph) decide entre: responder com base no índice existente, pedir para indexar um paper novo, ou pedir esclarecimento se a pergunta for ambígua.
- **FR07** — Usuário pode listar quais papers já estão indexados (`/papers`).
- **FR08** — Se a pergunta não tiver resposta suportada pelos papers indexados, o sistema informa isso explicitamente em vez de "alucinar" uma resposta.

## 3. Requisitos Não-Funcionais

- **NFR01 (Performance)** — Resposta a uma pergunta com paper já indexado em até ~15s (aceitável para LLM local rodando em GPU de consumo).
- **NFR02 (Custo)** — Stack 100% local (Ollama para LLM + embeddings) para custo zero por token; ponto de extensão documentado para trocar por API paga (ex: Claude) caso a qualidade de raciocínio do agente LangGraph não seja suficiente com modelo local.
- **NFR03 (Testabilidade)** — Lógica de parsing, chunking e formatação de citação deve ser testável sem depender de rede (LLM e arXiv mockados via fixtures).
- **NFR04 (Segurança — secrets)** — Token do bot (Discord) e eventuais chaves de API ficam em `.env`, nunca commitadas; `.env.example` versionado como template.
- **NFR05 (Segurança — prompt injection)** — Conteúdo extraído de PDFs é tratado como dado não confiável: nunca é interpretado como instrução de sistema; prompts do agente isolam claramente "contexto recuperado" de "instrução do usuário".
- **NFR06 (Observabilidade)** — Toda decisão do agente (qual nó do grafo foi executado, quais chunks foram recuperados) é logada, para depuração e para aprendizado (entender o "porquê" do comportamento do agente).
- **NFR07 (Manutenibilidade)** — Separação clara entre camada de ingestão, camada de retrieval e camada de orquestração de agente, para poder trocar peças (ex: vector store) sem reescrever o resto.
- **NFR08 (Portabilidade)** — Roda via Docker Compose (bot + Ollama + vector store), sem dependência de infraestrutura cloud.

## 4. Arquitetura

```
┌─────────────────────┐
│   Discord Bot        │  ← interface do usuário (discord.py)
└──────────┬───────────┘
           │ pergunta em linguagem natural
           ▼
┌──────────────────────────────────────────┐
│         Agent Orchestrator (LangGraph)     │
│                                            │
│   [entrada] → [classifica intenção]        │
│        ├── "indexar novo paper" ──────────┼──► Ingestion Pipeline
│        ├── "responder pergunta" ──────────┼──► Retrieval + Generation
│        └── "ambíguo" ──► pede esclarecimento
└──────────────────┬─────────────────────────┘
                    │
        ┌───────────┴────────────┐
        ▼                        ▼
┌───────────────────┐   ┌─────────────────────┐
│ Ingestion Pipeline │   │ Retrieval + Gen      │
│ - arXiv fetch      │   │ - query embedding    │
│ - PDF → texto       │   │ - vector search      │
│ - parse seções      │   │ - monta prompt com   │
│ - chunk + embed     │   │   chunks + metadata  │
│ - grava no vector   │   │ - LLM gera resposta  │
│   store             │   │   com citação        │
└─────────┬───────────┘   └──────────┬───────────┘
          │                          │
          ▼                          ▼
     ┌────────────────────────────────────┐
     │     Qdrant (vector store)          │
     │  payload: {paper_id, título, seção}│
     └────────────────────────────────────┘
                    │
                    ▼
          ┌───────────────────┐
          │  Ollama (local)    │
          │  LLM + embeddings  │
          └───────────────────┘
```

## 5. Stack Tecnológica

| Camada | Tecnologia | Por quê |
|---|---|---|
| Linguagem | Python 3.11+ | LangGraph é nativo em Python; ecossistema RAG (PDF parsing, arXiv clients) mais maduro que em TS |
| Orquestração de agente | LangGraph | Objetivo central de aprendizado do projeto |
| LLM + embeddings | Ollama (ex: `deepseek-r1:8b`, `nomic-embed-text`) | Local, custo zero, sua GPU (RTX 5060 Ti 16GB) roda bem modelos 7-8B |
| Vector store | Qdrant | Ferramenta nova (não repete o FAISS do projeto anterior); metadata filtering nativo, útil pra filtrar por `paper_id`/`seção` |
| Ingestão arXiv | `arxiv` (Python package) + `PyMuPDF`/`unstructured` | Download automático + extração de texto preservando estrutura de seções |
| Interface | `discord.py` | Simples de rodar no dia a dia, evita construir UI web |
| Infra | Docker Compose | Reproduzível, isola Ollama + Qdrant + bot |
| Config/secrets | `python-dotenv` + `.env` | Já é o padrão que você usa no DocuTalk |

## 6. Estratégia de Testes

- **Unitário:** parsing de PDF (seções corretamente identificadas), chunking (tamanho/overlap corretos), formatação de citação (`paper + seção` no formato esperado) — tudo com fixtures de 1-2 PDFs de exemplo salvos no repo (ex: um paper curto), sem chamar arXiv real.
- **Integração:** pipeline completo de ingestão (fixture PDF → chunks → Qdrant) rodando contra uma instância Qdrant local (Docker), e pipeline de resposta (pergunta → retrieval → prompt → resposta) com Ollama real rodando localmente. Sem mockar o LLM aqui — o objetivo é validar o comportamento fim-a-fim do agente.
- Fora de escopo por ora: testes de carga, testes de qualidade de resposta automatizados (avaliação de RAG é um projeto à parte).

## 7. Roadmap

**MVP:**
- Ingestão de 1 paper via arXiv ID → indexação no Qdrant.
- Bot no Discord responde perguntas sobre esse paper com citação de seção.
- Grafo LangGraph simples: 2 nós (classificar intenção → ingerir OU responder).

**Extensão 1 — Multi-paper com síntese entre documentos:**
- Perguntas que exigem combinar informação de mais de um paper indexado (ex: "como LoRA se compara à atenção do Transformer original?"), com o agente decidindo quando isso é necessário.

**Extensão 2 — Memória de conversa:**
- Agente mantém contexto entre perguntas na mesma sessão/canal, permitindo perguntas de acompanhamento sem repetir o contexto.

**Extensão 3 — Integração com WhatsApp:**
- Segunda interface de usuário, além do Discord. Só entra depois que o MVP estiver testado e funcionando no Discord — a interface de chat é tratada como camada substituível (bot/), então o agente/retrieval/ingestão não deveriam precisar mudar.

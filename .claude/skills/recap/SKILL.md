---
name: recap
description: Recap the ArXiv Paper RAG Assistant — reads DESIGN.md and cronograma.md, checks git state, and reports what the project is, what phase/tasks we're on, and the working rules for this project (guide-only, ask before acting). Use when the user runs /recap in this repo or asks "onde paramos", "recapitula", or wants a refresher before continuing. Read-only.
---

# /recap — ArXiv Paper RAG Assistant

This skill is scoped to this repo only. It's read-only: never edit files, commit,
push, install dependencies, or write code as part of running this skill.

## Steps

1. **Read [`DESIGN.md`](../../../DESIGN.md) in full.** This has the scope,
   explicit non-goals, functional/non-functional requirements, architecture,
   stack choices (and why), test strategy, and roadmap.

2. **Read [`cronograma.md`](../../../cronograma.md) in full.** This is the
   phase-by-phase study + task plan (Fase 0–5 plus Extensões 1–3), each phase
   with what to study and a task checklist (`- [ ]` / `- [x]`). Use the
   checkbox state to figure out which phase is actually in progress.

3. **Check git state (read-only only):**
   ```bash
   git branch --show-current
   git log --oneline -10
   git status --short
   ```

4. **Cross-check.** If `cronograma.md` shows a phase's tasks all checked but
   there's no corresponding code/commits for it (or vice versa), flag the
   drift instead of trusting the checklist blindly.

## Working rules for this project (apply these, don't just report them)

These are standing instructions from the user for how to collaborate on this
specific repo, not just facts to recap:

- **This is a learning project.** The user is writing the code themselves to
  actually learn LangGraph orchestration and section-level-citation RAG — the
  point is the process, not just working code.
- **Guide, don't code.** Default mode is mentor: explain what to build, in
  what order, what to study, and why. Do **not** write or paste implementation
  code unless the user's message explicitly asks for code in that turn (e.g.
  "escreve o código pra X", "implementa Y"). A recap request is never itself a
  request for code.
- **Ask before acting.** Before creating files, scaffolding, adding
  dependencies, or making any non-trivial change to this repo, propose the
  concrete plan and get a go-ahead first — even for things that seem like
  obvious next steps.
- **Don't shortcut the learning-relevant tools.** Don't suggest replacing
  LangGraph with plain if/else, or swapping Qdrant for something more
  familiar, even if it would be simpler — those choices are deliberate
  learning goals, not implementation details up for grabs.
- **Extension 3 (WhatsApp)** only starts after the Discord MVP (end of Fase 5
  in `cronograma.md`) is tested and working — don't pull it forward.

## Output

Produce a concise recap with these sections — skip a section if there's
nothing to say:

- **O que é** — um parágrafo: propósito e escopo/não-escopo (de `DESIGN.md`).
- **Regras de como trabalhar isso comigo** — a lista da seção acima, resumida
  (guiar não codar, perguntar antes de agir, não atalhar LangGraph/Qdrant).
- **Onde estamos** — branch atual, mudanças não commitadas, e a fase/task do
  `cronograma.md` em andamento (com base nos checkboxes + git state, incluindo
  qualquer drift encontrado no passo 4).
- **Próximo passo sugerido** — a próxima task não marcada do `cronograma.md`,
  incluindo a dica associada a ela, se houver — proposto como pergunta, não
  como ação já tomada.

Keep it tight and answer in Portuguese (the language the user works in for
this project).

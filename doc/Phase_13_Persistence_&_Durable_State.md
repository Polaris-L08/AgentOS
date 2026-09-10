# Phase 13: Persistence & Durable State

## Lesson 1: Durable State Model

### 三层模型

```text
┌─────────────────────────────┐
│       Live Runtime          │
│                             │
│ ExecutionHandle             │
│ RuntimeContext              │
│ AgentExecutionContext       │
│ AgentContext                │
│ MemoryRuntime                │
│ asyncio.Task                │
│ LLM Client                   │
│ Network Connection           │
└──────────────┬──────────────┘
               │
               │ snapshot / reconstruction
               ▼
┌─────────────────────────────┐
│       Durable State         │
│                             │
│ ExecutionState              │
│ Checkpoint                  │
│ SessionState                │
│ Memory State                │
│ Event Record                │
└──────────────┬──────────────┘
               │
               │ persistence
               ▼
┌─────────────────────────────┐
│        Persistence          │
│                             │
│ Memory Store                │
│ PostgreSQL                  │
│ Qdrant                      │
│ etc.                        │
└─────────────────────────────┘
```

最重要的一点：

> Durable State 不是 Persistence。


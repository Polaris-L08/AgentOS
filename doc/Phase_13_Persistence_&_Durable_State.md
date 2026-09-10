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


## Lesson 2： Execution / ExecutionState

> 正式建立 Logical Execution。

本节四个问题：

1. Execution 是什么？
2. ExecutionState 是什么？
3. Execution 的生命周期是什么？
4. Execution 如何 snapshot/restore ？

### 明确 Execution 和 ExecutionRuntime 的关系

当前Phase12：

```text
ExecutionRuntime
       │
       │ create_execution()
       ▼
ExecutionHandle
       │
       ▼
RuntimeContext
```

这个结构保持不变。

Phase13 增加：

```text
       Logical Layer
            
       Execution
          │
          │ owns
          ▼
    ExecutionState
            
       Live Layer
            
    ExecutionRuntime
          │
          ▼
    ExecutionHandle
          │
          ▼
    RuntimeContext
```

`Execution `不是 `ExecutionRuntime`的替代品。也不是一部分。而是代表：

> 一次 User Request 的逻辑执行实体。

### Logical Execution 与 Live Runtime

假设：

```text
Execution
execution_id = E123
```

第一次运行：

```text
ExecutionRuntime
        ↓
ExecutionHandle
        ↓
RuntimeContext
runtime_id = R001
```

如果发生进程崩溃：

```text
Execution E123
        ↓
Process crashed
```

恢复：

```text
Execution E123
        ↓
new ExecutionRuntime
        ↓
new ExecutionHandle
        ↓
RuntimeContext
runtime_id = R001
```

因此：

```text
execution_id
    = Logical Execution Identity

runtime_id
    = Live Runtime Identity
```

### ExecutionState 是什么？

```text
ExecutionState
    =
“这个 Execution 当前是什么生命周期状态？”
```

```text
Checkpoint
    =
“这个 Execution 执行到了哪里，以及恢复执行所需要的状态？”
```

**ExecutionState**

负责：

```text
Execution identity
Lifecycle status
Request metadata
Lifecycle timestamps
```

而不负责：

```text
AgentExecutionContext
Agent loop state
SharedContext execution snapshot
```

后者仍然由现有 Checkpoint 负责。

### Execution Lifecycle

```text
Created
Running
Paused
Completed
Failed
Cancelled
```

暂时不增加：

```text
Queued
Dispatched
Retrying
Recovering
```

生命周期：

```text
Created
   │
   │ start
   ▼
Running
   │
   ├──── pause ────► Paused
   │                    │
   │                    │ resume
   │                    ▼
   │                  Running
   │
   ├──── complete ──► Completed
   │
   ├──── fail ──────► Failed
   │
   └──── cancel ────► Cancelled
```

终止状态：

```text
Completed
Failed
Cancelled
```

### ExecutionState 字段设计

```text
ExecutionState
├── execution_id
├── status
├── task_id
├── session_id
├── created_at
├── updated_at
└── metadata
```

这里特意没有： `runtime_id`

原因非常重要：

> runtime_id 属于当前 Live Runtime，而 execution_id 属于 Logical Execution。

如果现在把 `runtime_id` 放进 `ExecutionState`，实际上又把 Logical Execution 和 Live Runtime 绑死了。
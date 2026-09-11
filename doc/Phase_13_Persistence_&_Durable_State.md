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


## Lesson 3: Execution ↔ Checkpoint

### execution_id 和 runtime_id

| 对象             | ID              | 意义                     |
|----------------|-----------------|------------------------|
| Execution      | `execution_id`  | 逻辑执行是谁                 |
| RuntimeContext | `runtime_id`    | 这个 Runtime Context 的身份 |
| Checkpoint     | `checkpoint_id` | 某一次执行快照是谁              |
| Trace          | `trace_id`      | 某一次 Trace 是谁           |

### ExecutionState 和 Checkpoint 不应该合并

**ExecutionState**

回答： 这个 Execution 现在处于什么生命周期状态？

例如：

```text
execution_id = E123
status       = PAUSED
task_id      = T001
session_id   = S001
```

它属于： `Logical Execution`

**Checkpoint**

回答： 这个 Execution 执行到哪里了？恢复它需要哪些 Runtime Execution State？

当前已有：

```text
checkpoint_id
runtime_id
shared_context
agents
task_id
```

其中：

```text
shared_context
agents
```

是恢复真正执行所需要的数据。

### Lesson 3 总结

```text
                Execution
                    │
          ┌─────────┴─────────┐
          ▼                   ▼
  ExecutionState          Checkpoint
  logical state           progress snapshot
          │                   │
 execution_id             runtime_id
 status                   shared_context
 lifecycle                agent states
```

以及：

```text
Execution
    ↓
snapshot()
    ↓
ExecutionState
```

恢复Runtime：

```text
Checkpoint
    ↓
ExecutionRuntime
    ↓
RuntimeContext
    ↓
SAME runtime_id
```


## Lesson 4: Session Persistence Model

### Session 和 Execution 的关系

进入 Phase13 后，我们现在有：

```text
Session
    │
    ├── Execution E001
    ├── Execution E002
    └── Execution E003
```

所以：

```text
Session
    = Conversation / Interaction Boundary

Execution
    = One logical execution inside that Session
```

例如：

```text
Session S001
│
├── Execution E001
│     "分析 NVIDIA"
│
├── Execution E002
│     "再分析一下风险"
│
└── Execution E003
      "给我最终结论"
```

因此：

> Session 不应该等价于 Execution。

### Session 需要持久化什么？

当前 Session 只有：

```text
session_id
created_at
metadata
```

因此 Lesson4 我们先保持这个边界。

Durable State：

```text
SessionState
├── session_id
├── created_at
└── metadata
```

而不应该包含：

```text
RuntimeContext
ExecutionRuntime
ExecutionHandle
AgentExecutionContext
asyncio.Task
Middleware Chain
Trace
EventBus
```

这些都是 **Live Runtime Object**。

### 架构结果

```text
┌──────────────────────┐
│       Session        │
│   Live Object        │
├──────────────────────┤
│ session_id           │
│ created_at            │
│ metadata             │
└──────────┬───────────┘
           │
       snapshot()
           │
           ▼
┌──────────────────────┐
│    SessionState      │
│   Durable State      │
├──────────────────────┤
│ session_id           │
│ created_at            │
│ metadata             │
└──────────────────────┘
```

```text
                     Session
                        │
                        │
                  SessionState
                        │
                        │
              ┌─────────┴─────────┐
              │                   │
        Execution E001       Execution E002
              │
              ├── ExecutionState
              │
              └── Checkpoint(s)
                       │
                       │
                 runtime_id
                       │
                       ▼
                RuntimeContext
```

**Session 不拥有 RuntimeContext。**

**ExecutionState 不等于 Checkpoint。**

**Checkpoint 不等于 RuntimeContext。**

**Durable State 不等于 Live Runtime Object。**

### 本科总结

我们现在正式建立了第二组 Durable State：

```text
Session
   ↕
SessionState
```

加上上一课：

```text
Execution
   ↕
ExecutionState
```

并明确：

`Checkpoint`

仍然独立存在，用于保存 恢复执行所需的进度状态。

所以 Phase13 当前核心结构是：

```text
Live Object
     │
     │ snapshot()
     ▼
Durable State
     │
     │ Persistence
     ▼
Durable Storage
     │
     │ load
     ▼
Durable State
     │
     │ from_state()
     ▼
Live Object
```


## Lesson 5： Persistence Contracts

### 完成后的整体架构

```text
┌─────────────────────────────────────┐
│           Live Domain               │
│                                     │
│  Session        Execution           │
└───────────────┬─────────────────────┘
                │
            snapshot()
                │
                ▼
┌─────────────────────────────────────┐
│          Durable State              │
│                                     │
│ SessionState   ExecutionState       │
│                                     │
│ Checkpoint                         │
└───────────────┬─────────────────────┘
                │
                ▼
┌─────────────────────────────────────┐
│       Persistence Contracts         │
│                                     │
│ SessionStore                        │
│ ExecutionStore                      │
│ CheckpointStore                     │
└───────────────┬─────────────────────┘
                │
                ▼
┌─────────────────────────────────────┐
│       Persistence Implementations   │
│                                     │
│ In-Memory        PostgreSQL          │
│                  Adapter             │
└─────────────────────────────────────┘
```

### Lesson 5 总结

这一课最重要的不是增加多少代码，而是正式确定：

> Persistence 是一个 Boundary，而不是 Runtime 的一部分。

我们现在有：

```text
Session
   ↓
SessionState
   ↓
SessionStore
```

```text
Execution
   ↓
ExecutionState
   ↓
ExecutionStore
```

以及已有：

```text
Checkpoint
   ↓
CheckpointStore
```

同时明确：

`ExecutionStore ≠ CheckpointStore`

以及：

`Cancelled ≠ Deleted`

更重要的是：

```text
Runtime Core
      ↓
Persistence Contract
      ↓
Adapter
      ↓
PostgreSQL
```

而不是 Runtime 直接连接数据库。


## Lesson 6: In-Memory Persistence

本课目标：

```text
SessionState
      ↓
InMemorySessionStore

ExecutionState
      ↓
InMemoryExecutionStore
```

并验证：

```text
save
load
replace
delete
missing record
state isolation
```

### 重要原则： Store 保存 Durable State，而不是 Live Object

我们不会设计：

`store.save(session)`

而是：

`store.save(session.snapshot())`

也就是：

```text
Session
   ↓
snapshot()
   ↓
SessionState
   ↓
InMemorySessionStore
```

Execution 同样：

```text
Execution
   ↓
snapshot()
   ↓
ExecutionState
   ↓
InMemoryExecutionStore
```

因此 Store 永远不知道：

```text
Session
Execution
RuntimeContext
ExecutionRuntime
```

它只知道 Durable State。

### 本课真正建立的不是两个字典

表面上我们只是实现了：

`self._states: dict[str, State]`

但实际上我们建立了一个非常重要的 Persistence 语义：

```text
save(State)
    ↓
Store owns a copy

load(id)
    ↓
Caller receives a copy
```

也就是：

> Persistence Boundary 不共享 Mutable State。

这对未来 PostgreSQL 是很自然的：

```text
Python Object
      ↓
SQLAlchemy serialization
      ↓
Database row
```

数据库天然不会和 Python 对象共享同一个 dict。

我们现在让 In-Memory 实现也遵守这个语义。

### 当前 Persistence 层结构

完成 Lesson6 后：

```text
runtime/persistence/
│
├── __init__.py
│
├── session_store.py
│       └── SessionStore
│
├── execution_store.py
│       └── ExecutionStore
│
├── in_memory_session_store.py
│       └── InMemorySessionStore
│
└── in_memory_execution_store.py
        └── InMemoryExecutionStore
```

Checkpoint 保持：

```text
runtime/checkpoint/
│
└── checkpoint_store.py
        └── CheckpointStore
```

所以现在：

```text
SessionStore
      │
      ▼
InMemorySessionStore
ExecutionStore
      │
      ▼
InMemoryExecutionStore
```

以及：

```text
CheckpointStore
      │
      ▼
MemoryCheckpointStore
```

实际上已经形成了三组：

```text
Durable State / Snapshot
            │
            ▼
       Persistence
            │
     ┌──────┴──────┐
     ▼             ▼
   Memory       PostgreSQL
```


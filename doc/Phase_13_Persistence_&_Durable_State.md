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


## Lesson 7: Persistence Integration

### 本课目标

本课要建立第一条真正的 Application Runtime 链路：

```text
Application
    │
    ├── Session
    │      ↓ snapshot()
    │   SessionState
    │      ↓
    │   SessionStore
    │
    └── Execution
           ↓ snapshot()
        ExecutionState
           ↓
        ExecutionStore
```

注意：

> 本课不是把所有 Runtime Object 都持久化。

尤其不能出现：

```text
RuntimeContext → DB
ExecutionHandle → DB
AgentExecutionContext → DB
Trace → DB
asyncio.Task → DB
```

这些仍然属于 Live Runtime。

### 设计原则

> Persistence 是 Application 的可配置能力。

应该是：

```text
AgentApplication
      │
      ├── SessionStore
      │
      └── ExecutionStore
```

Store是依赖注入的。例如：

```text
开发 / 测试

Application
 ├── InMemorySessionStore
 └── InMemoryExecutionStore
```

```text
生产环境

Application
 ├── PostgreSQLSessionStore
 └── PostgreSQLExecutionStore
```

### 最终执行链

```text
    AgentApplication
           │
           │ execute()
           ▼
       ApplicationExecutor
           │
           │ create logical Execution
           ▼
       Execution
           │
           │ snapshot()
           ▼
     ExecutionState
           │
           │ save()
           ▼
     ExecutionStore
           │
    InMemory / PostgreSQL
```

真正运行 Agent 的链路仍然完全没有改变：

```text
ApplicationExecutor
       │
       │ ExecutionRuntime.create_execution()
       ▼
ExecutionHandle
       │
       ▼
RuntimeContext
       │
       ▼
Application.invoke_agent()
       │
       ▼
AgentRuntime
       │
       ▼
Agent
```

### Lesson 7 总结

Lesson7 真正建立的是 Application 与 Persistence Contract 之间的连接，而不是数据库实现。

核心边界现在变成：

```text
Live Object
    ↓
snapshot()
    ↓
Durable State
    ↓
Store
```

并且我们正式让：

`Execution`

成为 Application 层可以识别的 Logical Execution Object，但没有让它取代：

`ExecutionHandle`

也没有把它变成 Database Entity。


## Lesson 8: PostgreSQL Persistence

### 本课目标

> 把 InMemory Persistence 替换为 PostgreSQL Persistence。

**重要原则**：

> PostgreSQL 只能出现在 Persistence Adapter 层，不能进入 Runtime Core。

### 数据库模型与 Runtime State 模型分离

```text
Session
   │
   ▼
SessionState
   │
   ▼
SessionStore
   │
   ▼
PostgresSessionStore
   │
   ├── SessionRecord
   │
   └── PostgreSQL
```

**SessionState** 是 `Durable State Model`。

**SQLAlchemy ORM Model** 是 `Persistence Model`。

### 数据库结构

#### 1. sessions

逻辑结构：

```text
sessions
────────────────────────
session_id       PK
created_at
metadata
```

其中： metadata 使用 PostgreSQL JSONB。

#### 2. executions

逻辑结构：

```text
executions
────────────────────────
execution_id     PK
status
task_id
session_id
created_at
updated_at
```

同样不需要把整个 Runtime Object 放进数据库。

这里存的是： ExecutionState 而不是： Execution


## Lesson 9： PostgreSQL Integration & Schema Initialization

### 本课目标

> 让 PostgreSQL Adapter 可以在本地真实数据库中完成建表和连接验证。


## Lesson 10：PostgreSQL Store Integration Test


## Lesson 11：Persistence Configuration & Store Selection

### 本课目标

核心原则：

> Application 只依赖 SessionStore 和 ExecutionStore 抽象，不负责决定具体存储实现。

引入：

```text
PersistenceConfig
        ↓
PersistenceMode
        ↓
PersistenceStoreFactory
        ↓
SessionStore / ExecutionStore
        ↓
Application
```

新增三个核心对象：

| **对象**                | **职责**               |
|-------------------------|------------------------|
| PersistenceMode         | 表示使用哪种持久化模式 |
| PersistenceConfig       | 描述持久化配置         |
| PersistenceStoreFactory | 根据配置创建具体Store  |

### 设计决定

#### 1. 持久化模式

当前只支持两种模式：

```text
IN_MEMORY
POSTGRES
```

#### 2. 默认模式

`PersistenceMode.IN_MEMORY`

这样可以保证：

 - 现有测试不需要启动 PostgreSQL
 - 现有 Application 行为不改变
 - 运行 AgentOS 不需要数据库
 - PostgreSQL 只在明确配置时启用

#### 3. PostgreSQL 配置

PostgreSQL 模式必须提供：

`DatabaseConfig`

不能在 Factory 内部硬编码数据库地址、用户名或密码。


## Lesson 12: 将 PersistenceConfig 接入 ApplicationAssembly

### 本课目标

Lesson11 已完成：

 - PersistenceMode
 - PersistenceConfig
 - PersistenceStoreFactory
 - In-Memory Store 选择
 - PostgreSQL Store 选择
 - 默认仍为 In-Memory
 - 测试通过

本课将把配置真正接入 Application，使调用方可以通过：

`PersistenceConfig(...)`

决定 Application 使用哪一种持久化实现。

最终希望支持：

```python
application = (
    ApplicationAssembly(...)
    .with_persistence(
        PersistenceConfig(
            mode=PersistenceMode.IN_MEMORY,
        )
    )
    .build()
)
```

或者：

```python
application = (
    ApplicationAssembly(...)
    .with_persistence(
        PersistenceConfig(
            mode=PersistenceMode.POSTGRES,
            database=DatabaseConfig(
                database_url=(
                    "postgresql+asyncpg://"
                    "agentos:agentos@localhost:5432/agentos"
                ),
            ),
        )
    )
    .build()
)
```

Application 本身不需要知道：

 - `InMemorySessionStore`
 - `PostgresSessionStore`
 - `InMemoryExecutionStore`
 - `PostgresExecutionStore`

这些具体类型由 PersistenceStoreFactory 负责创建。


## Lesson 13: Persistence Resource Lifecycle

> 由 ApplicationAssembly 创建的 Persistence Store，其底层数据库资源由谁负责释放？

### 当前生命周期

```text
ApplicationAssembly
        │
        │ build()
        ▼
AgentApplication
        │
        ├── SessionStore
        │      └── PostgresDatabase
        │
        └── ExecutionStore
               └── PostgresDatabase
```

这里还有一个更具体的问题。

当前的 `PersistenceStoreFactory.create_stores()` 是：

```text
PersistenceStoreFactory
        │
        ├── create_session_store()
        │       └── new PostgresDatabase
        │
        └── create_execution_store()
                └── new PostgresDatabase
```

也就是说，PostgreSQL 模式下目前实际上可能得到：

```text
PostgresSessionStore
        │
        └── PostgresDatabase A

PostgresExecutionStore
        │
        └── PostgresDatabase B
```

而不是：

```text
                 PostgresDatabase
                    /       \
                   /         \
                  ▼           ▼
       SessionStore       ExecutionStore
```

这是一个值得注意的问题。

### 区分三个概念

#### 1. Store

> 持久化能力的抽象/Adapter

负责：

```text
save
load
delete
```

#### 2. Database

> 基础设施资源

它可能拥有：

```text
connection pool
engine
database connections
```

所以它需要：

```text
open
close
```

或者至少需要 close()。

#### 3. Application

Application 才是一个完整运行单元。

它已经有：

```text
initialize()
start()
stop()
```

因此对于由 Application 组装出来的 Persistence 资源，一个自然的生命周期是：

```text
Application.initialize()
        ↓
Application.start()
        ↓
Application executes
        ↓
Application.stop()
        ↓
Persistence resources released
```

### 核心原则

> 谁创建资源，谁拥有资源；谁拥有资源，谁负责释放资源。Resource Ownership（资源所有权）

但是这里有一个特殊情况：

```text
ApplicationAssembly
        ↓
创建 Store
        ↓
Store 内部创建 Database
        ↓
返回给 Application
```

Assembly 本身只是一个： `Composition Root（组合根）`

它的生命周期很短：

```text
assembly.build()
       ↓
return application
       ↓
assembly 不再参与运行
```

因此不能让 Assembly 承担运行期间的资源生命周期。 所以最终应该是：

```text
ApplicationAssembly
       │
       │ build
       ▼
AgentApplication
       │
       │ owns
       ▼
Persistence resources
```

即：

> Assembly 负责组装，Application 负责运行期资源生命周期。


## Lesson 14： Execution / Checkpoint / Runtime Persistence Integration

### 本课目标

本课不是新增 Persistence 基础设施，也不是重新实现 CheckpointStore。

本课要解决的是：

> 一个 Logical Execution 如何与它实际运行的 Runtime，以及用于恢复的 Checkpoint 建立明确、可持久化的关系。

### 审计后的核心结论

```text
                     Logical Layer
                ┌────────────────────┐
                │     Execution      │
                │                    │
                │ execution_id = E1  │
                │ status = PAUSED    │
                └─────────┬──────────┘
                          │
                          │ associated checkpoint
                          ▼
                ┌────────────────────┐
                │     Checkpoint     │
                │                    │
                │ checkpoint_id=C1   │
                │ execution_id = E1  │
                │ runtime_id = R1   │
                │ shared_context     │
                │ agents             │
                └─────────┬──────────┘
                          │
                          │ reconstruct
                          ▼
                ┌────────────────────┐
                │  RuntimeContext    │
                │                    │
                │ runtime_id = R1    │
                │ trace = NEW        │
                └─────────┬──────────┘
                          │
                          ▼
                  ExecutionRuntime
                          │
                          ▼
                   ExecutionHandle
```

> Execution 是“我正在执行什么”，
> Checkpoint 是“它执行到了哪里”，
> Runtime 是“现在由哪个运行时实例承载它”。

### 核心设计

```text
Execution
    │
    │ current_checkpoint_id
    ▼
Checkpoint
    │
    │ runtime_id
    ▼
RuntimeContext
```

职责分别是：

| 对象                           | 核心职责                                |
|--------------------------------|-----------------------------------------|
| `Execution` / `ExecutionState` | 表示一次 Logical Execution 及其生命周期 |
| `Checkpoint`                   | 保存可恢复的 Runtime Snapshot           |
| `RuntimeContext`               | 当前正在运行的 Live Runtime             |
| `CheckpointStore`              | 持久化 / 读取 Checkpoint                |
| `ExecutionStore`               | 持久化 / 读取 Logical Execution         |

### 修改意见

1. `ExecutionState` 增加 `current_checkpoint_id`
    它表达的是：

    当前这个 Logical Execution 如果需要恢复，应该从哪个 Checkpoint 恢复。

    而不是：

    Checkpoint 属于哪个 Execution。

    这是一个很重要的方向性区别。

2. Checkpoint 不增加 execution_id

3. 为什么 ExecutionState 可以保存 current_checkpoint_id
    因为这是 Execution 自己的恢复游标。

    例如：
    ```text
    Execution E001
    
    status = PAUSED
    current_checkpoint_id = C003
   ```
    
    Checkpoint Store：

    ```text
    C001
    C002
    C003
    ```
   
    那么恢复：

    ```text
    E001
     │
     │ current_checkpoint_id = C003
     ▼
    C003
     │
     │ runtime_id = R001
     ▼
    RuntimeContext(R001)
    ```
   
    这意味着一个 Execution 可以拥有多个 Checkpoint：

4. 扩展ApplicationExecutor，增加恢复入口


    ```text
    E001
     ├── C001
     ├── C002
     └── C003 ← current
    ```
   
    而 ExecutionState 只需要知道： `current_checkpoint_id = C003`

### 最终模型

```text
┌─────────────────────────────┐
│       Execution E001        │
│                             │
│ execution_id = E001         │
│ status = PAUSED             │
│ current_checkpoint_id=C003  │
└──────────────┬──────────────┘
               │
               │ load(C003)
               ▼
┌─────────────────────────────┐
│      Checkpoint C003        │
│                             │
│ checkpoint_id = C003        │
│ runtime_id = R001           │
│ task_id = T001              │
│ shared_context = ...        │
│ agents = ...                │
└──────────────┬──────────────┘
               │
               │ resume
               ▼
┌─────────────────────────────┐
│     RuntimeContext          │
│                             │
│ runtime_id = R001           │
│ trace_id = NEW              │
│ shared_context = ...        │
└─────────────────────────────┘
```

> Execution 决定“恢复哪个 Checkpoint”；Checkpoint 决定“如何恢复 Runtime”。

### 测试文件

`tests/runtime/application/test_application_executor_recovery.py`

| 测试                                                                      | 验证内容                                           |
|---------------------------------------------------------------------------|----------------------------------------------------|
| `test_recover_persisted_execution_successfully`                           | 完整持久化恢复链路                                 |
| `test_recover_persisted_execution_preserves_execution_identity`           | `execution_id` 与 `runtime_id` 身份分离            |
| `test_recover_persisted_execution_fails_when_execution_does_not_exist`    | Execution 不存在                                   |
| `test_recover_persisted_execution_fails_when_execution_has_no_checkpoint` | 没有恢复 Checkpoint                                |
| `test_recover_persisted_execution_fails_when_checkpoint_does_not_exist`   | Checkpoint 不存在                                  |
| `test_recover_persisted_execution_fails_when_task_id_does_not_match`      | Execution / Checkpoint 关联校验                    |
| `test_recover_persisted_execution_restores_shared_context`                | SharedContext 恢复                                 |
| `test_recover_persisted_execution_creates_new_trace`                      | 恢复时创建新的 Trace，同时使用 `agent.resume` span |


## Lesson 15: TaskStore

在Lesson14的实现过程中，发现`task_id`与`task_request`之间没有映射关系。系统中缺乏TaskRequest的查询组件。


## Lesson 16: Persistence Integration

### 目标：

这一课我们正式把前面已经独立存在的：

```text
TaskStore
ExecutionStore
CheckpointStore
```
接入 Application / ApplicationExecutor。

本 Lesson 的目标不是做 PostgreSQL TaskStore，而是先把运行时的持久化写入链路闭合。

完成后：

```text
Application.execute(task)
        │
        ├── TaskStore.save(task)
        │
        ├── Execution.create
        │
        ├── ExecutionStore.save(Created)
        │
        ├── Execution.start
        │
        ├── ExecutionStore.save(Running)
        │
        └── Agent execution
```

同时提供Checkpoint持久化协调：

```text
ExecutionHandle
      +
Checkpoint
      │
      ↓
CheckpointStore.save()
      │
      ↓
Execution.set_checkpoint()
      │
      ↓
ExecutionStore.save()
```

### 需要注意的

Lesson16 没有修改 `PersistenceStoreBundle` 和 `PersistenceStoreFactory`。

当前它们只负责：

```text
SessionStore
ExecutionStore
```

这是当前源码的实际状态。`PersistenceStoreBundle` 目前只有 `session_store`、`execution_store` 和 PostgreSQL resources。 `PersistenceStoreFactory` 目前也只根据配置创建 SessionStore / ExecutionStore。

因此现在：

```text
IN_MEMORY
    SessionStore       → InMemory
    ExecutionStore     → InMemory
    TaskStore          → InMemory
    CheckpointStore    → Memory

POSTGRES
    SessionStore       → PostgreSQL
    ExecutionStore     → PostgreSQL
    TaskStore          → InMemory   ← 临时
    CheckpointStore    → Memory      ← 临时
```

这不是最终状态。

Lesson17 会一次性改成：

```text
POSTGRES
    SessionStore       → PostgreSQL
    ExecutionStore     → PostgreSQL
    TaskStore          → PostgreSQL
    CheckpointStore    → PostgreSQL
```

然后才开始真正的跨进程持久化。
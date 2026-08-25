# Phase 11: Agent Memory

## Lesson 1: Agent Memory Boundary

### 当前生命周期

当前项目中形成了三层结构：

**RuntimeContext**:

> 一次 Runtime Execution

服务于： `User Request -> 一次完整 Execution`

**AgentExecutionContext**:

> 一次 Agent Invocation。

**AgentContext**:

> Agent的长期上下文。

但是，当前项目中：

```text
AgentExecutionContext
    └── ContextState
          └── AgentContext
```

实际生命周期为：

```text
AgentExecutionContext
        ↓
ContextState
        ↓
AgentContext
        ↓
MemoryState
```

AgentContext实际上会随着AgentExecutionContext一起创建。

## Lesson 2： AgentContext 生命周期重构

> 让AgentContext 真正脱离 AgentExecutionContext 的生命周期。

目标结构：

```text
Agent Instance
    │
    └── AgentContext
          │
          └── MemoryState
                │
                └── 跨 Execution 存在

Execution #1
    │
    └── AgentExecutionContext #1
              │
              └── LoopState

Execution #2
    │
    └── AgentExecutionContext #2
              │
              └── LoopState
```

Checkpoint不再保存AgentContext.

> AgentContext 与 AgentExecutionContext 是两个并列但有关联的生命周期对象。

新架构如下：

```text
                         RuntimeContext
                              │
               ┌──────────────┼──────────────┐
               │              │              │
               ↓              ↓              ↓
          Supervisor      Research        Risk
               │              │              │
               ↓              ↓              ↓
         ExecutionCtx    ExecutionCtx    ExecutionCtx
               │              │              │
               ↓              ↓              ↓
          LoopState       LoopState       LoopState


Agent Instance
      │
      ├── AgentContext
      │       │
      │       └── MemoryState
      │
      └── identity
```

## Lesson 3: Memory Runtime 实现

关于使用`agent_id`作为`MemoryStore`中的key值：

事实上`agent_id`和`agent_type`都不能天然成为Memory的正确Key。

这是事实上是Memory Scope的问题。会在后续进行进一步讨论。


## Lesson 4: Memory Access Model

### Lesson 4 目标

> Agent 在什么情况下应该读 Memory、写 Memory，以及 Runtime 如何控制这种访问？

把：

```text
Agent
   ↓
memory.write()
memory.read()
```

提升为：

```text
Agent
   ↓
MemoryRuntime
   ↓
Memory Access Policy
   ↓
MemoryStore
```

> MemoryStore 决定“怎么存”，MemoryRuntime 决定“怎么访问”。

### 为什么需要Access Model

当存在多个Agent时，控制每个Agent的读写权限。

### 设计边界

```text
MemoryRuntime
    ↓
MemoryAccessPolicy
    ↓
MemoryStore
```

**MemoryRuntime**: 执行Memory操作

**AccessPolicy**： 这个操作是否允许

**MemoryStore**： 数据如何保存
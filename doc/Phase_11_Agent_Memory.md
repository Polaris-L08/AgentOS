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



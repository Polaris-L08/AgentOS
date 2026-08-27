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


## Lesson 5: MemoryScope

本节引入`MemoryScope`，用来终结 Memory 的key使用`agent_id`还是`agent_type`。

> 把 Memory 的“归属关系”从`agent_id`中抽象出来。

暂时只定义两个Scope: `AGENT`和`AGENT_TYPE`

不在现在加入： `USER`、`PROJECT`、`SESSION`、`SHARED`等。因为现在还没有User/Project等完整生命周期。


## Lesson 6: Multi-Scope Memory / Scope Resolution

> 当一个 Agent 同时拥有多个 Memory Scope 时，MemoryRuntime 到底访问哪个 Scope？

根据Lesson 5中的结构，一个Agent拥有两个`MemoryScope`:

```text
Agent A
│
├── AGENT
│     └── research-001
│
└── AGENT_TYPE
      └── research-agent
```

同时拥有： `Private Memory + Agent-Type Shared Memory`

那么调用 `agent.memory.read(context)` 应该返回 `AGENT Memory` 还是 `AGENT + AGENT_TYPE` ？

这个过程就是 **Scope Resolution(Scope解析)**

### ScopeResolver 的职责

**MemoryStore** 负责 **给定一个Scope，操作这个Scope 下的Memory。**

因此，增加 `MemoryScopeResolver` 承担Runtime层的语义。

> 当前 Memory 操作应该使用哪些Scope? 
> 
> Resolver不读取 Memory, 只负责 Scope。

### 第一版 Resolution Policy

> Private Memory 优先，Shared Agent-Type Memory 次之。

因此， `resolve()` 返回：

```text
[
    AGENT(research-001),
    AGENT_TYPE(research-agent),
]
```

顺序本身就是语义的一部分。 顺序就是优先级（AGENT > AGENT_TYPE）

>  越具体的 Scope 优先于越泛化的 Scope。


## Lesson 7: Memory Retrieval Boundary

当前的MemoryRuntime中包含以下方法：

```text
MemoryRuntime
    │
    ├── write()
    ├── read()
    ├── query()
    ├── forget()
    └── clear()
```

其中：write、forget、clear 属于 **Memory Lifecycle/Mutation**。

而： read、query 属于 **Memory Retrieval**。

因为当前Memory就是string，而未来可能会扩张为：

```text
Query
   ↓
Retrieval
   ├── lexical search
   ├── vector search
   ├── metadata filtering
   ├── recency
   ├── relevance ranking
   └── scope priority
```

所以，需要把`MemoryStore`和`Memory Retrieval`分开。

### 职责划分

**MemoryRuntime** 负责： 

```text
Access Control
Scope Resolution
Runtime Invocation
Lifecycle
```

**MemoryRetriever** 负责：`如何从给定 Memory 集合中找到相关 Memory`

**MemoryStore** 负责： `持久化`。

### 第一版Retriever

实现一个简单的`KeywordMemoryRetriever`，不做embedding。

接口：

```
class MemoryRetriever(Protocol):

    def retrieve(
        self,
        memories: list[MemoryItem],
        query: str,
        limit: int,
    ) -> list[MemoryItem]:
        ...
```

### 架构变化

以前：

```text
MemoryRuntime.query()
    ↓
MemoryStore.query()
```

现在：

```text
MemoryRuntime.query()
    ↓
MemoryStore.read()
    ↓
candidate memories
    ↓
MemoryRetriever.retrieve()
```

Store 只负责： `给我这个 Scope 下有什么 Memory。`

Retriever 负责： `在这些 Memory 中，哪些与 Query 相关？`

MemoryRetriever 是纯计算策略。

 - 不访问外部资源
 - 不修改 Runtime State
 - 不进行持久化
 - 不属于 Runtime Component
 - 不产生独立生命周期操作


## Lesson 8: Memory Lifecycle

相同的message在不同的时间意义完全不同。

在本节加入： MemoryMetadata 

```text
MemoryItem
├── id
├── content
└── metadata
      ├── created_at
      └── expires_at
```

## Lesson 9: Memory Ranking

当前查询会**按照Store返回的原始顺序返回**。因此，引入 Memory Ranking（记忆排序）。

单独建立MemoryRanker的作用在于：职责分离，而且便于未来更加复杂的排序策略的扩展。


## Lesson 10: Recency 时间相关性

当前项目中，排序策略只考虑Importance, 但时间是一个非常重要的维度。

所以当前阶段目标为：

> Recency Score Normalization（新鲜度归一化）

### 新增 RecencyScorer：

```text
MemoryItem
     ↓
created_at
     ↓
Recency Score
     ↓
0.0 ~ 1.0
```

### 对`ExponentialRecencyScorer(指数衰减`原理解释:

```text
score = exp(-λ × age)
```

```text
age = 0
    ↓
score = 1

age = half_life
    ↓
score = 0.5

age → ∞
    ↓
score → 0
```

```text
当 half_life_days = 30 时：

刚创建       1.00
30 天        0.50
60 天        0.25
90 天        0.125
```

### Half-Life 需是参数，原因如下：

不同Memory的生命周期不同：

 - 实时监控Agent： `half-life = 1 hour`
 - ResearchAgent： `half-life = 30 days`
 - Long-term Personal Assistant: `half-life = 365 days`

### 当前架构：

```text
                    MemoryRuntime
                          │
                          ↓
                     MemoryStore
                          │
                          ↓
                  MemoryRetriever
                          │
                 ┌────────┴────────┐
                 │                 │
             Filtering         Retrieval
                 │                 │
                 └────────┬────────┘
                          ↓
                     Candidates
                          │
                          ↓
                     MemoryRanker
                          │
              ┌───────────┴───────────┐
              │                       │
          Importance              Recency
              │                       │
              │                MemoryMetadata
              │                  created_at
              │                       │
              └───────────┬───────────┘
                          ↓
                     Final Ranking
                          ↓
                         Top-K
```

这里有一个很重要的变化：

`MemoryItem` 仍然完全不知道：

```text
Ranking
Scoring
Retrieval
```

它只提供：

```text
importance
source
metadata
```

这就是正确的 Entity Boundary。

### Lesson 10修改清单

新增

```text
runtime/memory/memory_recency.py

tests/runtime/test_memory_recency.py
```

修改

```text
runtime/memory/memory_ranker.py

tests/runtime/test_memory_ranker.py
```

### Lesson 10 核心结论

我们现在已经形成：

```text
Lesson8
Memory Lifecycle
        ↓
created_at / expires_at

Lesson9
Ranking Boundary
        ↓
MemoryRanker

Lesson10
Ranking Signals
        ↓
Importance + Recency
```
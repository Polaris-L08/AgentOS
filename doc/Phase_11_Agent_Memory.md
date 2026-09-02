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


## Lesson 11： Candidate Retrieval 与 Retrieval Strategy

当前的 `KeywordMemoryRetriever`事实上同时做了3件事：

1. 过滤 expired Memory
2. keyword matching
3. 调用 Ranker

随着系统的演进，这这三个职责会逐渐变得不够清晰。

把 Retrieval 拆成两个概念： Candidate Retrieval(候选召回)、Ranking(排序)

本节目标：

> Candidate Retrieval Strategy 的抽象

### 新增`MemoryCandidateRetriever`只负责 **Recall**。

### 调整`MemoryRetriever`职责，作为orchestration-level abstraction：

```text
CandidateRetriever
        ↓
Ranker
        ↓
Top-K
```

### 扩展

未来加入Vector,只需要增加：

```python
class VectorMemoryCandidateRetriever(
    MemoryCandidateRetriever
):
    ...
```

```text
DefaultMemoryRetriever
       │
       ├── VectorMemoryCandidateRetriever
       │
       └── ImportanceRecencyMemoryRanker
```

### Lesson 11 架构

```text
                      MemoryRuntime
                            │
                            ↓
                     MemoryRetriever
                            │
                            ↓
                  DefaultMemoryRetriever
                            │
                ┌───────────┴───────────┐
                ↓                       ↓
      MemoryCandidateRetriever      MemoryRanker
                │                       │
                ↓                       ↓
KeywordMemoryCandidateRetriever   ImportanceMemoryRanker
                                   ImportanceRecency...
                │
                ↓
           Candidates
                │
                ↓
             Ranking
                │
                ↓
              Top-K
```

`KeywordMemoryRetriever` 已经被 `DefaultMemoryRetriever`代替

```text
Keyword Retrieval
+
Ranking
+
Limit
```

由`KeywordMemoryCandidateRetriever + DefaultMemoryRetriever`构成。

### Lesson 11 修改清单

 - 新增

```text
runtime/memory/memory_candidate_retriever.py

tests/runtime/test_memory_candidate_retriever.py
```

 - 修改

```text
runtime/memory/memory_retriever.py

tests/runtime/test_memory_retriever.py
```

 - 删除

如果当前存在： `KeywordMemoryRetriever` 这个 Lesson9 具体实现，则删除它，

由： `DefaultMemoryRetriever` 取代。

### Lesson 11 最终结论

建立以下边界：

```text
                Retrieval
                   │
          ┌────────┴────────┐
          ↓                 ↓
       Recall             Ranking
          │                 │
CandidateRetriever       Ranker
          │                 │
          ↓                 ↓
     Candidates          Scores
          │                 │
          └────────┬────────┘
                   ↓
                  Top-K
```

**CandidateRetriever**:

> “哪些 Memory 值得进入候选集？”

**Ranker**:

> “候选集中哪些 Memory 更值得进入 Context？”


## Lesson 12: Memory Query

当前的DefaultMemoryRetriever流程大致为：

```text
memories = store.read(...)

candidates = candidate_retriever.retrieve(
    memories,
    query,
)
```

如果Store中数据量极大：

```text
MemoryStore
    ↓
读取 1,000,000 条
    ↓
Python
    ↓
KeywordMemoryCandidateRetriever
    ↓
筛选
```

合理的架构应该为：

```text
MemoryRuntime
      ↓
MemoryRetriever
      ↓
CandidateRetriever
      ↓
MemoryStore Query
      ↓
数据库 / Vector DB / Search Engine
```

目标为：

> CandidateRetriever 决定“我要找什么”，Store 决定“如何高效地从持久化数据中找到它”。

但是不能扩展 `read()` 方法。否则：

```text
read(
    scope=...,
    query=...,
    source=...,
    created_after=...,
    created_before=...,
    importance_gte=...,
    ...
)
```

会成为 God Method (上帝方法)。

### Lesson 12 核心结构

```text
MemoryStore
    │
    ├── read()
    ├── write()
    ├── delete()
    │
    └── query()
          ↑
          │
      MemoryQuery
```

新增 `MemoryQuery`：

> “我希望 Store 根据哪些条件寻找 Memory。”

### Lesson 12 架构

```text
                 MemoryRuntime
                       │
                       │ resolve()
                       ↓
                 MemoryScope[]
                       │
                       │ scope
                       ↓
                  MemoryStore
                       │
              ┌────────┴────────┐
              │                 │
            read()           query()
                                │
                         MemoryQuery
                                │
                                ↓
                           Filtered
                           Memories
```


## Lesson 13：把 Candidate Retrieval 真正接入 MemoryStore

要解决的问题：

> 当 Agent 真正提出一个“记忆检索请求”时，Memory Runtime 如何把 Query、Candidate Retrieval 
> 
> 和 Ranking 组织成一个完整的 Retrieval Pipeline？

从`Storage Query` 向 `Memory Retrieval` 演进。

### 问题分析

Lesson 12中引入`MemoryQuery` 解决的是：

> 哪些Memory 可以进入候选集？

但是Agent的真实需求通常不是： `“给我 source=reflection 且 importance>=0.7 的 Memory。”`

而是： `“帮我找和 NVIDIA 风险分析相关的、比较重要的历史记忆。”`

所以，存在以下3层：

**第一层：Filtering**

`MemoryQuery` 回答：

> 哪些 Memory 满足结构化约束？

**第二层：Retrieval**

`query = "NVIDIA risk analysis"` 回答：

> 哪些 Memory 与当前查询最相关？

然后才是：

**第三层：Ranking**

`MemoryRanker` 回答：

> 在候选结果中，哪些应该排在前面？

### 当前代码分析

Lesson 12加入的`MemoryQuery`使得Store能够进行结构化查询。

```python
MemoryQuery(
    source=...,
    min_importance=...,
    created_after=...,
    created_before=...,
    include_expired=...,
    limit=...,
)
```

Lesson 10/11 实现的`Retriever`能够：

```text
Candidate Retrieval
        ↓
Ranking
        ↓
Top-K
```

但是两者没有结合。

### Lesson 13 的职责边界

建立以下边界： `MemoryStore -> 结构化过滤`，例如：

```text
source
importance
created_at
expiration
```

而： `MemoryCandidateRetriever -> 内容相关性召回`， 例如： “NVIDIA”。

然后： `MemoryRanker -> 排序`， 例如：

```text
importance
recency
hybrid score
```

完整职责：

```text
  MemoryRuntime
        │
        ↓
  MemoryStore
        │
 Structured Filter
        │
        ↓
 Candidate Retriever
        │
  Semantic / Keyword
        │
        ↓
    Ranker
        │
        ↓
      Top-K
```

### 代码修改

#### 修改 MemoryRuntime

当前实际代码：

```python
async def query(
    self,
    query: str,
    runtime_context: RuntimeContext,
    limit: int = 10,
)
```

我们保留这个 API，同时增加：

`memory_query: MemoryQuery | None = None`

最终：

```python
async def query(
    self,
    query: str,
    runtime_context: RuntimeContext,
    limit: int = 10,
    memory_query: MemoryQuery | None = None,
)
```
这样不会破坏现有代码。

调用方式：

```python
await runtime.query(
    "NVIDIA",
    context,
)
```

仍然有效。

而新的调用：
```python
await runtime.query(
    "NVIDIA",
    context,
    memory_query=MemoryQuery(
        min_importance=0.7,
    ),
)
```
就可以表达：

> 找与 NVIDIA 相关，并且 importance >= 0.7 的 Memory。

本课先统一规则：

> 跨 Scope Retrieval 时，Store Query 不执行最终 limit；最终 limit 由 Retriever 在全局候选集上执行。

**不能直接删除 `MemoryQuery.limit`** 因为他对于single-scope Store query 仍然有意义：

```text
MemoryStore.query()
    ↓
单 Scope 查询
    ↓
可以使用 limit


MemoryRuntime.query()
    ↓
多 Scope Retrieval
    ↓
暂时关闭 Store-level limit
    ↓
全局 Retriever limit
```

#### 最终架构

```text
                         MemoryRuntime
                              │
                 ┌────────────┴────────────┐
                 │                         │
              query()                query_scope()
                 │                         │
          ScopeResolver              Explicit Scope
                 │                         │
          Multiple Scopes            One Scope
                 │                         │
                 └────────────┬────────────┘
                              ↓
                       MemoryStore.query()
                              ↓
                       Structured Filter
                              ↓
                         Candidates
                              ↓
                    MemoryCandidateRetriever
                              ↓
                           Ranker
                              ↓
                            Top-K
```


## Lesson 14: Memory Write Semantics：从“存进去”到“为什么应该存”

本节目标：

> 建立 Memory Write Boundary

明确区分：

```text
Memory Creation
        ↓
Memory Runtime
        ↓
Memory Store
```

避免让Agent/Workflow 直接操作Store。

### write() 和 remember() 的职责

 - `write()`: 接受已经构造好的MemoryItem，保存在Store中。
 - `remember()`：负责构造MemoryItem。

更准确的说法：

> Agent 决定把某个信息作为长期记忆保存。

但是不负责决定是否应该记住，这个决策由Reflection / Memory Policy 完成。

### 未来架构

```text
Agent / Reflection
        │
        │ candidate information
        ↓
Memory Policy
        │
        │ should remember?
        ↓
MemoryRuntime.remember()
        │
        ↓
MemoryItem
        │
        ↓
MemoryRuntime.write()
        │
        ↓
MemoryStore
```

### 当前 Memory System 结构

```text
                    Agent
                      │
                      ▼
               ┌──────────────┐
               │ MemoryRuntime│
               └──────────────┘
                  │    │
        ┌─────────┘    └──────────────┐
        ▼                             ▼
 Access Policy                  Scope Resolver
                                      │
                         ┌────────────┴────────────┐
                         ▼                         ▼
                    Primary Scope            Other Scopes
                         │                         │
                         ▼                         ▼
                       Write                    Read/Query
                         │
                         ▼
                  ┌─────────────┐
                  │ MemoryStore │
                  └─────────────┘
                         │
                         ▼
                 Candidate Retrieval
                         │
                         ▼
                       Ranker
                         │
                         ▼
                    Final Memory
```


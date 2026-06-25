# Phase 6: Reflection Runtime

---

## Step 1: 需求分析

为什么需要Reflection？

因为**Agent会犯错**，如果没有Reflection会造成：

 - 无限循环
 - 重复犯错
 - 无法总结失败原因

### Reflection 是什么？

> Reflection = 对执行结果进行元分析（Meta Analysis），产生指导下一轮规划的信息。

输入： `Observation`

输出： `Reflection`

形成 Self-correction Loop：

```text
Code
↓
Execute
↓
Fail
↓
Reflect
↓
Replan
↓
Code
```

Reflection 本质上不是 `Action` 也不是 `Tool`, 而是 `Agent`。

Action是面向外部世界的，改变环境或获取环境信息。而Reflection的作用对象是Agent自己。

Tool是 `input->execute->output`,近似Function，而Reflection更像mini agent，因为内部可能是 `LLM->分析->结构化结果`。

### Reflection 的边界

当前阶段，Reflection暂时属于Agent Runtime。未来会上移到 Workflow Runtime。

### Reflection 的领域模型

我们现在已经可以抽象出：

```text
CodeAgent
│
├── Planner
├── ActionExecutor
└── CriticAgent
         │
         ↓
    Reflection
```

数据流：

```text
Observation
↓
CriticAgent
↓
Reflection
↓
CodeAgent
↓
Planner
```

Reflection 应该成为新的 Domain Object。

而不是： str

类似：

```python
Reflection(
    summary=...
    suggestions=[...]
)
```

这样未来才能支持：

```text
Checkpoint
Memory
Replay
Long-term Learning
Multi-Agent Review
```

## Step 2: 领域建模（Domain Modeling）

> 阶段目标： 找出 Reflection Runtime 的核心领域对象和边界，收敛出 Version1 最小模型。

### Reflection Runtime 的职责

它解决的问题只有一个：

```text
失败
↓
分析失败
↓
形成经验
↓
指导下一轮规划
```

因此Reflection Runtime 不负责：

```text
执行 Tool
保存 Checkpoint
管理 Context
事件发布
长期记忆
```

只负责：

```text
Observation
↓
CriticAgent
↓
Reflection
```

讨论部分略过。

### 最终领域模型（Phase6 Version1）

```text
ObservationHistory
        ↓
   CriticAgent
        ↓
    Reflection
        ↓
ReflectionState
        ↓
ContextState
        ↓
Planner
```

结构：

```text
CodeAgent
│
├── Planner
├── ActionExecutor
├── Observation History
│
└── CriticAgent
        │
        ↓
    Reflection
        ↓
 ReflectionState
```

形成：

```text
Code
↓
Fail
↓
Critic
↓
Reflection
↓
Replan
↓
Code
```

### Step2 的核心共识

✓ Critic 输入是 Observation History : 不是单个 Observation。

✓ Reflection 是 Domain Object : 不是字符串。

✓ Reflection 是历史列表 : 不是 current_reflection。

✓ ReflectionState 属于 ContextState : 支持未来 Checkpoint。

✓ CriticAgent 不引入 BaseAgent : 保持独立。

✓ Reflection 默认 ON_FAILURE : 避免过度调用。

✓ 不引入 ReflectionManager : 保持最小模型。

## Step 3: 架构设计（Architecture Design）

> 阶段目标： 决定 Reflection Runtime 的目录结构、依赖方向和调用链。

讨论过程省略。

**Version1 架构目录：**

```text
agentos/

reflection/

    critic_agent.py
    reflection.py
    reflection_state.py
```

依赖关系：

```text
CodeAgent
    │
    ├──── Planner
    ├──── ActionExecutor
    │
    └──── CriticAgent
                │
                ↓
            Reflection
                │
                ↓
        ReflectionState
                │
                ↓
           ContextState
```

调用链：

```text
Task
↓
Planner
↓
Action
↓
ActionExecutor
↓
Observation

success
↓
continue

failure
↓
CriticAgent
↓
Reflection
↓
ReflectionState
↓
ContextState
↓
Planner
↓
Action
```

形成：

```text
CODE
↓
TEST
↓
FAIL
↓
REFLECT
↓
REPLAN
↓
CODE
```

### Step3 的核心共识
✓ 建立 reflection/ 独立目录 而不是放入 agents。

✓ CodeAgent 调用 CriticAgent 暂不上移到 Workflow。

✓ Reflection 进入 ContextState 供 Planner 使用。

✓ Reflection 只影响 Planner 不影响 Tool Runtime。

✓ CodeAgent 持有循环控制权 Critic 不控制 Loop。

✓ 不引入 ReflectionExecutor
✓ 不引入 ReflectionWorkflow
✓ Reflection Runtime 保持最小闭环

## Step 4: 接口设计（Interface Design）

> 阶段目标： 定义 Version1 可编码 API。

讨论部分略过。

**Version1 接口全景**

**Reflection**

```python
class Reflection(BaseModel):

    summary: str

    suggestions: list[str]
```

**ReflectionState**

```python
class ReflectionState(BaseModel):

    reflections: list[Reflection]
```

**CriticAgent**

```python
class CriticAgent:

    async def reflect(
        self,
        observations: list[Observation]
    ) -> Reflection:
        ...
```

**ContextState**

新增：`reflection_state: ReflectionState`

**Planner**

保持：

```python
async def plan(
    task,
    context_state
) -> Action
```

不修改。

**CodeAgent**

内部：

```python
observation_history = []

while True:

    action = planner.plan()

    observation = executor.execute()

    observations.append(observation)

    if observation.failed:
        reflection = critic.reflect(
            observations
        )

        context_state.reflection_state.reflections_state.append(
            reflection
        )
```

### 核心共识

✓ Critic 输入：`list[Observation]`

✓ Critic 输出： `Reflection`

✓ ReflectionState 保存历史

✓ Planner 接口保持不变

✓ TaskResult 接口保持不变

✓ Observation History 由 CodeAgent 维护

✓ Critic 不修改状态

✓ CodeAgent 更新 ReflectionState

✓ Critic 与 Planner 共用 LLMProvider  但不共享 Planner。

## Step 5: Data Model Design

> 阶段目标： 收敛出 Version1 最小数据结构，并避免为了未来而过度设计。

**Version1 数据模型最终收敛**

**reflection.py**

```python
class Reflection(BaseModel):

    summary: str

    suggestions: list[str]
```

**reflection_state.py**

```python
class ReflectionState(BaseModel):

    reflections: list[Reflection] = Field(
        default_factory=list
    )
```

**context_state.py**

新增：

reflection_state: ReflectionState

没有：

```text
id
timestamp
error_type
confidence
priority
current_reflection
max_reflections
ReflectionManager
```

全部属于未来阶段。
# Phase 7: Checkpoint

---

## Step 1: 需求分析

### Checkpoint是什么？

> Agent Runtime 在某一时刻的完整可序列化快照（Snapshot）。

例如：

当前执行到：

```text
step=5

历史：
tool1
tool2
tool3

reflection=1

workspace:
file_a.py

last_action:
search_code

等待 planner 下一步
```

突然 `进程退出/机器重启/pod被杀掉` 故障排除后不需要重新执行 `tool1 tool2 tool3`，而是从 `step=5` 开始重新执行。

### Checkpoint保存什么？

**LoopState**

```python
class LoopState(BaseModel):
    step_count: int
    observation_history: list[Observation]
    reflection_count: int
    last_action: Action | None
```

这些属于Loop状态，必须保存。

**ContextState**

```python
ContextState(
    history_state
    scratchpad_state
    memory_state
    workspace_state
    variable_state
    reflection_state
)
```

因为Planner Prompt来自 `ContextState`，所以必须保存。

**TaskRequest**

```python
TaskRequest(
    task_id="xxx",
    user_input="实现 quick sort"
)
```

Agent需要知道最初的任务是什么，所以必须保存。

**Agent Runtime Config**

例如：`max_steps`、`max_reflections`，这些属于运行配置，通常为外部注入，恢复是重新注入，不需要保存。

## Step 2: 领域建模

### Checkpoint的定性

Checkpoint表示某一时刻Runtime的快照，因此**Checkpoint本身是Value Object**，而不是Entity。

Checkpoint没有复杂业务，只是持久化，因此只有Repository，没有Manager。

### 得出的领域模型
**Value Object**

`Checkpoint`

内部：

```text
task_request
loop_state
context_state
version
```

**Repository**

`CheckpointStore`

负责：

```python
save()

load()

delete()
```

**状态流**

```text
ActionExecutor
    ↓
ToolExecutor
    ↓
Tool

ToolResult
(output + patch)

    ↓

ActionExecutor

    ↓

Patch Apply

    ↓

ContextState

    ↓

CheckpointStore.save()

    ↓

Observation

    ↓

Planner
```

**Restore**

统一入口：

```python
run(
    task_request,
    context_state,
    loop_state
)
```

事实上，`run()`和`resume()`是存在的但是只有一个Loop，就是`run(task_request, context_state, loop_state)`或者：`self._run_loop()`这种形式。

```text
run()    → create state → run loop
resume() → restore state → run loop
```

## Step 3: 架构设计

### 关键架构决策：

---

**决策1：谁拥有 LoopState？**

✔ 正确答案：

`RuntimeOrchestrator`

❌ 错误答案：
 - CodeAgent
 - LoopEngine
 - 外部调用方

---

**决策2：LoopEngine 是否持有状态？**

❌ 不持有任何状态
`LoopEngine(state) ❌`

✔ 正确：

`LoopEngine.run(state)`

---

**决策3：Checkpoint 是谁生成的？**

**✔ RuntimeOrchestrator**

原因：

**Checkpoint = Runtime State Snapshot**

只有 Runtime 才知道“完整状态”。

---

**决策4：Checkpoint 保存点在哪里？**

我们收敛一个非常重要结论：

**✔ Save 时机 = Loop Iteration Boundary**
`Action → Tool → Observation → Patch → Reflection → Save`

原因：

> 必须保证状态一致性（consistent state）

### 完整架构图：

```text
                 ┌──────────────────────┐
                 │      CodeAgent       │
                 │  run / resume API    │
                 └─────────┬────────────┘
                           │
                           ▼
            ┌────────────────────────────┐
            │ RuntimeOrchestrator        │
            │                            │
            │ - ContextState             │
            │ - LoopState               │
            │ - Checkpoint logic        │
            └─────────┬──────────────────┘
                      │
                      ▼
            ┌────────────────────────────┐
            │       LoopEngine           │
            │  (pure execution loop)     │
            │                            │
            │ Planner → Action → Tool    │
            │ → Observation → Reflection │
            └─────────┬──────────────────┘
                      │
          ┌───────────┴───────────┐
          ▼                       ▼
 ToolExecutor              ReflectionEngine
```

## Step 4: 接口设计

> 定义外部可以调用什么，不能调用什么

必须保证： `LoopState / ContextState / RuntimeOrchestrator 永远不暴露给用户`

### 最终对外API：

**CodeAgent API**:

```python
class CodeAgent:

    async def run(self, task: TaskRequest) -> TaskResult:
        ...

    async def resume(self, checkpoint: Checkpoint) -> TaskResult:
        ...
```

**关键点**：

**run()**：新任务执行

```text
输入： TaskRequest
输出： TaskResult
```

**resume()**: 恢复执行

```text
输入： Checkpoint
输出： TaskResult
```

**以下为禁止暴露的API**:

```text
run(task, context_state, loop_state) ❌
resume(task, loop_state) ❌
set_loop_state() ❌
get_context_state() ❌
```

因为： **外部不应该参与 Runtime 状态构造**

### Checkpoint API 设计：

**✔ Checkpoint 只作为输入，不作为操作对象**

外部允许：

```python
checkpoint = store.load(task_id)
agent.resume(checkpoint)
```

❌ 不允许：

```python
checkpoint.update()
checkpoint.apply_patch()
checkpoint.step_forward()
```

Checkpoint 必须是： **immutable snapshot**

### CheckpointStore API 设计：

这一层是唯一“状态持久化接口”：

```python
class CheckpointStore:

    async def save(self, checkpoint: Checkpoint) -> str:
        ...

    async def load(self, checkpoint_id: str) -> Checkpoint:
        ...
```

关键设计原则

```text
CheckpointStore ≠ Runtime
CheckpointStore ≠ Agent
CheckpointStore = IO Layer
```

### Checkpoint Save API设计：

**✔ 方案：完全自动 save（推荐）**

外部 API：

* 不存在 save()
* 不存在 checkpoint()

---

**Save 触发点（内部）**

```text
ActionExecutor 完成
→ Observation
→ Patch Apply
→ RuntimeOrchestrator.save_checkpoint()
```

---

**为什么不能暴露 save()？**

如果暴露：

`agent.save_checkpoint()`

会导致：

* 用户控制 checkpoint 粒度
* Runtime 不一致
* 恢复不可预测

> 原则： checkpoint不是用户行为。是Runtime的“副产品”

### Resume API 设计：

**✔ resume(checkpoint)**

```text
恢复 Runtime 状态
然后进入同一个 LoopEngine
```

**❌ resume 不允许做：**

* 重新初始化 Runtime
* 重新创建 LoopState
* 跳过历史步骤

**resume 内部行为：**

```text
RuntimeOrchestrator.restore(checkpoint)

→ set context_state
→ set loop_state
→ set task_request

→ call _run_loop()
```

### 完整 API 结构（Phase7 v1）

**CodeAgent（唯一外部接口）**
```text
CodeAgent
├── run(task)
├── resume(checkpoint)
└── (optional) inspect_checkpoint()
```

**CheckpointStore（基础设施）**

```text
CheckpointStore
├── save(checkpoint)
└── load(id)
```

**Checkpoint（Value Object）**

```text
Checkpoint
├── task_request
├── loop_state
├── context_state
└── version
```

### 关键架构结论

1. API 层只有两个动作 `run /resume`

2. Runtime 状态完全封闭
 - LoopState ❌ 外部不可见
 - ContextState ❌ 外部不可见

3. Checkpoint 是输入，不是操作对象

Checkpoint = immutable snapshot

4. Save 是自动行为（Runtime owned）

不是 API
不是用户行为

5. Loop Engine 完全统一

`run() == resume() == same loop`

**总结一句话**：

> Phase7 的 API 设计本质是：把 Runtime 复杂性封装在 Orchestrator 内，只暴露“开始执行”和“恢复执行”两个语义动作。

## Step 5: 数据模型设计

> 阶段目标： Runtime State 如何在“运行态 ↔ 持久态”之间无损转换

### 设计目标：

1. 可序列化（Serializable）
2. 可版本化（Versioned）
3. 可恢复一致性（Deterministic Restore）

### 核心数据结构总览

四个核心模型：

```text
Checkpoint
 ├── TaskRequest
 ├── LoopState
 ├── ContextState
 └── version
```

### Checkpoint 模型

**✔ Checkpoint（顶层）**

```python
class Checkpoint(BaseModel):
    version: int
    task_request: TaskRequest
    loop_state: LoopState
    context_state: ContextState
    created_at: datetime
```

**关键点**
✔ version 必须存在

原因：

>未来 LoopState / ContextState 会演进

必须支持：

>v1 → v2 migration

### LoopState 模型(执行状态)

```python
class LoopState(BaseModel):
    step_count: int

    observation_history: list[Observation]

    reflection_count: int

    last_action: Action | None

    status: Literal["running", "waiting", "failed", "done"]
```

**设计关键点**

1. observation_history 必须完整保存

原因： Planner 决策依赖 history 不能截断。

2. last_action 必须存在

原因： 恢复时必须知道“刚执行了什么” 否则无法推导下一步状态。

3. status 必须显式化

避免： 隐式 while True 状态

### ContextState 模型

ContextState 是“语义记忆”，必须拆 Channel：

```python
class ContextState(BaseModel):

    history_state: HistoryState
    scratchpad_state: ScratchpadState
    memory_state: MemoryState
    workspace_state: WorkspaceState
    variable_state: VariableState
    reflection_state: ReflectionState
```

**关键设计原则**

✔ ContextState 是“纯数据容器”

不能包含：

* 函数
* runtime reference
* loop control

**为什么必须分 Channel？**

因为： **Planner Prompt = structured context**

例如：

* History → 推理依据
* Workspace → 当前代码状态
* Reflection → 失败经验

这些必须隔离，否则： context becomes entangled memory

### Observation 模型(执行轨迹)

Observation 是 Loop 的“记录点”：

```python
class Observation(BaseModel):
    step_id: int

    action: Action

    tool_result: ToolResult | None

    reflection: Reflection | None

    timestamp: datetime
```

**设计关键点**

✔ Observation 是不可变日志 append-only

不能修改历史。

### Action/ToolResult 模型

**Action（统一动作模型）**

```python
class Action(BaseModel):
    type: Literal["tool", "finish"]

    tool_name: str | None = None
    arguments: dict | None = None

    answer: str | None = None
```

**ToolResult（执行结果）**

```python
class ToolResult(BaseModel):
    success: bool

    output: Any

    error: str | None = None

    patch: dict | None = None
```

**关键点（非常重要）**

✔ patch 只存在 ToolResult

`Tool → ToolResult → Context Apply`

Tool 本身不碰 Context。

### Patch 模型(Phase7 核心新增)

```python
class ContextPatch(BaseModel):

    workspace_patch: dict | None = None
    memory_patch: dict | None = None
    variable_patch: dict | None = None
```

**Patch 语义**

```text
Patch ≠ State

Patch = delta change
```
示例

```python
workspace_patch = {
    "main.py": "new content"
}
```

### Checkpoint 序列化策略

**✔ 统一 JSON serialization（Phase7 v1）**

`pydantic v2 → model_dump()`

Checkpoint：

`checkpoint.model_dump()`

❌ 不使用：

* pickle
* binary snapshot
* ORM object dump

原因是未来需要：

- version migration
- partial restore
- debugging

### 版本演进设计：

**Checkpoint version**

`version: int`

未来演进可能：

v1

```text
LoopState + ContextState + Task
```

v2（未来）

```text
+ token_usage
+ tool_trace
+ cost tracking
```

v3（更远）

```text
+ multi-agent graph state
```

### Step5 核心结论（非常重要）

1. Checkpoint 是纯数据结构

 - no behavior
 - no logic

2. ContextState 是语义容器

structured memory

3. LoopState 是执行控制状态

runtime control plane

4. Observation 是不可变日志

append-only trace

5. Patch 是 Phase7 核心新增能力

state mutation abstraction layer

### 总结一句话

> Phase7 的数据模型核心是：把“执行状态（Loop）”“语义状态（Context）”“变更（Patch）”“执行轨迹（Observation）”彻底分离，从而保证 Checkpoint 可恢复且可演进。

## Step 6: 
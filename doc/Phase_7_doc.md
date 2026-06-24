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


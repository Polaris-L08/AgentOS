# Phase5：Single Agent Runtime

---

# Step1：需求分析

这一阶段第一次开始构建真正的 Agent Loop。

先不写代码，先回答几个核心问题：

---

## 一、Single Agent Runtime 要解决什么问题？

Phase1~Phase4 已经有：

```text
Runtime
Workflow
Tool Runtime
Context Runtime
```

但是实际上还没有 Agent。

目前的执行链是：

```text
Task
↓
直接执行
↓
Result
```

缺少：

```text
思考
→ 决策
→ 调用工具
→ 观察结果
→ 再思考
→ 结束
```

也就是：

```text
Reason + Act
```

循环。

因此需要引入：

```text
Planner
Action
Observation
Loop
```

形成：

```text
Task
↓
Planner
↓
Action
↓
Tool
↓
Observation
↓
Planner
↓
...
↓
Finish
```

这就是 Single Agent Runtime。

---

## 二、Single Agent 的职责是什么？

Single Agent 负责：

### 1. 理解任务

例如：

```text
读取 foo.py
修复语法错误
```

---

### 2. 决定下一步

例如：

```text
Action(
    type="tool",
    tool_name="read_file"
)
```

---

### 3. 观察执行结果

ToolResult：

```python
success=True
output=...
```

---

### 4. 更新 Context

包括：

```text
history
scratchpad
memory
variables
```

---

### 5. 判断结束

产生：

```python
FinishAction(
    answer="修复完成"
)
```

---

因此：

Agent 的职责：

```text
Think
Observe
Decide
Finish
```

而不是：

```text
执行工具
管理生命周期
保存状态
```

这些职责属于别的模块。

---

## 三、Planner 和 Agent 的边界

这是整个 Runtime 最重要的一次边界划分。

很多框架：

```text
Agent = Planner
```

例如：

```python
agent.run()
```

内部直接：

```python
LLM
↓
Tool
↓
LLM
↓
Tool
```

全部耦合。

我们不这样设计。

我们分离：

**Planner**

负责：

```text
Thinking
```

输入：

```python
Task
Context
Observation
```

输出：

```python
Action
```

即：

```python
plan()
```

---

**Agent**

负责：

```text
Loop
```

即：

```python
while:
    action = planner.plan()

    if tool:
        execute()

    if finish:
        break
```

Agent 不产生 Action。

Planner 产生 Action。

因此：

```text
Agent
    ↓
Planner
    ↓
Action
```

而不是：

```text
Agent(LLM)
```

这样未来：

```text
CodePlanner
ResearchPlanner
ReviewerPlanner
```

可以替换。

---

## 四、为什么现在必须引入 Provider？

目前所有推理能力都来自：

```python
planner.plan()
```

里面一定会调用：

```python
OpenAI
Claude
Gemini
Ollama
```

如果直接：

```python
from openai import OpenAI
```

那么未来：

```text
Planner
Reflection
MultiAgent
Summary
Memory
```

都会散落 SDK。

因此现在必须建立：

```text
providers/

    llm_provider.py
```

统一：

```python
generate()
```

后面：

```python
OpenAIProvider

AnthropicProvider

GeminiProvider

OllamaProvider
```

都实现同一接口。

这样：

```text
Planner
Critic
Reviewer
```

完全不知道底层模型。

形成：

```text
Planner
↓
LLMProvider
↓
OpenAI
```

而不是：

```text
Planner
↓
OpenAI SDK
```

---

## 五、Action 和 ToolRequest 是否等价？

答案：

> 不等价。

这是整个 Runtime 的关键边界。

**Action**

表示：

```text
Agent 的意图
```

例如：

```python
ReadFileAction()

WriteFileAction()

FinishAction()
```

属于：

```text
Agent Domain
```

---

**ToolRequest**

表示：

```text
调用 Tool ABI
```

属于：

```text
Tool Domain
```

例如：

```python
ToolRequest(
    tool_name="read_file",
    arguments={}
)
```

---

关系：

```text
Action
↓ translate
ToolRequest
↓
ToolExecutor
↓
ToolResult
↓
Observation
```

因此：

```text
Action ≠ ToolRequest
```

中间会存在：

```text
ActionExecutor
```

负责：

```text
Action
↓
ToolRequest
```

转换。

这样未来：

```python
AskUserAction

DelegateAction

WaitAction

FinishAction
```

根本不需要 Tool。

这是工业级 Runtime 必须保留的一层抽象。

---

## 六、Phase5 的最终目标

我们希望得到：

```text
Task
↓
CodeAgent.run()
↓
Loop
↓
Planner.plan()
↓
Action
↓
ActionExecutor
↓
ToolExecutor
↓
ToolResult
↓
Observation
↓
Context update
↓
Planner.plan()
↓
...
↓
FinishAction
↓
TaskResult
```

---

**Step1 的核心共识**

```text
Agent ≠ Planner
```

Agent 管循环。

Planner 管思考。

---

```text
Action ≠ ToolRequest
```

Action 是意图。

ToolRequest 是 ABI。

---

Provider 必须现在引入

避免 SDK 污染整个系统。

---

Agent 不执行 Tool

Agent 调用：

```text
ActionExecutor
↓
ToolExecutor
```

---

Single Agent 的本质

```text
Observe
↓
Think
↓
Act
↓
Observe
```

形成闭环。

---

# Step2: 领域建模（Domain Model）

这阶段最容易犯的错误是：

> 看到一个概念就定义一个class

导致大量无意义对象：

```text
Agent
Planner
Executor
ToolAgent
ActionAgent
MemoryAgent
ObservationAgent
...
```

因此：Step2的目标是：

> 先做领域建模（Domain Model），确定什么是 Entity、Value Object、State、Service。

## 一、 领域对象分类

先画Single Agent Runtime的数据流：

```text
Task
 ↓
CodeAgent
 ↓
Planner
 ↓
Action
 ↓
ActionExecutor
 ↓
ToolExecutor
 ↓
ToolResult
 ↓
Observation
 ↓
Planner
 ...
 ↓
Finish
 ↓
TaskResult
```

其中有状态的对象很少，大多是： `输入-> 处理 -> 输出`。

候选对象：

```text
Task
TaskResult

Action
Observation

CodeAgent
Planner

ActionExecutor

LLMProvider

LoopState
```

## 二、 Entity(实体)

Entity的特点：

 - 具有生命周期
 - 有 identity
 - 会不断变化

**Task**

```python
Task(
    id,
    objective,
    metadata
)
```

生命周期：

```text
创建
↓
执行
↓
完成
```

有唯一id。

此外，**Agent**也属于Entity。

## 三、 Value Object(值对象)

特点：

 - 不可变
 - 无identity
 - 只描述数据

**Action**

例如：

```python
ReadFileAction(
    path="foo.py"
)
```

或者：

```python
FinishAction(
    answer="done"
)
```

没有 identity。

产生之后不会修改。

属于： **Value Object**

**Observation**

例如：

```python
Observation(
    success=True,
    content="..."
)
```

也是不可变。

属于： **Value Object**

**TaskResult**

```python
TaskResult(
    success=True,
    answer="..."
)
```

属于： **Value Object**



##  四、 State(状态)

**State** 用来保存循环过程中的动态状态。

这是 Phase5 新出现的状态对象。

我们需要：

```python
LoopState
```

记录：

```python
step_count

last_action

last_observation

finished
```

例如：

```python
LoopState(
    step_count=3,
    last_action=...
    last_observation=...
    finished=False
)
```

属于： **State**

注意：

不要把：

```text
history
memory
workspace
variables
```

放进来。

因为 Phase4 已经有：`AgentContext`保存这些状态。

LoopState 只保存：**当前循环状态**

职责非常小。

## 五、 Domain Service(服务)

**Planner**

职责：

```text
思考
```

输入：

```text
Task
AgentContext
Observation
```

输出：

```text
Action
```

无状态。

因此是 **Domain Service**, 而不是 Entity。

**ActionExecutor**

职责：

```text
Action
↓
ToolRequest
↓
ToolExecutor
↓
Observation
```

不保存状态。

因此：**Domain Service**

**LLMProvider**

职责：

```text
调用模型
```

也是： **Domain Service**


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



## 六、 不应该出现的对象

很多框架会出现：

**ObservationManager**

不需要。

Observation 是 VO。

没有生命周期。

**ActionManager**

不需要。

Action 是 VO。

不需要管理。

**TaskManager**

不需要。

当前没有任务队列。

**PlannerState**

不需要。

Planner 应该是 Stateless。

**AgentContext**

不需要。

已有：

`AgentContext + LoopState`

足够。

**ToolAgent**

不需要。

ToolExecutor 已存在。

## 七、 CodeAgent

CodeAgent 是聚合根（Aggregate Root）。负责协调：

```text
Task

Planner

ActionExecutor

Context

LoopState
```

不负责：

```text
Tool 执行细节

LLM 调用细节

Context 实现细节
```

结构：

```text
CodeAgent
│
├── Planner
├── ActionExecutor
├── AgentContext
└── LoopState
```

形成：

```text
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
Observation
↓
AgentContext
```

---

# Step3: 架构设计(Architecture)

本阶段的目标是：

> 固定依赖方向（Dependency Direction）

## 一、确定运行链路

Single Agent Runtime 的执行过程：

```text
Task
↓
CodeAgent.run()
↓
Planner.plan()
↓
Action
↓
ActionExecutor.execute()
↓
ToolExecutor.execute()
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

## 二、确定依赖方向

> 原则： 上层协调，下层执行

因此：

```text
CodeAgent
    ↓
Planner
ActionExecutor
    ↓
ToolExecutor
LLMProvider
```

`CodeAgent` 是协调者（Orchestrator）。不允许反向依赖。

## 三、目录结构设计

新增：

```text
agentos/

core/

agents/

planner/

actions/

providers/

tests/
```

很多项目会：

```text
agents/
    planner.py
    action.py
```

但后期加入： `CriticPlanner`、 `ReviewerPlanner`、 `ResearchPlanner`后，会越来越混乱，因此提前拆开。

## 四、 agents/

只放**聚合根**， 例如：

```text
agents/

    base_agent.py

    code_agent.py
```

职责： 

```text
Loop
Coordination
Lifecycle
```

不负责：

```text
Thinking
Tool Execution
LLM
```

因此： CodeAgent 很薄。

核心循环：

```python
while True:
    action = planner.plan()

    observation = action_executor.execute()

    context.update()

    if finish:
        break
```

## 五、 planner/

负责： **Agent 的思考能力**。

目录：

```text
planner/

    base_planner.py

    code_planner.py
```

职责： 输入：

```text
Task
Context
Observation
```

输出： `Action`

只有：

`plan()`

不执行 Tool。 不维护状态。 不保存历史。 Stateless。

未来：

```python
critic_planner.py
reviewer_planner.py
research_planner.py
```

都会在这里。

## 六、 actions/

这一层非常关键。 很多框架没有这一层。 我们必须保留。

目录：

```text
actions/

    action.py

    observation.py

    action_executor.py
```

形成：

```text
Action
↓
ActionExecutor
↓
ToolRequest
↓
ToolExecutor
↓
ToolResult
↓
Observation
```

这一层把： **Agent Domain** 与 **Tool Domain**隔离开。

否则：

```text
Planner
↓
ToolRequest
```

会导致 Agent 和 Tool 耦合。

未来：

```text
AskUserAction

WaitAction

DelegateAction
```

根本不是 Tool。 所以 Action 必须独立。

## 七、 providers/

本阶段开始引入LLM，为规范LLM SDK的接口，我们创建了 providers 目录。

依赖：

```text
Planner
↓
LLMProvider
↓
OpenAI SDK
```

而不是：

```text
Planner
↓
OpenAI SDK
```

未来增加：

```text
anthropic_provider.py
gemini_provider.py
ollama_provider.py
```

不影响上层的Planner。

## 八、 LoopState的位置

因为：

LoopState 属于 Agent Loop。

建议：

```text
agents/

    loop_state.py
```

结构：

```text
LoopState
step_count
last_action
last_observation
finished
```

只保存**循环状态**。

不保存：

```text
history
memory
workspace
```

这些已经属于： AgentContext

## 九、 Task 的位置

建议：

```text
core/

    task.py

    task_result.py
```

因为：Task 是整个 Runtime 的基础对象。

未来：

```text
Single Agent
Workflow
Multi-Agent
API
```

都会使用。

## 十、 依赖图

最终：
```text
                     Task
                      │
                      ▼
                CodeAgent
               /         \
              ▼           ▼
        CodePlanner    ActionExecutor
              │              │
              ▼              ▼
        LLMProvider      ToolExecutor
                              │
                              ▼
                         ToolRegistry
```

然后：

```text
ToolResult
↓
Observation
↓
Context Update
↓
CodePlanner
```

形成闭环。

## 十一、 哪些依赖禁止出现？

**Planner → ToolExecutor**

禁止。

Planner 只负责思考。

不知道工具存在。

---

**Planner → ToolRequest**

禁止。

否则 Tool ABI 泄漏。

---

**LLMProvider → Planner**

禁止。

Provider 是基础设施层。

不认识业务。

---

**ToolExecutor → AgentContext**

禁止。

Tool 不应修改 Context。

只能返回：

`ToolResult.patch`

由 Agent 决定是否应用。 这一点非常重要。

---

**ActionExecutor → Planner**

禁止。 执行层不能回调思考层。

---

**AgentContext → Agent**

禁止。

Context 是数据对象。 不能拥有 Agent。

## 十二、 最终共识

**Aggregate Root**

```text
CodeAgent
```

协调：

```text
Planner
ActionExecutor
Context
LoopState
```

---

**Thinking**

```text
planner/
```

---

**Acting**

```text
actions/
```

---

**LLM Infrastructure**

```text
providers/
```

---
**Runtime Kernel**

```text
core/
```

---

**单向依赖**

```text
CodeAgent
↓
Planner
↓
LLMProvider

CodeAgent
↓
ActionExecutor
↓
ToolExecutor
```

禁止横向依赖。

# Step4: 接口设计

前面的 Step2（领域模型）和 Step3（架构设计）实际上是在解决：

>谁负责什么，以及依赖关系如何。

Step4 的目标则是：

>固定 ABI（Application Binary Interface）

也就是： 各个组件之间如何通信

这一步结束后，后面的编码就不再需要频繁修改接口。

## 一、 确定 Runtime Loop

```text
Task
↓
CodeAgent.run()
↓
Planner.plan()
↓
Action
↓
ActionExecutor.execute()
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

因此需要定义接口的对象有：

```text
BaseAgent
BasePlanner
Action
Observation
ActionExecutor
LLMProvider
```

## 二、 BaseAgent

职责：

```text
管理循环
协调组件
返回 TaskResult
```

接口：

```python
class BaseAgent(ABC):

    @abstractmethod
    async def run(
        self,
        task: Task,
        context: AgentContext
    ) -> TaskResult:
        ...
```

输入：

```text
Task
AgentContext
```

输出： `TaskResult`

不暴露：

```python
step()
plan()
execute()
```

因为： 这些属于内部实现。

未来：

```text
CodeAgent
ResearchAgent
ReviewerAgent
```

都实现： `run()` 即可。

## 三、 Planner

Planner 是纯 Thinking Service。

核心原则：

>Planner 不知道 Tool。

输入：

```text
Task
Context
Observation
```

输出： `Action`

接口：

```text
class BasePlanner(ABC):

    @abstractmethod
    async def plan(
        self,
        task: Task,
        context: AgentContext,
        observation: Observation | None
    ) -> Action:
        ...
```

这里 `observation=None` 表示第一次进入循环。

例如：

第一次：

```python
plan(
    task,
    context,
    None
)
```

第二次：

```python
plan(
    task,
    context,
    observation
)
```

形成：

```text
Observe
↓
Think
↓
Act
```
循环。

## 四、 Action

Action 是 Value Object。

目前先不要设计：

```text
ReadFileAction
WriteFileAction
```

这种几十个子类。 会过度设计。

先抽象成：

```python
class ActionType(str, Enum):

    TOOL = "tool"

    FINISH = "finish"
```

对应：

```python
@dataclass(frozen=True)
class Action:

    type: ActionType

    content: dict[str, Any]
```

例如：

Tool：

```python
Action(
    type=TOOL,
    content={
        "tool_name":"read_file",
        "arguments":{
            "path":"foo.py"
        }
    }
)
```

Finish：

```python
Action(
    type=FINISH,
    content={
        "answer":"done"
    }
)
```


先使用：**Tagged Union** 而不是大量继承。 以后再拆。

## 五、 Observation

Observation 是： ToolResult 的 Agent Domain 表达。 不直接暴露： `ToolResult`

接口：

```python
@dataclass(frozen=True)
class Observation:

    success: bool

    content: str

    metadata: dict[str, Any] = field(
        default_factory=dict
    )
```

例如：

```python
Observation(
    success=True,
    content=file_content
)
```

或者：

```python
Observation(
    success=False,
    content="file not found"
)
```

这里刻意屏蔽： `patch` `tool_name`

因为： Planner 不应该知道 Tool ABI。

## 六、 ActionExecutor

这是 Agent Domain 和 Tool Domain 的桥。

输入： `Action`

输出： `Observation`

接口：

```python
class ActionExecutor:

    async def execute(
        self,
        action: Action,
        context: AgentContext
    ) -> Observation:
        ...
```

内部：

```text
Action
↓
ToolRequest
↓
ToolExecutor
↓
ToolResult
↓
Observation
```

但外部看不到。 这层非常关键。

未来：

```text
AskUserAction

WaitAction

DelegateAction
```

都可以在这里实现。

## 七、 LLMProvider

统一模型调用。 接口：

```python
class LLMProvider(ABC):

    @abstractmethod
    async def generate(
        self,
        messages: list[dict]
    ) -> str:
        ...
```

后面再扩展 `tool_call`、`json_schema`、`stream`。

## 八、 CodePlanner

实现：

```python
class CodePlanner(BasePlanner):

    async def plan(
        self,
        task,
        context,
        observation
    ) -> Action:
        ...
```

内部：

```text
build prompt
↓
LLMProvider.generate()
↓
parse response
↓
Action
```

输出永远是： `Action`

不知道： `ToolExecutor` 存在。

## 九、 CodeAgent

内部循环：

```python
async def run():

    observation = None

    while True:

        action = planner.plan()

        if action.type == FINISH:

            return TaskResult()

        observation = action_executor.execute()

        context.apply_patch()
```

Agent 只协调。 不负责：`prompt`、`tool request`、`llm sdk`。

## 十、 LoopState 是否暴露？

不暴露。 属于 Agent 内部状态。

例如：

```python
@dataclass
class LoopState:

    step_count: int

    last_action: Action | None

    last_observation: Observation | None

    finished: bool
```

由`CodeAgent` 维护。 不进入： `Planner` `ActionExecutor`接口。

这样以后： Checkpoint 保存： `LoopState`即可恢复。

## 十一、 TaskResult

接口：

```python
@dataclass(frozen=True)
class TaskResult:

    success: bool

    answer: str

    metadata: dict[str, Any]
```

结束时：

```text
FinishAction
↓
TaskResult
```

## 十二、 最终调用关系

**Thinking Side**

```text
BasePlanner.plan(
    task,
    context,
    observation
)
→ Action
```

---

**Acting Side**
```text
ActionExecutor.execute(
    action,
    context
)
→ Observation
```

---

**Infrastructure**

```text
LLMProvider.generate(
    messages
)
→ str
```

---


**Runtime**

```text
CodeAgent.run(
    task,
    context
)
→ TaskResult
```

形成：
```text
             CodeAgent
            /         \
           ▼           ▼
      Planner      ActionExecutor
           │             │
           ▼             ▼
      LLMProvider    ToolExecutor
           ▲             │
            \           /
             Observation
```

# Step5: 数据模型设计（Data Model）

> 目标： 确定哪些对象使用 dataclass，哪些使用 Pydantic。

| 功能      | dataclass                      | Pydantic                      |
|---------|--------------------------------|-------------------------------|
| 自动生成方法  | ✅ __init__, __repr__, __eq__ 等 | ✅ 同左                          |
| 类型注解    | ✅ 仅作为提示                        | ✅ 运行时验证                       |
| 数据验证    | ❌ 无                            | ✅ 强大的验证器                      |
| 类型转换    | ❌ 无                            | ✅ 自动转换                        |
| JSON序列化 | ⚠️ 需手动实现                       | ✅ 内置支持(如`.model_dump_json()`) |
| 性能      | ⚡ 快（无验证开销）                     | 🐢 较慢（有验证开销）                  |
| 依赖      | ✅ 标准库                          | ⚠️ 需安装第三方库(pydantic-core)     |
| 适用场景    | 内部数据结构                         | 配置、API、外部数据                   |

最终共识:

**Entity**

```text
Task
```

---

**Value Object**

```text
Action

Observation

TaskResult

PromptMessage

LLMResponse
```

全部：

```python
@dataclass(frozen=True)
```

---

**State**

```text
LoopState
```

唯一可变对象：

```python
@dataclass
```

不使用

```python
BaseModel
```

作为 Runtime 内部模型。

---

**Action**

使用：

`ActionType + content(dict)`

而不是大量子类。

---

**Provider**

引入：

```python
PromptMessage

LLMResponse
```

避免：

```python
dict
str
```

污染接口。
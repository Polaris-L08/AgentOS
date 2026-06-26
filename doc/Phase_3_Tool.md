
# Phase3 Step1 — Tool System 本质重建（先纠正认知边界）

在进入设计前，需要先把一个关键点“工业级校正”：

## ❗ Tool ≠ function（这是当前最容易设计错的点）

在你的 AgentOS 体系中：

```text
Tool 不是函数封装
Tool 是一个“可执行能力单元（Execution Capability Unit）”
```

它必须同时具备：

* 输入契约（Input Schema）
* 执行语义（Execution Semantics）
* 上下文副作用模型（Context Mutation Policy）
* 执行边界（Timeout / Sandbox / IO限制）
* 可观测性（Tracing / Logging / Metadata）

---

# 1. Tool System 设计目标（重新收敛问题）

我们不做“工具集合”，而是做一个：

```text
Tool Execution Subsystem（TES）
```

它要解决的是：

## ✔ 核心问题拆解

### (1) 标准化执行接口

所有 Tool 必须统一执行模型：

```text
Tool.execute(input, context) → ToolResult
```

但这里的关键不是 signature，而是：

> execution contract must be deterministic at runtime layer

---

### (2) Tool 与 Context 的关系必须“受控耦合”

禁止：

```text
Tool 直接改 runtime state
Tool 直接访问 global state
Tool 自己决定 context structure
```

允许：

```text
Tool → Context Mutation Request → Runtime commit
```

---

### (3) Tool 必须可替换 / 可注册 / 可扩展

即：

```text
Registry = capability namespace
```

---

### (4) Tool 必须支持 execution isolation（未来扩展 sandbox）

虽然 Phase3 不实现 sandbox，但 ABI 必须预留：

```text
execution_mode:
    - local
    - subprocess
    - remote
    - sandbox
```

---

# 2. Tool ABI 设计（核心）

我们现在进入工业级定义。

---

## ✔ Tool 基础抽象（概念模型）

一个 Tool 在 AgentOS 中必须满足：

```text
Tool = {
    identity
    schema
    executor
    lifecycle
    policy
}
```

---

## ✔ 1. Tool Identity（工具身份）

```python
ToolId:
    name: str
    version: str
    namespace: str
```

### 为什么必须存在？

因为：

* Tool 是可升级的
* Tool 是可替换的
* Tool 需要 registry resolution

---

## ✔ 2. Tool Input Schema（结构契约）

不是 dict，而是：

```python
Pydantic / JSON Schema
```

例如：

```python
class ToolInput(BaseModel):
    query: str
    max_tokens: int = 512
```

关键原则：

> Tool input must be strictly typed, not dynamic dict

---

## ✔ 3. Tool Execution Contract（执行契约）

核心 ABI：

```python
Tool.execute(
    input: ToolInput,
    context: AgentContext
) -> ToolResult
```

但工业级版本必须补充：

```python
async Tool.execute(...)
```

---

## ✔ 4. ToolResult（统一输出模型）

必须标准化：

```python
class ToolResult:
    success: bool
    output: Any
    error: Optional[str]
    metadata: dict
    context_patch: Optional[dict]
```

### 关键设计点（非常重要）

#### ❗ Tool 不直接修改 Context

而是返回：

```text
context_patch
```

由 Runtime 决定是否 commit

---

## ✔ 5. Tool Policy（执行策略层）

这是很多系统缺失的部分。

```python
class ToolPolicy:
    timeout: int
    retry: int
    rate_limit: Optional[int]
    execution_mode: str
```

---

# 3. Tool vs Agent vs Workflow 边界（必须明确）

这是 Phase3 的关键认知收敛。

---

## ✔ Tool

```text
执行“原子能力”
```

例：

* read file
* run command
* search
* call API

---

## ✔ Agent

```text
决策 + 推理 + tool selection
```

---

## ✔ Workflow

```text
控制执行循环
```

---

## ✔ StateMachine

```text
约束状态转移
```

---

## ✔ Context

```text
唯一事实状态载体
```

---

# 4. Tool Execution Runtime（设计核心）

我们定义一个执行层：

```text
ToolExecutor
```

职责：

### ✔ 负责：

* 调度 tool
* timeout 控制
* error wrapping
* result normalization
* context patch validation

---

## ✔ Execution Flow（标准流程）

```text
Agent → ToolRequest
        ↓
ToolRegistry.resolve()
        ↓
ToolExecutor.execute()
        ↓
Tool.run()
        ↓
ToolResult
        ↓
ContextPatch (optional)
        ↓
Runtime.commit()
```

---

# 5. Tool Registry（必须设计为 Capability Map）

不是 list，而是：

```python
class ToolRegistry:
    tools: Dict[ToolId, Tool]
```

支持：

* register
* resolve
* version selection

---

## ✔ Resolution Strategy

```text
(name + version) → Tool instance
```

未来扩展：

* semantic versioning
* fallback version
* capability matching

---

# 6. Context Mutation Model（关键设计）

这是 Phase3 最重要的边界控制点。

---

## ❗ 禁止 Tool 直接写 Context

必须走：

```text
Tool → ContextPatch → Runtime → Commit
```

---

## ✔ ContextPatch 结构

```python
class ContextPatch:
    updates: dict
    deletes: list[str]
    merges: dict
```

---

## ✔ 为什么必须这样设计？

避免：

* Tool side effects不可控
* Debug困难
* replay失败
* deterministic execution broken

---

# 7. Phase3 MVP 定义（收敛范围）

我们现在明确 Phase3 第一阶段实现范围：

---

## ✔ 必须实现

### 1. Tool base interface

```text
AbstractTool
```

---

### 2. ToolResult

标准化输出

---

### 3. ToolRegistry

注册 + resolve

---

### 4. ToolExecutor

执行 + timeout + error handling

---

### 5. ContextPatch机制

但不做 memory system

---

## ❌ 不做（严格限制）

* sandbox runtime
* event bus
* async distributed tools
* memory integration
* workflow integration

---

# 8. Phase3 Step1 结论（设计收敛）

我们最终得到 Tool System 的工业级定义：

```text
Tool System =

Tool ABI
+ Tool Registry
+ Tool Executor Runtime
+ Tool Result Standardization
+ Context Patch Control Layer
```

---

很好。

从这里开始进入 **Phase3 Step2：领域建模 → 接口设计**。

# 一、重新定义 Tool 子系统中的对象

先做领域建模。

整个 Tool Runtime 里面有哪些 Entity？

```text
Agent
 ↓
ToolRequest
 ↓
ToolExecutor
 ↓
ToolRegistry
 ↓
Tool
 ↓
ToolResult
 ↓
ContextPatch
 ↓
Context
```

其中只有部分对象是真正的 Domain Entity。

---

# 二、哪些是 Entity？

## Tool

这是核心 Entity。

它代表：

```text
一种能力（Capability）
```

例如：

```text
FileTool
CommandTool
SearchTool
PythonTool
```

Tool 是长期存在的对象。

拥有：

```python
id
name
version
schema
policy
executor
```

---

## ToolResult

也是 Entity。

因为：

它不是过程数据。

而是：

```text
一次执行结果的标准表示
```

拥有：

```python
success
output
error
metadata
context_patch
```

---

## ContextPatch

也是 Entity。

因为：

它描述：

```text
对 Context 的修改意图
```

而不是直接修改。

例如：

```python
{
    "scratchpad": "...",
    "working_dir": "...",
}
```

---

# 三、哪些不是 Entity？

### ToolExecutor

不是。

它是 Domain Service。

负责：

```text
调度
timeout
异常包装
```

没有状态。

---

### ToolRegistry

不是。

它是 Repository。

负责：

```text
register
resolve
lookup
```

---

### ToolRequest

不是。

属于 DTO。

---

因此：

整个结构应该是：

```text
Entity
-------
Tool
ToolResult
ContextPatch

Service
-------
ToolExecutor

Repository
-------
ToolRegistry

DTO
-------
ToolRequest
```

这是 DDD 上更合理的划分。

---

# 四、目录结构设计

先不要急着实现 Tool。

先设计目录。

我建议：

```text
agentos/

core/
    tools/
        entities/
            tool.py
            result.py
            patch.py

        services/
            executor.py

        repositories/
            registry.py

        dto/
            request.py

        exceptions/
            exceptions.py
```

但我其实不满意。

因为 Tool 是一级概念。

后面会有：

```text
memory
eventbus
checkpoint
reflection
```

它们都不需要 entities/services/repositories 这种拆法。

所以更推荐：

```text
core/

tools/
    base.py
    result.py
    patch.py
    registry.py
    executor.py
    exceptions.py
```

简单、工业界常见、可维护。

---

# 五、开始接口设计

这是最重要的部分。

先定义 Tool 抽象。

注意：

Tool 不应该是：

```python
class Tool:
    async def execute(...)
```

这样太弱。

Tool 本身应该包含：

### Identity

```python
name
version
description
```

### Schema

```python
input_schema
output_schema
```

### Policy

```python
timeout
retry
execution_mode
```

### Execution

```python
execute()
```

因此：

Tool 实际上是：

```text
Tool
=
Identity
+
Schema
+
Policy
+
Executor
```

---

# 六、Tool Base Interface

抽象结构：

```python
class AbstractTool(ABC):

    @property
    def name(self):
        ...

    @property
    def version(self):
        ...

    @property
    def description(self):
        ...

    @property
    def input_schema(self):
        ...

    @property
    def output_schema(self):
        ...

    @property
    def policy(self):
        ...

    async def execute(
        self,
        input,
        context
    ):
        ...
```

这里先不要实现。

继续分析。

---

# 七、ToolResult

ToolResult 是整个 Tool Runtime 的 ABI。

我希望它足够稳定。

因此：

```python
ToolResult

success
output
error
metadata
patch
```

例如：

```python
ToolResult(
    success=True,
    output="hello",
    error=None,
    metadata={
        "duration":0.3
    },
    patch=ContextPatch(...)
)
```

未来：

Workflow

Checkpoint

Memory

Reflection

都会依赖这个 ABI。

因此：

### ToolResult 属于 core ABI

非常稳定。

不能轻易改。

---

# 八、ContextPatch

这是整个系统未来可 replay 的基础。

禁止：

```python
context["scratchpad"]="xxx"
```

而是：

返回：

```python
ContextPatch(
    updates={
        "scratchpad":"xxx"
    }
)
```

然后：

```text
Runtime
    ↓
apply_patch()
    ↓
Context
```

这样：

Checkpoint

Replay

Tracing

都能做。

---

# 九、Registry 接口

最简单：

```python
register()

resolve()

list_tools()
```

内部：

```python
dict[
    str,
    AbstractTool
]
```

即可。

Phase3 不做：

* semantic version
* namespace

保持最小。

---

# 十、Executor 接口

这是真正的 Service。

职责：

```text
resolve tool
↓

timeout

↓

execute

↓

exception capture

↓

normalize ToolResult

↓

return
```

因此：

```python
execute(
    request
)
    ->
ToolResult
```

而不是：

```python
tool.execute()
```

Agent 永远不直接碰 Tool。

必须经过：

```text
Agent
 ↓
ToolExecutor
 ↓
Tool
```

这样才能统一：

* tracing
* timeout
* retry
* metrics

---

# Step2 结束

现在我们已经完成：

### Tool 子系统领域模型

以及：

### 五个核心对象接口设计

```text
AbstractTool
ToolResult
ContextPatch
ToolRegistry
ToolExecutor
```

一个很重要的原则出现了
Tool 不拥有状态

而是：

Tool 消费状态 + 产生状态变化

即：

SessionContext
       ↓
Tool.execute()
       ↓
ToolResult
       ↓
ContextPatch
       ↓
SessionContext

形成闭环。

更准确地说

真正保存 Tool 状态的不是 Runtime。

而是：

Runtime Session Context

例如：

```python

class SessionContext:

    scratchpad

    working_dir

    variables

    resources

    memories

```

Tool：

只是：
```python

execute(
    input,
    context
)
```

读取：

context.xxx

返回：

patch.xxx

不保存任何东西。

这里会得到一个非常漂亮的结构
```
             Tool(singleton)
                     ↑
                     │
              no internal state
                     │
                     ▼

SessionContext(stateful)
        ↑                   ↓
        │                   │
apply_patch()          execute()

        ▲                   │
        │                   ▼

     ContextPatch      ToolResult
```
于是：

Tool 可以安全 Singleton。
多 Session 可以并发。
Checkpoint 可以做。
Replay 可以做。
Event sourcing 可以做。

所以我会把你的答案进一步精炼成：

Tool 的状态不属于 Tool，而属于 SessionContext。

更进一步：

Tool 本质上是一个纯 Capability。

它：

读取 Context
↓
执行能力
↓
返回 Result + Patch

不持有任何 execution state。

### 三、Context 真正应该是什么？

其实：

Context 不应该是 State。

而应该是：

Session Runtime

里面包含：

State
+
Resources
+
Metadata

所以：

SessionContext
    ├── State
    ├── Resources
    └── Metadata
四、第一层：State

真正可 checkpoint 的状态。

例如：

class ContextState(BaseModel):

    working_dir: str = "."

    scratchpad: str = ""

    variables: dict[str, Any] = Field(default_factory=dict)

特点：

可序列化
可 replay
可 checkpoint
五、第二层：Resources

不可 checkpoint。

例如：

shell_session

browser

redis_client

llm_client

这些东西：

不能：

json.dumps()

所以：

Resources 必须和 State 分离。

例如：

class ContextResources:

    shell = None

    browser = None

甚至后面：

class ResourceManager

负责管理。

六、第三层：Metadata

运行时信息。

例如：

task_id

session_id

user_id

start_time

这些：

属于 Runtime Metadata。

不是业务状态。

七、于是 Context 结构变成：
SessionContext
│
├── state
│      ├── working_dir
│      ├── scratchpad
│      └── variables
│
├── resources
│      ├── shell
│      └── browser
│
└── metadata
       ├── task_id
       └── session_id

这时候：

Tool：

```python
execute(
    input,
    context
)
```

访问：

context.state.working_dir

而不是：

context["working_dir"]
八、ContextPatch 应该 patch 谁？

答案是：

只 patch：

```
ContextState
```

绝不 patch：

```
Resources
Metadata
```

例如：

允许：
```python
patch.updates = {
    "working_dir": "/repo2"
}
```

不允许：

```python
patch.updates = {
    "browser": Browser()
}
```
因为：

Browser 是 Resource。

不是 State。

### 我们刚刚实际上做出了一个关键决定：

State ≠ Context

而是：
```
Context
=
State
+
Resources
+
Metadata
```
这会直接影响：

Workflow

因为 Workflow 处理的是：

```
State
```

**Checkpoint**

保存的是：

```
State
```

**Tool**

访问的是：

```
Context
```

**Memory**

属于：
```
State 的一部分
```

**Browser**

属于：

```
Resources
```

### 需要确定的是： ContextState是Mutable State还是Immutable State？

1. Mutable State

直接更新原State中的字段：

 - 简单
 - 内存占用小
 - Python风格自然

但是当node执行失败时无法恢复，因为状态已经被修改了。通过`deepcopy()`或者`pickle()`来保存状态，代价非常高。

2. Immutable State

直接返回新的State对象，可以：
 - Replay
 - Recover
 - Deterministic execution

本项目中使用的是 Immutable State。

### Step9: ToolRequest创建

### Step10: ToolExecutor创建

```
Agent
 ↓
ToolRequest
 ↓
ToolExecutor
 ↓
Tool
```

为了与Agent解耦，Agent不能直接调用`tool.execute()`,而是创建`ToolRequest`，并传递给`ToolExecutor`执行

但是`ToolExecutor`不能直接调用`Tool.execute()`,而是通过`ToolRegistry`获取`Tool`实例并执行

`ToolRegistry`就是一个`name -> Tool`的映射。最简单的实现方式就是使用一个字典：

```python
TOOLS = {
    "echo": FakeEchoTool()
}
```
但是全局变量的问题：

 - 无法替换
 - 无法测试
 - 无法 DI
 - 生命周期不明确

## Phase3 的架构已经开始变得非常清晰：
```angular2html
Agent
 ↓
ToolRequest
 ↓
ToolExecutor
 ↓
ToolRegistry
 ↓
Tool
 ↓
ToolResult
 ↓
ContextPatch

(停止)

SessionContext
 ↓
apply_patch()
 ↓
Session1
```

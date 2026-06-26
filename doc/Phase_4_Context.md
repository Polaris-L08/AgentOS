# Phase4 Step1：需求分析

这一阶段先不写代码。

目标是回答两个问题：

```text
AgentContext 应该是什么？
Context 和 Memory 的边界在哪里？
```

---

# 一、为什么需要 Context Runtime？

目前 Phase3 结束时：

```text
Task
↓
ToolExecutor
↓
Tool
↓
Patch
↓
SessionContext
```

SessionContext 更像：

```python
dict[str, Any]
```

它只能保存：

```python
state["current_file"]
state["code"]
state["price"]
```

但真正 Agent 在运行时需要维护更多东西：

```text
用户任务
历史消息
中间思考
工具执行结果
短期记忆
工作目录
共享变量
```

例如：

```text
用户：
帮我修复 bug

Agent：

step1
读取文件

step2
分析错误

step3
修改代码

step4
运行测试

step5
失败

step6
重新规划
```

如果没有 Runtime Context：

每一步都必须重新构造 prompt。

状态无法持续。

所以需要：

```text
AgentContext
```

作为整个 Session 的运行时载体。

---

# 二、Context 是什么？

先给一个定义：

### Context = 当前执行所需的一切状态

注意：

### Context ≠ Memory

Context 更大。

例如：

```text
AgentContext
│
├── task
├── workspace
├── history
├── scratchpad
├── variables
├── tool_cache
├── short_term_memory
└── metadata
```

它是：

```text
Runtime State Container
```

生命周期：

```text
Task Start
↓
创建 Context
↓
不断修改
↓
Task Finish
↓
销毁
```

属于：

### Session 级对象

---

# 三、Memory 是什么？

Memory 是 Context 的一个子系统。

作用：

### 提供跨 step 的经验保存

例如：

用户：

```text
我喜欢简洁代码
```

5 步以后：

Agent 不需要重新分析历史。

直接：

```python
memory["coding_style"]="simple"
```

Memory 更像：

```text
Knowledge Layer
```

而 Context 是：

```text
Runtime Layer
```

所以：

```text
Context
└── Memory
```

而不是：

```text
Memory
└── Context
```

---

# 四、哪些东西属于 Context？

先列出所有候选项。

### ① task

当前任务。

例如：

```python
TaskRequest
```

保存：

```python
task_id
goal
input
```

生命周期：

整个 session。

---

### ② workspace

运行环境。

例如：

```python
workspace/
```

当前：

```python
cwd
project_root
files
```

例如：

```python
workspace.current_file
```

属于：

Runtime State。

---

### ③ history

交互历史。

例如：

```python
[
    Message(...)
]
```

保存：

```text
user
assistant
tool
system
```

作用：

构造 prompt。

生命周期：

整个 session。

---

### ④ scratchpad

临时思考区域。

例如：

```python
发现错误：
ImportError

猜测：
版本冲突

下一步：
检查 requirements
```

类似 ReAct 的：

```text
Thought
Observation
```

特点：

动态变化。

允许覆盖。

任务结束后丢弃。

---

### ⑤ variables

共享变量。

例如：

```python
{
    "language":"python",
    "repo":"agentos"
}
```

工具之间共享。

---

### ⑥ tool_cache

避免重复调用工具。

例如：

```python
read_file(a.py)
```

缓存：

```python
{
    key → ToolResult
}
```

属于：

Session Cache。

---

### ⑦ short_term_memory

最近的重要结论。

例如：

```text
项目使用 uv

测试框架 pytest

代码风格 black
```

特点：

可压缩。

可总结。

不一定保留完整历史。

---

### ⑧ metadata

运行信息。

例如：

```python
token_usage
cost
start_time
```

属于：

观测层。

---

# 五、哪些不应该进入 Context？

### 长期记忆

例如：

```text
Qdrant
VectorDB
```

不属于。

原因：

生命周期跨 session。

应该在：

```text
memory/
    vector_memory.py
```

按需召回。

---

### Checkpoint

属于：

```text
checkpoint/
```

不是 Context。

Checkpoint 只是：

```python
save(context)
```

---

### EventBus

属于：

```text
eventbus/
```

不属于 Context。

---

### Tracing

属于：

```text
tracing/
```

不属于 Context。

---

# 六、初步领域模型

目前得到：

```text
AgentContext
│
├── task
│
├── workspace
│
├── history
│
├── scratchpad
│
├── variables
│
├── tool_cache
│
├── short_term_memory
│
└── metadata
```

其中：

```text
history
scratchpad
short_term_memory
```

最容易混淆。

这是下一步需要继续做的领域建模。

---

# Phase4 Step2： 领域建模

Phase4 真正困难的部分其实不是 `AgentContext`，而是区分：

```text
history
scratchpad
short_term_memory
```

很多 Agent Framework（包括 LangChain、CrewAI、AutoGen）最终都会出现一个问题：

```text
所有东西都塞进 message history
```

导致：

* prompt 越来越长
* checkpoint 难以恢复
* reflection 无法插入
* memory 无法压缩
* multi-agent 无法共享

因此这一步本质上是在做：

> Runtime Information Modeling

仍然按照：

```text
需求分析
↓
领域建模（当前）
↓
架构设计
↓
接口设计
↓
数据模型
↓
编码
```

---

### 一、先不要看实现，先看信息的性质

Agent 运行过程中会产生很多信息：

```text
用户：
帮我修复 pytest 报错
↓
读取文件
↓
发现 ImportError
↓
怀疑版本冲突
↓
查看 pyproject.toml
↓
发现 pytest=7
↓
requirements 中 pytest=8
↓
修改
↓
运行测试
↓
通过
```

这些信息并不是一种东西。

其实包含三类：

```text
事实（Fact）

思考（Thought）

对话（Conversation）
```

这三类东西生命周期完全不同。

---

### 二、history 是 Conversation

例如：

User：

```text
帮我修复 pytest 报错
```

Assistant：

```text
好的
```

Tool：

```text
read_file()
```

Observation：

```text
文件内容……
```

这些形成：

```python
messages = [
    ...
]
```

特点：

**append-only**

只能追加：

```text
user
assistant
tool
system
```

不会修改。

生命周期：

```text
session 内有效
```

作用：

**构造 prompt**

所以：

> history 是 Conversation Log

而不是记忆系统。

---

### 三、scratchpad 是 Thought

例如：

Agent：

```text
错误：

ImportError
```

猜测：

```text
版本冲突
```

下一步：

```text
检查 requirements
```

运行后发现：

```text
猜错了
```

于是：

重新推理：

```text
可能是 virtualenv 问题
```

注意：

这些推理过程：

**可以被覆盖**

不是 append-only。

特点：

```text
动态变化
可删除
可重写
任务结束丢弃
```

本质：

```text
Working Memory
```

类似 CPU cache。

不是长期信息。

---

### 四、short_term_memory 是 Fact

执行过程中产生的重要结论：

例如：

发现：

```text
项目使用 uv
```

发现：

```text
测试框架 pytest
```

发现：

```text
代码风格 black
```

这些不是对话。

也不是推理。

而是：

### 稳定事实

特点：

任务后半段仍然有用。

可以压缩。

例如：

前面 100 条 message：

压缩后：

```python
[
    "repo use uv",
    "style black",
    "framework pytest"
]
```

所以：

**short_term_memory = session knowledge**

---

### 五、三者最大的区别

#### history

记录： **发生了什么**

形式：

```python
Message[]
```

特点：

append-only

作用：

prompt

---

#### scratchpad

记录： **正在想什么**

形式：

```python
Scratchpad
```

特点：

mutable

作用：

reasoning

---

#### short_term_memory

记录： **已经知道什么**

形式：

```python
MemoryItem[]
```

特点：

可压缩

作用：

knowledge

---

所以：

```text
Conversation
≠
Thought
≠
Fact
```

这是最重要的领域边界。

---

### 六、生命周期分析

#### history

```text
session start
↓
append
↓
append
↓
append
↓
session end
```

一直增长。

---

#### scratchpad

```text
thought1
↓
thought2
↓
overwrite
↓
overwrite
↓
clear
```

生命周期最短。

---

#### short_term_memory

```text
fact1
fact2
fact3
↓
summarize
↓
compressed memory
```

介于二者之间。

---

### 七、是否把 scratchpad 放入 message？

很多框架这样做：

```python
assistant:
Thought:
...

assistant:
Action:
...

assistant:
Observation:
...
```

全部塞进：

```python
messages
```

看起来简单。

但问题很大。

 - **token 爆炸**

每一步：

```text
Thought
Action
Observation
```

都重复进入 prompt。

越来越长。

---

 - **无法 checkpoint**

恢复时：

必须重新解析 message。

不能直接恢复推理状态。

---

 - **reflection 很难**

CriticAgent 想修改：

```text
当前假设
```

必须改 message。

message 是 append-only。

不合理。

---

 - **multi-agent 难共享**

Planner 的 thought：

Coder 不应该看到。

但都在 messages。

无法隔离。

---

所以：**scratchpad 必须独立**。

---

### 八、是否把 short_term_memory 放入 history？

也不应该。

例如：

100 条历史：

压缩得到：

```text
repo uses uv
```

如果放入 history： 

会出现：

```text
message1

...

message100

summary
```

之后继续：

message101

message102

又压缩：

summary2

最终：

history 中出现：

```text
summary1
summary2
summary3
```

产生重复知识。

知识污染。

所以：

memory 应独立。

---

# 九、领域模型

现在得到：

```text
AgentContext
│
├── history
│       ↓
│     Message[]
│
├── scratchpad
│       ↓
│     Scratchpad
│
└── short_term_memory
        ↓
      MemoryItem[]
```

三者职责：

```text
history
记录过去

scratchpad
记录现在

memory
记录结论
```

时间维度：

```text
过去
↓
现在
↓
已知事实
```

---

### 十、进一步的问题

现在其实出现了新的领域对象：

```text
Message
Scratchpad
MemoryItem
```

以及：

```text
Workspace
Variables
Metadata
ToolCache
```

---

# Phase4 Step3 架构设计

从 Phase4 开始，复杂度开始真正上升。因为我们不再是在设计一个数据结构，而是在设计一个 Runtime。

---

### 一、先看最简单的方案

很多框架会这样设计：

```python
class AgentContext:

    task

    history

    scratchpad

    short_term_memory

    workspace

    variables

    metadata

    tool_cache
```

所有东西放在一个对象里面。

使用：

```python
context.history.append(...)

context.short_term_memory.add(...)

context.workspace.current_file
```

看起来很简单。

**问题是什么？**

随着系统演进：

```text
Checkpoint
Summary
Compression
Reflection
EventBus
Persistence
Multi-Agent
```

都会进入。

于是：

```python
class AgentContext:

    def add_message()

    def summarize()

    def checkpoint()

    def recover()

    def publish_event()

    def compress_memory()

    def merge_context()

    ...
```

最终：

**God Object（上帝对象）**

Context 变成整个 Runtime。

这是要避免的。

---

### 二、AgentContext 应该只是 Container

核心原则：

**AgentContext 不拥有行为**

只拥有：

```text
state
```

真正的行为应该属于：

```text
HistoryManager

ScratchpadManager

MemoryManager

WorkspaceManager

ToolCacheManager
```

所以：

```text
AgentContext
│
├── history
├── scratchpad
├── memory
├── workspace
├── variables
├── metadata
└── tool_cache
```

更像：

```text
Aggregate Root
```

自己不做复杂逻辑。

---

### 三、第一种架构：Manager 模式

```text
AgentContext
│
├── HistoryManager
│
├── ScratchpadManager
│
├── MemoryManager
│
├── WorkspaceManager
│
└── ToolCacheManager
```

例如：

```python
context.history.add()

context.memory.store()

context.scratchpad.set()

context.workspace.change_file()
```

优点：

职责清晰。

Checkpoint 时：

```python
context.memory.snapshot()

context.history.snapshot()
```

Reflection：

```python
context.scratchpad.reset()
```

容易扩展。

---

### 四、第二种架构：全部 Manager 独立

甚至：

```text
Runtime
│
├── HistoryManager
├── ScratchpadManager
├── MemoryManager
├── WorkspaceManager
```

AgentContext 只是：

```python
class AgentContext:

    session_id
```

通过 Service Locator 获取。

例如：

```python
runtime.memory_manager.store()
```

这种模式看起来很高级。

但有个严重问题：

**上下文不再自包含**

Checkpoint：

想保存：

```python
save(context)
```

结果发现：

状态散落在：

```text
runtime.memory_manager

runtime.history_manager

runtime.workspace_manager
```

恢复非常困难。

所以：

这种模式不适合 Durable Execution。

---

### 五、第三种架构：State + Manager

这是推荐方案。

**State**

纯数据。

例如：

```text
HistoryState

ScratchpadState

MemoryState

WorkspaceState

ToolCacheState
```

不包含行为。

---

**Manager**

负责操作 state。

例如：

```text
HistoryManager
↓
HistoryState

MemoryManager
↓
MemoryState

ScratchpadManager
↓
ScratchpadState
```

---

**AgentContext**

聚合所有 state

```text
AgentContext
│
├── HistoryState
├── ScratchpadState
├── MemoryState
├── WorkspaceState
└── ToolCacheState
```

形成：

```text
Manager
↓
State
↓
AgentContext
```

这样：

**Context 天然可序列化**

Checkpoint：

```python
save(context)
```

即可。

---

### 六、未来 Reflection 怎么工作？

CriticAgent：

发现：

```text
假设错误
```

只需要：

```python
scratchpad_manager.reset()
```

修改：

```python
ScratchpadState
```

而：

history

保持不变。

这是：

```text
Conversation
≠
Reasoning
```

的好处。

---

### 七、未来 Memory Compression

History：

1000 条消息。

总结出：

```text
repo use uv
framework pytest
```

MemoryManager：

更新：

```python
MemoryState
```

但：

HistoryState 不动。

因此：

```text
Conversation
不丢

Knowledge
被压缩
```

可以共存。

---

### 八、未来 Checkpoint

CheckpointManager：

不关心 Manager。

只保存：

```python
AgentContext
```

内部：

```python
{
    history_state,

    scratchpad_state,

    memory_state,

    workspace_state,

    ...
}
```

恢复：

```python
context = load()
```

然后重新构造：

```python
HistoryManager(context.history)

MemoryManager(context.memory)
```

天然支持 Durable Execution。

---

### 九、未来 Multi-Agent

最容易出问题的地方。

例如：

PlannerAgent：

拥有：

```text
history
scratchpad
memory
```

CoderAgent：

拥有：

```text
history
scratchpad
memory
```

但：

共享：

```text
workspace
```

或者：

共享：

```text
memory
```

不同 Agent 可以：

**部分共享 State**

而不是共享整个 Context。

这是组合式设计最大的价值。

---

### 十、最终推荐架构

**State Layer**

```text
HistoryState
ScratchpadState
MemoryState
WorkspaceState
ToolCacheState
MetadataState
VariableState
```

全部：

Pydantic Model。

纯数据。

---

**Context Layer**

```text
AgentContext
│
├── history_state
├── scratchpad_state
├── memory_state
├── workspace_state
├── variable_state
├── metadata_state
└── cache_state
```

负责：

聚合。

没有复杂行为。

---

**Manager Layer**

```text
HistoryManager

ScratchpadManager

MemoryManager

WorkspaceManager

ToolCacheManager
```

负责：

业务逻辑。

---

形成：

```text
Agent
↓
Manager
↓
State
↓
AgentContext
```

而不是：

```text
Agent
↓
God Context
```

---

# Phase4 Step4 接口设计

---

# Phase4 Step5 数据模型设计

从这里开始，我们不再讨论概念，而是在确定：

> Runtime State 应该如何表示？

```text
> State mutable
> Context immutable
```

这是一个折中方案。

例如：

HistoryState：

```python
messages: list[Message]
```

允许：

```python
history.messages.append()
```

但是：

AgentContext 不允许：

```python
context.history = ...
```

Context 聚合关系固定。

即：
```text
AgentContext
│
├── history_state
├── memory_state
├── scratchpad_state
```

不可替换。

内部 State 可修改。

### 领域对象设计

#### Message

Message 是 Value Object。

建议：

```python
Message

id
role
content
timestamp
metadata
```

role：

```python
USER
ASSISTANT
SYSTEM
TOOL
```

用 Enum。

不要字符串。

未来：

```python
THOUGHT
OBSERVATION
```

也能扩展。

Message： immutable。

#### MemoryItem

也是 Value Object。

```python
MemoryItem

id

content

importance

source

timestamp
```

source：

例如：

```python
history

tool

reflection
```

importance：

以后支持：

```python
forget
compress
rank
```

immutable。

#### Scratchpad

最值得讨论。

不要：

```python
scratchpad: str
```

推荐：

```python
current_goal

hypothesis

next_action

notes
```

Reflection：

只修改：

```
hypothesis
```

而不是整个字符串。

这是结构化推理。

---

### State Model

**HistoryState**

```python
messages: list[Message]
```

---

**MemoryState**

```python
items: list[MemoryItem]
```

---

**ScratchpadState**

```python
scratchpad: Scratchpad
```

---

**WorkspaceState**

```python
project_root

cwd

current_file
```

---

**VariableState**

```python
variables: dict[str, Any]
```

以后可能：

```VariableValue```

暂时不需要。

---

**MetadataState**

```python
session_id

created_at

token_usage

cost
```

---

**ToolCacheState**

```python
cache: dict[str, ToolResult]
```

key：

建议：

```python
tool_name + hash(arguments)
```

以后支持 TTL。

---

#### AgentContext

这里有一个重要的问题：**直接聚合State** 还是 **再包一层ContextState** ？

方案A:

```python
class AgentContext:
    history_state

    memory_state

    scratchpad_state

    workspace_state
```

方案B:

```python
class ContextState:
    history_state
    memory_state
    ...

class AgentContext:
    state: ContextState
```

未来 AgentContext再引入

```python
session_id
version
agent_id
...
```

更推荐：方案B。

这样：

Checkpoint 保存： ```ContextState```

Runtime 保存： ```AgentContext```

边界更清晰。

#### ContextState 与 AgentContext 分离

根据上面的讨论，AgentContext中同时保存了 ContextState 和 Runtime Object。

这样： AgentContext != Serializable State

先确定AgentContext为什么会这样：

最简单的设计下：

```python
class AgentContext(BaseModel):
    history: HistoryState
    memory: MemoryState
    scratchpad: ScratchpadState
    workspace: WorkspaceState
```

Checkpoint:

```python
save(context)
```

恢复：

```python
load(context)
```

随着系统迭代：

```python
class AgentContext(BaseModel):
    state: ContextState
    config
    provider
    event_bus
    tracer
    middleware
    runtime_id
    agent_id
```

这里包含了很多**runtime dependency**：

```python
event_bus
tracer
provider
```

这些不应该被checkpoint。

### Phase4 Step6 编码

目录，建议：

```text
agentos/

core/
    agent_context.py

memory/
    message.py

    history_state.py

    history_manager.py

    context_state.py

tests/
    test_history_manager.py
```

```text
History
↓
Conversation

Scratchpad
↓
Thought

Memory
↓
Fact

Workspace
↓
Environment

Variables
↓
Shared Runtime Data
```
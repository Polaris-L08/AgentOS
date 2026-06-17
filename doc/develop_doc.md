
# 项目背景

我是 AI Agent 开发初学者。

已经完整学习过 TradingAgents-CN，并理解：

* Planner
* Multi-Agent
* Tool Calling
* Memory
* Report Agent
* Workflow

现在希望从零开始，构建一个真正工业级（Industrial-grade）的 Agent 项目，用于：

1. 巩固 Agent Engineering 知识；
2. 深入理解 Runtime、Workflow、Memory 等底层机制；
3. 为未来求职 AI Agent Engineer / LLM Application Engineer / AI Runtime Engineer 做准备；
4. 项目周期预计 6~12 个月；
5. 希望按照工业软件演化方式逐步开发，而不是一次性完成。

---

# 项目方向

项目不是：

* 股票 Agent
* PDF Agent
* 旅游 Agent

项目目标是：

> 从零实现一个工业级 Code Agent Runtime（类似 Devin / OpenHands，但完全自己设计）。

业务只是外壳。

真正的核心是：

* Runtime
* Workflow Engine
* Tool System
* Memory System
* Reflection
* Checkpoint
* Event Bus
* Middleware
* Tracing
* Multi-Agent

目标是构建一个：

```text
AgentOS
```

或者：

```text
Industrial Agent Runtime
```

以后可以支持：

* Code Agent
* Research Agent
* Manufacturing Agent
* DevOps Agent

共享同一个 Runtime。

---

# 设计原则

## 不依赖 LangGraph

允许使用：

* OpenAI SDK
* LiteLLM
* Pydantic
* FastAPI
* PostgreSQL
* Redis
* Qdrant

不要把核心能力交给：

* LangGraph
* CrewAI
* AutoGen

原因：

希望自己实现：

* Workflow
* State Machine
* Checkpoint
* Event Bus
* Reflection

真正理解 Agent Runtime。

---

# 技术栈

Python 3.12

依赖：

```python
asyncio
pydantic
fastapi
litellm
openai
sqlalchemy
redis
qdrant-client
pytest
uv
```

数据库：

```text
PostgreSQL
Redis
Qdrant
```

部署：

```text
Docker
Docker Compose
```

---

# 整体架构

最终目录目标：

```text
agentos/

core/
    runtime.py
    dispatcher.py
    worker.py

workflow/
    state_machine.py

agents/
    planner_agent.py
    coder_agent.py
    tester_agent.py
    reviewer_agent.py

tools/
    base_tool.py
    file_tool.py
    command_tool.py

memory/
    short_term.py
    vector_memory.py

reflection/
    critic_agent.py

checkpoint/
    checkpoint_manager.py

eventbus/
    bus.py

middleware/
    retry.py
    timeout.py

tracing/
    tracer.py

providers/
    llm_provider.py

storage/
    postgres.py
    redis.py
    qdrant.py

api/
    fastapi/

tests/
```

---

# 开发方式

不追求快速完成。

遵循：

> Every Version Must Work

每一个版本必须：

* 可运行
* 有测试
* 有 README
* 有架构图
* 可以演示

采用增量开发。

---

# V1~V10 演进路线

---

## Phase 1

### Single Agent Runtime

实现：

```python
AgentRuntime
```

状态：

```python
IDLE
RUNNING
FAILED
DONE
```

支持：

```python
run()
```

目标：

跑通最小闭环。

不要考虑多 Agent。

---

## Phase 2

### Workflow Runtime

引入：

```python
StateMachine
```

流程：

```text
PLAN
↓
CODE
↓
TEST
↓
DONE
```

实现：

```python
next_state()
```

目标：

状态机驱动 Workflow。

---

## Phase 3

### Tool System

统一接口：

```python
class Tool:
    async execute()
```

实现：

#### ReadFileTool

#### WriteFileTool

#### SearchCodeTool

#### RunCommandTool

形成：

```python
ToolRegistry
```

---

## Phase 4

### Context & Memory

实现：

```python
AgentContext
```

保存：

```python
task
workspace
history
```

加入：

### Short-term Memory

Conversation Memory

### Long-term Memory

Vector Memory

目录：

```text
memory/
```

---

## Phase 5

### Reflection Runtime

加入：

```python
CriticAgent
```

流程：

```text
CODE
↓
TEST
↓
FAIL
↓
REFLECTION
↓
REPLAN
↓
CODE
```

形成自修正循环。

这是 Agent 最核心能力。

---

## Phase 6

### Checkpoint Runtime

实现：

```python
CheckpointManager
```

保存：

```python
session_id
workflow_state
tool_result
memory
```

支持：

```python
save()

resume()
```

模拟：

* API 超时
* Worker 崩溃

实现恢复执行。

---

## Phase 7

### Event Bus

事件：

```python
TaskStarted
CodeFinished
TestFinished
TaskCompleted
```

订阅者：

```python
Tracer
Logger
Metrics
Memory
```

实现模块解耦。

Role 与 Consumer 分离。

---

## Phase 8

### Middleware

实现：

```python
RetryMiddleware

TimeoutMiddleware

LoggingMiddleware
```

形成 Pipeline。

---

## Phase 9

### Tracing

类似 LangSmith。

记录：

```python
Trace
Span
Latency
Cost
Token
```

形成执行树：

```text
Planner
 ↓
Coder
 ↓
Tool
 ↓
Tester
```

---

## Phase 10

### Multi-Agent Runtime

加入：

```text
PlannerAgent
CoderAgent
TesterAgent
ReviewerAgent
```

通过 Event Bus 协作。

不要 Agent 之间直接调用。

---

# 非功能性目标

整个项目重点放在：

### Runtime

而不是 Prompt。

### Architecture

而不是 Demo。

### State Machine

而不是 LangGraph。

### Event-driven

而不是同步调用。

### Durable Execution

而不是一次执行完成。

### Observability

而不是黑盒运行。

### Scalability

而不是脚本工程。

---

# 学习方式要求

希望以导师模式进行学习。

不要直接给出完整代码。

优先：

1. 分析需求；
2. 讨论架构；
3. 定义职责边界；
4. 设计数据结构；
5. 讨论为什么这样设计；
6. 对比不同方案；
7. 最后才进入编码。

每个阶段按照工业软件开发方式推进：

```text
需求分析
↓
领域建模
↓
架构设计
↓
接口设计
↓
数据模型
↓
编码
↓
测试
↓
重构
```

希望深入理解：

* 为什么这样设计；
* 各模块职责边界；
* 如何解耦；
* 如何支持扩展；
* 如何支持多 Agent；
* 如何支持分布式；
* 如何支持 Durable Execution；

而不仅仅是实现功能。

---

# 当前阶段

尚未开始编码。

希望从 Phase 1 开始。

先完成：

> Agent Runtime V1 的领域建模和架构设计。

希望采用导师式、工业级、循序渐进的方式学习，而不是直接得到答案。

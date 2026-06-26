Phase 1
Agent Runtime V1

目标：

建立最小闭环：

Task
 ↓
AgentRuntime
 ↓
Agent
 ↓
Result

暂时不考虑：

Workflow
Tool
Memory
EventBus
Multi-Agent
Checkpoint

只解决：

一个 Agent 如何被 Runtime 驱动执行

Step 1：需求分析

用户调用：

runtime.run(
    task="write hello world"
)

Runtime：

IDLE
 ↓
RUNNING
 ↓
DONE

或者：

IDLE
 ↓
RUNNING
 ↓
FAILED

返回：

TaskResult

这是全部需求。

Step 2：领域建模（最重要）

先不要写代码。

先找领域对象（Domain Objects）。

我会问一个问题：

Runtime 的核心对象有哪些？

很多人第一反应：

Agent
Runtime
Task
Result

其实不够。

工业系统应该至少有：

TaskRequest
TaskContext
Agent
RuntimeState
TaskResult
AgentRuntime

关系：

          TaskRequest
                │
                ▼
          AgentRuntime
                │
        ┌───────┴────────┐
        ▼                ▼
 RuntimeState       TaskContext
        │                │
        └───────┬────────┘
                ▼
             Agent
                │
                ▼
            TaskResult

这里已经出现：

Command + Context + State

三种完全不同的概念。

这是 Runtime 的基础。

Step 3：职责划分
TaskRequest

外部输入。

例如：

task="write hello world"

特点：

immutable
一次执行的入口

类似：

class TaskRequest:
    task:str

生命周期：

创建
↓
进入 Runtime
↓
结束

之后不再存在。

TaskContext

执行上下文。

生命周期贯穿整个任务。

未来会越来越大：

V1：

task

V4：

task
workspace
history
memory

V6：

checkpoint

V10：

shared_state

所以：

Context 是 Runtime 世界里的 Session。

它不是 Request。

RuntimeState

这是 Runtime 自己的状态。

而不是 Workflow State。

注意这两个概念以后会分开。

Runtime State：

IDLE
RUNNING
DONE
FAILED

Workflow State（Phase2 才有）：

PLAN
CODE
TEST
DONE

不要混淆。

这是很多 LangGraph 项目容易混掉的地方。

Agent

Agent 是纯业务逻辑。

不管理：

状态
checkpoint
tracing
retry

Agent 只负责：

input

↓

think()

↓

TaskResult

即：

class Agent:
    async invoke(context)->TaskResult

它不知道 Runtime 的存在。

这一点很重要。

以后才能支持：

PlannerAgent
CoderAgent
TesterAgent

共享同一个 Runtime。

TaskResult

执行结果。

success
output
error

不要直接：

return str

因为未来：

Phase9：

需要：

token_usage
cost
latency

Phase10：

需要：

events
artifacts

所以：

Result 必须是对象。

Step 4：核心架构

V1：

建议只有三层：

app
│
└── AgentRuntime
          │
          ▼
        Agent
          │
          ▼
      TaskResult

目录：

agentos/

core/
    runtime.py
    state.py

agents/
    base_agent.py
    simple_agent.py

schemas/
    request.py
    context.py
    result.py

tests/

非常小。

故意不要提前设计几十个目录。

因为：

Architecture grows.

不是一开始就长成最终形态。

Step 5：AgentRuntime 的职责

这是 Phase1 最重要的问题。

Runtime 应该做什么？

应该：

1 状态管理

负责：

IDLE
RUNNING
DONE
FAILED
2 生命周期管理

负责：

before_run()

invoke()

after_run()

未来 middleware 会挂在这里。

3 异常处理

捕获：

Exception

生成：

TaskResult(success=False)

Agent 内部不处理。

不负责
Prompt

不负责。

Tool

不负责。

Memory

不负责。

Workflow

不负责。

Retry

不负责。

EventBus

不负责。

这是后续 Phase 再增加。

Step 6：状态机？

这里故意不引入 StateMachine。

因为：

Runtime State：

IDLE
↓
RUNNING
↓
DONE

是简单生命周期。

还没有：

PLAN
↓
CODE
↓
TEST

所以：

Phase1 不需要 StateMachine。

避免过度设计。

Step 7：我希望你先思考两个问题
问题1

TaskRequest 和 TaskContext 是否应该是同一个对象？

还是：

Request -> Context

两个对象？

为什么？

问题2

AgentRuntime 是否应该持有 Agent：

runtime = AgentRuntime(agent)

还是：

runtime.run(agent, task)

即：

Agent 属于 Runtime？

还是 Task 属于 Runtime？

这两个选择会影响未来：

Multi-Agent
EventBus
Dispatcher

建议先不要编码。

先把这两个问题想透。

等这两个问题确定，我们再进入：

Phase1 Step2

接口设计（Interface Design）

再开始真正编码。
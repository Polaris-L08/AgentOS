# Phase 10： Multi-Agent Runtime

---

## Step 1: Agent Model Design

### 1.1 Agent Model Design

当前CodeAgent的意义：

 - Agent类型: 一类Agent的定义
 - Agent实例
 - Agent Role： Coder是个角色，类似：Supervisor、Reviewer、Tester
 - Runtime Component： 是Runtime内执行单元

在Single Agent中是把以上全部揉在一起了。

#### Agent 和 Runtime 的关系

工业设计中： 

```text
Runtime

负责：

执行生命周期


        |
        |
        v


AgentInstance

负责：

Agent状态
Agent行为
```

关系：

```text
                 Runtime

                    |
                    |
          +---------+---------+

          |                   |

    AgentInstance A     AgentInstance B


          |
          |

   AgentDefinition
```

Runtime不应该知道： CodeAgent、ResearchAgent、ReviewAgent

只知道： AgentInstance

Role表示：

> Agent在当前协作系统中的职责。

同一个Agent可以担任不同的Role。例如CodeAgent可以是Developer，也可以是Reviewer，能力一样，职责不同。

```text
AgentDefinition 描述：我是谁，我会什么

Role 描述： 我现在负责什么

AgentInstance 描述： 哪个具体运行实体

Runtime 描述： 如何运行
```

#### AgentRuntime 和 ExecutionRuntime

```text
AgentDefinition
    描述 Agent 类型

AgentInstance
    一个真实存在的 Agent

BaseAgent
    Agent 行为实现
```

关系：

```text
AgentDefinition
        |
        | create
        v
AgentInstance
        |
        | bind
        v
BaseAgent
```

**AgentRuntime**负责管理AgentInstance的生命周期。

 - Agent Creation
 - Agent Registration
 - Lifecycle Management
 - Agent Availability
 - Agent Recovery

在Phase 9 中创建的ExecutionRuntime是负责创建一次执行环境。 负责管理：

 - Trace
 - RuntimeContext
 - LoopState
 - Checkpoint

对比：

|        | AgentRuntime  | ExecutionRuntime |
|--------|---------------|------------------|
| 管理对象   | AgentInstance | Execution        |
| 生命周期   | 长生命周期         | 短生命周期            |
| 是否持久存在 | 是             | 否                |
| 状态     | Agent State   | Execution State  |
| 负责创建   | Agent         | Context          |
| 负责恢复   | Agent         | Task             |

#### 完整 Multi-Agent Runtime 流程

1. Scheduler 接收任务： Need Research capability
2. 查询Registry： ResearchAgent-001
3. AgentRuntime 确认 Agent available
4. 创建 Execution： Execution-001
5. ExecutionRuntime创建：RuntimeContext、Trace、Checkpoint
6. 调用BaseAgent.execute()

```text
User Task
   |
Scheduler
   |
AgentRuntime
   |
AgentInstance
   |
ExecutionRuntime
   |
RuntimeContext
   |
BaseAgent
   |
Tool
```

最终结构：

```text
             AgentRuntime
                  |
          管理 Agent
                  |
        +---------+---------+
        |                   |
 ResearchAgent-001    RiskAgent-001
        |
        |
    一个任务来了
        |
        v
   ExecutionRuntime
        |
        v
   RuntimeContext
        |
        v
    BaseAgent代码
```

```text
ResearchAgentDefinition

        creates

ResearchAgentInstance

        uses

ResearchAgent(BaseAgent)

        executes

ExecutionRuntime

        runs

Task
```

| **对象**           | **解决的问题**   |
|------------------|-------------|
| AgentDefinition  | 这个Agent是什么  |
| AgentInstance    | 哪个具体Agent存在 |
| BaseAgent        | 这个Agent怎么工作 |
| ExecutionRuntime | 一次任务怎么可靠执行  |


#### 1.1 完整模型总结

```text
                    AgentDefinition
                         |
                         |
                      create
                         v
                  AgentInstance
                         |
              +----------+----------+
              |                     |
        Lifecycle State       Agent Context
                         |
                      bind
                         v
                  BaseAgent
                         |
                      execute
                         v
                ExecutionRuntime
                         |
                         v
                    Execution
                         |
                         v
                  RuntimeContext
```

### 1.1 AgentDefinition 设计

> AgentDefinition 描述一个 Agent 类型，而不是运行中的Agent。

例如： 
`ResearchAgentDefinition` 描述：

```text
名称
版本
能力
工具
模型
策略
限制
```

### 1.2: AgentRegistry —— 第一个 Multi-Agent基础设施

之前已经有类似的概念： ToolRegistry管理Tool。

现在，AgentRegistry用于管理Agent。

当前第一个版本的Registry只实现以下功能：

 - 注册：`registry.register(agent)`
 - 查找：`registry.get(name)`
 - 删除：`registry.remove(name)`
 - 查询所有：`registry.list()`

相比较ToolRegistry， AgentRegistry是有状态自治单元，Agent是长期存在的，例如：

ResearchAgent是有memory、experience、context的。

现在的架构：

```text
User
 |
Supervisor
 |
AgentRegistry
 |
+-------------+
|             |
Research    Risk
Agent       Agent
 |
Task

```

### 1.3： Agent Communication -- Agent之间如何传递任务和结果

Registry解决了如何找到Agent的问题。 现在问题是Agent之间如何协作。

利用EventBus， 把Agent也作为EventBus的使用者。

但是 Agent Message 和 Event 是有区别的：

| --- | **Event**        | **Message**        |
|-----|------------------|--------------------|
| 含义  | 事实               | 请求                 |
| 方向  | 广播               | 定向                 |
| 时间  | 发生后              | 发生前                |
| 消费者 | 多个               | 通常一个               |
| 例子  | ResearchFinished | Please analye risk |

在工业系统中，这两个通信机制都需要。

架构图：

```text
              Supervisor
                  |
             Message
                  |
                  v
            ResearchAgent
                  |
              Event
                  |
                  v
             EventBus
                  |
        +---------+---------+
        |                   |
    RiskAgent        ReportAgent

```

#### 中间层

AgentMessageRouter是中间层，负责根据receiver找Agent。

另外，Agent中添加`handle_message()`用于接收message，不要直接修改`BaseAgent.run()`。

现在完整流程：

例如：

**用户**：

`分析 Apple`

**Supervisor**:

创建：

```python
AgentMessage(
    sender="supervisor",
    receiver="research",
    message_type="RESEARCH_REQUEST",
    payload={
        "company":"Apple"
    }
)
```

**Router**:

找到：

`ResearchAgent`

**ResearchAgent**:

执行：

`Research`

完成：

发布：

`ResearchCompletedEvent`

**EventBus**:

通知：

```text
RiskAgent
ReportAgent
Metrics
Memory
```

完整架构：

```text
User
 |
Supervisor
 |
AgentMessage
 |
MessageRouter
 |
ResearchAgent
 |
ResearchCompletedEvent
 |
EventBus
 |
+-------------+
|             |
Risk       Report
```

到目前为止，Phase10架构升级为：

```text
                 SupervisorAgent
                        |
                 AgentMessage
                        |
               AgentMessageRouter
                        |
                 AgentRegistry
                        |
        +---------------+---------------+
        |                               |
 ResearchAgent                    RiskAgent
        |
        |
 EventBus
        |
 Subscribers
```

### 1.4: Shared Context —— 多Agent共享知识和隔离

防止**Context Leakage(上下文泄露)**，Agent需要有私有Context。

例如：

ResearchAgent有：

```text
    搜索历史

    中间推理

    临时变量

    工作笔记
```

RiskAgent有：

```text
    风险模型

    风险指标

    判断过程
```

不能共享。

#### **Shared Context**:

> 存放已经形成的、可以被其他Agent使用的知识。

Shared Context 和 Memory的区别：

| ---  | **Memory** | **Shared Context** |
|------|------------|--------------------|
| 所有者  | Agent      | Task/Workflow      |
| 生命周期 | 长期         | 任务期间               |
| 访问   | 私有         | 共享                 |
| 用途   | 经验         | 协作                 |

#### 和当前 ContextState 的关系

当前RuntimeContext是：一次执行上下文。

在Multi-Agent中，一次任务可能有多个Execution。例如：

```text
Apple Analysis Task
        |
        +-------------+
        |             |
 Research Exec   Risk Exec
        |
 SharedContext
```

所以，未来RuntimeContext会变为：

```text
                 TaskContext
                     |
        +----------------------+
        |                      |
 SharedContext          AgentContexts
                             |
              +--------------+--------------+
              |                             |
       Research Context              Risk Context
```

#### 最终Context层级

```text
                    AgentOS
                      |
                  TaskContext
          +-----------+-----------+
          |                       |
 SharedContext             Executions
                                  |
                         RuntimeContext
                                  |
                         AgentContext
```

**TaskContext**: 一次业务任务。如：`Analyze Apple`

**SharedContext**: 任务共享数据。如：`Financial Data`、`Research Result`

**RuntimeContext**：一次Agent执行。如：`ResearchAgent execution #1`

**AgentContext**：Agent私有状态。如：`Research Agent memory`

#### 和EventBus结合

现在，ResearchAgent完成：

```text
shared_context.set(
    "research_result",
    result
)
```

然后，发布： `ResearchCompletedEvent`

RiskAgent 收到： `ResearchCompletedEvent`，然后 读取：

```text
shared_context.get(
    "research_result"
)
```

#### 当前的Multi-Agent架构：

```text
                         User
                          |
                          v
                  SupervisorAgent
                          |
                    AgentMessage
                          |
                  MessageRouter
                          |
                  AgentRegistry
                          |
          +---------------+---------------+
          |                               |
   ResearchAgent                    RiskAgent
          |                               |
          +---------------+---------------+
                          |
                  SharedContext
                          |
                    ReportAgent
```

### 1.5 Supervisor Agent —— Multi-Agent系统的大脑

Supervisor的本质是**项目经理**。 Supervisor不是干活儿的人，它负责：

- 理解任务
- 拆解任务
- 分配任务
- 汇总任务

与Planner的区别：

| ---  | **Planner** | **Supervisor** |
|------|-------------|----------------|
| 作用范围 | Agent内部     | Agent之间        |
| 对象   | Action      | Agent          |
| 输出   | 步骤          | 任务分配           |
| 位置   | BaseAgent内部 | Multi-Agent层   |

#### Supervior核心流程

第一版：

```text
User Task
    |
    v
SupervisorAgent
    |
    |
Task Decomposition
    |
    +-------------+
    |             |
ResearchTask  RiskTask
    |             |
    v             v
ResearchAgent RiskAgent
```

输入： 

```json
{
    "task": "Analyze Apple"
}
```

输出：

```json
[
 {
  "agent": "research",
  "task": "collect financial data"
 },
 {
  "agent": "risk",
  "task": "analyze risk"
 }
]
```

然后通过 `AgentMessageRouter` 发送 Message。

#### Supervior和Workflow的关系

**Workflow**控制`系统流程`

**Supervior**控制`Agent选择`

更进一步的解释是：

Workflow 确定性控制

> 负责 Durable Execution 和生命周期控制

- Execution lifecycle
- State transition
- Checkpoint
- Retry
- Timeout
- Persistence

Supervisor 概率性决策

> 负责 Dynamic Agent Orchestration

- Agent selection
- Task decomposition
- Collaboration strategy
- Dynamic planning

在工业系统中，一般会结合两者。

如果**流程已知**，不要Supervisor。如：季度财报分析。

如果**任务未知**，需要Supervisor。如：用户说，帮我分析这个公司。

最终：

```text
              Workflow Runtime
                     |
                     |
             Supervisor Agent
                     |
          Agent Task Planning
                     |
       +-------------+-------------+
       |             |             |
 Research       Risk        Report
 Agent          Agent       Agent
```

### 1.6 从Single-Agent Runtime 到 Multi-Agent Runtime

Multi-Agent Runtime 最终分层：

```text
                    User
                     |
                     v
              Workflow Runtime
          (Durability / State)
                     |
                     v
          Supervisor Agent (optional)
                     |
             Agent Planning
                     |
              Agent Scheduler
                     |
        +------------+------------+
        |            |            |
        v            v            v
 ResearchAgent   RiskAgent   ReportAgent
        |            |            |
        +------------+------------+
                     |
              SharedContext
                     |
                EventBus
                     |
        Observability / Memory / Metrics
```

这里有3个控制层：

第一层： Workflow Runtime 负责 **可靠执行**。

第二层： Supervisor 负责 **智能决策**

第三层： Agent 负责 **领域能力**

#### 真实任务流程

用户输入： `分析Apple是否值得投资`

##### Step 1： 

创建 `TaskRequest`

Workflow创建： `WorkflowState` 例如：

```python
class InvestmentState:

    company="Apple"

    status="START"
```

然后进入 `Supervisor Node`

##### Step 2： Supervisor 分析任务

Supervisor继承 BaseAgent，所以执行仍然经过：

```text
RuntimeComponent
↓
Middleware
↓
Tracing
↓
Agent
```

Supervisor内部调用Planner，可能有两层Planner：

**Workflow Planner**： 决定 下一阶段是什么。

**Agent Planner**： 决定 自己怎么完成任务。

Supervisor Planner 示例输出：

```json
[
 {
   "agent":"research",
   "task":"collect financial data"
 },
 {
   "agent":"risk",
   "task":"analyze risk"
 }
]
```

##### Step 3: Agent Scheduler

Supervisor只产生**任务计划**，但是谁什么时候执行需要调度。 例如： Supervisor 输出 Research Task、 Risk Task。

Scheduler 发现两个任务没有依赖关系，可以并行：

```text
ResearchAgent

        \
         \
          Scheduler
        /
RiskAgent

```

##### Step 4: Agent Message

Scheduler 创建 Agent Message。例如：

Research:

```python
AgentMessage(

 sender="supervisor",

 receiver="research",

 type="TASK",

 payload={
    "company":"Apple"
 }

)
```

通过`MessageRouter.send()`发送。

流程：

```text
Scheduler
    |
AgentMessage
    |
MessageRouter
    |
AgentRegistry
    |
ResearchAgent
```

##### Step 5： ResearchAgent执行

继承BaseAgent, 执行链：

```text
ResearchAgent
        |
RuntimeComponent
        |
Middleware
        |
Tracing
        |
Planner
        |
ToolExecutor
        |
Observation
        |
Reflection
        |
Checkpoint
```

##### Step 6: 共享结果

ResearchAgent 得到：

```json
{
 "revenue_growth":8,
 "margin":45
}
```

写入： `SharedContext.set("financial_analysis", result)`

然后发布： `ResearchCompletedEvent`，进入： `EventBus`。

##### Step 7: RiskAgent

RiskAgent 收到：`ResearchCompletedEvent`或`AgentMessage`，开始执行。

读取：`SharedContext.get("financial_analysis")`

生成： `{"risk_level": "medium"}` 继续写入： `SharedContext`。

##### Step 8: ReportAgent

ReportAgent 收到 `RiskCompletedEvent`

读取：

```text
SharedContext
financial_analysis
risk_analysis
```

生成：`Investment Report`

##### Step 9: Workflow 收敛

最终 Workflow State 更新：`state.status="COMPLETED"`，保存 Checkpoint。

整个链路：

```text
User
 |
Workflow Runtime
 |
Supervisor Agent
 |
Agent Scheduler
 |
AgentMessage
 |
ResearchAgent
 |
SharedContext
 |
RiskAgent
 |
SharedContext
 |
ReportAgent
 |
Workflow Complete
 |
Checkpoint
```

## Step 2： Multi-Agent Execution Runtime

### State/Context 的职责边界

#### 第一类： Execution Runtime State

##### RuntimeContext

> 当前一次执行过程中的运行环境

生命周期：

```text
一次执行开始
↓
创建 RuntimeContext
↓
Agent / Tool / Middleware 使用
↓
Execution结束
↓
销毁
```

例如： 

用户输入：分析Tesla股票。

启动 runtime_id=A001 整个任务的 Supervisor、ResearchAgent、RiskAgent、ReportAgent 都是A001。

即：

```text
Runtime Execution
        |
        |
        +--- Supervisor Agent
        |
        +--- Research Agent
        |
        +--- Risk Agent
```

#### 第二类： Trace State

##### TraceContext

> 观察执行路径。（谁调用谁、耗时多少、哪里失败）

生命周期：

```text
Runtime开始
↓
创建Trace
↓
所有组件共享
↓
Runtime结束
↓
保存Trace
```

例如：

```text
trace_id=001

Supervisor Agent span
        |
        |
        Research Agent span
        |
        |
        Tool span
```

#### 第三类：Execution Loop State

##### LoopState

生命周期：

```text
Agent执行循环
↓
step++
↓
action
↓
observation
↓
结束
```

> LoopState 属于 Agent Execution，不属于整个Runtime。

#### 第四类：Agent State

##### Agent Private State

生命周期：

```text
Agent实例
↓
执行
↓
更新
↓
Checkpoint保存
↓
恢复
```

例如：

ResearchAgent： visited_sources/research_notes/analysis_history

完全隔离。

#### 整体结构

```text
                                 User Request
                                      |
                                      |
                                      v
                         +----------------------+
                         |   ExecutionRuntime   |
                         +----------------------+
                                      |
                                      |
                                      v
                         +----------------------+
                         |   RuntimeContext     |
                         |----------------------|
                         | runtime_id           |
                         |                      |
                         | TraceContext         |
                         | Event Context        |
                         | SharedContext        |
                         | Execution Metadata   |
                         +----------------------+
                                      |
                                      |
                 +--------------------+--------------------+
                 |                    |                    |
                 v                    v                    v
        +----------------+   +----------------+   +----------------+
        | Supervisor     |   | ResearchAgent  |   | RiskAgent      |
        | Execution      |   | Execution      |   | Execution      |
        +----------------+   +----------------+   +----------------+
                 |                    |                    |
                 |                    |                    |
                 v                    v                    v
        +----------------+   +----------------+   +----------------+
        |AgentExecution  |   |AgentExecution  |   |AgentExecution  |
        |Context         |   |Context         |   |Context         |
        +----------------+   +----------------+   +----------------+
        |                |   |                |   |                |
        | AgentIdentity  |   | AgentIdentity  |   | AgentIdentity  |
        |                |   |                |   |                |
        | AgentContext   |   | AgentContext   |   | AgentContext   |
        |                |   |                |   |                |
        | LoopState      |   | LoopState      |   | LoopState      |
        |                |   |                |   |                |
        | Private State  |   | Private State  |   | Private State  |
        +----------------+   +----------------+   +----------------+
```

#### 最终职责表

| 对象                    | 代表        | 生命周期   | 共享        |
| --------------------- | --------- | ------ | --------- |
| ExecutionRuntime      | 一次运行调度    | 请求级    | 否         |
| RuntimeContext        | Runtime环境 | 请求级    | 所有Agent共享 |
| TraceContext          | 调用链追踪     | 请求级    | 共享        |
| SharedContext         | 协作数据      | 请求级    | 共享        |
| AgentRuntime          | Agent调用入口 | 调用级    | 共享服务      |
| AgentExecutionContext | Agent一次执行 | Agent级 | 隔离        |
| AgentContext          | Agent私有状态 | Agent级 | 隔离        |
| LoopState             | Agent循环状态 | Agent级 | 隔离        |


### 

## Step 3: Checkpoint Runtime 边界迁移

在Multi-Agent下，Checkpoint模型变成

```text
ExecutionCheckpoint

    runtime_id

    RuntimeState

        trace metadata

        shared context

    AgentExecutions

        agent_id

        execution state

        loop state
```

当前目标： 增加 `AgentExecutionCheckpoint`

完成后结构：

```text
                 Checkpoint
                    |
        +-----------+------------+
        |                        |
 Runtime Snapshot          Agent Snapshots

 shared_context            ResearchAgent

 trace metadata            RiskAgent

                           ReportAgent
```

## Step 4: AgentResult 与 Agent-to-Agent Communication

上一节完成了 Multi-Agent Runtime的两个基础：

 - Execution Boundary。 确定 RuntimeContext表示一次任务执行共享上下文； AgentExecutionContext 表示单个Agent的私有执行上下文。
 - Durable Boundary。确定 Agent状态可以保存；多个Agent状态可以独立恢复。

### AgentResult 设计 （重复设计了）

**TaskResult**: 整个Workflow或Runtime最终结果。

**AgentResult**： 一次Agent invocation的结果。

## 当前项目中示例ResearchAgent的能力进化路线如下：

```text
Step 5
Task
 ↓
ResearchAgent
 ↓
Report
```

↓

```text
Step 6
Task
 ↓
ResearchAgent
 ↓
Tool
 ↓
Report
```

↓

```text
Step 7
Task
 ↓
ResearchAgent
 ↓
Agent Logic
 ↓
Tool Selection
 ↓
Tool
 ↓
Report
```

↓ 下一步

```text
Step 8

Task
 ↓
ResearchAgent
 ↓
LLM
 ↓
Decision
 ↓
ToolRequest
 ↓
ToolExecutor
 ↓
Tool
 ↓
Observation
 ↓
LLM
 ↓
ResearchReport
```

## Step 8: Research Agent + LLM Provider + Tool Decision

> 这一步不是上LLM直接“完成研究”，而是让LLM参与**Agent Decision**。

```text
TaskRequest
    ↓
ResearchAgent
    ↓
LLM
    ↓
Decision
    ↓
ToolRequest
    ↓
ToolExecutor
    ↓
MarketResearchTool
    ↓
ToolResult
    ↓
ResearchAgent
```

需要注意的是： **LLM不应该直接返回ToolRequest**，因为LLM是不可信来源。

## Step 9: 统一 Observation 边界

- `ToolResult`是**Tool Runtime的结果**
- `Observation`是**Agent执行环境看到的反馈**
- `AgentResult`是**Agent于调用方之间的通信结果**

但是当前 `ResearchAgent`中： `observations=[tool_result]`,需要区分这三个对象。

最终关系如下：
```text
                    ToolExecutor
                         │
                         ▼
                    ToolResult
                         │
                         │ convert
                         ▼
                    Observation
                         │
                         ▼
                  Agent internal state
                         │
                         │
                         ▼
                    AgentResult
                         │
                         ├── output
                         ├── observations
                         └── metadata
```

Observation处理完成后，ResearchAgent一次执行的完整链路是：

```text
TaskRequest
    │
    ▼
ResearchAgent
    │
    ├── ResearchTask
    │
    ├── LLMProvider
    │      │
    │      ▼
    │   LLMResponse
    │      │
    │      ▼
    │   Tool decision
    │
    ▼
ToolRequest
    │
    ▼
ToolExecutor
    │
    ▼
Tool
    │
    ▼
ToolResult
    │
    ▼
Observation
    │
    ▼
ResearchAgent
    │
    ▼
ResearchReport
    │
    ▼
AgentResult
```

## Step 10: ResearchAgent 多轮 Agent Loop

## Step 11: Supervisor Agent实现

## Step 12: Supervisor Multi-Agent Loop

## Step 13: SharedContext 跨 Agent 协作

当前Agent的结果只能通过AgentResult返回给Supervisor，但是Multi-Agent系统需要支持：

```text
ResearchAgent
       │
       │ 写入共享研究信息
       ▼
RuntimeContext.shared_context
       │
       ▼
Supervisor
       │
       │ 再调用其他 Agent
       ▼
RiskAgent / StockAgent / ReportAgent
```

另外，SupervisorAgent不应该使用Observation充当共享数据。

**Observation**
> Agent 内部推理过程的数据。

**AgentResult**
> Agent 执行完成后，对调用方公开的结果。

**SharedContext**
> 同一次 Execution 中多个 Agent 共享的业务状态。

结构为：

```text
┌───────────────────────────────────────────┐
│ AgentExecutionContext                     │
│                                           │
│  state                                    │
│  loop                                     │
│    └── observation_history                │
│                                           │
│  Agent private                            │
└───────────────────────────────────────────┘
                    │
                    │ Agent完成执行
                    ▼
┌───────────────────────────────────────────┐
│ AgentResult                               │
│                                           │
│  success                                  │
│  output                                   │
│  metadata                                 │
│                                           │
│  Agent → Agent communication              │
└───────────────────────────────────────────┘
                    │
                    │ 业务结果
                    ▼
┌───────────────────────────────────────────┐
│ SharedContext                             │
│                                           │
│  research.report                          │
│  ...                                      │
│                                           │
│  Execution-wide shared business state     │
└───────────────────────────────────────────┘
```

## Step 14: Multi-Agent State Boundary & Checkpoint

### 再次确认结构

```text
ExecutionRuntime
        │
        ▼
RuntimeContext
        │
        ├── trace
        ├── shared_context
        └── runtime_id
                │
        ┌───────┴────────┐
        ▼                ▼
Supervisor           ResearchAgent
ExecutionContext    ExecutionContext
        │                │
        ├── state        ├── state
        │                │
        └── loop         └── loop
             │                 │
             ▼                 ▼
        Observation       Observation
             │                 │
             ▼                 ▼
       Agent reasoning   Agent reasoning
```


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


# Phase 10： Multi-Agent Runtime

---

## Step 1: 重新定义 Agent Model——Agent、AgentInstance、Runtime、Role 边界设计

当前CodeAgent的意义：

 - Agent类型: 一类Agent的定义
 - Agent实例
 - Agent Role： Coder是个角色，类似：Supervisor、Reviewer、Tester
 - Runtime Component： 是Runtime内执行单元

在Single Agent中是把以上全部揉在一起了。

### Agent 和 Runtime 的关系

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

### AgentRuntime 和 ExecutionRuntime

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

### 完整 Multi-Agent Runtime 流程

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


### Step 1 完整模型总结

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


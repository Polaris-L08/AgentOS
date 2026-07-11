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


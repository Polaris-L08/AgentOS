# Phase 10: Autonomous Research Agent

---

> 目标： 构建第一个真实 Agent Application
> 选择方向： AI Research Analyst Agent

## Step 1: 从 Runtime Kernel 到 Autonomous Research Agent 的架构设计

### 回顾当前状态

当前能力： Task -> Runtime Loop -> Planner -> Action -> Tool Executor -> Observation -> Context Update -> Reflection -> Checkpoint -> Repeat

已经具备： 

 - Durable Execution
 - Event-driven Architecture
 - Middleware
 - Tracing
 - Runtime Context
 - Error Boundary

这些是保证： **Agent能够可靠的运行**， 但是没有解决： **Agent应该如何完成一个目标**。

当前系统的问题：

1. Task和Goal没有区分。 真实的Agent需要区分
```text
Goal
↓
Plan
↓
Task
↓
Action
↓
Observation
```

例如， 用户输入：分析Tesla投资价值。

Goal: 完成 Tesla 投资研究

Plan： 收集财务数据、分析竞争环境、评估风险、生成报告

Task： 获取财务数据

Action： 调用 Financial API

2. Planner 职责太弱：

当前的Planner返回Action，但是高级的Agent中Planner不应该直接决定工具，Executor负责具体的执行。

3. Observation不应该只是ToolResult

Observation应该是：Agent对外部世界的一次认知更新。

### Research Agent 架构

```text
                    Research Goal
                         |
                         v
                 Research Agent
                         |
        +----------------+----------------+
        |                |                |
     Planner          Memory          Reflection
        |
        |
     Research Plan
        |
        |
     Executor
        |
        |
      Tools
        |
        |
   Observation
        |
        |
    Context Update
        |
        |
     Report
```

## Step 2: Research Task Domain Model 设计

```text
User Request
      |
      v
Runtime TaskRequest
      |
      v
Agent Goal
      |
      v
Agent Tasks
      |
      v
Runtime Actions
```

**Runtime Task**: 一次执行请求。

**Agent Task**: Agent为完成目标拆出的工作单元。

### Research Agent领域模型设计

#### ResearchGoal(核心)

> 用户希望Agent最终完成什么。

#### ResearchPlan

> Agent对Goal的当前解决方案。

Plan是动态的，不是WorkFlow。

#### ResearchTask(核心)

> Agent当前需要完成的一个研究子目标。

#### ResearchFinding

> 子目标的结论。

#### ResearchReport(核心)

> 最终输出。

完整关系：

```text
                  User Request
                       |
                       v
              ResearchGoal
                       |
                       v
              ResearchPlan
                       |
          +------------+------------+
          |                         |
     ResearchTask             ResearchTask
          |
          |
     ResearchFinding
          |
          |
      ResearchReport
```

事实上，`ResearchPlan`和`ResearchFinding`是过度设计，尤其是Finding。

Plan层在以下场景下考虑引入：
 - 复杂长任务： 完整的行业研究，可能持续几个小时。
 - Human-in-the-loop： 需要人类专家介入的场景。展示Plan，然后等待用户确认。
 - Multi-Agent: 多Agent协作

## Step 3： Agent Execution Model Design

目标是确定：

> Runtime、Agent、Planner、Executor、Reflection 的最终职责边界。

核心问题：

> 如何从 Single Agent Runtime 演进到 Autonomous Agent Framework，而不会退化为 Workflow Engine。

模型：

```text
                Runtime Kernel
                     |
                     |
          Agent Execution Runtime
                     |
                     |
                   Agent
                     |
        +------------+------------+
        |            |            |
     Planner     Reflection    Memory
        |
        |
    AgentDecision
        |
        |
     Executor
        |
        |
      Tools
```

### Runtime Kernel

> 负责可靠执行

包括：

 - RuntimeContext
 - Middleware
 - Trace
 - Checkpoint
 - EventBus
 - Exception Boundary

### Agent Execution Runtime

> 负责驱动 Agent 运行

负责：

 - 调用 Agent
 - 管理生命周期
 - 连接 Runtime Kernel
 - 调度 Action

### Agent

> Agent 是决策主体

决定下一步做什么

### Planner

属于Agent，因为不同Agent的规划方式不同

### Reflection

属于Agent，不是**Runtime 每次执行后调用 Reflection**， 而是**Agent 根据需要反思**

例如：

```text
Observation
↓
Reflection
↓
发现缺少数据
↓
生成新 Task
```

### Executor

Executor 属于执行能力。 它负责：

```text
Decision
↓
Action
↓
Tool
```

例如：

```text
Agent: 我要获取财务数据

Executor: 调用 FinancialTool
```

### AgentOS 与 LangGraph 的区别

| ---  | LangGraph | AgentOS        |
|------|-----------|----------------|
| 核心抽象 | Graph     | Agent Decision |
| 控制主体 | Graph     | Agent          |
| 节点   | Agent     | 能力模块           |
| 流程来源 | Develop定义 | Agent产生        |
| 动态范围 | Graph范围内  | Agent能力范围内     |
| 重点   | 编排        | 自治             |

## Step 4： 

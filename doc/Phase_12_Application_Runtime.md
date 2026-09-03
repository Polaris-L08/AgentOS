# Phase 12: Application Runtime

## Lesson 1: Application/Session/Execution/Agent Invocation 生命周期模型

### 回顾Phase11的最终边界

```text
Agent Instance
    │
    ├── AgentContext
    │
    └── MemoryRuntime
           │
           ▼
    AgentExecutionContext
           │
           ▼
      RuntimeContext
```

其中：

**AgentContext**:

> Agent Instance 生命周期，代表Agent的长期状态。

**MemoryRuntime**:

> Agent Instance 生命周期，是Agent长期拥有的Capability。

**AgentExecutionContext**:

> 一次Agent Invocation。 每次Agent被调用，都有自己的Execution Context。

**RuntimeContext**：

> 一次Execution。 一个Execution内可以产生多个Agent Invocation。

### 建立四层模型

```text
Application
    │
    ├── Session
    │      │
    │      ├── Execution
    │      │      │
    │      │      ├── Agent Invocation
    │      │      │
    │      │      ├── Agent Invocation
    │      │      │
    │      │      └── ...
    │      │
    │      └── Execution
    │
    └── Session
```

```text
Application
    ↓
Session
    ↓
Execution
    ↓
Agent Invocation
```

#### 第一层： Application

> 一个可以被用户或外部系统调用的完整Agent应用实例。

Application负责组装：

```text
Application
    │
    ├── Agents
    ├── Workflow
    ├── Tools
    ├── Memory
    ├── EventBus
    ├── Middleware
    └── Runtime
```

> Application 是 **Composition Boundary(组合边界)**。

#### 第二层： Session

> Application 与一个持续交互主体之间的一段持续交互上下文。

```text
User
 │
 │ "帮我分析 NVIDIA"
 ▼
Session
 │
 ├── Execution #1
 │
 └── Execution #2
```

#### 第三层： Execution

> 一次完整的 User Request/Task 执行过程。

```text
User Request
     │
     ▼
Execution
     │
     ├── Planner
     ├── Agent A
     ├── Tool
     ├── Agent B
     ├── Reflection
     └── Result
```

Execution有明确的开始和结束：

```text
Created
   ↓
Running
   ↓
Completed
```

#### 第四层： Agent Invocation

> 每一次Agent被调用 都是一个Agent Invocation。

#### 架构图

```text
                         Application
                              │
                              │ owns
                              ▼
                           Session
                              │
                         creates / owns
                              │
                              ▼
                          Execution
                              │
                         owns context
                              │
                              ▼
                       RuntimeContext
                              │
                  ┌───────────┼───────────┐
                  │           │           │
                  ▼           ▼           ▼
             Invocation    Invocation   Invocation
                  │           │           │
                  ▼           ▼           ▼
          AgentExecutionContext
                  │
                  ▼
               Agent
                  │
          ┌───────┴────────┐
          ▼                ▼
    AgentContext      MemoryRuntime
```

需要注意的是：`AgentContext`和`MemoryRuntime`不是由Invocation创建的，它们属于Agent Instance。

### 确认四种生命周期

| **对象**           | **生命周期**        | **主要职责**                 |
|------------------|-----------------|--------------------------|
| Application      | Application生命周期 | 组装和管理整个Agent Application |
| Session          | 多次交互生命周期        | 组织多个Execution            |
| Execution        | 单次请求生命周期        | 执行一个完整任务                 |
| Agent Invocation | 单次Agent调用       | 执行某个Agent                |

### 最终生命周期图

```text
                         ┌──────────────────┐
                         │   Application    │
                         │                  │
                         │ owns Components  │
                         └────────┬─────────┘
                                  │
                                  │
                       ┌──────────▼──────────┐
                       │       Session       │
                       │                     │
                       │ groups Executions   │
                       └──────────┬──────────┘
                                  │
                    ┌─────────────┼─────────────┐
                    │             │             │
                    ▼             ▼             ▼
               Execution 1   Execution 2   Execution 3
                    │             │
                    ▼             ▼
              RuntimeContext RuntimeContext
                    │
                    │
             ┌──────┴──────┐
             │             │
             ▼             ▼
        Agent Invocation  Agent Invocation
             │             │
             ▼             ▼
      AgentExecutionContext
             │
             ▼
        Agent Instance
             │
       ┌─────┴─────┐
       ▼           ▼
 AgentContext   MemoryRuntime
```

```text
Application
    │
    ├────────────── owns ──────────────┐
    │                                  ▼
    │                            Agent Instance
    │                                  │
    │                            ┌─────┴─────┐
    │                            ▼           ▼
    │                       AgentContext MemoryRuntime
    │
    └── Session
          │
          └── Execution
                │
                └── Agent Invocation
                         │
                         └── uses ──► Agent Instance
```


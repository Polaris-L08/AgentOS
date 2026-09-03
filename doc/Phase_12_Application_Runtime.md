# Phase 12: Application Runtime

课程路线

```text
Lesson 1
Application / Session / Execution / Agent Invocation 生命周期模型

Lesson 2
Application Model & Ownership

Lesson 3
Application Lifecycle

Lesson 4
Application Assembly / Component Registry

Lesson 5
Session Runtime

Lesson 6
Execution Creation & Execution Handle

Lesson 7
Application → AgentRuntime Integration

Lesson 8
Application-level Event / Middleware Integration

Lesson 9
Application Configuration

Lesson 10
Application Execution API

Lesson 11
Application Error / Cancellation / Shutdown

Lesson 12
Application + Checkpoint / Recovery

Lesson 13
Application Integration Tests

Lesson 14
Phase12 Final Integration & Acceptance
```

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


## Lesson 2: Application Model & Ownership

本节建立一个非常小的模型：

```text
AgentApplication
    │
    ├── application_id
    ├── name
    │
    └── agents
          │
          ├── agent_id → Agent Instance
          ├── agent_id → Agent Instance
          └── ...
```

现在暂时不加入：

```text
Session
Workflow
Tool
Memory
EventBus
Middleware
```

### Ownership

Application持有：`AgentRuntime、ExecutionRuntime、Agent instances`

```text
Application
    │
    ├── AgentRuntime
    │
    ├── ExecutionRuntime
    │
    └── Agents
```

但是Application**不拥有RuntimeContext**。 因为RuntimeContext是一次Execution的对象。

所以：

```text
Application
    ├── AgentRuntime
    ├── ExecutionRuntime
    └── Agent
          │
          ├── AgentContext
          └── MemoryRuntime


Execution
    └── RuntimeContext
```


## Lesson 3: Application Lifecycle

### Application Lifecycle的第一版定义

```text
ApplicationState

CREATED
INITIALIZED
RUNNING
STOPPING
STOPPED
```

**CREATE**: Application对象已经创建，但是Application尚未完成初始化。

**INITIALIZED**： Application 已经完成初始化，可以准备运行。不代表已经接受 User Request。

**RUNNING**： Application 正式进入运行状态。

**STOPPING**： Application 正在关闭。因为真实系统中 `stop()` 通常不是瞬间完成的。

**STOPPED**: Application 已经停止。

### 完整状态图

```text
                    ┌──────────────┐
                    │   CREATED    │
                    └──────┬───────┘
                           │
                      initialize()
                           │
                           ▼
                  ┌────────────────┐
                  │  INITIALIZED   │
                  └───────┬────────┘
                          │
                       start()
                          │
                          ▼
                  ┌────────────────┐
                  │    RUNNING     │
                  └───────┬────────┘
                          │
                       stop()
                          │
                          ▼
                  ┌────────────────┐
                  │    STOPPING    │
                  └───────┬────────┘
                          │
                    shutdown done
                          │
                          ▼
                  ┌────────────────┐
                  │    STOPPED     │
                  └────────────────┘
```
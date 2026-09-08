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


## Lesson 4: Application Assembly / Component Registry

本节目标：

> 防止AgentApplication变成God Object，引入 Application Assembly。
> 
> 把“创建和组装组件” 与 “Application使用这些组件运行” 分开。

形成：

```text
Application Assembly
        │
        │ creates / registers
        ↓
Component Registry
        │
        │ provides
        ↓
AgentApplication
        │
        ↓
Runtime Execution
```

```text
             ApplicationAssembly
                     │
             ┌───────┴───────┐
             ↓               ↓
      ComponentRegistry   Agent instances
             │               │
             └───────┬───────┘
                     ↓
              AgentApplication
```

### 概念区分

##### **Component** —— Runtime能力组件

Component是 AgentOS Runtime中长期存在的能力组件。例如：

```text
AgentRuntime
ExecutionRuntime
WorkflowRuntime
ToolExecutor
EventBus
CheckpointCoordinator
MemoryRuntime
```

解决的是：“系统具备什么运行能力？” 例如：

```text
AgentRuntime
    → 如何执行 Agent

ExecutionRuntime
    → 如何创建和管理一次 Execution

EventBus
    → 如何发布事件

MemoryRuntime
    → 如何访问 Memory

ToolExecutor
    → 如何执行 Tool

CheckpointStore
    → 如何保存 / 恢复 Checkpoint
```

##### **Agent** —— Application的能力实例

Agent解决的是：“这个应用具有什么智能能力？”，例如：

```text
Research Application：
ResearchAgent
SupervisorAgent

投资助手：
InvestmentResearchAgent
RiskAnalysisAgent
PortfolioAgent
```

##### **Application** —— 一个完整的Agent应用

Application解决的是： “我要把哪些 Agent 和哪些 Runtime 能力组合成一个可以运行的应用？”，例如：

```text
Research Application
│
├── SupervisorAgent
├── ResearchAgent
│
├── AgentRuntime
├── ExecutionRuntime
├── EventBus
├── Middleware
├── Checkpoint
└── ...
```

Application不是一个具体能力，是一个：**Composition + Ownership + Lifecycle Boundary**

```text
Application
    │
    ├── owns Agents
    ├── owns / references Runtime Components
    └── owns Application Lifecycle
```

### 目标架构

```text
                 Application Assembly
                         │
          ┌──────────────┴──────────────┐
          │                             │
          ▼                             ▼
     Components                      Agents
          │                             │
          │                             │
    ┌─────┴──────┐              ┌───────┴──────┐
    ▼            ▼              ▼              ▼
AgentRuntime ExecutionRuntime SupervisorAgent ResearchAgent
          │                             │
          └──────────────┬──────────────┘
                         ▼
                  AgentApplication
```

```text
component_registry.py
    ↓
管理 Application Components

application_assembly.py
    ↓
负责组装 Application

application.py
    ↓
运行时 Application Boundary
```

### Lesson 4 最终结论

#### 架构图

```text
                    ┌─────────────────────────┐
                    │   ApplicationAssembly    │
                    │                         │
                    │  composition root       │
                    └────────────┬────────────┘
                                 │
                    ┌────────────┴────────────┐
                    │                         │
                    ▼                         ▼
          ComponentRegistry             Agent Instances
                    │                         │
          ┌─────────┴─────────┐              │
          │                   │              │
          ▼                   ▼              │
    AgentRuntime      ExecutionRuntime       │
          │                   │              │
          └─────────┬─────────┘              │
                    ▼                        ▼
             ┌──────────────────────────────────┐
             │          AgentApplication         │
             │                                  │
             │  Application Identity             │
             │  Agent Ownership                  │
             │  Runtime Services                 │
             │  Application Lifecycle             │
             └──────────────────────────────────┘
```

**Assembly** 负责： 

> Composition（组装）

**Registry** 负责：

> Lookup / Ownership of references（组件引用管理）

**Application** 负责：

> Application Boundary + Lifecycle（应用边界与生命周期）

**Runtime** 负责：

> Execution（执行）

**Agent** 负责：

> Agent Capability / Behavior（Agent 能力与行为）


## Lesson 5: Session Runtime —— 建立Session生命周期与 Application 的 Session Ownership

> Application如何创建、持有和管理Session。

建立：

```text
AgentApplication
       │
       │ owns
       ▼
SessionManager
       │
       ├── Session A
       ├── Session B
       └── Session C
```

建立生命周期关系：

```text
Application Lifetime
       │
       └── Session Lifetime
                │
                └── Execution Lifetime
                         │
                         └── Agent Invocation Lifetime
```

### Session 与现有Context的区分

#### AgentApplication

Application 生命周期：

```text
CREATED
   ↓
INITIALIZED
   ↓
RUNNING
   ↓
STOPPING
   ↓
STOPPED
```

#### Session

一个持续的用户交互会话： Session A

生命周期比一次 Execution 长。

#### RuntimeContext

一次 Execution 的运行时上下文：

```text
Execution #1
    └── RuntimeContext #1
```

#### AgentExecutionContext

一次 Agent Invocation 的上下文：

```text
Execution #1
    ├── ResearchAgent
    │     └── AgentExecutionContext #1
    │
    └── RiskAgent
          └── AgentExecutionContext #2
```

#### AgentContext

属于一个长期存在的 Agent Instance：

```text
ResearchAgent instance
       │
       └── AgentContext
```

#### Memory

Memory 是信息持久化/检索能力，不是 Session 本身。

### Lesson 5的最终关系

```text
AgentApplication
│
├── Agents
│
├── Runtime Components
│
└── SessionManager
       │
       ├── Session A
       │      │
       │      ├── Execution A1
       │      ├── Execution A2
       │      └── Execution A3
       │
       └── Session B
              │
              ├── Execution B1
              └── Execution B2
```

> `SessionManager` 不持有 `RuntimeContext`。

> `Session` 不持有 `RuntimeContext`。

> `Session` 也不直接持有 `AgentContext`。

这几个边界必须保持干净。

### Lesson 5完成后的架构

```text
                         AgentApplication
                                │
             ┌──────────────────┼──────────────────┐
             │                  │                  │
        Application         Agent Ownership   Runtime Services
        Lifecycle                │                  │
             │                   │                  │
             │              BaseAgent         AgentRuntime
             │                   │            ExecutionRuntime
             │                   │
             │              AgentContext
             │                   │
             │              MemoryRuntime
             │
             └────────── SessionManager
                              │
                    ┌─────────┴─────────┐
                    │                   │
                 Session A           Session B
                    │
              (future executions)
```

生命周期层次：

```text
Application Lifetime
        │
        └── Session Lifetime
                │
                └── Execution Lifetime
                        │
                        └── Agent Invocation Lifetime
```

对象对应：

```text
Application
    ↓
AgentApplication

Session
    ↓
Session

Execution
    ↓
RuntimeContext        ← 当前已有
                      ← Lesson 6 将完善其生命周期管理

Agent Invocation
    ↓
AgentExecutionContext
```

### 重要结论

> Application 管应用，
> 
> Session 管会话边界，
> 
> Execution 管一次执行，
> 
> AgentExecutionContext 管一次 Agent 调用。

AgentContext 是 **Agent Instance 的长期上下文**。

Memory 是 **信息存储与检索能力**。


## Lesson 6: Execution Creation & Execution Handle

> 一次 Execution 没有一个明确的生命周期对象。

`RuntimeContext`是上下文（Context），不是生命周期控制器（Lifecycle Controller）。

引入 `ExecutionHandle`。

> Application 如何创建一次 Execution，以及如何明确管理这次 Execution 的生命周期。

### Lesson 6 完成后的结构

目标：

```text
ExecutionRuntime
      │
      │ create_execution()
      ▼
ExecutionHandle
      │
      ├── execution_id
      ├── runtime_context
      ├── closed
      │
      └── close()
```

`RuntimeContext`是Execution的运行时上下文。

`ExecutionHandle`时 对这次Execution生命周期的控制句柄。

因此：

```text
ExecutionHandle
      │
      └── owns lifecycle
              │
              └── RuntimeContext
```

而不是让 `RuntimeContext`自己承担生命周期管理。

### 重新理解ExecutionRuntime

在Lesson 6之后 ExecutionRuntime不再只是 RuntimeContext Factory，

而是： **Execution Lifecycle Service**。

职责：

```text
create_execution()
        ↓
创建 Execution

create_context()
        ↓
底层 Context 创建

close()
        ↓
Execution Finalization
```

### 核心结论

> RuntimeContext 描述 Execution，而 ExecutionHandle 管理 Execution。

```text
ExecutionRuntime
    = 创建/结束 Execution 的服务

ExecutionHandle
    = 一次具体 Execution 的生命周期句柄

RuntimeContext
    = 一次具体 Execution 的运行时上下文
```

三者关系：

```text
ExecutionRuntime
       │
       │ create
       ▼
ExecutionHandle
       │
       │ exposes
       ▼
RuntimeContext
```

完整生命周期：

```text
Application
    │
    └── Session
          │
          └── ExecutionHandle
                 │
                 └── RuntimeContext
                        │
                        └── AgentExecutionContext
                               │
                               └── Agent
```


## Lesson 7: Application -> AgentRuntime Integration

> 建立 Application -> AgentRuntime 的正式集成边界

### 设计原则

当前有三个不同层次：

**Application** 负责：“这个 AgentOS Application 里有哪些运行时组件，以及它们如何协作。”，包括：

```text
Ownership
Lifecycle
Composition
Runtime Coordination
```

**ExecutionRuntime** 负责： “创建和结束一次执行。” 包括：

```text
Execution Creation
Execution Finalization
RuntimeContext
```

**AgentRuntime** 负责： “如何真正运行一个 Agent。” 包括：

```text
Agent Invocation
AgentExecutionContext
Agent Lifecycle Boundary
Agent Events
Middleware
```

正确的方向是：

```text
Application
    │
    │ obtains Agent
    │
    ▼
AgentRuntime
    │
    │ execute(agent, task, runtime_context)
    ▼
Agent
```

Application 是**协调者（Coordinator）**， AgentRuntime是**执行者（Executor）**。

### Lesson 7 完成后的架构

```text
                         AgentApplication
                                │
          ┌─────────────────────┼─────────────────────┐
          │                     │                     │
          ▼                     ▼                     ▼
   SessionManager       ExecutionRuntime        AgentRuntime
          │                     │                     │
          ▼                     ▼                     │
       Session          ExecutionHandle             │
                                │                   │
                                ▼                   ▼
                         RuntimeContext          Agent
                                                    │
                                                    ▼
                                         AgentExecutionContext
```

> Application 管理边界，ExecutionRuntime 管理 Execution，AgentRuntime 管理 Agent Invocation。


## Lesson 8: Application Runtime Integration

> Application接入Event和Middleware。

目标形成：

```text
                    AgentApplication
                           │
              ┌────────────┴────────────┐
              │                         │
       Application Middleware      Application Events
              │                         │
              └────────────┬────────────┘
                           │
                           ▼
                     AgentRuntime
                           │
                  ┌────────┴────────┐
                  │                 │
             Agent Middleware   Agent Events
                  │                 │
                  └────────┬────────┘
                           ▼
                         Agent
```

### Middleware 分层

Phase 9 中确立了以下原则：

> Runtime operation 如果属于 Runtime Boundary，就必须经过 RuntimeComponent.invoke()。

RuntimeComponent.invoke() 是Runtime Middleware的统一入口。

因为 `AgentApplication` 不是普通的 Runtime Component，而是 **Application Boundary(应用边界)**。

所以，Application组合Middleware，而不是继承 RuntimeComponent。

> Application Middleware 的职责
>
> Application-level operation




## Lesson 9: Application Configuration + Assembly

本节目标：

> 让 ApplicationAssembly 成为真正的 Application Composition Root。

### Configuration 和 Assembly 的区分

#### Configuration 

描述： “我要什么样的 Application？”， 例如：

```text
application_id = "agentos"
name = "AgentOS"

middleware = [...]
event publisher = ...
```

是 **声明性配置（Declarative Configuration）**。

#### Assembly

描述： “如何把这些东西组装成 Application？”

```text
Configuration
     ↓
Assembly
     ↓
Application
```

而不是：

```text
Configuration
     ↓
Application 自己创建一切
```

### 完成后的架构

```text
                  ApplicationConfig
                         │
                         ▼
                ApplicationAssembly
                         │
          ┌──────────────┼───────────────┐
          │              │               │
          ▼              ▼               ▼
    AgentRuntime   ExecutionRuntime   EventBus
          │                              │
          │                              │
          └──────────────┬───────────────┘
                         │
                         ▼
                 AgentApplication
                         │
              ┌──────────┼──────────┐
              │          │          │
           Session    Agents    Lifecycle
              │
              │
              ▼
         Application Runtime
```


## Lesson 10： Public Application Execution API

本节目标：

> 把底层 Execution Runtime 正式封装成 Application 的公共执行 API。

### 目前的问题

当前架构下，用户想要执行一个Agent：

```python
execution_handle = execution_runtime.create_execution()

result = await application.invoke_agent(
    agent_id="research",
    task=task,
    execution_handle=execution_handle,
)

await execution_handle.close()
```

这个过程暴漏了太多 Runtime 内部概念。

希望的理想情况是：

```text
User
 │
 ▼
Application.execute(task)
 │
 ├── create Execution
 │
 ├── invoke Agent
 │
 ├── close Execution
 │
 └── return TaskResult
```

Application API也不能简单的写为： `await application.execute(task, agent_id="research")`

因为这会把 API 固定为： `User → Application → 指定 Agent`

实际的 Application API 应该为： `application.execute(task)`,把任务交给 Application的执行编排层（Execution Orchestration）。

但是当前没有SupervisorAgent，所以先引入 `ApplicationExecutor`作为临时替代。


## Lesson 11: Application Error/Cancellation/Shutdown

> 执行异常处理

### 三个问题

#### Agent 执行异常

> 业务异常不能导致Execution生命周期泄露。

保证：

```text
Agent failure
      │
      ▼
异常向上传播
      │
      ▼
Application.execute()
      │
      └── ExecutionHandle finally.close()
```

#### Cancellation

`asyncio.CancelledError`不是普通的业务异常，不能当作 `RuntimeError`处理。

`asyncio.CancelledError`代表**当前Execution被请求停止**。

正常语义应该为：

```text
Cancellation
    │
    ▼
Execution finally cleanup
    │
    ▼
CancelledError continues propagating
```

#### Application.stop()

当前的Application lifecycle是：

```text
CREATED
   │
   ▼
INITIALIZED
   │
   ▼
RUNNING
   │
   ▼
STOPPING
   │
   ▼
STOPPED
```

目前 `Application.stop()` 只是调用 ` _shutdown_components()`。这在Lesson 3是合理的。

明确： **Application shutdown 和 Execution shutdown 是两个不同层级的生命周期**。

### 明确 Error Boundary

> 原则： Application 不吞业务异常。

```text
Agent
  ↓
AgentRuntime
  ↓
Application
  ↓
Caller
```

错误应该原样传播。

### Cancellation

> Cancellation 不应该破坏 Execution cleanup。

### Shutdown

### Lesson 11的核心状态机

```text
CREATED
   │
 initialize()
   ▼
INITIALIZED
   │
 start()
   ▼
RUNNING
   │
 stop()
   ▼
STOPPING
   │
   ├───────────────┐
   │               │
 success          failure
   │               │
   ▼               ▼
STOPPED          STOPPING
```

### 关键的工业级原则

建立： **Error Propagation VS Error Handling**

#### Error Propagation

异常向上传播。 

Application不应该随意把 RuntimeError 转换成 `TaskResult(success = False,...)`

否则调用方无法区分： 正常完成但业务结果失败 与 Runtime execution failure。

#### Error Handling

Runtime 可以负责：

```text
cleanup
trace
event
middleware
checkpoint
logging
```

但处理完以后： `raise`，仍然可以让异常继续传播。

所以： Error Propagation 和 Error Handling 可以同时存在。


## Lesson 12: Application + Checkpoint / Recovery

Phase 7 中建立了Checkpoint、CheckpointStore等，但是这些东西目前还是相对独立的，并没有和Application连接。

### Checkpoint的层级

现在由三种不同的生命周期：

```text
Application
    │
    ├── Session
    │
    └── Execution
            │
            ├── RuntimeContext
            │
            └── AgentExecutionContext
```

Checkpoint应该属于 **Execution 层**，而不是Application层。

Application只提供 **Recovery的入口**。

### 职责划分

```text
Application
    │
    │ public API
    ▼
ApplicationExecutor
    │
    ▼
ExecutionRuntime
    │
    ▼
CheckpointManager
    │
    ▼
CheckpointStore
```

**Application**

负责：

```text
Application lifecycle
Application API
Session ownership
Agent ownership
```

**ApplicationExecutor**

负责：

```text
Application-level execution coordination
```

**ExecutionRuntime**

负责：

```text
Execution lifecycle
Execution context
Execution recovery
```

**CheckpointManager**

负责：

```text
Checkpoint save
Checkpoint load
Checkpoint validation
```

**CheckpointStore**

负责：

```text
Checkpoint persistence
```

### Recovery的正确过程

```text
Checkpoint
   │
   ├── runtime_id
   ├── task_id
   ├── shared_context
   └── agent checkpoints
          │
          ▼
ExecutionRuntime
          │
          ├── create new TraceContext
          │
          ├── reconstruct RuntimeContext
          │
          └── create ExecutionHandle
                    │
                    ▼
             AgentExecutionContext
```

> 恢复的是Execution State，而不是恢复 Python runtime objects。

### Checkpoint Identity

runtime_id 是 Execution Identity（执行身份）。

因此， Checkpoint.runtime_id应该能够找到 Execution，

但是，Checkpoint.runtime_id **不意味着可以直接恢复旧RuntimeContext对象**。

### Lesson12-A: Checkpoint / RuntimeContext Recovery Model

修改
`runtime/context/runtime_context.py`

加入：

`RuntimeContext.create()`

并让：

`ExecutionRuntime.create_context()`

使用这个工厂方法。

### Lesson12-B: ExecutionRuntime Recovery

本节处理：

Execution-level Recovery（执行级恢复）。完成后 `ExecutionRuntime`将同时支持两种Execution创建方式：

```text
正常执行：

create_execution()
    ↓
new RuntimeContext
    ↓
ExecutionHandle


恢复执行：

resume_execution(checkpoint)
    ↓
reconstructed RuntimeContext
    ↓
ExecutionHandle
```

> 正常执行和恢复执行最终都返回`ExecutionHandle`。

#### Recovery后Runtime Identity必须保持

假设原 Execution：

```text
runtime_id = exec-001
trace_id   = trace-A
```

创建 Checkpoint：

```text
Checkpoint
    runtime_id = exec-001
```

发生故障。

然后恢复：

```text
runtime_id = exec-001
trace_id   = trace-B
```

所以：

```text
┌──────────────────────────────┐
│ Execution exec-001            │
│                              │
│  original execution          │
│      trace-A                 │
│                              │
│  recovery execution          │
│      trace-B                 │
└──────────────────────────────┘
```

这两个 ID 的职责不能混淆：

| **ID**       | **Recovery** |
|--------------|--------------|
| `runtime_id` | 保持不变         |
| `trace_id    | 重新生成         |
| `span_id`    | 重新生成         |

#### `shared_context` 也应该恢复

### Lesson12-C: Agent Runtime Recovery

> 恢复某个具体Agent的执行状态

#### 重新明确三种Context

##### RuntimeContext

> 一次Execution的运行时上下文。

```text
User Request
     │
     ▼
ExecutionRuntime
     │
     ▼
RuntimeContext
```

属于整个Execution，多个Agent共享。

##### AgentExecutionContext

> 一次 Agent Invocation 的上下文。

```text
Execution #100
│
├── Agent A invocation #1
│      └── AgentExecutionContext
│
├── Agent B invocation #1
│      └── AgentExecutionContext
│
└── Agent A invocation #2
       └── AgentExecutionContext
```

##### AgentContext / MemoryRuntime

> 属于 Agent Instance。

例如：

```text
ResearchAgent instance
│
├── AgentIdentity
├── AgentContext
└── MemoryRuntime
```

是长期存在的，属于AgentInstance本身。

#### 重构AgentRuntime

> 把AgentExecutionContext的创建/恢复统一收敛到AgentRuntime。

但是Recovery API 暂时不要暴露给Application。

### Lesson12-D: Application Recovery Entry Point

> Application 正式进入 Recovery 流程。

明确语义：

```text
execute()
    = 创建一次新的 Execution

recover()
    = 从 Durable Checkpoint 恢复一次已有 Execution
```

Application的公开API：

```text
await application.execute(task)

和

await application.recover(checkpoint)
```

#### 本课采用“两层 Recovery”

第一层： Application.recover() 负责：

> 恢复Execution。

第二层： ApplicationExecutor 负责：

> 管理 recovered ExecutionHandle 的生命周期。

Agent 如何恢复、从哪个 Agent 继续，则暂时留给后面的 Workflow/Supervisor。

#### ApplicationExecutor 增加 Recovery 能力

现在的正常执行流程为：

```text
Application.execute()
        ↓
ApplicationExecutor.execute()
        ↓
ExecutionRuntime.create_execution()
        ↓
ExecutionHandle
        ↓
Agent
        ↓
TaskResult
        ↓
finally close()
```

Recovery 增加：

```text
Application.recover()
        ↓
ApplicationExecutor.recover()
        ↓
ExecutionRuntime.resume_execution()
        ↓
ExecutionHandle
        ↓
[后续恢复逻辑]
        ↓
finally close()
```

> ExecutionHandle 的生命周期仍然由 ApplicationExecutor 管理。
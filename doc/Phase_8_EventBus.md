# Phase 8: Event Bus

---

## Step 1: Event 领域定义和边界建模

> Event = Runtime 中发生的“可被外部系统感知的状态变化事实

**三个关键词**：

 - Runtime中发生： 必须来自系统执行过程，而不是静态数据。
 - 状态变化事实： Event 必须满足`something changed OR something occurred` 而不是`prediction / plan / speculation`
 - 可被外部系统感知： 

|属性|Observation|Event|
|---|---|---|
|scope|local step|system-wide|
|可见性|Agent internal|external + internal|
|生命周期|transient|broadcast|
|目的|继续执行|通知 + 解耦|

### Event 来源：

1. Tool Execution -> Event

`ToolResult -> ToolExecutedEvent`

包含：

 - tool_name 
 - success/failure 
 - patch applied?

2. Action -> Event

`Action (Planner output) -> ActionSelectedEvent`

> agent 决策轨迹

3. Reflection -> Event

`Reflection -> ReflectionGeneratedEvent`

特点：

 - 不是失败结果
 - 是“认知层输出”

4. Checkpoint ->  Event

```text
CheckpointSavedEvent
CheckpointRestoredEvent
```

这是 **系统级事件**（非常关键）

5. Runtime Lifecycle → Event

```text
TaskStartedEvent
TaskFinishedEvent
```
> 是 system boundary events

### Event 的本体定义：

```python
@dataclass(frozen=True)
class Event:
    id: str
    type: str
    timestamp: int

    source: str   # tool / agent / runtime
    trace_id: str

    payload: dict
```

### Event 的设计边界总结（非常重要）

**✔ Event 是**：

 - 事实
 - 广播
 - 可订阅
 - 不可变

**❌ Event 不是**：

 - 状态
 - 控制信号
 - 任务执行器
 - Context mutation本身

## Step 2: Event 与系统架构关系建模（EventBus 在 Runtime 中的位置）

### EventBus 的最终架构定位（收敛）

我们现在给出 Phase8 的正式架构定义：

**✔ EventBus Layer 定位**

```text
Infrastructure Layer (sidecar runtime service)
```

**✔ 与 Runtime 的关系**

```text
Runtime Core (Loop)
    ↓ emits
EventBus (sidecar)
    ↓ dispatch
Subscribers (observability / memory / logging)
```

### EventBus 最小职责模型

EventBus 在 Phase8 只做三件事：

1. register subscriber: `subscribe(event_type, handler)`

2. emit event

3. dispatch synchronously

```text
call all handlers immediately
```

### 总结

**✔ EventBus 归属**

> Infrastructure sidecar layer

**✔ Event 流向**

> Runtime Loop → Event → EventBus → Subscribers

**✔ 强约束（非常重要）**

* Event 不影响 Loop control flow
* Event 不直接修改 Context
* EventBus 不参与 execution decision
* Event dispatch 默认同步
* ordering 仅局部保证

**✔ 系统形态变化（关键转折）**

从： `single closed loop runtime`

变成： `loop + observable event layer`

但仍然：

> ❗ single-agent deterministic runtime

## Step 3: Event Schema 设计

### 框架设计

为避免未来80+，120+ 的Event都继承统一的Event基类，导致 class Explosion。采用数据驱动（Data-Oriented）

大量继承可能导致的问题：

 - Event Explosion
 - Subscriber 很难泛化
    需要大量使用 isinstance()
 - 未来插件不好扩展
    第三方插件增加CustomEvent需要继承Event，修改 Event Registry。

### 结论

经过这一课，我们可以收敛出 Event 的核心模型：

```text
Event
├── id
├── type
├── source
├── trace_id
├── timestamp
└── payload
```

其中：

* Event 是唯一的数据结构，不为每种事件建立子类。
* EventType 使用命名空间字符串（如 tool.executed）。
* payload 是开放结构，具体字段由对应的 EventType 定义约束。
* trace_id 贯穿整个 Runtime，为未来的 Tracing、Replay、Multi-Agent 打下基础。

## Step 4: EventBus API设计

当前阶段，防止EventBus无限发展，禁止以下：

 - ❌ MQ 
 - ❌ Event Store 
 - ❌ Replay 
 - ❌ Persistence 
 - ❌ Scheduler

### Step4 收敛

**EventBus 的职责**

```text
Receive Event
↓

Find Subscribers

↓

Dispatch

↓

Done
```

除此之外：

什么都不做。

**Runtime 中的关系**

```text
Planner ─────────┐
ToolExecutor ────┤
Checkpoint ──────┤
Reflection ──────┤
                 ▼
             EventBus
                 ▼
        Multiple Subscribers
```

**Phase8 的 EventBus 特征**

* 同步（Synchronous）
* 单进程（In-process）
* 无队列（No Queue）
* 无持久化（No Persistence）
* 无重试（No Retry）
* 无事务（No Transaction）
* 一个 Event 可对应多个 Subscriber
* Subscriber 互相独立
* Subscriber 异常不影响 Runtime 主流程

### 最终采用的角色划分

```text
                 Event
                    │
                    ▼
            EventPublisher
                    │
                    ▼
               EventBus
                    │
         ┌──────────┴──────────┐
         ▼                     ▼
Subscriber A            Subscriber B
```

```text
                 +------------------------+
                 |   EventPublisher       |
                 |------------------------|
                 | emit(event)            |
                 +-----------▲------------+
                             |
                             | implements
                             |
                 +-----------+------------+
                 |      EventBus          |
                 |------------------------|
                 | emit(event)            |
                 | subscribe(...)         |
                 | unsubscribe(...)       |
                 +-----------+------------+
                             |
                    dispatch to subscribers
                             |
        +--------------------+--------------------+
        |                    |                    |
        ▼                    ▼                    ▼
  LoggerSubscriber   MemorySubscriber   CheckpointSubscriber
```

其中：

**EventPublisher** 职责：

> 发事件。

**EventBus** 职责：

> 分发事件。

**Subscriber** 职责：

> 消费事件。

三个角色完全独立。

## Step 5: Interface Design

```text
                    RuntimeBuilder
                           │
        ┌──────────────────┼──────────────────┐
        ▼                  ▼                  ▼
    EventBus          Subscribers        Runtime Components
        │                                      │
        │ implements                           │ depends on
        ▼                                      ▼
   EventPublisher <──────────────────────── Planner
                                          ToolExecutor
                                          CheckpointRuntime
                                          ReflectionRuntime
```

这里有几个非常重要的结论：

* Runtime 组件依赖 EventPublisher，而不是 EventBus。
* 只有 Composition Root（RuntimeBuilder）知道 EventBus 的存在。
* EventBus 负责 Subscriber 的生命周期和分发，不进入业务逻辑。
* EventBus 不是全局单例，而是 Runtime 的组成部分。


## Step9：收尾总结（EventBus Runtime 定型）

这一阶段不再扩展设计，只做三件事：

> **定边界、定能力、定不可做的事**

---

### 1. Phase8 已完成的核心能力

我们现在的 Event Runtime 已经是一个完整闭环：

```text id="s1"
ToolExecutor
    ↓
ToolResult（主流程）
    ↓
ToolEvents（fact builder）
    ↓
Event
    ↓
EventBus
    ↓
Subscriber
```

同时具备：

#### ✔ 1.1 事件发布能力

* tool.executed
* tool.failed

Runtime 可以将“发生的事实”广播出去

---

#### ✔ 1.2 事件分发能力

```text id="s2"
EventBus.subscribe()
EventBus.emit()
```

支持：

* 按 type 路由
* 多 subscriber
* 解耦发布与消费

---

#### ✔ 1.3 运行时完全解耦

三层完全分离：

```text id="s3"
Tool Runtime   → 业务执行
Event Runtime  → 事实广播
Subscriber     → 观察系统
```

---

#### ✔ 1.4 不影响主流程

关键原则已验证：

* ToolResult 不依赖 Event
* Event 不影响 Tool 执行
* Subscriber 不影响 Runtime

---

### 2. EventBus Runtime 的本质定位

这一阶段结束后，AgentOS 中 EventBus 的定位已经明确：

> **EventBus = Runtime Side-effect Distribution Layer**

它不是：

* ❌ 工作流引擎
* ❌ 状态机
* ❌ Event Sourcing 系统
* ❌ 消息队列替代品

---

它是：

> **“事实发生后的广播系统”**

---

### 3. Event 在 AgentOS 中的正确语义

我们现在可以给 Event 一个非常清晰的定义：

**✔ Event = Fact（事实）**

```text id="s4"
tool.executed
tool.failed
```

表达：

> “系统中发生过某件事”

---

**❌ Event 不是：**

❌ 状态

不是：

```text id="s5"
tool.status = running
```

---

**❌ 控制流**

不是：

```text id="s6"
if event: execute next step
```

---

**❌ 数据快照**

不是：

```text id="s7"
ToolResult snapshot
```

---

### 4. EventBus 的边界（非常重要）

这一点是 Phase8 的最终收敛。

---

**✔ EventBus 做什么**

* 接收 Event
* 按 type 分发
* 调用 Subscriber.handle()

---

**❌ EventBus 不做什么**

❌ 不改变 Context

```text id="s8"
ContextState ❌
```

---

**❌ 不参与业务决策**

```text id="s9"
Tool success/failure ❌
```

---

**❌ 不保证可靠性**

```text id="s10"
no retry / no durability
```

---

**❌ 不做事件编排**

```text id="s11"
no workflow logic
```

---

### 5. Subscriber 的本质定位

Phase8 已经隐含确立一个重要事实：

> Subscriber = Runtime Capability Extension Point

但目前仅用于：

* 观察
* 记录
* 外围系统扩展

例如：

```text id="s12"
RecordingSubscriber
LoggerSubscriber（未来）
MetricsSubscriber（未来）
```

---

关键点：

> Subscriber 不能反向驱动业务流程

---

### 6. Phase8 最重要的架构收敛

我们现在可以用一张图总结：

```text id="s13"
        ┌────────────────────────┐
        │      ToolExecutor       │
        │  (Business Execution)   │
        └──────────┬─────────────┘
                   │
                   ▼
            ToolResult (truth)
                   │
                   ▼
        ┌────────────────────────┐
        │       Event Layer       │
        │   Fact-based Events     │
        └──────────┬─────────────┘
                   │
                   ▼
        ┌────────────────────────┐
        │        EventBus         │
        │   Dispatch Mechanism    │
        └──────────┬─────────────┘
                   │
        ┌──────────┼──────────┐
        ▼          ▼          ▼
   Logger     Metrics   Recording
```

---

### 7. Phase8 已明确禁止的方向（重要）

为了防止架构再次膨胀，这里正式冻结：

**❌ 不做 Multi-Agent**

EventBus ≠ Agent communication system

---

**❌ 不做 Event Sourcing**

没有：

* replay
* event store
* aggregate rebuild

---

**❌ 不做 Workflow Engine**

没有：

* DAG
* Saga
* orchestration

---

**❌ 不做分布式消息系统**

没有：

* Kafka
* MQ
* retry semantics

---

**❌ 不做 Trace / Span（Phase9+）**

* no trace_id
* no OpenTelemetry

---

### 8. Phase8 的真正成果（一句话总结）

> AgentOS 现在拥有了一个“最小但正确”的事件广播系统，使 Runtime 可以产生事实，并被外部系统观察，而不影响执行本身。

---

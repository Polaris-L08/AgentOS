# Phase 9: Middleware + Tracing

---

## Step 1: Tracing Model

要回答的本质问题：

> 如何唯一标识一次Agent执行， 并能切分其内部所有子执行单元？

划分为：

* 一次Agent run是什么？
* run内部的“步骤”如何拆分？
* Tool/Planner/Action/Reflection如何挂到同一条链上？

### 三层Trace模型

```text
Trace (一次完整Agent运行)
 └── Span (一个逻辑执行单元)
       └── Event (事实记录，Phase8已有)
```

### Core 定义

#### Trace

> 一次 Agent Runtime 的完整生命周期

```text
Trace
- trace_id: str
- task_id: str
- start_time: timestamp
- end_time: timestamp | None
- root_span: Span
```

**语义**：

Trace = 

> 从Task输入到FinishAction输出的完整过程。

#### Span

> 一次 "可观测的执行单元"

例如：

| **Runtime动作**  |   **是否Span**  |
|----------------|:-------------:|
| Planner生成      |       是       |
| Tool执行         |       是       |
| Reflection     |       是       |
| Context update | 否(通常不作为span)  |

```text
Span
- span_id: str
- trace_id: str
- parent_span_id: str | None
- name: str                # e.g. "tool.execute"
- start_time: timestamp
- end_time: timestamp | None
- status: SpanStatus
- metadata: dict
```

```text
SpanStatus:
- SUCCESS
- ERROR
- RUNNING
```

**Span的关键设计原则**：

1. Span != Event

| **Span**   | **Event**  |
|------------|------------|
| 表示“过程”     | 表示“事实”     |
| 有start/end | 一次性        |
| 可嵌套        | 不可嵌套       |

2. Span是结构，Event是流

3. Span必须支持嵌套

```text
Trace
 └── root span (agent.run)
       ├── span (planner)
       ├── span (tool)
       │     ├── span (tool.internal)
       ├── span (reflection)
```

### Executing Boundary

> Span 在哪里创建？

1. ToolExecutor → span

```text
tool.execute start
tool.execute end
```

**✔ 必须 span 化**

2. Planner → span

```text
planner.run
```

**✔ 必须 span 化**

3. Reflection → span

```text
reflection.run
```

**✔ 必须 span 化**

4. Context update → ❌ 不单独 span

原因：
* 太细粒度
* 不影响观测结构
* 属于 side-effect

### TraceContext

引入： `TraceContext` 

用于在任何 runtime 组件中：
* 获取当前 trace
* 创建 child span
* 自动归档 span tree

### Span生命周期模型

```text
create_span()
   ↓
start_span()
   ↓
execute runtime logic
   ↓
end_span()
   ↓
attach to parent
```

### Span 与 EventBus 的关系

当前：

```text
Tool → EventBus (tool.executed)
```

加入Span后：

```text
Tool → Span → Event → EventBus
```

**关系定义**：

**✔ Span ≠ Event替代**

Span 不是替代 Event，而是**Event 的结构化执行容器**

### 设计约束

**❌ 禁止**

* Span驱动业务逻辑
* Span作为 workflow
* Span触发 execution flow
* Span跨 Agent 通信

**✔ 允许**

* Span记录执行结构
* Span用于 tracing
* Span用于 debug / observability

### Phase 9 Trace Model

```text
Trace
 └── Span (root: agent.run)
       ├── Span: planner.run
       ├── Span: tool.execute
       ├── Span: reflection.run
       └── Span: finish
```

每个 Span：

* 可以 emit Event
* 可以嵌套 child span
* 不改变 execution flow

### Step 1 结论

**✔ 三个核心对象**

* Trace（一次运行）
* Span（执行单元）
* TraceContext（运行时状态）

**✔ 一个核心关系**

> Span = execution structure layer
> Event = fact stream layer

**✔ 一个核心目标**

> 让 AgentOS 可以回答：
> “这一轮执行到底发生了什么？”

## Step 2: Middleware Layer 设计

**为什么需要Middleware？**

Middleware 要解决的问题：

> 把所有横切关注点（Cross-cutting Concerns）从业务逻辑中抽离出来。

Middleware的职责：

Middleware 不能负责业务。

它只负责：

```text
Runtime
    ↓
before()

真正执行

after()

或者

on_error()
```

### Middleware 生命周期

```python
class Middleware:

    async def before(self, context):
        ...

    async def after(self, context, result):
        ...

    async def on_error(self, context, error):
        ...
```

只定义以上3个Hook，而不是过度定义`before_tool()`,`after_tool()`,`before_plan()`,`before_reflection()`等。

但是，如果只有一个`before()`时，方法接收的参数是什么？ 如果写成`before(tool_request)`或者`before(action)`，这是**错误**的，这样的定义导致middleware依赖具体的业务对象。

定义统一的对象`RuntimeOperation`:

```python
@dataclass
class RuntimeOperation:
    name: str
    component: str
    metadata: dict[str, Any]
```

例如：

```python
RuntimeOperation(
    name="execute",
    component="tool_executor",
    metadata={
        "tool": "bash"
    }
)
```

```python
RuntimeOperation(
    name="plan",
    component="planner",
)
```

```python
RuntimeOperation(
    name="reflect",
    component="reflection",
)
```

```python
RuntimeOperation(
    name="save",
    component="checkpoint",
)
```

这是最重要的一层解耦。

### MiddlewareChain

有多个Middleware之后，需要一个调度器，负责**依次调用所有Middleware**。

```text
before()

Middleware A

Middleware B

Middleware C

============

Runtime

============

after()

Middleware C

Middleware B

Middleware A
```

也就是：

* before：按注册顺序执行。
* after 与 on_error：按相反顺序执行（LIFO）。

这样形成一层层包裹（类似栈展开）的效果，资源获取与释放能够自然配对。例如，TracingMiddleware 在 before 创建 Span，就能保证在对应的 after 中最后关闭 Span；如果未来加入事务、计时器等资源管理，也遵循相同模式。

### 总结

我们建立了四个新的核心抽象：
```text
RuntimeOperation
        │
        ▼
Middleware
(before / after / on_error)
        │
        ▼
MiddlewareChain
        │
        ▼
Runtime Component
(ToolExecutor / Planner / Reflection ...)
```

## Step 3

> 让 ToolExecutor 支持 Middleware，而不改变 ToolExecutor 的业务职责。

### 执行流程

原流程：

```text
ToolExecutor
    │
    ▼
 execute()
    │
    ▼
 ToolResult
```

加入Middleware之后：

```text
                RuntimeOperation
                       │
                       ▼
             MiddlewareChain.before()
                       │
                       ▼
                 ToolExecutor.execute()
                       │
                       ▼
              MiddlewareChain.after()
                       │
                       ▼
                   ToolResult
```

异常时：

```text
ToolExecutor.execute()
        │
        ▼
 Exception
        │
        ▼
 MiddlewareChain.on_error()
        │
        ▼
 raise
```

Middleware 不吞异常。

### 建模

**RuntimeOperation**：

```python
from dataclasses import dataclass
from typing import Any

@dataclass(slots=True)
class RuntimeOperation:
    name: str
    component: str
    metadata: dict[str, Any]
```

不要放：

* ToolResult
* Exception
* 大文本
* Context

**Middleware 基类**:

```python
from abc import ABC, abstractmethod
from typing import Any

class Middleware(ABC):

    @abstractmethod
    async def before(
        self,
        operation: RuntimeOperation,
        runtime_context: RuntimeContext,
    ) -> None:
        ...

    @abstractmethod
    async def after(
        self,
        operation: RuntimeOperation,
        runtime_context: RuntimeContext,
        result: Any,
    ) -> None:
        ...

    @abstractmethod
    async def on_error(
        self,
        operation: RuntimeOperation,
        runtime_context: RuntimeContext,
        error: Exception,
    ) -> None:
        ...
```

**MiddlewareChain**:

```python
from typing import Iterable

class MiddlewareChain:

    def __init__(
        self,
        middlewares: Iterable[Middleware] | None = None,
    ):
        self._middlewares = list(middlewares or [])

    async def before(
        self,
        operation: RuntimeOperation,
        runtime_context: RuntimeContext,
    ) -> None:
        for middleware in self._middlewares:
            await middleware.before(operation, runtime_context)

    async def after(
        self,
        operation: RuntimeOperation,
        runtime_context: RuntimeContext,
        result: Any,
    ) -> None:
        for middleware in reversed(self._middlewares):
            await middleware.after(
                operation,
                runtime_context,
                result,
            )

    async def on_error(
        self,
        operation: RuntimeOperation,
        runtime_context: RuntimeContext,
        error: Exception,
    ) -> None:
        for middleware in reversed(self._middlewares):
            await middleware.on_error(
                operation,
                runtime_context,
                error,
            )
```

### 完成后的架构图

```text
                  CodeAgent
                      │
                      ▼
              ToolExecutor.execute()
                      │
          ┌───────────┴───────────┐
          ▼                       ▼
 MiddlewareChain.before()    RuntimeOperation
                      │
                      ▼
                 Tool.execute()
                      │
        ┌─────────────┴─────────────┐
        ▼                           ▼
 MiddlewareChain.after()     MiddlewareChain.on_error()
                      │
                      ▼
                  ToolResult
```

## Step 4: 实现 TradingMiddleware

需要注意的是：

> TracingMiddleware 不保存 Span

只负责 `创建Span->结束Span`，真正保存Span的是 `TraceRecorder`，职责分离。

因为如果 TracingMiddleware 包含了保存Span，那么后面如果有Export、Persistence、Remote等，都需要加进去。

如果职责分离，只用替换或增加 Recorder 就行了。
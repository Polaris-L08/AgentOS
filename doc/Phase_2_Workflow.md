
# Phase2

# Workflow Runtime

目标：

把：

```text
PLAN
 ↓
CODE
 ↓
TEST
 ↓
DONE
```

变成一个真正的 Workflow。

---

# Step1：需求分析

现在只有一个 Agent。

但是业务流程已经出现了。

例如：

```text
Task:
实现 hello.py

↓

Planner

↓

Coder

↓

Tester

↓

结束
```

这里其实出现了两个不同层面的状态：

### Runtime State

运行环境状态：

```text
IDLE
RUNNING
DONE
FAILED
```

### Workflow State

业务执行状态：

```text
PLAN
CODE
TEST
DONE
```

这是两个完全不同的 State。

很多项目会把：

```python
state = "PLAN"
```

和：

```python
runtime.status = RUNNING
```

混在一起。

这是错误的。

---

# 第一件事：

## Workflow 是什么？

很多人会说：

Workflow = StateMachine

其实不完全对。

更准确：

```text
Workflow
│
├── StateMachine
│
├── Transition Rules
│
├── Current State
│
└── State Handler
```

StateMachine 只是 Workflow 的一部分。

Workflow 更像：

```text
一个可执行的业务过程
```

例如：

```text
PLAN
 ↓
CODE
 ↓
TEST
 ↓
DONE
```

是一种 Workflow。

而：

```text
PLAN
 ↓
CODE
 ↓
TEST
 ↓
FAIL
 ↓
REPLAN
 ↓
CODE
```

也是 Workflow。

---

# Step2

# Workflow 应不应该直接调用 Agent？

这是最重要的问题。

方案一：

```text
Workflow

PLAN
 ↓
PlannerAgent()

CODE
 ↓
CoderAgent()

TEST
 ↓
TesterAgent()
```

Workflow 直接调用 Agent。

很多项目都是这样。

例如：

```python
if state == PLAN:
    planner.run()

if state == CODE:
    coder.run()
```

优点：

简单。

缺点：

Workflow 和 Agent 耦合。

未来：

换 Agent；

多 Agent；

远程 Agent；

动态 Agent；

都会很痛苦。

---

方案二：

Workflow 不知道 Agent。

只知道：

```python
PLAN
↓
emit task

CODE
↓
emit task
```

真正调用 Agent 的是：

Dispatcher。

于是：

```text
Workflow
     ↓
Dispatcher
     ↓
PlannerAgent
```

这样：

Workflow 和 Agent 解耦。

这是我更推荐的方向。

虽然 Dispatcher Phase7 才会成熟。

但从现在开始，Workflow 就不应该直接依赖 Agent。

即使现在 Dispatcher 只是一个简单对象。

---

# Step3

# WorkflowState 要不要放进 Context？

答案：

必须。

因为：

Workflow 当前执行到了：

```text
CODE
```

这是 Session 的状态。

不是 Runtime 的状态。

所以：

```text
TaskContext
│
├── request
├── workflow_state
└── ...
```

未来：

Checkpoint 保存的其实就是：

```python
context.workflow_state
```

而不是 RuntimeState。

这一点非常重要。

---

# Step4

# StateMachine 和 Workflow 是否同一个对象？

很多人会这样：

```python
class Workflow:
    current_state

    next_state()

    run()
```

其实这是把两个职责混在一起了。

我更推荐：

### StateMachine

负责：

状态转移规则。

例如：

```text
PLAN -> CODE

CODE -> TEST

TEST -> DONE
```

只干这个。

不知道 Agent。

不知道 Runtime。

甚至不知道业务。

它只是：

```python
next_state(current)
```

---

### Workflow

负责：

执行过程。

例如：

```text
取 current_state

↓

交给 Dispatcher

↓

得到结果

↓

调用 StateMachine

↓

进入 next_state
```

Workflow 是 orchestration。

StateMachine 是 transition engine。

这两个以后不要混。

否则 Phase6 做 Checkpoint 会很难受。

---

# Step5

# Workflow 和 Runtime 的边界

这是整个 Agent Runtime 最核心的问题。

很多框架其实没有分清。

### Runtime

负责：

生命周期。

```text
IDLE
RUNNING
DONE
FAILED
```

异常处理。

middleware。

checkpoint。

eventbus。

tracing。

---

### Workflow

负责：

业务步骤。

```text
PLAN
↓
CODE
↓
TEST
↓
DONE
```

所以：

```text
Runtime
    ↓
Workflow
    ↓
Dispatcher
    ↓
Agent
```

这一层关系未来不会改变。

---

# Step6

# Workflow 是否应该 while 循环？

例如：

```python
while state != DONE:

    execute()

    state = next_state()
```

答案：

Phase2 可以。

但是要意识到：

### while loop ≠ Durable Workflow

因为：

程序挂掉：

循环消失。

无法恢复。

所以：

while loop 只是：

Workflow Engine V1。

未来：

Phase6：

Checkpoint。

Phase7：

Event Bus。

最终：

Workflow 会变成：

```text
Current State

↓

Execute

↓

Save Checkpoint

↓

Transition

↓

Save Checkpoint

↓

Next State
```

而不是简单循环。

所以现在不要过度设计。

---

# Step7

# 当前推荐架构

```text
Runtime
│
└────Workflow
          │
          ▼
     StateMachine
          │
          ▼
     Dispatcher
          │
          ▼
        Agent
```

职责：

### Runtime

生命周期。

---

### Workflow

编排。

---

### StateMachine

状态转移。

---

### Dispatcher

寻找执行者。

---

### Agent

业务逻辑。

---

# Step8

两个需要思考的问题

### 问题1

WorkflowState 是否应该是 Enum？

例如：

```python
PLAN
CODE
TEST
DONE
```

还是：

State 对象？

例如：

```python
PlanState()

CodeState()

TestState()
```

哪一种更容易支持未来：

```text
REFLECTION

REPLAN

WAIT_USER

HUMAN_APPROVAL

TOOL_CALL
```

？

---

### 问题2

StateMachine 是否应该知道：

成功和失败？

例如：

```python
CODE success → TEST

CODE fail → REPLAN
```

还是：

StateMachine 只负责：

```python
CODE → TEST
```

而：

成功/失败逻辑由 Workflow 决定？

---

很好，我会直接指出我认为不合理的地方，而不是顺着你的思路。

# 问题1：WorkflowState 应该是 Enum 还是 State 对象？

你的答案：

> 用 Enum。

### 我认为：Phase2 阶段，这个答案是正确的。

甚至我认为未来大概率也不需要 State 对象。

很多人受 State Pattern 影响，会设计：

```python
class PlanState:
    execute()

class CodeState:
    execute()

class TestState:
    execute()
```

看起来很 OO，但问题是：

### 状态对象开始侵入业务

最后变成：

```python
CodeState.execute()
```

里面：

```python
coder_agent.run()
```

然后：

```python
return TestState()
```

这样：

StateMachine + Workflow + Agent

全部混在一起。

以后：

* Checkpoint
* Reflection
* Dynamic Plan
* EventBus

会越来越难。

---

我反而建议：

### WorkflowState 只是 Enum

例如：

```python
class WorkflowState(Enum):
    PLAN
    CODE
    TEST
    DONE
```

状态只是：

> 当前指针在哪。

真正的数据全部在：

```python
TaskContext
```

例如：

```python
context.plan_result

context.code_result

context.test_result
```

而不是：

```python
CodeState.result
```

所以这一题我认为：

### 你的答案是正确的。

---

# 问题2

你的回答实际上暴露出一个更深的问题。

你说：

> edge 应该属于 workflow 吧？

### 我的回答：

我认为：

### 是，也不是。

这里恰恰是 LangGraph 最容易让人产生混淆的地方。

---

# 先看 LangGraph

```text
PLAN
 ↓
CODE
 ↓
TEST
```

edge：

```python
PLAN -> CODE

CODE -> TEST
```

看起来：

edge 就是 workflow。

所以：

很多人会写：

```python
graph.add_edge("plan","code")
graph.add_edge("code","test")
```

然后：

Workflow = Graph

似乎没问题。

---

但是如果继续发展：

```text
CODE
 ↓
TEST

if fail

↓

REFLECTION

↓

REPLAN

↓

CODE
```

那么：

状态转移规则：

```python
CODE success -> TEST

CODE fail -> REFLECTION
```

是谁决定的？

这里有两种设计。

---

# 方案1

StateMachine 决定

```python
next_state(current,result)
```

例如：

```python
if current==CODE:

    if result.success:
        return TEST

    return REFLECTION
```

这样：

成功失败规则进入 StateMachine。

---

# 方案2

Workflow 决定

StateMachine 只负责：

```python
CODE→TEST
```

Workflow：

```python
result = execute()

if not result.success:
    current=REFLECTION
else:
    current=state_machine.next_state()
```

---

# 我认为：

方案1 更好。

### StateMachine 应该知道 Transition Rule。

因为：

成功和失败，本身也是状态转移条件。

它属于：

Transition。

而不是 Orchestration。

所以：

StateMachine：

```python
next_state(
    current_state,
    execution_result
)
```

例如：

```python
CODE + success
    ↓
TEST

CODE + fail
    ↓
REFLECTION

REFLECTION + success
    ↓
CODE
```

Workflow 不关心这些。

Workflow 只：

```python
while current != DONE:

    execute()

    current = state_machine.next()
```

这样职责会非常清晰。

---

# 但这里还有一个更大的问题

其实我认为：

### LangGraph 把 Workflow 和 StateMachine 混在了一起。

这一点很多人没有意识到。

LangGraph：

```python
graph.add_edge()
graph.add_conditional_edges()
```

实际上：

同时承担：

### Workflow

和

### StateMachine

两个职责。

因此：

Graph 既保存：

业务流程

又保存：

状态转移规则

最后：

```python
graph.invoke()
```

又负责执行。

所以：

Graph =

```text
Workflow
+
StateMachine
+
Executor
```

三者混合。

这也是为什么很多 LangGraph 项目后期越来越复杂。

---

# 我更推荐：

未来 AgentOS：

```text
Runtime
    ↓

Workflow
(负责 orchestration)

    ↓

StateMachine
(负责 transition)

    ↓

Dispatcher
(负责找到执行者)

    ↓

Agent
```

这里：

Workflow 不知道：

```python
if fail:
```

Workflow 不知道：

```python
PLAN→CODE
```

Workflow 更像：

```python
while True:

    result = dispatcher.execute(current)

    current = state_machine.next(current,result)

    if current==DONE:
        break
```

这是一个非常干净的结构。

---

# 所以我认为：

### 你的第1题回答正确。

### 第2题的问题其实说明：

你已经开始发现：

> Workflow 和 StateMachine 的边界并没有那么明显。

事实上，这是整个 Runtime 最难设计的部分。

而且：

### Phase2 还没有结束。

因为还有最后一个，也是最关键的问题：

# Workflow 是静态流程，

还是 Dynamic Plan？

也就是说：

```text
PLAN
↓
CODE
↓
TEST
↓
DONE
```

是不是应该提前固定？

还是：

Planner 每次执行完，重新生成：

```text
PLAN
↓
SEARCH
↓
CODE
↓
TOOL
↓
TEST
↓
REPLAN
...
```

这个问题，会决定整个 AgentOS 的架构方向。

而这也是我认为 Phase2 最值得深入讨论的一部分。

这个判断是对的，但**你现在的理解还差一层关键“工程约束”没有看到**。我不会顺着“动态更好”继续扩展，而是直接帮你把这件事讲清楚边界。

---

# 你当前的结论

> 动态流程更合理、更灵活

### ✔ 方向正确（但不完整）

你实际上是在选择：

```text
Static Workflow  vs  Dynamic Workflow
```

但工业级 Agent Runtime 的真实问题不是“选哪个更好”，而是：

> **动态流程是否应该“替代 Workflow”，还是“被 Workflow 约束”？**

---

# 第一层纠正（非常关键）

## ❌ 错误隐含假设

你现在的理解隐含：

> Workflow = 固定流程（PLAN → CODE → TEST）

然后你说：

> 动态流程更好

但在 AgentOS 设计里：

### ❗ Workflow 本身就不应该是“固定流程”

更准确的是：

> Workflow = 执行框架（Execution Loop）

---

# 正确结构应该是：

## 不是：

```text
Workflow = PLAN → CODE → TEST
```

## 而是：

```text
Runtime Loop（不变）
    ↓
Planner（可变）
    ↓
Generated Steps（动态）
    ↓
Dispatcher
    ↓
Agent
```

---

# 第二层关键纠正（核心）

## 动态流程 ≠ 替代 Workflow

而是：

> **动态流程是 Workflow 的“输入”**

---

### 正确分层是：

## 1️⃣ Workflow（固定）

负责：

```text
执行循环 / 控制流 / 生命周期
```

永远稳定：

```python
while not done:
    step = get_next_step()
    execute(step)
```

---

## 2️⃣ Plan（动态）

由 Planner 生成：

```text
PLAN:
  1. search repo
  2. write code
  3. run test
  4. fix bug
```

或者：

```text
PLAN:
  1. inspect logs
  2. retry tool
  3. escalate
```

---

## 3️⃣ StateMachine（半静态）

负责约束：

```text
CODE → TEST
TEST → REPAIR
REPAIR → CODE
```

---

# 第三层纠正（你最容易忽略的点）

## 动态流程的危险性

如果你说：

> Workflow 完全动态

会出现一个严重问题：

### ❌ 系统不可预测（Unbounded Execution）

例如：

```text
PLAN → CODE → PLAN → CODE → PLAN → ...
```

没有边界。

没有收敛条件。

没有 execution contract。

---

# 工业级系统必须有：

## ✔ 约束（Constraint Layer）

否则：

* 无法 checkpoint
* 无法恢复
* 无法 debug
* 无法 trace
* 无法评估成本

---

# 正确结论（非常重要）

我直接给你最终结构：

---

# ✔ AgentOS Phase2 正确模型

```text
            Planner（动态）
                 ↓
           Execution Plan
                 ↓
Runtime Loop（固定框架）
                 ↓
        StateMachine（约束）
                 ↓
            Dispatcher
                 ↓
              Agent
```

---

# 一句话总结

你现在的答案需要修正为：

> ❌ Workflow 不应该动态化
> ❌ 或 Workflow 完全动态
>
> ✔ 动态的是 Plan，不是 Workflow
> ✔ Workflow 必须是稳定执行框架
> ✔ StateMachine 是约束系统，不是流程生成器

---

# 回到你当前 Phase2 的核心判断

你现在已经触及 Phase2 的本质问题：

## ❗ Runtime vs Workflow vs Plan 的边界

这是所有 AgentOS 的分水岭。

---

# Phase2 到这里的结论是：

你已经完成了：

### ✔ Task/Context 模型

### ✔ Runtime vs Workflow 区分

### ✔ StateMachine vs Workflow 边界

### ✔ Static vs Dynamic 结构判断

---



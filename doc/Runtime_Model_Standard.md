# Runtime Model Standard

Version: 1.0

This document defines the coding standard for all Runtime Domain Models in AgentOS.

---

# 1. Scope

This specification applies to all Runtime models, including but not limited to:

- Span
- Trace
- Event
- Checkpoint
- LoopState
- RuntimeOperation
- ContextState
- HistoryState
- ScratchpadState
- VariableState
- WorkspaceState

Business-specific models (such as Tool implementations) are not required to follow this specification.

---

# 2. Design Principles

Runtime Models are **Data Objects**.

They represent runtime state only.

Runtime Models should not contain workflow logic.

Managers, Executors and Middleware own the runtime behavior.

---

# 3. Dataclass

All Runtime Models MUST use:

```python
@dataclass(
    slots=True,
    kw_only=True,
)
```

Reason:

- reduce memory usage
- prevent dynamic attributes
- improve readability
- explicit construction

Example:

```python
@dataclass(slots=True, kw_only=True)
class Span:
    ...
```

---

# 4. Constructors

Runtime Models MUST NOT generate runtime data automatically.

Do NOT generate:

- uuid
- timestamp
- random values

Incorrect:

```python
span = Span()
```

Correct:

```python
span = Span(
    span_id=span_id,
    start_time=start_time,
)
```

Creation belongs to:

- Manager
- Recorder
- Factory

---

# 5. Business Logic

Runtime Models should contain data only.

Allowed:

- @property
- simple derived values

Not allowed:

```python
span.start()

span.end()

checkpoint.save()

trace.attach()
```

These operations belong to runtime services.

---

# 6. Time

All timestamps MUST use UTC.

Correct:

```python
from datetime import datetime, timezone

datetime.now(timezone.utc)
```

Incorrect:

```python
datetime.now()
```

---

# 7. Enum

Enums MUST inherit from str.

Example:

```python
class SpanStatus(str, Enum):
    RUNNING = "running"
```

Reason:

- JSON serialization
- logging
- persistence

---

# 8. Optional Fields

Fields that are unavailable during initialization should use Optional.

Example:

```python
end_time: datetime | None = None
```

---

# 9. Mutable Defaults

Never use mutable default values.

Incorrect:

```python
metadata: dict = {}
```

Correct:

```python
metadata: dict[str, Any] = field(default_factory=dict)
```

---

# 10. IDs

IDs are immutable.

Examples:

- trace_id
- span_id
- event_id

They should never change after creation.

---

# 11. Relationships

Runtime Models should reference other models by ID.

Preferred:

```python
parent_span_id: str | None
```

Avoid object references unless there is a strong runtime requirement.

Reason:

- serialization
- checkpoint
- persistence
- testing

---

# 12. Serialization

Runtime Models should be serialization-friendly.

Avoid storing:

- callbacks
- file handles
- locks
- threads
- async objects

Runtime Models should be compatible with:

- JSON
- Checkpoint
- Future persistence

---

# 13. Type Hints

All Runtime Models MUST use complete type annotations.

Enable postponed annotations:

```python
from __future__ import annotations
```

---

# 14. Documentation

Every Runtime Model should contain a concise docstring describing:

- responsibility
- lifecycle
- owner

Example:

```python
"""
Represents one execution span within a trace.

Span is a runtime data object and contains no execution logic.
"""
```

---

# 15. Ownership

| Object | Owner |
|----------|------|
| Span | TraceRecorder |
| Trace | TraceContext |
| Event | EventBus |
| Checkpoint | CheckpointStore |
| LoopState | CodeAgent |

Runtime Models should never manage their own lifecycle.

---

# Summary

Runtime Models should be:

- Simple
- Immutable where possible
- Serialization-friendly
- Logic-free
- Explicit
- Easy to test
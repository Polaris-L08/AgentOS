from collections import defaultdict

from runtime.tracing.span import Span
from runtime.tracing.trace import Trace


class TraceFormatter:
    """
    Pretty formatter for Trace.

    The formatter builds the span hierarchy and renders
    a human-readable execution tree.

    It is intended for debugging, testing and future
    observability exporters.
    """

    def format(self, trace: Trace) -> str:
        lines: list[str] = []

        lines.append("=" * 60)
        lines.append("Trace Report")
        lines.append("=" * 60)
        lines.append(f"Trace ID : {trace.trace_id}")
        lines.append(f"Duration : {trace.duration_ms:.2f} ms"
                     if trace.duration_ms is not None
                     else "Duration : RUNNING")
        lines.append(f"Span Count : {trace.span_count}")
        lines.append("")

        children = self._build_tree(trace)

        root = trace.get_span(trace.root_span_id)

        if root is not None:
            self._render_span(
                root,
                children,
                lines,
                depth=0,
            )

        lines.append("")
        lines.append("=" * 60)

        return "\n".join(lines)

    def _build_tree(
            self,
            trace: Trace,
    ) -> dict[str | None, list[Span]]:

        tree: dict[str | None, list[Span]] = defaultdict(list)

        for span in trace.all_spans():
            tree[span.parent_span_id].append(span)

        return tree

    def _render_span(
            self,
            span: Span,
            tree: dict[str | None, list[Span]],
            lines: list[str],
            depth: int,
    ) -> None:

        indent = "    " * depth

        duration = (
            f"{span.duration_ms:.2f} ms"
            if span.duration_ms is not None
            else "RUNNING"
        )

        lines.append(
            f"{indent}- {span.name}"
            f" [{span.status.name}]"
            f" ({duration})"
        )

        for child in tree.get(span.span_id, []):
            self._render_span(
                child,
                tree,
                lines,
                depth + 1,
            )
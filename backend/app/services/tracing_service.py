from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.utils.config import LANGSMITH_API_KEY, LANGSMITH_ENDPOINT, LANGSMITH_PROJECT, LANGSMITH_TRACING_ENABLED

try:
    from langsmith import Client
except Exception:  # pragma: no cover
    Client = None


class TracingService:
    _active_run_id: ContextVar[str | None] = ContextVar("langsmith_active_run_id", default=None)

    def __init__(self) -> None:
        self.enabled = bool(LANGSMITH_TRACING_ENABLED and LANGSMITH_API_KEY and Client is not None)
        self.project = LANGSMITH_PROJECT
        self.client = None
        if self.enabled:
            try:
                self.client = Client(api_key=LANGSMITH_API_KEY, api_url=LANGSMITH_ENDPOINT)
            except Exception:
                self.client = None
                self.enabled = False

    def current_run_id(self) -> str | None:
        return self._active_run_id.get()

    def start_span(
        self,
        *,
        name: str,
        run_type: str,
        inputs: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        tags: list[str] | None = None,
        parent_run_id: str | None = None,
    ) -> str | None:
        if not self.enabled or self.client is None:
            return None
        run_id = str(uuid4())
        parent_id = parent_run_id or self.current_run_id()
        payload_inputs = inputs or {}
        payload_metadata = metadata or {}
        try:
            self.client.create_run(
                id=run_id,
                name=name,
                run_type=run_type,
                project_name=self.project,
                inputs=payload_inputs,
                extra={"metadata": payload_metadata},
                tags=tags or [],
                parent_run_id=parent_id,
            )
            return run_id
        except TypeError:
            # Compatibility path for older/newer langsmith signatures.
            try:
                self.client.create_run(
                    id=run_id,
                    name=name,
                    run_type=run_type,
                    project_name=self.project,
                    inputs=payload_inputs,
                    tags=tags or [],
                )
                return run_id
            except Exception:
                return None
        except Exception:
            return None

    def end_span(
        self,
        run_id: str | None,
        *,
        outputs: dict[str, Any] | None = None,
        error: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        if not run_id or not self.enabled or self.client is None:
            return
        try:
            self.client.update_run(
                run_id=run_id,
                outputs=outputs or {},
                error=error,
                end_time=datetime.now(timezone.utc),
                extra={"metadata": metadata or {}},
            )
        except TypeError:
            try:
                self.client.update_run(
                    run_id=run_id,
                    outputs=outputs or {},
                    error=error,
                    end_time=datetime.now(timezone.utc),
                )
            except Exception:
                return
        except Exception:
            return

    @contextmanager
    def span(
        self,
        *,
        name: str,
        run_type: str,
        inputs: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        tags: list[str] | None = None,
        parent_run_id: str | None = None,
    ):
        run_id = self.start_span(
            name=name,
            run_type=run_type,
            inputs=inputs,
            metadata=metadata,
            tags=tags,
            parent_run_id=parent_run_id,
        )
        token = None
        if run_id is not None:
            token = self._active_run_id.set(run_id)
        try:
            yield run_id
        except Exception as exc:
            self.end_span(run_id, error=str(exc))
            raise
        finally:
            if token is not None:
                self._active_run_id.reset(token)

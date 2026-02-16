from __future__ import annotations

import json
import logging
from collections.abc import MutableMapping
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


class LoggingConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    format: Literal["text", "json"] = "text"
    file: Path | None = None
    include_tracebacks: bool = True


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key in payload or key.startswith("_"):
                continue
            payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload)


class _ContextAdapter(logging.LoggerAdapter):
    def process(
        self, msg: Any, kwargs: MutableMapping[str, Any]
    ) -> tuple[Any, MutableMapping[str, Any]]:
        extra = kwargs.get("extra", {})
        extra.update(self.extra)
        kwargs["extra"] = extra
        return msg, kwargs


def configure_logging(config: LoggingConfig) -> None:
    handlers: list[logging.Handler] = []

    stream_handler = logging.StreamHandler()
    handlers.append(stream_handler)

    if config.file is not None:
        handlers.append(logging.FileHandler(config.file))

    if config.format == "json":
        formatter: logging.Formatter = _JsonFormatter()
    else:
        formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")

    for handler in handlers:
        handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(logging.CRITICAL)

    for logger in logging.Logger.manager.loggerDict.values():
        if not isinstance(logger, logging.Logger):
            continue
        if logger.name.startswith("doc_parsing"):
            continue
        logger.handlers.clear()
        logger.propagate = True
        logger.setLevel(logging.NOTSET)

    doc_logger = logging.getLogger("doc_parsing")
    doc_logger.handlers.clear()
    for handler in handlers:
        doc_logger.addHandler(handler)
    doc_logger.setLevel(config.level)
    doc_logger.propagate = False


def get_logger(name: str, **context: Any) -> logging.LoggerAdapter:
    base = logging.getLogger(name)
    return _ContextAdapter(base, context)

"""
Pipeline execution layer.

This module contains the executor that runs a Pipeline against an input,
manages per-stage failure handling, and assembles the final Result.
The executor is separate from the Pipeline definition so that alternative
execution strategies (e.g. DAG execution, parallel stages) can be added
without changing the core Pipeline abstraction.
"""

from lingualdub.pipeline.executor import PipelineExecutor

__all__ = ["PipelineExecutor"]

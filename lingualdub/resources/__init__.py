"""
Framework dataset and evaluation resources.
"""

from lingualdub.resources.eval_sets import (
    LUGANDA_ASR_EVAL_SET,
    LUGANDA_ENG_PARALLEL_EVAL_SET,
    LUGANDA_ENG_CODESWITCH_EVAL_SET,
    get_evaluation_resource,
)

__all__ = [
    "LUGANDA_ASR_EVAL_SET",
    "LUGANDA_ENG_PARALLEL_EVAL_SET",
    "LUGANDA_ENG_CODESWITCH_EVAL_SET",
    "get_evaluation_resource",
]

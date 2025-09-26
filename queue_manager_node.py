"""
Main ComfyUI custom node for the Queue Manager.
"""

from __future__ import annotations

from typing import Any


class QueueManagerNode:
    """
    ComfyUI custom node for queue management functionality.
    This node serves as the entry point for the queue manager system.
    """

    @classmethod
    def INPUT_TYPES(cls) -> dict[str, Any]:  # noqa: N802
        """Define the input types for the node."""
        return {
            "required": {},
            "optional": {
                "workflow_name": ("STRING", {"default": ""}),
                "auto_queue": ("BOOLEAN", {"default": True}),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("queue_item_id",)
    FUNCTION = "process"
    CATEGORY = "Queue Management"
    DESCRIPTION = (
        "Manages workflow execution queues with persistence and control features"
    )

    def __init__(self):
        """Initialize the queue manager node."""
        self.queue_service = None  # Will be initialized when needed

    def process(self, workflow_name: str = "", auto_queue: bool = True) -> tuple[str]:
        """
        Process the node execution.

        Args:
            workflow_name: Optional name for the workflow
            auto_queue: Whether to automatically add to queue

        Returns:
            Tuple containing the queue item ID
        """
        # For now, return a placeholder ID
        # This will be implemented in later tasks when the queue service is available
        queue_item_id = "placeholder_id"

        return (queue_item_id,)

    @classmethod
    def IS_CHANGED(cls, **kwargs: Any) -> float:  # noqa: N802, ARG003
        """Determine if the node needs to be re-executed."""
        # Always execute for now
        return float("nan")

    @classmethod
    def VALIDATE_INPUTS(cls, **kwargs: Any) -> bool:  # noqa: N802, ARG003
        """Validate the inputs to the node."""
        return True

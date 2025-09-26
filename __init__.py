"""
ComfyUI Queue Manager Custom Node
A comprehensive queue management system for ComfyUI workflows.
"""

from .queue_manager_node import QueueManagerNode

NODE_CLASS_MAPPINGS = {
    "QueueManagerNode": QueueManagerNode
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "QueueManagerNode": "Queue Manager"
}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
"""CPU SFT preparation. Importing this package never loads a model backend."""

from .collator import Batch, collate_selected, collate_sequence
from .data import SelectionView, prepare
from .plan import EpochPlan, Segment, epoch_plan, validate_plan

__all__ = ["Batch", "EpochPlan", "Segment", "SelectionView", "collate_selected",
           "collate_sequence", "epoch_plan", "prepare", "validate_plan"]

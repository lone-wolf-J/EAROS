"""EAROS Platform Core.

Runtime, Planner, Policy Engine, Capability Registry, Memory, World State,
Governance, Reflection.

The Runtime never lets the LLM directly execute business actions.
Every action flows: Planner -> Runtime -> Policy -> Capability -> WorldState.
"""

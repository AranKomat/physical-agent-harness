"""Opt-in embodied executive/discovery integration; no services start on import.

Import concrete modules for their APIs. Keeping this namespace light avoids loading
GPU, provider, segmentation or simulator dependencies in the robot's core process.
"""

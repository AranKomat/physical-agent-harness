# Navigation And Maps

`world.topology.TopologicalMap` remains the semantic place/connection store.
`planning.navigation` provides existing metric occupancy/navigation behavior.
`planning.map_tools` projects that data into a `NavigationGrid`, frontier choices,
exploration history and compact map summaries. It is not a second SLAM system.

The hierarchy is a semantic destination, current local route, and then a bounded
native base operation. `MapTool` returns an opaque search/destination hint, not a
collision approval. A remembered object location requests reacquisition before
action. Unknown occupancy, stale gateways, changed localization epochs and missing
visibility providers cannot be treated as certified free space.

Maps grow online from permitted observations. Neither pre-mapping a benchmark
episode nor importing simulator object/world poses is part of this runtime.
Dense reconstruction is optional on-demand evidence, not a required digital twin.

R1Pro base response, localization, low-space clearance and measured stopping need
native qualification. Existing labeled exploratory probes are not strict-gate
qualification and do not automatically promote a controller.

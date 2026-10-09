# DynaMesh Studio

Procedural geometry and dynamic node scaling for large-scale virtual environments.

Website: https://dynameshstudio.com
Founded 2026 by Diego, Santiago, Chile.

## What this is

DynaMesh Studio is developing a procedural generation pipeline in **Python** and **Luau** that automates the creation of large-scale 3D province meshes for virtual environments.

### Dynamic node scaling

A scaling system calculates spatial representation from population parameters:

- Nodes under 1,000,000 population render as optimized cylinders.
- Larger "mega-nodes" transform into more complex square geometries.
- The aim is to balance render cost and visual fidelity.

## How Claude is used

The founder defines the design, reviews all output, and tests results. Claude is used to:

- Write and refactor the Python geometry generation code.
- Write the Luau integration for the target environment.
- Generate tests and validators for mesh output.
- Review edge cases in the scaling rules and draft documentation.

## Roadmap

This is the plan. Items are checked off only when they work.

### Now: foundations
- [x] Project website and public repository
- [ ] Define the input format (region and population parameters per node)
- [ ] First Python generator that builds a simple province mesh and exports it
- [ ] Implement the node scaling rule (cylinders under 1,000,000, squares above)
- [ ] Automated mesh checks and a first demo image

### Next: integration
- [ ] Luau integration to bring generated meshes into the target environment
- [ ] Performance budgeting (part counts, level of detail, render cost)
- [ ] Batch generation across many provinces from one data file
- [ ] Better automatic validation of geometry

### Later: scale
- [ ] Configurations for many regions worldwide
- [ ] Real-time updates when population parameters change
- [ ] Simple tooling or interface to configure and preview a map
- [ ] Public demo and full documentation

## Tech stack

- Python (generation pipeline)
- Luau (integration with the target environment)
- LLM-assisted development

## Repository layout

| Path | Contents |
| --- | --- |
| `index.html` | Project website source |
| `CNAME` | Custom domain configuration |

More paths will be added as the pipeline code is added.

## Contact

Diego, founder@dynameshstudio.com

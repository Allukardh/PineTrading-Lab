# Versioning

Each core script is versioned independently with Semantic Versioning.

## Reboot

All old application versions are reset. Historical values remain only in `archive/`.

- `0.1.x`: correctness/stabilization
- `0.2.0+`: controlled feature/refactor milestones
- `1.0.0`: audited, deterministic, accepted behavior

Recommended tags:

```text
signalgate-dashboard/v0.1.0
liquidity-zones-tactical/v0.1.0
ma-6x/v0.1.0
```

Every promoted change records behavioral impact, timing/repaint impact, alert impact, configuration impact and validation evidence.

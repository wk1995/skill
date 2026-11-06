# Branch roles

The source A/x maps only to B/x. B's independently created default (for example
personal-main) and personal feature/maintenance branches are not source targets.
Source synchronization cannot merge or rebase personal work. Accidental personal
commits on a source branch block sync; preserve them on a personal branch first.

Select single, selected, or all upstream heads. existing-only updates the selected
registered intersection; include-new may create absent corresponding heads.
Neither grants permission to adopt existing unregistered branches, change roles,
delete B branches missing upstream, or alter the personal default setting. Plans
freeze SHA and selection: upstream branches created later need another plan.

If A's default is selected, its copied SHA is the initial personal base. Otherwise
the user selects a base from the copied sources. Always create a new personal
branch; names colliding with the native bootstrap default must be changed before
initialization. Native GitHub forking only exposes default/all creation; the CLI
then imports explicit heads and removes only an authorized unchanged bootstrap
head created by that operation. Reused repositories with extra heads require an
explicit migration; the initializer does not clean them up.

```mermaid
flowchart LR
    A5[A main 5] --> A7[A main 7]
    B5[B main 5] --> B7[B main 7]
    P5[B personal-main 5] --> PX[B personal-main 5 plus X]
    A5 -. fork .-> B5
    B5 -. initial base only .-> P5
    A7 -. manual source sync .-> B7
    PX --> P7[B personal-main 7 plus adapted X]
    B7 -. separate reviewed integrate .-> P7
```

Source sync publishes each branch using a verified fast-forward plus an explicit
expected-old lease. A lease does not by itself prove a safe fast-forward. The
personal integration workflow separately preserves history or creates a new
personal line; it never force-replaces a published personal default.

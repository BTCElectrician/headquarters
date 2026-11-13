<!-- reviewed: 2026-11-12 | review every: as needed -->
# Why a Headquarters

On a large construction job, the general foreman does not pull wire. The crews
do that, each on its own floor or system, each with its own foreman who knows
the local conditions. The general foreman's job is different. He knows which
crew owns which floor, what has been released for work, what is waiting on an
answer from the engineer, and what nobody touches until it has been inspected
and signed off. When a question comes in, he knows who should answer it. When
two crews need the same wall, he decides the order. When something is about
to be energized, he makes sure the person with authority has said yes.

Running several codebases with AI agents creates the same need. Each
repository is a crew with its own rules, its own tests and its own way of
shipping. An agent working inside one repository can do excellent work there.
What it cannot see is the rest of the job: which repository owns the change,
whether the work was approved or only discussed, whether the other service
that depends on this one will still accept what it sends, and whether pushing
this branch quietly ships to production.

Without a headquarters, the person running the work becomes the wiring. They
carry decisions from one chat to the next, re-explain the same context to
every new agent, and remember on their own which plans were approved and
which were only ideas. That works for one repository. It stops working
somewhere around the third, and it fails quietly: an agent picks up an old
plan and treats it as a go-ahead, or reports that a feature works because a
status note said so weeks ago.

A common first fix is to point one agent at every repository at once. That
solves the map problem and creates a new one. The agent can now reach
everything, and nothing tells it what it is allowed to touch, whose rules
apply in each place, or when it must stop and ask. It edits from one chair,
under no one's local rules.

A headquarters keeps the map and adds the foreman's discipline. It holds a
registry of who owns what, one place where permission is recorded, a short
list of decisions that only the operator can make, and the rules that keep
agents inside their lanes. The work itself still happens in the repository
that owns it, by a worker that follows that repository's rules. Headquarters
routes the work, checks that it landed where it was supposed to, and keeps
the record of what is released and what is still waiting.

The seven rules in `AGENTS.md` are that discipline written down. Each one
answers a specific failure: work done in the wrong place, permission inferred
from an old note, a confident claim about code nobody read, a change that
passed its own tests and broke the thing downstream, an irreversible action
taken without a yes, and a pile of open questions nobody prepared. The
history of when each rule was added is in `docs/HISTORY.md`.

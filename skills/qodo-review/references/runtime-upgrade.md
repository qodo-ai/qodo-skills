# Runtime upgrades for the review compatibility gate

If the version is older or cannot be parsed, do not run `whoami`, `login`, a review, or a managed tool and
do not describe the failure as an authentication problem. Choose one deployment-approved upgrade
route, explain it, and reuse covering runtime-update authorization or ask once before changing the
installation. For a parsed 1.x runtime, `qodo update` can reach approved 2.x when its recorded
origin has enabled legacy migration. Use the CLI's supported update check to select the route;
if its legacy alias still advertises 1.x, the same-origin recovery is `qodo update --channel latest-2`.
Do not assume every origin has activated migration or claim that normal updates can never cross majors.
For an unparseable runtime or no usable update route, use a checksum-pinned installer supplied by
Qodo or the organization with covering installation authorization. Preserve the recorded origin,
explicit version choices and update holds; never switch an enterprise deployment to the public
service or invent a digest. Make one approved runtime attempt, then rerun the unadorned version
probe and continue only when it satisfies the minimum. On denial, failure or continued
incompatibility, stop with skill and user files unchanged; do not retry through another route.

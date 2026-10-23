import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parent
continuation = root.parent.parent
design = root.parent / 'training-strategy-20261019-v1/EXPERIMENT_DESIGN.json'
state = {
    'date': '2026-10-20',
    'status': 'resumption-authorized-awaiting-working-authenticated-cluster-status',
    'cluster_available': 'Reported available again by user; service state not independently established',
    'attempts': [
        {'mode': 'sandbox noninteractive read-only SSH true', 'result': 'DNS unavailable in sandbox'},
        {'mode': 'approved network access, noninteractive read-only SSH true',
         'result': 'Resolved uc3.scc.kit.edu to 141.52.43.11; SSH key exchange reset before authentication'},
    ],
    'cluster_commands_executed': 0, 'new_jobs': 0, 'new_uploads': 0,
    'collection_job_id': None, 'collection_state': 'Still unconfirmed; no replacement permitted',
    'data_ready': False, 'checkpoint_unchanged': True, 'production_adoption': False,
    'strategy_sha256': hashlib.sha256(design.read_bytes()).hexdigest(),
    'cluster_check_sha256': hashlib.sha256((root/'Check-Existing-Collection.sh').read_bytes()).hexdigest(),
    'cluster_check_bash_syntax': 'passed',
    'required_input': 'Run the provided read-only check in an authenticated KIT terminal and return job/status output, never credentials.',
    'next_step': 'Identify/recover existing collection; review fresh data before CPU controls and paired GPU trials.',
}
(root/'CURRENT_STATE.json').write_text(json.dumps(state, indent=2)+'\n', encoding='utf-8')
handoff = continuation/'CURRENT_HANDOFF.md'
previous = root/'HANDOFF_BEFORE_RESUMPTION.md'
if not previous.exists():
    previous.write_bytes(handoff.read_bytes())
header = f'''# Current FrameTrail state — KIT resumption authorized, transport blocked

20 October 2026. The user reports KIT available again and explicitly instructs applying yesterday's data-first strategy. The outage is no longer the operative user-reported condition. Resume authorized work; do not ask for routine approval.

This agent's noninteractive read-only SSH probe failed: sandbox DNS was unavailable, then an approved-network attempt resolved uc3.scc.kit.edu to 141.52.43.11 but key exchange was reset before authentication. No remote command, upload, retrieval, scheduler query or submission executed. This does not establish that KIT remains down; it establishes that agent transport is currently unusable. Direct user authentication/status from a working cluster terminal is needed. Never request pasted credentials or keep making blind connection attempts.

Recovery artifacts: {root}
Check-Existing-Collection.sh passed bash syntax checking. It reads the existing submitted-job record and report if available; otherwise it shows this user's scheduler history from18October2026. It never submits, retries, replaces, uploads or extracts. The latest collection's job ID/completion remains unconfirmed. Identify it before any new collection or training. If no job exists, inspect upload/lock/account evidence before preparing a legitimate first submission; do not label an unknown run as completed.

The training design, data readiness and release gates remain unchanged. Four scientific conditions after fresh reviewed data: two local cached CPU controls and two GPU selector trials, paired seeds17/29, max1500 updates/condition, max1.5 allocated GPU-hours, at most two concurrent GPUs. Exact runnable package still requires actual source/scene/box-reviewed data, fixed splits, cache/loss parity and live account admission. No threshold/gate relaxation, no automatic retries/replacements, and no test-based selection. Current RF weights and ONNX hold remain unchanged.

The completed lean app package/launchers below remain current. Explain progress plainly in chat, continue authorized work until real input is needed, and end every response with one concrete next step and why.

Next step: obtain the read-only collection status from the user's working KIT terminal, because the agent cannot currently connect and no duplicate job should be created.

---

## Preserved verified app and training state

'''
handoff.write_text(header+previous.read_text(encoding='utf-8-sig'), encoding='utf-8')
print(json.dumps({'status': state['status'], 'new_jobs': 0, 'cluster_commands_executed': 0}))

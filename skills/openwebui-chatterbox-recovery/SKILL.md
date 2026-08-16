---
name: "openwebui-chatterbox-recovery"
description: "Restore and verify the known-good Open WebUI Chatterbox TTS behaviour after upgrades."
---

# Open WebUI Chatterbox Upgrade Recovery

Use this procedure after an Open WebUI upgrade/reinstall or whenever Read Aloud/autoplay stops behaving like the known-good Chatterbox setup.

## Protected behaviour

- Open WebUI TTS uses the loopback OpenAI-compatible bridge at `http://127.0.0.1:8010/v1`.
- Chatterbox runs CPU-only on demand through `chatterbox-nano.service`.
- It uses all logical CPUs minus one for intra-op/BLAS work, with one Torch inter-op thread.
- TTS text splits on every non-empty line break.
- Playback begins only after two completed clips are buffered.
- Later clips generate while earlier clips play.
- An empty playback queue does not mean completion while the producer is active.
- Explicit Stop aborts browser work, forwards to `/api/v1/audio/stop`, terminates inference, and unloads Chatterbox.
- Browser Kokoro must remain disabled/absent.
- Do not unload Ollama models as part of this CPU Chatterbox path.

## Durable files

- `~/.config/systemd/user/chatterbox-nano.service`
- `~/.config/systemd/user/chatterbox-nano.service.d/20-voice-app-default.conf`
- `~/.config/systemd/user/chatterbox-nano.service.d/30-cpu-performance.conf`
- `~/.config/systemd/user/openwebui-audio-bridge.service`
- `TTS_SST/chatterbox_nano_server.py`
- `TTS_SST/openwebui_audio_bridge.py`
- `TTS_SST/openwebui_chatterbox_stop_patch.py`

## Open WebUI patch owners

Generated chunk names are build-specific. Locate code semantically after an upgrade; do not assume old hashes survived.

Known-good Open WebUI 0.11.0 locations:

- TTS producer and two-clip startup buffer: `frontend/_app/immutable/chunks/Bd1cmSN4.js`
- Audio queue state (`producerActive`) and Stop lifecycle: `frontend/_app/immutable/chunks/ci5FwYEI.js`
- Authenticated Stop forwarding: `open_webui/routers/audio.py`

The two-clip buffer has this semantic shape:

```js
const startup = [];
// after each successful line TTS response:
if (startup.length < 2) {
  startup.push(url);
  if (startup.length === 2) {
    for (const clip of startup) audioQueue.enqueue(clip);
  }
} else {
  audioQueue.enqueue(url);
}
// producer completion fallback for replies shorter than two lines:
if (startup.length < 2) {
  for (const clip of startup) audioQueue.enqueue(clip);
}
```

The queue must retain a producer-active flag. When a clip ends and the queue is temporarily empty, it waits if production remains active; it completes only when the producer is inactive and the queue/current clip are empty.

## Recovery steps after an Open WebUI upgrade

1. Read `TOOLS.md` and current live service state first.
2. Confirm Open WebUI version and snapshot/rollback availability.
3. Search the new frontend chunks for the TTS request call, audio queue class, `enqueue`, `producerActive`, and Stop handler.
4. Compare new upstream behaviour with the protected behaviour above. Reapply only missing semantics.
5. Ensure `routers/audio.py` forwards authenticated Stop to the local bridge.
6. Confirm `30-cpu-performance.conf` computes/sets logical CPUs minus one for OMP, MKL and OpenBLAS; Torch health must report the computed thread count and `torch_interop_threads: 1`.
7. Reload systemd only if unit/drop-in files changed. Restart only affected services.
8. Hard-reload/relaunch the real Open WebUI app so changed immutable frontend assets are loaded.

## Acceptance checks

Configuration alone is not acceptance.

1. Parse edited JS as an ES module:
   `node --input-type=module --check < PATH_TO_CHUNK`
2. Direct bridge canary must return HTTP 200 and a valid 24 kHz mono PCM WAV.
3. Health must report CPU device, the expected computed Torch thread count, and one inter-op thread.
4. Real logged-in Chrome-app canary: use a fresh six-line response. Confirm six distinct TTS requests/clips, ordered continuous playback, two clips buffered before playback, and no repeats or early cutoff.
5. Real uncached Stop canary: Stop during active synthesis. Confirm the speech request is cancelled/failed as expected and `chatterbox-nano.service` becomes `inactive/dead`.
6. Confirm Open WebUI and bridge have zero unexpected restarts.
7. Run SQLite integrity check and delete only disposable test chats.
8. Record exact upgraded chunk names and rollback path in `TOOLS.md`.

## Known-good evidence

- Open WebUI 0.11.0 real Chrome-app test played six line-broken clips continuously.
- Uncached cancellation stopped active CPU inference and unloaded the service.
- Final tuning: two-line startup buffer and logical-CPU-count-minus-one worker threads.
- Keep a local rollback snapshot before reapplying upgrade patches; record its path in `TOOLS.md`.

# Agent Evolution — Final Setup

## 1. Python runtime
Run the Agent Evolution Python runtime on the Android device (for example in a local Python/Termux-style environment). Install dependencies from `requirements.txt`.

```bash
python -m pip install -r requirements.txt
```

## 2. Android controller
1. Open `android_controller/` in Android Studio.
2. Build the debug APK.
3. Install it on the Android phone.
4. Open the controller app.
5. In Android Settings, enable its Accessibility service.
6. Keep the controller running while an agent needs device control.

The controller uses localhost (`127.0.0.1:8787`) by default.

## 3. Internet agent
Configure legitimate service credentials through environment variables or the secret store used by the runtime. Do not put passwords/API keys in Git.

The Internet layer can browse public HTTPS pages and perform ordinary permitted browser actions. Login requires an account that the user is authorized to use.

## 4. Game AI
Add a permitted game package to `android_game_policy.json`, then run:

```bash
python game_ai/game_agent.py --package <GAME_PACKAGE> --steps 100
```

The agent learns from screen observations and action outcomes. Learning is persisted between sessions.

## 5. Game-file discovery
Explicitly grant the runtime access to a game-data directory and put that directory in `game_file_policy.json` under `allowed_roots`.

Then run:

```bash
python game_file_discovery.py discover
```

The system inventories supported save/config files and records field-meaning hypotheses. Experiments should use copies first:

```bash
python game_file_discovery.py experiment-copy /authorized/path/to/save.json
```

## 6. Important Android limitation
Android does not allow an ordinary app to read every other app's private data. The system only works with files and controls that Android explicitly makes accessible. It does not bypass scoped storage, encryption, DRM, anti-cheat, authentication, or protected executable code.

## 7. GitHub automation
GitHub Actions can run the farm's cloud-side logic, but it cannot directly control the physical Android phone. For phone control, run the Android controller + agent runtime locally or use a separately authenticated relay.

## 8. First test
Start small:
1. Enable Accessibility.
2. Open a game you are authorized to control.
3. Add its package to the allowlist.
4. Run the game agent for 20–50 steps.
5. Check `game_ai_state.json` and `game_learning_memory.jsonl`.
6. Grant a test save/config folder and run discovery.

Only after that should you increase the step/session limits.

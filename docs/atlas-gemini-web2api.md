# Atlas AI Runtime Playbook

Use this playbook when Codebase Atlas needs conversational explanations from Gemini Web2API. It is bundled with the portable ExcaliFlow skill so Codex, Antigravity, AGY, and other installed hosts can follow the same verified flow.

## Boundary first

- Atlas stays local, but an AI question and structural code context are sent through the local Gemini Web2API proxy to Gemini.
- Use it only with source context that the user permits to leave the machine.
- Bind Gemini Web2API and the Atlas Bridge to `127.0.0.1`; do not expose either service on LAN.
- ExcaliFlow never installs, starts, or authenticates this third-party proxy silently. A person or their AI agent performs those explicit actions.

## One diagnostic before changing anything

```powershell
excaliflow bridge doctor --dir "D:\MyProject" --port 8789
```

The diagnostic reports separately whether the project manifest, Gemini Web2API upstream, and Atlas Bridge are ready. Follow its `Next:` instruction; do not assume a listening port means that Gemini answers work.

## First-time local setup on Windows

```powershell
git clone --depth 1 https://github.com/Sophomoresty/gemini-web2api.git "D:\Sandbox\gemini-web2api"
cd "D:\Sandbox\gemini-web2api"
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Create `config.json` beside `gemini_web2api.py` with the safe local defaults:

```json
{
  "port": 8081,
  "host": "127.0.0.1",
  "api_keys": [],
  "temporary_chats": true,
  "log_requests": true
}
```

`api_keys: []` lets the browser-side Atlas use the local proxy without embedding a secret. `temporary_chats: true` asks Gemini Web to use temporary chats. These choices do not make Gemini processing local or private.

## Start the two local services

Terminal 1 starts the upstream:

```powershell
cd "D:\Sandbox\gemini-web2api"
.\.venv\Scripts\python.exe gemini_web2api.py
```

Terminal 2 starts the project bridge. Choose the same port used when creating the manifest; `8789` is an example when `8788` is already in use.

```powershell
cd "D:\Sandbox\ExcaliFlow Studio"
$env:PYTHONPATH = "$PWD\src"
py -3 -m excaliflow.cli bridge start --dir "D:\MyProject" --port 8789
```

Then refresh the Atlas HTML and ask a question. Keep both terminals running while using AI answers.

## Verify end to end

```powershell
excaliflow bridge doctor --dir "D:\MyProject" --port 8789
```

Expected status is `ready` for all three lines. If Gemini is unavailable, Atlas deliberately falls back to source-backed local explanations rather than pretending an AI answer was received.

## Troubleshooting

| Doctor result | Meaning | Safe next action |
|---|---|---|
| Project manifest missing or invalid | Atlas has no project bridge contract. | Run `excaliflow bridge init --dir "D:\MyProject" --port 8789`. |
| Gemini Web2API not responding | Upstream is stopped, misconfigured, or cannot reach Gemini. | Start it from its own folder; inspect its terminal output before changing settings. |
| Atlas Bridge not responding | The local proxy is not running or is using another port. | Start `excaliflow bridge start` with the manifest port. |
| All ready but a question fails | Gemini can still reject/rate-limit an individual request. | Read the Gemini terminal log; Atlas will fall back to source-backed local evidence. |

For current Gemini Web2API options and limitations, consult its upstream README. Do not add cookies or credentials to a project repository.

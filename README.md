# MISTRAL WORLDWIDE HACKS 2K26

> Hackathon submissions. Each folder = one project.

## Projects

| Project | Description |
|---------|-------------|
| [`swarm/`](./swarm/) | Darwinian multi-agent debate arena powered by Mistral |
| [`backend-relay/`](./backend-relay/) | HTTP/WS relay between Game Master and Swarm arena |
| [`mistralski/`](./mistralski/) | **Game Master "Mistralski"** — autonomous adversarial AI that crafts news, manipulates the player, and strategizes against arena agents |

### Mistralski — Game Master Agent

The GM is an **autonomous Mistral-powered agent** with its own memory, per-agent vision files, and multi-turn strategy. It plays the role of Eric Cartman running a satirical disinformation dashboard.

**Key features:**
- Mistral Large function calling with 5 tools (read/write memory, agent vision files)
- Generates 3 news per turn (real/fake/satirical) with full Gorafi-style articles
- Secretly manipulates the player into choosing the strategically optimal news
- Maintains persistent dossiers on each arena agent (threat level, vulnerabilities, targeted strategy)
- SSE streaming endpoints for real-time frontend integration (Lovable)
- Connects to the Swarm arena via the backend-relay (HTTP + WebSocket)

```
Player ←→ Lovable (frontend) ←→ Mistralski (GM) ←→ backend-relay ←→ Swarm (agents)
```

---

Built with Mistral AI APIs during the Mistral Worldwide Hacks 2026.

import express, { Request, Response } from "express";
import path from "path";
import fetch from "node-fetch";
import { RunResult, TaskRequest } from "./types";

const app = express();
const PORT = process.env.PORT ? Number(process.env.PORT) : 3000;
const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8420";

app.use(express.json());
app.use(express.static(path.join(__dirname, "..", "public")));

// Thin BFF layer: the browser never talks to FastAPI directly. This is
// where you'd add auth, rate limiting, or response shaping specific to
// the dashboard without touching the orchestration service.
app.post("/api/runs", async (req: Request, res: Response) => {
  const body: TaskRequest = req.body;
  if (!body.query || typeof body.query !== "string") {
    res.status(400).json({ error: "Field 'query' (string) is required." });
    return;
  }
  try {
    const backendRes = await fetch(`${BACKEND_URL}/runs`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = (await backendRes.json()) as RunResult;
    res.status(backendRes.status).json(data);
  } catch (err) {
    res.status(502).json({ error: `Backend unreachable: ${(err as Error).message}` });
  }
});

app.get("/api/runs", async (_req: Request, res: Response) => {
  try {
    const backendRes = await fetch(`${BACKEND_URL}/runs`);
    const data = await backendRes.json();
    res.status(backendRes.status).json(data);
  } catch (err) {
    res.status(502).json({ error: `Backend unreachable: ${(err as Error).message}` });
  }
});

app.get("/api/health", async (_req: Request, res: Response) => {
  try {
    const backendRes = await fetch(`${BACKEND_URL}/health`);
    const data = await backendRes.json();
    res.json({ frontend: "ok", backend: data });
  } catch (err) {
    res.status(502).json({ frontend: "ok", backend: "unreachable" });
  }
});

app.listen(PORT, () => {
  // eslint-disable-next-line no-console
  console.log(`Frontend BFF listening on http://localhost:${PORT} (backend: ${BACKEND_URL})`);
});

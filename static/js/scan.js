// Live company scan: start it, then read the Server-Sent Events stream as it runs.

import { api } from "./lib/api.js";

const button = document.querySelector("[data-scan-start]");
const log = document.getElementById("scan-log");
const status = document.getElementById("scan-status");

function addLine(event) {
  const item = document.createElement("li");
  item.className = event.status || event.step;
  const step = document.createElement("span");
  step.className = "step";
  step.textContent = event.step.replace("_", " ");
  const message = document.createElement("span");
  message.textContent = event.message; // textContent, never innerHTML: it's site text
  item.append(step, message);
  log.append(item);
  log.scrollTop = log.scrollHeight;
}

button?.addEventListener("click", async () => {
  button.disabled = true;
  log.replaceChildren();
  log.hidden = false;
  status.className = "state busy";
  status.textContent = "Scanning. Each step appears below as it happens.";
  try {
    const { events_url: eventsUrl } = await api(button.dataset.scanStart, { method: "POST" });
    const stream = new EventSource(eventsUrl);
    const steps = ["check", "robots", "page", "skip", "ai", "ai_done", "ai_skipped",
      "baseline", "alerts", "busy", "done"];
    steps.forEach((step) =>
      stream.addEventListener(step, (message) => {
        const event = JSON.parse(message.data);
        addLine(event);
        if (step === "done" || step === "busy") {
          stream.close();
          status.className = event.status === "completed" ? "state" : "state error";
          status.textContent = event.status === "completed"
            ? "Done. Reloading to show the profile and any alerts…"
            : event.message;
          if (event.status === "completed") setTimeout(() => window.location.reload(), 900);
          else button.disabled = false;
        }
      }),
    );
    stream.onerror = () => {
      stream.close();
      status.className = "state error";
      status.textContent = "Lost the connection to the scan. Reload to see where it got to.";
      button.disabled = false;
    };
  } catch (error) {
    status.className = "state error";
    status.textContent = error.message;
    button.disabled = false;
  }
});

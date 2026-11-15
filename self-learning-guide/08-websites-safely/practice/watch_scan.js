// Paste into the browser console (after the api() helper) to watch a scan live.
function watch(eventsUrl) {
  const stream = new EventSource(eventsUrl);
  const steps = ["check", "robots", "page", "skip", "ai", "ai_done", "ai_skipped",
    "baseline", "alerts", "busy", "done"];
  for (const step of steps) {
    stream.addEventListener(step, (message) => {
      const event = JSON.parse(message.data);
      console.log(`[${step}] ${event.message}`);
      if (step === "done" || step === "busy") stream.close();
    });
  }
  stream.onerror = () => stream.close();
}

console.log("watch() ready");

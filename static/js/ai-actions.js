// Buttons that ask Gemini for something (run explanation, committee review).
// <button data-ai-action="/api/v1/..." data-busy="Asking the analyst…">
// On success the page reloads to show the stored, labelled analysis; on failure the API's
// own message is shown next to the button (quota used up, no key, rate limited...).

import { api } from "./lib/api.js";

document.querySelectorAll("[data-ai-action]").forEach((button) => {
  const status = document.getElementById(button.dataset.status);
  button.addEventListener("click", async () => {
    button.disabled = true;
    if (status) {
      status.className = "state busy";
      status.textContent = button.dataset.busy || "Working…";
    }
    try {
      await api(button.dataset.aiAction, { method: "POST" });
      window.location.hash = button.dataset.anchor || "";
      window.location.reload();
    } catch (error) {
      button.disabled = false;
      if (status) {
        status.className = "state error";
        status.textContent = error.message;
      }
    }
  });
});

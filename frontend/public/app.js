// Intentional stage 2 exercise: the browser cannot resolve a Compose service name.
// The next commit replaces this with a same-origin URL and an Nginx proxy.
const HEALTH_URL = "http://backend:8000/api/health";

const status = document.querySelector("#connection-status");
const detail = document.querySelector("#connection-detail");
const retry = document.querySelector("#retry");

async function checkConnection() {
  retry.disabled = true;
  status.dataset.state = "checking";
  status.textContent = "Checking…";
  detail.textContent = "Checking the workspace connection…";

  try {
    const response = await fetch(HEALTH_URL, {
      cache: "no-store",
      signal: AbortSignal.timeout(6000),
    });
    if (!response.ok || (await response.json()).status !== "ok") {
      throw new Error("Workspace unavailable");
    }
    status.dataset.state = "ok";
    status.textContent = "Connected";
    detail.textContent = "The workspace is connected and ready for the next stage.";
  } catch {
    status.dataset.state = "error";
    status.textContent = "Unavailable";
    detail.textContent = "We couldn’t connect just now. Please try again.";
  } finally {
    retry.disabled = false;
  }
}

retry.addEventListener("click", checkConnection);
checkConnection();

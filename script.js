const $ = (id) => document.getElementById(id);
let lastAdvice = null;

// ---- helpers ----
function setStatus(msg, isError = false) {
  $("status").textContent = msg;
  $("status").classList.toggle("error", isError);
}

function getProfile() {
  const conditions = [...document.querySelectorAll("fieldset input[type=checkbox][value]")]
    .filter((c) => c.checked)
    .map((c) => c.value);
  return {
    city: $("city").value,
    age_group: $("age").value,
    conditions,
    outdoor_worker: $("outdoor").checked,
  };
}

function fillList(id, items) {
  const ul = $(id);
  ul.innerHTML = "";
  (items || []).forEach((t) => {
    const li = document.createElement("li");
    li.textContent = t;
    ul.appendChild(li);
  });
}

function badgeClass(band) {
  const b = (band || "").toLowerCase();
  if (b.startsWith("good")) return "good";
  if (b.startsWith("moderate")) return "moderate";
  if (b.startsWith("unhealthy for")) return "usg";
  if (b.startsWith("very")) return "vunhealthy";
  if (b.startsWith("hazardous")) return "hazardous";
  return "unhealthy";
}

// ---- hero: show live AQI and tint the page with today's band ----
function animateNumber(el, target) {
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
    el.textContent = target;
    return;
  }
  const start = performance.now();
  const duration = 900;
  const step = (t) => {
    const p = Math.min((t - start) / duration, 1);
    el.textContent = Math.round(target * (1 - Math.pow(1 - p, 3)));
    if (p < 1) requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
}

function showHero(data) {
  document.body.dataset.band = badgeClass(data.band);
  $("heroCity").textContent = data.city;
  $("heroBand").textContent = data.band;
  animateNumber($("heroAqi"), data.aqi);
}

// ---- live AQI ----
async function loadAqi() {
  $("aqi").value = "";
  $("aqi").placeholder = "loading...";
  try {
    const res = await fetch("/api/aqi?city=" + encodeURIComponent($("city").value));
    const data = await res.json();
    if (!res.ok) throw new Error(data.error);
    $("aqi").value = data.aqi;
    showHero(data);
    setStatus("");
  } catch (e) {
    $("heroAqi").textContent = "--";
    $("heroBand").textContent = "Live data unavailable. Enter the AQI below.";
    $("aqi").placeholder = "enter AQI";
    setStatus("Could not get live AQI. Please enter the AQI manually.", true);
  }
}
$("city").addEventListener("change", loadAqi);

// ---- AI guidance ----
$("btn").addEventListener("click", async () => {
  const aqi = $("aqi").value;
  if (aqi === "") { setStatus("Please enter the AQI first.", true); return; }

  $("btn").disabled = true;
  $("result").classList.add("hidden");
  setStatus("The AI is preparing your guidance...");

  try {
    const res = await fetch("/api/advice", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ aqi, profile: getProfile(), language: $("lang").value }),
    });
    const data = await res.json();
    if (!res.ok) { setStatus(data.error || "Something went wrong.", true); return; }

    lastAdvice = data;
    $("badge").textContent = `AQI ${data.aqi} - ${data.band} | For you: ${data.risk_level || ""}`;
    $("badge").className = "badge " + badgeClass(data.band);
    $("headline").textContent = data.headline || "";
    const go = data.go_outside || {};
    $("outside").textContent = `Going outside: ${go.verdict || ""}. ${go.details || ""}`;
    $("mask").textContent = `Mask: ${data.mask || ""}`;
    fillList("do", data.do);
    fillList("avoid", data.avoid);
    fillList("home", data.home_tips);
    fillList("doctor", data.see_doctor_if);
    $("answer").textContent = "";
    $("result").classList.remove("hidden");
    setStatus("");
  } catch (e) {
    setStatus("Could not reach the server. Check your internet or the server.", true);
  } finally {
    $("btn").disabled = false;
  }
});

// ---- follow-up question ----
$("askBtn").addEventListener("click", async () => {
  const question = $("question").value.trim();
  if (!question) { setStatus("Please write a question first.", true); return; }
  $("askBtn").disabled = true;
  setStatus("The AI is thinking...");
  try {
    const res = await fetch("/api/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        question, aqi: $("aqi").value, profile: getProfile(),
        language: $("lang").value, advice: lastAdvice,
      }),
    });
    const data = await res.json();
    if (!res.ok) { setStatus(data.error || "Something went wrong.", true); return; }
    $("answer").textContent = data.answer;
    setStatus("");
  } catch (e) {
    setStatus("Could not reach the server.", true);
  } finally {
    $("askBtn").disabled = false;
  }
});

// ---- read aloud (free browser voice) ----
$("speak").addEventListener("click", () => {
  if (!lastAdvice || !window.speechSynthesis) return;
  const text = [lastAdvice.headline, lastAdvice.mask, ...(lastAdvice.do || [])].filter(Boolean).join(". ");
  const u = new SpeechSynthesisUtterance(text);
  u.lang = $("lang").value.startsWith("English") ? "en-US" : "ur-PK";
  window.speechSynthesis.cancel();
  window.speechSynthesis.speak(u);
});

loadAqi();
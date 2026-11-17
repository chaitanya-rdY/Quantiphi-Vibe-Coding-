import { api } from "./api.js";
import { $, el, clear } from "./dom.js";
import * as view from "./render.js";

let current = null;
let currentData = null;

const SUGGESTIONS = [
  "What are their top languages?", "What is their most popular project?",
  "How consistent are they?", "How well do they fit the job?", "Give me a summary",
];

function setLoading(on) {
  $("#loading").hidden = !on;
  $("#empty").hidden = true;
  document.querySelectorAll("#search-form button").forEach((b) => (b.disabled = on));
}

function hideAll() {
  ["#profile", "#stats", "#activity", "#tools", "#repos-section"].forEach((s) => ($(s).hidden = true));
  clear($("#notices"));
}

async function load(username, refresh = false) {
  username = username.trim();
  if (!username) return;
  hideAll();
  setLoading(true);
  try {
    const [data, last] = await Promise.all([api.portfolio(username, refresh), api.lastMatch(username)]);
    current = username;
    currentData = data;
    localStorage.setItem("lastUser", username);
    history.replaceState(null, "", `#${username}`);

    view.renderProfile(data, last.match);
    view.renderStats(data.contributions);
    view.renderHeatmap(data.contributions);
    view.renderRepos(data.repos);
    view.renderMatchDetail(last.match);
    $("#jd").value = last.job_description || "";
    $("#tools").hidden = false;
    resetChat();

    if (data.meta.stale) view.notice("warn", "GitHub is unreachable or rate-limited — showing cached data.");
    if (data.contributions.source === "unavailable") view.notice("warn", "Could not load contributions. Set GITHUB_TOKEN on the server for the full calendar.");
  } catch (err) {
    $("#empty").hidden = false;
    view.notice("err", err.message);
  } finally {
    setLoading(false);
  }
}

// ---- tech stack compatibility ----
async function analyze() {
  const jd = $("#jd").value.trim();
  $("#match-error").textContent = "";
  if (jd.length < 3) { $("#match-error").textContent = "Paste a job description first."; return; }
  $("#analyze").disabled = true;
  try {
    const m = await api.match(current, jd);
    $("#match-badge").replaceWith(view.renderMatchBadge(m));
    view.renderMatchDetail(m);
  } catch (err) {
    $("#match-error").textContent = err.message;
  } finally {
    $("#analyze").disabled = false;
  }
}

// ---- chat assistant ----
function addMsg(kind, text) {
  const log = $("#chat-log");
  log.append(el("div", { class: `msg ${kind}` }, text));
  log.scrollTop = log.scrollHeight;
}

function setChips(list) {
  const chips = $("#chips");
  clear(chips);
  list.forEach((s) => chips.append(el("button", { type: "button", onclick: () => ask(s) }, s)));
}

function resetChat() {
  clear($("#chat-log"));
  clear($("#bio-out"));
  addMsg("bot", `Hi! Ask me anything about ${currentData.profile.name}'s GitHub profile.`);
  setChips(SUGGESTIONS);
}

async function ask(question) {
  if (!question.trim() || !current) return;
  addMsg("user", question);
  $("#chat-input").value = "";
  try {
    const res = await api.chat(current, question);
    addMsg("bot", res.answer);
    setChips(res.suggestions);
  } catch (err) {
    addMsg("bot", `Sorry — ${err.message}`);
  }
}

async function generateBio() {
  const out = $("#bio-out");
  clear(out);
  try {
    const b = await api.bio(current);
    out.append(
      el("h3", {}, b.headline), el("p", {}, b.bio),
      el("div", { class: "chips" }, b.highlights.map((h) => el("span", { class: "chip" }, h))),
      b.pitch ? el("p", {}, el("strong", {}, "Pitch: "), b.pitch) : null);
  } catch (err) {
    out.append(el("p", { class: "error" }, err.message));
  }
}

// ---- wiring ----
$("#search-form").addEventListener("submit", (e) => { e.preventDefault(); load($("#username").value); });
$("#refresh").addEventListener("click", () => current && load(current, true));
$("#analyze").addEventListener("click", analyze);
$("#chat-form").addEventListener("submit", (e) => { e.preventDefault(); ask($("#chat-input").value); });
$("#bio-btn").addEventListener("click", generateBio);

const initial = location.hash.slice(1) || localStorage.getItem("lastUser") || "";
if (initial) { $("#username").value = initial; load(initial); }

// Presentation-only rendering. All numbers arrive pre-computed from the backend.
import { el, $, clear } from "./dom.js";

const LANG_COLORS = {
  Python: "#3572A5", JavaScript: "#f1e05a", TypeScript: "#3178c6", Java: "#b07219", "C++": "#f34b7d",
  C: "#8a8a8a", "C#": "#178600", Go: "#00ADD8", Rust: "#dea584", Ruby: "#cc342d", PHP: "#4F5D95",
  Shell: "#89e051", HTML: "#e34c26", CSS: "#563d7c", Kotlin: "#A97BFF", Swift: "#F05138",
  "Jupyter Notebook": "#DA5B0B", Dart: "#00B4AB", SQL: "#e38c00", MATLAB: "#e16737",
};
export function langColor(name) {
  if (LANG_COLORS[name]) return LANG_COLORS[name];
  let h = 0;
  for (const ch of name) h = (h * 31 + ch.charCodeAt(0)) % 360;
  return `hsl(${h} 60% 55%)`;
}

const fmt = (n) => (n >= 1000 ? `${(n / 1000).toFixed(1)}k` : String(n));

export function renderMatchBadge(match) {
  if (!match || match.percent == null) {
    return el("span", { class: "match-badge none", id: "match-badge" }, "Match: add a job description ↓");
  }
  const cls = { "Strong Match": "strong", "Good Match": "good", "Partial Match": "partial" }[match.label] || "low";
  return el("span", { class: `match-badge ${cls}`, id: "match-badge" }, `◎ ${match.percent}% · ${match.label}`);
}

function renderPie(languages) {
  const top = languages.slice(0, 6);
  let acc = 0;
  const stops = top.map((l) => {
    const from = acc; acc += l.percent;
    return `${langColor(l.language)} ${from}% ${acc}%`;
  });
  if (acc < 100) stops.push(`#3a4658 ${acc}% 100%`);
  const bg = top.length ? `conic-gradient(${stops.join(", ")})` : "#243044";
  return el("div", {},
    el("div", { class: "pie-title" }, "Top languages"),
    el("div", { class: "pie-box" },
      el("div", { class: "pie", style: `background:${bg}`, role: "img", "aria-label": "Top languages pie chart" }),
      el("ul", { class: "pie-legend" }, top.map((l) =>
        el("li", {}, el("i", { style: `background:${langColor(l.language)}` }), `${l.language} ${l.percent}%`)))));
}

export function renderProfile(data, match) {
  const p = data.profile;
  const root = $("#profile");
  clear(root);
  const left = el("div", {},
    el("div", { class: "who" },
      el("img", { class: "avatar", src: p.avatar_url || "", alt: `${p.login} avatar` }),
      el("div", {},
        el("h1", {}, p.name),
        el("a", { class: "handle", href: p.html_url, target: "_blank", rel: "noopener noreferrer" }, `@${p.login}`),
        p.bio ? el("p", { class: "bio" }, p.bio) : null)),
    renderMatchBadge(match),
    el("div", { class: "meta" },
      [["Followers", p.followers], ["Total stars", p.total_stars], ["Forks", p.total_forks], ["Repos", p.repo_count]]
        .map(([label, v]) => el("div", { class: "m" }, el("b", {}, fmt(v)), el("span", {}, label)))));
  root.append(left, renderPie(data.languages));
  root.hidden = false;
}

export function renderStats(c) {
  const root = $("#stats");
  clear(root);
  [["Current streak", `${c.current_streak}d`], ["Longest streak", `${c.longest_streak}d`],
   ["Contributions", fmt(c.total)], ["Active days", c.active_days]]
    .forEach(([label, v]) => root.append(el("div", { class: "stat" }, el("b", {}, v), el("span", {}, label))));
  root.hidden = false;
}

export function renderHeatmap(c) {
  const wrap = $("#heatmap");
  clear(wrap);
  $("#activity-source").textContent =
    c.source === "graphql" ? "Last 12 months" :
    c.source === "events" ? "Approximate · recent public events (add a GITHUB_TOKEN for the full calendar)" :
    "Contribution data unavailable";
  if (!c.days.length) {
    wrap.append(el("p", { class: "muted" }, "No contribution data to show."));
  } else {
    const grid = el("div", { class: "heatmap" });
    const lead = new Date(c.days[0].date + "T00:00:00Z").getUTCDay(); // align first column to Sunday
    for (let i = 0; i < lead; i++) grid.append(el("i", { class: "cell", style: "visibility:hidden" }));
    c.days.forEach((d) =>
      grid.append(el("i", { class: `cell l${d.level}`, title: `${d.count} contribution${d.count === 1 ? "" : "s"} on ${d.date}` })));
    wrap.append(grid);
  }
  $("#activity").hidden = false;
}

export function renderRepos(repos) {
  const root = $("#repos");
  clear(root);
  $("#repo-count").textContent = `${repos.length} repositories · sorted by stars`;
  repos.forEach((r) => root.append(
    el("article", { class: "repo" },
      el("h3", {}, el("a", { href: r.html_url, target: "_blank", rel: "noopener noreferrer" }, r.name)),
      el("p", {}, r.description || "No description provided."),
      el("div", { class: "foot" },
        r.language ? el("span", { class: "lang" }, el("i", { style: `background:${langColor(r.language)}` }), r.language) : null,
        el("span", {}, `★ ${fmt(r.stars)}`),
        el("span", {}, `⑂ ${fmt(r.forks)}`)))));
  $("#repos-section").hidden = false;
}

export function renderMatchDetail(m) {
  const root = $("#match-detail");
  clear(root);
  if (!m) return;
  if (m.percent == null) { root.append(el("p", { class: "muted" }, m.message)); return; }
  const group = (title, chips) => chips.length
    ? el("div", { class: "match-group" }, el("h3", {}, title), el("div", { class: "chips" }, chips)) : null;
  root.append(
    group("Matched", m.matched.map((x) => el("span", { class: "chip ok" }, `${x.language} · ${x.your_repos} repos`))),
    group("Missing from your repos", m.missing.map((x) => el("span", { class: "chip miss" }, x.language))),
    group("Bonus skills", m.bonus.map((x) => el("span", { class: "chip bonus" }, x))));
}

export function notice(kind, text) {
  $("#notices").append(el("div", { class: `notice ${kind}` }, text));
}

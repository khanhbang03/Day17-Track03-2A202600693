const benchmarkData = {
  standard: {
    baselineRecall: 3.6,
    advancedRecall: 100,
    baselineTokens: 12852,
    advancedTokens: 23699,
    insight: "<span>↑ 27.8×</span> stronger recall across normal sessions.",
    verdict: '<span class="verdict-icon">↗</span><p><b>Expected overhead.</b> Persistent memory costs more before compaction activates.</p>',
    proof: ["1.0", "Perfect advanced recall.", "Every expected stable fact was recovered across fresh sessions."]
  },
  stress: {
    baselineRecall: 0,
    advancedRecall: 100,
    baselineTokens: 21718,
    advancedTokens: 15362,
    insight: "<span>+100 pts</span> recall after moving into a completely fresh thread.",
    verdict: '<span class="verdict-icon">↘</span><p><b>29.3% fewer prompt tokens.</b> Seven compactions keep long context under control.</p>',
    proof: ["29.3%", "Less context. Full recall.", "Compact memory cuts prompt load without sacrificing a single expected fact."]
  }
};

const comparisonData = {
  standard: {
    label: "Standard suite",
    baselineRecall: "3.6%",
    advancedRecall: "100%",
    recallVerdict: "27.8× stronger recall.",
    baselinePrompt: 12852,
    advancedPrompt: 23699,
    baselinePromptNote: "Lower short-chat context cost.",
    advancedPromptNote: "Profile overhead before compaction.",
    promptWinner: "Baseline",
    promptWinnerClass: "baseline-win",
    promptVerdict: "Wins for short conversations.",
    baselineOutput: 1080,
    advancedOutput: 2005,
    baselineQuality: "0.161",
    advancedQuality: "1.000",
    advancedStorage: "341 bytes",
    compactions: "0",
    compactionNote: "Threshold not reached.",
    compactionWinner: "Not needed"
  },
  stress: {
    label: "Long-context stress",
    baselineRecall: "0%",
    advancedRecall: "100%",
    recallVerdict: "+100 percentage points.",
    baselinePrompt: 21718,
    advancedPrompt: 15362,
    baselinePromptNote: "Full history grows every turn.",
    advancedPromptNote: "Compaction bounds carried context.",
    promptWinner: "Advanced",
    promptWinnerClass: "advanced-win",
    promptVerdict: "29.3% fewer prompt tokens.",
    baselineOutput: 192,
    advancedOutput: 391,
    baselineQuality: "0.125",
    advancedQuality: "1.000",
    advancedStorage: "248 bytes",
    compactions: "7",
    compactionNote: "Seven real threshold triggers.",
    compactionWinner: "Advanced"
  }
};

const formatNumber = value => new Intl.NumberFormat("en-US").format(value);
const $ = selector => document.querySelector(selector);
const $$ = selector => [...document.querySelectorAll(selector)];

const revealObserver = new IntersectionObserver(entries => {
  entries.forEach(entry => {
    if (!entry.isIntersecting) return;
    const delay = Number(entry.target.dataset.delay || 0);
    setTimeout(() => entry.target.classList.add("visible"), delay);
    revealObserver.unobserve(entry.target);
  });
}, { threshold: .12 });
$$(".reveal").forEach(el => revealObserver.observe(el));

document.addEventListener("pointermove", event => {
  const glow = $(".cursor-glow");
  glow.style.left = `${event.clientX}px`;
  glow.style.top = `${event.clientY}px`;
});

const architectureCopy = {
  short: "<b>Incoming message</b> → keep recent turns verbatim → answer immediate follow-ups with full local fidelity.",
  profile: "<b>Stable assertion</b> → confidence filter → structured field upsert → persist across every future thread.",
  compact: "<b>Token threshold crossed</b> → summarize older turns → enforce summary bound → retain the six newest messages."
};
$$(".memory-layer").forEach(layer => {
  layer.addEventListener("click", () => {
    $$(".memory-layer").forEach(item => item.classList.remove("active"));
    layer.classList.add("active");
    $("#architectureDetail p").innerHTML = architectureCopy[layer.dataset.layer];
  });
});

function animateChart() {
  $$(".chart-line").forEach(line => {
    line.style.transition = "none";
    line.style.strokeDashoffset = "1";
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        line.style.transition = "stroke-dashoffset 1.5s cubic-bezier(.2,.8,.2,1)";
        line.style.strokeDashoffset = "0";
      });
    });
  });
}
$("#replayChart").addEventListener("click", animateChart);

function setSuite(name) {
  const data = benchmarkData[name];
  $$(".suite-toggle button").forEach(button => button.classList.toggle("active", button.dataset.suite === name));
  $("#baselineRecall").textContent = data.baselineRecall;
  $("#advancedRecall").textContent = data.advancedRecall;
  $(".baseline-ring").style.setProperty("--score", data.baselineRecall);
  $(".advanced-ring").style.setProperty("--score", data.advancedRecall);
  $("#baselineTokens").textContent = formatNumber(data.baselineTokens);
  $("#advancedTokens").textContent = formatNumber(data.advancedTokens);
  const max = Math.max(data.baselineTokens, data.advancedTokens);
  $(".baseline-bar").style.width = `${data.baselineTokens / max * 100}%`;
  $(".advanced-bar").style.width = `${data.advancedTokens / max * 100}%`;
  $("#recallInsight").innerHTML = data.insight;
  $("#tokenVerdict").innerHTML = data.verdict;
  $("#proofNumber").textContent = data.proof[0];
  $("#proofTitle").textContent = data.proof[1];
  $("#proofCopy").textContent = data.proof[2];
  animateChart();
}
$$(".suite-toggle button").forEach(button => button.addEventListener("click", () => setSuite(button.dataset.suite)));
setTimeout(() => setSuite("standard"), 500);

$$(".results-filter button").forEach(button => button.addEventListener("click", () => {
  const filter = button.dataset.resultsFilter;
  $$(".results-filter button").forEach(item => item.classList.toggle("active", item === button));
  $$("#fullBenchmarkTable tbody tr").forEach(row => {
    row.classList.toggle("hidden", filter !== "all" && row.dataset.resultSuite !== filter);
  });
}));

$("#copyResults").addEventListener("click", async () => {
  const rows = [
    ["Benchmark suite", "Agent", "Agent tokens only", "Prompt tokens processed", "Cross-session recall", "Response quality", "Memory growth (bytes)", "Compactions"],
    ["Standard", "Baseline", "1080", "12852", "0.036", "0.161", "0", "0"],
    ["Standard", "Advanced", "2005", "23699", "1.000", "1.000", "341", "0"],
    ["Long-Context Stress", "Baseline", "192", "21718", "0.000", "0.125", "0", "0"],
    ["Long-Context Stress", "Advanced", "391", "15362", "1.000", "1.000", "248", "7"]
  ];
  const text = rows.map(row => row.join("\t")).join("\n");
  const button = $("#copyResults");
  try {
    await navigator.clipboard.writeText(text);
    button.innerHTML = "Copied <span>✓</span>";
    button.classList.add("copied");
  } catch {
    button.innerHTML = "Copy unavailable";
  }
  setTimeout(() => {
    button.innerHTML = "Copy table <span>⧉</span>";
    button.classList.remove("copied");
  }, 1800);
});

function setComparisonSuite(name) {
  const data = comparisonData[name];
  $$(".compare-suite button").forEach(button => button.classList.toggle("active", button.dataset.compareSuite === name));
  ["Recall", "Tokens", "Output", "Quality", "Storage", "Compactions"].forEach(metric => {
    $(`#compareSuite${metric}`).textContent = data.label;
  });
  $("#compareBaselineRecall").textContent = data.baselineRecall;
  $("#compareAdvancedRecall").textContent = data.advancedRecall;
  $("#compareRecallVerdict").textContent = data.recallVerdict;
  $("#compareBaselinePrompt").textContent = formatNumber(data.baselinePrompt);
  $("#compareAdvancedPrompt").textContent = formatNumber(data.advancedPrompt);
  $("#compareBaselinePromptNote").textContent = data.baselinePromptNote;
  $("#compareAdvancedPromptNote").textContent = data.advancedPromptNote;
  const winner = $("#comparePromptWinner");
  winner.textContent = data.promptWinner;
  winner.className = `winner ${data.promptWinnerClass}`;
  $("#comparePromptVerdict").textContent = data.promptVerdict;
  $("#compareBaselineOutput").textContent = formatNumber(data.baselineOutput);
  $("#compareAdvancedOutput").textContent = formatNumber(data.advancedOutput);
  $("#compareBaselineQuality").textContent = data.baselineQuality;
  $("#compareAdvancedQuality").textContent = data.advancedQuality;
  $("#compareAdvancedStorage").textContent = data.advancedStorage;
  $("#compareAdvancedCompactions").textContent = data.compactions;
  $("#compareCompactionNote").textContent = data.compactionNote;
  const compactWinner = $("#compareCompactionWinner");
  compactWinner.textContent = data.compactionWinner;
  compactWinner.className = `winner ${name === "stress" ? "advanced-win" : "neutral-win"}`;
}

$$(".compare-suite button").forEach(button => button.addEventListener("click", () => setComparisonSuite(button.dataset.compareSuite)));
$$(".compare-filters button").forEach(button => button.addEventListener("click", () => {
  const category = button.dataset.compareFilter;
  $$(".compare-filters button").forEach(item => item.classList.toggle("active", item === button));
  $$(".comparison-row[data-category]").forEach(row => row.classList.toggle("hidden", category !== "all" && row.dataset.category !== category));
}));
setComparisonSuite("standard");

const demoSteps = [
  {
    thread: "THREAD_A",
    messages: [
      ["user", "USR", "Mình tên là DũngCT, ở Đà Nẵng và đang làm backend engineer."],
      ["agent", "AGT", "Đã ghi nhận các thông tin ổn định của bạn."]
    ],
    profile: `<span class="md-h"># User Profile</span>

<span class="md-h">## Facts</span>
- <span class="md-key">name:</span> <span class="md-value">DũngCT</span>
- <span class="md-key">location:</span> <span class="md-value">Đà Nẵng</span>
- <span class="md-key">profession:</span> <span class="md-value">backend engineer</span>`,
    event: "3 durable facts inserted"
  },
  {
    thread: "THREAD_A",
    messages: [
      ["user", "USR", "Mình không còn làm backend engineer nữa. Giờ chuyển sang MLOps engineer."],
      ["agent", "AGT", "Đã cập nhật nghề nghiệp hiện tại."]
    ],
    profile: `<span class="md-h"># User Profile</span>

<span class="md-h">## Facts</span>
- <span class="md-key">name:</span> <span class="md-value">DũngCT</span>
- <span class="md-key">location:</span> <span class="md-value">Đà Nẵng</span>
- <span class="md-key">profession:</span> <span class="md-old">backend engineer</span>
  <span class="md-value">→ MLOps engineer</span>`,
    event: "Conflict resolved: profession replaced"
  },
  {
    thread: "THREAD_B / NEW",
    messages: [
      ["system", "SYS", "Fresh thread created. Short-term history is empty."],
      ["system", "MEM", "User.md loaded: 3 persistent facts available."]
    ],
    profile: `<span class="md-h"># User Profile</span>

<span class="md-h">## Facts</span>
- <span class="md-key">name:</span> <span class="md-value">DũngCT</span>
- <span class="md-key">location:</span> <span class="md-value">Đà Nẵng</span>
- <span class="md-key">profession:</span> <span class="md-value">MLOps engineer</span>`,
    event: "Profile injected into new thread"
  },
  {
    thread: "THREAD_B / NEW",
    messages: [
      ["user", "USR", "Hiện tại mình làm nghề gì và đang ở đâu?"],
      ["agent", "AGT", "Bạn hiện là MLOps engineer và đang ở Đà Nẵng."]
    ],
    profile: `<span class="md-h"># User Profile</span>

<span class="md-h">## Facts</span>
- <span class="md-key">name:</span> <span class="md-value">DũngCT</span>
- <span class="md-key">location:</span> <span class="md-value">Đà Nẵng</span>
- <span class="md-key">profession:</span> <span class="md-value">MLOps engineer</span>`,
    event: "Cross-session recall succeeded"
  }
];

let currentDemoStep = -1;
function renderDemoStep(index, reset = false) {
  if (reset) {
    $("#demoMessages").innerHTML = '<div class="message system"><span>SYS</span><p>Agent initialized. No persistent facts yet.</p></div>';
    $("#eventLog").innerHTML = "<p><i></i> Profile store ready</p>";
  }
  const step = demoSteps[index];
  $("#threadLabel").textContent = step.thread;
  step.messages.forEach(([type, label, text]) => {
    const message = document.createElement("div");
    message.className = `message ${type}`;
    message.innerHTML = `<span>${label}</span><p>${text}</p>`;
    $("#demoMessages").appendChild(message);
  });
  $("#demoMessages").scrollTop = $("#demoMessages").scrollHeight;
  $("#profileContent").innerHTML = `<code>${step.profile}</code>`;
  $("#eventLog").insertAdjacentHTML("beforeend", `<p><i></i> ${step.event}</p>`);
  $$(".demo-step").forEach((button, buttonIndex) => button.classList.toggle("active", buttonIndex === index));
  currentDemoStep = index;
}
$$(".demo-step").forEach(button => button.addEventListener("click", () => {
  const target = Number(button.dataset.step);
  if (target <= currentDemoStep) {
    renderDemoStep(target, true);
  } else {
    for (let index = currentDemoStep + 1; index <= target; index++) renderDemoStep(index, index === 0 && currentDemoStep < 0);
  }
}));
$("#resetDemo").addEventListener("click", () => {
  currentDemoStep = -1;
  $("#threadLabel").textContent = "THREAD_A";
  $("#demoMessages").innerHTML = '<div class="message system"><span>SYS</span><p>Agent initialized. No persistent facts yet.</p></div>';
  $("#profileContent").innerHTML = '<code><span class="md-h"># User Profile</span>\n\n<span class="md-h">## Facts</span>\n<span class="md-comment"># Waiting for stable facts...</span></code>';
  $("#eventLog").innerHTML = "<p><i></i> Profile store ready</p>";
  $$(".demo-step").forEach((button, index) => button.classList.toggle("active", index === 0));
});

const sections = $$(".section");
let presentationMode = false;
function updateSlideCount() {
  const viewportMiddle = window.scrollY + window.innerHeight / 2;
  let active = 0;
  sections.forEach((section, index) => {
    if (section.offsetTop <= viewportMiddle) active = index;
  });
  $("#slideCount").textContent = `${String(active + 1).padStart(2, "0")} / ${String(sections.length).padStart(2, "0")}`;
}
function togglePresentation(force) {
  presentationMode = typeof force === "boolean" ? force : !presentationMode;
  document.body.classList.toggle("presentation", presentationMode);
  if (presentationMode && document.documentElement.requestFullscreen) document.documentElement.requestFullscreen().catch(() => {});
  if (!presentationMode && document.fullscreenElement) document.exitFullscreen().catch(() => {});
  updateSlideCount();
}
$("#presentBtn").addEventListener("click", () => togglePresentation());
document.addEventListener("keydown", event => {
  if (event.key === "Escape" && presentationMode) togglePresentation(false);
  if (!presentationMode || !["ArrowDown", "ArrowUp", "PageDown", "PageUp"].includes(event.key)) return;
  event.preventDefault();
  const middle = window.scrollY + window.innerHeight / 2;
  let current = sections.findIndex(section => section.offsetTop + section.offsetHeight > middle);
  current = Math.max(0, current);
  const direction = ["ArrowDown", "PageDown"].includes(event.key) ? 1 : -1;
  sections[Math.min(sections.length - 1, Math.max(0, current + direction))].scrollIntoView({ behavior: "smooth" });
});
window.addEventListener("scroll", updateSlideCount, { passive: true });
$("#topBtn").addEventListener("click", () => window.scrollTo({ top: 0, behavior: "smooth" }));

const benchmarkSection = $("#benchmark");
const chartObserver = new IntersectionObserver(entries => {
  if (entries[0].isIntersecting) {
    animateChart();
    chartObserver.disconnect();
  }
}, { threshold: .25 });
chartObserver.observe(benchmarkSection);

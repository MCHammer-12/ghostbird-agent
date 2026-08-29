const $ = (selector, parent = document) => parent.querySelector(selector);
const $$ = (selector, parent = document) => [...parent.querySelectorAll(selector)];

const evidence = {
  meridian: {
    title: "The reliable lead-time promise",
    source: "Vance & Kinder × Ghostbird Content Interview",
    meta: "Jul 9, 2026 · Marisol Vance · 02:07–02:28",
    before: "Their procurement guy called us because he remembered we talked a lot about lead times at a trade show the year before.",
    quote: "“We can’t always win on price. Steel’s steel, but we can win on your stuff shows up when we say it will.”",
    after: "We’re up about forty percent year over year. Which is wild because I keep waiting for it to slow down.",
    tags: ["Client story", "Reliable lead times", "Voice cue"],
  },
  erp: {
    title: "Transparency before it becomes a problem",
    source: "Vance & Kinder × Ghostbird Content Interview",
    meta: "Aug 20, 2026 · Marisol Vance · 01:20–02:13",
    before: "We had a two-day window where the new system and old system were both half working, and we almost shipped an order to the wrong facility.",
    quote: "“Instead of pretending it was seamless, I sent an email to our top accounts saying there might be a hiccup or two this month — here’s who to call directly if anything looks off.”",
    after: "Two different customers wrote back just saying thanks for the heads up. One said most vendors would never admit something like that.",
    tags: ["Client story", "Transparency", "Leadership"],
  },
  growth: {
    title: "40% year-over-year growth",
    source: "Vance & Kinder × Ghostbird Content Interview",
    meta: "Jul 9, 2026 · Marisol Vance · 02:42–03:15",
    before: "It wasn’t even a sales pitch that won Meridian. It was being memorable a year earlier.",
    quote: "“We’re up about forty percent year over year. Which is wild because I keep waiting for it to slow down and it just hasn’t.”",
    after: "We hired three new people this quarter: two in the warehouse, and one inside-sales rep.",
    tags: ["Metric", "Growth", "Team"],
  },
  dad: {
    title: "Bad news doesn’t get better with age",
    source: "Vance & Kinder × Ghostbird Content Interview",
    meta: "Aug 20, 2026 · Marisol Vance · 02:28–02:43",
    before: "Customers responded better than Marisol expected after she warned them about the system transition.",
    quote: "“My dad actually used to say something like bad news doesn’t get better with age, and I finally understood what he meant by that.”",
    after: "She had the same instinct when explaining an eight percent price increase to customers.",
    tags: ["Quote", "Family business", "Voice cue"],
  },
  feedback: {
    title: "Use the exact detail",
    source: "Re: Drafts from July content call",
    meta: "Jul 11, 2026 · Marisol Vance · Client feedback email",
    before: "Marisol reviewed three drafts from the July content interview.",
    quote: "“On the Meridian post, can we say ‘nine years with their previous supplier’ instead of just ‘a decade’ — nine is the actual number and it’s a better detail anyway.”",
    after: "She approved the dad story and asked to hold the half-marathon post until a finish-line photo was available.",
    tags: ["Client feedback", "Exact details", "Voice cue"],
    kind: "email",
  },
  succession: {
    title: "Can you put your dad on the phone?",
    source: "Vance & Kinder × Ghostbird Content Interview",
    meta: "Jul 9, 2026 · Marisol Vance · 04:13–05:48",
    before: "A Big Sky Fabrication customer who had worked with Marisol’s father since 1994 called without knowing she had taken over.",
    quote: "“And I said, this is Marisol, I run the company now, how can I help? And he just goes quiet for a second and then says well, can you put your dad on the phone.”",
    after: "Marisol handled the order. The customer later became a top-twenty account and referred two other fabrication shops.",
    tags: ["Client story", "Family business", "Leadership"],
  },
  colton: {
    title: "Colton’s first $4,000 close",
    source: "Vance & Kinder × Ghostbird Content Interview",
    meta: "Jul 9, 2026 · Marisol Vance · 06:01–06:51",
    before: "Colton was new to sales and still learning the product line.",
    quote: "“I still remember my first sale after I took over, and it was smaller than his. Everybody starts small.”",
    after: "Marisol saw the moment as a reminder that owners need to say this out loud to new people.",
    tags: ["Client story", "Mentoring", "$4,000 sale"],
  },
  pricing: {
    title: "The transparent 8% price increase",
    source: "Vance & Kinder × Ghostbird Content Interview",
    meta: "Aug 20, 2026 · Marisol Vance · 02:54–03:45",
    before: "Steel tariffs forced Vance & Kinder to raise prices by eight percent.",
    quote: "“I sent a short letter explaining exactly why, showed the actual cost increase we were absorbing, and didn’t try to hide behind vague language like market conditions.”",
    after: "One small account left, while larger customers thanked the company for being upfront.",
    tags: ["Client story", "8% price increase", "Transparency"],
  },
  marathon: {
    title: "Hold the half-marathon post",
    source: "Re: Drafts from July content call",
    meta: "Jul 11, 2026 · Marisol Vance · Client feedback email",
    before: "Marisol had discussed turning her half-marathon into a personal post.",
    quote: "“Let’s hold the marathon post like we talked about, I still don’t have a finish line photo yet.”",
    after: "The agency held the idea until the real visual was available.",
    tags: ["Client feedback", "Visual asset", "Editorial timing"],
    kind: "email",
  },
};

const clients = {
  vance_kinder: {
    name: "Marisol Vance",
    firstName: "Marisol",
    company: "Vance & Kinder",
    initials: "MV",
    pronoun: "her.",
    sourceCount: 4,
    voice: `# Marisol Vance — voice profile

## The feeling
Practical, candid, and quietly proud. Marisol tells stories like she is talking across a desk — never performing expertise, but clearly the person who has done the work.

## What to lean into
- Specific details over abstractions: *nine years*, *two missed ship dates*, *a $4,000 first sale*.
- Plainspoken leadership lessons earned from an actual moment.
- Her family-business perspective, without making every post sentimental.
- A little dry humor when it naturally belongs.

## How she sounds
Short to medium sentences. Conversational openers. She will say “honestly,” “kind of,” or “basically,” but the published post can be a little cleaner than her spoken voice.

## Avoid
- Generic motivational language.
- Big, polished claims about disruption or innovation.
- Making a lesson sound too neat. Let the mess stay visible.

## Evidence notes
Her edits favor exact details over round numbers. She explicitly preferred “nine years with their previous supplier” to “a decade.”`,
  },
  bloom_bar: {
    name: "Priya Chandrasekhar",
    firstName: "Priya",
    company: "Bloom & Bar",
    initials: "PC",
    pronoun: "her.",
    sourceCount: 0,
    voice: "# Priya Chandrasekhar — voice profile\n\nAdd approved client material to begin an evidence-backed profile.\n\n## Notes for review\n- Keep writing guidance traceable to approved sources.\n- Separate spoken voice from published LinkedIn style.",
  },
  ridgeline: {
    name: "Desmond Okafor",
    firstName: "Desmond",
    company: "Ridgeline",
    initials: "DO",
    pronoun: "him.",
    sourceCount: 0,
    voice: "# Desmond Okafor — voice profile\n\nAdd approved client material to begin an evidence-backed profile.\n\n## Notes for review\n- Keep writing guidance traceable to approved sources.\n- Separate spoken voice from published LinkedIn style.",
  },
};

const clientButton = $("#clientButton");
const clientMenu = $("#clientMenu");
clientButton.addEventListener("click", () => {
  const open = clientMenu.hidden;
  clientMenu.hidden = !open;
  clientButton.setAttribute("aria-expanded", String(open));
});
document.addEventListener("click", (event) => {
  if (!event.target.closest(".client-switcher")) {
    clientMenu.hidden = true;
    clientButton.setAttribute("aria-expanded", "false");
  }
});

let activeClient = "vance_kinder";
let outputsVisible = false;
function isPreparedClient() {
  return activeClient === "vance_kinder";
}
function syncWorkspaceOutputs() {
  const visible = isPreparedClient() && outputsVisible;
  $("#resultsSection").hidden = !visible;
  $(".draft-section").hidden = !visible;
}
function selectClient(clientId) {
  if (!clients[clientId]) return;
  draftsByClient[activeClient][activeMode] = $("#writingPrompt").value;
  voiceProfiles[activeClient] = $(".markdown-editor textarea").value;
  activeClient = clientId;
  const client = clients[clientId];
  $(".client-initials").textContent = client.initials;
  $("#selectedClientName").textContent = client.name;
  $("#selectedClientCompany").textContent = client.company;
  $("#clientPronoun").textContent = client.pronoun;
  $("#sourceClientName").textContent = `${client.firstName}.`;
  $("#voiceClientName").textContent = client.firstName;
  $$('[data-client-first-name]').forEach((element) => { element.textContent = client.firstName; });
  $("#sourceTotal").textContent = String(client.sourceCount);
  $("#sourceNavCount").textContent = String(client.sourceCount);
  $(".markdown-editor textarea").value = voiceProfiles[clientId] || client.voice;
  $$(".client-option").forEach((option) => option.classList.toggle("active", option.dataset.client === clientId));
  $$("[data-marisol-context]").forEach((section) => {
    if (section.id !== "resultsSection" && !section.classList.contains("draft-section")) {
      section.hidden = !isPreparedClient();
    }
  });
  $("#emptyWorkspaceContext").hidden = isPreparedClient();
  $("#emptySourceContext").hidden = isPreparedClient();
  $("#writingPrompt").value = draftsByClient[clientId][activeMode];
  syncWorkspaceOutputs();
  clientMenu.hidden = true;
  clientButton.setAttribute("aria-expanded", "false");
}
$$('.client-option').forEach((option) => option.addEventListener('click', () => selectClient(option.dataset.client)));

$$('.nav-item').forEach((button) => button.addEventListener('click', () => {
  $$('.nav-item').forEach((item) => item.classList.toggle('active', item === button));
  $$('.view').forEach((view) => view.classList.remove('active'));
  $(`#${button.dataset.view}View`).classList.add('active');
  window.scrollTo({ top: 0, behavior: 'smooth' });
}));

const modes = {
  enrich: {
    eyebrow: 'Start with a draft',
    title: 'Paste in what you have.',
    prompt: 'The best customer relationships aren’t built when everything goes right.\n\nThey’re built in the moments when you have to tell someone something they don’t want to hear.',
    hint: 'Ghostbird will surface proof and voice cues that fit this draft.',
    label: 'Enrich this post',
    outputEyebrow: 'Grounded draft',
    outputTitle: 'What client context changes',
  },
  create: {
    eyebrow: 'Start with an idea',
    title: 'What should we brainstorm?',
    prompt: 'An honest post about leading through an operational change — for owners who feel pressure to make every transition look seamless.',
    hint: 'Ghostbird will return 10 distinct directions grounded in client context.',
    label: 'Brainstorm 10 ideas',
    outputEyebrow: 'Idea brainstorm',
    outputTitle: '10 directions to explore',
  },
};
let activeMode = 'enrich';
const draftsByClient = Object.fromEntries(Object.keys(clients).map((clientId) => [
  clientId,
  {
    enrich: clientId === 'vance_kinder' ? modes.enrich.prompt : '',
    create: clientId === 'vance_kinder' ? modes.create.prompt : '',
  },
]));
const voiceProfiles = Object.fromEntries(Object.entries(clients).map(([clientId, client]) => [clientId, client.voice]));

function selectMode(nextMode) {
  draftsByClient[activeClient][activeMode] = $('#writingPrompt').value;
  activeMode = nextMode;
  outputsVisible = false;
  const mode = modes[nextMode];
  const button = $(`.mode[data-mode="${nextMode}"]`);
  $$('.mode').forEach((item) => {
    const active = item === button;
    item.classList.toggle('active', active);
    item.setAttribute('aria-pressed', String(active));
  });
  $('#composerEyebrow').textContent = mode.eyebrow;
  $('#composerTitle').textContent = mode.title;
  $('#writingPrompt').value = draftsByClient[activeClient][nextMode];
  $('#composerHint').textContent = mode.hint;
  $('#generateLabel').textContent = mode.label;
  $('#outputEyebrow').textContent = mode.outputEyebrow;
  $('#outputTitle').textContent = mode.outputTitle;
  $$('[data-mode-output]').forEach((output) => {
    output.hidden = output.dataset.modeOutput !== nextMode;
  });
  syncWorkspaceOutputs();
}
$$('.mode').forEach((button) => button.addEventListener('click', () => selectMode(button.dataset.mode)));

$('#generateButton').addEventListener('click', () => {
  outputsVisible = true;
  syncWorkspaceOutputs();
  $('#resultsSection').scrollIntoView({ behavior: 'smooth', block: 'start' });
  showToast(activeMode === 'enrich' ? 'Your post is ready to enrich' : '10 ideas are ready to explore');
});

let returnFocus;
function focusableElements(element) {
  return $$('button:not([disabled]), [href], input, select, textarea, [tabindex]:not([tabindex="-1"])', element)
    .filter((node) => !node.hidden && getComputedStyle(node).visibility !== 'hidden');
}
function showOverlay(element, trigger) {
  if (trigger) returnFocus = trigger;
  if (element.classList.contains('evidence-drawer')) {
    element.classList.add('open');
    element.removeAttribute('inert');
    element.setAttribute('aria-hidden', 'false');
    $('#drawerScrim').hidden = false;
  } else {
    element.hidden = false;
  }
  $('.app-shell').inert = true;
  window.setTimeout(() => (
    focusableElements(element)[0] || element.querySelector('[tabindex="-1"]') || element
  ).focus(), 0);
}
function hideOverlay(element, restoreFocus = true) {
  if (element.classList.contains('evidence-drawer')) {
    element.classList.remove('open');
    element.setAttribute('inert', '');
    element.setAttribute('aria-hidden', 'true');
    $('#drawerScrim').hidden = true;
  } else {
    element.hidden = true;
  }
  $('.app-shell').inert = false;
  if (restoreFocus) returnFocus?.focus();
}
document.addEventListener('keydown', (event) => {
  const overlay = $('.modal-backdrop:not([hidden])') || $('.evidence-drawer.open');
  if (!overlay) return;
  if (event.key === 'Escape') {
    event.preventDefault();
    hideOverlay(overlay);
    return;
  }
  if (event.key !== 'Tab') return;
  const items = focusableElements(overlay);
  const first = items[0];
  const last = items.at(-1);
  if (!first || !last) return;
  if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
  if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
});

function openDrawer(key, trigger) {
  const item = evidence[key];
  if (!item) return;
  $('#drawerTitle').textContent = item.title;
  $('#drawerSource').textContent = item.source;
  $('#drawerMeta').textContent = item.meta;
  $('#drawerBefore').textContent = item.before;
  $('#drawerQuote').textContent = item.quote;
  $('#drawerAfter').textContent = item.after;
  $('.drawer-tags').innerHTML = item.tags.map((tag) => `<span>${tag}</span>`).join('');
  $('#drawerSourceType').textContent = item.kind === 'email' ? '✉' : '⌁';
  $('#drawerSourceType').className = `source-type ${item.kind === 'email' ? 'email' : 'transcript'}`;
  showOverlay($('#evidenceDrawer'), trigger);
}
$$('[data-evidence]').forEach((button) => button.addEventListener('click', () => openDrawer(button.dataset.evidence, button)));
function closeDrawer() {
  hideOverlay($('#evidenceDrawer'));
}
$('#closeDrawer').addEventListener('click', closeDrawer);
$('#drawerScrim').addEventListener('click', closeDrawer);

const uploadModal = $('#uploadModal');
function openUpload(trigger) { showOverlay(uploadModal, trigger); }
function closeUpload() { hideOverlay(uploadModal); }
$('#openUpload').addEventListener('click', (event) => openUpload(event.currentTarget));
$('#sourceUploadButton').addEventListener('click', (event) => openUpload(event.currentTarget));
$$('.empty-upload').forEach((button) => button.addEventListener('click', (event) => openUpload(event.currentTarget)));
$('#closeUpload').addEventListener('click', closeUpload);

$('#prepareSource').addEventListener('click', () => {
  hideOverlay(uploadModal, false);
  const statusModal = $('#statusModal');
  $('#statusTitle').textContent = 'Making this useful';
  $('#statusCopy').textContent = 'Reading the source, finding moments that matter, and adding it to this client’s private context.';
  $('#statusStep').textContent = '○ Extract usable details';
  $('#statusStep').classList.remove('complete');
  $('.process-steps').lastElementChild.textContent = '○ Ready for writing';
  $('.process-steps').lastElementChild.classList.remove('complete');
  $('#closeStatus').hidden = true;
  showOverlay(statusModal);
  setTimeout(() => {
    $('#statusTitle').textContent = 'Source is ready';
    $('#statusCopy').textContent = `We found useful details and added this source to ${clients[activeClient].firstName}’s private writing context.`;
    $('#statusStep').textContent = '✓ Extract usable details';
    $('#statusStep').classList.add('complete');
    $('.process-steps').lastElementChild.textContent = '✓ Ready for writing';
    $('.process-steps').lastElementChild.classList.add('complete');
    $('#closeStatus').hidden = false;
  }, 1500);
});
$('#closeStatus').addEventListener('click', () => { hideOverlay($('#statusModal')); });

$('#saveProfile').addEventListener('click', () => showToast('Voice profile saved'));
function showToast(message) {
  const toast = $('#toast');
  toast.textContent = message;
  toast.hidden = false;
  window.clearTimeout(showToast.timer);
  showToast.timer = window.setTimeout(() => { toast.hidden = true; }, 2500);
}

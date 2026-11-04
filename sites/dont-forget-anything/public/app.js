const GearCheck = (() => {
const STORAGE_KEY = "fishingGearCheck.lists.v1";
const CHECKS_KEY = "fishingGearCheck.checks.v1";
const ACTIVE_KEY = "fishingGearCheck.activeList.v1";
const BACKUP_VERSION = 1;
const SHARE_API_URL = "https://cutlassfish.tokyo/dont-forget-anything-share/share.php";
const SHARE_APP_URL = "https://dont-forget-anything.cutlassfish.tokyo/";
let deferredInstallPrompt = null;
let handledShareId = "";
window.addEventListener("beforeinstallprompt", event => {
event.preventDefault();
deferredInstallPrompt = event;
updateInstallGuide();
});
const defaultLists = [
{
id: "tenya-tachiuo",
name: "テンヤタチウオ用",
sections: [
defaultSection("must", "絶対いるもの", [
"竿", "リール", "テンヤ", "簡易竿掛け+尻手ロープ", "糸一式", "スナップスイベル",
"ハサミ等一式", "餌", "ドリンクマグ", "サングラス", "帽子", "ライフジャケット",
"着替え", "タオル", "ウェットティッシュ", "ビニール袋（魚用）", "ビニール袋（ゴミなど用）",
"魚用クーラーボックス", "ラテックス手袋（指サック）", "財布", "免許（カード）",
"自宅の鍵", "モバイルバッテリー", "IQOS"
]),
defaultSection("season", "季節限定", [
"長靴", "電熱ベスト", "ビブ", "ホッカイロ（貼る+靴用）", "日焼け止め",
"ネックウォーマー", "エアコン服", "空調服"
]),
defaultSection("optional", "必要時", [
"テンヤ用クーラー", "ロッドホルダー", "ロッドホルダー（竿側）", "餌入れ", "探見丸",
"探見丸用マウント", "探見丸用バッテリー+コード", "GoPro", "GoPro用マウント+尻手ロープ",
"ギンバル", "電動バッテリー", "電動コード"
])
]
},
{
id: "nomase",
name: "泳がせ用",
sections: [
defaultSection("must", "絶対いるもの", [
"竿", "リール", "仕掛け", "錘・カゴ", "天秤", "ロッドホルダー",
"ロッドホルダー（竿側）", "尻手ロープ", "簡易竿掛け+尻手ロープ", "電動バッテリー",
"電動コード", "針、糸", "スナップスイベル", "ハサミ等一式", "餌", "ドリンクマグ",
"サングラス", "帽子", "ライフジャケット", "着替え", "タオル", "ウェットティッシュ",
"ビニール袋（魚用）", "ビニール袋（ゴミなど用）", "魚用クーラーボックス",
"ラテックス手袋（指サック）", "財布", "免許（カード）", "自宅の鍵",
"モバイルバッテリー", "IQOS"
]),
defaultSection("season", "季節限定", [
"長靴", "電熱ベスト", "ビブ", "ホッカイロ（貼る+靴用）", "日焼け止め",
"ネックウォーマー", "エアコン服", "空調服"
]),
defaultSection("optional", "必要時", [
"餌入れ", "探見丸", "探見丸用マウント", "探見丸用バッテリー+コード", "GoPro",
"GoPro用マウント+尻手ロープ", "ギンバル", "ザル"
])
]
},
{
id: "expedition",
name: "遠征用",
sections: [
defaultSection("must", "絶対いるもの", [
"竿", "リール", "泳がせ仕掛け", "錘・カゴ", "ムロ仕掛け", "ムロ外し", "天秤",
"ロッドホルダー", "ロッドホルダー（竿側）", "尻手ロープ", "簡易竿掛け+尻手ロープ",
"電動バッテリー", "電動コード", "針、糸", "スナップスイベル", "ハサミ等一式",
"餌", "ドリンクマグ", "サングラス", "帽子", "ライフジャケット", "着替え",
"タオル", "ウェットティッシュ", "ビニール袋（魚用）", "ビニール袋（ゴミなど用）",
"魚用クーラーボックス", "ラテックス手袋（指サック）", "財布", "免許（カード）",
"自宅の鍵", "モバイルバッテリー", "IQOS"
]),
defaultSection("season", "季節限定", [
"長靴", "電熱ベスト", "ビブ", "ホッカイロ（貼る+靴用）", "日焼け止め",
"ネックウォーマー", "エアコン服", "空調服"
]),
defaultSection("optional", "必要時", [
"餌入れ", "探見丸", "探見丸用マウント", "探見丸用バッテリー+コード", "GoPro",
"GoPro用マウント+尻手ロープ", "ギンバル", "ザル"
])
]
}
];
let lists = normalizeLists(loadJson(STORAGE_KEY, defaultLists));
let checks = loadJson(CHECKS_KEY, {});
let activeListId = localStorage.getItem(ACTIVE_KEY) || lists[0]?.id || "tenya-tachiuo";
migrateLegacyDefaultLists();
function renderChecklistPage() {
const els = {
activeListName: document.getElementById("activeListName"),
activeListNote: document.getElementById("activeListNote"),
doneCount: document.getElementById("doneCount"),
csvRestoreInput: document.getElementById("csvRestoreInput"),
defaultGuide: document.getElementById("defaultGuide"),
exportChecklistCsvButton: document.getElementById("exportChecklistCsvButton"),
exportChecklistJsonButton: document.getElementById("exportChecklistJsonButton"),
installGuide: document.getElementById("installGuide"),
installGuideButton: document.getElementById("installGuideButton"),
jsonRestoreInput: document.getElementById("jsonRestoreInput"),
listTabs: document.getElementById("listTabs"),
progressBar: document.getElementById("progressBar"),
resetChecksButton: document.getElementById("resetChecksButton"),
sections: document.getElementById("sections"),
totalCount: document.getElementById("totalCount")
};
els.resetChecksButton.addEventListener("click", () => {
const list = getActiveList();
checks[list.id] = {};
persist();
trackEvent("checklist_reset", { list_id: list.id });
toast("チェックを全部外しました");
render();
});
els.exportChecklistJsonButton.addEventListener("click", exportJsonBackup);
els.exportChecklistCsvButton.addEventListener("click", exportCsvBackup);
els.installGuideButton.addEventListener("click", openInstallGuide);
els.jsonRestoreInput.addEventListener("change", event => {
const file = event.target.files?.[0];
event.target.value = "";
if (!file) return;
importBackup(file, render);
});
els.csvRestoreInput.addEventListener("change", event => {
const file = event.target.files?.[0];
event.target.value = "";
if (!file) return;
importCsvBackup(file, render);
});
function render() {
ensureLists();
const list = getActiveList();
els.activeListName.textContent = list.name;
renderListNote(els.activeListNote, list);
renderOtherTabs(els.listTabs, list.id, nextId => {
activeListId = nextId;
persist();
trackEvent("list_select", { list_id: nextId, surface: "checklist" });
render();
});
renderSections(els.sections, list);
updateProgress(els, list);
updateDefaultGuide(els);
updateInstallGuide(els);
}
render();
importSharedListFromUrl(render);
registerServiceWorker();
}
function renderEditPage() {
const els = {
addSectionButton: document.getElementById("addSectionButton"),
deleteListButton: document.getElementById("deleteListButton"),
duplicateListButton: document.getElementById("duplicateListButton"),
editList: document.getElementById("editList"),
editListTabs: document.getElementById("editListTabs"),
editingListName: document.getElementById("editingListName"),
exportBackupButton: document.getElementById("exportBackupButton"),
importBackupInput: document.getElementById("importBackupInput"),
importShareButton: document.getElementById("importShareButton"),
listNameInput: document.getElementById("listNameInput"),
listNoteInput: document.getElementById("listNoteInput"),
newListButton: document.getElementById("newListButton"),
saveListNameButton: document.getElementById("saveListNameButton"),
shareListButton: document.getElementById("shareListButton"),
shareImportInput: document.getElementById("shareImportInput"),
shareUrlInput: document.getElementById("shareUrlInput"),
copyShareUrlButton: document.getElementById("copyShareUrlButton")
};
els.saveListNameButton.addEventListener("click", () => {
const list = getActiveList();
const name = els.listNameInput.value.trim();
if (!name) {
toast("リスト名を入力してください");
return;
}
list.name = name;
list.note = els.listNoteInput.value.trim();
persist();
trackEvent("list_save", { has_note: Boolean(list.note), list_id: list.id });
toast("リスト名とメモを保存しました");
render();
});
els.duplicateListButton.addEventListener("click", () => {
const source = getActiveList();
const copy = structuredClone(source);
copy.id = uid("list");
copy.name = `${source.name} コピー`;
copy.sections.forEach(section => {
section.id = uid("section");
section.items.forEach(item => item.id = uid("item"));
});
lists.push(copy);
activeListId = copy.id;
persist();
trackEvent("list_duplicate", { list_id: copy.id, source_list_id: source.id });
toast("リストを複製しました");
render();
});
els.newListButton.addEventListener("click", () => {
createNewList();
render();
});
els.deleteListButton.addEventListener("click", () => {
if (lists.length <= 1) {
toast("最後のリストは削除できません");
return;
}
const list = getActiveList();
if (!confirm(`「${list.name}」を削除しますか？`)) return;
lists = lists.filter(entry => entry.id !== list.id);
delete checks[list.id];
activeListId = lists[0].id;
persist();
trackEvent("list_delete", { list_id: list.id });
render();
});
els.addSectionButton.addEventListener("click", () => {
const title = prompt("カテゴリ名", "必要時");
if (!title?.trim()) return;
getActiveList().sections.push({ id: uid("section"), title: title.trim(), countInProgress: true, items: [] });
persist();
trackEvent("section_create", { list_id: getActiveList().id });
render();
});
els.exportBackupButton.addEventListener("click", exportJsonBackup);
els.shareListButton.addEventListener("click", () => createShareUrl(els));
els.copyShareUrlButton.addEventListener("click", () => copyText(els.shareUrlInput.value, els.shareUrlInput));
els.importShareButton.addEventListener("click", () => importSharedListFromInput(els, render));
els.shareImportInput.addEventListener("keydown", event => {
if (event.key === "Enter") importSharedListFromInput(els, render);
});
els.importBackupInput.addEventListener("change", event => {
const file = event.target.files?.[0];
event.target.value = "";
if (!file) return;
importBackup(file, render);
});
function render() {
ensureLists();
const list = getActiveList();
els.editingListName.textContent = list.name;
els.listNameInput.value = list.name;
els.listNoteInput.value = list.note || "";
els.shareUrlInput.value = "";
els.shareUrlInput.hidden = true;
els.copyShareUrlButton.hidden = true;
renderTabs(els.editListTabs, list.id, nextId => {
activeListId = nextId;
persist();
trackEvent("list_select", { list_id: nextId, surface: "editor" });
render();
});
renderEditor(els.editList, list, render);
}
render();
importSharedListFromUrl(render);
registerServiceWorker();
}
function renderListNote(container, list) {
if (!container) return;
const note = String(list.note || "").trim();
container.hidden = !note;
container.textContent = note;
}
function isStandaloneApp() {
return window.matchMedia("(display-mode: standalone)").matches ||
window.matchMedia("(display-mode: fullscreen)").matches ||
window.navigator.standalone === true;
}
function updateInstallGuide(els = {}) {
const guide = els.installGuide || document.getElementById("installGuide");
const button = els.installGuideButton || document.getElementById("installGuideButton");
if (!guide || !button) return;
guide.hidden = isStandaloneApp();
button.textContent = deferredInstallPrompt ? "アプリとして追加" : "共有メニューを開く";
}
async function openInstallGuide() {
if (deferredInstallPrompt) {
const promptEvent = deferredInstallPrompt;
deferredInstallPrompt = null;
promptEvent.prompt();
await promptEvent.userChoice.catch(() => null);
updateInstallGuide();
return;
}
if (navigator.share) {
try {
await navigator.share({
title: document.title,
text: "忘れ物チェックをホーム画面に追加して使う",
url: location.href
});
return;
} catch (error) {
if (error?.name === "AbortError") return;
}
}
toast("iPhoneはSafariの共有ボタンから「ホーム画面に追加」を選んでください。AndroidはChromeのメニューから追加できます。");
}
async function createShareUrl(els) {
const list = getActiveList();
if (!list) return;
setShareControlsLoading(els, true);
try {
const response = await fetch(SHARE_API_URL, {
method: "POST",
headers: { "Content-Type": "application/json" },
body: JSON.stringify({
app: "fishingGearCheck",
version: BACKUP_VERSION,
list: serializeSharedList(list)
})
});
const result = await response.json().catch(() => ({}));
if (!response.ok || !result.id) throw new Error(result.error || "share_failed");
const shareUrl = buildShareUrl(result.id);
els.shareUrlInput.value = shareUrl;
els.shareUrlInput.hidden = false;
els.copyShareUrlButton.hidden = false;
trackEvent("list_share_create", { list_id: list.id });
await copyText(shareUrl, els.shareUrlInput);
} catch {
toast("共有URLを作成できませんでした");
} finally {
setShareControlsLoading(els, false);
}
}
function setShareControlsLoading(els, loading) {
if (!els.shareListButton) return;
els.shareListButton.disabled = loading;
els.shareListButton.textContent = loading ? "共有URLを作成中..." : "このリストを共有";
}
async function copyText(value, sourceInput) {
if (!value) return;
try {
await navigator.clipboard.writeText(value);
toast("共有URLをコピーしました");
} catch {
if (copyTextFallback(value, sourceInput)) {
toast("共有URLをコピーしました");
} else {
if (sourceInput) {
sourceInput.focus();
sourceInput.select();
sourceInput.setSelectionRange(0, sourceInput.value.length);
}
toast("共有URLを表示しました");
}
}
}
function copyTextFallback(value, sourceInput) {
const input = sourceInput || document.createElement("textarea");
const temporary = !sourceInput;
if (temporary) {
input.value = value;
input.setAttribute("readonly", "");
input.style.position = "fixed";
input.style.left = "-9999px";
document.body.appendChild(input);
} else {
input.value = value;
}
input.focus();
input.select();
input.setSelectionRange(0, input.value.length);
try {
return document.execCommand("copy");
} catch {
return false;
} finally {
if (temporary) input.remove();
}
}
function buildShareUrl(id) {
const url = new URL(SHARE_APP_URL);
url.searchParams.set("share", id);
return url.toString();
}
function serializeSharedList(list) {
return {
name: list.name,
note: list.note || "",
sections: list.sections.map(section => ({
title: section.title,
countInProgress: isSectionCounted(section),
items: section.items.map(item => item.label)
}))
};
}
async function importSharedListFromUrl(refresh) {
const shareId = new URLSearchParams(location.search).get("share");
if (!shareId || shareId === handledShareId) return;
handledShareId = shareId;
await importSharedListById(shareId, refresh);
}
async function importSharedListFromInput(els, refresh) {
const shareId = extractShareId(els.shareImportInput.value);
if (!shareId) {
toast("共有URLを貼り付けてください");
return;
}
els.importShareButton.disabled = true;
els.importShareButton.textContent = "取り込み中...";
try {
const imported = await importSharedListById(shareId, refresh, { clearUrl: false });
if (imported) els.shareImportInput.value = "";
} finally {
els.importShareButton.disabled = false;
els.importShareButton.textContent = "取り込む";
}
}
async function importSharedListById(shareId, refresh, options = {}) {
try {
const response = await fetch(`${SHARE_API_URL}?id=${encodeURIComponent(shareId)}`);
const payload = await response.json().catch(() => ({}));
if (!response.ok || !payload.list) throw new Error(payload.error || "share_not_found");
const list = createListFromSharedPayload(payload.list);
if (!confirm(`共有リスト「${list.name}」をこの端末に追加しますか？`)) {
if (options.clearUrl !== false) clearShareParam();
return false;
}
if (isDefaultListSetup()) {
lists = [list];
checks = {};
} else {
lists.push(list);
}
activeListId = list.id;
persist();
if (options.clearUrl !== false) clearShareParam();
trackEvent("list_share_import", { share_id: shareId });
toast("共有リストを追加しました");
refresh();
return true;
} catch {
toast("共有リストを読み込めませんでした");
return false;
}
}
function extractShareId(value) {
const text = String(value || "").trim();
if (!text) return "";
try {
const url = new URL(text);
return normalizeShareId(url.searchParams.get("share"));
} catch {
return normalizeShareId(text);
}
}
function normalizeShareId(value) {
const text = String(value || "").trim();
return /^[a-zA-Z0-9_-]{10,32}$/.test(text) ? text : "";
}
function createListFromSharedPayload(sharedList) {
const normalized = normalizeLists([{
name: `${String(sharedList.name || "共有リスト").trim() || "共有リスト"} コピー`,
note: sharedList.note || "",
sections: Array.isArray(sharedList.sections) ? sharedList.sections.map(section => ({
title: section.title,
countInProgress: section.countInProgress !== false,
items: Array.isArray(section.items) ? section.items.map(label => ({ label })) : []
})) : []
}]);
const list = normalized[0] || { id: uid("list"), name: "共有リスト コピー", note: "", sections: [] };
list.id = uid("list");
list.sections.forEach(section => {
section.id = uid("section");
section.items.forEach(item => item.id = uniqueItemId(list, item.label));
});
return list;
}
function clearShareParam() {
const url = new URL(location.href);
url.searchParams.delete("share");
history.replaceState(null, "", `${url.pathname}${url.search}${url.hash}`);
}
function renderTabs(container, selectedId, onSelect) {
container.replaceChildren(...lists.map(list => {
const button = document.createElement("button");
button.type = "button";
button.className = `list-tab${list.id === selectedId ? " active" : ""}`;
button.textContent = list.name;
button.addEventListener("click", () => onSelect(list.id));
return button;
}));
}
function renderOtherTabs(container, selectedId, onSelect) {
const otherLists = lists.filter(list => list.id !== selectedId);
if (!otherLists.length) {
const empty = document.createElement("div");
empty.className = "empty-inline";
empty.textContent = "他の登録済みリストはありません";
container.replaceChildren(empty);
return;
}
container.replaceChildren(...otherLists.map(list => {
const button = document.createElement("button");
button.type = "button";
button.className = "list-tab";
button.textContent = list.name;
button.addEventListener("click", () => onSelect(list.id));
return button;
}));
}
function renderSections(container, list) {
const listChecks = getListChecks(list.id);
const nodes = list.sections.map(section => {
const checkedCount = section.items.filter(item => listChecks[item.id]).length;
const article = document.createElement("article");
article.className = "section";
const header = document.createElement("header");
header.className = "section-header";
const title = document.createElement("h2");
title.className = "section-title";
title.textContent = section.title;
const count = document.createElement("span");
count.className = "section-count";
count.textContent = isSectionCounted(section) ? `${checkedCount} / ${section.items.length}` : "集計対象外";
header.append(title, count);
const items = document.createElement("div");
items.className = "items";
section.items.forEach(item => {
const label = document.createElement("label");
label.className = `item-row${listChecks[item.id] ? " checked" : ""}`;
const checkbox = document.createElement("input");
checkbox.type = "checkbox";
checkbox.checked = Boolean(listChecks[item.id]);
checkbox.addEventListener("change", () => {
listChecks[item.id] = checkbox.checked;
persist();
trackEvent("checklist_item_toggle", {
checked: checkbox.checked,
list_id: list.id,
section_id: section.id
});
renderSections(container, list);
updateProgress({
doneCount: document.getElementById("doneCount"),
progressBar: document.getElementById("progressBar"),
totalCount: document.getElementById("totalCount")
}, list);
});
const text = document.createElement("span");
text.textContent = item.label;
label.append(checkbox, text);
items.append(label);
});
article.append(header, items);
return article;
});
container.replaceChildren(...nodes);
}
function renderEditor(container, list, refresh) {
if (!list.sections.length) {
container.innerHTML = `<div class="empty">カテゴリがありません</div>`;
return;
}
container.replaceChildren(...list.sections.map((section, sectionIndex) => {
const wrapper = document.createElement("div");
wrapper.className = "edit-section";
const head = document.createElement("div");
head.className = "edit-section-head";
const sectionBody = document.createElement("label");
sectionBody.className = "edit-section-label";
const sectionCaption = document.createElement("span");
sectionCaption.className = "edit-label-caption";
sectionCaption.textContent = `カテゴリ・見出し / ${section.items.length}件`;
const sectionInput = document.createElement("input");
sectionInput.value = section.title;
sectionInput.setAttribute("aria-label", "カテゴリ名");
sectionInput.addEventListener("change", () => {
section.title = sectionInput.value.trim() || "未分類";
persist();
refresh();
});
sectionBody.append(sectionCaption, sectionInput);
const sectionMoveControls = moveControls({
upLabel: "カテゴリを上へ移動",
downLabel: "カテゴリを下へ移動",
canMoveUp: sectionIndex > 0,
canMoveDown: sectionIndex < list.sections.length - 1,
onMoveUp: () => {
moveEntry(list.sections, sectionIndex, sectionIndex - 1);
persist();
refresh();
},
onMoveDown: () => {
moveEntry(list.sections, sectionIndex, sectionIndex + 1);
persist();
refresh();
}
});
const deleteSection = iconButton("カテゴリを削除");
deleteSection.addEventListener("click", () => {
if (!confirm(`「${section.title}」を削除しますか？`)) return;
list.sections = list.sections.filter(entry => entry.id !== section.id);
persist();
refresh();
});
head.append(sectionBody, sectionMoveControls, deleteSection);
wrapper.append(head);
const countOption = document.createElement("label");
countOption.className = "edit-section-option";
const countCheckbox = document.createElement("input");
countCheckbox.type = "checkbox";
countCheckbox.checked = isSectionCounted(section);
countCheckbox.addEventListener("change", () => {
section.countInProgress = countCheckbox.checked;
persist();
refresh();
});
const countText = document.createElement("span");
countText.textContent = "準備状況の集計対象にする";
countOption.append(countCheckbox, countText);
wrapper.append(countOption);
section.items.forEach((item, itemIndex) => {
const row = document.createElement("div");
row.className = "edit-item";
const itemBody = document.createElement("label");
itemBody.className = "edit-item-label";
const itemCaption = document.createElement("span");
itemCaption.className = "edit-label-caption";
itemCaption.textContent = "品目";
const input = document.createElement("input");
input.value = item.label;
input.setAttribute("aria-label", "品目名");
input.addEventListener("change", () => {
item.label = input.value.trim() || "未入力";
persist();
refresh();
});
itemBody.append(itemCaption, input);
const itemMoveControls = moveControls({
upLabel: "品目を上へ移動",
downLabel: "品目を下へ移動",
canMoveUp: itemIndex > 0,
canMoveDown: itemIndex < section.items.length - 1,
onMoveUp: () => {
moveEntry(section.items, itemIndex, itemIndex - 1);
persist();
refresh();
},
onMoveDown: () => {
moveEntry(section.items, itemIndex, itemIndex + 1);
persist();
refresh();
}
});
const deleteItem = iconButton("品目を削除");
deleteItem.addEventListener("click", () => {
section.items = section.items.filter(entry => entry.id !== item.id);
delete getListChecks(list.id)[item.id];
persist();
refresh();
});
row.append(itemBody, itemMoveControls, deleteItem);
wrapper.append(row);
});
const actions = document.createElement("div");
actions.className = "edit-actions";
const duplicateSection = document.createElement("button");
duplicateSection.type = "button";
duplicateSection.className = "button ghost";
duplicateSection.textContent = "カテゴリを複製";
duplicateSection.addEventListener("click", () => {
const copy = {
id: uid("section"),
title: `${section.title} コピー`,
countInProgress: isSectionCounted(section),
items: section.items.map(item => ({ id: uid("item"), label: item.label }))
};
list.sections.splice(sectionIndex + 1, 0, copy);
persist();
toast("カテゴリを複製しました");
refresh();
});
const addItem = document.createElement("button");
addItem.type = "button";
addItem.className = "button ghost";
addItem.textContent = "品目を追加";
addItem.addEventListener("click", () => {
const label = prompt("追加する品目名");
if (!label?.trim()) return;
section.items.push({ id: uid("item"), label: label.trim() });
persist();
refresh();
});
actions.append(duplicateSection, addItem);
wrapper.append(actions);
return wrapper;
}));
}
function iconButton(label) {
const button = document.createElement("button");
button.type = "button";
button.className = "button danger icon-button";
button.title = label;
button.setAttribute("aria-label", label);
button.textContent = "×";
return button;
}
function moveControls({ upLabel, downLabel, canMoveUp, canMoveDown, onMoveUp, onMoveDown }) {
const controls = document.createElement("div");
controls.className = "move-controls";
controls.append(
moveButton("↑", upLabel, canMoveUp, onMoveUp),
moveButton("↓", downLabel, canMoveDown, onMoveDown)
);
return controls;
}
function moveButton(symbol, label, enabled, handler) {
const button = document.createElement("button");
button.type = "button";
button.className = "button ghost icon-button move-button";
button.title = label;
button.setAttribute("aria-label", label);
button.disabled = !enabled;
button.textContent = symbol;
button.addEventListener("click", handler);
return button;
}
function moveEntry(entries, fromIndex, toIndex) {
if (toIndex < 0 || toIndex >= entries.length) return;
const [entry] = entries.splice(fromIndex, 1);
entries.splice(toIndex, 0, entry);
}
function updateProgress(els, list) {
const listChecks = getListChecks(list.id);
const items = list.sections.filter(isSectionCounted).flatMap(section => section.items);
const done = items.filter(item => listChecks[item.id]).length;
const total = items.length;
els.doneCount.textContent = done;
els.totalCount.textContent = total;
els.progressBar.style.width = total ? `${Math.round((done / total) * 100)}%` : "0%";
}
function updateDefaultGuide(els) {
if (!els.defaultGuide) return;
els.defaultGuide.hidden = !isDefaultListSetup();
}
function isDefaultListSetup() {
return listSignature(lists) === listSignature(defaultLists);
}
function listSignature(sourceLists) {
return JSON.stringify(sourceLists.map(list => ({
id: list.id,
name: list.name,
note: list.note || "",
sections: list.sections.map(section => ({
id: section.id,
title: section.title,
countInProgress: isSectionCounted(section),
items: section.items.map(item => item.label)
}))
})));
}
function createNewList() {
const list = {
id: uid("list"),
name: "新しいリスト",
note: "",
sections: [{ id: uid("section"), title: "絶対いるもの", countInProgress: true, items: [] }]
};
lists.push(list);
activeListId = list.id;
persist();
trackEvent("list_create", { list_id: list.id });
toast("新しいリストを作成しました");
return list;
}
function exportJsonBackup() {
const backup = {
app: "fishingGearCheck",
version: BACKUP_VERSION,
exportedAt: new Date().toISOString(),
activeListId,
lists,
checks
};
const blob = new Blob([JSON.stringify(backup, null, 2)], { type: "application/json" });
const url = URL.createObjectURL(blob);
const date = new Date().toISOString().slice(0, 10);
const link = document.createElement("a");
link.href = url;
link.download = `fishing-gear-check-backup-${date}.json`;
document.body.append(link);
link.click();
link.remove();
URL.revokeObjectURL(url);
trackEvent("backup_export", { format: "json" });
toast("バックアップを書き出しました");
}
function exportCsvBackup() {
const listHeaders = lists.map((list, index) => `リスト${index + 1}:${list.name}`);
const listNoteHeaders = lists.map((list, index) => `リスト${index + 1}メモ:${list.note || ""}`);
const rows = [["品目番号", "品目", "カテゴリ", "対象リスト番号", "リスト内表示順", "リスト別カテゴリ", "チェック済みリスト番号", ...listHeaders, ...listNoteHeaders]];
const itemMap = new Map();
lists.forEach((list, listIndex) => {
const listNumber = listIndex + 1;
const listChecks = getListChecks(list.id);
let displayOrder = 1;
list.sections.forEach(section => {
section.items.forEach(item => {
const key = normalizeItemKey(item.label);
if (!itemMap.has(key)) {
itemMap.set(key, {
label: item.label,
sectionTitle: section.title,
targets: [],
checkedTargets: [],
sections: new Map(),
orders: new Map()
});
}
const entry = itemMap.get(key);
entry.targets.push(listNumber);
entry.orders.set(listNumber, displayOrder);
entry.sections.set(listNumber, section.title);
if (listChecks[item.id]) entry.checkedTargets.push(listNumber);
displayOrder += 1;
});
});
});
Array.from(itemMap.values()).forEach((entry, index) => {
const targetNumbers = entry.targets.join(";");
const orderValues = entry.targets.map(listNumber => `${listNumber}:${entry.orders.get(listNumber)}`).join(";");
const sectionValues = entry.targets.map(listNumber => `${listNumber}:${entry.sections.get(listNumber)}`).join(";");
rows.push([
index + 1,
entry.label,
entry.sectionTitle,
targetNumbers,
orderValues,
sectionValues,
entry.checkedTargets.join(";"),
...lists.map(() => ""),
...lists.map(() => "")
]);
});
const csv = rows.map(row => row.map(csvCell).join(",")).join("\r\n");
const blob = new Blob([`\uFEFF${csv}`], { type: "text/csv;charset=utf-8" });
const url = URL.createObjectURL(blob);
const date = new Date().toISOString().slice(0, 10);
const link = document.createElement("a");
link.href = url;
link.download = `fishing-gear-check-backup-${date}.csv`;
document.body.append(link);
link.click();
link.remove();
URL.revokeObjectURL(url);
trackEvent("backup_export", { format: "csv" });
toast("CSVバックアップを書き出しました");
}
function csvCell(value) {
return `"${String(value ?? "").replaceAll('"', '""')}"`;
}
function importBackup(file, refresh) {
const reader = new FileReader();
reader.addEventListener("load", () => {
try {
const backup = JSON.parse(String(reader.result || "{}"));
if (!backup || backup.app !== "fishingGearCheck" || !Array.isArray(backup.lists)) {
throw new Error("Invalid backup");
}
if (!confirm("バックアップ内容で現在の保存内容を置き換えますか？")) return;
lists = normalizeLists(backup.lists);
checks = backup.checks && typeof backup.checks === "object" ? backup.checks : {};
activeListId = lists.find(list => list.id === backup.activeListId)?.id || lists[0].id;
persist();
trackEvent("backup_import", { format: "json" });
toast("バックアップを復元しました");
refresh();
} catch {
toast("バックアップを読み込めませんでした");
}
});
reader.readAsText(file);
}
function importCsvBackup(file, refresh) {
const reader = new FileReader();
reader.addEventListener("load", () => {
try {
const rows = parseCsv(String(reader.result || ""));
const dataRows = rows.slice(1).filter(row => row.some(cell => cell.trim()));
if (!dataRows.length) throw new Error("Empty CSV");
if (!confirm("CSV内容で現在の保存内容を置き換えますか？")) return;
const parsed = isMatrixCsv(rows[0]) ? parseMatrixCsv(rows) : parseLegacyCsv(dataRows);
lists = normalizeLists(parsed.lists);
checks = parsed.checks;
activeListId = lists[0].id;
persist();
trackEvent("backup_import", { format: "csv" });
toast("CSVバックアップを復元しました");
refresh();
} catch {
toast("CSVバックアップを読み込めませんでした");
}
});
reader.readAsText(file);
}
function isMatrixCsv(headerRow = []) {
return headerRow.includes("品目") && headerRow.includes("対象リスト番号") && headerRow.includes("リスト内表示順");
}
function parseMatrixCsv(rows) {
const header = rows[0];
const itemIndex = header.indexOf("品目");
const sectionIndex = header.indexOf("カテゴリ");
const targetIndex = header.indexOf("対象リスト番号");
const orderIndex = header.indexOf("リスト内表示順");
const sectionMapIndex = header.indexOf("リスト別カテゴリ");
const checkedIndex = header.indexOf("チェック済みリスト番号");
const listDefs = readListDefs(header);
const nextLists = listDefs.map(def => ({ id: uid("list"), name: def.name, note: def.note || "", sections: [] }));
const nextChecks = {};
const pendingItems = new Map();
rows.slice(1).forEach(row => {
if (!row.some(cell => cell.trim())) return;
const label = (row[itemIndex] || "").trim();
if (!label) return;
const sectionTitle = (row[sectionIndex] || "").trim() || "未分類";
const targetNumbers = parseNumberList(row[targetIndex]);
const orderMap = parseOrderMap(row[orderIndex]);
const sectionMap = parseTextMap(row[sectionMapIndex]);
const checkedNumbers = new Set(parseNumberList(row[checkedIndex]));
targetNumbers.forEach(listNumber => {
const list = nextLists[listNumber - 1];
if (!list) return;
const order = orderMap.get(listNumber) ?? Number.MAX_SAFE_INTEGER;
const listSectionTitle = sectionMap.get(listNumber) || sectionTitle;
if (!pendingItems.has(list.id)) pendingItems.set(list.id, []);
pendingItems.get(list.id).push({ label, sectionTitle: listSectionTitle, order, checked: checkedNumbers.has(listNumber) });
});
});
nextLists.forEach(list => {
const entries = (pendingItems.get(list.id) || []).sort((a, b) => a.order - b.order || a.label.localeCompare(b.label, "ja"));
entries.forEach(entry => {
let section = list.sections.find(candidate => candidate.title === entry.sectionTitle);
if (!section) {
section = { id: uid("section"), title: entry.sectionTitle, items: [] };
list.sections.push(section);
}
const item = { id: uniqueItemId(list, entry.label), label: entry.label };
section.items.push(item);
if (entry.checked) {
nextChecks[list.id] ||= {};
nextChecks[list.id][item.id] = true;
}
});
});
return { lists: nextLists, checks: nextChecks };
}
function parseLegacyCsv(dataRows) {
const nextLists = [];
const nextChecks = {};
dataRows.forEach(row => {
const [listName = "", sectionTitle = "", itemLabel = "", checked = ""] = row;
const cleanListName = listName.trim() || "未命名リスト";
const cleanSectionTitle = sectionTitle.trim() || "未分類";
let list = nextLists.find(entry => entry.name === cleanListName);
if (!list) {
list = { id: uid("list"), name: cleanListName, note: "", sections: [] };
nextLists.push(list);
}
let section = list.sections.find(entry => entry.title === cleanSectionTitle);
if (!section) {
section = { id: uid("section"), title: cleanSectionTitle, items: [] };
list.sections.push(section);
}
if (!itemLabel.trim()) return;
const item = { id: uniqueItemId(list, itemLabel.trim()), label: itemLabel.trim() };
section.items.push(item);
if (/^(yes|true|1|済|チェック済み)$/i.test(checked.trim())) {
nextChecks[list.id] ||= {};
nextChecks[list.id][item.id] = true;
}
});
return { lists: nextLists, checks: nextChecks };
}
function readListDefs(header) {
const noteMap = new Map();
header.forEach(cell => {
const match = String(cell || "").match(/^リスト(\d+)メモ[:：](.*)$/);
if (match) noteMap.set(Number(match[1]), match[2].trim());
});
const defs = header
.map(cell => String(cell || "").match(/^リスト(\d+)[:：](.+)$/))
.filter(Boolean)
.map(match => {
const number = Number(match[1]);
return {
number,
name: match[2].trim() || `リスト${match[1]}`,
note: noteMap.get(number) || ""
};
})
.sort((a, b) => a.number - b.number);
return defs.length ? defs : [{ number: 1, name: "リスト1", note: "" }];
}
function parseNumberList(value) {
return String(value || "")
.split(/[;；、,\s]+/)
.map(entry => Number(entry.trim()))
.filter(Number.isFinite);
}
function parseOrderMap(value) {
const orderMap = new Map();
String(value || "").split(/[;；]+/).forEach(entry => {
const [listNumber, order] = entry.split(/[:：]/).map(part => Number(String(part || "").trim()));
if (Number.isFinite(listNumber) && Number.isFinite(order)) orderMap.set(listNumber, order);
});
return orderMap;
}
function parseTextMap(value) {
const textMap = new Map();
String(value || "").split(/[;；]+/).forEach(entry => {
const separatorIndex = entry.search(/[:：]/);
if (separatorIndex < 0) return;
const listNumber = Number(entry.slice(0, separatorIndex).trim());
const text = entry.slice(separatorIndex + 1).trim();
if (Number.isFinite(listNumber) && text) textMap.set(listNumber, text);
});
return textMap;
}
function normalizeItemKey(value) {
return String(value || "").normalize("NFKC").trim().toLowerCase();
}
function uniqueItemId(list, label) {
const usedIds = new Set(list.sections.flatMap(section => section.items.map(item => item.id)));
const base = slugify(label);
if (!usedIds.has(base)) return base;
let index = 2;
while (usedIds.has(`${base}-${index}`)) index += 1;
return `${base}-${index}`;
}
function parseCsv(text) {
const rows = [];
let row = [];
let cell = "";
let quoted = false;
for (let i = 0; i < text.length; i++) {
const char = text[i];
const next = text[i + 1];
if (quoted) {
if (char === "\"" && next === "\"") {
cell += "\"";
i++;
} else if (char === "\"") {
quoted = false;
} else {
cell += char;
}
} else if (char === "\"") {
quoted = true;
} else if (char === ",") {
row.push(cell);
cell = "";
} else if (char === "\n") {
row.push(cell.replace(/\r$/, ""));
rows.push(row);
row = [];
cell = "";
} else {
cell += char;
}
}
row.push(cell.replace(/\r$/, ""));
rows.push(row);
return rows;
}
function getActiveList() {
return lists.find(list => list.id === activeListId) || lists[0];
}
function getListChecks(listId) {
checks[listId] ||= {};
return checks[listId];
}
function ensureLists() {
if (!lists.length) {
lists = structuredClone(defaultLists);
activeListId = lists[0].id;
persist();
}
if (!lists.some(list => list.id === activeListId)) {
activeListId = lists[0].id;
persist();
}
}
function migrateLegacyDefaultLists() {
if (!localStorage.getItem(STORAGE_KEY) || !isLegacyDefaultListSetup()) return;
lists = structuredClone(defaultLists);
activeListId = lists[0].id;
persist();
}
function isLegacyDefaultListSetup() {
return lists.length === 3 &&
lists[0]?.id === "tenya-tachiuo" &&
lists[1]?.id === "casting-game" &&
lists[2]?.id === "nomase" &&
lists[0]?.name === "テンヤタチウオ用" &&
lists[1]?.name === "キャスティングゲーム用" &&
lists[2]?.name === "泳がせ用" &&
lists[0]?.sections?.length === 3 &&
lists[1]?.sections?.length === 2 &&
lists[2]?.sections?.length === 2 &&
lists[0]?.sections?.[0]?.items?.length === 26 &&
lists[0]?.sections?.[0]?.items?.[2]?.label === "仕掛け（テンヤ、タイラバ）" &&
lists[1]?.sections?.[0]?.items?.length === 15 &&
lists[1]?.sections?.[0]?.items?.[2]?.label === "ルアーケース" &&
lists[2]?.sections?.[0]?.items?.length === 14 &&
lists[2]?.sections?.[0]?.items?.[2]?.label === "泳がせ仕掛け";
}
function persist() {
localStorage.setItem(STORAGE_KEY, JSON.stringify(lists));
localStorage.setItem(CHECKS_KEY, JSON.stringify(checks));
localStorage.setItem(ACTIVE_KEY, activeListId);
}
function trackEvent(name, params = {}) {
if (typeof gtag !== "function") return;
gtag("event", name, params);
}
function loadJson(key, fallback) {
try {
const value = localStorage.getItem(key);
return value ? JSON.parse(value) : structuredClone(fallback);
} catch {
return structuredClone(fallback);
}
}
function normalizeLists(rawLists) {
return rawLists
.filter(list => list && typeof list === "object")
.map(list => ({
id: String(list.id || uid("list")),
name: String(list.name || "未命名リスト"),
note: String(list.note || ""),
sections: Array.isArray(list.sections) ? list.sections.map(section => ({
id: String(section.id || uid("section")),
title: String(section.title || "未分類"),
countInProgress: section.countInProgress !== false,
items: Array.isArray(section.items) ? section.items.map(item => ({
id: String(item.id || uid("item")),
label: String(item.label || "未入力")
})) : []
})) : []
}));
}
function defaultSection(id, title, itemLabels) {
return { id, title, countInProgress: true, items: itemLabels.map(makeItem) };
}
function isSectionCounted(section) {
return section.countInProgress !== false;
}
function makeItem(label) {
return { id: slugify(label), label };
}
function slugify(value) {
return String(value)
.normalize("NFKC")
.replace(/[^\p{Letter}\p{Number}]+/gu, "-")
.replace(/^-|-$/g, "")
.toLowerCase() || uid("item");
}
function uid(prefix) {
if (crypto.randomUUID) return `${prefix}-${crypto.randomUUID()}`;
return `${prefix}-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 7)}`;
}
function toast(message) {
const el = document.getElementById("toast");
if (!el) return;
el.textContent = message;
el.classList.add("show");
clearTimeout(toast.timer);
toast.timer = setTimeout(() => el.classList.remove("show"), 1800);
}
function registerServiceWorker() {
if ("serviceWorker" in navigator) {
window.addEventListener("load", () => navigator.serviceWorker.register("service-worker.js"));
}
}
return {
renderChecklistPage,
renderEditPage
};
})();
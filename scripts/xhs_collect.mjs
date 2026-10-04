// 用专用的有窗口 Chrome（CDP 端口）打开小红书链接，读取笔记数据，关闭标签页。
// 用法: node xhs_collect.mjs <port> <url>   -> stdout 输出一行 JSON
const [port, url] = process.argv.slice(2);
const base = `http://127.0.0.1:${port}`;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const tab = await (await fetch(`${base}/json/new?${encodeURI(url)}`, { method: 'PUT' })).json();
const ws = new WebSocket(tab.webSocketDebuggerUrl);
await new Promise((r) => (ws.onopen = r));
let seq = 0;
const pending = new Map();
ws.onmessage = (m) => { const d = JSON.parse(m.data); if (pending.has(d.id)) { pending.get(d.id)(d); pending.delete(d.id); } };
const call = (method, params = {}) => new Promise((r) => { const id = ++seq; pending.set(id, r); ws.send(JSON.stringify({ id, method, params })); });
const evaluate = async (expr) => (await call('Runtime.evaluate', { expression: expr, returnByValue: true })).result?.result?.value;

const EXTRACT = `(() => {
  const href = location.href;
  if (href.includes('website-login/error') || href.includes('/404')) return {error: 'blocked', href};
  const st = window.__INITIAL_STATE__; if (!st || !st.note) return null;
  const map = st.note.noteDetailMap || {}; const id = Object.keys(map).find(k => map[k] && map[k].note && map[k].note.noteId);
  if (!id) return null; const n = map[id].note; const v = n.video || {};
  const streams = []; try { const s = v.media.stream; for (const k of Object.keys(s)) for (const x of (s[k]||[])) if (x && x.masterUrl) streams.push({codec:k, url:x.masterUrl, backup:(x.backupUrls||[]), size:x.size||0}); } catch(e) {}
  streams.sort((a, b) => (a.size || 1e12) - (b.size || 1e12));
  return {href, note_id: id, title: n.title || '', desc: n.desc || '', type: n.type, author: n.user && n.user.nickname,
    time: n.time, ip: n.ipLocation || '', interact: n.interactInfo || {}, tags: (n.tagList||[]).map(t => t.name).filter(Boolean),
    images: (n.imageList||[]).map(i => i.urlDefault || i.urlPre), duration: v.capa && v.capa.duration, streams};
})()`;

const ok = (d) => d && (d.error || d.type !== 'video' || d.streams.length > 0);
let data = null;
for (let i = 0; i < 30 && !ok(data); i++) { await sleep(500); try { data = await evaluate(EXTRACT); } catch (e) {} }
// 短链有时跳到 /discovery/item/ 页面，那里没有视频地址：改去标准 /explore/ 页面再读
if (data && !ok(data) && data.note_id) {
  const tok = (data.href.match(/xsec_token=([^&]+)/) || [])[1];
  const target = `https://www.xiaohongshu.com/explore/${data.note_id}` + (tok ? `?xsec_token=${tok}&xsec_source=app_share` : '');
  await call('Page.navigate', { url: target });
  await sleep(1500);
  for (let i = 0; i < 30; i++) { await sleep(500); let d = null; try { d = await evaluate(EXTRACT); } catch (e) {} if (d && (d.error || ok(d))) { data = d.error ? data : d; break; } }
}
await fetch(`${base}/json/close/${tab.id}`).catch(() => {});
ws.close();
console.log(JSON.stringify(data || { error: 'timeout' }));
process.exit(0);

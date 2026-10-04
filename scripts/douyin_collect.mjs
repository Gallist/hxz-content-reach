// 用专用后台 Chrome（CDP 端口）打开抖音作品页，读取页面自己请求的作品详情接口返回。
// 用法: node douyin_collect.mjs <port> <url>   -> stdout 输出一行 JSON：aweme_detail 或 {error}
const [port, url] = process.argv.slice(2);
const base = `http://127.0.0.1:${port}`;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const tab = await (await fetch(`${base}/json/new?about:blank`, { method: 'PUT' })).json();
const ws = new WebSocket(tab.webSocketDebuggerUrl);
await new Promise((r) => (ws.onopen = r));
let seq = 0;
const pending = new Map();
const detailReqs = [];
ws.onmessage = (m) => {
  const d = JSON.parse(m.data);
  if (d.id && pending.has(d.id)) { pending.get(d.id)(d); pending.delete(d.id); return; }
  if (d.method === 'Network.responseReceived' && /aweme\/v1\/web\/aweme\/detail/.test(d.params.response.url)) detailReqs.push(d.params.requestId);
};
const call = (method, params = {}) => new Promise((r) => { const id = ++seq; pending.set(id, r); ws.send(JSON.stringify({ id, method, params })); });

await call('Network.enable', { maxResourceBufferSize: 50e6, maxTotalBufferSize: 100e6 });
await call('Page.navigate', { url });
let detail = null;
for (let i = 0; i < 60 && !detail; i++) {
  await sleep(500);
  for (const rid of detailReqs) {
    const body = await call('Network.getResponseBody', { requestId: rid });
    try { const j = JSON.parse(body.result.body); if (j.aweme_detail) { detail = j.aweme_detail; break; } } catch (e) {}
  }
}
const href = (await call('Runtime.evaluate', { expression: 'location.href', returnByValue: true })).result?.result?.value;
await fetch(`${base}/json/close/${tab.id}`).catch(() => {});
ws.close();
console.log(JSON.stringify(detail || { error: 'no aweme_detail', href }));
process.exit(0);

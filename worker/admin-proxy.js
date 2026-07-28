const GAS_EXEC_URL = "https://script.google.com/macros/s/AKfycbxAxJXx-tQ1l0RF8Xu3n3jP272oB2NV3bYz-eNMxm4Z101B92q_I1bsCDdWOW6zptVEGA/exec";

async function proxyTo(target) {
  const upstream = await fetch(target, { redirect: "follow" });
  const headers = new Headers(upstream.headers);
  headers.delete("x-frame-options");
  headers.delete("content-security-policy");
  return new Response(upstream.body, { status: upstream.status, headers });
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (url.pathname === "/admin" || url.pathname.startsWith("/admin/")) {
      return proxyTo(GAS_EXEC_URL + url.search);
    }

    // trang GAS tham chieu CSS/JS bang duong dan tuong doi /static/macros/...
    // (goc script.google.com) — phai proxy tiep, khong thi trang /admin trang
    // vi thieu JS khoi tao sandbox iframe.
    if (url.pathname.startsWith("/static/macros/")) {
      return proxyTo("https://script.google.com" + url.pathname + url.search);
    }

    return env.ASSETS.fetch(request);
  },
};

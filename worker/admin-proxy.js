const GAS_EXEC_URL = "https://script.google.com/macros/s/AKfycbxAxJXx-tQ1l0RF8Xu3n3jP272oB2NV3bYz-eNMxm4Z101B92q_I1bsCDdWOW6zptVEGA/exec";

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    // Reverse-proxy day du bi chan boi man canh bao "unverified app" cua Google
    // (yeu cau nguoi dung bam xac nhan tren chinh domain script.google.com) —
    // khong the bypass tu server. Fallback: redirect thang, khong gia domain nua.
    if (url.pathname === "/admin" || url.pathname.startsWith("/admin/")) {
      return Response.redirect(GAS_EXEC_URL, 302);
    }

    return env.ASSETS.fetch(request);
  },
};

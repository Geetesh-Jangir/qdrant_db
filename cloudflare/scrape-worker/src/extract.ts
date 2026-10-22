const THIN_CHARS = 120;

function decodeHtmlEntities(text: string): string {
  return text
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/&nbsp;/g, " ");
}

function stripTags(html: string): string {
  return decodeHtmlEntities(html.replace(/<script[\s\S]*?<\/script>/gi, "").replace(/<style[\s\S]*?<\/style>/gi, ""))
    .replace(/<[^>]+>/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function metaContent(html: string, pattern: RegExp): string | null {
  const m = html.match(pattern);
  return m?.[1] ? decodeHtmlEntities(m[1].trim()) : null;
}

export function extractFromHtml(html: string, pageUrl: string): {
  title: string | null;
  date: string | null;
  text: string;
  thin: boolean;
} {
  const title =
    metaContent(html, /<meta[^>]+property=["']og:title["'][^>]+content=["']([^"']+)["']/i) ||
    metaContent(html, /<meta[^>]+name=["']twitter:title["'][^>]+content=["']([^"']+)["']/i) ||
    metaContent(html, /<title[^>]*>([^<]+)<\/title>/i);

  const date =
    metaContent(html, /<meta[^>]+property=["']article:published_time["'][^>]+content=["']([^"']+)["']/i) ||
    metaContent(html, /<meta[^>]+name=["']date["'][^>]+content=["']([^"']+)["']/i);

  let text = "";
  const articleMatch = html.match(/<article[\s\S]*?<\/article>/i);
  if (articleMatch) {
    text = stripTags(articleMatch[0]);
  }
  if (text.length < THIN_CHARS) {
    const paras: string[] = [];
    const re = /<p[^>]*>([\s\S]*?)<\/p>/gi;
    let m: RegExpExecArray | null;
    while ((m = re.exec(html)) !== null) {
      const chunk = stripTags(m[1]);
      if (chunk.length > 40) paras.push(chunk);
    }
    if (paras.length) text = paras.join("\n\n");
  }
  if (text.length < THIN_CHARS) {
    const desc =
      metaContent(html, /<meta[^>]+property=["']og:description["'][^>]+content=["']([^"']+)["']/i) ||
      metaContent(html, /<meta[^>]+name=["']description["'][^>]+content=["']([^"']+)["']/i);
    if (desc) text = desc;
  }

  if (!text && title) text = title;

  return {
    title,
    date,
    text: text || "",
    thin: (text || "").length < THIN_CHARS,
  };
}

export { THIN_CHARS };

const fs = require("fs");
const path = require("path");

const input = process.argv[2];
const output = process.argv[3];

if (!input || !output) {
  console.error("Usage: node tools/optimize-screen-design-html.js <input.html> <output.html>");
  process.exit(1);
}

function decodeHtml(value) {
  return value
    .replace(/&quot;/g, '"')
    .replace(/&#34;/g, '"')
    .replace(/&apos;/g, "'")
    .replace(/&#39;/g, "'")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&amp;/g, "&");
}

function extractTag(source, tag) {
  const re = new RegExp(`<${tag}\\b[^>]*>([\\s\\S]*?)<\\/${tag}>`, "i");
  const match = source.match(re);
  return match ? match[1] : "";
}

function splitSelectors(selectorText) {
  const selectors = [];
  let current = "";
  let depth = 0;

  for (const char of selectorText) {
    if (char === "(" || char === "[") depth += 1;
    if (char === ")" || char === "]") depth = Math.max(0, depth - 1);
    if (char === "," && depth === 0) {
      selectors.push(current.trim());
      current = "";
    } else {
      current += char;
    }
  }
  if (current.trim()) selectors.push(current.trim());
  return selectors;
}

function prefixSelector(selector, scope) {
  const trimmed = selector.trim();
  if (!trimmed) return trimmed;
  if (trimmed.startsWith(scope)) return trimmed;

  if (trimmed === "html" || trimmed === "body" || trimmed === ":root") return scope;
  if (trimmed === "*" || trimmed === "*,*::before,*::after") return `${scope} ${trimmed}`;
  if (trimmed.startsWith("html ") || trimmed.startsWith("body ")) {
    return trimmed.replace(/^(html|body)\b/, scope);
  }
  return `${scope} ${trimmed}`;
}

function findMatchingBrace(css, openIndex) {
  let depth = 0;
  for (let i = openIndex; i < css.length; i += 1) {
    if (css[i] === "{") depth += 1;
    if (css[i] === "}") {
      depth -= 1;
      if (depth === 0) return i;
    }
  }
  return -1;
}

function scopeCss(css, scope) {
  const clean = css.replace(/^\uFEFF/, "");
  let result = "";
  let index = 0;

  while (index < clean.length) {
    const open = clean.indexOf("{", index);
    if (open === -1) {
      result += clean.slice(index);
      break;
    }

    const selector = clean.slice(index, open).trim();
    const close = findMatchingBrace(clean, open);
    if (close === -1) {
      result += clean.slice(index);
      break;
    }

    const block = clean.slice(open + 1, close);
    if (selector.startsWith("@media") || selector.startsWith("@supports")) {
      result += `${selector}{${scopeCss(block, scope)}}`;
    } else if (selector.startsWith("@keyframes") || selector.startsWith("@font-face") || selector.startsWith("@page")) {
      result += `${selector}{${block}}`;
    } else if (selector.startsWith("@")) {
      result += `${selector}{${block}}`;
    } else {
      const prefixed = splitSelectors(selector)
        .map((item) => prefixSelector(item, scope))
        .join(",");
      result += `${prefixed}{${block}}`;
    }

    index = close + 1;
  }

  return result;
}

function screenClass(screenId) {
  return `screen-${screenId.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "")}`;
}

function annotateScreenSheets(body) {
  return body.replace(/<div class="sheet screen-fit">([\s\S]*?)(?=<div class="sheet screen-fit">|$)/g, (match) => {
    const idMatch = match.match(/<td class="l">Screen ID<\/td><td>([^<]+)<\/td>/);
    if (!idMatch) return match;

    const classes = idMatch[1]
      .split(/[,\s~]+/)
      .map((id) => id.trim())
      .filter(Boolean)
      .map(screenClass)
      .join(" ");

    return match.replace('<div class="sheet screen-fit">', `<div class="sheet screen-fit ${classes}">`);
  });
}

function flattenIframes(html) {
  let count = 0;
  return html.replace(
    /<section class="part"><h2>([\s\S]*?)<\/h2><iframe\b([^>]*)\bsrcdoc="([\s\S]*?)"><\/iframe><\/section>/g,
    (_match, heading, attrs, encodedSrcdoc) => {
      count += 1;
      const titleMatch = attrs.match(/\btitle="([^"]*)"/);
      const title = titleMatch ? titleMatch[1] : heading;
      const decoded = decodeHtml(encodedSrcdoc);
      const styles = [...decoded.matchAll(/<style\b[^>]*>([\s\S]*?)<\/style>/gi)]
        .map((match) => match[1])
        .join("\n");
      const body = annotateScreenSheets(extractTag(decoded, "body") || decoded);
      const scope = `embedded-doc-${count}`;
      const scopedCss = scopeCss(styles, `.${scope}`);

      return `<section class="part print-part"><h2>${heading}</h2>
<div class="embedded-doc ${scope}" data-source-title="${title}">
<style>${scopedCss}</style>
${body}
</div>
</section>`;
    },
  );
}

const pdfCss = `

/* PDF/print optimization: detail screens are flattened, not nested iframe scroll boxes. */
@page { size: A4 landscape; margin: 6mm; }
.embedded-doc{width:100%;overflow:visible;}
.embedded-doc iframe{display:none!important;}
.part.print-part{overflow:visible;}
.part.print-part>h2{display:block;margin:0 0 12px;font-size:17px;color:#0f6e56;}

@media screen{
  .part.print-part{padding:18px 20px;}
  .embedded-doc{border-radius:8px;overflow:visible;}
  .embedded-doc .doc-title,
  .embedded-doc .sec,
  .embedded-doc .sheet{max-width:none!important;}
}

/* HTML-first normalization: use F-MY-001's 1314:788 room ratio as the shared detail-screen frame. */
.embedded-doc .sheet.screen-fit{max-width:1240px!important;margin-left:auto!important;margin-right:auto!important;}
.embedded-doc .sheet.screen-fit .grid{display:grid!important;grid-template-columns:minmax(0,1.72fr) minmax(280px,.92fr)!important;gap:16px!important;align-items:start!important;}
.embedded-doc .sheet.screen-fit .canvas{width:100%!important;min-width:0!important;padding:16px 20px!important;display:flex!important;align-items:center!important;justify-content:center!important;}
.embedded-doc .sheet.screen-fit .panel{min-width:280px!important;max-width:100%!important;}
.embedded-doc .sheet.screen-fit .canvas>.browser{width:100%!important;aspect-ratio:1314/788!important;min-height:0!important;height:auto!important;display:flex!important;flex-direction:column!important;overflow:hidden!important;}
.embedded-doc .sheet.screen-fit .browser>.bbar{flex:0 0 34px!important;}
.embedded-doc .sheet.screen-fit .browser>.body,
.embedded-doc .sheet.screen-fit .browser>.ob-shot,
.embedded-doc .sheet.screen-fit .browser>.landing-clean,
.embedded-doc .sheet.screen-fit .browser>.chat-stage,
.embedded-doc .sheet.screen-fit .browser>.report-shell,
.embedded-doc .sheet.screen-fit .browser>.my-realroom{flex:1 1 auto!important;min-height:0!important;height:auto!important;}
.embedded-doc .sheet.screen-fit .ob-shot,
.embedded-doc .sheet.screen-fit .landing-clean,
.embedded-doc .sheet.screen-fit .ref-chat,
.embedded-doc .sheet.screen-fit .ref-report,
.embedded-doc .sheet.screen-fit .my-app.ref-room{min-height:0!important;}
.embedded-doc .sheet.screen-fit .ob-shot{padding:20px!important;}
.embedded-doc .sheet.screen-fit .ob-center{height:100%!important;}
.embedded-doc .sheet.screen-fit .ob-card{width:min(440px,86%)!important;padding:18px!important;}
.embedded-doc .sheet.screen-fit .ob-layout,
.embedded-doc .sheet.screen-fit .ob-cal{height:100%!important;grid-template-columns:minmax(0,1.25fr) minmax(210px,.85fr)!important;gap:12px!important;}
.embedded-doc .sheet.screen-fit .ob-stepper{margin-bottom:10px!important;}
.embedded-doc .sheet.screen-fit .ob-title{font-size:22px!important;line-height:1.16!important;}
.embedded-doc .sheet.screen-fit .ob-copy{font-size:12px!important;line-height:1.45!important;}
.embedded-doc .sheet.screen-fit .ob-char-grid button,
.embedded-doc .sheet.screen-fit .ob-choice-grid button,
.embedded-doc .sheet.screen-fit .ob-social button{min-height:30px!important;}
.embedded-doc .sheet.screen-fit .landing-clean .clean-wrap{height:100%!important;min-height:0!important;grid-template-rows:40px minmax(0,1fr) 96px!important;padding:16px 22px!important;gap:12px!important;}
.embedded-doc .sheet.screen-fit .landing-clean .clean-main{min-height:0!important;grid-template-columns:minmax(0,1fr) 270px!important;gap:22px!important;}
.embedded-doc .sheet.screen-fit .landing-clean .clean-copy h3{font-size:34px!important;line-height:1.08!important;}
.embedded-doc .sheet.screen-fit .landing-clean .clean-copy p{font-size:13px!important;line-height:1.55!important;margin-top:14px!important;}
.embedded-doc .sheet.screen-fit .landing-clean .clean-tarot{min-height:128px!important;padding:16px!important;}
.embedded-doc .sheet.screen-fit .landing-clean .clean-cards{grid-template-columns:repeat(3,1fr)!important;gap:8px!important;}
.embedded-doc .sheet.screen-fit .landing-clean .clean-card{min-height:78px!important;padding:10px!important;}
.embedded-doc .sheet.screen-fit .ref-chat{display:flex!important;flex-direction:column!important;}
.embedded-doc .sheet.screen-fit .ref-chat .bbar{display:none!important;}
.embedded-doc .sheet.screen-fit .chat-stage{flex:1 1 auto!important;min-height:0!important;grid-template-columns:210px minmax(0,1fr)!important;}
.embedded-doc .sheet.screen-fit .chat-side{padding:16px 12px!important;}
.embedded-doc .sheet.screen-fit .chat-bg{min-height:0!important;height:100%!important;}
.embedded-doc .sheet.screen-fit .bot-face{width:108px!important;height:76px!important;margin-bottom:10px!important;}
.embedded-doc .sheet.screen-fit .chat-opener{font-size:12px!important;line-height:1.38!important;padding:10px!important;}
.embedded-doc .sheet.screen-fit .chat-input{flex:0 0 54px!important;}
.embedded-doc .sheet.screen-fit .ref-report{display:flex!important;flex-direction:column!important;}
.embedded-doc .sheet.screen-fit .ref-report .bbar,
.embedded-doc .sheet.screen-fit .ref-report .nav{display:none!important;}
.embedded-doc .sheet.screen-fit .report-shell{height:100%!important;min-height:0!important;grid-template-columns:180px minmax(0,1fr)!important;gap:12px!important;padding:14px!important;}
.embedded-doc .sheet.screen-fit .report-main{padding:16px 18px!important;}
.embedded-doc .sheet.screen-fit .report-main h3{font-size:20px!important;margin:16px 0 8px!important;}
.embedded-doc .sheet.screen-fit .report-text{font-size:11.5px!important;line-height:1.55!important;padding:12px!important;}
.embedded-doc .sheet.screen-fit .my-app.ref-room{display:flex!important;flex-direction:column!important;}
.embedded-doc .sheet.screen-fit .my-app.ref-room .my-topchips{flex:0 0 54px!important;}
.embedded-doc .sheet.screen-fit .my-app.ref-room .my-realroom{flex:1 1 auto!important;min-height:0!important;aspect-ratio:auto!important;background-size:cover!important;background-position:center top!important;}
.embedded-doc .sheet.screen-fit .my-modal-mini{height:100%!important;display:flex!important;flex-direction:column!important;}
.embedded-doc .sheet.screen-fit .my-modal-mini>.head{flex:0 0 auto!important;}
.embedded-doc .sheet.screen-fit .my-profile,
.embedded-doc .sheet.screen-fit .my-mbti.ref{flex:1 1 auto!important;min-height:0!important;}
.embedded-doc .sheet.screen-fit .my-profile{grid-template-columns:190px minmax(0,1fr)!important;gap:12px!important;padding:12px!important;}
.embedded-doc .sheet.screen-fit .my-mbti.ref{grid-template-columns:200px minmax(0,1fr)!important;padding:12px!important;}
.embedded-doc .sheet.screen-fit .my-type b{font-size:34px!important;}
.embedded-doc .sheet.screen-fit .mbti-evidence{font-size:11px!important;line-height:1.5!important;margin:0 12px 12px!important;}
.embedded-doc .sheet.screen-fit ol.desc{font-size:11.5px!important;line-height:1.42!important;}
.embedded-doc .sheet.screen-fit ul.cp{font-size:11px!important;line-height:1.42!important;}

/* Detail UI refinement: keep controls, cards, panels, and descriptions balanced inside the shared frame. */
.embedded-doc .sheet.screen-fit .browser *{min-width:0!important;}
.embedded-doc .sheet.screen-fit .browser button,
.embedded-doc .sheet.screen-fit .browser .ob-btn,
.embedded-doc .sheet.screen-fit .browser .clean-btn,
.embedded-doc .sheet.screen-fit .browser .report-export button,
.embedded-doc .sheet.screen-fit .browser .select-btn{white-space:nowrap!important;line-height:1.15!important;}
.embedded-doc .sheet.screen-fit .browser .m{width:24px!important;height:24px!important;min-height:24px!important;font-size:12px!important;line-height:1!important;}
.embedded-doc .sheet.screen-fit .panel{display:flex!important;flex-direction:column!important;gap:10px!important;}
.embedded-doc .sheet.screen-fit .panel .ph{border-radius:6px 6px 0 0!important;padding:7px!important;}
.embedded-doc .sheet.screen-fit .panel ol.desc,
.embedded-doc .sheet.screen-fit .panel ul.cp{margin:0!important;border-radius:0 0 6px 6px!important;}
.embedded-doc .sheet.screen-fit .panel ol.desc + .ph,
.embedded-doc .sheet.screen-fit .panel ul.cp + .ph{margin-top:2px!important;}
.embedded-doc .sheet.screen-fit .ob-glass,
.embedded-doc .sheet.screen-fit .clean-card,
.embedded-doc .sheet.screen-fit .report-panel,
.embedded-doc .sheet.screen-fit .report-main,
.embedded-doc .sheet.screen-fit .my-card,
.embedded-doc .sheet.screen-fit .my-type,
.embedded-doc .sheet.screen-fit .my-report{overflow:hidden!important;}
.embedded-doc .sheet.screen-fit .ob-hero-panel{display:flex!important;flex-direction:column!important;justify-content:center!important;padding:18px!important;}
.embedded-doc .sheet.screen-fit .ob-char-grid,
.embedded-doc .sheet.screen-fit .ob-choice-grid,
.embedded-doc .sheet.screen-fit .ob-actions,
.embedded-doc .sheet.screen-fit .tag-row,
.embedded-doc .sheet.screen-fit .chat-actions{display:flex!important;flex-wrap:wrap!important;align-items:center!important;gap:8px!important;}
.embedded-doc .sheet.screen-fit .ob-chip{min-height:26px!important;padding:0 10px!important;display:inline-flex!important;align-items:center!important;}
.embedded-doc .sheet.screen-fit .ob-field-grid{grid-template-columns:repeat(2,minmax(0,1fr))!important;gap:8px!important;}
.embedded-doc .sheet.screen-fit .ob-field-grid input{height:30px!important;padding:5px 8px!important;}
.embedded-doc .sheet.screen-fit .ob-textarea{min-height:58px!important;max-height:78px!important;line-height:1.35!important;}
.embedded-doc .sheet.screen-fit .ob-resultbox{line-height:1.38!important;}
.embedded-doc .sheet.screen-fit .ob-tarot-row{display:grid!important;grid-template-columns:repeat(4,1fr)!important;gap:8px!important;align-items:center!important;}
.embedded-doc .sheet.screen-fit .ob-tarot{width:100%!important;height:auto!important;aspect-ratio:48/68!important;}
.embedded-doc .sheet.screen-fit .ob-tarot.large{width:86px!important;height:122px!important;}
.embedded-doc .sheet.screen-fit .ob-cal-grid{gap:3px!important;}
.embedded-doc .sheet.screen-fit .ob-cal-grid div{padding:5px 0!important;}
.embedded-doc .sheet.screen-fit .landing-clean .clean-top{height:40px!important;}
.embedded-doc .sheet.screen-fit .landing-clean .clean-actions{margin-top:18px!important;}
.embedded-doc .sheet.screen-fit .landing-clean .clean-btn{min-height:36px!important;min-width:118px!important;padding:0 14px!important;}
.embedded-doc .sheet.screen-fit .landing-clean .clean-features{min-height:0!important;}
.embedded-doc .sheet.screen-fit .landing-clean .clean-card{display:flex!important;flex-direction:column!important;justify-content:center!important;}
.embedded-doc .sheet.screen-fit .landing-clean .clean-card i{width:28px!important;height:28px!important;line-height:28px!important;margin-bottom:7px!important;}
.embedded-doc .sheet.screen-fit .landing-clean .clean-card span{font-size:11px!important;line-height:1.35!important;}
.embedded-doc .sheet.screen-fit .chat-side{display:flex!important;flex-direction:column!important;justify-content:center!important;gap:10px!important;}
.embedded-doc .sheet.screen-fit .chat-actions span{border-radius:8px!important;padding:7px 9px!important;font-size:11px!important;}
.embedded-doc .sheet.screen-fit .chat-bubble{max-width:54%!important;top:22px!important;left:28px!important;padding:12px 16px!important;}
.embedded-doc .sheet.screen-fit .chat-suggest{height:38px!important;padding:10px 14px!important;}
.embedded-doc .sheet.screen-fit .chat-input{display:grid!important;grid-template-columns:38px minmax(0,1fr) 72px 64px!important;gap:8px!important;padding:9px 12px!important;}
.embedded-doc .sheet.screen-fit .chat-input span{min-height:32px!important;height:32px!important;}
.embedded-doc .sheet.screen-fit .report-left{display:flex!important;flex-direction:column!important;gap:12px!important;}
.embedded-doc .sheet.screen-fit .report-panel{padding:10px!important;}
.embedded-doc .sheet.screen-fit .period-card{padding:9px!important;margin-bottom:7px!important;line-height:1.35!important;}
.embedded-doc .sheet.screen-fit .diary-row{gap:3px!important;}
.embedded-doc .sheet.screen-fit .diary-day{width:auto!important;flex:1 1 0!important;padding:5px 0!important;}
.embedded-doc .sheet.screen-fit .tag-row span{padding:4px 9px!important;font-size:10.5px!important;}
.embedded-doc .sheet.screen-fit .report-export{margin-top:10px!important;}
.embedded-doc .sheet.screen-fit .report-export button{padding:7px 12px!important;}
.embedded-doc .sheet.screen-fit .my-app.ref-room .my-topchips{grid-template-columns:repeat(2,minmax(160px,313px))!important;gap:8px!important;align-content:center!important;}
.embedded-doc .sheet.screen-fit .my-app.ref-room .my-topchips button{height:32px!important;}
.embedded-doc .sheet.screen-fit .my-cardgrid{display:grid!important;grid-template-columns:180px minmax(0,1fr)!important;gap:12px!important;min-height:0!important;}
.embedded-doc .sheet.screen-fit .my-card{padding:12px!important;}
.embedded-doc .sheet.screen-fit .my-avatar{display:grid!important;place-items:center!important;text-align:center!important;}
.embedded-doc .sheet.screen-fit .my-person{width:88px!important;height:88px!important;margin:0 auto 10px!important;}
.embedded-doc .sheet.screen-fit .my-fieldset{display:grid!important;grid-template-columns:repeat(2,minmax(0,1fr))!important;gap:8px!important;}
.embedded-doc .sheet.screen-fit .my-fi{margin:0!important;padding:8px 10px!important;font-size:11px!important;}
.embedded-doc .sheet.screen-fit .my-fi.my-full{grid-column:1/-1!important;}
.embedded-doc .sheet.screen-fit .my-chip{margin:2px 4px 2px 0!important;padding:3px 8px!important;}
.embedded-doc .sheet.screen-fit .taste-later{margin:12px!important;font-size:11.5px!important;line-height:1.45!important;}
.embedded-doc .sheet.screen-fit .my-type{display:flex!important;flex-direction:column!important;justify-content:center!important;}
.embedded-doc .sheet.screen-fit .my-report{display:flex!important;flex-direction:column!important;justify-content:center!important;}
.embedded-doc .sheet.screen-fit .my-axis-row{margin-bottom:8px!important;}
.embedded-doc .sheet.screen-fit .my-axis-row div:first-child{display:flex!important;justify-content:space-between!important;gap:10px!important;}

/* Taller hero/modal screens that need more breathing room than the standard My Room ratio. */
.embedded-doc .sheet.screen-onb-001 .canvas>.browser{aspect-ratio:1314/870!important;}
.embedded-doc .sheet.screen-onb-001 .landing-clean .clean-wrap{grid-template-rows:42px minmax(0,1fr) 110px!important;padding:22px 28px!important;gap:16px!important;}
.embedded-doc .sheet.screen-onb-001 .landing-clean .clean-main{grid-template-columns:minmax(0,1fr) 286px!important;gap:28px!important;align-items:center!important;}
.embedded-doc .sheet.screen-onb-001 .landing-clean .clean-copy{align-self:center!important;}
.embedded-doc .sheet.screen-onb-001 .landing-clean .clean-copy h3{font-size:38px!important;max-width:440px!important;}
.embedded-doc .sheet.screen-onb-001 .landing-clean .clean-copy p{max-width:430px!important;margin-top:16px!important;}
.embedded-doc .sheet.screen-onb-001 .landing-clean .clean-actions{margin-top:22px!important;}
.embedded-doc .sheet.screen-onb-001 .landing-clean .clean-tarot{align-self:center!important;min-height:156px!important;padding:18px!important;}
.embedded-doc .sheet.screen-onb-001 .landing-clean .clean-features{align-items:stretch!important;}
.embedded-doc .sheet.screen-onb-001 .landing-clean .clean-card{min-height:86px!important;padding:12px!important;}

.embedded-doc .sheet.screen-f-my-002 .canvas>.browser,
.embedded-doc .sheet.screen-f-my-004 .canvas>.browser{aspect-ratio:1314/930!important;}
.embedded-doc .sheet.screen-f-my-002 .browser>.my-modal-mini,
.embedded-doc .sheet.screen-f-my-004 .browser>.my-modal-mini{flex:1 1 auto!important;height:auto!important;margin:10px!important;display:flex!important;flex-direction:column!important;}
.embedded-doc .sheet.screen-f-my-002 .my-modal-mini .head,
.embedded-doc .sheet.screen-f-my-004 .my-modal-mini .head{padding:12px 14px!important;}
.embedded-doc .sheet.screen-f-my-002 .my-cardgrid{grid-template-columns:210px minmax(0,1fr)!important;gap:14px!important;flex:1 1 auto!important;padding:14px!important;}
.embedded-doc .sheet.screen-f-my-002 .my-card{display:flex!important;flex-direction:column!important;justify-content:center!important;padding:14px!important;}
.embedded-doc .sheet.screen-f-my-002 .my-avatar{min-height:0!important;}
.embedded-doc .sheet.screen-f-my-002 .my-person{width:104px!important;height:128px!important;}
.embedded-doc .sheet.screen-f-my-002 .my-fieldset{grid-template-columns:repeat(2,minmax(0,1fr))!important;gap:9px!important;}
.embedded-doc .sheet.screen-f-my-002 .my-fi{min-height:38px!important;padding:8px 10px!important;font-size:11.5px!important;}
.embedded-doc .sheet.screen-f-my-002 .my-fi.my-full{min-height:42px!important;}

.embedded-doc .sheet.screen-f-my-004 .my-mbti-modal-ref{background:#100b35!important;}
.embedded-doc .sheet.screen-f-my-004 .mbti-example{margin:10px 14px 0!important;padding:8px 12px!important;}
.embedded-doc .sheet.screen-f-my-004 .my-mbti.ref{grid-template-columns:230px minmax(0,1fr)!important;gap:14px!important;flex:1 1 auto!important;padding:14px!important;}
.embedded-doc .sheet.screen-f-my-004 .my-mbti.ref .my-type{padding:18px!important;justify-content:center!important;}
.embedded-doc .sheet.screen-f-my-004 .my-mbti.ref .my-type b{font-size:40px!important;}
.embedded-doc .sheet.screen-f-my-004 .my-mbti.ref .my-type .prev{margin-top:14px!important;padding-top:14px!important;}
.embedded-doc .sheet.screen-f-my-004 .my-mbti.ref .my-report{padding:16px!important;justify-content:center!important;}
.embedded-doc .sheet.screen-f-my-004 .my-axis{gap:10px!important;}
.embedded-doc .sheet.screen-f-my-004 .my-axis-row{gap:6px!important;margin-bottom:0!important;}
.embedded-doc .sheet.screen-f-my-004 .my-meter{height:10px!important;}
.embedded-doc .sheet.screen-f-my-004 .mbti-evidence{margin:0 14px 14px!important;padding:12px 14px!important;font-size:11.5px!important;line-height:1.55!important;}

@media print{
  *{-webkit-print-color-adjust:exact!important;print-color-adjust:exact!important;}
  html,body{width:297mm;margin:0!important;background:#fff!important;}
  body{padding:0!important;font-size:9px!important;}
  h1{max-width:none!important;margin:0 0 4mm!important;font-size:15pt!important;line-height:1.25!important;}
  .note{max-width:none!important;margin:0 0 4mm!important;font-size:8pt!important;line-height:1.45!important;}
  .spec-section{max-width:none!important;margin:0 0 4mm!important;padding:4mm!important;border-radius:0!important;break-inside:avoid;page-break-inside:avoid;}
  .spec-section h2{font-size:11pt!important;margin:0 0 2.5mm!important;}
  .spec-section table{font-size:7pt!important;}
  .spec-section th,.spec-section td{padding:1.5mm 2mm!important;}
  .tree{gap:2mm!important;}
  .root,.branch{padding:2.5mm!important;font-size:7pt!important;}
  .flow{gap:1.5mm!important;margin-bottom:2mm!important;}
  .flow span{padding:1.5mm 2.5mm!important;font-size:7pt!important;}
  .part.print-part{max-width:none!important;margin:0!important;padding:0!important;border:0!important;border-radius:0!important;background:transparent!important;break-before:page;page-break-before:always;}
  .part.print-part>h2{display:none!important;}
  .embedded-doc{width:100%!important;overflow:visible!important;}
  .embedded-doc .doc-title,
  .embedded-doc .sec{display:none!important;}
  .embedded-doc .sheet{max-width:none!important;margin:0 0 4mm!important;padding:3mm!important;border-radius:1.5mm!important;break-inside:avoid;page-break-inside:avoid;}
  .embedded-doc .sheet + .sheet,
  .embedded-doc .sec + .sheet{break-before:page;page-break-before:always;}
  .embedded-doc table.meta{font-size:6.6pt!important;margin-bottom:2mm!important;line-height:1.2!important;}
  .embedded-doc table.meta td{padding:1mm 1.2mm!important;}
  .embedded-doc table.meta td.l{width:17mm!important;}
  .embedded-doc .grid{display:flex!important;gap:2.5mm!important;align-items:flex-start!important;}
  .embedded-doc .canvas{flex:1.7 1 0!important;min-width:0!important;padding:2.5mm!important;}
  .embedded-doc .panel{flex:0.9 1 46mm!important;min-width:46mm!important;}
  .embedded-doc .ph{font-size:7pt!important;padding:1.1mm!important;}
  .embedded-doc ol.desc{font-size:6.5pt!important;line-height:1.25!important;margin:0 0 1.7mm!important;padding:1.6mm 1.8mm!important;}
  .embedded-doc ol.desc li{margin-bottom:.9mm!important;}
  .embedded-doc ul.cp{font-size:6.3pt!important;line-height:1.25!important;padding:1.6mm 1.8mm!important;}
  .embedded-doc ul.cp li{margin-bottom:.7mm!important;}
  .embedded-doc .browser{box-shadow:none!important;}
  .embedded-doc .bbar{padding:1.2mm 1.6mm!important;}
  .embedded-doc .dot{width:2.2mm!important;height:2.2mm!important;}
  .embedded-doc .url{font-size:6pt!important;padding:.7mm 1.2mm!important;}
  .embedded-doc .m{width:5mm!important;height:5mm!important;min-height:5mm!important;font-size:6.8pt!important;line-height:1!important;}
  .embedded-doc .screen-fit .body,
  .embedded-doc .body{padding:2.2mm!important;}
  .embedded-doc .ob-shot,
  .embedded-doc .landing-clean,
  .embedded-doc .ref-chat,
  .embedded-doc .report-screen,
  .embedded-doc .my-app.ref-room{min-height:72mm!important;}
  .embedded-doc .landing-clean .clean-wrap{min-height:72mm!important;grid-template-rows:7mm 1fr 20mm!important;padding:3mm 5mm!important;gap:2.5mm!important;}
  .embedded-doc .landing-clean .clean-copy h3,
  .embedded-doc .landing-ref .ob-title{font-size:20pt!important;line-height:1.08!important;}
  .embedded-doc .landing-clean .clean-copy p,
  .embedded-doc .landing-ref .ob-copy{font-size:7.5pt!important;line-height:1.45!important;margin-top:2.5mm!important;}
  .embedded-doc .ob-title{font-size:14pt!important;}
  .embedded-doc .ob-copy{font-size:7pt!important;line-height:1.35!important;}
  .embedded-doc .ob-dock div{min-height:14mm!important;padding:2mm!important;}
  .embedded-doc .chat-stage,
  .embedded-doc .chat-bg{min-height:64mm!important;}
  .embedded-doc .report-shell{min-height:70mm!important;padding:3mm!important;gap:2.5mm!important;grid-template-columns:40mm 1fr!important;}
  .embedded-doc .my-app.ref-room .my-realroom{min-height:72mm!important;}
  .embedded-doc .t,
  .embedded-doc table.t{font-size:6.2pt!important;}
  .embedded-doc .t th,
  .embedded-doc .t td{padding:.9mm 1.2mm!important;}
}
`;

const original = fs.readFileSync(input, "utf8");
const flattened = flattenIframes(original);
const optimized = flattened.replace("</style>", `${pdfCss}\n</style>`);

fs.mkdirSync(path.dirname(output), { recursive: true });
fs.writeFileSync(output, optimized, "utf8");

console.log(`Optimized ${input}`);
console.log(`Wrote ${output}`);

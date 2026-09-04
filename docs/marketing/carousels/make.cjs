/**
 * Renders the LinkedIn carousels (docs/marketing/linkedin-series.md) as PDFs, one page per slide,
 * 1080 x 1350 px. Needs a Playwright Chromium: `NODE_PATH=<global node_modules> node make.cjs [outdir]`.
 * The numbers are the current baseline run's; update them here and in the series document together.
 */
const fs = require('fs')
const path = require('path')
const { chromium } = require('playwright')

const OUT = process.argv[2] || __dirname
const APP = 'saro-saravanan.github.io/ai-workforce-sim'
const FOOT = 'AI Workforce Sim · an open-source scenario model by Saro Saravanan'

/** A slide: { k: kicker, h: headline, big?: big number, sub?: line under the big number, items?: bullets, close?: true } */
const CAROUSELS = {
  'A-why-i-built-this': [
    { cover: true, h: 'I fretted about what AI means for my kids. So I built a model.', sub: 'AI Workforce Sim · open source · every assumption visible' },
    { k: 'The problem', h: 'The headlines could not agree.', items: ['Half of all jobs gone', 'Everyone richer', 'Nothing changes', 'Every number from somewhere I could not see'] },
    { k: 'So I made the assumptions visible', h: 'A model, not a forecast.', items: ['19,000 task statements', '831 occupations · 20 sectors', '10 regions on one capability clock', 'Every parameter sourced, ranged, and a lever'] },
    { k: 'The framing', h: 'Every number is a difference.', items: ['A world where AI keeps improving', 'minus a world where it stopped in 2023', 'Not a forecast of the level of jobs'] },
    { k: 'The headline · United States · 2040', big: '13.5M', sub: 'fewer jobs than there would have been, out of 194 million. Most never posted, not lost.' },
    { k: 'The honest part', big: '7 to 20M', sub: 'the range, depending mostly on whether the gains are spent back into the economy' },
    { k: 'Thirteen questions', h: 'The ones I could not answer at dinner.', items: ['Will there be work for my grandchildren?', 'Who pays first?', 'Who keeps the gains?', 'Will the capital pay back?', 'Which businesses win, and which get competed away?'] },
    { k: 'It keeps score', h: 'Checked every quarter against what has happened.', items: ['Firm adoption', 'Announced AI-cited job cuts', 'AI industry revenue', 'Data-centre spending', 'Where it misses, it says so'] },
    { close: true, h: 'Open source. Two-minute tour.', sub: 'What question would you add?' },
  ],
  'B-two-ledgers': [
    { cover: true, h: '13.5 million fewer jobs. 2.9 million layoffs.', sub: 'Those are not the same number.' },
    { k: 'The jobs ledger counts positions', big: '13.5M', sub: 'fewer in 2040 than there would have been · United States, central assumptions' },
    { k: 'The people ledger counts people', big: '11.0M', sub: 'found the job they had, or would have had, gone' },
    { k: 'How they lost it', h: 'Mostly a door that never opened.', items: ['7.8M positions never offered to new entrants', '2.9M layoffs', '0.3M gig and freelance hours cut'] },
    { k: 'Where they went', h: 'Most found other work.', items: ['9.2M found other work', '1.0M left the workforce', '137,000 unemployed in 2040'] },
    { k: 'The peak', big: '489,000', sub: 'extra unemployed at the 2034 peak. The unemployment rate barely moves. The cost is somewhere else.' },
    { k: 'Why the ledgers differ', h: 'Someone who finds other work fills a position that would otherwise have gone to someone else.' },
    { close: true, h: 'A cut through attrition never makes the news.', sub: 'Who is counting in your organisation?' },
  ],
  'C-the-young-pay-first': [
    { cover: true, h: 'The young pay first.', sub: 'Under-25s carry 31% of the jobs AI takes away' },
    { k: 'How the cut arrives', h: 'Attrition and hiring freezes first, layoffs second.', sub: 'The people who cannot yet vote with their feet pay.' },
    { k: 'Share of the shortfall, by age', big: '31%', sub: 'carried by workers under 25, on the central run' },
    { k: 'Share of the group’s own jobs', h: 'Small numbers, unevenly placed.', items: ['Under 25: about 3%', '25 to 44: about 1%', '55 and over: about 1%'] },
    { k: 'By education and income', h: 'The degree and the paycheque both protect.', items: ['No degree: about 2% of jobs', 'Graduates: barely affected', 'Bottom half of earners: about 2%', 'Top tenth: barely touched'] },
    { k: 'The practical advice', h: 'Incumbents are mostly safe. Entrants are not.' },
    { k: 'What changes it', h: 'If employers cut through layoffs instead.', sub: 'Same total, borne by incumbents, and unemployment peaks higher.' },
    { close: true, h: 'What are you telling the seventeen-year-old in your life?', sub: 'Try their outlook in the app' },
  ],
  'D-pay-up-share-down': [
    { cover: true, h: 'Pay goes up. The worker’s share goes down.', sub: 'Both are true, and the model shows how.' },
    { k: 'Prices', big: '−3%', sub: 'lower by 2040 than they would have been · United States' },
    { k: 'Real pay', big: '+3%', sub: 'likely between 2% and 6% · about $2,000 a year on a $60,000 salary' },
    { k: 'The economy', big: '+5%', sub: 'larger than it would have been' },
    { k: 'The worker’s share of income', big: '−5.8 pts', sub: 'The gains are real, and they go disproportionately to owners.' },
    { k: 'What decides it', h: 'How much of the cost saving reaches prices.', sub: 'Kept as margin: pay rises less, the owner share rises more.' },
    { k: 'One lever', h: 'Optimists and pessimists disagree about pass-through.', sub: 'Move it in the What-if panel and watch the split change.' },
    { close: true, h: 'Will AI make us richer? On average, yes.', sub: 'Who is “us”?' },
  ],
  'E-the-trillion-dollar-bet': [
    { cover: true, h: 'A trillion dollars a year into data centres.', sub: 'Who gets the return?' },
    { k: 'The money going in · four companies', h: 'Front-loaded.', items: ['$413B in 2025', '$732B guided for 2026', 'about $1.05T a year by 2030'] },
    { k: 'Over 2024 to 2040', big: '$15.6T', sub: 'of capital, on the model’s path' },
    { k: 'The money coming back to the builders', h: 'Producer revenue.', items: ['$95B in 2026', 'about $500B by 2030', 'about $630B by 2040'] },
    { k: 'Cumulative producer revenue', big: '$7.7T', sub: 'Half the capital. It never catches up by 2040.' },
    { k: 'The return to the economy', h: 'Productivity gain.', items: ['$1.4T a year by 2030', '$4.3T a year by 2040', '$35.6T cumulative · 2.3× the capital'] },
    { k: 'Payback', h: 'On productivity: 2033. On producer revenue: never within the horizon.' },
    { k: 'Who keeps it', h: 'The firms that adopt AI and, through lower prices, their customers.', sub: 'Not the builders.' },
    { k: 'The pattern', h: 'Railways. Electricity. Fibre.', sub: 'Society earns the return; the builders earn a normal or poor one. Unless pricing power, or faster adoption, changes the answer.' },
    { close: true, h: 'Builders: a bet on pricing power. Adopters: a bet on execution.', sub: 'Where is your portfolio?' },
  ],
  'F-cheaper-or-competed-away': [
    { cover: true, h: 'Is the work AI does your cost, or your product?', sub: 'That one question sorts most companies.' },
    { k: 'Two axes', h: 'Every company sits somewhere on both.', items: ['How much of the cost base is exposed work', 'How much of revenue is exposed work'] },
    { k: 'Cost-exposed, revenue-protected', h: 'Winners, for a while.', items: ['Manufacturer with a big back office', 'Bank with floors of analysts', 'Hospital with claims and billing staff', 'Insurer · Logistics operator'] },
    { k: 'How long the margin lasts', h: 'Depends on adoption speed and pass-through.', items: ['Slow-adopting, regulated, fragmented sectors: years', 'Fast, transparent sectors: a few'] },
    { k: 'Revenue-exposed', h: 'The losers.', items: ['Call-centre outsourcer', 'Translation agency', 'Document-review law practice', 'Preparation-heavy accounting', 'Offshore IT services'] },
    { k: 'How bad it gets', h: 'Three things decide.', items: ['Elastic demand: volume offsets part of the price fall', 'Inelastic demand: revenue simply shrinks', 'AI-made output accepted: pricing power gone'] },
    { k: 'The third group', h: 'AI-native entrants.', sub: 'No legacy cost base, no integration bill. They take share from both.' },
    { k: 'What the model contributes, by sector', h: 'A prior, not a valuation.', items: ['Exposed share of labour cost', 'When it pays to automate', 'How far prices fall', 'How demand responds', 'Where the saving flows next'] },
    { k: 'The five diligence questions', h: 'I now ask them of every target.', items: ['Cost exposure vs revenue exposure', 'Is demand elastic?', 'Would the customer accept AI-made output?', 'Adoption speed and pass-through', 'The entrant, and the offshore model'] },
    { close: true, h: 'Which of the three is your company, or your target?', sub: 'Compare notes' },
  ],
  'G-three-waves': [
    { cover: true, h: 'Three waves, not one.', sub: 'And they run on three clocks.' },
    { k: 'Wave one · software · now', h: 'By 2030, against where they would have been.', items: ['Data scientists −10%', 'Network and systems administrators −9%', 'Computer support specialists −9%'] },
    { k: 'Why now', h: 'Software-only AI needs no factory, no permit and no fleet.' },
    { k: 'Wave two · robots and vehicles · later', big: '0.2% → 5.0%', sub: 'of task-hours, 2030 to 2040' },
    { k: 'Why later', h: 'Production ramps. Permits. Hardware cost.', sub: 'Not the software. The model’s driving fleet tracks Waymo’s real count over 2024 to 2025.' },
    { k: 'Wave three · AI-made content', h: 'Category by category.', items: ['Translation and voice first: 74% of spending by 2040', 'Video last: 8%'] },
    { k: 'Growing', h: 'The people who build and fix the machines.', items: ['Production and maintenance work', 'Work where a person is the product'] },
    { close: true, h: 'Which wave is your industry in?', sub: 'Drag the time slider' },
  ],
  'H-the-world': [
    { cover: true, h: '108 million fewer jobs, and $367 billion a year to the United States.', sub: 'The world story, ten regions' },
    { k: 'The world · 2040', big: '108M', sub: 'fewer jobs than there would have been, out of 2.95 billion · −3.7%' },
    { k: 'By region · employment vs no AI', h: 'Same clock, different lags.', items: ['United States −7.0%', 'European Union −5.8%', 'India −3.9%', 'China −1.9%'] },
    { k: 'Why the world number is smaller', h: 'India, China and the rest of Asia carry most of the weight and see the frontier later.' },
    { k: 'Where the AI income goes · 2040', h: 'More concentrated than the jobs.', items: ['United States $367B', 'China $102B', 'European Union $83B', 'Taiwan $63B'] },
    { k: 'Who pays it · $651B in 2040', h: 'Mostly employers.', items: ['65% employers replacing tasks with software', '23% consumers’ subscriptions and services', '9% tools that speed up workers', '3% AI-made content'] },
    { k: 'Biggest GDP gains', h: 'Taiwan and Korea, through chip exports.' },
    { k: 'The caveat', h: 'Outside the U.S. the occupation mix is the American one tilted by income.', sub: 'Regional differences are the mechanism, not local data. Help wanted.' },
    { close: true, h: 'Which region are you in, and does the mechanism ring true?', sub: 'Drill the map' },
  ],
  'I-the-scoreboard': [
    { cover: true, h: 'A model that cannot be wrong is worthless.', sub: 'Here is where mine is scored.' },
    { k: 'Goldman Sachs 2023', h: 'Employment effect 7.0%', sub: 'Model 5.8% · below' },
    { k: 'IMF 2024', h: 'Advanced-economy jobs exposed 60%', sub: 'Model 28% · below' },
    { k: 'Acemoglu 2024', h: 'TFP gain 0.66%', sub: 'Model 4.8% · above' },
    { k: 'Three of them are also presets', h: 'Rebuild each report’s assumptions with the same engine.', sub: 'See how much of the disagreement is data and how much is assumptions.' },
    { k: 'Backtest · hyperscaler capex', h: 'Within a few percent.', items: ['2025: observed $413B · model $400B', '2026 guidance: $725B · model $720B'] },
    { k: 'Backtest · revenue and job cuts', h: 'Within the band.', items: ['AI revenue 2025: $60B observed · $55B model', 'AI-cited cuts 2025: 55k announced · 63k model'] },
    { k: 'The honest rows', h: 'Two rows set a parameter and are marked calibration targets, not evidence.', sub: 'Over 2023 to 2026 together the model overshoots announced cuts.' },
    { close: true, h: 'Where would you push hardest?', sub: 'The Backtest view has every row' },
  ],
}

const CSS = `
@page { size: 1080px 1350px; margin: 0; }
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; }
body { font-family: -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; color: #0b0b0b; }
.slide { width: 1080px; height: 1350px; page-break-after: always; padding: 84px 84px 72px; display: flex; flex-direction: column; background: #f4f4f1; position: relative; }
.slide.cover, .slide.close { background: #0b0b0b; color: #fcfcfb; }
.slide.cover .foot, .slide.close .foot { color: #a09e97; border-color: rgba(255,255,255,0.18); }
.kicker { font-size: 30px; font-weight: 600; letter-spacing: 0.02em; text-transform: uppercase; color: #1c5cab; margin-bottom: 26px; }
.slide.cover .kicker, .slide.close .kicker { color: #86b6ef; }
h1 { font-size: 78px; line-height: 1.08; margin: 0 0 24px; font-weight: 700; letter-spacing: -0.01em; }
.slide.cover h1 { font-size: 92px; margin-top: 140px; }
.slide.close h1 { font-size: 80px; margin-top: 160px; }
.sub { font-size: 40px; line-height: 1.32; color: #52514e; margin: 0; }
.slide.cover .sub, .slide.close .sub { color: #c3c2b7; }
.big { font-size: 190px; line-height: 1; font-weight: 800; letter-spacing: -0.03em; margin: 40px 0 28px; color: #1c5cab; }
ul { list-style: none; padding: 0; margin: 12px 0 0; }
li { font-size: 42px; line-height: 1.3; padding: 18px 0 18px 44px; border-top: 1px solid rgba(11,11,11,0.12); position: relative; }
li::before { content: ""; position: absolute; left: 0; top: 36px; width: 18px; height: 18px; border-radius: 50%; background: #2a78d6; }
.body { flex: 1; display: flex; flex-direction: column; justify-content: center; }
.foot { display: flex; justify-content: space-between; font-size: 24px; color: #6f6d67; border-top: 1px solid rgba(11,11,11,0.12); padding-top: 22px; }
.cta { font-size: 34px; margin-top: 60px; color: #86b6ef; font-weight: 600; }
`

function esc(s) {
  return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
}

function slideHtml(s, i, n) {
  const cls = s.cover ? 'slide cover' : s.close ? 'slide close' : 'slide'
  let body = ''
  if (s.k) body += `<div class="kicker">${esc(s.k)}</div>`
  if (s.big) body += `<div class="big">${esc(s.big)}</div>`
  if (s.h) body += `<h1>${esc(s.h)}</h1>`
  if (s.sub) body += `<p class="sub">${esc(s.sub)}</p>`
  if (s.items) body += `<ul>${s.items.map((x) => `<li>${esc(x)}</li>`).join('')}</ul>`
  if (s.close) body += `<div class="cta">${esc(APP)} · link in the comments</div>`
  if (s.cover) body += `<div class="cta">${esc(APP)}</div>`
  return `<section class="${cls}"><div class="body">${body}</div><div class="foot"><span>${esc(FOOT)}</span><span>${i + 1} / ${n}</span></div></section>`
}

;(async () => {
  fs.mkdirSync(OUT, { recursive: true })
  const browser = await chromium.launch()
  const page = await browser.newPage({ viewport: { width: 1080, height: 1350 } })
  for (const [name, slides] of Object.entries(CAROUSELS)) {
    const html = `<!doctype html><html><head><meta charset="utf-8"><style>${CSS}</style></head><body>${slides
      .map((s, i) => slideHtml(s, i, slides.length))
      .join('')}</body></html>`
    await page.setContent(html, { waitUntil: 'load' })
    const file = path.join(OUT, `${name}.pdf`)
    await page.pdf({ path: file, preferCSSPageSize: true, printBackground: true })
    if (process.env.PREVIEW) {
      for (const i of [0, 4]) await page.locator('.slide').nth(i).screenshot({ path: path.join(process.env.PREVIEW, `${name}-${i + 1}.png`) })
    }
    console.log(name, slides.length, 'slides ->', file)
  }
  await browser.close()
})()

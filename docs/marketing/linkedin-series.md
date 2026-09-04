# LinkedIn series: AI Workforce Sim

Ten posts over three weeks, three a week, each with a carousel (PDF, in `carousels/`) or a long-form article. Every number below comes from the current baseline run (384 draws, U.S. and ten regions; the Story view shows the same figures). Links: app `https://saro-saravanan.github.io/ai-workforce-sim/`, repository `https://github.com/saro-saravanan/ai-workforce-sim`, profile `https://saro-saravanan.github.io`.

Conventions that make LinkedIn work for this material:

- First line is the whole hook; LinkedIn truncates after about 210 characters, so the first sentence must carry the post on its own.
- One idea per post. The carousel restates it in numbers; the text says why it matters.
- Carousels are PDFs, 1080 × 1350, eight to ten slides, one thought per slide, the last slide a question that invites comments.
- Post between 7:30 and 9:00 local on Tuesday to Thursday for reach; Monday and Friday posts are fine for a warm network.
- Put the link in the first comment, not the post body, and say so in the post ("link in the first comment").
- Reply to every comment in the first two hours; ask a follow-up question in each reply.
- Tag nobody in the post; mention people in comments when they have said something relevant.
- Hashtags: three to five, at the end, the same set each time so the series is findable: `#AIandWork #FutureOfWork #AIWorkforceSim #TechDueDiligence #PrivateEquity` (drop the last two on the family-oriented posts, add `#Parenting` there).

## Calendar

| Day | Post | Format | Audience | Carousel |
|---|---|---|---|---|
| Tue 1 | Why I built a model of what AI does to work | Article + carousel | Everyone | A |
| Thu 3 | Two ledgers: 13.5 million fewer jobs, 2.9 million layoffs | Post + carousel | Everyone, HR, policy | B |
| Mon 6 | The young pay first | Post + carousel | Parents, educators | C |
| Wed 8 | Pay goes up, the worker's share goes down | Post + carousel | Economists, policy, general | D |
| Fri 10 | The trillion-dollar bet | Article + carousel | PE, VC, CFOs, boards | E |
| Mon 13 | Which businesses get cheaper to run, and which get competed away | Article + carousel | PE, VC, operators | F |
| Wed 15 | Three waves, not one | Post + carousel | Everyone, robotics, operators | G |
| Fri 17 | 108 million fewer jobs in the world, and where the money goes | Post + carousel | International, policy | H |
| Mon 20 | Can you trust it? The scoreboard | Post + carousel | Analysts, sceptics | I |
| Wed 22 | What would change my mind: the open-source call | Post | Engineers, economists, data people | none |

---

## Day 1 (Tuesday). Article: Why I built a model of what AI does to work

**Hook (first line):** I have spent the last few years fretting about what AI means for my children and grandchildren. So I built a model, and I am giving it away.

**Article (about 650 words):**

Like most people, I have spent a good deal of the last few years fretting about what accelerating AI means for my children, my grandchildren, and the society they will live in. I have spent my career building software: a 401(k) platform, Fidelity's NetBenefits, the systems behind TSA PreCheck. I know what it looks like when a technology stops being a demo and starts changing who gets hired. This time it is aimed at the kind of work I do, and the kind of work I hoped they would do.

The public conversation did not help. One week the headline said half of all jobs would vanish; the next said AI would make everyone richer. Every number came from somewhere I could not see, with assumptions I could not change, and none of them agreed with each other. I could not answer the simple questions my family asked me at dinner. And in my day job, technology due diligence for private-equity and venture investors, the same questions arrived in a suit: will the capital pouring into AI earn a return, and which companies will be on the right side of it?

So I built a model. Not to predict the future, which nobody can, but to make the assumptions visible, so that when we disagree we disagree about the right things.

Here is how it works, in one paragraph. It starts from about 19,000 task statements in 831 occupations and asks of each task: can software ever do this, when does it become feasible on a capability clock fitted to measured AI progress, and does doing it pay at the wage of the person who does it now? Firms adopt when it pays, slowly in some sectors and fast in others. Automated work becomes positions never posted first and layoffs second. Cheaper output sells more, new kinds of work appear, and the gains either get spent back into the economy or pocketed. Ten regions run on the same clock. Every parameter has a source, a central value, a range and a lever.

Every number it produces is a difference between a world where AI keeps improving and a world where it stopped in 2023. That framing matters. It is not "how many jobs will there be", which depends mostly on population and growth. It is "how many fewer than there would have been", which is the part AI is responsible for.

The headline, on central assumptions for the United States: about 13.5 million fewer jobs in 2040 than there would have been, out of 194 million. Most of them are positions never offered to new entrants rather than layoffs. Real pay is about 3% higher because prices fall. The economy is about 5% larger. And the worker's share of national income falls by nearly six points. All four at once.

The range around that headline is wide, and the model says so on every finding: between 7 and 20 million fewer jobs, depending mostly on whether the productivity gains are spent back into the economy. That is partly policy, partly corporate behaviour, and partly what each of us chooses to pay for.

Three things I want to be honest about. The model is a structured set of mechanisms, not an estimated forecasting model; its ranges are ranges over its own assumptions. Outside the United States the occupation structure is the U.S. one tilted by income, so regional differences are the mechanism speaking, not local data. And the model is scored every quarter against what has already happened: firm adoption, announced AI-cited job cuts, AI industry revenue, data-centre spending. Where it misses, the page says so.

It is open source under the MIT licence. There is a two-minute tour, a story in plain language, a personal outlook for one occupation and one age, and a What-if panel where you can move any assumption and watch what follows. If you think it is wrong, the levers are there. If you can make it better, the repository is open.

Over the next three weeks I will post one finding at a time. Today: why. Link in the first comment.

**First comment:** The model: https://saro-saravanan.github.io/ai-workforce-sim/ · Why I built it, and the thirteen questions: the About page · Source: https://github.com/saro-saravanan/ai-workforce-sim

**Hashtags:** #AIandWork #FutureOfWork #AIWorkforceSim #OpenSource

**Carousel A: Why I built this** (9 slides)
1. Cover: "I fretted about what AI means for my kids. So I built a model." · sub: AI Workforce Sim, open source
2. "The headlines could not agree." Half of jobs gone / everyone richer / nothing changes. Every number from somewhere I could not see.
3. "So I made the assumptions visible." 19,000 tasks · 831 occupations · 20 sectors · 10 regions · every parameter sourced, ranged, and a lever
4. "Every number is a difference." A world where AI keeps improving, minus a world where it stopped in 2023. Not a forecast of the level of jobs.
5. "The headline, United States, 2040." 13.5 million fewer jobs than there would have been · out of 194 million · most never posted, not lost
6. "The range is the honest part." 7 to 20 million fewer, depending mostly on whether the gains are spent back into the economy.
7. "Thirteen questions." Will there be work for my grandchildren · Who pays first · Who keeps the gains · Will the capital pay back · Which businesses win
8. "It keeps score." Checked every quarter against firm adoption, announced job cuts, AI revenue and data-centre spending. Where it misses, it says so.
9. Close: "Open source. Take the two-minute tour. What question would you add?" · link

---

## Day 3 (Thursday). Post: Two ledgers

**Hook:** 13.5 million fewer jobs by 2040, and only 2.9 million of them are layoffs. The rest are jobs that quietly never get posted.

**Post (about 220 words):**

There is a world of difference between a layoff and a position that is never offered. The first hits someone with a mortgage. The second hits someone with a diploma and no first job. Most of the public argument about AI and work conflates them, and that is why it goes nowhere.

The model keeps two ledgers apart. The jobs ledger counts positions: about 13.5 million fewer exist in the United States in 2040 than there would have been. The people ledger counts people: over the period about 11 million found the job they had, or would have had, gone. Of those, 7.8 million are positions never offered to new entrants and 2.9 million are layoffs. About 9.2 million found other work, about a million left the workforce, and 137,000 are unemployed in 2040. Extra unemployment peaks at about half a million in 2034.

The two ledgers differ because someone who finds other work fills a position that would otherwise have gone to someone else.

Why it matters: if the cut comes through attrition and hiring freezes rather than layoffs, it never shows up as a headline, the unemployment rate barely moves, and the cost lands on the people who cannot yet vote with their feet. The layoff share is the least certain number in the model, and it is fitted to what employers have actually announced.

Which ledger does your organisation watch? Link in the first comment.

**Hashtags:** #AIandWork #FutureOfWork #AIWorkforceSim #HR

**Carousel B: Two ledgers** (8 slides)
1. Cover: "13.5 million fewer jobs. 2.9 million layoffs. Those are not the same number."
2. "The jobs ledger counts positions." 13.5M fewer in 2040 than there would have been · U.S., central assumptions
3. "The people ledger counts people." 11.0M found the job they had, or would have had, gone
4. "How they lost it." 7.8M positions never offered to new entrants · 2.9M layoffs · 0.3M gig and freelance hours cut
5. "Where they went." 9.2M found other work · 1.0M left the workforce · 137,000 unemployed in 2040
6. "The peak." Extra unemployment tops out at about 489,000 in 2034. The unemployment rate barely moves. The cost is somewhere else.
7. "Why the ledgers differ." Someone who finds other work fills a position that would otherwise have gone to someone else.
8. Close: "If your company cuts through attrition, it will never make the news. Who is counting? Link in comments."

---

## Day 6 (Monday). Post: The young pay first

**Hook:** Workers under 25 carry 31% of the jobs that go missing to AI, while their parents are largely protected. What do you tell a seventeen-year-old?

**Post (about 230 words):**

This is the question I care about most, and the model's answer is uncomfortable.

If employers cut through attrition and hiring freezes rather than layoffs, which is what the announcements so far say they do, the shortfall lands on the people trying to get their first job. In the model, workers under 25 carry 31% of the jobs that go missing by 2040, about 3% of their group's jobs, against 1% for people aged 25 to 44 and 1% for those over 55. Workers without a degree lose about 2% of their jobs while graduates are barely affected; the bottom half of earners lose about 2% while the top tenth is barely touched.

Incumbents are mostly safe. Entrants are not. That is the practical advice hidden in the numbers.

What changes it is how employers cut. If they cut through layoffs instead, the total is the same, but it moves from entrants to incumbents and the unemployment peak rises. The model runs both as variants.

What I tell the seventeen-year-old: the broad kinds of work that are exposed are fairly robust across data sources, but which exact occupation ranks where is not. Aim at the work where a person is the product, at the work that builds and runs the machines, and at the first job, because the first job is where the risk now sits.

The personal outlook in the app narrows the whole model to one occupation and one age. Link in the first comment.

**Hashtags:** #AIandWork #FutureOfWork #AIWorkforceSim #Parenting #Education

**Carousel C: The young pay first** (8 slides)
1. Cover: "The young pay first." Under-25s carry 31% of the jobs AI takes away.
2. "How the cut arrives." Employers cut through attrition and hiring freezes first, layoffs second. The people who cannot yet vote with their feet pay.
3. "By age, share of the shortfall." Under 25: 31% · 25 to 44 · 45 to 54 · 55 and over (bars)
4. "By age, share of the group's own jobs." Under 25: about 3% · 25 to 44: about 1% · 55 and over: about 1%
5. "By education and income." No degree: about 2% of jobs · Graduates: barely affected · Bottom half of earners: about 2% · Top tenth: barely touched
6. "Incumbents are mostly safe. Entrants are not." That is the practical advice hidden in the numbers.
7. "What changes it." If employers cut through layoffs instead, the total is the same; it moves from entrants to incumbents, and unemployment peaks higher.
8. Close: "What are you telling the seventeen-year-old in your life? Try their outlook: link in comments."

---

## Day 8 (Wednesday). Post: Pay goes up, the worker's share goes down

**Hook:** Real pay up 3%. The economy 5% larger. Workers' share of income down almost six points. All three at once, and the model shows how.

**Post (about 200 words):**

Both sides of the AI argument are right, and that is the problem.

In the model's central run for the United States, prices fall about 3% by 2040 because AI lowers the cost of a large share of office and analytical work. Real pay rises about 3% as a result, roughly $2,000 a year for someone on $60,000, with a likely range of 2% to 6%. The economy is about 5% larger.

And the worker's share of national income falls by 5.8 points. The gains are real, and they go disproportionately to owners.

What decides the split is how much of the cost saving reaches prices. If firms keep it as margin, pay rises less and the owner share rises more. In the model that is a lever, and it is the lever that separates the optimists from the pessimists more than any other. The optimists assume high pass-through; the pessimists assume the gains are pocketed.

So the question is not "will AI make us richer". On average it does. The question is who "us" turns out to be, and that is partly a policy choice.

Link in the first comment.

**Hashtags:** #AIandWork #FutureOfWork #AIWorkforceSim #Economics

**Carousel D: Pay up, share down** (8 slides)
1. Cover: "Pay goes up. The worker's share goes down. Both are true."
2. "Prices." About 3% lower by 2040 than they would have been
3. "Real pay." About 3% higher · likely between 2% and 6% · about $2,000 a year on a $60,000 salary
4. "The economy." About 5% larger than it would have been
5. "The worker's share of income." Down 5.8 points. The gains are real, and they go disproportionately to owners.
6. "What decides it." How much of the cost saving reaches prices. Kept as margin: pay rises less, the owner share rises more.
7. "Optimists and pessimists disagree about one lever." Pass-through. Move it in the What-if panel and watch the split change.
8. Close: "Will AI make us richer? On average, yes. Who is 'us'? Link in comments."

---

## Day 10 (Friday). Article: The trillion-dollar bet

**Hook:** The four largest cloud companies spent $413 billion on AI infrastructure in 2025 and have guided to $732 billion for 2026. Here is what a model says about whether it pays back, and for whom.

**Article (about 600 words):**

If you invest for a living, the question underneath every AI conversation is simpler than the technology: does the capital earn a return, and who gets it?

The money going in is not in dispute. The four largest cloud companies spent about $413 billion on data centres, chips and power in 2025 and have guided to about $732 billion for 2026. My model takes that path as given and carries it to about $1.05 trillion a year by 2030, flat after: roughly $15.6 trillion over 2024 to 2040.

The money coming back to the builders is where the argument starts. In the model, employers and consumers spend about $95 billion a year on AI in 2026, about $500 billion by 2030 and about $630 billion by 2040: roughly $7.7 trillion over the period, half of the capital spent. Producers' cumulative revenue never catches up with cumulative capex by 2040. The revenue path is fitted to the industry's reported 2025 revenue and 2026 run rates, so this is not a pessimistic assumption; it is the industry's own numbers extended along the model's adoption curve.

The return to the economy is a different story. The same AI adds about $1.4 trillion a year of productivity gain by 2030 and $4.3 trillion by 2040 across the ten modelled regions: about $35.6 trillion cumulative, 2.3 times the capital spent. On productivity alone the capex is repaid by 2033. Counting the data-centre build itself as output, the GDP effect is about $3.9 trillion a year by 2040.

But most of that gain goes to the firms that adopt AI and, through lower prices, to their customers. Not to the companies that built the capacity.

That is the railway pattern, the electricity pattern, and the fibre pattern: society earns most of the return and the builders earn a normal or poor one. Investors in 1999 were right about the internet and wrong about who would capture it.

Three things can close the gap for the builders, and each is a lever in the model. AI revenue far above what labour substitution alone justifies: consumer and advertising businesses, or prices held well above token cost. Adoption faster than the central pace: the Seba/RethinkX presets are that case, and the model runs them. Or investors accepting that the return is social, which is what the railway investors eventually accepted.

The model cannot say which. It can say that the productivity return is real and large, that it lands with adopters, and that it arrives about a decade after the capital.

What that means for a portfolio, in my view: the builders are a bet on pricing power; the adopters are a bet on execution; and the companies whose product is the work being automated are exposed on the revenue line regardless of who wins the infrastructure race. I will post the framework I use to sort companies into those buckets on Monday.

The investment section of the Story view carries the full table by year. Link in the first comment.

**Hashtags:** #AIandWork #AIWorkforceSim #TechDueDiligence #PrivateEquity #VentureCapital

**Carousel E: The trillion-dollar bet** (10 slides)
1. Cover: "A trillion dollars a year into data centres. Who gets the return?"
2. "The money going in." $413B in 2025 · $732B guided for 2026 · about $1.05T a year by 2030 · four companies
3. "Over 2024 to 2040." About $15.6 trillion of capital
4. "The money coming back to the builders." $95B in 2026 · about $500B by 2030 · about $630B by 2040
5. "Cumulative." $7.7 trillion of producer revenue. Half the capital. It never catches up by 2040.
6. "The return to the economy." $1.4T a year of productivity gain by 2030 · $4.3T by 2040 · $35.6T cumulative · 2.3× the capital
7. "Payback." On productivity, the capital is repaid by 2033. On producer revenue, never within the horizon.
8. "Who keeps it." The firms that adopt AI and, through lower prices, their customers. Not the builders.
9. "The pattern." Railways. Electricity. Fibre. Society earns the return; the builders earn a normal or poor one. Unless pricing power, or faster adoption, changes the answer.
10. Close: "Builders: a bet on pricing power. Adopters: a bet on execution. Where is your portfolio? Link in comments."

---

## Day 13 (Monday). Article: Which businesses get cheaper to run, and which get competed away

**Hook:** The first question I now ask of any company in diligence: is the work AI does its cost, or its product?

**Article (about 700 words):**

Every company sits somewhere on two axes: how much of its cost base is the kind of work AI is learning to do, and how much of its revenue is that work. Where it sits tells you most of what you need to know about the next decade.

AI lowers the cost of a particular kind of work: office and analytical work now, physical work later. The model I built puts a number on that by sector, from the BEA input-output tables and the OEWS occupation data: what share of each sector's labour cost is exposed, when automating it becomes feasible and profitable at that sector's wages, how far the sector's prices fall, how demand responds, and how much of the saving flows on to the sectors that buy from it.

**Cost-exposed, revenue-protected companies are the winners, for a while.** A manufacturer with a large back office. A bank with floors of analysts. A hospital with claims and billing staff. An insurer. A logistics operator. Their product is not the exposed work, but a lot of their cost is. Their costs fall and their margins widen. How long they keep the margin depends on two things the model carries as levers: how fast competitors adopt, which varies by sector and firm size, and how much of the saving the market forces through to prices. In slow-adopting, regulated or fragmented sectors the margin lasts years. In fast, transparent ones it is competed away in a few.

**Revenue-exposed companies are the losers, and the more of their revenue is billable exposed work, the harder they fall.** A call-centre outsourcer. A translation agency. A law firm billing hours for document review. An accounting practice built on preparation work. An offshore IT-services firm. Their product is the work AI now does, and their price falls faster than their cost, because their customers can also buy the AI directly. Two things decide how bad it gets. If demand for the output is elastic, so more gets bought when it is cheaper, as with software, design and analysis, volume can offset part of the price fall. If it is not, and a document reviewed once is reviewed once, revenue simply shrinks. And if customers accept AI-made output as a substitute for human-made output, which the model tracks category by category, pricing power is gone, not merely reduced.

**The third group takes share from both.** AI-native entrants arrive without a legacy cost base or an integration bill, built to sell the cheaper output at the lower price from day one. They matter most in exactly the markets where incumbents are revenue-exposed.

None of this is a company valuation. It is a sector-level prior, and the diligence still has to be done. But it changes the questions I ask, and I now ask them of every target:

1. What fraction of the cost base is exposed work, and what fraction of revenue?
2. Is demand for the product elastic, or is a unit a unit?
3. Would the customer accept AI-made output as a substitute?
4. How fast does this sector adopt, and how much of the saving does its market pass through?
5. Who is the AI-native entrant, and is the offshore delivery model an asset or a liability?

A company that answers those well is on the right side of this. One that cannot is not, however good its last three years look.

I do this work for private-equity and venture investors as technology due diligence, and as a fractional CTO for the companies on the receiving end. If any of the five questions above is one you are facing on a live deal or in a portfolio company, I would be glad to compare notes.

The sector numbers are in the Economy and Occupations views, and the levers in the What-if panel. Link in the first comment.

**Hashtags:** #AIandWork #AIWorkforceSim #TechDueDiligence #PrivateEquity #FractionalCTO

**Carousel F: Cheaper to run, or competed away?** (10 slides)
1. Cover: "Is the work AI does your cost, or your product? That one question sorts most companies."
2. "Two axes." How much of the cost base is exposed work · How much of revenue is exposed work
3. "Cost-exposed, revenue-protected: winners, for a while." Manufacturer with a big back office · Bank · Hospital · Insurer · Logistics
4. "How long the margin lasts." Slow-adopting, regulated, fragmented sectors: years · Fast, transparent sectors: a few
5. "Revenue-exposed: the losers." Call-centre outsourcer · Translation agency · Document-review law practice · Preparation-heavy accounting · Offshore IT services
6. "How bad it gets." Elastic demand: volume offsets part of the price fall · Inelastic demand: revenue simply shrinks · AI-made output accepted: pricing power gone
7. "The third group." AI-native entrants. No legacy cost base, no integration bill. They take share from both.
8. "What the model contributes." Exposed share of labour cost by sector · When it pays to automate · How far prices fall · How demand responds · Where the saving flows next
9. "The five diligence questions." Cost vs revenue exposure · Elastic demand? · AI output accepted? · Adoption speed and pass-through · The entrant and the offshore model
10. Close: "Which of the three is your company, or your target? Link in comments."

---

## Day 15 (Wednesday). Post: Three waves, not one

**Hook:** Data scientists down 10% by 2030. Robots at 0.2% of task-hours in 2030 and 5% by 2040. This is a 2027 story and a 2040 story, and getting the sequence right matters more than any single number.

**Post (about 210 words):**

People argue about AI and jobs as if it were one event. The model says it is three, on three clocks.

Wave one is now. Office and analytical work is being reshaped: in the model, data scientists, network and systems administrators and computer support specialists are each down 9 to 10% by 2030 against where they would have been. Software-only AI needs no factory and no permit.

Wave two is later. Robots and self-driving vehicles have to be manufactured, approved and paid for. The model's embodied work is 0.2% of task-hours in 2030 and 5% by 2040, held back by production ramps, permits and hardware cost, not by the software. The model's driving fleet runs a little ahead of Waymo's actual vehicle count over 2024 to 2025, which is the kind of check it is built to take.

Wave three is quieter. AI-made content spreads category by category: translation and voice first, at about three quarters of spending by 2040, video last at under a tenth.

Growing, meanwhile: the people who build and fix the machines, and the work where a person is the product.

Drag the time slider in the app and watch the three arrive. Link in the first comment.

**Hashtags:** #AIandWork #FutureOfWork #AIWorkforceSim #Robotics

**Carousel G: Three waves** (8 slides)
1. Cover: "Three waves, not one. And they run on three clocks."
2. "Wave one: software, now." Data scientists −10% · Network and systems administrators −9% · Computer support specialists −9% · by 2030, against where they would have been
3. "Why now." Software-only AI needs no factory, no permit and no fleet.
4. "Wave two: robots and vehicles, later." 0.2% of task-hours in 2030 · 5.0% by 2040
5. "Why later." Production ramps. Permits. Hardware cost. Not the software. The model's driving fleet tracks Waymo's real count over 2024 to 2025.
6. "Wave three: AI-made content, category by category." Translation and voice first: 74% of spending by 2040 · Video last: 8%
7. "Growing." Production and maintenance work · the people who build and fix the machines · work where a person is the product
8. Close: "Which wave is your industry in? Drag the slider: link in comments."

---

## Day 17 (Friday). Post: 108 million, and where the money goes

**Hook:** Across ten regions, about 108 million fewer jobs by 2040 than there would have been. The United States collects $367 billion a year of the AI income. India and China carry the most people.

**Post (about 220 words):**

The world story is different from the American one, and the model runs both.

Across the ten modelled regions, about 108 million fewer jobs exist in 2040 than there would have been, out of 2.95 billion: 3.7% against 7.0% for the United States alone. India, China and the rest of Asia carry most of the world's weight and see the frontier later, so the percentage is smaller and the headcount is larger. The European Union sits between, at 5.8%.

The money is more concentrated than the jobs. By 2040 the United States collects about $367 billion a year of AI income, the makers of models, the data centres and the chips; China about $102 billion, the EU about $83 billion, Taiwan about $63 billion. The largest GDP gains are in Taiwan and Korea through chip exports. Of the $651 billion spent on AI worldwide in 2040, about two thirds is employers replacing tasks with software and about a quarter is consumers paying for AI subscriptions and services.

An honest caveat: outside the United States the occupation structure in the model is the American one tilted by income, so regional differences are the mechanism speaking, not local data. That is the fixture I would most like help replacing.

The map in the app drills from world to region to state. Link in the first comment.

**Hashtags:** #AIandWork #FutureOfWork #AIWorkforceSim #GlobalEconomy

**Carousel H: The world** (9 slides)
1. Cover: "108 million fewer jobs, and $367 billion a year to the United States."
2. "The world, 2040." 108M fewer jobs than there would have been · out of 2.95 billion · −3.7%
3. "By region, employment vs no AI." United States −7.0% · European Union −5.8% · India −3.9% · China −1.9%
4. "Why the world number is smaller." India, China and the rest of Asia carry most of the weight and see the frontier later.
5. "Where the AI income goes, 2040." United States $367B · China $102B · European Union $83B · Taiwan $63B
6. "Who pays it." $651B spent on AI worldwide in 2040 · 65% employers replacing tasks · 23% consumers' subscriptions · 9% tools that speed up workers · 3% AI-made content
7. "Biggest GDP gains." Taiwan and Korea, through chip exports.
8. "The caveat." Outside the U.S. the occupation mix is the American one tilted by income. Regional differences are the mechanism, not local data. Help wanted.
9. Close: "Which region are you in, and does the mechanism ring true? Link in comments."

---

## Day 20 (Monday). Post: Can you trust it? The scoreboard

**Hook:** Goldman said 7%. The IMF said 60% exposed. Acemoglu said 0.66%. My model lands below Goldman, below the IMF, above Acemoglu, and it prints the misses.

**Post (about 240 words):**

A model that cannot be wrong is worthless. So mine keeps a scoreboard of named public claims beside its own central value, and a backtest against what has already happened.

The scoreboard, as of the current run. Goldman Sachs 2023 put the developed-economy employment effect at about 7%; the model's comparable number is 5.8%, below. The IMF in 2024 said about 60% of advanced-economy jobs are exposed; the model's comparable exposure is 28%, below. Acemoglu's 2024 paper put the TFP gain at 0.66%; the model says 4.8%, above. RethinkX's claims about self-driving fleets and drivers come out far above the model.

Two of those are also presets: the model can rebuild Goldman's, the IMF's and Acemoglu's assumptions with its own engine, so you can see how much of the disagreement is data and how much is assumptions.

The backtest. Hyperscaler capex: 2025 observed $413 billion, model $400 billion; 2026 guidance $725 billion, model $720 billion. AI industry revenue 2025: observed $60 billion, model $55 billion. Announced AI-cited job cuts in 2025, by Challenger's count: about 55,000 observed, model 63,000. The model is also honest that two of those rows were used to fit a parameter and are marked as calibration targets rather than evidence, and that it overshoots announced job cuts across 2023 to 2026 taken together.

Where would you push hardest? Link in the first comment.

**Hashtags:** #AIandWork #AIWorkforceSim #Forecasting #Economics

**Carousel I: The scoreboard** (9 slides)
1. Cover: "A model that cannot be wrong is worthless. Here is where mine is scored."
2. "Named claims vs the model." Goldman Sachs 2023: 7.0% · model 5.8% (below)
3. "IMF 2024." 60% of advanced-economy jobs exposed · model 28% (below)
4. "Acemoglu 2024." TFP gain 0.66% · model 4.8% (above)
5. "Three of them are also presets." Rebuild each report's assumptions with the same engine, and see how much of the disagreement is data and how much is assumptions.
6. "Backtest: capex." 2025: observed $413B, model $400B · 2026 guidance: $725B, model $720B
7. "Backtest: revenue and cuts." AI revenue 2025: $60B observed, $55B model · AI-cited job cuts 2025: 55k announced, 63k model
8. "The honest rows." Two rows set a parameter and are marked calibration targets, not evidence. Over 2023 to 2026 together the model overshoots announced cuts.
9. Close: "Where would you push hardest? The Backtest view has every row. Link in comments."

---

## Day 22 (Wednesday). Post: What would change my mind

**Hook:** Every finding in my model lists what would change it. Here is what would change mine, and where I need help.

**Post (about 200 words):**

Three weeks of findings, and the most useful replies have been the ones that said "that assumption is wrong". Good. That is the point of publishing the levers.

What would move the headline most, in order: whether the productivity gains are spent back into the economy or pocketed; how much of the cost saving reaches prices; how fast employers cut ahead of attrition; and the domain-transfer discount that says how much of software's measured progress carries to non-software work. Each is a lever, each has a source and a range, and each is one afternoon's argument away from a better value.

Where I need help, concretely: a human pass over the 120-statement classifier audit; occupation data for regions outside the United States, which currently use the American mix tilted by income; sector adoption frictions from the Census BTOS cuts; and any published estimate the scoreboard does not yet carry.

The code, the data pipeline and the scenario files are open source under MIT. If you are an economist, a data person or an engineer with an afternoon, the repository is open and I will answer every issue.

Link in the first comment. Thank you for reading along.

**Hashtags:** #AIandWork #AIWorkforceSim #OpenSource #Economics

---

## Reuse

- Each carousel's last slide is a question; pin the best reply.
- Repost the Day 13 article to the profile page and to relevant PE and CTO groups a week later with a one-line update ("three deals since I posted this used these five questions").
- The Day 1 article doubles as the newsletter issue if you run one.
- Quote-post your own Day 3 carousel on Day 6 ("this is why").

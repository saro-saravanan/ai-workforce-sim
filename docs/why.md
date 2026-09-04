# Why I built this

*Saro Saravanan, September 2026*

Like most people, I have spent a good deal of the last few years fretting about what accelerating AI means for my children, my grandchildren, and the society they will live in. I have spent my career building software, and I know what it looks like when a technology stops being a demo and starts changing who gets hired. This time the technology is aimed at the kind of work I do, and the kind of work I hoped they would do.

The public conversation did not help. One week the headline said half of all jobs would vanish; the next it said AI would make everyone richer. Every number came from somewhere I could not see, with assumptions I could not change, and none of them agreed with each other. I found I could not answer the simple questions my family asked me at dinner. And in my day job, technology due diligence for private-equity and venture investors, the same questions arrived in a suit: will the capital pouring into AI earn a return, and which of the companies we are looking at will be on the right side of it?

So I built a model. Not to predict the future, which nobody can, but to make the assumptions visible, so that when we disagree we disagree about the right things. Every number it produces is a difference between a world where AI keeps improving and a world where it stopped in 2023. Every parameter has a source, a range and a lever. When the model is wrong, and it will be, you can see where.

It does not make one prediction. It produces projections under different **scenarios** and **presets**, and shows the range between them. A scenario changes the world the model runs in: the baseline with every assumption at its central value; a what-if in which the EU AI Act is delayed two years and an open-weights frontier model arrives from China in 2027; policy runs that add a retraining subsidy, a $500-a-month basic income paid for by an income-tax surcharge, wage insurance, or a 36-hour week; variants in which employers cut through layoffs rather than attrition, or wages fall to clear the market. A preset rebuilds someone else's published estimate with the same engine, so you can see how much of the disagreement between reports is the data and how much is the assumptions: Acemoglu's 2024 paper, Goldman Sachs 2023, the IMF's 2024 study, and Tony Seba's RethinkX disruption thesis, which the model carries as a named future rather than a forecast. Every one of them is a JSON file in `scenarios/`, and the app's About page describes each.

These are the questions I have been trying to answer.

## The questions

**1. Will there be work for my children and grandchildren, and what kind?**
Not "will jobs exist", which is too easy to answer with yes, but how many fewer than there would have been, in which occupations, and whether the work that remains is the kind a person can build a life on. *The first finding on the Story view, and the Occupations view.*

**2. Do the jobs disappear in a crash, or do they quietly stop being offered?**
There is a world of difference between a layoff and a position that is never posted. The first hits someone with a mortgage; the second hits someone with a diploma and no first job. The model keeps those two ledgers apart on purpose. *The second finding, and the Flows view.*

**3. Who pays first: the people in jobs today, or the ones trying to get their first one?**
This is the question I care about most. If employers cut through attrition rather than layoffs, the young carry the shortfall while their parents are largely protected. That changes what advice a parent should give. *The third finding, and the Cohorts view.*

**4. If AI makes everything cheaper, do we get richer, and who keeps the gains?**
Prices fall, real pay can rise, and at the same time the worker's share of national income can shrink. All three can be true at once, and the model shows how. *The fourth finding, and the Economy view.*

**5. When? Is this a 2027 story or a 2040 story?**
Office and analytical work is being reshaped now. Robots and self-driving vehicles have to be manufactured, approved and paid for, which takes years. Getting the sequence right matters more than getting any single number right. *The fifth finding, the AI Supply view and the time scrubber.*

**6. Where does the money go, and which countries come out ahead?**
Someone collects the revenue from all of this: the model makers, the data centres, the chip makers. The regions are not affected equally, and the map shows who gains and who loses. *The sixth finding, and the Map.*

**7. Will the trillion dollars a year going into data centres ever pay back, and for whom?**
The four largest cloud companies spent about $400 billion on data centres, chips and power in 2025 and have guided to over $700 billion for 2026; the model carries that path past a trillion a year. On its central assumptions, the producers' revenue never catches up with the capital by 2040, while the productivity gain to the economy repays it by the early 2030s and lands with the firms that adopt AI and, through lower prices, their customers, not with the builders. That is the railway, electricity and fibre pattern: society earns the return and the builders earn a normal or poor one. Faster adoption, or prices held well above token cost, changes the answer, and both are levers. *Investment versus returns, on the Story view.*

**8. For an investor or an operator: which businesses get cheaper to run, and which get competed away?**
It depends on three things about the company: what it buys, what it sells, and how fast prices in its market move. AI lowers the cost of a particular kind of work, mostly office and analytical work now and physical work later. Every company sits somewhere on two axes: how much of its cost base is that work, and how much of its revenue is that work.

Cost-exposed, revenue-protected companies are the winners, for a while. A manufacturer with a large back office, a bank with floors of analysts, a hospital with claims and billing staff, an insurer, a logistics operator: their product is not the exposed work, but a lot of their cost is. Their costs fall and their margins widen. How long they keep the margin depends on how fast competitors adopt and how much of the saving the market forces through to prices; the model carries both as levers (adoption friction by sector and firm size, and pass-through). In slow-adopting, regulated or fragmented sectors the margin lasts years; in fast, transparent ones it is competed away in a few.

Revenue-exposed companies are the losers, and the more of their revenue is billable exposed work, the harder they fall. A call-centre outsourcer, a translation agency, a law firm billing hours for document review, an accounting practice built on preparation work, an offshore IT-services firm: their product is the work AI now does. Their price falls faster than their cost, because their customers can also buy the AI directly. Two things decide how bad it gets. If demand for the output is elastic (more gets bought when it is cheaper: software, design, analysis), volume can offset part of the price fall; if it is not (a document reviewed once is reviewed once), revenue simply shrinks. And if customers accept AI-made output as a substitute for human-made output, which the model tracks category by category, the pricing power is gone, not merely reduced.

The third group takes share from both: AI-native entrants that arrive without a legacy cost base or an integration bill, and are built to sell the cheaper output at the lower price from day one. The model lets them in as a parameter, and they matter most in exactly the markets where incumbents are revenue-exposed.

What the model contributes is a number for each side, by sector: the share of labour cost that is exposed, when it becomes feasible and profitable to automate at that sector's wages, how far the sector's prices fall, how demand responds, and how much of the saving flows on to the sectors that buy from it through the input-output table. It is a sector-level prior, not a company valuation; the diligence still has to be done. But it changes the questions I ask. What fraction of the cost base is exposed work, and what fraction of revenue? Is demand for the product elastic? Would the customer accept AI-made output? How fast does this sector adopt, and how much of the saving does its market pass through? Who is the AI-native entrant, and is the offshore delivery model an asset or a liability? A company that answers those well is on the right side of this; one that cannot is not, however good its last three years look. *The Economy and Occupations views, and the sector levers in What if.*

**9. How much of this is a choice, and how much is coming regardless?**
The single biggest swing in the model is whether the productivity gains are spent back into the economy or pocketed. That is partly policy, partly corporate behaviour, and partly what each of us decides to pay for. *The seventh finding, and the named futures.*

**10. What could a government actually do that helps, and what would it cost?**
Retraining subsidies, wage insurance, a basic income, a shorter working week: each is a scenario you can run against the baseline, with its price tag and its financing. *The policy runs on the Story view, and the What if panel.*

**11. What should I tell a seventeen-year-old choosing what to study?**
The honest answer is that the deciles are stable and the individual ranks are not: which broad kinds of work are exposed is fairly robust across data sources, which exact occupation ranks where is not. *Your outlook, one occupation and one age at a time.*

**12. Can any of this be trusted, and how would we know when it is wrong?**
A model that cannot be wrong is worthless. This one is scored every quarter against what has already happened: firm adoption, announced AI-cited job cuts, AI industry revenue, data-centre spending. Where it misses, the page says so. *The Backtest view, and the ranges and confidence marks on every finding.*

**13. What would change my mind?**
Every finding lists what would move it. If you think the model is wrong, the levers are there: change the assumption and see what follows. That is the whole point.

## What I hope happens

I do not have the answers. I have a set of mechanisms, stated in the open, that anyone can inspect, argue with and improve. If this helps one family have a calmer and better-informed conversation about the future, or one policymaker ask a sharper question, it has done its job. If you can make it better, the repository is open and I would be glad of the help.

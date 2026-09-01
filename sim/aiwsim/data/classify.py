r"""Keyword-rule classifiers over O*NET task text (tag ``E`` — estimated; Phase 1 placeholders).

These produce the four static task attributes of spec §2.2 that Phase 1 cannot yet take from
O*NET Work Context / GWA data:

* ``modality``          one of ``software`` (software/analytical), ``other_cognitive``,
                        ``interpersonal``, ``physical``
* ``presence``          presence requirement pi_k in [0, 1]
* ``use_case``          EU AI Act class: ``high_risk`` (Annex III families), ``transparency``
                        (content generation facing the public, Art. 50), ``unregulated``
* ``consequence_high``  0/1, proxy for O*NET Work Context "Consequence of Error"

Rules are plain tables of ``(regex, value)`` pairs, compiled case-insensitively.  The rule tables
are the documentation: read ``MODALITY_RULES``, ``PRESENCE_UP``, ``PRESENCE_DOWN``,
``USE_CASE_RULES`` and ``CONSEQUENCE_RULES`` below.

Decision logic
--------------
modality
    Count the rules that match for each class; take the class with the most hits.  Ties are
    broken in the order physical > interpersonal > software.  No hits -> ``other_cognitive``.
presence
    Start from a base by modality (``PRESENCE_BASE``), add ``PRESENCE_STEP`` per matching
    ``PRESENCE_UP`` rule, subtract ``PRESENCE_STEP`` per matching ``PRESENCE_DOWN`` rule, clip to
    [0, 1], round to 2 decimals.
use_case
    First class with a matching rule in the order high_risk > transparency; else ``unregulated``.
    High-risk families follow Annex III: biometrics, critical-infrastructure safety, education
    access/assessment, recruitment/selection, worker management and evaluation, creditworthiness
    and insurance risk, essential-services eligibility and emergency dispatch, law enforcement,
    migration/asylum/border, administration of justice.
consequence_high
    1 if ``use_case == high_risk`` or any ``CONSEQUENCE_RULES`` regex matches (medical, safety,
    legal/financial, vulnerable persons), else 0.

These rules will be replaced by O*NET Work Context items (presence, consequence of error) and GWA
mappings (modality) on the real ingest (``aiwsim.data.ingest.onet``).  They are deliberately
simple; ``distribution()`` prints the class shares so a reviewer can eyeball them.
"""

from __future__ import annotations

import re
from collections import Counter

import polars as pl

MODALITIES = ("software", "other_cognitive", "interpersonal", "physical")
USE_CASES = ("high_risk", "transparency", "unregulated")
CLASSIFIER_VERSION = "keyword-rules v1 (E)"

_F = re.IGNORECASE

# ----------------------------------------------------------------------------------------------
# Modality: (regex, class).  Each matching rule adds one vote for its class.
# ----------------------------------------------------------------------------------------------
MODALITY_RULES: list[tuple[str, str]] = [
    # --- physical ---------------------------------------------------------------------------
    ((r"\b(lift|lifts|lifting|carry|carries|carrying|haul\w*|load|loads|loading|unload\w*|stack\w*|"
     r"shovel\w*|dig|digs|digging|climb\w*|crawl\w*|kneel\w*|push|pushes|pushing|pull|pulls|pulling)\b"),
     "physical"),
    ((r"\b(operat\w*|driv(e|es|ing)|steer\w*|maneuver\w*|adjust\w*|set up|position\w*|align\w*|"
     r"attach\w*|connect\w*|tend\w*|feed\w*|calibrat\w*|lubricat\w*|dismantl\w*)\b[^.;]{0,40}\b"
     r"(equipment|machinery|machines?|tools?|instruments?|apparatus|vehicles?|trucks?|buses|"
     r"forklifts?|cranes?|tractors?|engines?|pumps?|valves?|conveyors?|presses?|furnaces?|ovens?|"
     r"kilns?|looms?|saws?|drills?|lathes?|hoists?|boilers?|turbines?|generators?|aircraft|"
     r"locomotives?|boats?|ships?|vessels?)\b"),
     "physical"),
    ((r"\b(repair(s|ed|ing)?|install(s|ed|ing)?|assembl(e|es|ed|ing)|disassembl\w*|weld\w*|solder\w*|fabricat\w*|grind\w*|"
     r"polish\w*|plaster\w*|rivet\w*|hammer\w*|caulk\w*|braz(e|es|ing)|mount\w*|unpack\w*|"
     r"wrap\w*|bottl(e|es|ing)|shelv(e|es|ing)|wash\w*|scrub\w*|mop\w*|sweep\w*|vacuum\w*|"
     r"clean\w*|disinfect\w*|steriliz\w*|sanitiz\w*|paint\w*|sand\w*|spray\w*|glue|gluing|"
     r"bolt\w*|screw\w*|fasten\w*|nail\w*|splice\w*|thread\w*|wire|wiring)\b"),
     "physical"),
    ((r"\b(hand tools|power tools|by hand|manually|manual labor|physical(ly)?|heavy objects|"
     r"ladders?|scaffold\w*|harness\w*|protective (gear|clothing|equipment))\b"),
     "physical"),
    ((r"\b(lift|move|position|transfer|bathe|bath|feed|dress|turn|transport|restrain)\w*\b"
     r"[^.;]{0,30}\b(patients?|residents?|animals?|livestock|cattle|horses?)\b"),
     "physical"),
    ((r"\bdeliver\w*\b(?!\s+(a |an |the )?(lecture|presentation|speech|talk|training|sermon|course|"
     r"instruction|address|program))"), "physical"),
    ((r"\b(transport\w*|tow\w*|walk\w*|patrol\w*|guard\w*|escort\w*|direct traffic|fight fires?|"
     r"extinguish\w*|rescu(e|es|ing))\b"), "physical"),
    ((r"\b(plant(s|ed|ing)? (seeds?|crops?|trees?|seedlings?|bulbs?|flowers?|vegetables?)|prun(e|es|ing)|harvest\w*|mow\w*|irrigat\w*|fertiliz\w*|herd\w*|milk\w*|"
     r"groom\w*|shear\w*|slaughter\w*|butcher\w*|cook\w*|bak(e|es|ing)|fry\w*|grill\w*|chop\w*|"
     r"slic(e|es|ing)|garnish\w*|sew\w*|stitch\w*|knit\w*|weav(e|es|ing)|launder\w*|iron\w*)\b"),
     "physical"),
    ((r"\b(construct(s|ed|ing)?|erect(s|ed|ing)?|demolish\w*|excavat(e|es|ed|ing)|pav(e|es|ing)|shingl\w*|"
     r"lay(s|ing)? (bricks?|pipes?|tile|tiles|carpet|flooring|cable|track)|pipe ?fitt\w*|trench(es|ed|ing))\b"), "physical"),
    # physical materials handled on site
    ((r"\b(pipes?|lumber|concrete|steel beams?|girders?|bricks?|cables?|hoses?|drywall|shingles?|asphalt|gravel|"
     r"mortar|scaffolds?|pallets?|crates?|cargo|freight|luggage|baggage)\b"), "physical"),
    (r"\b(specimens?|samples?)\b[^.;]{0,20}\b(collect\w*|draw\w*|prepar\w*)\b", "physical"),
    # --- interpersonal ----------------------------------------------------------------------
    ((r"\b(counsel\w*|advis(e|es|ing)|consult\w*|confer\w*|negotiat\w*|persuad\w*|mediat\w*|"
     r"coach\w*|mentor\w*|teach\w*|instruct(s|ed|ing|ors?)?\b|train(s|ed|ing)?\b|tutor\w*|lectur\w*|"
     r"interview\w*|greet\w*|welcom\w*|entertain\w*|host\w*|supervis\w*|delegat\w*|motivat\w*|"
     r"recruit\w*|comfort\w*|reassur\w*|encourag\w*|refer\w* (patients|clients|students|customers))\b"),
     "interpersonal"),
    ((r"\b(meet|meets|meetings?|discuss\w*|convers\w*|speak\w*|talk\w*|explain\w*|listen\w*|"
     r"present\w* to|answer\w* (questions|inquiries|calls|telephones?|phones?)|"
     r"respond\w* to (questions|inquiries|complaints|requests|calls))\b"),
     "interpersonal"),
    ((r"\b(customers?|clients?|patients?|students?|children|pupils|guests?|visitors?|passengers?|"
     r"residents?|families|parents|the public|audiences?|community|patrons|members|colleagues|"
     r"coworkers|staff|employees|subordinates|teams?|stakeholders|vendors|suppliers|officials|"
     r"inmates|offenders|victims|witnesses|juveniles|participants|attendees|learners|"
     r"individuals|people|persons)\b"),
     "interpersonal"),
    ((r"\b(care for|caring for|provide care|serv(e|es|ing) (customers|clients|patrons|guests|food|"
     r"meals|drinks|beverages)|treat\w* (patients|clients|children|injuries)|examin\w* patients?|"
     r"nurs(e|es|ing)|administer\w* (medication|injections|treatments|first aid)|"
     r"perform\w* (surgery|surgical|procedures))\b"),
     "interpersonal"),
    ((r"\b(perform\w* (for|before|in front of)|sing\w*|danc(e|es|ing)|act in|acting|"
     r"play\w* (music|instruments?|roles?)|conduct\w* (orchestras?|choirs?|ceremonies|tours|classes)|"
     r"officiat\w*|preach\w*|testif\w*|testimony|hearings?|depositions?|cross-examin\w*|plead\w*)\b"),
     "interpersonal"),
    ((r"\b(sell\w*|solicit\w*|promot(e|es|ing)|demonstrat\w* (products|merchandise)|upsell\w*|"
     r"canvass\w*|fundrais\w*)\b"), "interpersonal"),
    ((r"\b(coordinat\w* with|collaborat\w*|liais\w*|cooperat\w* with|work(s|ing)? (closely )?with|"
     r"interact\w*|communicat\w* with|network\w* with|represent\w* (the )?(organization|company|"
     r"agency|clients|employer|union))\b"), "interpersonal"),
    # --- software / analytical --------------------------------------------------------------
    ((r"\b(computers?|computerized|software|programs?\b(?! of study)|programming|code|coding|"
     r"databases?|spreadsheets?|algorithms?|scripts?|computer systems?|information systems?|"
     r"networks?|servers?|websites?|web|online|internet|e-?mail|electronic(ally)?|digital|CAD|"
     r"automated|automation)\b"), "software"),
    ((r"\b(analy[sz]\w*|calculat\w*|comput(e|es|ing|ations?)|estimat\w*|forecast\w*|model\w*|"
     r"simulat\w*|statistic\w*|quantitative|numerical|mathematic\w*|budget\w*|financial statements?|"
     r"accounts?\b|accounting|audit\w*|reconcil\w*|tabulat\w*|formulas?|evaluat\w* data|"
     r"interpret\w* (data|results|findings|test results))\b"), "software"),
    ((r"\b(writ(e|es|ing|ten)|draft\w*|compos(e|es|ing)|author\w*|edit\w*|proofread\w*|typ(e|es|ing)|"
     r"transcrib\w*|translat\w*|summariz\w*|document\w*|record\w*|log\b|logs\b|fil(e|es|ing)\b|"
     r"catalog\w*|index\w*|enter\w* (data|information)|data entry|input\w* (data|information)|"
     r"key(s|ing)? (in|data)|compil\w*|prepar\w* (reports?|documents?|correspondence|letters?|"
     r"memos?|proposals?|contracts?|invoices?|forms?|schedules?|budgets?|plans?|specifications?|"
     r"drawings?|manuscripts?|articles?|presentations?|statements?|summaries|estimates?|bids?))\b"),
     "software"),
    ((r"\b(reports?|documents?|records|correspondence|letters|memos?|forms|invoices|receipts|ledgers|"
     r"manuscripts|articles|publications|drawings|blueprints|schematics|diagrams|charts|graphs|"
     r"tables|maps|specifications|contracts|proposals|grant applications|manuals|paperwork|"
     r"data|information|figures|statistics|metrics|results|findings|files)\b"), "software"),
    ((r"\b(research\w*|review\w* (literature|documents|records|data|reports|files|applications|"
     r"contracts|plans|manuscripts)|read\w* (reports|documents|records|manuscripts|blueprints|"
     r"meters?|gauges?)|stud(y|ies)|search\w* (databases|records|literature)|"
     r"design\w*|develop\w* (software|programs|applications|models|algorithms|databases|websites|"
     r"systems|procedures|plans|policies|curricula|strategies|budgets|specifications))\b"),
     "software"),
]

MODALITY_TIEBREAK = ("physical", "interpersonal", "software")

# ----------------------------------------------------------------------------------------------
# Presence requirement pi_k
# ----------------------------------------------------------------------------------------------
PRESENCE_BASE = {"physical": 0.70, "interpersonal": 0.55, "other_cognitive": 0.30, "software": 0.10}
PRESENCE_STEP = 0.15

PRESENCE_UP: list[str] = [
    (r"\b(in[- ]person|face[- ]to[- ]face|on[- ]?site|bedside|hands[- ]on|physically present|"
    r"in the field|at the scene|at (the )?(site|premises|facility|facilities|plant|store|hospital|"
    r"school|classroom|clinic|worksite|home|homes))\b"),
    (r"\b(patients?|customers?|guests?|visitors?|passengers?|students?|children|pupils|residents?|"
    r"inmates|audiences?|the public|spectators|attendees|diners|shoppers|clients?|families)\b"),
    (r"\b(escort\w*|greet\w*|welcom\w*|seat\w*|usher\w*|serv(e|es|ing) (food|meals|drinks|beverages)|"
    r"examin\w* patients?|palpat\w*|auscultat\w*|bath(e|es|ing)|restrain\w*|apprehend\w*|arrest\w*|"
    r"patrol\w*|guard\w*|lift\w*|carry\w*)\b"),
    (r"\b(construction sites?|work ?sites?|fields?|farms?|forests?|mines?|factories|plants?|"
    r"warehouses?|kitchens?|stores?|shops?|classrooms?|hospitals?|clinics?|wards?|laboratories|"
    r"labs?|stages?|theaters?|arenas?|vehicles?|roads?|highways?|railways?|ships?|vessels?|"
    r"aircraft|buildings?|premises|homes?)\b"),
]
PRESENCE_DOWN: list[str] = [
    (r"\b(remote(ly)?|telephone|phone|by mail|e-?mail|online|electronically|via (the )?internet|"
    r"virtual(ly)?|video ?conferenc\w*|written|in writing|correspondence)\b"),
    r"\b(computers?|software|databases?|spreadsheets?|reports?|documents?|records|data)\b",
]

# ----------------------------------------------------------------------------------------------
# EU AI Act use-case class (Annex III families -> high_risk; Art. 50 content -> transparency)
# ----------------------------------------------------------------------------------------------
USE_CASE_RULES: list[tuple[str, str]] = [
    # Annex III (1) biometrics
    ((r"\b(biometric\w*|facial recognition|fingerprint\w*|identify (individuals|persons|suspects)|"
     r"emotion recognition)\b"), "high_risk"),
    # Annex III (2) critical infrastructure safety components
    ((r"\b(air traffic|traffic control|traffic signals?|power (grid|distribution|plants?) operations?|"
     r"water (supply|treatment) (systems?|operations?)|gas (distribution|supply)|"
     r"electricity (supply|distribution|grid)|nuclear (reactors?|plants?))\b"), "high_risk"),
    # Annex III (3) education and vocational training: access, assessment
    ((r"\b(admissions?|admit\w* students|enroll\w* (students|applicants)|grad(e|es|ing) (exams?|tests?|"
     r"papers|assignments|homework|students|coursework|essays|examinations?)|"
     r"scor(e|es|ing) (tests?|exams?|assessments?)|(assess|evaluat)\w* (students?|pupils?|learners?|"
     r"trainees?|student (progress|performance|learning|achievement|work))|proctor\w*|"
     r"academic (placement|standing|progress)|standardized tests?|placement tests?)\b"), "high_risk"),
    # Annex III (4a) recruitment and selection
    ((r"\b(recruit\w*|hir(e|es|ing)|job (applicants?|candidates?|seekers?)|applicants?\b|candidates?\b|"
     r"r[eé]sum[eé]s?|curricula vitae|job interviews?|interview\w* (applicants|candidates|prospective)|"
     r"screen\w* (applicants|candidates)|select\w* (applicants|candidates|employees|staff|personnel)|"
     r"staffing|personnel (selection|decisions)|placement of workers)\b"), "high_risk"),
    # Annex III (4b) worker management: evaluation, promotion, termination, task allocation
    ((r"\b(evaluat\w*|assess\w*|apprais\w*|rat(e|es|ing)|review\w*|monitor\w*|grad(e|es|ing))\b[^.;]{0,25}\b"
     r"((employee|staff|worker|subordinate|personnel|team member|crew member)s?'? (performance|conduct|"
     r"productivity|attendance|job performance|work performance)|(performance|conduct|productivity) of "
     r"(employees|staff|workers|subordinates|personnel|team members|crews?))\b"), "high_risk"),
    ((r"\b(disciplin(e|es|ing)|promot(e|es|ing)|terminat(e|es|ing)|dismiss(es|ed|ing)?|fir(e|es|ing)|lay(s|ing)? off|"
     r"demot(e|es|ing)|reprimand\w*|suspend(s|ed|ing)?)\b[^.;]{0,25}\b(employees?|staff|workers?|subordinates?|"
     r"personnel|team members?)\b"), "high_risk"),
    ((r"\b(performance (appraisals?|evaluations?|reviews?|ratings?)|employee (evaluations?|performance|discipline|"
     r"grievances?|terminations?|promotions?)|disciplinary (actions?|proceedings?|measures?)|"
     r"(assign|allocate|distribute)\w*\b[^.;]{0,30}\b(work|tasks|duties|workloads?)\b[^.;]{0,30}\b(to|among) "
     r"(employees|staff|workers|subordinates|personnel|crews?|team members))\b"), "high_risk"),
    # Annex III (5b, 5c) creditworthiness, life/health insurance risk and pricing
    ((r"\b(credit ?worthiness|credit (risk|scor\w*|ratings?|histor\w*|applications?|limits?|approvals?|"
     r"reports?)|loan (applications?|approvals?|eligibility|underwriting)|approv\w* (loans?|credit|"
     r"mortgages?)|underwrit\w*|(life|health) insurance (risk|premiums?|eligibility|pricing)|"
     r"insurance (applications?|underwriting|risk assessment|premiums?)|mortgage applications?)\b"),
     "high_risk"),
    # Annex III (5a, 5d) essential public services eligibility; emergency dispatch and triage
    ((r"\b(eligibility|entitlements?|benefits? (claims?|eligibility|applications?)|"
     r"(public|social|welfare|unemployment|disability|housing|medicaid|medicare|social security|"
     r"food stamp|SNAP) (assistance|benefits?|programs?|services?)|welfare|"
     r"emergency (calls?|dispatch\w*|services?|responses?|medical)|"
     r"dispatch\w* (emergency|police|fire|ambulances?)|triag\w*|\b911)\b"), "high_risk"),
    # Annex III (6) law enforcement
    ((r"\b(law enforcement|police|crimes?|criminals?|suspects?|arrest\w*|offenders?|parole|probation|"
     r"inmates?|prisoners?|detain\w*|investigat\w* (crimes?|criminal|complaints? of (abuse|fraud)|"
     r"violations?|incidents?)|surveillance|evidence|polygraph|lie detector|forensic\w*|recidivism|"
     r"profiling|interrogat\w*|warrants?)\b"), "high_risk"),
    # Annex III (7) migration, asylum, border control
    ((r"\b(immigra\w*|visas?|asylum|refugees?|border (patrol|crossing|security|control)|"
     r"customs (inspection|declarations?|enforcement)|passports?|deport\w*|naturalization|"
     r"citizenship applications?)\b"), "high_risk"),
    # Annex III (8) administration of justice
    ((r"\b(courts?|judges?|judicial|adjudicat\w*|arbitrat\w*|sentenc\w*|verdicts?|rulings?|"
     r"legal (decisions?|opinions?|precedents?)|case law|statutes?|juries|jury|litigation|lawsuits?|"
     r"pleadings|(?<!clinical )trials?)\b"), "high_risk"),
    # Art. 50 transparency: content generation / interaction facing the public
    ((r"\b(news|journalis\w*|(news|magazine|journal|feature|newspaper) (articles?|stories|columns?)|"
     r"(writ(e|es|ing)|draft\w*|author\w*|edit\w*|produc\w*|creat\w*|develop\w*|compos\w*|design\w*|prepar\w*)\b"
     r"[^.;]{0,30}\b(articles?|stories|scripts?|screenplays?|speeches|newsletters?|blogs?|books?|novels?|poems?|"
     r"lyrics|songs?|advertisements?|commercials?|brochures?|pamphlets?|catalogs?|posters?|logos?|illustrations?|"
     r"artwork|graphics?|animations?|videos?|films?|documentaries|podcasts?|jingles?|slogans?|press releases?|"
     r"marketing (materials?|copy|content|campaigns?)|promotional (materials?|content|copy)|social media (posts?|content))|"
     r"press releases?|social media|advertis(e|es|ing|ements?)|public relations|publicity|broadcast\w*|"
     r"announc\w* to (the public|passengers|customers|audiences?)|narrat\w*|voice[- ]?overs?|"
     r"publish\w*(?! (findings|research|results|scientific|technical|papers))|"
     r"(respond|reply|answer)\w* to (customer|client|public|consumer|patron|user|visitor|caller)s? "
     r"(inquiries|questions|complaints|requests|calls)|customer (service|support|inquiries|questions)|"
     r"chatbots?|translat\w*|interpret\w* (for|between)|subtitl\w*|captions?)\b"), "transparency"),
]

# ----------------------------------------------------------------------------------------------
# Consequence of error proxy
# ----------------------------------------------------------------------------------------------
CONSEQUENCE_RULES: list[str] = [
    # medical
    (r"\b(patients?|surg\w*|diagnos\w*|medications?|medicines?|drugs?|dosages?|prescri\w*|anesthe\w*|"
    r"treatment plans?|clinical|medical|injur\w*|illness\w*|diseases?|infections?|emergenc\w*|"
    r"life[- ]threatening|fatal\w*|death|casualt\w*)\b"),
    # safety-critical
    (r"\b(safety|hazard\w*|dangerous|unsafe|accidents?|explosi\w*|toxic|poison\w*|radiation|"
    r"radioactive|nuclear|flammable|fires?\b|collisions?|crash\w*|structural (integrity|soundness|"
    r"failure)|load[- ]bearing|pressure vessels?|high[- ]voltage|electrical hazards?|aircraft|"
    r"airplanes?|flights?|pilots?|air traffic|trains?|bridges?|dams?|weapons?|firearms?|ammunition)\b"),
    # legal / financial
    (r"\b(legal|laws?|regulations?|regulatory|compliance|statut\w*|liabilit\w*|contracts?|litigation|"
    r"lawsuits?|courts?|evidence|audit\w*|financial statements?|tax(es| returns?)?|fraud|embezzl\w*|"
    r"large (sums|amounts)|millions?|investments?|mergers?|acquisitions?)\b"),
    # vulnerable persons
    r"\b(children|child|minors|juveniles|elderly|vulnerable|abuse|neglect|welfare)\b",
]

_MOD = [(re.compile(p, _F), c) for p, c in MODALITY_RULES]
_PUP = [re.compile(p, _F) for p in PRESENCE_UP]
_PDOWN = [re.compile(p, _F) for p in PRESENCE_DOWN]
_USE = [(re.compile(p, _F), c) for p, c in USE_CASE_RULES]
_CONS = [re.compile(p, _F) for p in CONSEQUENCE_RULES]


def classify_modality(text: str) -> str:
    votes = Counter(c for rx, c in _MOD if rx.search(text))
    if not votes:
        return "other_cognitive"
    best = max(votes.values())
    for cls in MODALITY_TIEBREAK:
        if votes.get(cls) == best:
            return cls
    return "other_cognitive"  # unreachable, kept for clarity


def presence(text: str, modality: str) -> float:
    p = PRESENCE_BASE[modality]
    p += PRESENCE_STEP * sum(1 for rx in _PUP if rx.search(text))
    p -= PRESENCE_STEP * sum(1 for rx in _PDOWN if rx.search(text))
    return round(min(1.0, max(0.0, p)), 2)


def classify_use_case(text: str) -> str:
    for cls in ("high_risk", "transparency"):
        if any(rx.search(text) for rx, c in _USE if c == cls):
            return cls
    return "unregulated"


def consequence_high(text: str, use_case: str) -> int:
    if use_case == "high_risk":
        return 1
    return int(any(rx.search(text) for rx in _CONS))


def explain(text: str) -> dict:
    """Which rules fired for ``text`` — for debugging a surprising classification."""
    return {
        "modality_votes": [(c, rx.pattern[:60]) for rx, c in _MOD if rx.search(text)],
        "presence_up": [rx.pattern[:60] for rx in _PUP if rx.search(text)],
        "presence_down": [rx.pattern[:60] for rx in _PDOWN if rx.search(text)],
        "use_case": [(c, rx.pattern[:60]) for rx, c in _USE if rx.search(text)],
        "consequence": [rx.pattern[:60] for rx in _CONS if rx.search(text)],
    }


def classify_text(text: str) -> dict:
    m = classify_modality(text)
    u = classify_use_case(text)
    return {
        "modality": m,
        "presence": presence(text, m),
        "use_case": u,
        "consequence_high": consequence_high(text, u),
    }


def classify_frame(df: pl.DataFrame, text_col: str = "task_text") -> pl.DataFrame:
    """Append ``modality``, ``presence``, ``use_case``, ``consequence_high`` to ``df``."""
    rows = [classify_text(t or "") for t in df[text_col].to_list()]
    cols = pl.DataFrame(rows, schema={"modality": pl.Utf8, "presence": pl.Float64,
                                       "use_case": pl.Utf8, "consequence_high": pl.Int64})
    return df.hstack(cols)


def distribution(df: pl.DataFrame, weight_col: str | None = None) -> dict[str, dict]:
    """Class shares (row-weighted, or by ``weight_col``) for the four classifier columns."""
    out: dict[str, dict] = {}
    n = df.height
    for col in ("modality", "use_case", "consequence_high"):
        if weight_col:
            g = df.group_by(col).agg(pl.col(weight_col).sum().alias("w")).sort(col)
            tot = g["w"].sum()
            out[col] = {str(k): round(v / tot, 4) for k, v in zip(g[col], g["w"])}
        else:
            vc = df[col].value_counts().sort(col)
            out[col] = {str(k): round(v / n, 4) for k, v in zip(vc[col], vc["count"])}
    pres = df["presence"]
    out["presence"] = {"mean": round(float(pres.mean()), 3), "p10": round(float(pres.quantile(0.1)), 2),
                       "p50": round(float(pres.quantile(0.5)), 2), "p90": round(float(pres.quantile(0.9)), 2)}
    return out


def print_distribution(df: pl.DataFrame) -> None:
    d = distribution(df)
    print(f"classifier {CLASSIFIER_VERSION}: n={df.height}")
    for col, shares in d.items():
        print(f"  {col:17s} " + ", ".join(f"{k}={v}" for k, v in shares.items()))


if __name__ == "__main__":  # quick manual check
    for t in [
        "Operate forklifts to move pallets of materials in the warehouse.",
        "Interview job applicants and evaluate their qualifications.",
        "Write software code and debug programs using integrated development environments.",
        "Counsel students on academic and career plans.",
        "Analyze financial data to prepare budget reports.",
    ]:
        print(classify_text(t), "|", t)

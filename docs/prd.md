# Schoolscouter — Product Requirements

## Problem

The English state school admissions system is unusually opaque to families navigating it for the first time. Unlike systems with clear geographic catchments or selection-by-exam alone, England layers four distinct admissions mechanics — distance-based oversubscription, banding plus lottery, faith priority, and academic selection — onto a fragmented landscape of community schools, academies, free schools, voluntary aided faith schools, and grammars. Each school sets its own rules within a statutory framework (the School Admissions Code) but applies them mechanically and without discretion.

For a parent, the practical consequence is that "what school will my child go to?" depends on:

- Where the family lives
- The family's faith status (and ability to evidence regular practice)
- Whether the child has siblings already attending a school
- The child's gender (some schools are single-sex)
- The child's performance in entrance tests (for grammars and some banded schools)
- Random allocation (for ballot-based schools)
- The behaviour of every other applicant that year

Existing tools surface fragments of this — Ofsted ratings, Progress 8 scores, distance circles — but none integrate the *applicable* admissions mechanic with the school-quality data, and none make the family-specific eligibility logic legible. Parents either rely on commercial tools that paywall the catchment data, on local Facebook groups with patchy and outdated information, or on word-of-mouth that disproportionately benefits already-informed families.

Schoolscouter aims to make the actual mechanics of state school admissions in England legible, accurate, and free.

## Target users

Primary: parents in London considering state schools for their child, with a focus on the secondary admissions decision (most consequential, most complex). Particularly users who are new to the English system — relocating from elsewhere in the UK, returning from abroad, or moving from independent to state.

Secondary: anyone researching school quality and admissions mechanics in their area, including journalists, researchers, and policy-interested members of the public.

Not targeted in v1: parents seeking independent (private) schools, parents of children with EHCPs (special educational needs admissions follow a different process), parents outside Greater London.

## Non-goals

- Replacing professional admissions advice for complex cases (EHCP, in-year admissions, appeals)
- Predicting future admissions outcomes with confidence (we present last year's data and explain its limits, not forecasts)
- Ranking schools as "best" or "worst" — we surface the data and let users decide
- Operating as a chat assistant (deferred to v2 as a learning project)
- Recommending house purchases or estate agency referrals

## v1 scope

### Geographic scope

Greater London secondaries only. Primary schools and pre-school options are out of scope for v1.

### Schools covered

All state-funded secondary schools in Greater London, including community schools, foundation schools, voluntary aided and voluntary controlled schools, academies, free schools, university technical colleges, and grammar schools.

### Data integrated

For every school in scope:

- **Identity** (GIAS): name, URN, address, postcode, coordinates, phase, type, religious character, gender, age range, capacity, local authority
- **Performance** (DfE Explore Education Statistics, KS4): Progress 8 (with confidence intervals), Attainment 8, percentage achieving grades 9–5 in English and Maths, percentage achieving 9–7, EBacc entry and average points, where published
- **Inspection** (Ofsted Five-Year Inspection Data): most recent inspection grade and date, with awareness of the post-2024 sub-judgement model
- **Geography** (ONS Postcode Directory): postcode-to-coordinate lookup with local authority and IMD decile

For three boroughs (Lewisham, Southwark, Bromley), additionally:

- **Catchment** (LA admissions booklets): last-distance-offered figures per school per oversubscription criterion per year, with explicit provenance, retrieval date, extraction method, and confidence indicator

### User-facing features

- **Postcode lookup**: enter a postcode, the map centres there, the user's location is marked
- **School map**: nearby schools rendered as markers on an interactive map, styled by phase and admissions mechanic (distance / banding+lottery / faith / academic selection)
- **School detail**: a panel for each school showing identity, performance metrics, Ofsted grade, distance from the user, admissions criteria summary, and where available catchment data with provenance
- **Filters**: by phase (initially fixed to secondary), by distance radius, by school type, by gender, by religious character, by Ofsted grade, by Progress 8 band
- **Comparison**: select up to three schools to compare side-by-side on key metrics
- **Plain-English explanations**: tooltips and inline copy explaining what Progress 8 is, why catchment is not a boundary, what each admissions mechanic actually means, and how to interpret confidence intervals
- **Sources page**: full citations for every dataset, dates of currency, and known limitations

### Out of v1 (in v2 backlog)

- Primary schools
- KS5 / A-level data and destinations data (including Oxbridge / Russell Group rates)
- Family-eligibility tool ("given my postcode, my child's gender, our faith status, and our siblings, which schools could realistically offer us a place?")
- Catchment coverage beyond the three pilot boroughs
- National coverage beyond Greater London
- Sibling-priority modelling
- Faith-school priority simulation
- Conversational agent with tool access
- User accounts, saved comparisons, favourites
- Notifications when school data updates

## Success criteria for v1

- A user can enter their postcode and see all relevant secondary schools within configurable radius
- For every school, the user can read a coherent explanation of how that school admits pupils
- For schools in the three pilot boroughs, the user can see last-known catchment outcomes with clear provenance
- The user can compare three schools on the metrics that matter
- A user new to the English system finishes the session understanding the four admissions mechanics, what Progress 8 measures, and what they should do next
- The site is accessible (WCAG 2.1 AA), works on mobile, and loads in under 2 seconds on a typical connection
- The data refreshes weekly without manual intervention

## Editorial principles

- **Accuracy over comprehensiveness.** Better to cover three boroughs well than thirty-three poorly. Better to flag missing data than fabricate it.
- **Provenance as a feature.** Every catchment number carries a source URL, retrieval date, and confidence level. Users see this when they click through.
- **Explain the limits.** Where data is suppressed, missing, or noisy (small confidence intervals, COVID gaps in Progress 8), say so explicitly rather than rendering a misleading number cleanly.
- **Don't rank.** Do not produce composite "school scores" or rankings. Surface the underlying metrics, explain them, let the user weigh.
- **Don't recommend.** Do not tell users which school to choose. Provide information that helps them decide.
- **Privacy by default.** No accounts, no analytics that captures postcodes, no logging of postcode-to-IP joins, no PII retention.

## Compliance and accuracy obligations

- Data is presented for informational purposes; the site does not constitute admissions advice
- All numerical data carries the academic year it relates to and the date it was last refreshed
- Catchment data for any given school is explicitly labelled with the year, the source document, and a confidence level
- The site links users to official sources (LA admissions booklets, individual school admissions policies) for binding information
- A clear "this is not the admissions authority — confirm with your LA before applying" disclaimer is shown on relevant pages

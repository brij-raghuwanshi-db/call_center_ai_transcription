# Toyota Call Center Scenario Catalog

**Date:** 21 October 2026  
**Scope:** U.S. Toyota owner support (Brand Engagement Center, Safety Connect Response Center, roadside assistance, dealer service, Toyota Financial Services, and related programs).  
**Purpose:** Translate public Toyota support programs into a working catalog of call scenarios. This document starts from the two owner situations captured in `toyota_translation` and expands to the full set of problems a Toyota call center actually solves.

Coverage terms, hours, and phone numbers change. Agents must always verify eligibility by VIN, in-service date, mileage, subscription status, and the current Warranty and Maintenance Guide. This is an operating catalog, not a substitute for those systems of record.

---

## 1. Why this document exists

This Databricks call-center app is now a standalone Toyota owner-support assistant. The product pattern is the same as the earlier healthcare POC, but every live scenario, knowledge snippet, guardrail, and audio asset is Toyota:

- A frightened owner is on a live call.
- The agent needs intent, risk, next-best action, and a nearest facility.
- The wrong answer is not just a bad CSAT score. For coolant, oil pressure, and crash events it can destroy an engine or delay emergency services.

The source note in `toyota_translation` contains two real owner situations:

1. A high-temperature caution on the screen while the driver still needs to reach a destination. The owner is scared the engine will fail and wants the nearest service center.
2. Check-engine and oil lights after a recent maintenance visit, while the owner is already on a highway and does not want an accident. The owner does not know whether to call a dealership, an independent shop, or Toyota.

Those two calls sit inside a much larger Toyota support network. Toyota Motor North America does not run a single generic help desk. It runs several specialized contact centers plus thousands of dealer service desks, and it routes owners among them.

---

## 2. The Toyota support network

Toyota’s North American owner support is split by urgency and by system of record. The AWS case study on Toyota Motor North America’s Brand Engagement Center (BEC) describes about 700 agents handling more than 1 million calls a year, using Amazon Connect with Salesforce Service Cloud Voice, real-time transcription, and a “Know Me, Know My Vehicle” program that identifies the guest and the VIN.

Toyota Connected North America operates a separate telematics response layer (Drivelink) for in-vehicle SOS, Automatic Collision Notification, stolen-vehicle locator, enhanced roadside assistance, and Destination Assist. Toyota has stated that this platform is in more than 5.5 million North American vehicles and has handled more than 3 million in-vehicle calls.

### 2.1 Who answers what

| Channel | Typical number / access | Hours | What it is for |
|---|---|---|---|
| Toyota Brand Engagement Center (BEC) | 1-800-331-4331 | Mon–Fri 8:00 a.m.–8:00 p.m. ET; Sat 9:00 a.m.–7:00 p.m. ET | Warranty, dealer disputes, product concerns, recalls, connected-services enrollment, “Know Me, Know My Vehicle,” liaison to dealers and area offices |
| Safety Connect Response Center | In-vehicle **SOS** button | 24/7 | Crash, medical emergency, police/fire, enhanced roadside with GPS, stolen-vehicle tracking after a police report |
| Toyota Roadside Assistance / ToyotaCare roadside | 1-800-444-4195; Toyota app 24/7 button; multimedia “Roadside Assistance” | 24/7/365 | Jump-start, lockout, spare-tire change, fuel delivery, towing, winching |
| Destination Assist | Voice: “Call Destination Assist”; nav menu. **Not** the SOS button | 24/7 with Drive Connect trial/subscription | Live agent sends a destination into factory navigation |
| Dealer service advisor / dealer BDC | Local dealer | Dealer hours; some 24-hour lots | Diagnosis, repair, ToyotaCare maintenance, appointments, come-backs, loaners |
| Toyota Financial Services | 1-800-874-8822 | Mon–Fri 8:00 a.m.–5:00 p.m. local | Loan, lease, payoff, billing, hardship |
| Toyota Extra Care / VSA / prepaid maintenance | 1-800-228-8559 | Mon–Fri 7:00 a.m.–7:00 p.m. CT; Sat 8:00 a.m.–1:00 p.m. CT | Vehicle Service Agreement claims, rental/travel reimbursement authorization |
| Fleet Customer Services | 1-800-732-2798 | Mon–Fri 7:00 a.m.–4:00 p.m. CT | Commercial/fleet orders, allocation, fleet policy |
| Lexus Customer Satisfaction | 1-800-255-3987 | Lexus hours | Lexus-brand equivalent of BEC |
| NCDS Dispute Settlement / California CDSP | NCDS 1-800-777-8119; CDSP 1-888-300-6237 | Business hours | Informal arbitration after dealer + BEC cannot resolve a warranty dispute |
| 911 / local emergency services | 911 | 24/7 | Injury, fire, crash with unknown occupant status, immediate danger |

TTY/TDD for BEC: dial 711, then request 1-800-331-4331. Roadside TTY: 1-800-747-2128.

### 2.2 Official Toyota escalation path (non-emergency product/service concerns)

From the Warranty and Maintenance Guide:

1. Talk to a dealership manager (service manager or customer relations manager).
2. If unresolved, call the Toyota Brand Engagement Center with VIN, current mileage, and dealer name. BEC works the case with the dealer.
3. If still unresolved, file with the National Center for Dispute Settlement (or California Dispute Settlement Program). Toyota states that using this program may be required before certain Magnuson-Moss or state lemon-law court actions.

**That path does not apply when the owner is immobilized on a highway.** Those calls go to roadside, Safety Connect, or 911 first. Warranty and goodwill are handled after the vehicle is safe.

### 2.3 What the agent must collect on almost every call

- VIN (dashboard, windshield, door jamb, Toyota app, or insurance card)
- Year, model, mileage, in-service / purchase date
- Location (GPS from SOS/app, highway mile marker, exit, city)
- Occupants, injuries, fuel remaining, whether the vehicle can still move
- Dashboard color (red vs amber), steady vs flashing, exact message text
- Recent service (dealer name, date, work performed, whether the light returned immediately)
- Coverage: ToyotaCare, Safety Connect trial/subscription, VSA, Certified Used, fleet
- Preferred dealer vs nearest open dealer vs independent shop constraint (warranty repairs generally require an authorized Toyota dealer)

---

## 3. How a Toyota call is triaged

The first question is not “what is the product issue?” It is “is anyone in danger, and can this vehicle keep moving?”

```text
Caller connects (phone, SOS, app, chat)
        |
        v
Is there injury, fire, smoke, crash, or no occupant response?
        | yes -> 911 / Safety Connect emergency dispatch
        | no
        v
Is the vehicle immobilized, overheating, or showing a red oil/coolant/brake/EPS light?
        | yes -> stop safely, roadside / SOS, do not keep driving
        | no
        v
Is this a connected-services, app, key, or navigation request?
        | yes -> Safety Connect / Destination Assist / BEC tech queue
        | no
        v
Is this money (loan, lease, VSA claim, ToyotaCare eligibility)?
        | yes -> TFS / Extra Care / BEC
        | no
        v
Product, dealer, warranty, recall, come-back
        -> BEC + dealer service
```

This is the same risk-first pattern the healthcare POC uses for symptom escalation. Toyota’s “red light” is the analog of chest pain.

---

## 4. Scenario catalog

Each scenario below includes:

- **Who usually handles it**
- **Urgency** (Critical / High / Medium / Low)
- **What “solved” looks like**
- **Typical next-best actions**

Urgency here is operational, not legal advice.

---

### 4.1 Life-safety, crash, and medical events

These are Safety Connect Response Center and 911 work, not Brand Engagement Center goodwill cases.

| ID | Scenario | Who handles it | Urgency | What the center does | Solved when |
|---|---|---|---|---|---|
| S1 | Airbag deployment or severe rear-end collision (Automatic Collision Notification) | Safety Connect | Critical | Vehicle places the call. Agent tries to speak with occupants. If no response or confirmed injury, agent requests local emergency dispatch to GPS location. Optional emergency-contact notification if on file. | EMS/police/fire notified; occupants accounted for; tow arranged if needed |
| S2 | Owner or passenger presses SOS after a crash that did not trigger ACN | Safety Connect | Critical | Confirm location, injuries, vehicle status; dispatch 911; stay on line | Emergency services rolling |
| S3 | Medical emergency in the vehicle (chest pain, seizure, diabetic event, childbirth) | Safety Connect + 911 | Critical | Treat as emergency assistance, not a car problem. Location + medical dispatch. Do not diagnose. | EMS dispatched |
| S4 | Fire, smoke from engine/hybrid battery, or fuel leak | Safety Connect + 911 | Critical | Get occupants out and away from the vehicle; fire dispatch; hybrid/EV high-voltage caution for first responders | Occupants safe; fire service on scene |
| S5 | Witnessing another motorist in distress | Safety Connect | High | Agent can request help for the other party using caller location | Other party’s emergency services notified |
| S6 | Accidental SOS press | Safety Connect | Low if occupant answers | Automated “press again to cancel,” or agent confirms no emergency. **No verbal response = dispatch anyway.** | Call closed or emergency confirmed |
| S7 | SOS light red / both lights off / service inactive | BEC + dealer | Medium | Green light = active. Red (except startup flash) = hardware issue, send to dealer. Both off = inactive trial/subscription. | Hardware repaired or subscription restored |

**Agent coaching notes**

- SOS is a priority emergency line. Destination Assist and billing questions do not belong on SOS.
- If occupants cannot speak, the protocol is to send help, not to wait.
- Hybrid and BEV crash response must mention high-voltage isolation for first responders.

---

### 4.2 Roadside immobilization

Covered services under ToyotaCare / Toyota Roadside Assistance typically include battery jump-start, lockout, emergency fuel delivery, spare-tire change, towing (often up to 25 miles to a Toyota dealer or chosen facility), and winching from a position adjacent to a regularly traveled road. Parts and fluids are generally not included except limited emergency fuel. Eligibility is VIN-based and is not the same for every vehicle:

- ToyotaCare roadside is commonly 2 years / unlimited miles from first use, with 3 years / unlimited miles for Mirai, Prius, BEVs, and PHEVs in current public materials.
- Separate Toyota app roadside copy describes 4 years / unlimited miles on a new vehicle and 2 years / unlimited miles on a Toyota Certified Used vehicle.
- Safety Connect Enhanced Roadside Assistance can apply **regardless of age/mileage** while a trial or paid subscription is active, and it shares GPS with the agent.
- Toyota Extra Care VSA and some Certified Used plans add or extend roadside.

Agents must look up the VIN instead of quoting a single number.

| ID | Scenario | Who handles it | Urgency | What the center does | Solved when |
|---|---|---|---|---|---|
| R1 | Dead 12-volt battery / no-start | Roadside | High | Jump-start. If it will not hold, tow to dealer. Hybrids/BEVs: 12-V failure can prevent READY and shifting; do not confuse with traction-battery failure. | Vehicle starts or is towed |
| R2 | Flat or blowout | Roadside | High | Replace impaired tire with inflated spare. No spare (many newer Toyotas have kits) → tow. | Spare mounted or vehicle towed |
| R3 | Lockout (keys in car, dead fob) | Roadside + Remote Connect if subscribed | High | Unlock via app/remote if available and legal/safe; otherwise locksmith/roadside. Immobilizer keys are restricted; copies often require a dealer or registered locksmith. | Owner back in vehicle |
| R4 | Out of fuel | Roadside | Medium | Deliver limited emergency fuel (VSA often caps gallons and monthly uses). BEVs/FCEVs: tow to charger or hydrogen station, no “fuel delivery.” | Enough energy to reach a station or vehicle towed |
| R5 | Stuck in ditch, mud, snow, sand | Roadside | Medium | Winch only if immediately adjacent to a traveled road and recoverable with standard equipment. Otherwise commercial recovery. | Vehicle back on road or commercial wrecker dispatched |
| R6 | Breakdown / will not move | Roadside | High | Tow to nearest Toyota dealer, or owner-chosen facility within policy mileage. Hybrid/BEV towing rules: prefer flatbed; rolling drive wheels can damage the transaxle / generate electricity. | Vehicle at a qualified repair facility |
| R7 | Overheating on the road | Roadside + safety triage | Critical | See playbook A. Stop, cool, do not open a hot cap, tow if the light stays on. | Occupants safe; vehicle not driven hot |
| R8 | Highway oil-pressure or dual warning lights | Roadside + safety triage | Critical | See playbook B. Stop, shut off, do not “make it to the next exit” if the oil light is red. | Engine off in a safe place; tow arranged |
| R9 | Need nearest dealer while traveling | App, BEC, Destination Assist, roadside | Medium–High | Locate open Toyota dealer; for warranty/ToyotaCare send to authorized dealer, not an independent shop. | Appointment or tow destination set |
| R10 | After-hours / holiday / rural area | Roadside 24/7 | High | Dispatch national network; set ETA; if delay is long, safety coaching (stay with vehicle vs. leave the roadway). | Provider ETA accepted |

**Dealer vs independent shop on these calls**

- Warranty diagnosis and ToyotaCare scheduled maintenance: authorized Toyota dealer.
- Emergency tow destination: nearest Toyota dealer, or another facility if the owner insists and policy allows.
- Independent shops can do some out-of-warranty work, but they generally cannot perform campaign/recall repairs, and using non-Genuine parts can affect remaining warranty on related systems.

---

### 4.3 Dashboard warnings and “should I keep driving?”

Toyota’s owner site is explicit: **yellow/amber** means important but not always stop-now; **red** means immediate attention. A flashing check-engine light is treated as urgent even though the lamp is not red.

This family is the direct expansion of the two `toyota_translation` scenarios.

| ID | Scenario | Light / message | Drive or stop? | Who handles it | Urgency |
|---|---|---|---|---|---|
| W1 | High coolant temperature | Red thermometer / “engine coolant temperature is too high” + buzzer | **Stop immediately in a safe place.** Do not keep driving to “get there urgently.” | Roadside / SOS, then dealer | Critical |
| W2 | Low engine oil pressure | Red oil-can | **Stop immediately, shut off engine**, contact dealer. Driving can destroy the engine. | Roadside / SOS, then dealer | Critical |
| W3 | Check engine steady | Amber engine outline | Drive cautiously to a dealer soon. Capture whether there is loss of power, noise, smell, or overheating. | Dealer service; BEC if recent service/warranty | High |
| W4 | Check engine flashing | Flashing MIL | Reduce speed, avoid hard acceleration, get to service immediately (misfire can destroy the catalytic converter). | Dealer / roadside if power is lost | Critical |
| W5 | Engine + oil lights together after service | Combined W2 + W3 | Treat as oil-pressure critical until proven otherwise. Come-back / goodwill after the vehicle is safe. | Roadside then dealer + BEC | Critical |
| W6 | Brake warning | Red BRAKE | Confirm parking brake is released. If light stays on, brake-fluid or hydraulic concern — do not continue highway driving. | Roadside / dealer | Critical |
| W7 | ABS / Brake Assist | Amber ABS | Normal brakes may still work; ABS may not. Schedule dealer inspection. | Dealer | High |
| W8 | Charging system / battery | Red battery | Alternator/charging failure. Electrical systems will die. Drive only to a nearby safe stop; often needs tow. | Roadside | High |
| W9 | Electric power steering | EPS warning | Steering assist may be lost or heavy. Stop safely; do not continue at speed. | Roadside / dealer | Critical |
| W10 | SRS airbag | Amber SRS | Airbags/seatbelts may not deploy. Drive to dealer soon; not an overheating-level stop unless crash-related. | Dealer; recall check | High |
| W11 | Tire pressure (TPMS) | Amber | Inflate/inspect. Blowout symptoms → roadside. | Owner + dealer if leak/sensor | Medium |
| W12 | Master warning + MID message | Varies | Read the multi-information display. Follow that message; it may be anything from a door ajar to a hybrid-system fault. | Depends on text | Varies |
| W13 | Maintenance required / wrench | Amber reminder | Schedule ToyotaCare or paid maintenance. Not an emergency. | Dealer BDC | Low |
| W14 | Hybrid system / traction battery / “Have Traction Battery Inspected” | Hybrid warning | Do not ignore. If the vehicle will not move, contact dealer before towing. | Dealer; roadside for immobilization | High–Critical |
| W15 | BEV low traction-battery charge | Charge warning | Charge; in cold weather the light may come on earlier. If stranded, tow to charger. | Roadside / charging network | Medium–High |
| W16 | Unengaged Park | Park warning | Have dealer inspect immediately; vehicle may not stay in Park. | Dealer; do not leave unattended on a grade | Critical |
| W17 | Air suspension malfunction | Suspension warning | Dealer immediately. | Dealer | High |
| W18 | Toyota Safety Sense inoperative (pre-collision, LDA, radar cruise) | TSS message | Driving is legal but driver-assist is down. Check camera/radar blockage (ice, dirt, aftermarket plates). Campaign/software updates are common. | Dealer; BEC for campaign status | Medium |
| W19 | Inappropriate pedal operation | Buzzer + MID | Follow on-screen instructions (often simultaneous brake/accelerator). | Coach from owner’s manual / dealer if repeat | High |

**What a call-center agent should never do on warning-light calls**

- Tell a frightened owner to “just keep driving” when the light is red coolant or red oil.
- Open a hot radiator/reservoir cap over the phone.
- Diagnose “it’s probably the gas cap” while the owner is on a highway with an oil light.
- Send a still-warranted vehicle only to an independent shop because it is closer, without explaining warranty and Genuine Parts implications.

---

### 4.4 Post-service come-backs (the second transcribed scenario)

These are among the highest-emotion non-crash calls. The owner already paid with time or money, trusts the brand less, and is often in an unsafe place.

| ID | Scenario | Who handles it | Urgency | Typical resolution |
|---|---|---|---|---|
| C1 | Warning lights return the same day as oil service | Dealer first; BEC if dealer is unresponsive | Critical on-road, then High | Tow back to servicing dealer; do not “drive it in.” Inspect oil level/pressure, filter, drain plug, correct viscosity. |
| C2 | Drain plug, filter housing, or oil cap left loose / oil leak after service | Dealer + BEC goodwill | Critical if leaking/pressure light | Engine damage review; goodwill/warranty/dealer policy; possible engine replacement discussion if run low. |
| C3 | Wrong oil specification or over/under fill | Dealer | High | Correct oil, inspect; document for BEC. |
| C4 | Vehicle not fixed after multiple visits (“I keep coming back”) | Dealer CRM + BEC | High | Case file, repair history, possible parts analysis, loaner via Transportation Assistance Policy if overnight warranty work. |
| C5 | Repeat MIL after a repair that was supposed to clear it | Dealer diagnosis + BEC | High | Freeze-frame/DTC review; campaign search; possible NCDS path if unresolved. |
| C6 | ToyotaCare visit but extra paid services were added and now there is a problem | Dealer + BEC | Medium | Explain what ToyotaCare covers vs. additional dealer recommendations; goodwill if the extra work is tied to the failure. |
| C7 | Independent shop service, then lights; owner wants Toyota to pay | BEC | Medium | Toyota generally does not cover independent workmanship. Warranty may still cover a defective Toyota part if unrelated to the shop’s work. |

**Come-back handling pattern (mirrors healthcare “symptom returned after discharge”)**

1. Safety first: can they drive?
2. Stabilize: roadside tow to the servicing dealer if unsafe.
3. Document: RO number, date, mileage, work performed, photos of lights.
4. Dealer action: inspect before any debate about who pays.
5. BEC action: if the dealer stalls, open a case, involve district service/parts manager as needed.
6. If still unresolved: NCDS / CDSP.

---

### 4.5 Maintenance, ToyotaCare, and service scheduling

| ID | Scenario | Who handles it | Urgency | Notes |
|---|---|---|---|---|
| M1 | First complimentary service due | Dealer; Service Connect reminder | Low | Welcome email ~14–20 days after purchase; reminder ~90 days before first service. |
| M2 | What does ToyotaCare include? | BEC / dealer | Low | Factory-scheduled maintenance: oil/filter as specified, tire rotation, multi-point inspection, fluid level inspect/adjust. Not every maintenance-light cycle is an oil change on every model. |
| M3 | ToyotaCare term questions | BEC / dealer | Low | Public materials: MY26 and earlier commonly 2 years / 25,000 miles; MY27 materials describe 1 year / 10,000 miles except Mirai (3 years / 35,000). Always VIN-check. |
| M4 | Can I use any Toyota dealer? | BEC | Low | Yes for ToyotaCare, at participating dealers using Toyota Genuine Parts when available. Not limited to the selling dealer. |
| M5 | ToyotaCare Plus / prepaid maintenance purchase or claim | Dealer sales; Extra Care 1-800-228-8559 | Low | Eligibility windows differ by model year. |
| M6 | Dealer recommended extra services beyond ToyotaCare | Dealer + BEC if dispute | Medium | Extra work is not automatically complimentary. Agent should distinguish required vs. optional. |
| M7 | Maintenance light vs. warning light confusion | Dealer / BEC | Medium | Owners often treat a yellow wrench like a red oil can. Educate, then triage the actual symbol. |
| M8 | Need a loaner / shuttle | Dealer; warranty Transportation Assistance Policy | Medium | Overnight warranty repairs that cannot be finished same day may qualify during New Vehicle Limited Warranty. Scheduling convenience overnight does not. |
| M9 | Service appointment booking | Dealer / Toyota app click-to-call preferred dealer | Low | BEC does not usually hold the dealer’s schedule; it navigates and can conference. |
| M10 | Missed interval / “did I void my warranty?” | BEC | Medium | Lack of or improper maintenance can affect coverage for related failures. Agent collects service records rather than declaring a void over the phone. |

---

### 4.6 Warranty, goodwill, lemon-law, and disputes

Typical U.S. new-vehicle structure (confirm in the guide for that VIN):

| Coverage | Common term |
|---|---|
| Basic | 3 years / 36,000 miles |
| Powertrain (engine, transmission, driveline) | 5 years / 60,000 miles |
| Restraint systems (airbags, seatbelts) | 5 years / 60,000 miles (Kansas seatbelts: 10 years, unlimited miles in the 2024 guide) |
| Corrosion perforation | 5 years / unlimited miles |
| Hybrid battery (MY2020+ HEV/PHEV/FCEV) | 10 years / 150,000 miles |
| Other hybrid system components (inverter, control modules, etc.) | 8 years / 100,000 miles |
| BEV drive (bZ4X class): traction battery below 70% capacity, transaxle, inverter | 8 years / 100,000 miles |
| Towing for inoperable warranted part | To nearest authorized Toyota dealer |
| Tires | Tire manufacturer’s warranty, not Toyota basic |

| ID | Scenario | Who handles it | Urgency | Solved when |
|---|---|---|---|---|
| G1 | “Is this covered?” | BEC + dealer | Medium | Coverage decision with VIN, mileage, cause, maintenance history |
| G2 | Warranty repair denied at dealer | BEC | High | BEC reviews with dealer/district; possible goodwill |
| G3 | Repeat failure of same component | BEC | High | Case, parts return, possible policy adjustment |
| G4 | Engine damage after overheating or no-oil | BEC + dealer | High | Cause analysis (maintenance, defect, abuse). Do not promise a new engine on the first call. |
| G5 | Aftermarket accessories / chip tunes / lift kits | BEC | Medium | Alteration/non-Genuine parts can exclude related damage |
| G6 | Used / subsequent owner asking about remaining warranty | BEC | Low | Coverage transfers automatically at no cost on the New Vehicle Limited Warranty |
| G7 | Policy adjustment / special coverage for out-of-warranty known issues | BEC | Medium | Toyota sometimes mails special policy adjustments; BEC can check |
| G8 | Lemon-law / repurchase / replacement request | BEC then NCDS/CDSP | High | Do not give legal conclusions. Explain informal dispute program. California: failure to use CDSP may affect lemon-law rights. |
| G9 | Request for reimbursement of repairs already paid | BEC / recall reimbursement portal | Medium | Common after a campaign is announced |
| G10 | Transportation assistance for overnight warranty work | Dealer / BEC | Medium | See section 4.5 M8 |

---

### 4.7 Recalls and service campaigns

Toyota distinguishes:

- **Safety Recall Campaign** — safety defect under the Safety Act; free inspection/repair.
- **Special Service Campaign** — customer-satisfaction technical issue; free.
- **Limited Service Campaign** — free for a defined window, then expires.

VIN lookup: toyota.com/recall (Toyota, Lexus, Scion, U.S., territories, Mexico, since 1999).

| ID | Scenario | Who handles it | Urgency | Notes |
|---|---|---|---|---|
| K1 | “Is my VIN in a recall?” | BEC / web / dealer | Medium–High | Know Me, Know My Vehicle is designed to surface this when the guest is identified |
| K2 | Airbag / Takata-class inflator | Dealer; BEC | High | Do not delay. Schedule campaign repair. |
| K3 | TSS / camera / radar campaign (example: intermittent Safety Sense inoperative) | Dealer | Medium | Software/calibration; owner may only notice a message |
| K4 | Stop-sale / “can I drive it?” | BEC + dealer | High | Follow the specific campaign instructions; some are “do not drive” |
| K5 | Parts not available yet | BEC + dealer | Medium | Interim risk guidance, rental/loaner if the bulletin provides it |
| K6 | Recall notice received after owner already paid for the repair | Reimbursement process + BEC | Low | Paperwork through toyota.com/owners/recalls |
| K7 | Campaign completed but symptom remains | Dealer inspection + BEC | High | Not automatically “fixed forever”; inspect |

---

### 4.8 Connected services, Toyota app, subscriptions

Products (availability varies by year/model; needs cellular + GPS):

| Product | What owners think it is | Call-center reality |
|---|---|---|
| Safety Connect | SOS button | Emergency, ACN, stolen vehicle, enhanced roadside. Trial then paid subscription. |
| Service Connect | “The car emails the dealer” | Vehicle Health Reports, warning-light notifications, maintenance alerts. Dealer contact is **opt-in**. |
| Remote Connect | Phone as a key | Remote start/stop (not manual transmission), lock/unlock, locate, guest-driver monitor, smartwatch. ~$8/month standalone in current plan cards. |
| Drive Connect | Built-in Google-like nav | Cloud Navigation, Intelligent Assistant, Destination Assist live agent. |
| Destination Assist | Concierge | Live agent sends POI into factory nav. Do not use SOS. |
| Wi-Fi Connect | Hotspot | AT&T; device limits; streaming add-ons by model year. |
| Supra Connect | BMW-related stack on GR Supra | Separate from main Toyota app services. |

| ID | Scenario | Who handles it | Urgency |
|---|---|---|---|
| N1 | Enroll / cancel / renew Safety Connect, Drive Connect, Remote Connect | Toyota app Shop → Manage Subscriptions; BEC | Low |
| N2 | “My trial expired and SOS does not work” | BEC | High if they need SOS now; otherwise Medium |
| N3 | Remote start will not work | BEC tech | Low–Medium | Enclosed-space warning; manual-transmission exclusion; cellular/out-of-range |
| N4 | App cannot find / add vehicle | BEC | Medium |
| N5 | Guest driver / shared family account | BEC | Low |
| N6 | Unwanted dealer calls/texts from Service Connect | App privacy portal or BEC 1-800-331-4331; reply STOP | Medium (privacy) |
| N7 | Opt out of Service Connect entirely | App or BEC (some materials also list 1-877-855-8377) | Low |
| N8 | Vehicle Health Report shows a warning the owner has not seen | BEC + dealer | Medium–High | Treat the underlying light with the W-series rules |
| N9 | Destination Assist request | Destination Assist agents | Low | Address/POI into nav |
| N10 | Wi-Fi hotspot / Integrated Streaming billing | BEC / AT&T as applicable | Low |
| N11 | Privacy / “is Toyota tracking me?” | BEC | Medium | Explain Safety/Service/Remote data uses; law-enforcement requests go through legal process except exigent 1-800-331-4331 |
| N12 | Stolen vehicle locator | Police report first, then 1-800-331-4331 with case number | Critical | Agents share GPS with police; they do not “disable the car” as a consumer feature |

Service Connect is especially relevant to this POC: the vehicle can already send coolant temperature, oil life, DTCs, odometer, fuel level, and hybrid/EV battery data. A live agent-assist product can join that telemetry to the spoken complaint (“temperature is too high”) instead of relying only on the transcript.

---

### 4.9 In-car technology, audio, and ADAS

| ID | Scenario | Who handles it | Urgency |
|---|---|---|---|
| T1 | Bluetooth pairing / dropped calls | Dealer multimedia / BEC how-to | Low |
| T2 | Apple CarPlay / Android Auto will not connect | Same | Low | USB quality, wireless compatibility, OS version |
| T3 | Backup camera / parking sensors | Dealer | Medium | Safety-related if camera is blank |
| T4 | Audio / JBL / SiriusXM subscription | BEC / SiriusXM | Low |
| T5 | Over-the-air or dealer software update questions | Dealer / BEC | Low–Medium |
| T6 | Head unit frozen / reboots | Dealer | Medium | Safety Connect is independent of nav; SOS can still work |
| T7 | Toyota Safety Sense false braking or no braking | Dealer immediately | High | Campaign check; do not tell them to ignore pre-collision braking |
| T8 | Adaptive cruise / LTA disable requests | Dealer education | Low |
| T9 | “Hey Toyota” / Intelligent Assistant not listening | Drive Connect subscription + dealer | Low |
| T10 | Digital key / smartwatch integration | BEC | Low |

---

### 4.10 Keys, immobilizer, theft, and security

| ID | Scenario | Who handles it | Urgency |
|---|---|---|---|
| L1 | All keys lost | Dealer or ALOA registered locksmith | High | Immobilizer programming is restricted |
| L2 | Spare key / fob battery | Dealer / roadside if locked out | Medium |
| L3 | Vehicle stolen | Police → BEC Stolen Vehicle Locator if Safety Connect active | Critical |
| L4 | Suspected relay-theft / fob cloning | Police + dealer (software/hardware updates where applicable) | High |
| L5 | Immobilizer will not allow start | Dealer | High | Distinguish from 12-V battery |
| L6 | Valet / guest driver remote monitoring | Remote Connect | Low |

---

### 4.11 Hybrid, plug-in, BEV, and Mirai

These generate a distinct queue because owner mental models are wrong (“the hybrid battery is dead” when it is the 12-volt; “I need to plug in my RAV4 Hybrid”).

| ID | Scenario | Who handles it | Urgency |
|---|---|---|---|
| E1 | READY light off / vehicle silent so owner thinks it is broken | BEC education + dealer if true no-start | Medium |
| E2 | 12-V vs traction battery confusion | Roadside jump vs dealer HV diagnosis | High |
| E3 | Hybrid battery warning / inspection message | Dealer | High | MY2020+ HV battery warranty commonly 10 yr / 150k mi |
| E4 | Inverter, hybrid control module, DC-DC | Dealer | High | Often 8 yr / 100k mi hybrid-component coverage |
| E5 | Parked too long, HV battery discharged | Dealer | Medium | Toyota guidance: drive at least ~30 minutes or 10 miles every several months; do not leave in Neutral |
| E6 | PHEV / bZ will not charge (home EVSE, public DC fast charge, app) | BEC + dealer + charging provider | High if stranded | Charging-procedure exclusions exist in BEV warranty |
| E7 | Range anxiety / winter range drop | BEC education | Low–Medium | Capacity loss ≤30% on BEV is described as normal in the bZ4X guide; below 70% original capacity is a warranty topic |
| E8 | Fuel-cell Mirai hydrogen station locator / empty tank | Destination Assist + roadside tow to station | High |
| E9 | High-voltage after collision | Safety Connect + first responders | Critical |
| E10 | Towing a hybrid/BEV incorrectly | Roadside | High | Flatbed preferred; do not dinghy-tow against the owner’s manual |
| E11 | “My hybrid uses too much gas” | BEC / dealer | Low | Driving style, short trips, HVAC, tire pressure |
| E12 | Traction battery recycling / end of life | Dealer only | Low | Do not dispose of the pack yourself |

---

### 4.12 Collision, body, insurance, and parts

| ID | Scenario | Who handles it | Urgency |
|---|---|---|---|
| P1 | Post-crash “where do I take it?” | Toyota Certified Collision Center locator + insurance | High | Owner chooses the shop; insurer may recommend otherwise |
| P2 | Insist on Toyota Genuine parts vs aftermarket | TCCC / dealer wholesale parts / BEC | Medium | Safety systems (airbags, ADAS calibration) are the talking point |
| P3 | ADAS recalibration after windshield replacement | Dealer / TCCC | High | TSS will misbehave if skipped |
| P4 | Glass, dent, hail | Insurance + dealer/TCCC | Medium |
| P5 | Accessory damage (running boards, hitches) | Dealer accessories / insurance | Low |
| P6 | Wholesale / independent body shop cannot get a part | Dealer parts + BEC parts/reimbursement (Toyota has said this is a future BEC expansion area) | Medium |
| P7 | Title / salvage / branded title after total loss | Insurance + DMV; BEC limited | Medium |

---

### 4.13 Sales, dealer experience, and product concerns

BEC job descriptions describe the advocate as a liaison among owners, prospective owners, dealerships, area offices, and headquarters. These are not roadside calls, but they are a large share of the 1 million+ annual BEC contacts.

| ID | Scenario | Who handles it | Urgency |
|---|---|---|---|
| D1 | Dealer sales pressure, add-ons, documentation fees | BEC + dealer CRM | Medium |
| D2 | Delivery condition (missing items, open campaigns, dirty, unrepaired PDI) | Dealer + BEC | Medium |
| D3 | Appointment not honored / long wait / poor communication | Dealer + BEC | Medium |
| D4 | Perceived discrimination or safety incident at a store | BEC + dealer operator | High |
| D5 | Product quality (rattle, paint, wind noise, consumption) | Dealer diagnosis + BEC | Low–Medium |
| D6 | Advertising / price / allocation (“why can’t I get a Grand Highlander Hybrid?”) | Dealer sales; fleet/BEC limited | Low |
| D7 | Buy-back of a damaged new vehicle at delivery | Dealer + BEC | High |
| D8 | Compliment / executive letter | BEC | Low |

---

### 4.14 Toyota Financial Services and protection products

Wrong-queue risk is high. A BEC agent who tries to quote a payoff wastes the call.

| ID | Scenario | Number | Urgency |
|---|---|---|---|
| F1 | Payment, due date, autopay, late fee | TFS 1-800-874-8822 | Medium |
| F2 | Lease-end, excess wear, mileage | TFS; Excess Wear 1-888-548-8821 | Medium |
| F3 | Hardship / extension | TFS | High |
| F4 | Payoff / refinance quote | TFS | Low |
| F5 | GAP claim after total loss | GAP 1-800-255-8713 | High |
| F6 | VSA mechanical claim authorization | Extra Care 1-800-228-8559 | High | Prior authorization required; unauthorized repairs can be denied |
| F7 | VSA rental, meals, lodging reimbursement | Same; prior approval | Medium | Typical published caps: ~$50/day rental, ~$100/day lodging if >150 miles from home, 5-day limits — **confirm on the contract** |
| F8 | Tire & wheel / key replacement product | 1-855-999-0518 | Medium |
| F9 | Credit life / disability claim | 1-800-445-8154 | High |
| F10 | Toyota Rewards Visa / loyalty | Card servicer, not BEC | Low |

---

### 4.15 Certified Used, fleet, mobility, and specialty

| ID | Scenario | Who handles it | Urgency |
|---|---|---|---|
| X1 | Toyota Certified Used warranty / 7-year/100k powertrain style questions | Dealer CPO + BEC | Medium | Terms vary; roadside often 2 years unlimited on CPO in public roadside copy |
| X2 | Fleet order status, upfitting, RNPO | Fleet 1-800-732-2798 | Medium |
| X3 | Wheelchair conversion (BraunAbility / VMI), scooter lift, transfer seat | Toyota Mobility Center + authorized conversion dealer | Medium | Needs assessment / driving rehab specialist referral |
| X4 | Adaptive equipment warranty vs vehicle warranty | Mobility dealer + BEC | Medium | Conversion company vs Toyota split |
| X5 | GR / TRD / racing use | BEC | Medium | Racing/overloading is a warranty exclusion |
| X6 | Accessory installation (tow package, roof rack) | Dealer accessories | Low |
| X7 | Owner’s manual / how-to video | toyota.com/owners | Low |
| X8 | Law-enforcement vehicle-data request | Exigent: 1-800-331-4331; otherwise warrant/subpoena/court order via CT Corporation | Critical if exigent | Location generally requires a warrant |

---

## 5. Deep-dive playbooks for the two transcribed scenarios

The `toyota_translation` file is a spoken owner note, not a clean transcript. ASR and overlapping speakers produced fragments such as “your card. Temperature is too high.” In context this is almost certainly **coolant / engine temperature**, not a “card.” The second scenario is an **engine (MIL) light plus oil light after recent maintenance, on a highway.**

These two playbooks are written so they can be dropped into the POC as scenario scripts, RAG documents, and next-best-action logic.

---

### Playbook A — High coolant temperature while the owner still needs to get somewhere

**Source line (cleaned):**  
*“I was just driving by and a caution came up on the screen saying that [the car] temperature is too high, and I just have to reach somewhere urgently. Can you connect me to the nearest service center? I am really scared to drive. I think the engine might blow up.”*

**Official Toyota position (owners.toyota.com warning lights and owner’s manuals):**  
High coolant temperature warning light / buzzer = engine coolant temperature is too high. **Immediately stop the vehicle in a safe place.**

**Intent:** `overheat_roadside_assist`  
**Risk:** Critical  
**Primary queue:** Safety Connect SOS or 1-800-444-4195, not a routine BEC callback  
**Secondary queue:** Nearest authorized Toyota dealer for diagnosis; BEC if coverage/come-back

#### A.1 What is actually happening

Possible causes the agent should not diagnose on the phone, but should keep in mind:

- Low coolant (leak, recent service, reservoir empty)
- Stuck thermostat, failed water pump, collapsed hose
- Cooling-fan failure
- Heavy load, towing, mountain grade, stopped traffic with A/C on
- Head-gasket or internal failure (the owner’s “engine might blow up” fear is not irrational)

Continuing to drive a red-hot engine can warp the head, destroy the gasket, and seize the engine. “I have to be somewhere urgently” is the trap.

#### A.2 Live-call script pattern

1. **Stabilize the person.** Acknowledge fear. Do not minimize.
2. **Hazard first.** “Are you able to pull over to a safe shoulder or exit now? Put hazards on. Do not keep driving to your appointment.”
3. **Stop and shut down.** Once parked: shift to P, parking brake, engine off. Hybrid: POWER off.
4. **Do not open the hood cap.** If they can smell coolant or see steam, stay away from the front of the car. Never open a hot reservoir or radiator cap.
5. **Occupant check.** Kids, heat, traffic. If they are on a live highway with no shoulder, stay in the vehicle with belts on until a patrol/roadside truck arrives, unless fire/smoke.
6. **Identity + location.** VIN if possible, but GPS from SOS/app is enough to dispatch.
7. **Dispatch.** Enhanced roadside if Safety Connect is active (GPS already shared). Otherwise 1-800-444-4195 or app 24/7 button. Tow, do not “let it cool and try again” if the light already came on under load.
8. **Destination.** Nearest authorized Toyota dealer that can take a tow now, not the original selling dealer 40 miles away, unless the owner insists and mileage policy allows.
9. **Coverage check in parallel.** ToyotaCare roadside, Safety Connect, VSA, warranty towing if a warranted part failed.
10. **Only after the vehicle is moving on a flatbed:** collect destination urgency (rental, TFS travel protection if VSA, dealer shuttle, family pickup).

#### A.3 Next-best actions for an agent-assist UI

| Priority | Action | Why |
|---|---|---|
| 1 | Prompt: pull over, hazards, engine off | Prevents catastrophic engine damage and highway crash |
| 2 | Dispatch roadside with GPS | Owner is scared and may not navigate IVR |
| 3 | Locate nearest Toyota dealer open for tows | Warranty and ToyotaCare path |
| 4 | Warn: do not open hot coolant cap | Scald injury |
| 5 | After tow: open dealer RO and BEC case if recent service | Come-back if a shop just worked cooling system |
| 6 | Offer rental / Transportation Assistance if warranty overnight | Owner’s “I have to be somewhere” is now a mobility problem, not a driving problem |

#### A.4 Knowledge snippets the RAG layer needs

- High coolant temperature = stop now.
- Difference between temperature **warning** and temperature **gauge in the red**.
- Hybrid still has an engine that can overheat.
- Towing: prefer flatbed; 25-mile typical complimentary window; owner can choose another facility if policy allows.
- Never use SOS for Destination Assist, but SOS **is** correct if this is an emergency / enhanced roadside.

#### A.5 Demo caller persona

**Maya Chen, 34, 2023 RAV4 Hybrid, 18,400 miles, ToyotaCare still active, Safety Connect trial expired last month.** Driving on I-35, 20 minutes from a hospital appointment, steam smell, red temperature message on the MID. Wants the agent to “just tell me I can make it.” Correct agent behavior is to refuse that, stop her, and tow.

---

### Playbook B — Engine light and oil light after recent maintenance, already on a highway

**Source line (cleaned):**  
*“The engine light and the oil light started coming up, even though I just had car maintenance. I need to understand how to fix this. Do I need to go to a dealership? A service center? Who do I need to call? I’m in the middle of the highway and I don’t want to have an accident.”*

**Official Toyota position:**

- Low engine oil pressure warning: **Immediately stop in a safe place and contact your Toyota dealer.** Oil is not lubricating the engine.
- Malfunction indicator lamp (check engine): have the vehicle inspected by a Toyota dealer immediately. If flashing, treat as urgent.

When **both** are on, oil pressure wins. This is not a “schedule a diagnostic when you can” call.

**Intent:** `oil_pressure_highway_comeback`  
**Risk:** Critical  
**Primary queue:** Roadside / SOS  
**Secondary queue:** Servicing dealer come-back + BEC case

#### B.1 Why “I just had maintenance” makes this worse, not better

A same-visit or next-drive oil light after an oil change is a classic come-back:

- Drain plug not torqued / washer missing → oil dumped on the highway
- Filter not seated / cap not tightened (especially Toyota cartridge housings)
- Underfilled or overfilled
- Wrong viscosity
- Oil-pressure switch unplugged
- Unrelated: true oil-pump or bearing failure that the service did not cause

The owner is asking a **navigation** question (“dealer vs service center vs who to call”) because they do not have a **safety** answer yet. The agent must invert that: safety, then destination, then accountability.

#### B.2 Live-call script pattern

1. **Highway safety.** Hazards, right lane, next safe shoulder or exit **without accelerating hard**. If traffic is dense, 911/Safety Connect for a safety stop, not a debate about shops.
2. **Color and behavior.** “Is the oil light red? Is the engine light steady or flashing? Any knocking, loss of power, or smell of oil?”
3. **Stop and shut off.** Do not idle for a long time either; if pressure is gone, idle still wears bearings.
4. **Do not restart to “see if it goes out.”**
5. **Who to call, in order:**
   - If SOS green: press SOS, say “roadside assistance.”
   - Else: 1-800-444-4195 or Toyota app 24/7.
   - 911 if they cannot get off the live lanes.
   - **Not** an independent “service center” while the oil light is red.
6. **Tow destination:** the Toyota dealer that just performed the maintenance, if it is within the complimentary tow radius and open to receive. Otherwise nearest Toyota dealer, then dealer-to-dealer transfer.
7. **Do not check oil on the shoulder of a highway** unless they are fully clear of traffic and the engine has been off. Even then, a low stick confirms leak/underfill; a full stick with a red light still means **tow** (pump/sensor).
8. **After dispatch:** take the RO number, dealer name, what was done, mileage today vs. mileage on the RO.
9. **BEC case** if the dealer is closed, denies responsibility, or the owner is stranded far from home.
10. **Engine-damage freeze:** if they admit they drove many miles with the oil light on, document it. Do not accuse. Diagnosis first.

#### B.3 Dealer vs independent “service center”

| Option | Use now? | Why |
|---|---|---|
| Authorized Toyota dealer that did the oil change | **Yes, preferred tow destination** | Come-back, Genuine Parts, warranty, ToyotaCare, they have the RO |
| Any authorized Toyota dealer | **Yes if closer / open** | Warranty and campaign capability |
| Independent general shop | **No while oil light is red** | Cannot close a ToyotaCare/warranty come-back; highway oil-pressure failures need dealer diagnosis |
| Quick-lube that did the work (if not the Toyota dealer) | Only as the responsible party after the vehicle is towed somewhere safe | Toyota BEC will not usually pay for that shop’s workmanship |
| BEC 1-800-331-4331 | After the vehicle is safe, or if the dealer will not help | Goodwill, case management, NCDS later |

#### B.4 Next-best actions for an agent-assist UI

| Priority | Action |
|---|---|
| 1 | Classify oil-pressure as Critical regardless of “I just had it serviced” |
| 2 | Highway pull-over coaching; do not continue to destination |
| 3 | Dispatch tow; default destination = servicing Toyota dealer |
| 4 | Flag come-back: recent RO, possible loose drain plug/filter |
| 5 | Open BEC case template: VIN, mileage, dealer, RO, lights, miles driven after light |
| 6 | After vehicle is safe: coverage path (warranty, dealer policy, goodwill, NCDS) |

#### B.5 Demo caller persona

**James Patel, 51, 2022 Camry, 27,900 miles, oil change at the selling dealer yesterday.** Check-engine and red oil lights on I-80. He wants a phone fix and is trying to make a meeting. Correct behavior: get him off the highway, kill the engine, tow to that dealer, open a come-back case. Incorrect behavior: “it’s probably the sensor, you’re fine to keep going.”

---

## 6. Urgency model for the Databricks agent-assist product

Map Toyota events onto the same risk scale the healthcare POC already uses.

| Risk | Toyota examples | Agent-assist behavior |
|---|---|---|
| Critical | Crash/ACN, SOS with no response, fire, red coolant, red oil pressure, red brake (not parking brake), EPS heavy steering, unengaged Park, highway immobilization in live lanes | Interrupt the agent. Show stop-driving guidance. Offer 911 / SOS / roadside dispatch. Do not wait for a full transcript. |
| High | Flashing MIL, charging-system light, hybrid system warning with reduced power, stolen vehicle, repeat come-back, stop-sale recall, TSS unexpected braking | Fast dealer + roadside options. Surface VIN campaigns. |
| Medium | Steady MIL, TPMS, TSS inoperative, warranty denial, Service Connect alert, app/subscription failure | Schedule, explain coverage, conference dealer. |
| Low | ToyotaCare interval, Bluetooth, Destination Assist, how-to, loyalty | Knowledge-base answer; self-service; no supervisor alert. |

**Guardrails (Toyota analog to HIPAA / medication rules)**

- Never advise continued driving on red coolant or red oil pressure.
- Never advise opening a hot cooling system.
- Never treat SOS as concierge.
- Never quote a payoff or close a VSA claim from the BEC script; transfer.
- Never tell an owner a lemon-law outcome.
- Never claim a hybrid “doesn’t need oil.”
- Redact payment card, driver’s license, and exact live location in stored transcripts if the call is used for QA (Toyota already redacts via Contact Lens in the BEC AWS deployment).

---

## 7. Systems of record the agent (or the POC) should see

Toyota’s own BEC modernization is built around **guest + vehicle** in one pane. For this use case, the equivalent Databricks view is:

| Data | Why it matters on these two scenarios |
|---|---|
| VIN decode (year, model, engine, hybrid/BEV) | Overheat and oil procedures differ; towing rules differ |
| Safety Connect / Remote / Service Connect status | SOS GPS vs phone-only roadside |
| ToyotaCare / VSA / CPO roadside windows | Who pays for the tow |
| Last dealer RO (oil change yesterday) | Come-back routing |
| Open campaigns | Maybe the light is a known SSC/LSC |
| Service Connect Vehicle Health Report / DTCs | Confirm coolant temp, oil pressure, MIL codes instead of guessing from ASR |
| Preferred dealer + nearest open dealer + TCCC | Destination |
| Warranty in-service date and mileage | Engine damage coverage later |
| Emergency contact | ACN / SOS |

Service Connect already collects engine coolant temperature, oil life, DTCs, RPM, and hybrid battery data. That is the Toyota equivalent of an EHR feed: the assistant should not rely on the owner to pronounce “coolant” correctly.

---

## 8. Recommended scenarios to implement in this POC

The Databricks app now implements all ten of these as live demo scenarios, with matching synthetic audio, knowledge-base documents, evaluation examples, and stop-driving / routing guardrails. They are high-emotion, easy to demo, and map cleanly onto transcript + risk + citation + next-best-action.

| POC ID | Title | Maps from healthcare | Why it demos well |
|---|---|---|---|
| 1 | High coolant temperature, owner wants to keep driving | Symptom escalation | Critical guardrail: refuse unsafe advice, dispatch tow, nearest dealer |
| 2 | Engine + oil lights after dealer oil change, on a highway | Medication concern + symptom escalation | Come-back + safety + “who do I call?” |
| 3 | SOS / ACN occupant not responding | Urgent clinical escalation | Automatic emergency path |
| 4 | Dead 12-V in a hybrid, owner thinks HV battery died | Care navigation | Education + jump vs tow |
| 5 | Open safety recall, owner asking if they can drive | Care navigation | VIN campaign lookup |
| 6 | Warranty denied at dealer, owner angry | Billing confusion | BEC liaison + NCDS path, after safety is cleared |
| 7 | Safety Connect trial expired, SOS dark | Appointment / retention analog | Subscription restore |
| 8 | Destination Assist vs accidental SOS | Low-risk control | Teach routing; do not clog emergency line |
| 9 | Post-collision “where do I take it?” | Care navigation | TCCC vs insurer shop, Genuine parts, ADAS calibration |
| 10 | Service Connect alert: dealer is calling and owner wants it stopped | Privacy / HIPAA analog | Consent and opt-out |

Scenarios 1 and 2 are the `toyota_translation` pair and should be the primary demo.

---

## 9. What “a call center use case helps Toyota” actually means

From the owner’s first sentence in `toyota_translation`: *“How can a call center use case help Toyota?”*

A live agent-assist layer helps Toyota on these calls in five concrete ways:

1. **Stop the unsafe plan.** The owner’s instinct is to keep driving to an appointment. The assistant should detect “temperature too high” / “oil light” and force the stop-driving card before the agent improvises.
2. **Route to the right Toyota phone tree.** SOS vs 800-444-4195 vs 800-331-4331 vs the dealer vs TFS is the number-one owner confusion in both source scenarios.
3. **Attach the vehicle, not just the voice.** VIN, Service Connect DTCs, last RO, and Safety Connect GPS turn “I’m somewhere on the highway” into a dispatch.
4. **Treat come-backs as a retention event.** Lights after maintenance are how owners leave the brand. BEC already exists to work those cases with dealers; the assistant should open that case while roadside is rolling.
5. **Keep BEC on the high-value work.** Toyota already auto-routes and self-serves ~4% of BEC calls and cut transfers 13% with NLP. The remaining calls are the frightened, angry, or legally sensitive ones. Those are the ones this POC is for.

---

## 10. Sources

Public materials used to build this catalog (retrieved October 2026):

- Toyota contact / Brand Engagement Center: [toyota.com/support/contact-us](https://www.toyota.com/support/contact-us/)
- Toyota warning lights: [toyota.com/owners/warning-lights](https://www.toyota.com/owners/warning-lights)
- Toyota Connected Services, Safety Connect, Service Connect, Drive Connect, Remote Connect, Destination Assist: [toyota.com/connected-services](https://www.toyota.com/connected-services/) and [toyota.com/connected-services/toyota-app](https://www.toyota.com/connected-services/toyota-app/)
- Toyota Roadside Assistance (app / SOS / 1-800-444-4195): [support.toyota.com roadside article](https://support.toyota.com/s/article/Toyota-24MM-Roadside-Assistance)
- ToyotaCare maintenance and roadside: [toyota.com/maintenance-plans](https://www.toyota.com/maintenance-plans/) and [support.toyota.com ToyotaCare](https://support.toyota.com/s/article/How-can-I-view-my-Toy-10401)
- Warranty and Maintenance Guide (assistance path, immobilizer keys, Transportation Assistance, coverage terms): [2024 guide PDF](https://www.toyota.com/content/dam/toyota/brochures/pdf/2024/T-MMS-24_86.pdf) and [bZ4X guide](https://www.toyota.com/content/dam/toyota/brochures/pdf/2024/T-MMS-24bZ4X.pdf)
- Recalls and campaigns: [toyota.com/owners/recalls](https://www.toyota.com/owners/recalls/)
- Hybrid / EV battery warranty: [toyota.com/electrified-vehicles/warranty](https://www.toyota.com/electrified-vehicles/warranty/) and Toyota USA Newsroom, 10 October 2019
- Service Connect data and dealer-consent opt-out: [toyota.com/privacyvts](https://www.toyota.com/privacyvts/)
- Toyota Financial Services contact split: [toyotafinancial.com/us/en/contact_us.html](https://www.toyotafinancial.com/us/en/contact_us.html)
- Extra Care VSA: [toyotafinancial.com vehicle service agreements](https://www.toyotafinancial.com/us/en/vehicle_protection_plan/vehicle_service_agreements.html)
- NCDS / CDSP: [ncdsusa.org/clients/toyota.html](https://www.ncdsusa.org/clients/toyota.html)
- Toyota Certified Collision Centers: [toyota.com/owners/collision-center](https://www.toyota.com/owners/collision-center/)
- Toyota Mobility: [toyotamobility.toyota.com](https://toyotamobility.toyota.com/)
- Fleet contacts: 2026 Toyota Fleet Guide
- BEC scale, channels, Know Me Know My Vehicle: [AWS Toyota case study](https://aws.amazon.com/solutions/case-studies/toyota-case-study/)
- Safety Connect / Drivelink response centers: [Toyota Connected, Drivelink](https://toyotaconnected.com/insights/drivelink/)
- Owner’s-manual emergency procedures for overheating, oil pressure, and hybrid towing (RAV4 / Prius / bZ4X manuals)

Internal seed:

- `toyota_translation` — owner scenarios (coolant-temperature caution while in a hurry; engine + oil lights after maintenance on a highway)

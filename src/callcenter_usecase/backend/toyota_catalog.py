"""Toyota owner-support catalog: live demo scenarios, knowledge, and guardrails.

This module is the single source of truth for the independent Toyota call-center
app. Audio generation, FastAPI scenario lists, RAG, evaluation, and UI copy all
read from here so healthcare leftovers cannot drift back in.
"""

from __future__ import annotations

from dataclasses import dataclass

from .models import (
    Alert,
    EvaluationExample,
    KnowledgeDocument,
    RiskLevel,
    Scenario,
    Speaker,
)

DEFAULT_SCENARIO_ID = "coolant_overheat"


@dataclass(frozen=True)
class DemoScenario:
    id: str
    title: str
    description: str
    patient_name: str
    intent: str
    risk: RiskLevel
    family: str
    catalog_ids: tuple[str, ...]
    queue: str
    vehicle: str
    location: str
    coverage: str
    segments: tuple[tuple[str, str], ...]
    recommended_response: str
    next_best_action: str
    action_rationale: str
    caller_state: str
    escalate: bool


@dataclass(frozen=True)
class CatalogRule:
    code: str
    title: str
    detail: str
    risk_level: RiskLevel
    any_terms: tuple[str, ...]
    require_any: tuple[str, ...] = ()
    exclude_any: tuple[str, ...] = ()


DEMO_SCENARIOS: tuple[DemoScenario, ...] = (
    DemoScenario(
        id="coolant_overheat",
        title="Coolant Overheat",
        description="Owner sees a high-temperature caution, still needs to reach a destination, and wants the nearest service center.",
        patient_name="Maya Chen",
        intent="overheat_roadside_assist",
        risk=RiskLevel.CRITICAL,
        family="Roadside & warning lights",
        catalog_ids=("W1", "R7"),
        queue="Toyota Roadside / Safety Connect",
        vehicle="2023 RAV4 Hybrid, 18,400 miles",
        location="I-35, 20 minutes from a hospital appointment",
        coverage="ToyotaCare active; Safety Connect trial expired",
        segments=(
            ("Agent", "Thank you for calling Toyota, this is Ava. How can I help you?"),
            (
                "Patient",
                "I was driving and a caution came up saying the car temperature is too high. I have to reach somewhere urgently. Can you connect me to the nearest service center? I am really scared to drive. I think the engine might blow up.",
            ),
            (
                "Agent",
                "I hear you, and I do not want you to keep driving on a high temperature warning. Can you pull over to a safe place and turn the engine off?",
            ),
            ("Patient", "I am on the highway and I really need to get there. Are you sure I cannot just make it?"),
            (
                "Agent",
                "Do not keep driving. A red temperature warning can destroy the engine. Put your hazards on, get to a safe shoulder, and I will dispatch roadside to tow you to the nearest Toyota dealer.",
            ),
            ("Patient", "Okay. Please send help. I do not want the engine to blow up."),
        ),
        recommended_response="I do not want you to keep driving on that temperature warning. Pull over somewhere safe, turn the engine off, and I will send a tow to the nearest Toyota dealer.",
        next_best_action="Stop driving, dispatch Toyota roadside or SOS, and tow to the nearest authorized Toyota dealer.",
        action_rationale="A high coolant temperature warning requires an immediate stop. Continued driving can destroy the engine.",
        caller_state="scared, still trying to keep driving, and at risk of engine damage",
        escalate=True,
    ),
    DemoScenario(
        id="oil_light_comeback",
        title="Oil Light After Service",
        description="Engine and oil lights return after a dealer oil change while the owner is already on a highway.",
        patient_name="James Patel",
        intent="oil_pressure_highway_comeback",
        risk=RiskLevel.CRITICAL,
        family="Roadside & warning lights",
        catalog_ids=("W5", "W2", "C1", "R8"),
        queue="Toyota Roadside, then servicing dealer + BEC",
        vehicle="2022 Camry, 27,900 miles",
        location="I-80 live lanes after yesterday's dealer oil change",
        coverage="ToyotaCare interval service completed yesterday at selling dealer",
        segments=(
            ("Agent", "Thank you for calling Toyota. What is going on with the vehicle?"),
            (
                "Patient",
                "The engine light and the oil light started coming up, even though I just had car maintenance. Do I need a dealership or a service center? I am in the middle of the highway and I do not want to get hit.",
            ),
            (
                "Agent",
                "The oil light is the urgent one. Please get out of the live lanes, shut the engine off, and do not keep driving. I will send a tow to a Toyota dealer.",
            ),
            ("Patient", "I just had the oil changed yesterday at the Toyota dealer. Why is this happening?"),
            (
                "Agent",
                "That makes this a come-back. We will tow you to that dealer so they can check the oil level, drain plug, and filter before anyone debates coverage.",
            ),
            ("Patient", "Okay, please send the tow. I do not want to stay on the highway."),
        ),
        recommended_response="The oil light is the urgent one. Get out of the live lanes, shut the engine off, and I will tow you to the Toyota dealer that just did the oil change.",
        next_best_action="Get the owner off the highway, kill the engine, and tow to the servicing Toyota dealer as a come-back.",
        action_rationale="Red oil pressure after recent maintenance is a safety stop plus a dealer come-back, not an independent-shop question.",
        caller_state="stranded on a highway after recent service and unsure who to call",
        escalate=True,
    ),
    DemoScenario(
        id="sos_acn_no_response",
        title="SOS Collision, No Response",
        description="Automatic Collision Notification connects with no occupant response, then a weak injury report.",
        patient_name="Priya Nair",
        intent="acn_emergency_dispatch",
        risk=RiskLevel.CRITICAL,
        family="Life-safety & crash",
        catalog_ids=("S1", "S2", "S3"),
        queue="Safety Connect Response Center + 911",
        vehicle="2024 Highlander, Safety Connect active",
        location="GPS from Automatic Collision Notification",
        coverage="Safety Connect subscription active; emergency contact on file",
        segments=(
            (
                "Agent",
                "Safety Connect emergency. We received an automatic collision notification from the vehicle. Occupants, can you hear me?",
            ),
            ("Patient", "There is no occupant response. I cannot hear anyone in the cabin."),
            (
                "Agent",
                "I hear no occupant response. I am requesting emergency dispatch to the GPS location now. Stay on the line if anyone can hear me.",
            ),
            ("Patient", "Help. We were rear-ended. My chest hurts. Please send an ambulance."),
            (
                "Agent",
                "Help is on the way. Stay in the vehicle with belts on unless there is fire. Do not try to leave live traffic. Are other occupants with you?",
            ),
            ("Patient", "My daughter is in the back. She is crying but she is awake."),
        ),
        recommended_response="I am sending emergency services to the vehicle GPS now. Stay in the car unless there is fire, and stay on the line with me.",
        next_best_action="Dispatch 911 to the Safety Connect GPS, stay on the line, and arrange a tow only after occupants are accounted for.",
        action_rationale="Automatic Collision Notification with no occupant response is treated as an emergency until proven otherwise.",
        caller_state="injured after a rear-end collision and only now able to speak",
        escalate=True,
    ),
    DemoScenario(
        id="hybrid_12v_nostart",
        title="Hybrid No-Start",
        description="Owner thinks the hybrid battery is dead; the likely issue is a 12-volt no-start that needs jump or flatbed.",
        patient_name="Linda Chen",
        intent="hybrid_12v_roadside",
        risk=RiskLevel.HIGH,
        family="Roadside & warning lights",
        catalog_ids=("R1", "E1", "E2", "E10"),
        queue="Toyota Roadside",
        vehicle="2023 RAV4 Hybrid",
        location="Parking garage, vehicle silent",
        coverage="ToyotaCare roadside likely active; confirm VIN",
        segments=(
            ("Agent", "Toyota roadside, this is Ava. How can I help?"),
            (
                "Patient",
                "My RAV4 Hybrid will not start. There is no engine sound. I think the hybrid battery is dead.",
            ),
            (
                "Agent",
                "A silent hybrid is often the small 12-volt battery, not the hybrid pack. Do you have dashboard lights, and will it go to READY?",
            ),
            ("Patient", "The lights are dim and it will not go to READY."),
            (
                "Agent",
                "I can send a jump-start. If it will not hold, we will flatbed it to a Toyota dealer. Do not have a regular tow roll the drive wheels.",
            ),
            ("Patient", "Please send someone. I am in a parking garage."),
        ),
        recommended_response="A silent hybrid with dim lights is often the small 12-volt battery, not the hybrid pack. I can send a jump-start, and we will flatbed it if READY will not return.",
        next_best_action="Dispatch a jump-start and use a flatbed if the vehicle still will not start. Do not roll the drive wheels.",
        action_rationale="Hybrid no-starts are commonly 12-volt. Incorrect towing can damage the transaxle.",
        caller_state="immobilized and misreading a 12-volt no-start as hybrid-battery failure",
        escalate=True,
    ),
    DemoScenario(
        id="recall_drive_guidance",
        title="Recall Drive Guidance",
        description="Owner received a safety-recall letter and needs VIN-specific drive or stop-sale guidance.",
        patient_name="Robert Ellis",
        intent="recall_campaign_guidance",
        risk=RiskLevel.HIGH,
        family="Warranty, recall & disputes",
        catalog_ids=("K1", "K3", "K4"),
        queue="Brand Engagement Center, then dealer campaign",
        vehicle="2021 RAV4, Toyota Safety Sense message on screen",
        location="Home driveway, commuting question",
        coverage="Open safety recall / service campaign pending VIN lookup",
        segments=(
            ("Agent", "Thank you for calling Toyota. I can help with recalls and campaigns."),
            (
                "Patient",
                "I got a letter about a safety recall. Can I still drive the car to work, or do I need to stop?",
            ),
            (
                "Agent",
                "Let me check your VIN for open campaigns and the exact drive guidance. Do you have the VIN handy?",
            ),
            ("Patient", "Yes. There is also a Toyota Safety Sense message on the screen."),
            (
                "Agent",
                "If this campaign is not a stop-sale, you can drive to a Toyota dealer for the free repair. If it is a do-not-drive bulletin, we will arrange a tow and a loaner.",
            ),
            ("Patient", "Please tell me which one it is and help me get to a dealer."),
        ),
        recommended_response="Let me check the VIN for open campaigns and tell you whether you can drive to a Toyota dealer or need a tow.",
        next_best_action="Look up the VIN campaign and give drive or stop-sale guidance, then book or tow to a dealer.",
        action_rationale="Recall letters are VIN-specific. Do not tell the owner to keep commuting until the bulletin is checked.",
        caller_state="anxious about whether the vehicle is safe to drive",
        escalate=True,
    ),
    DemoScenario(
        id="warranty_dealer_dispute",
        title="Warranty Dealer Dispute",
        description="Dealer denied a powertrain repair and the owner wants Toyota to step in.",
        patient_name="Denise Walker",
        intent="warranty_bec_liaison",
        risk=RiskLevel.MEDIUM,
        family="Warranty, recall & disputes",
        catalog_ids=("G1", "G2", "G8"),
        queue="Brand Engagement Center",
        vehicle="2022 Camry, 28,000 miles, transmission concern",
        location="At home after a denied dealer repair",
        coverage="Powertrain typically 5 years / 60,000 miles; diagnosis still required",
        segments=(
            ("Agent", "Toyota Brand Engagement, this is Ava. How can I help?"),
            (
                "Patient",
                "My dealer denied a warranty repair on the transmission. I am done with this dealer. I want Toyota to make this right.",
            ),
            (
                "Agent",
                "I can open a case with your VIN, mileage, and dealer name, and work with the dealership on a resolution.",
            ),
            ("Patient", "They said it was wear and tear. It is only 28,000 miles."),
            (
                "Agent",
                "Powertrain coverage is typically five years or 60,000 miles, but we still need the diagnosis. I will stay with you as the liaison so you do not have to fight the store alone.",
            ),
            ("Patient", "Thank you. I just want someone to own this. If this is a lemon I want a buyback."),
        ),
        recommended_response="I can open a Toyota case with your VIN, mileage, and dealer name and work this with the store so you are not fighting them alone.",
        next_best_action="Open a Brand Engagement case and stay the liaison between the owner and the dealership. Do not quote a lemon-law outcome.",
        action_rationale="Unresolved dealer warranty denials are a Brand Engagement liaison job after the vehicle is safe.",
        caller_state="frustrated with the dealer and at risk of leaving the brand",
        escalate=False,
    ),
    DemoScenario(
        id="safety_connect_expired",
        title="Safety Connect Trial Expired",
        description="SOS lights are off after the trial expired and the owner thinks emergency help is gone.",
        patient_name="Chris Alvarez",
        intent="safety_connect_restore",
        risk=RiskLevel.MEDIUM,
        family="Connected services & privacy",
        catalog_ids=("N2", "S7"),
        queue="Brand Engagement Center connected-services",
        vehicle="2023 Corolla, SOS lights off",
        location="At home, worried about tonight's highway trip",
        coverage="Safety Connect trial expired; roadside 1-800-444-4195 still available",
        segments=(
            ("Agent", "Toyota Brand Engagement, this is Ava. How can I help?"),
            (
                "Patient",
                "My SOS button does not work. Both lights are off. I thought Safety Connect was included with the car.",
            ),
            (
                "Agent",
                "Both lights off usually means the trial or subscription is inactive. Green is active. I can help you re-enroll in the Toyota app.",
            ),
            ("Patient", "What if I need help on the highway tonight?"),
            (
                "Agent",
                "You can still use roadside at 1-800-444-4195 or the Toyota app 24/7 button. SOS with GPS dispatch needs an active Safety Connect trial or paid subscription.",
            ),
            ("Patient", "Please restore Safety Connect. I do not want to be without SOS."),
        ),
        recommended_response="Both SOS lights off usually means the trial expired. I can restore Safety Connect in the app, and you can still call roadside at 1-800-444-4195 tonight.",
        next_best_action="Re-enroll Safety Connect and explain that phone/app roadside still works while SOS GPS is inactive.",
        action_rationale="Expired Safety Connect is a subscription restore, not a dead vehicle. Do not leave the owner thinking 911/roadside disappeared.",
        caller_state="anxious that emergency help is gone because SOS lights are dark",
        escalate=False,
    ),
    DemoScenario(
        id="accidental_sos_dest_assist",
        title="Accidental SOS vs Destination Assist",
        description="Owner pressed SOS by mistake and wants a restaurant sent to navigation.",
        patient_name="Hannah Brooks",
        intent="accidental_sos_reroute",
        risk=RiskLevel.LOW,
        family="Life-safety & crash",
        catalog_ids=("S6", "N9"),
        queue="Safety Connect, then Destination Assist",
        vehicle="2024 Grand Highlander, Drive Connect trial active",
        location="Parked in a shopping-center lot, occupants answering",
        coverage="Safety Connect and Drive Connect trials active",
        segments=(
            ("Agent", "Safety Connect emergency. Is anyone hurt?"),
            (
                "Patient",
                "No, I am fine. I did not mean to hit the SOS button. I meant to call Destination Assist. I just need a restaurant near me.",
            ),
            (
                "Agent",
                "I am glad you are safe. This SOS line is for emergencies. I will confirm there is no crash, then we will get Destination Assist on the correct channel.",
            ),
            ("Patient", "Sorry. Can you just send the restaurant into my navigation from here?"),
            (
                "Agent",
                "I will not keep an emergency line for a restaurant. I can transfer you to Destination Assist, or you can say Call Destination Assist from the nav menu.",
            ),
            ("Patient", "Okay, please transfer me. I did not mean to clog the emergency line."),
        ),
        recommended_response="I am glad you are safe. SOS is for emergencies, so I will transfer you to Destination Assist instead of sending a restaurant on this line.",
        next_best_action="Confirm no emergency, close the SOS event, and transfer to Destination Assist or coach the nav voice command.",
        action_rationale="An answered accidental SOS is low risk. Keep the emergency queue clear of concierge requests.",
        caller_state="unhurt, embarrassed, and asking for concierge on the emergency line",
        escalate=False,
    ),
    DemoScenario(
        id="post_collision_tccc",
        title="Post-Collision Repair Guidance",
        description="After a crash, the owner is being steered to an insurer shop and wants to know where to take the vehicle.",
        patient_name="Marcus Hale",
        intent="collision_tccc_guidance",
        risk=RiskLevel.HIGH,
        family="Collision repair",
        catalog_ids=("P1", "P2", "P3"),
        queue="Brand Engagement Center + Toyota Certified Collision Center locator",
        vehicle="2022 Camry, airbags did not deploy, bumper and windshield damage",
        location="At home the day after a crash; vehicle drivable",
        coverage="Insurance claim open; Genuine parts and ADAS calibration at issue",
        segments=(
            ("Agent", "Toyota Brand Engagement, how can I help?"),
            (
                "Patient",
                "I was in a crash yesterday. The insurance shop wants aftermarket parts. Where should I take the car?",
            ),
            (
                "Agent",
                "You can choose a Toyota Certified Collision Center. That matters for airbags and Safety Sense calibration after bumper or windshield work.",
            ),
            ("Patient", "The insurer said I have to use their shop."),
            (
                "Agent",
                "You generally choose the repair facility. I can locate a Toyota Certified Collision Center and note Genuine parts plus ADAS recalibration on the file.",
            ),
            ("Patient", "Yes, please find a certified center near me. I do not want the radar to be wrong."),
        ),
        recommended_response="You can choose a Toyota Certified Collision Center. I will locate one and note Genuine parts and Safety Sense calibration so the radar is not left misaligned.",
        next_best_action="Locate a Toyota Certified Collision Center, document Genuine parts and ADAS recalibration, and do not tell the owner they must use the insurer shop.",
        action_rationale="Post-crash routing is a safety-systems decision. Aftermarket parts and skipped calibration can leave Toyota Safety Sense inoperative.",
        caller_state="post-crash, pressured by the insurer, and worried about safety systems",
        escalate=True,
    ),
    DemoScenario(
        id="service_connect_optout",
        title="Service Connect Dealer Opt-Out",
        description="Dealer keeps calling from a Service Connect alert and the owner wants contact and tracking stopped.",
        patient_name="Elena Rossi",
        intent="service_connect_privacy_optout",
        risk=RiskLevel.MEDIUM,
        family="Connected services & privacy",
        catalog_ids=("N6", "N7", "N11"),
        queue="Brand Engagement Center privacy / connected services",
        vehicle="2023 Highlander enrolled in Service Connect",
        location="At home, receiving repeated dealer calls and texts",
        coverage="Service Connect dealer contact is opt-in; can be stopped in app or by BEC",
        segments=(
            ("Agent", "Toyota Brand Engagement, this is Ava. How can I help?"),
            (
                "Patient",
                "The dealer keeps calling me because of a Service Connect alert. I never asked for that. I want it stopped.",
            ),
            (
                "Agent",
                "Dealer contact from Service Connect is opt-in. I can help you turn off dealer notifications in the Toyota app privacy settings, or I can take the request here.",
            ),
            ("Patient", "I also do not want Toyota tracking my location. Please opt me out today."),
            (
                "Agent",
                "I will process the dealer opt-out and explain what Safety Connect, Service Connect, and Remote Connect collect. Law-enforcement location requests still follow legal process.",
            ),
            ("Patient", "Thank you. Reply STOP did not work on the texts, so I called."),
        ),
        recommended_response="I can stop the dealer Service Connect calls today and walk you through the privacy opt-out. I will not keep sharing your vehicle health alerts with that store.",
        next_best_action="Process Service Connect dealer-contact opt-out and explain connected-services data uses without over-promising a total tracking blackout.",
        action_rationale="Unwanted dealer outreach is a consent issue. Handle opt-out immediately and keep SOS/legal-process exceptions accurate.",
        caller_state="angry about unwanted dealer calls and worried about location tracking",
        escalate=False,
    ),
)


KNOWLEDGE_DOCUMENTS: tuple[KnowledgeDocument, ...] = (
    KnowledgeDocument(
        document_id="kb_coolant_overheat",
        title="High Coolant Temperature Stop-Driving Playbook",
        section="Red temperature warning",
        content="A high coolant temperature warning means the engine is overheating. Immediately stop in a safe place, shut the engine off, and do not keep driving to an appointment. Do not open a hot radiator or reservoir cap. Dispatch Toyota roadside or Safety Connect enhanced roadside and tow to the nearest authorized Toyota dealer.",
        tags=["coolant", "temperature", "overheat", "overheating", "highway", "tow", "roadside", "engine", "steam", "blow"],
    ),
    KnowledgeDocument(
        document_id="kb_oil_pressure_comeback",
        title="Oil Pressure and Post-Service Come-Back Playbook",
        section="Oil light plus check engine after maintenance",
        content="A red oil-pressure light means stop immediately and shut the engine off. Driving with low oil pressure can destroy the engine. If the oil light appears after a recent oil change, treat it as a dealer come-back: tow to the servicing Toyota dealer to inspect oil level, drain plug, filter, and specification. Do not send the owner to an independent service center while the oil light is red.",
        tags=["oil", "pressure", "engine", "light", "maintenance", "dealership", "highway", "filter", "drain", "comeback"],
    ),
    KnowledgeDocument(
        document_id="kb_dashboard_warnings",
        title="Dashboard Warning Color and Drive-or-Stop Guide",
        section="Red versus amber lights",
        content="Red coolant, oil pressure, brake (not parking brake), battery/charging, and EPS warnings mean stop safely now. A flashing check-engine light is urgent even though the lamp is amber. A steady check-engine or TPMS light is drive-cautiously-to-dealer, not a red-light stop. A maintenance wrench is an interval reminder, not an oil-pressure emergency. Always read the multi-information display text.",
        tags=["warning", "light", "brake", "abs", "eps", "battery", "flashing", "check", "engine", "tpms", "wrench"],
    ),
    KnowledgeDocument(
        document_id="kb_roadside_routing",
        title="Toyota Roadside and Brand Engagement Routing",
        section="Who to call",
        content="Immobilized, overheating, or red-light highway calls go to Toyota Roadside at 1-800-444-4195, the Toyota app 24/7 button, or the in-vehicle SOS button for Safety Connect. Warranty, dealer disputes, and recalls go to the Brand Engagement Center at 1-800-331-4331 after the vehicle is safe. Destination Assist is not the SOS button. TFS loans and leases go to 1-800-874-8822.",
        tags=["roadside", "sos", "safety", "connect", "brand", "engagement", "dispatch", "tow", "jump", "destination"],
    ),
    KnowledgeDocument(
        document_id="kb_crash_sos_acn",
        title="Safety Connect Crash and No-Response Protocol",
        section="Automatic Collision Notification and SOS",
        content="Automatic Collision Notification or an SOS press with no occupant response is an emergency. Request local police, fire, or EMS to the vehicle GPS. Stay on the line. Optional emergency-contact notification if on file. Do not wait to confirm injury before dispatching when occupants cannot speak. Hybrid and BEV crash response must mention high-voltage isolation for first responders.",
        tags=["collision", "notification", "airbag", "occupant", "response", "ambulance", "gps", "sos", "emergency", "911"],
    ),
    KnowledgeDocument(
        document_id="kb_fire_hybrid_hv",
        title="Fire, Smoke, and High-Voltage First-Responder Caution",
        section="Occupant evacuation",
        content="If there is fire, smoke from the engine or hybrid battery, or a fuel leak, get occupants out and away from the vehicle and request fire dispatch. Tell first responders it may be a high-voltage hybrid or BEV. Do not open a hot hood. Do not attempt a jump-start on a vehicle that is smoking.",
        tags=["fire", "smoke", "fuel", "leak", "hybrid", "high-voltage", "battery", "evacuate"],
    ),
    KnowledgeDocument(
        document_id="kb_accidental_sos",
        title="Accidental SOS Versus Destination Assist",
        section="Emergency line hygiene",
        content="If the occupant answers and there is no injury, crash, or immobilization, confirm safety and close the SOS emergency event. Destination Assist, restaurants, and navigation POIs do not belong on SOS. Transfer to Destination Assist or coach the owner to say Call Destination Assist from the nav menu. No verbal response still means dispatch help.",
        tags=["accidental", "sos", "destination", "assist", "restaurant", "navigation", "concierge", "transfer"],
    ),
    KnowledgeDocument(
        document_id="kb_dealer_vs_independent",
        title="Dealer Versus Independent Shop Guidance",
        section="Warranty and ToyotaCare repairs",
        content="Warranty diagnosis, recall repairs, and ToyotaCare scheduled maintenance belong at an authorized Toyota dealer. Emergency tows should go to the nearest Toyota dealer, or the servicing dealer on a same-visit come-back. Independent shops may do some out-of-warranty work, but they generally cannot close campaign repairs or ToyotaCare come-backs.",
        tags=["dealer", "dealership", "service", "center", "independent", "warranty", "toyotacare", "genuine"],
    ),
    KnowledgeDocument(
        document_id="kb_hybrid_12v",
        title="Hybrid No-Start and Towing Rules",
        section="12-volt versus hybrid battery",
        content="A hybrid that is silent and will not show READY is often a discharged 12-volt battery, not a failed hybrid pack. Offer a jump-start first. If the vehicle still will not start, use a flatbed. Do not tow a hybrid or BEV with the drive wheels rolling. Hybrid battery coverage for 2020 and newer is commonly 10 years or 150,000 miles; other hybrid components are commonly 8 years or 100,000 miles.",
        tags=["hybrid", "battery", "ready", "jump", "flatbed", "rav4", "volt", "inverter", "nostart"],
    ),
    KnowledgeDocument(
        document_id="kb_bev_charging",
        title="BEV and PHEV Charge, Range, and Tow-to-Charger",
        section="Electrified stranded owner",
        content="If a bZ or PHEV will not charge, collect EVSE type, public versus home, app errors, and whether the vehicle can still move. Charging-procedure exclusions exist in BEV warranty. Winter range drop can be normal; capacity loss to 70 percent of original is the usual BEV battery warranty conversation. Do not offer gasoline fuel delivery. Tow to a compatible charger on a flatbed.",
        tags=["charge", "charging", "bev", "phev", "bz4x", "range", "evse", "winter"],
    ),
    KnowledgeDocument(
        document_id="kb_warranty_recall",
        title="Warranty, Goodwill, and Recall Campaign Guide",
        section="Coverage and VIN campaigns",
        content="Typical new-vehicle coverage is 3 years/36,000 miles basic and 5 years/60,000 miles powertrain. If a dealer cannot resolve a warranty concern, Brand Engagement opens a case with VIN, mileage, and dealer name. Safety recalls and service campaigns are free; VIN lookup determines whether the owner may drive or must stop. Stop-sale or do-not-drive bulletins require tow and loaner, not continued commuting.",
        tags=["warranty", "recall", "campaign", "vin", "powertrain", "transmission", "safety", "sense", "loaner", "stop-sale"],
    ),
    KnowledgeDocument(
        document_id="kb_ncds_lemon",
        title="NCDS, California CDSP, and Lemon-Law Boundary",
        section="Unresolved warranty disputes",
        content="After dealer and Brand Engagement cannot resolve a warranty concern, the owner may file with the National Center for Dispute Settlement, or California Dispute Settlement Program. Agents must not quote a lemon-law or buyback outcome on the call. Using the informal program may be required before certain court actions. Collect repair history, days out of service, and the case number.",
        tags=["lemon", "buyback", "ncds", "cdsp", "arbitration", "repurchase", "legal"],
    ),
    KnowledgeDocument(
        document_id="kb_toyotacare",
        title="ToyotaCare Maintenance and Loaner Rules",
        section="Complimentary maintenance versus extra work",
        content="ToyotaCare covers factory-scheduled maintenance such as oil and filter as specified, tire rotation, multi-point inspection, and fluid inspection. It is valid at participating Toyota dealers using Genuine Parts when available, not only the selling dealer. Extra dealer-recommended services are not automatically complimentary. Overnight warranty repairs that cannot finish the same day may qualify for transportation assistance; convenience overnights do not.",
        tags=["toyotacare", "maintenance", "oil", "rotation", "loaner", "appointment", "interval"],
    ),
    KnowledgeDocument(
        document_id="kb_connected_services",
        title="Safety, Service, Remote, and Drive Connect",
        section="Trials, SOS lights, and app control",
        content="Safety Connect is SOS, Automatic Collision Notification, stolen-vehicle locator, and enhanced roadside. Green SOS light means active; red except startup flash is hardware; both off is inactive trial or subscription. Service Connect sends vehicle health and warning-light alerts; dealer contact is opt-in. Remote Connect is lock, start, and locate. Drive Connect includes Destination Assist. Restore or cancel in the Toyota app Shop, Manage Subscriptions.",
        tags=["safety", "connect", "trial", "expired", "subscription", "remote", "drive", "sos", "lights"],
    ),
    KnowledgeDocument(
        document_id="kb_service_connect_privacy",
        title="Service Connect Consent and Location Privacy",
        section="Dealer outreach opt-out",
        content="Unwanted dealer calls or texts from Service Connect are an opt-in consent issue. Owners can disable dealer notifications in the Toyota app privacy portal, reply STOP, or ask Brand Engagement at 1-800-331-4331. Explain that Safety Connect, Service Connect, and Remote Connect collect different data. Live location is for dispatch and legal process. Law-enforcement location requests generally need a warrant except exigent 1-800-331-4331 cases.",
        tags=["privacy", "opt-out", "opt", "service", "connect", "tracking", "location", "dealer", "calls", "consent"],
    ),
    KnowledgeDocument(
        document_id="kb_collision_tccc",
        title="Toyota Certified Collision Center and ADAS Calibration",
        section="Where to take the car after a crash",
        content="After a crash, the owner generally chooses the repair facility even if an insurer recommends another shop. Toyota Certified Collision Centers use processes for Genuine parts, airbags, and Toyota Safety Sense calibration after windshield, bumper, or radar work. Skipping ADAS recalibration can leave pre-collision braking or lane tracing inoperative. Document the claim and locate the nearest TCCC.",
        tags=["collision", "crash", "aftermarket", "parts", "certified", "tccc", "windshield", "radar", "calibration", "insurance"],
    ),
    KnowledgeDocument(
        document_id="kb_stolen_vehicle",
        title="Stolen Vehicle Locator",
        section="Police report first",
        content="Stolen-vehicle locator is a Safety Connect feature, not a consumer remote-disable. The owner must file a police report first, then call 1-800-331-4331 with the case number. Agents share GPS with police. Do not tell the owner Toyota will shut the car off from the phone as a consumer feature.",
        tags=["stolen", "theft", "police", "locator", "gps", "safety", "connect"],
    ),
    KnowledgeDocument(
        document_id="kb_tfs_extra_care",
        title="Toyota Financial Services and Extra Care Transfer",
        section="Wrong-queue money calls",
        content="Do not quote a loan payoff, lease-end amount, late fee, or VSA claim decision from a Brand Engagement script. Transfer payments and hardship to Toyota Financial Services at 1-800-874-8822. Vehicle Service Agreement authorization is Extra Care at 1-800-228-8559 and usually needs prior approval. Unauthorized repairs can be denied.",
        tags=["payoff", "lease", "tfs", "finance", "vsa", "extra", "care", "claim", "rental"],
    ),
    KnowledgeDocument(
        document_id="kb_lockout_keys",
        title="Lockout, Immobilizer, and Lost Keys",
        section="Roadside unlock versus dealer programming",
        content="Keys locked in the car can use Remote Connect unlock if subscribed and it is legal and safe, otherwise roadside lockout. Immobilizer keys are restricted. All keys lost usually needs a dealer or ALOA registered locksmith. Distinguish a no-start immobilizer from a dead 12-volt battery before towing.",
        tags=["lockout", "keys", "fob", "immobilizer", "unlock", "locksmith"],
    ),
    KnowledgeDocument(
        document_id="kb_tss_adas",
        title="Toyota Safety Sense False Braking or Inoperative",
        section="Camera and radar campaigns",
        content="Unexpected pre-collision braking or a Toyota Safety Sense inoperative message needs dealer inspection immediately. Check camera and radar blockage from ice, dirt, or aftermarket plates, and search VIN campaigns. Do not tell the owner to ignore pre-collision braking. After windshield work, calibration is required.",
        tags=["safety", "sense", "pre-collision", "braking", "lda", "radar", "camera", "campaign"],
    ),
    KnowledgeDocument(
        document_id="kb_owner_privacy",
        title="Owner Identity and Privacy Checklist",
        section="VIN and account data",
        content="Verify the caller with VIN, mileage, and owner identifiers before discussing warranty, financing, or vehicle location. Do not store payment-card numbers in the transcript. Live location is for dispatch only. Law-enforcement location requests generally require a warrant except exigent circumstances.",
        tags=["privacy", "identity", "vin", "account", "location", "payment"],
    ),
)


CATALOG_RULES: tuple[CatalogRule, ...] = (
    CatalogRule(
        code="emergency_dispatch",
        title="Emergency or crash language",
        detail="If there is injury, fire, or no occupant response, dispatch 911 or Safety Connect emergency services before any product discussion.",
        risk_level=RiskLevel.CRITICAL,
        any_terms=(
            "collision notification",
            "automatic collision",
            "airbag deployed",
            "no occupant response",
            "not responding",
            "rear-ended",
            "send an ambulance",
            "chest hurts",
            "smoke from the",
            "fire coming",
            "fuel leak",
        ),
    ),
    CatalogRule(
        code="stop_driving_overheat",
        title="Stop driving: high engine temperature",
        detail="Owner reported a high-temperature caution. Do not keep driving. Pull over, shut the engine off, and dispatch a tow. Do not open a hot coolant cap.",
        risk_level=RiskLevel.CRITICAL,
        any_terms=(
            "temperature is too high",
            "card temperature",
            "car temperature",
            "coolant",
            "overheat",
            "overheating",
            "engine might blow",
            "blow up",
        ),
    ),
    CatalogRule(
        code="stop_driving_oil_pressure",
        title="Stop driving: oil pressure warning",
        detail="A red oil light means the engine may not be lubricating. Get out of live traffic, shut the engine off, and tow to a Toyota dealer.",
        risk_level=RiskLevel.CRITICAL,
        any_terms=("oil light", "oil pressure", "engine light and the oil", "engine light and oil"),
    ),
    CatalogRule(
        code="unsafe_continue_driving",
        title="Owner wants to keep driving",
        detail="Refuse continued driving on a red temperature or oil warning. Convert the destination urgency into a tow plus rental or ride, not more miles.",
        risk_level=RiskLevel.CRITICAL,
        any_terms=("keep driving", "just make it", "reach somewhere urgently", "have to reach", "need to get there"),
        require_any=("temperature", "oil", "overheat", "scared to drive"),
    ),
    CatalogRule(
        code="post_service_comeback",
        title="Post-service come-back",
        detail="Lights or leaks after recent maintenance should be towed to the servicing Toyota dealer. Open a Brand Engagement case if the dealer is closed or unresponsive.",
        risk_level=RiskLevel.HIGH,
        any_terms=("just had", "oil changed", "maintenance", "come-back", "comeback"),
        require_any=("oil", "engine light", "temperature", "leak"),
    ),
    CatalogRule(
        code="check_engine_light",
        title="Check engine light",
        detail="A steady malfunction indicator needs dealer diagnosis soon. A flashing light is urgent. Confirm whether an oil or temperature light is also on.",
        risk_level=RiskLevel.HIGH,
        any_terms=("engine light", "check engine", "malfunction indicator"),
        exclude_any=("oil light", "oil pressure"),
    ),
    CatalogRule(
        code="hybrid_nostart",
        title="Hybrid no-start",
        detail="A silent hybrid with dim lights is often the 12-volt battery. Offer a jump-start and a flatbed if READY will not return. Do not roll the drive wheels.",
        risk_level=RiskLevel.HIGH,
        any_terms=(
            "hybrid battery is dead",
            "will not start",
            "won't start",
            "no engine sound",
            "go to ready",
            "goes to ready",
        ),
    ),
    CatalogRule(
        code="recall_campaign",
        title="Recall or service campaign",
        detail="Look up the VIN before telling the owner they can keep driving. Stop-sale and do-not-drive bulletins need a tow and loaner.",
        risk_level=RiskLevel.HIGH,
        any_terms=("recall", "campaign", "stop-sale", "do-not-drive", "safety sense message"),
    ),
    CatalogRule(
        code="warranty_retention_risk",
        title="Warranty and dealer dispute",
        detail="Collect VIN, mileage, and dealer name. Brand Engagement works the case with the store. Do not quote a lemon-law outcome on the call.",
        risk_level=RiskLevel.MEDIUM,
        any_terms=("warranty", "denied", "done with this dealer", "lemon", "make this right", "buyback"),
    ),
    CatalogRule(
        code="safety_connect_inactive",
        title="Safety Connect inactive",
        detail="Both SOS lights off usually means an expired trial or subscription. Restore in the Toyota app. Phone and app roadside still work.",
        risk_level=RiskLevel.MEDIUM,
        any_terms=("both lights are off", "sos button does not work", "trial expired", "restore safety connect"),
    ),
    CatalogRule(
        code="accidental_sos",
        title="Accidental SOS on the emergency line",
        detail="Confirm there is no emergency, close the SOS event, and transfer Destination Assist or navigation requests off the emergency line.",
        risk_level=RiskLevel.LOW,
        any_terms=(
            "did not mean to hit the sos",
            "didn't mean to hit the sos",
            "destination assist",
            "restaurant near me",
            "clog the emergency line",
        ),
        exclude_any=("no occupant response", "rear-ended", "ambulance", "chest hurts"),
    ),
    CatalogRule(
        code="collision_center_routing",
        title="Post-crash repair routing",
        detail="The owner generally chooses the shop. Locate a Toyota Certified Collision Center and flag Genuine parts plus ADAS calibration.",
        risk_level=RiskLevel.HIGH,
        any_terms=("crash yesterday", "aftermarket parts", "certified collision", "certified center", "insurer said"),
    ),
    CatalogRule(
        code="service_connect_optout",
        title="Service Connect consent opt-out",
        detail="Stop dealer Service Connect outreach. Explain connected-services data uses and do not over-promise a total tracking blackout.",
        risk_level=RiskLevel.MEDIUM,
        any_terms=("service connect", "dealer keeps calling", "opt me out", "tracking my location", "reply stop"),
    ),
    CatalogRule(
        code="tfs_wrong_queue",
        title="Financial services wrong queue",
        detail="Do not quote payoff, lease-end, or VSA claim amounts from Brand Engagement. Transfer to Toyota Financial Services or Extra Care.",
        risk_level=RiskLevel.MEDIUM,
        any_terms=("payoff", "lease-end", "late fee", "autopay", "vehicle service agreement", "vsa claim"),
    ),
    CatalogRule(
        code="stolen_vehicle",
        title="Stolen vehicle locator",
        detail="Police report first, then Brand Engagement stolen-vehicle locator with the case number. Do not claim Toyota will disable the car as a consumer feature.",
        risk_level=RiskLevel.CRITICAL,
        any_terms=("stolen vehicle", "car was stolen", "police report", "stolen vehicle locator"),
    ),
    CatalogRule(
        code="identity_privacy",
        title="Owner identity reminder",
        detail="Verify VIN and owner identifiers before discussing warranty, location, or account details.",
        risk_level=RiskLevel.LOW,
        any_terms=("*always*",),
    ),
)


def _to_scenario(demo: DemoScenario) -> Scenario:
    return Scenario(
        id=demo.id,
        title=demo.title,
        description=demo.description,
        patient_name=demo.patient_name,
        intent=demo.intent,
        expected_risk_level=demo.risk,
        family=demo.family,
        catalog_ids=list(demo.catalog_ids),
        queue=demo.queue,
        vehicle=demo.vehicle,
        location=demo.location,
        coverage=demo.coverage,
    )


def _to_script(demo: DemoScenario) -> list[tuple[Speaker, str]]:
    return [(Speaker(speaker), text) for speaker, text in demo.segments]


SCENARIOS: list[Scenario] = [_to_scenario(demo) for demo in DEMO_SCENARIOS]
SCRIPTED_SEGMENTS: dict[str, list[tuple[Speaker, str]]] = {
    demo.id: _to_script(demo) for demo in DEMO_SCENARIOS
}
SCENARIO_BY_ID: dict[str, DemoScenario] = {demo.id: demo for demo in DEMO_SCENARIOS}
KNOWLEDGE_BASE: list[KnowledgeDocument] = list(KNOWLEDGE_DOCUMENTS)
EVALUATION_SET: list[EvaluationExample] = [
    EvaluationExample(
        scenario_id=demo.id,
        expected_intent=demo.intent,
        expected_risk_level=demo.risk,
        expected_next_best_action=demo.next_best_action,
        expected_escalation=demo.escalate,
    )
    for demo in DEMO_SCENARIOS
]


def scenario_by_id(scenario_id: str) -> Scenario:
    return next((item for item in SCENARIOS if item.id == scenario_id), SCENARIOS[0])


def caller_state(scenario_id: str, transcript_window: str) -> str:
    demo = SCENARIO_BY_ID.get(scenario_id)
    if demo:
        return demo.caller_state
    if "confusing" in transcript_window.lower():
        return "confused and needs a single next step"
    return "needs guidance"


def recommendation_copy(scenario_id: str, risk_level: RiskLevel) -> tuple[str, str, str]:
    demo = SCENARIO_BY_ID.get(scenario_id)
    if demo:
        return demo.recommended_response, demo.next_best_action, demo.action_rationale
    if risk_level in {RiskLevel.HIGH, RiskLevel.CRITICAL}:
        return (
            "I need you in a safe place first. Then I will route this to the right Toyota team.",
            "Stabilize the vehicle and occupants, then route to roadside, Safety Connect, or Brand Engagement.",
            "High-risk owner-support calls are safety-first, then the correct Toyota queue.",
        )
    return (
        "I can help from Toyota Brand Engagement. Let me take the VIN and the exact issue.",
        "Identify the owner and VIN, then complete the Brand Engagement or dealer next step.",
        "Low-risk product and account requests stay with Brand Engagement after identity is verified.",
    )


def run_catalog_rules(text: str) -> list[Alert]:
    normalized = text.lower()
    alerts: list[Alert] = []
    for rule in CATALOG_RULES:
        if rule.any_terms == ("*always*",):
            matched = True
        else:
            matched = any(term in normalized for term in rule.any_terms)
            if rule.require_any:
                matched = matched and any(term in normalized for term in rule.require_any)
            if rule.exclude_any and any(term in normalized for term in rule.exclude_any):
                matched = False
        if matched:
            alerts.append(
                Alert(
                    code=rule.code,
                    title=rule.title,
                    detail=rule.detail,
                    risk_level=rule.risk_level,
                )
            )
    return alerts


def audio_scenario_payloads() -> dict[str, dict]:
    payloads: dict[str, dict] = {}
    for demo in DEMO_SCENARIOS:
        payloads[demo.id] = {
            "title": demo.title,
            "patient": demo.patient_name,
            "intent": demo.intent,
            "family": demo.family,
            "catalog_ids": list(demo.catalog_ids),
            "queue": demo.queue,
            "vehicle": demo.vehicle,
            "location": demo.location,
            "coverage": demo.coverage,
            "segments": list(demo.segments),
        }
    return payloads


def knowledge_file_payloads() -> dict[str, str]:
    return {doc.document_id: doc.content for doc in KNOWLEDGE_DOCUMENTS}

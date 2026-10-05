import os
import pptx
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor

# Open the presentation
src_pptx = "Progress_Presentation_Redesigned_backup.pptx"
tgt_pptx = "Progress_Presentation_Redesigned.pptx"
prs = pptx.Presentation(src_pptx)

def update_shape_text(shape, new_text, font_size_pt=None, bold=None, font_name="Arial", text_color=None):
    if not shape.has_text_frame:
        return
    tf = shape.text_frame
    tf.word_wrap = True
    if not tf.paragraphs:
        return
    
    # If new_text has multiple lines (paragraphs)
    lines = new_text.split("\n")
    
    # Store style from existing first run if available
    orig_font_name = font_name
    orig_size = Pt(font_size_pt) if font_size_pt else None
    orig_bold = bold
    orig_color = text_color
    
    p0 = tf.paragraphs[0]
    if p0.runs:
        r0 = p0.runs[0]
        if not orig_font_name and r0.font.name:
            orig_font_name = r0.font.name
        if not orig_size and r0.font.size:
            orig_size = r0.font.size
        if orig_bold is None and r0.font.bold is not None:
            orig_bold = r0.font.bold
        if not orig_color and r0.font.color and r0.font.color.type == 1:
            orig_color = r0.font.color.rgb

    # Clear text frame
    p0.text = ""
    for extra_p in list(tf.paragraphs)[1:]:
        # cannot easily delete paragraphs in python-pptx, so we set their text to empty
        extra_p.text = ""

    # Re-populate paragraphs
    for idx, line in enumerate(lines):
        if idx == 0:
            p = p0
        else:
            p = tf.add_paragraph()
        p.text = line
        if p.runs:
            r = p.runs[0]
            if orig_font_name: r.font.name = orig_font_name
            if orig_size: r.font.size = orig_size
            if orig_bold is not None: r.font.bold = orig_bold
            if orig_color: r.font.color.rgb = orig_color

# Helper to find shape by name or text in slide
def find_shape_by_name(slide, name):
    for s in slide.shapes:
        if s.name == name:
            return s
    return None

def find_shape_by_text_fragment(slide, fragment):
    for s in slide.shapes:
        if s.has_text_frame and fragment in s.text_frame.text:
            return s
    return None

print(f"Loaded presentation: {len(prs.slides)} slides.")

# ==============================================================================
# SLIDE 1: Title Slide
# ==============================================================================
s1 = prs.slides[0]
for sh in s1.shapes:
    if not sh.has_text_frame: continue
    t = sh.text_frame.text.strip()
    if "[Project Title]" in t:
        update_shape_text(sh, "Rule-Based Cooperative Highway Ramp Merging for CAVs", font_size_pt=28, bold=True)
    elif "Progress Presentation" in t:
        update_shape_text(sh, "Minor Project Mid-Semester Progress Evaluation", font_size_pt=18, bold=False)
    elif "[Name 1]" in t or "Group Members" in t:
        if "[Name 1]" in t:
            update_shape_text(sh, "Pranjal Gupta  •  Swagata Barik  •  Aryan Dubey", font_size_pt=13, bold=True)
    elif "[Supervisor Name]" in t:
        update_shape_text(sh, "Dr. Debanjan Das", font_size_pt=13, bold=True)
    elif "[Date]" in t:
        update_shape_text(sh, "IIIT Naya Raipur  •  October 2026", font_size_pt=12, bold=False)
    elif "A clearer story" in t:
        update_shape_text(sh, "Distributed Consensus CACC with Event-Triggered Communication & Safety Fail-Safe", font_size_pt=12, bold=False)

# ==============================================================================
# SLIDE 2: Roadmap
# ==============================================================================
s2 = prs.slides[1]
for sh in s2.shapes:
    if not sh.has_text_frame: continue
    t = sh.text_frame.text.strip()
    if "A compact narrative" in t:
        update_shape_text(sh, "A structured research journey: establishing the merging bottleneck, identifying communication gaps, presenting event-triggered CACC, and demonstrating empirical evidence.")
    elif "What problem are we solving?" in t:
        update_shape_text(sh, "Highway on-ramp bottlenecks & CAV cooperative speed harmonization")
    elif "Why existing approaches are not enough" in t:
        update_shape_text(sh, "Wireless channel saturation & vulnerability to packet drop")
    elif "How the proposed system works" in t:
        update_shape_text(sh, "Virtual platoon sequencing + event-triggered consensus CACC")
    elif "How performance will be measured" in t:
        update_shape_text(sh, "Microscopic SUMO/TraCI co-simulation & packet loss benchmarks")
    elif "What remains before completion" in t:
        update_shape_text(sh, "Multi-lane scaling, mixed autonomy, and saturation capacity testing")
    elif "Source structure retained" in t:
        update_shape_text(sh, "Presentation Narrative Flow")
    elif "Introduction → Motivation" in t:
        update_shape_text(sh, "Context → Motivation → Literature Review → Problem Definition → Objectives → Methodology → Simulation Setup → Results & Discussion → Action Plan → Conclusion")

# ==============================================================================
# SLIDE 3: Context & Introduction
# ==============================================================================
s3 = prs.slides[2]
for sh in s3.shapes:
    if not sh.has_text_frame: continue
    t = sh.text_frame.text.strip()
    if "Use this slide to establish" in t:
        update_shape_text(sh, "Cooperative Automated Driving (CAD) orchestrates multi-agent vehicle merges to eliminate freeway bottleneck congestion.")
    elif "[2–3 lines on the domain" in t:
        update_shape_text(sh, "Highway on-ramps account for over 30% of freeway congestion and elevated collision risks. Asymmetric vehicle streams demand cooperative right-of-way negotiation.")
    elif "[What is happening today?" in t:
        update_shape_text(sh, "Human drivers execute selfish, abrupt lane insertions causing upstream shockwaves and phantom jams. Unconnected ACC systems operate reactively without inter-lane preview.")
    elif "[What exactly is included?" in t:
        update_shape_text(sh, "In scope: 100% CAV penetration, single-lane ramp and highway, dynamic merge speed estimation, virtual sequencing, and event-triggered CACC. Out of scope: human-driven vehicles and multi-lane weaving.")
    elif "[What artifact, model," in t:
        update_shape_text(sh, "An end-to-end SUMO/TraCI co-simulation framework, event-triggered V2V communication protocol with dead reckoning, and exhaustive benchmarking under ideal and lossy wireless links.")
    elif "“We investigate [problem]" in t:
        update_shape_text(sh, "“We investigate cooperative CAV highway ramp merging using virtual platoon sequencing and event-triggered consensus CACC to achieve 100% collision-free merging with ~90% communication overhead reduction.”")

# ==============================================================================
# SLIDE 4: Motivation: Issues & Challenges
# ==============================================================================
s4 = prs.slides[3]
for sh in s4.shapes:
    if not sh.has_text_frame: continue
    t = sh.text_frame.text.strip()
    if "Turn the motivation into" in t:
        update_shape_text(sh, "Addressing moving bottleneck conflicts while resolving physical safety and wireless channel congestion.")
    elif "What makes the existing task difficult?" in t:
        update_shape_text(sh, "Asymmetric entry speeds (25 m/s highway vs 15 m/s ramp) cause severe deceleration waves at the merge point without anticipatory speed harmonization.")
    elif "Data, compute, latency," in t:
        update_shape_text(sh, "DSRC / C-V2X 5.9 GHz channels experience packet collision, transmission latency, and interference as vehicle density escalates under periodic 10 Hz broadcast.")
    elif "Who is affected and what changes" in t:
        update_shape_text(sh, "Commuters face stop-and-go delays and elevated collision risks; cooperative merging increases highway corridor capacity by 20–40% and ensures zero collisions.")
    elif "[State the strongest reason" in t:
        update_shape_text(sh, "With emerging V2X standards (C-V2X Rel-16) and commercial automated vehicle deployment, merging controllers must be bandwidth-frugal and resilient to real packet loss.")
    elif "From “current limitation”" in t:
        update_shape_text(sh, "From channel-saturating 10 Hz periodic broadcasting → to bandwidth-efficient event-triggered communication with dead-reckoning safety guarantees.")

# ==============================================================================
# SLIDE 5: Literature Review
# ==============================================================================
s5 = prs.slides[4]
for sh in s5.shapes:
    if not sh.has_text_frame: continue
    t = sh.text_frame.text.strip()
    if "Keep only studies that directly inform" in t:
        update_shape_text(sh, "Critical comparison of leading cooperative merging, CACC platooning, and event-triggered control methodologies.")
    # Headers
    elif "Database used" in t:
        update_shape_text(sh, "Evaluation Platform")
    elif "Accuracy / Measures" in t:
        update_shape_text(sh, "Performance Metric")
    # Row 1: Wang et al.
    elif sh.name == "Text 15" and "[Author, Year]" in t:
        update_shape_text(sh, "Wang et al. (2020)")
    elif sh.name == "Text 17" and "[Method / model]" in t:
        update_shape_text(sh, "Consensus CACC + RSU")
    elif sh.name == "Text 19" and "[Dataset]" in t:
        update_shape_text(sh, "SUMO Simulation")
    elif sh.name == "Text 21" and "[Metric]" in t:
        update_shape_text(sh, "0 Collisions (Ideal)")
    elif sh.name == "Text 23" and "[What it does well" in t:
        update_shape_text(sh, "Proposes dynamic merge speed & virtual sequence; assumes ideal 0-loss, 0-delay V2X with no channel optimization")
    # Row 2: Milanes et al.
    elif sh.name == "Text 25" and "[Author, Year]" in t:
        update_shape_text(sh, "Milanes et al. (2014)")
    elif sh.name == "Text 27" and "[Method / model]" in t:
        update_shape_text(sh, "Empirical CACC Platoon")
    elif sh.name == "Text 29" and "[Dataset]" in t:
        update_shape_text(sh, "Real Vehicle Fleet")
    elif sh.name == "Text 31" and "[Metric]" in t:
        update_shape_text(sh, "String Stability (10 Hz)")
    elif sh.name == "Text 33" and "[What it does well" in t:
        update_shape_text(sh, "Demonstrated stable vehicle following in real traffic; limited to single-lane following without ramp merge coordination")
    # Row 3: Rios-Torres et al.
    elif sh.name == "Text 35" and "[Author, Year]" in t:
        update_shape_text(sh, "Rios-Torres et al. (2017)")
    elif sh.name == "Text 37" and "[Method / model]" in t:
        update_shape_text(sh, "Centralized Optimal Control")
    elif sh.name == "Text 39" and "[Dataset]" in t:
        update_shape_text(sh, "Analytical / MATLAB")
    elif sh.name == "Text 41" and "[Metric]" in t:
        update_shape_text(sh, "Min Fuel / Accel")
    elif sh.name == "Text 43" and "[What it does well" in t:
        update_shape_text(sh, "Optimizes individual trajectories; computationally prohibitive (QP) and prone to catastrophic failure if RSU drops")
    # Row 4: Molin & Dimarogonas
    elif sh.name == "Text 45" and "[Author, Year]" in t:
        update_shape_text(sh, "Molin et al. (2014)")
    elif sh.name == "Text 47" and "[Method / model]" in t:
        update_shape_text(sh, "Event-Triggered Consensus")
    elif sh.name == "Text 49" and "[Dataset]" in t:
        update_shape_text(sh, "Networked Multi-Agent")
    elif sh.name == "Text 51" and "[Metric]" in t:
        update_shape_text(sh, "Bounded Error")
    elif sh.name == "Text 53" and "[What it does well" in t:
        update_shape_text(sh, "Theoretical multi-agent consensus proofs; not adapted for highway ramp geometry, asymmetric speeds, or SUMO physics")
    elif "Review rule" in t:
        update_shape_text(sh, "Literature Review Takeaway")
    elif "Compare studies for a reason" in t:
        update_shape_text(sh, "Prior works either unrealistically assume perfect wireless channels or suffer severe channel saturation under continuous 10 Hz beaconing during high-density merging.")

# ==============================================================================
# SLIDE 6: Problem Definition
# ==============================================================================
s6 = prs.slides[5]
for sh in s6.shapes:
    if not sh.has_text_frame: continue
    t = sh.text_frame.text.strip()
    if "Compress the research problem" in t:
        update_shape_text(sh, "Mathematical formalization of cooperative ramp merging under communication constraints.")
    elif "“[Define the input" in t:
        update_shape_text(sh, "“Given asymmetric CAV streams on a main highway (25 m/s) and an on-ramp (15 m/s), design a distributed coordination system that dynamically determines a bottleneck merge speed, assigns conflict-free arrival slots, and executes longitudinal consensus control under realistic and bandwidth-constrained wireless channels without physical collisions.”")
    elif "Keep this one sentence specific" in t:
        update_shape_text(sh, "The objective is to minimize V2X communication overhead while guaranteeing string stability, zero collisions, and passenger comfort.")
    elif "[Data / signal / user request" in t:
        update_shape_text(sh, "Vehicle telemetry (t, x, v, a) from highway and ramp detectors; road geometry (ramp 368m, main 400m); speed limits (30 m/s); safe headways (1.5s).")
    elif "[Latency / resource / noise" in t:
        update_shape_text(sh, "Comfortable accel bounds [-3.0, +2.0] m/s², symmetric jerk limit ≤ 2.5 m/s³, wireless packet loss (up to 30%), and autonomous radar fail-safe threshold (TTC < 2.0s).")
    elif "[Prediction / ranking / generation" in t:
        update_shape_text(sh, "Conflict-free virtual sequence, continuous acceleration command a_cmd(t), event-triggered broadcast decisions, and emergency fail-safe actuation.")

# ==============================================================================
# SLIDE 7: Research Gap
# ==============================================================================
s7 = prs.slides[6]
for sh in s7.shapes:
    if not sh.has_text_frame: continue
    t = sh.text_frame.text.strip()
    if "Make the gap visible" in t:
        update_shape_text(sh, "Explicit breakdown of shortcomings in state-of-the-art cooperative merging research.")
    elif "[Existing work addresses A" in t:
        update_shape_text(sh, "Prevailing literature assumes ideal zero-packet-loss communication, ignoring realistic wireless channel impairments (10%–30% packet drop and delay jitter).")
    elif "[Current methods have limitation" in t:
        update_shape_text(sh, "Standard 10 Hz periodic V2V broadcasting causes channel saturation and packet collision during dense traffic, transmitting redundant state data during steady cruising.")
    elif "[Results are not sufficiently validated" in t:
        update_shape_text(sh, "Cooperative controllers often degrade chaotically during wireless blackouts without an independent, radar-based fail-safe to decouple cooperative consensus from emergency braking.")
    elif "Therefore" in t:
        update_shape_text(sh, "Our Proposed Contribution")
    elif "[Your project] targets these gaps" in t:
        update_shape_text(sh, "Our project addresses these gaps by introducing an Event-Triggered V2V mechanism with Dead-Reckoning state estimation and a radar-based TTC fail-safe, cutting communication by ~90% while guaranteeing zero collisions.")

# ==============================================================================
# SLIDE 8: Objectives
# ==============================================================================
s8 = prs.slides[7]
for sh in s8.shapes:
    if not sh.has_text_frame: continue
    t = sh.text_frame.text.strip()
    if "Use action verbs and make each objective testable" in t:
        update_shape_text(sh, "Actionable, testable research milestones for the minor project.")
    elif "[One strong sentence describing the main outcome.]" in t:
        update_shape_text(sh, "Develop, simulate, and benchmark an event-triggered, consensus-driven cooperative merging framework for CAVs that drastically reduces wireless communication load while guaranteeing 100% collision-free safety under ideal and lossy channels.")
    elif sh.name == "Text 9" and "Define" in t:
        update_shape_text(sh, "Model & Formalize")
    elif "formalize the task and success criteria" in t:
        update_shape_text(sh, "Kinematic arrival projections, dynamic merge speed estimation (v_m), and headway constraints along the virtual platoon coordinate axis.")
    elif sh.name == "Text 14" and "Develop" in t:
        update_shape_text(sh, "Design & Implement")
    elif "the proposed framework / model / prototype" in t:
        update_shape_text(sh, "Low-frequency RSU virtual sequencing (0.5 Hz) and distributed consensus CACC with event-triggered broadcast criteria and dead-reckoning extrapolation.")
    elif sh.name == "Text 19" and "Evaluate" in t:
        update_shape_text(sh, "Benchmark & Simulate")
    elif "against suitable baselines and metrics" in t:
        update_shape_text(sh, "Microscopic co-simulations in Eclipse SUMO/TraCI evaluating safety, throughput, packet volume, and latency across baseline and event-based configurations.")
    elif sh.name == "Text 24" and "Analyze" in t:
        update_shape_text(sh, "Stress-Test & Analyze")
    elif "failure cases, limitations and future improvements" in t:
        update_shape_text(sh, "Empirically assess resilience against channel packet loss (0%, 10%, 30%) and validate autonomous radar fail-safe intervention mechanisms.")
    elif "Success looks like…" in t:
        update_shape_text(sh, "Target Success Criteria")
    elif "[Metric / threshold / deliverable that proves" in t:
        update_shape_text(sh, "Zero physical collisions across all scenarios, ≥ 80% reduction in V2V packet transmissions, and stable headway convergence under both perfect and lossy channels.")

# ==============================================================================
# SLIDE 9: Methodology
# ==============================================================================
s9 = prs.slides[8]
for sh in s9.shapes:
    if not sh.has_text_frame: continue
    t = sh.text_frame.text.strip()
    if "A visual pipeline makes the logic" in t:
        update_shape_text(sh, "Hierarchical architecture: Centralized RSU virtual sequencing combined with distributed event-triggered consensus CACC and radar fail-safe.")
    elif sh.name == "Text 7" and "Input" in t:
        update_shape_text(sh, "V2I Ingestion")
    elif "Data / signal / query" in t:
        update_shape_text(sh, "Entry detection at 368m; report speed & distance")
    elif sh.name == "Text 14" and "Pre-process" in t:
        update_shape_text(sh, "Bottleneck Speed")
    elif "Clean • normalize • split" in t:
        update_shape_text(sh, "Compute dynamic merge velocity v_m (Eq. 1-2)")
    elif sh.name == "Text 21" and "Representation" in t:
        update_shape_text(sh, "Virtual Sequencing")
    elif "Features / embeddings" in t:
        update_shape_text(sh, "RSU calculates ETA, assigns FIFO + 1.5s slot")
    elif sh.name == "Text 28" and "Model / Method" in t:
        update_shape_text(sh, "Distributed CACC")
    elif "[Proposed approach]" in t:
        update_shape_text(sh, "Vehicles execute consensus control along virtual axis")
    elif sh.name == "Text 35" and "Evaluate" in t:
        update_shape_text(sh, "Event Trigger V2V")
    elif "Metrics • baselines" in t:
        update_shape_text(sh, "Broadcast on Δv ≥ 0.3 m/s, Δd ≥ 0.5 m, or 1.0s heartbeat")
    elif sh.name == "Text 42" and "Output" in t:
        update_shape_text(sh, "Autonomous Safety")
    elif "Prediction / decision / artifact" in t:
        update_shape_text(sh, "Radar fail-safe engages SUMO car-following if TTC < 2.0s")
    elif "Working logic" in t:
        update_shape_text(sh, "Hierarchical Control Strategy")
    elif "Input → transformation → decision → evidence" in t:
        update_shape_text(sh, "Macro-Coordination (0.5 Hz RSU) + Micro-Execution (10 Hz Onboard)")
    elif "[Briefly explain the information flow" in t:
        update_shape_text(sh, "The RSU provides macroscopic collision-free slot allocations at low frequency (0.5 Hz), while CAVs execute high-frequency (10 Hz) longitudinal consensus control locally. The event-triggered filter suppresses 90% of redundant V2V packets during steady-state tracking.")
    elif "Algorithm / protocol" in t:
        update_shape_text(sh, "Consensus Law & Dead Reckoning Protocol")
    elif "[Pseudocode / decision rules" in t:
        update_shape_text(sh, "Acceleration law: a = -kp*(d_des - gap_ghost) - kv*(v - v_pred). Followers apply constant-velocity dead reckoning d_pred(t) = d_last - v_last * Δt during silent intervals, preventing false deceleration.")

# ==============================================================================
# SLIDE 10: Database / Simulation Traffic Scenario
# ==============================================================================
s10 = prs.slides[9]
for sh in s10.shapes:
    if not sh.has_text_frame: continue
    t = sh.text_frame.text.strip()
    if "Describe what was used, how much" in t:
        update_shape_text(sh, "Microscopic traffic simulation environment modeled in Eclipse SUMO v1.27.1 via Python TraCI co-simulation.")
    elif sh.name == "Text 6" and "[N]" in t:
        update_shape_text(sh, "75", font_size_pt=26, bold=True)
    elif "total instances" in t:
        update_shape_text(sh, "Total CAVs Simulated")
    elif sh.name == "Text 10" and "[K]" in t:
        update_shape_text(sh, "2", font_size_pt=26, bold=True)
    elif "classes / categories" in t:
        update_shape_text(sh, "Traffic Inflow Streams")
    elif sh.name == "Text 14" and "[%]" in t:
        update_shape_text(sh, "300s", font_size_pt=26, bold=True)
    elif "train / test split" in t:
        update_shape_text(sh, "Evaluation Time Horizon")
    elif sh.name == "Text 18" and "[X]" in t:
        update_shape_text(sh, "100%", font_size_pt=26, bold=True)
    elif "key data property" in t:
        update_shape_text(sh, "Autonomous Penetration")
    # Table headers
    elif "Dataset" in t:
        update_shape_text(sh, "Flow Identifier")
    elif "Classes" in t:
        update_shape_text(sh, "Vehicles")
    elif "Train / test" in t:
        update_shape_text(sh, "Flow Rate")
    elif "Source" in t:
        update_shape_text(sh, "Platform")
    elif "Remarks" in t:
        update_shape_text(sh, "Operational Characteristics")
    # Row 1
    elif sh.name == "Text 31":
        update_shape_text(sh, "flow_main (Highway)")
    elif sh.name == "Text 33":
        update_shape_text(sh, "50 CAVs")
    elif sh.name == "Text 35":
        update_shape_text(sh, "600 veh/hr")
    elif sh.name == "Text 37":
        update_shape_text(sh, "SUMO / TraCI")
    elif sh.name == "Text 39":
        update_shape_text(sh, "Single lane 400m, depart speed 25.0 m/s (90 km/h), speed limit 30 m/s")
    # Row 2
    elif sh.name == "Text 41":
        update_shape_text(sh, "flow_ramp (On-Ramp)")
    elif sh.name == "Text 43":
        update_shape_text(sh, "25 CAVs")
    elif sh.name == "Text 45":
        update_shape_text(sh, "300 veh/hr")
    elif sh.name == "Text 47":
        update_shape_text(sh, "SUMO / TraCI")
    elif sh.name == "Text 49":
        update_shape_text(sh, "Single lane 368m, depart speed 15.0 m/s (54 km/h), speed limit 30 m/s")
    # Row 3
    elif sh.name == "Text 51":
        update_shape_text(sh, "main_out (Merged Highway)")
    elif sh.name == "Text 53":
        update_shape_text(sh, "75 CAVs")
    elif sh.name == "Text 55":
        update_shape_text(sh, "900 veh/hr total")
    elif sh.name == "Text 57":
        update_shape_text(sh, "SUMO / TraCI")
    elif sh.name == "Text 59":
        update_shape_text(sh, "Single lane 400m, 8m junction zone (:gneJ2), bottleneck speed v_m = 25 m/s")
    elif "Tip:" in t:
        update_shape_text(sh, "Physical CAV Parameters:")
    elif "Call out anything that could change" in t:
        update_shape_text(sh, "All vehicles are modeled as 5.0m CAVs with comfortable acceleration [-3.0, +2.0] m/s², emergency decel 9.0 m/s², safe standstill gap 5.0m, safe time headway 1.5s, and symmetric jerk limit 2.5 m/s³.")

# ==============================================================================
# SLIDE 11: Experimental Setup
# ==============================================================================
s11 = prs.slides[10]
for sh in s11.shapes:
    if not sh.has_text_frame: continue
    t = sh.text_frame.text.strip()
    if "Before showing results, make the comparison" in t:
        update_shape_text(sh, "Rigorous comparison protocol across baseline, event-triggered, and packet-loss configurations.")
    elif "Model settings" in t:
        update_shape_text(sh, "Controller & Channel Parameters")
    elif "[Architecture / hyperparameters" in t:
        update_shape_text(sh, "Step size Δt = 0.1s (10 Hz), RSU sort period = 2.0s (0.5 Hz), consensus gains kp = 0.15, kv = 0.80, jerk limit = 2.5 m/s³, radar lookahead = 150m, TTC threshold = 2.0s.")
    elif sh.name == "Text 10" and "Protocol" in t:
        update_shape_text(sh, "Simulation Protocol")
    elif "[Train / validation / test split" in t:
        update_shape_text(sh, "300.0s multi-vehicle simulation; reproducible RNG channel seeds; full 0.1s telemetry tracking position, velocity, acceleration, command, predecessor age, and wireless packet transfers.")
    elif sh.name == "Text 14" and "Benchmarks" in t:
        update_shape_text(sh, "Evaluated Benchmarks")
    elif "[Baseline methods / prior work" in t:
        update_shape_text(sh, "1) Perfect Comm (10 Hz periodic V2V baseline); 2) Event-Triggered V2V (Proposed); 3) Real Comm with 0% loss; 4) Real Comm with 10% packet drop; 5) Real Comm with 30% packet drop.")
    elif sh.name == "Text 18" and "Evaluation" in t:
        update_shape_text(sh, "Performance Metrics")
    elif "[Accuracy • precision • recall" in t:
        update_shape_text(sh, "Safety (collisions, TTC < 2.0s conflicts), Communication Cost (packet counts, total data volume KB, bitrate kbps), and Traffic Stability (merge speed, speed variance).")
    elif "Fair comparison principle:" in t:
        update_shape_text(sh, "Fair Comparison Principle:")
    elif "Keep data splits, preprocessing" in t:
        update_shape_text(sh, "Identical vehicle arrival sequences, speed distributions, and road networks are maintained across all baseline and experimental runs for exact comparability.")

# ==============================================================================
# SLIDE 12: Experimental Results & Discussion
# ==============================================================================
s12 = prs.slides[11]
for sh in s12.shapes:
    if not sh.has_text_frame: continue
    t = sh.text_frame.text.strip()
    if "Show the evidence first, then explain" in t:
        update_shape_text(sh, "Quantitative evidence: 89.60% wireless communication reduction with 100% collision-free safety across all scenarios.")
    elif "Performance comparison" in t:
        update_shape_text(sh, "Key Quantitative Benchmark Results")
    elif "Insert your actual metric values" in t:
        update_shape_text(sh, "Tested over 300.0s / 75 CAVs / 900 veh/hr")
    elif "Baseline A" in t:
        update_shape_text(sh, "10 Hz Baseline V2V")
    elif "48%" in t:
        update_shape_text(sh, "16,129 pkts")
    elif "Baseline B" in t:
        update_shape_text(sh, "Event-Triggered V2V")
    elif "66%" in t:
        update_shape_text(sh, "1,677 pkts (-89.6%)")
    elif "Proposed" in t:
        update_shape_text(sh, "Bandwidth Volume")
    elif "82%" in t:
        update_shape_text(sh, "243.9 KB (-78.7%)")
    elif "Example visual only" in t:
        update_shape_text(sh, "Zero physical collisions and zero TTC conflict events (<2.0s) across all ideal and lossy runs (0%, 10%, 30% loss).")
    elif sh.name == "Text 21" and "Discussion" in t:
        update_shape_text(sh, "Performance Discussion")
    elif "What improved, and by how much?" in t:
        update_shape_text(sh, "What improved, and by how much?\n• V2V transmissions dropped by 89.60% (from 16,129 to 1,677 packets).\n• Total wireless data reduced by 78.73% (from 1,147.2 KB to 243.9 KB).\n• Average bitrate dropped from 31.33 kbps to 6.66 kbps with zero collisions.")
    elif "Where did the model / method fail?" in t:
        update_shape_text(sh, "How does the system handle packet loss?\n• Under 10% and 30% packet loss, linear dead reckoning prevented false braking.\n• Max predecessor age reached 4.3s during deep loss bursts with zero collisions.\n• Radar fail-safe stood ready as autonomous safety net but required 0 emergency overrides.")
    elif "Which result supports the research gap?" in t:
        update_shape_text(sh, "Which result supports the core hypothesis?\n• Preserving 100% collision-free merges with zero TTC fail-safe interventions proves that high-rate periodic broadcasting is redundant for longitudinal safety.\n• State updates are only needed during acceleration, deceleration, or drift.")
    elif "What does the evidence not prove?" in t:
        update_shape_text(sh, "Current boundaries and next steps\n• Present evaluation validates single-lane bottleneck geometries.\n• Multi-lane highway weaving and unequipped human vehicles will be addressed in W1–W3.")

# Scale bar shapes on Slide 12 to reflect actual values
# Full width of bar = 4224528
full_w = 4224528
# Shape 9 (Baseline 10Hz) -> 100%
sh9 = find_shape_by_name(s12, "Shape 9")
if sh9: sh9.width = full_w
# Shape 13 (Event V2V) -> 10.4%
sh13 = find_shape_by_name(s12, "Shape 13")
if sh13: sh13.width = int(full_w * 0.104)
# Shape 17 (Bandwidth Volume) -> 21.3%
sh17 = find_shape_by_name(s12, "Shape 17")
if sh17: sh17.width = int(full_w * 0.213)

# ==============================================================================
# SLIDE 13: Plan of Action
# ==============================================================================
s13 = prs.slides[12]
for sh in s13.shapes:
    if not sh.has_text_frame: continue
    t = sh.text_frame.text.strip()
    if "12 • DELIVERY" in t:
        update_shape_text(sh, "13 • DELIVERY")
    elif "Make the remaining work concrete" in t:
        update_shape_text(sh, "Concrete, time-bounded execution milestones for the second half of the semester.")
    elif "Finalize method" in t:
        update_shape_text(sh, "Multi-Lane Highway Scaling")
    elif "[Remaining implementation / tuning]" in t:
        update_shape_text(sh, "Extend road geometry to 2-lane highway with discretionary lane-changing maneuvers before the merge.")
    elif "Run experiments" in t:
        update_shape_text(sh, "Saturation Capacity Tests")
    elif "[Full benchmark + ablations]" in t:
        update_shape_text(sh, "Simulate heavy traffic densities (1500–2400 veh/hr) and evaluate queue spillover and shockwave damping.")
    elif "Analyze results" in t:
        update_shape_text(sh, "Mixed Autonomy & Energy Impact")
    elif "[Error analysis + plots + tables]" in t:
        update_shape_text(sh, "Incorporate human-driven vehicles (Krauss/IDM) and calculate fuel consumption and emissions reductions.")
    elif "Document" in t:
        update_shape_text(sh, "Thesis Report & Manuscript")
    elif "[Report + references + reproducibility]" in t:
        update_shape_text(sh, "Complete comprehensive minor project report, clean modular codebase, and draft conference manuscript.")
    elif "Prepare review" in t:
        update_shape_text(sh, "Final Evaluation & Live Demo")
    elif "[Slides + demo + final checks]" in t:
        update_shape_text(sh, "Prepare interactive SUMO GUI demonstration and final defense presentation for end-sem review.")
    elif "Review checkpoint:" in t:
        update_shape_text(sh, "Final Review Milestone:")
    elif "[Next supervisor / progress review date]" in t:
        update_shape_text(sh, "End-Semester Evaluation (November 2026)  •  Deliverable: Multi-Lane CAV Merge Simulator, Comprehensive Thesis Report, and Research Paper Draft")

# ==============================================================================
# SLIDE 14: Conclusion & Future Directions
# ==============================================================================
s14 = prs.slides[13]
for sh in s14.shapes:
    if not sh.has_text_frame: continue
    t = sh.text_frame.text.strip()
    if "13 • CLOSE" in t:
        update_shape_text(sh, "14 • CLOSE")
    elif "Finish with three things" in t:
        update_shape_text(sh, "Summary of established findings, identified limitations, and roadmap for end-semester completion.")
    elif "What we establish" in t:
        update_shape_text(sh, "What We Have Established")
    elif "[1–2 lines summarizing the strongest finding" in t:
        update_shape_text(sh, "Successfully demonstrated that virtual platoon sequencing + event-triggered consensus CACC achieves 100% collision-free merging while slashing V2V communication overhead by 89.60%.")
    elif "What remains open" in t:
        update_shape_text(sh, "Current Limitations & Open Questions")
    elif "[Main limitation, uncertainty or unresolved challenge.]" in t:
        update_shape_text(sh, "Current evaluation assumes 100% CAV penetration in a single-lane merge; unequipped human vehicles and multi-lane lane selection introduce non-deterministic trajectory noise.")
    elif "What comes next" in t:
        update_shape_text(sh, "Next Steps & Future Directions")
    elif "[Next experiment, extension, deployment" in t:
        update_shape_text(sh, "Integrate Deep Reinforcement Learning for dynamic event-threshold tuning, extend to heterogeneous vehicular traffic, and validate on ROS2 / hardware-in-the-loop testbeds.")
    elif "Takeaway" in t:
        update_shape_text(sh, "Core Takeaway")
    elif "[One memorable sentence that connects" in t:
        update_shape_text(sh, "“Cooperative CAV merging does not require channel-saturating 10 Hz continuous beaconing: intelligent event triggers and dead reckoning deliver flawless safety with ~90% lower communication footprint.”")

# ==============================================================================
# SLIDE 15: Closing Slide
# ==============================================================================
s15 = prs.slides[14]
for sh in s15.shapes:
    if not sh.has_text_frame: continue
    t = sh.text_frame.text.strip()
    if "[Project Title]" in t:
        update_shape_text(sh, "Rule-Based Cooperative Highway Ramp Merging for Connected and Autonomous Vehicles", font_size_pt=18, bold=True)
    elif "[Group Members]" in t:
        update_shape_text(sh, "Pranjal Gupta  •  Swagata Barik  •  Aryan Dubey  •  Dr. Debanjan Das", font_size_pt=13, bold=True)
    elif "IIIT Naya Raipur  •  [Date]" in t:
        update_shape_text(sh, "Department of Computer Science and Engineering  •  IIIT Naya Raipur  •  October 2026", font_size_pt=12, bold=False)

# ==============================================================================
# ADD A DEDICATED VISUAL RESULTS & DASHBOARD SLIDE
# ==============================================================================
from pptx.enum.shapes import MSO_SHAPE

blank_layout = prs.slide_layouts[6] if len(prs.slide_layouts) > 6 else prs.slide_layouts[0]
new_slide = prs.slides.add_slide(blank_layout)

# Add title box
title_box = new_slide.shapes.add_textbox(Inches(0.58), Inches(0.35), Inches(12), Inches(0.85))
tf = title_box.text_frame
tf.word_wrap = True
p = tf.paragraphs[0]
p.text = "12 • VISUAL EVIDENCE : SIMULATION DASHBOARDS & TRAJECTORIES"
p.font.size = Pt(11)
p.font.bold = True
p.font.color.rgb = RGBColor(0x15, 0x65, 0xC0)

p2 = tf.add_paragraph()
p2.text = "Microscopic Trajectory Convergence & Empirical Communication Benchmarks"
p2.font.size = Pt(18)
p2.font.bold = True
p2.font.color.rgb = RGBColor(0x21, 0x21, 0x21)

# Add Dashboard image (left side)
dash_img = "figures/performance_comparison_dashboard.png"
if os.path.exists(dash_img):
    new_slide.shapes.add_picture(dash_img, Inches(0.58), Inches(1.30), width=Inches(5.85))

# Add Trajectory image (right side)
traj_img = "figures/trajectory_and_speed_profiles.png"
if os.path.exists(traj_img):
    new_slide.shapes.add_picture(traj_img, Inches(6.75), Inches(1.30), width=Inches(5.85))

# Left Card: Communication Takeaways
card1 = new_slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.58), Inches(3.30), Inches(5.85), Inches(2.75))
card1.fill.solid()
card1.fill.fore_color.rgb = RGBColor(0xF8, 0xFA, 0xFC)
card1.line.color.rgb = RGBColor(0xCB, 0xD5, 0xE1)
tf1 = card1.text_frame
tf1.word_wrap = True
tf1.margin_left = Inches(0.18)
tf1.margin_right = Inches(0.18)
tf1.margin_top = Inches(0.12)
tf1.margin_bottom = Inches(0.12)

p_h1 = tf1.paragraphs[0]
p_h1.text = "Communication & Channel Efficiency Findings"
p_h1.font.size = Pt(12)
p_h1.font.bold = True
p_h1.font.color.rgb = RGBColor(0x0F, 0x17, 0x2A)

bullets1 = [
    "89.60% reduction in V2V transmissions (16,129 down to 1,677 packets).",
    "78.73% bandwidth savings (1,147.2 KB down to 243.9 KB total volume).",
    "Transmission bitrate dropped from 31.33 kbps to 6.66 kbps (4.7x reduction).",
    "Constant-velocity dead reckoning maintained predictive continuity under 10% and 30% packet loss without phantom deceleration."
]
for b in bullets1:
    pb = tf1.add_paragraph()
    pb.text = "• " + b
    pb.font.size = Pt(9.5)
    pb.font.color.rgb = RGBColor(0x33, 0x41, 0x55)

# Right Card: Safety & Dynamics Takeaways
card2 = new_slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(6.75), Inches(3.30), Inches(5.85), Inches(2.75))
card2.fill.solid()
card2.fill.fore_color.rgb = RGBColor(0xF8, 0xFA, 0xFC)
card2.line.color.rgb = RGBColor(0xCB, 0xD5, 0xE1)
tf2 = card2.text_frame
tf2.word_wrap = True
tf2.margin_left = Inches(0.18)
tf2.margin_right = Inches(0.18)
tf2.margin_top = Inches(0.12)
tf2.margin_bottom = Inches(0.12)

p_h2 = tf2.paragraphs[0]
p_h2.text = "Microscopic Merging Dynamics & Safety Findings"
p_h2.font.size = Pt(12)
p_h2.font.bold = True
p_h2.font.color.rgb = RGBColor(0x0F, 0x17, 0x2A)

bullets2 = [
    "100% collision-free merging across all 75 CAVs (50 highway, 25 ramp).",
    "Zero critical TTC conflict events (<2.0s) observed in all baseline and lossy runs.",
    "Smooth velocity convergence to dynamic merge speed vm = 25.0 m/s prior to merge point.",
    "Virtual predecessor gap (10m + 1.2s headway) reliably maintained without string instability or shockwave amplification."
]
for b in bullets2:
    pb = tf2.add_paragraph()
    pb.text = "• " + b
    pb.font.size = Pt(9.5)
    pb.font.color.rgb = RGBColor(0x33, 0x41, 0x55)

# Bottom Banner: Core Conclusion
banner = new_slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.58), Inches(6.18), Inches(12.02), Inches(0.52))
banner.fill.solid()
banner.fill.fore_color.rgb = RGBColor(0xEF, 0xF6, 0xFF)
banner.line.color.rgb = RGBColor(0x93, 0xC5, 0xFD)
tf_b = banner.text_frame
tf_b.word_wrap = True
tf_b.margin_left = Inches(0.15)
tf_b.margin_right = Inches(0.15)
tf_b.margin_top = Inches(0.08)
tf_b.margin_bottom = Inches(0.08)
p_b = tf_b.paragraphs[0]
p_b.text = "Core Empirical Takeaway: Rule-based event triggering guarantees string stability and 100% collision-free safety while liberating 78.7% of V2X spectral capacity for congested highway environments."
p_b.font.size = Pt(10)
p_b.font.bold = True
p_b.font.color.rgb = RGBColor(0x1D, 0x4E, 0xD8)

# Reorder new slide to be Slide 13 (immediately after Slide 12 Results)
slide_ids = list(prs.slides._sldIdLst)
prs.slides._sldIdLst.remove(slide_ids[-1])
prs.slides._sldIdLst.insert(12, slide_ids[-1])

# Save to destination
prs.save(tgt_pptx)
print(f"Successfully updated presentation saved to {tgt_pptx}!")

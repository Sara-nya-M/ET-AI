import os
import fitz  # PyMuPDF

def create_pdf(filename, title, sections):
    """
    Creates a PDF file with a title and sections.
    sections is a list of tuples: (heading, text)
    """
    doc = fitz.open()
    page = doc.new_page()
    
    y = 50
    # Draw Title using "hebo" (Helvetica-Bold)
    page.insert_text((50, y), title, fontsize=18, fontname="hebo")
    y += 40
    
    for heading, text in sections:
        # Check for page overflow
        if y > 750:
            page = doc.new_page()
            y = 50
            
        # Draw section heading using "hebo"
        page.insert_text((50, y), heading, fontsize=12, fontname="hebo")
        y += 20
        
        # Wrap text simple logic (approx 75 chars per line)
        lines = []
        words = text.split(' ')
        current_line = []
        for word in words:
            if len(' '.join(current_line + [word])) > 75:
                lines.append(' '.join(current_line))
                current_line = [word]
            else:
                current_line.append(word)
        if current_line:
            lines.append(' '.join(current_line))
            
        for line in lines:
            if y > 750:
                page = doc.new_page()
                y = 50
            # Draw body using "helv" (Helvetica-Regular)
            page.insert_text((50, y), line, fontsize=10, fontname="helv")
            y += 15
        y += 15  # space between sections

    os.makedirs(os.path.dirname(filename), exist_ok=True)
    doc.save(filename)
    doc.close()
    print(f"Created PDF: {filename}")

def generate_all():
    # ------------------ REGULATIONS ------------------
    # 1. Factories Act 1948
    factory_act_sections = [
        ("Section 36.1: Egress and Manhole", 
         "No person shall enter or be permitted to enter any chamber, tank, vat, pipe, flue or other confined space in any factory in which any gas, fume, dust or vapor is likely to be present so as to involve risk of persons being overcome thereby, unless it is provided with a manhole of adequate size or other effective means of egress."),
        ("Section 36.2: Gas Free Certification", 
         "No person shall enter any such confined space until a competent person has examined the space, certified in writing that the space is free from dangerous gas, fume, dust or vapor, and that the person entering wears a suitable breathing apparatus and a safety belt securely attached to a rope, the free end of which is held by a person outside."),
        ("Section 37: Explosive Gas Controls", 
         "Where any process in a factory gives rise to dust, gas, fume or vapor of such character and to such extent as to be likely to explode on ignition, all practicable measures shall be taken to prevent such explosion by: (a) effective isolation of the process, and (b) exclusion or effective enclosure of all possible sources of ignition.")
    ]
    create_pdf("data/regulations/Factory_Act_1948.pdf", "The Factories Act, 1948", factory_act_sections)

    # 2. OISD-STD-105
    oisd_sections = [
        ("Clause 4.1: General Permit Rules", 
         "A work permit is a written document authorizing specific work to be carried out in a specific area. No hot work, cold work, or confined space entry shall be performed without a valid permit issued by an authorized receiver and issuer."),
        ("Clause 4.2.1: Atmosphere Gas Testing", 
         "Gas testing must be performed by a competent person certified by the safety department. Entry shall only be allowed if: Oxygen content is between 19.5% and 23.5% by volume, Flammable gases (LEL) are below 1.0%, and Toxic gas concentrations are below threshold limit values (e.g. H2S below 10 ppm)."),
        ("Clause 4.2.2: Permit Shift Validity", 
         "A work permit shall be valid for a maximum of one shift or 12 hours, whichever is less. A fresh permit or renewal is required if the work extends beyond the authorized shift. Re-testing of the atmosphere is mandatory upon permit renewal or if work is suspended for more than 2 hours."),
        ("Clause 5.1: Isolation and Energy Control", 
         "All energy sources (electrical, mechanical, hydraulic) must be isolated, locked out, and tagged out (LOTO) prior to confined space entry. Physical blinding or disconnection of process piping is mandatory to prevent material entry."),
        ("Clause 5.2: Rescue and Observer Standby", 
         "A standby person must be stationed at the entrance of the confined space at all times. The standby person must remain at the entrance and monitor entrants. Under no circumstances shall the standby person leave the entrance or enter the space. A safety harness and lifeline must be worn by entrants, and rescue equipment must be available on-site."),
        ("Clause 6.1: Hot Work Fire Precautions", 
         "All combustible materials must be removed or protected within a radius of 15 meters from the hot work location. A designated fire watch with appropriate firefighting equipment (extinguishers, fire hose) must be present.")
    ]
    create_pdf("data/regulations/OISD_STD_105.pdf", "OISD-STD-105: Work Permit System", oisd_sections)

    # 3. PESO Guidelines
    peso_sections = [
        ("Clause 3.2: Storage Tank Hazardous Operations", 
         "For storage tanks containing petroleum products or hazardous chemicals: Before cleaning or repair, the tank must be completely drained, isolated, and gas-freed. All electrical lighting, tools, and communication equipment used inside the tank must be certified flame-proof or explosion-proof. Spark-producing tools, including steel hammers, are strictly prohibited. Non-sparking brass or bronze tools must be used.")
    ]
    create_pdf("data/regulations/PESO_Guidelines.pdf", "PESO Guidelines: Hazardous Area Operations", peso_sections)


    # ------------------ SYNTHETIC PROCEDURES (SOPs) ------------------
    # 1. SOP Confined Space Entry (Gaps: Gas testing by anyone, standby leaves)
    sop_cs = [
        ("Section 1.0: Purpose and Scope", 
         "This procedure defines the safety rules for entering chambers, tanks, and other enclosed areas at the refinery plant."),
        ("Section 2.0: Gas Testing Requirements", 
         "Before entering any confined space, gas testing shall be performed. Any available plant operator can conduct the gas test using a portable meter. If the space has been ventilated for 2 hours, gas testing is considered optional."),
        ("Section 3.0: Standby Observer Duties", 
         "A standby observer must sit near the entrance. If the observer needs to retrieve tools, spare parts, or take a quick break, they may temporarily leave their post, provided they return within 10 minutes and verify the entrants are safe.")
    ]
    create_pdf("data/procedures/SOP_Confined_Space_Entry.pdf", "SOP: Confined Space Entry Procedure", sop_cs)

    # 2. SOP Hot Work (Gap: 5m clearance instead of 15m)
    sop_hw = [
        ("Section 1.0: Scope of Hot Work", 
         "Covers operations involving welding, cutting, grinding, and open flames in the plant premises."),
        ("Section 2.0: Combustible Management", 
         "To prevent fires, all combustible materials, oil drums, and rags must be cleared from a radius of 5 meters around the hot work spot. Any items that cannot be moved must be covered with fire-retardant blankets.")
    ]
    create_pdf("data/procedures/SOP_Hot_Work.pdf", "SOP: Hot Work Permit Procedure", sop_hw)

    # 3. SOP Tank Cleaning (Gap: Steel hammers & standard lights)
    sop_tc = [
        ("Section 1.0: Tank Ingress Preparation", 
         "Procedure for draining and preparing petroleum product tanks for internal cleaning and scale removal."),
        ("Section 2.0: Tooling and Lighting", 
         "Operators entering the tank shall use standard portable LED flashlights for visibility. Hard scale on the tank floor and walls must be chipped off using heavy-duty steel hammers or chisels to ensure complete scale removal.")
    ]
    create_pdf("data/procedures/SOP_Tank_Cleaning.pdf", "SOP: Petroleum Storage Tank Cleaning Procedure", sop_tc)

    # 4. SOP Gas Detector Calibration (Gap: 12-month calibration instead of regular monthly/quarterly)
    sop_gdc = [
        ("Section 1.0: Calibration Scope", 
         "Covers portable gas detectors used for confined space safety monitoring."),
        ("Section 2.0: Calibration Frequency", 
         "To maintain sensor accuracy, all portable gas detectors must undergo testing and calibration at least once every 12 months. Calibrations must be logged in the maintenance file.")
    ]
    create_pdf("data/procedures/SOP_Gas_Detector_Calibration.pdf", "SOP: Gas Detector Calibration Procedure", sop_gdc)

    # 5. SOP Vessel Inspection Checklist (Gap: 24h validity)
    sop_vi = [
        ("Section 1.0: Routine Vessel Check", 
         "Defines procedures for inspection of pressure vessels during shutdown."),
        ("Section 2.0: Permit Validity Period", 
         "The entry permit remains valid for a duration of 24 hours from the time of issue. Work can proceed continuously across multiple shifts without re-running the atmospheric tests unless a strong odor is noticed.")
    ]
    create_pdf("data/procedures/SOP_Vessel_Inspection_Checklist.pdf", "SOP: Vessel Inspection Checklist", sop_vi)

    # 6. SOP Lockout Tagout (Gap: Verbal isolation)
    sop_loto = [
        ("Section 1.0: Energy Isolation Scope", 
         "Applies to electrical motors, pumps, and valves during piping inspection."),
        ("Section 2.0: Isolation Verification", 
         "Physical locks and tags must be applied to main breakers. However, during urgent operations, verbal confirmation of isolation from the control room operator is acceptable in place of physical locks to save time.")
    ]
    create_pdf("data/procedures/SOP_Lockout_Tagout_LOTO.pdf", "SOP: Lockout Tagout Procedure", sop_loto)

    # 7. SOP Emergency Rescue (Gap: Standby rescue team 30 mins away)
    sop_er = [
        ("Section 1.0: Emergency Response Plan", 
         "Defines rescue procedures for injuries inside process columns."),
        ("Section 2.0: Rescue Team Availability", 
         "In case of an incident, the entry observer must contact the safety division. The standby rescue team is stationed at the corporate office (30 minutes drive) and will arrive with ropes and breathing sets to perform rescue.")
    ]
    create_pdf("data/procedures/SOP_Emergency_Rescue.pdf", "SOP: Confined Space Emergency Rescue SOP", sop_er)

    # 8. SOP Pipeline Maintenance (Gap: Work without permit if below 5 bar)
    sop_pm = [
        ("Section 1.0: Piping System Repairs", 
         "Procedures for minor line replacements and gasket repairs."),
        ("Section 2.0: Permitting Requirements", 
         "A cold work permit is required for line breaking. However, if the pipeline pressure is confirmed to be below 5 bar, work may proceed without a work permit, provided the line is blocked at upstream valves.")
    ]
    create_pdf("data/procedures/SOP_Pipeline_Maintenance.pdf", "SOP: Pipeline Gasket Maintenance Procedure", sop_pm)

    # 9. SOP Electrical Maintenance (Fully Compliant)
    sop_em = [
        ("Section 1.0: Electrical Substation Safety", 
         "Applies to high voltage breaker servicing."),
        ("Section 2.0: Safety Protocol", 
         "No work shall start without a valid electrical isolation permit. The technician must wear dielectric gloves and safety boots. Isolation must be locked out, tagged out, and verified using a calibrated voltage tester.")
    ]
    create_pdf("data/procedures/SOP_Electrical_Maintenance.pdf", "SOP: Substation Electrical Maintenance Procedure", sop_em)

    # 10. SOP Chemical Handling (Fully Compliant)
    sop_ch = [
        ("Section 1.0: Caustic Ingestion and Unloading", 
         "Safe handling procedure for caustic soda unloading operations."),
        ("Section 2.0: Personal Protective Equipment", 
         "Operators must wear full chemical-resistant suits, face shields, and rubber boots. A safety shower and eyewash station must be inspected and confirmed functional within 10 meters of the work area before unloading starts.")
    ]
    create_pdf("data/procedures/SOP_Chemical_Handling.pdf", "SOP: Chemical Storage Handling and Safety Procedure", sop_ch)

if __name__ == "__main__":
    generate_all()

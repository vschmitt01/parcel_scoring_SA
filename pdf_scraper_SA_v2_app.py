import streamlit as st
import pandas as pd
import pdfplumber
import re
from io import BytesIO

st.title("South Australia Planning Report Extractor")

uploaded_files = st.file_uploader("Upload one or more PDFs", type="pdf", accept_multiple_files=True)

FIELDS = ['Adress', 
          'Council', 
          'Valuation Number', 
          'Title Reference',
          'Plan No. Parcel No.', 
          'Zones', 
          'Overlays'
          ]

def extract_field(label, text):
    """
    Extracts the field value from text after a label, 
    returning only full words written in CAPITAL LETTERS.
    """
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if re.match(rf"{label}[:\-]?", line, re.IGNORECASE):
            # Remove the label part
            inline = re.sub(rf"{label}[:\-]?", "", line, flags=re.IGNORECASE).strip()
            # Extract only full uppercase words (A–Z, possibly with numbers if needed)
            uppercase_words = re.findall(r'\b[A-Z0-9]{2,}\b', inline)
            # Join them into a single string
            return " ".join(uppercase_words)
    return ""


def extract_zone(text):
    """
    Extracts the zone information from the line immediately following the label 'Zones'.
    """
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if re.match(r"Zones\s*$", line.strip(), re.IGNORECASE):
            # Return the next non-empty line if available
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                if next_line:
                    return next_line
    return ""


def extract_overlays(text):
    """
    Extracts all overlay lines following the 'Overlays' label
    that contain a code in the format '(XXXXX)'.
    Returns them joined as a single string separated by newlines.
    """
    lines = text.splitlines()
    collecting = False
    collected = []

    for line in lines:
        stripped = line.strip()

        if re.match(r"Overlays\s*$", stripped, re.IGNORECASE):
            collecting = True
            continue
                  
        # Stop capturing at 'Variations'
        if re.match(r'^Variations$', line, re.IGNORECASE):
            break
                  
        if collecting:
            # Stop collecting if we reach another section label (heuristic)
            if re.match(r"^[A-Z][A-Za-z\s]+:$", stripped) or stripped == "":
                continue
            # Match lines containing a code like (O1234), (Z5402), etc.
            if re.search(r"\([A-Z0-9]{4,}\)", stripped):
                collected.append(stripped)

    return " / ".join(collected)


            
if uploaded_files:
    records = []    
    for uploaded_file in uploaded_files:
        if uploaded_file.name.endswith(".pdf"):
            with pdfplumber.open(uploaded_file) as pdf:
                text = "\n".join([page.extract_text() or "" for page in pdf.pages])
            
        entry = {"File Name": uploaded_file.name}
        
        st_nbr = extract_field("Street Number:", text)
        st_name = extract_field("Street Name:", text)
        st_type = extract_field("Street Type:", text)
        suburb = extract_field("Suburb:", text)
        postcode = extract_field("Postcode:", text)
        
        entry["Adress"] = st_nbr + " " + st_name + " " + st_type + " " + suburb + " " + postcode

        entry["Council"] = extract_field("Council:", text)
        entry["Valuation Number"] = extract_field("Valuation Number:", text)
        entry["Title Reference"] = extract_field("Title Reference:", text)
        entry["Plan No. Parcel No."] = extract_field("Plan No. Parcel No.:", text)
        
        entry["Zones"] = extract_zone(text)
        
        entry["Overlays"] = extract_overlays(text)
        
        records.append(entry)

    
    df = pd.DataFrame(records, columns=["File Name"] + FIELDS)
    st.dataframe(df)
    
    # Download Excel
    output = BytesIO()
    df.to_excel(output, index=False)
    st.download_button(
        "💾 Download Excel",
        data=output.getvalue(),
        file_name="parsed_sites.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )





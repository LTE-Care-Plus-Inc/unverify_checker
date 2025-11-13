import io

import pandas as pd
import streamlit as st


st.set_page_config(page_title="Session Matcher by Appointment ID", layout="wide")
st.title("Session Matcher by Appointment ID")

st.markdown("""
**File 1 = Aloha file**  
- Must contain: `Appointment ID`, `Completed`

**File 2 = Unbilled file**  
- Must contain: `Appointment ID`

The app will:
1. Automatically run once both files are uploaded.  
2. Inner join on `Appointment ID` (only sessions that appear in **both** files).  
3. Filter to rows where **Completed = "Yes"** (from the Aloha file).  
4. Let you download that filtered inner-join table as Excel (single sheet).
""")


def read_table(file):
    """Read CSV or Excel into a DataFrame."""
    if file is None:
        return None, "No file uploaded"

    filename = file.name.lower()

    try:
        if filename.endswith(".csv"):
            df = pd.read_csv(file)
        elif filename.endswith((".xlsx", ".xls")):
            # Read the first sheet by default
            df = pd.read_excel(file)
        else:
            return None, "Unsupported file type. Please upload CSV or Excel."
    except Exception as e:
        return None, f"Error reading file: {e}"

    if df.empty:
        return None, "File appears to be empty."
    return df, None


def validate_columns(df, required_cols, file_label):
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        return f"{file_label} is missing required column(s): {', '.join(missing)}"
    return None


# --- File upload ---
col1, col2 = st.columns(2)

with col1:
    file1 = st.file_uploader("Upload File 1 (Aloha file)", type=["csv", "xlsx", "xls"])
with col2:
    file2 = st.file_uploader("Upload File 2 (Unbilled file)", type=["csv", "xlsx", "xls"])

df1, err1 = (None, None)
df2, err2 = (None, None)

if file1:
    df1, err1 = read_table(file1)
if file2:
    df2, err2 = read_table(file2)

if err1:
    st.error(f"File 1 (Aloha): {err1}")
if err2:
    st.error(f"File 2 (Unbilled): {err2}")

# --- Main logic: auto-run when both files are present and valid ---
if df1 is not None and df2 is not None and not err1 and not err2:
    # Validate required columns
    err_cols1 = validate_columns(df1, ["Appointment ID", "Completed"], "File 1 (Aloha)")
    err_cols2 = validate_columns(df2, ["Appointment ID"], "File 2 (Unbilled)")

    if err_cols1:
        st.error(err_cols1)
    if err_cols2:
        st.error(err_cols2)

    if not err_cols1 and not err_cols2:
        # Normalize Appointment ID to string for safe joins
        df1["Appointment ID"] = df1["Appointment ID"].astype(str)
        df2["Appointment ID"] = df2["Appointment ID"].astype(str)

        # Inner join on Appointment ID
        merged = pd.merge(
            df1,
            df2,
            on="Appointment ID",
            how="inner",  # only rows present in both Aloha & Unbilled
            suffixes=("_aloha", "_unbilled"),
        )

        # Filter for Completed == "Yes" from Aloha file
        if "Completed" not in merged.columns:
            st.error("Merged result does not contain 'Completed' column from Aloha file.")
        else:
            matched_completed_yes = merged[
                merged["Completed"]
                .astype(str)
                .str.strip()
                .str.lower()
                .eq("yes")
            ]

            st.subheader("Matched Sessions (Inner Join, Completed = Yes)")
            st.write(f"Total inner-joined rows: **{len(merged)}**")
            st.write(f"Rows with `Completed = 'Yes'`: **{len(matched_completed_yes)}**")

            st.dataframe(matched_completed_yes.head(200))

            # Prepare Excel with ONLY the inner-join filtered table
            if not matched_completed_yes.empty:
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                    matched_completed_yes.to_excel(
                        writer,
                        sheet_name="Matched_Completed_Yes",
                        index=False,
                    )
                buffer.seek(0)

                st.download_button(
                    label="Download Matched Sessions (Completed = Yes)",
                    data=buffer,
                    file_name="matched_sessions_completed_yes.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            else:
                st.info("No rows found where Completed = 'Yes' after inner join.")
else:
    st.info("Please upload both files to start.")

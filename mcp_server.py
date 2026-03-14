import json
import requests
from mcp.server.fastmcp import FastMCP

# Initialize FastMCP server
mcp = FastMCP("MediQ-Database-Server")

DB_BASE_URL = "http://localhost:5090/api"

def make_request(endpoint: str, params: dict):
    """Helper to make safe requests to the database and cleanly format JSON."""
    # Clean out None/empty values so we don't send garbage to the DB
    clean_params = {k: v for k, v in params.items() if v and str(v).lower() not in ["null", "none"]}
    
    try:
        response = requests.get(f"{DB_BASE_URL}{endpoint}", params=clean_params)
        response.raise_for_status()
        data = response.json()
        
        # Claude Desktop handles context well, but we should still stringify safely
        return json.dumps(data)
    except Exception as e:
        return json.dumps({"error": str(e)})

# ==========================================
# CLAUDE MCP TOOLS (Mirroring server.py)
# ==========================================

@mcp.tool()
def get_patient_history(patient_id: str, start_date: str = None, end_date: str = None) -> str:
    """Retrieve a chronological timeline of a specific patient's medical history using their UUID."""
    return make_request("/patient/history", {"patientId": patient_id, "startDate": start_date, "endDate": end_date})

@mcp.tool()
def get_encounters(encounter_id: str = None, start_date: str = None, end_date: str = None) -> str:
    """Retrieve specific medical encounter records."""
    return make_request("/encounters", {"encounterId": encounter_id, "startDate": start_date, "endDate": end_date})

@mcp.tool()
def get_procedures(procedure_id: str = None, patient_id: str = None, start_date: str = None, end_date: str = None) -> str:
    """Retrieve records of medical procedures or surgeries."""
    return make_request("/procedures", {"procedureId": procedure_id, "patientId": patient_id, "startDate": start_date, "endDate": end_date})

@mcp.tool()
def get_patient_demographics(patient_id: str) -> str:
    """Retrieve personal demographic data for a single patient (human name, gender, birthdate)."""
    return make_request("/patients", {"patientId": patient_id})

@mcp.tool()
def get_organization_details(organization_id: str) -> str:
    """Retrieve hospital or clinic details (address, location) by their ID."""
    return make_request("/organizations", {"organizationId": organization_id})

@mcp.tool()
def get_payer_details(payer_id: str) -> str:
    """Retrieve insurance provider (Payer) details by their ID."""
    return make_request("/payers", {"payerId": payer_id})

@mcp.tool()
def search_patients_by_name(first_name: str = None, last_name: str = None) -> str:
    """Find a patient's UUID using their first or last name. Use this FIRST to get an ID before querying history."""
    return make_request("/patients/search", {"firstName": first_name, "lastName": last_name})

@mcp.tool()
def get_patient_count_by_factor(factor_value: str, factor_field: str = "REASONDESCRIPTION") -> str:
    """Get the total count of unique patients based on a specific clinical factor or diagnosis (e.g., 'Viral sinusitis')."""
    return make_request("/analytics/patient_count", {"factorValue": factor_value, "factorField": factor_field})

if __name__ == "__main__":
    # MCP communicates via standard input/output (stdio) when run by Claude Desktop.
    mcp.run()
from flask import Flask, request, jsonify
from flasgger import Swagger
from pymongo import MongoClient
import re

app = Flask(__name__)
swagger = Swagger(app)

client = MongoClient('mongodb://localhost:27017/')
db = client['healthcare_db']

def build_date_query(start_date, end_date, date_field="START"):
    """
    Smarter date query builder that handles approximate/short dates 
    like 'YYYY-MM-DD' by padding them to cover the full day.
    """
    date_query = {}
    
    if start_date:
        if len(start_date) <= 10:
            start_date = f"{start_date}T00:00:00Z"
        date_query["$gte"] = start_date
        
    if end_date:
        if len(end_date) <= 10:
            end_date = f"{end_date}T23:59:59Z"
        date_query["$lte"] = end_date
        
    return {date_field: date_query} if date_query else {}

# ==========================================
# GET ENDPOINTS (NEW HACKATHON TOOLS ADDED)
# ==========================================

@app.route('/api/patients/search', methods=['GET'])
def search_patients_by_name():
    """
    Search for patients by their first and/or last name
    """
    first_name = request.args.get('firstName')
    last_name = request.args.get('lastName')

    # If both are missing OR both are just empty strings, return error
    if not first_name and not last_name:
        return jsonify({"error": "Provide at least firstName or lastName"}), 400

    query = {}
    
    # Use re.escape() to safely handle special characters like "?" or "*" 
    # so MongoDB doesn't crash on invalid regex
    if first_name and first_name != "?":
        safe_first = re.escape(first_name)
        query["FIRST"] = {"$regex": safe_first, "$options": "i"}
        
    if last_name and last_name != "?":
        safe_last = re.escape(last_name)
        query["LAST"] = {"$regex": safe_last, "$options": "i"}
        
    # If the AI passed literally just "?" for both fields, return empty
    if not query:
        return jsonify([]), 200

    patients = list(db.patients.find(query, {"_id": 0}))
    return jsonify(patients), 200
@app.route('/api/analytics/patient_count', methods=['GET'])
def get_patient_count_by_factor():
    """ 
    Get the total count of unique patients based on a specific clinical factor
    ---
    parameters:
      - name: factorValue
        in: query
        type: string
        required: true
        description: The clinical value to search for (e.g., 'Viral sinusitis', 'Normal pregnancy').
      - name: factorField
        in: query
        type: string
        required: false
        description: The DB field to search in (defaults to 'REASONDESCRIPTION').
    responses:
      200:
        description: An aggregation of unique patients matching the criteria.
    """
    factor_value = request.args.get('factorValue')
    factor_field = request.args.get('factorField', 'REASONDESCRIPTION')

    if not factor_value:
        return jsonify({"error": "factorValue is required"}), 400

    # We use regex to catch slight variations in spelling/casing in the dataset
    query = {factor_field: {"$regex": factor_value, "$options": "i"}}
    
    # Aggregation Pipeline: Match condition -> Group by unique PATIENT ID -> Count
    pipeline = [
        {"$match": query},
        {"$group": {"_id": "$PATIENT"}},
        {"$count": "total_unique_patients"}
    ]
    
    result = list(db.encounters.aggregate(pipeline))
    count = result[0]["total_unique_patients"] if result else 0
    
    return jsonify({
        "searched_field": factor_field,
        "searched_value": factor_value,
        "total_patients": count
    }), 200

# ==========================================
# EXISTING GET ENDPOINTS
# ==========================================

@app.route('/api/patient/history', methods=['GET'])
def get_patient_history():
    """
    Get patient history chronologically
    ---
    parameters:
      - name: patientId
        in: query
        type: string
        required: true
      - name: startDate
        in: query
        type: string
        required: false
      - name: endDate
        in: query
        type: string
        required: false
    responses:
      200:
        description: A list of patient encounters with hospital details.
    """
    patient_id = request.args.get('patientId')
    if not patient_id:
        return jsonify({"error": "patientId is required"}), 400

    match_query = {"PATIENT": patient_id}
    match_query.update(build_date_query(request.args.get('startDate'), request.args.get('endDate')))

    pipeline = [
        {"$match": match_query},
        {"$sort": {"START": 1}},
        {
            "$lookup": {
                "from": "organizations",
                "localField": "ORGANIZATION",
                "foreignField": "Id",
                "as": "HospitalDetails"
            }
        },
        {"$project": {"_id": 0, "HospitalDetails._id": 0}}
    ]
    return jsonify(list(db.encounters.aggregate(pipeline))), 200

@app.route('/api/encounters', methods=['GET'])
def get_encounters():
    """
    Get encounter details and associated patients
    ---
    parameters:
      - name: encounterId
        in: query
        type: string
        required: false
      - name: startDate
        in: query
        type: string
        required: false
      - name: endDate
        in: query
        type: string
        required: false
    responses:
      200:
        description: Encounter details.
    """
    encounter_id = request.args.get('encounterId')
    start_date = request.args.get('startDate')
    end_date = request.args.get('endDate')

    pipeline = []
    if encounter_id:
        pipeline.append({"$match": {"Id": encounter_id}})
        pipeline.append({
            "$lookup": {
                "from": "patients",
                "localField": "PATIENT",
                "foreignField": "Id",
                "as": "PatientDetails"
            }
        })
    elif start_date or end_date:
        pipeline.append({"$match": build_date_query(start_date, end_date)})
    else:
        return jsonify({"error": "Provide either encounterId or date range"}), 400

    pipeline.append({"$project": {"_id": 0, "PatientDetails._id": 0}})
    return jsonify(list(db.encounters.aggregate(pipeline))), 200

@app.route('/api/procedures', methods=['GET'])
def get_procedures():
    """
    Get procedure details and context
    ---
    parameters:
      - name: procedureId
        in: query
        type: string
        required: false
      - name: patientId
        in: query
        type: string
        required: false
      - name: startDate
        in: query
        type: string
        required: false
      - name: endDate
        in: query
        type: string
        required: false
    responses:
      200:
        description: Procedure list.
    """
    match_query = {}
    if request.args.get('procedureId'):
        match_query["CODE"] = request.args.get('procedureId')
    if request.args.get('patientId'):
        match_query["PATIENT"] = request.args.get('patientId')
        
    match_query.update(build_date_query(request.args.get('startDate'), request.args.get('endDate')))

    pipeline = [
        {"$match": match_query},
        {"$sort": {"START": 1}},
        {"$project": {"_id": 0}}
    ]
    return jsonify(list(db.procedures.aggregate(pipeline))), 200

@app.route('/api/patients', methods=['GET'])
def get_patient():
    """
    Get demographic details of a patient
    ---
    parameters:
      - name: patientId
        in: query
        type: string
        required: true
    responses:
      200:
        description: Patient demographic data.
    """
    patient_id = request.args.get('patientId')
    if not patient_id:
        return jsonify({"error": "patientId is required"}), 400

    patient = db.patients.find_one({"Id": patient_id}, {"_id": 0})
    return jsonify(patient if patient else {}), 200 if patient else 404

@app.route('/api/organizations', methods=['GET'])
def get_organization():
    """
    Get hospital or organization details
    ---
    parameters:
      - name: organizationId
        in: query
        type: string
        required: true
    responses:
      200:
        description: Organization details.
    """
    org_id = request.args.get('organizationId')
    if not org_id:
        return jsonify({"error": "organizationId is required"}), 400

    org = db.organizations.find_one({"Id": org_id}, {"_id": 0})
    return jsonify(org if org else {}), 200 if org else 404

@app.route('/api/payers', methods=['GET'])
def get_payer():
    """
    Get insurance payer details
    ---
    parameters:
      - name: payerId
        in: query
        type: string
        required: true
    responses:
      200:
        description: Payer details.
    """
    payer_id = request.args.get('payerId')
    if not payer_id:
        return jsonify({"error": "payerId is required"}), 400

    payer = db.payers.find_one({"Id": payer_id}, {"_id": 0})
    return jsonify(payer if payer else {}), 200 if payer else 404

# ==========================================
# POST ENDPOINTS
# ==========================================

@app.route('/api/encounters', methods=['POST'])
def add_encounter():
    """Add a new encounter"""
    data = request.json
    db.encounters.insert_one(data)
    data.pop('_id', None)
    return jsonify({"message": "Encounter added", "data": data}), 201

@app.route('/api/patients', methods=['POST'])
def add_patient():
    """Add a new patient"""
    data = request.json
    db.patients.insert_one(data)
    data.pop('_id', None)
    return jsonify({"message": "Patient added", "data": data}), 201

@app.route('/api/procedures', methods=['POST'])
def add_procedure():
    """Add a new procedure"""
    data = request.json
    db.procedures.insert_one(data)
    data.pop('_id', None)
    return jsonify({"message": "Procedure added", "data": data}), 201

if __name__ == '__main__':
    # Running on port 5090 for macOS AirPlay conflict avoidance
    app.run(host='0.0.0.0', port=5090, debug=True)
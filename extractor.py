import json
from groq import Groq

# Make sure to use your actual API key here!
client = Groq(api_key="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")

def extract_knowledge_triplets(json_data) -> list:
    """Uses Groq to extract relational triplets using a strict JSON schema."""
    # Convert to string and truncate to save tokens, but keep enough for context
    data_str = json.dumps(json_data)[:2500] 
    
    prompt = f"""
    You are a data extraction tool. Extract entities and relationships from this healthcare data.
    You MUST respond with a valid JSON object containing a SINGLE key called "triplets".
    The value must be a list of arrays, where each array has exactly 3 strings: ["Subject", "RELATION_TYPE", "Object"].
    
    Example format:
    {{
        "triplets": [
            ["Patient 123", "HAD_ENCOUNTER", "Encounter ABC"],
            ["Encounter ABC", "OCCURRED_AT", "City Hospital"]
        ]
    }}
    
    Data to process:
    {data_str}
    """
    
    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            response_format={"type": "json_object"} # Force strict JSON object
        )
        
        result_str = response.choices[0].message.content
        print(f"\n--- [Extractor Debug] LLM Raw JSON --- \n{result_str}\n--------------------------------------")
        
        # Safely parse the strict schema
        data_dict = json.loads(result_str)
        triplets = data_dict.get("triplets", [])
        
        # Validate that it is actually a list of 3-item lists
        valid_triplets = [t for t in triplets if isinstance(t, list) and len(t) == 3]
        print(f"[System] Successfully added {len(valid_triplets)} relationships to the Graph!")
        return valid_triplets
            
    except Exception as e:
        print(f"\n[Extractor Error] Failed to parse: {e}\n")
        return []
import os
import json

from dotenv import load_dotenv
from google import genai
from google.genai import types


load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")
MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

if not API_KEY:
    raise ValueError("GEMINI_API_KEY is missing from .env")

client = genai.Client(api_key=API_KEY)


class MedicineAIError(Exception):

    def __init__(self, user_message):
        self.user_message = user_message
        super().__init__(user_message)


def is_api_key_configured():
    return bool(API_KEY)


def _clean_json(text):

    if not text:
        raise ValueError("Empty AI response.")

    text = text.strip()

    if text.startswith("```"):
        text = text.replace("```json", "")
        text = text.replace("```", "")
        text = text.strip()

    return text


def _read_json_response(response):

    text = getattr(response, "text", None)

    if not text:
        raise ValueError("AI returned an empty response.")

    return json.loads(_clean_json(text))


def _get_mime_type(file_path):

    extension = os.path.splitext(file_path)[1].lower()

    if extension == ".png":
        return "image/png"

    if extension == ".webp":
        return "image/webp"

    if extension == ".jpg" or extension == ".jpeg":
        return "image/jpeg"

    return "image/jpeg"


def analyze_medicine_image(image_path):

    try:

        with open(image_path, "rb") as f:
            image_data = f.read()

        mime_type = _get_mime_type(image_path)

        prompt = """
You are MedCheck, an AI medicine recognition assistant.

Analyze the medicine package in this image.

Return ONLY valid JSON.

{
  "medicine_name": "",
  "active_ingredient": "",
  "dosage": "",
  "dosage_unit": "",
  "manufacturer": "",
  "medicine_type": "",
  "package_size": "",
  "description": "",
  "confidence": 0.0,
  "visible_text": []
}

Rules:

1. Read the medicine name from the package carefully.
2. Do not guess.
3. If the medicine name cannot be read, use "Unknown".
4. If information cannot be read, use "Unknown".
5. Confidence must be between 0.0 and 1.0.
6. Return JSON only.
"""

        response = client.models.generate_content(
            model=MODEL,
            contents=[
                types.Part.from_bytes(
                    data=image_data,
                    mime_type=mime_type
                ),
                prompt
            ]
        )

        result = _read_json_response(response)

        defaults = {
            "medicine_name": "Unknown",
            "active_ingredient": "Unknown",
            "dosage": "Unknown",
            "dosage_unit": "",
            "manufacturer": "Unknown",
            "medicine_type": "Unknown",
            "package_size": "Unknown",
            "description": "Unknown",
            "visible_text": []
        }

        for key, value in defaults.items():
            result.setdefault(key, value)

        try:

            result["confidence"] = max(
                0.0,
                min(
                    1.0,
                    float(
                        result.get(
                            "confidence",
                            0.0
                        )
                    )
                )
            )

        except (TypeError, ValueError):

            result["confidence"] = 0.0

        return result

    except Exception as e:

        raise MedicineAIError(
            f"Unable to analyze medicine image: {str(e)}"
        )


def _read_prescription_medicines(
    prescription_path
):

    with open(prescription_path, "rb") as f:
        prescription_data = f.read()

    mime_type = _get_mime_type(
        prescription_path
    )

    prompt = """
You are MedCheck.

Read the doctor's prescription image very carefully.

Your MOST IMPORTANT task is to identify EVERY medicine
written on the prescription.

Do NOT stop after finding a few medicines.

Count all medicine entries on the prescription.

Return ONLY valid JSON in this exact format:

{
  "medicines": [
    {
      "name": "",
      "dosage": "",
      "quantity": "",
      "usage": ""
    }
  ]
}

Rules:

1. Read ALL medicine names on the prescription.
2. Return one object for EVERY medicine.
3. Do not skip medicines.
4. Do not merge two different medicines.
5. Preserve the medicine name as written on the prescription
   as accurately as possible.
6. Read the doctor's instructions beside each medicine.
7. Do not invent instructions.
8. If an instruction is unclear, write:
   "Instruction unclear"
9. If dosage is unclear, write:
   "Unclear"
10. If quantity is unclear, write:
   "Unclear"
11. Return JSON only.
"""

    response = client.models.generate_content(
        model=MODEL,
        contents=[
            types.Part.from_bytes(
                data=prescription_data,
                mime_type=mime_type
            ),
            prompt
        ]
    )

    result = _read_json_response(
        response
    )

    medicines = result.get(
        "medicines",
        []
    )

    if not isinstance(
        medicines,
        list
    ):
        medicines = []

    cleaned = []

    for medicine in medicines:

        if not isinstance(
            medicine,
            dict
        ):
            continue

        name = str(
            medicine.get(
                "name",
                ""
            )
        ).strip()

        if not name:
            continue

        dosage = str(
            medicine.get(
                "dosage",
                "Unclear"
            )
        ).strip()

        quantity = str(
            medicine.get(
                "quantity",
                "Unclear"
            )
        ).strip()

        usage = str(
            medicine.get(
                "usage",
                "Instruction unclear"
            )
        ).strip()

        cleaned.append(
            {
                "name": name,
                "dosage": dosage,
                "quantity": quantity,
                "usage": usage
            }
        )

    return cleaned


def analyze_prescription_with_inventory(
    prescription_path,
    inventory
):

    try:

        # ============================================
        # STEP 1
        # READ ALL MEDICINES FROM PRESCRIPTION
        # ============================================

        prescription_medicines = (
            _read_prescription_medicines(
                prescription_path
            )
        )

        if not prescription_medicines:

            return {
                "medicines": []
            }

        # ============================================
        # STEP 2
        # PREPARE SCANNED MEDICINE INVENTORY
        # ============================================

        inventory_text = []

        for i, medicine in enumerate(
            inventory
        ):

            data = medicine.get(
                "data",
                {}
            )

            inventory_text.append(
                f"""
SCANNED MEDICINE #{i}

medicine_name:
{data.get("medicine_name", "Unknown")}

active_ingredient:
{data.get("active_ingredient", "Unknown")}

dosage:
{data.get("dosage", "Unknown")}

dosage_unit:
{data.get("dosage_unit", "")}

manufacturer:
{data.get("manufacturer", "Unknown")}
"""
            )

        inventory_text = "\n".join(
            inventory_text
        )

        # ============================================
        # STEP 3
        # SEND ALL PRESCRIPTION MEDICINES TO AI
        # ============================================

        prescription_text = []

        for i, medicine in enumerate(
            prescription_medicines
        ):

            prescription_text.append(
                f"""
PRESCRIPTION MEDICINE #{i}

name:
{medicine["name"]}

dosage:
{medicine["dosage"]}

quantity:
{medicine["quantity"]}

doctor_instruction:
{medicine["usage"]}
"""
            )

        prescription_text = "\n".join(
            prescription_text
        )

        prompt = f"""
You are MedCheck.

We already extracted ALL medicines from the doctor's
prescription.

You must compare EVERY prescription medicine against
the user's scanned medicine inventory.

IMPORTANT:

The prescription medicines listed below are the COMPLETE
list that must be returned.

You MUST return one result for EVERY prescription medicine.

NEVER remove a prescription medicine from the result.

NEVER return only matched medicines.

If a prescription medicine does NOT exist in the scanned
inventory, it MUST still appear in the result with:

available = false

matched_medicine_index = -1

matched_medicine_name = ""

usage = "Not available in scanned medicines."

The prescription medicine name MUST remain in
prescription_name.

SCANNED MEDICINE INVENTORY:

{inventory_text}

PRESCRIPTION MEDICINES:

{prescription_text}

MATCHING RULES:

1. Compare every prescription medicine with ALL scanned
   medicines.

2. A medicine is available only when the scanned medicine
   is reliably the same medicine.

3. A reliable match can be based on:
   - medicine name
   - active ingredient
   - clearly equivalent medicine identity

4. Do NOT make random matches.

5. Do NOT match similar-looking names unless they are
   actually the same medicine.

6. matched_medicine_index starts from 0.

7. If no reliable match exists:
   available = false
   matched_medicine_index = -1
   matched_medicine_name = ""

8. For a matched medicine, use the doctor's instruction
   from the prescription as the usage.

9. Do NOT invent dosage or instructions.

10. Keep EVERY prescription medicine in the final result.

11. The number of returned medicines MUST be exactly:
    {len(prescription_medicines)}

12. Return ONLY valid JSON.

JSON FORMAT:

{{
  "medicines": [
    {{
      "prescription_name": "",
      "available": false,
      "matched_medicine_index": -1,
      "matched_medicine_name": "",
      "usage": "",
      "confidence": 0.0
    }}
  ]
}}
"""

        response = client.models.generate_content(
            model=MODEL,
            contents=[
                prompt
            ]
        )

        result = _read_json_response(
            response
        )

        ai_results = result.get(
            "medicines",
            []
        )

        if not isinstance(
            ai_results,
            list
        ):
            ai_results = []

        # ============================================
        # STEP 4
        # FORCE EVERY PRESCRIPTION MEDICINE TO EXIST
        # ============================================

        final_results = []

        for i, prescription in enumerate(
            prescription_medicines
        ):

            ai_item = None

            # Try to find the AI result using the
            # prescription name.

            prescription_name = prescription[
                "name"
            ]

            for item in ai_results:

                if not isinstance(
                    item,
                    dict
                ):
                    continue

                ai_name = str(
                    item.get(
                        "prescription_name",
                        ""
                    )
                ).strip()

                if ai_name.lower() == prescription_name.lower():

                    ai_item = item
                    break

            # If AI did not return this medicine,
            # create a NOT MATCH result ourselves.

            if ai_item is None:

                final_results.append(
                    {
                        "prescription_name":
                            prescription_name,

                        "available":
                            False,

                        "matched_medicine_index":
                            -1,

                        "matched_medicine_name":
                            "",

                        "usage":
                            "Not available in scanned medicines.",

                        "confidence":
                            0.0
                    }
                )

                continue

            available = bool(
                ai_item.get(
                    "available",
                    False
                )
            )

            matched_index = ai_item.get(
                "matched_medicine_index",
                -1
            )

            try:

                matched_index = int(
                    matched_index
                )

            except (
                TypeError,
                ValueError
            ):

                matched_index = -1

            matched_name = str(
                ai_item.get(
                    "matched_medicine_name",
                    ""
                )
            ).strip()

            usage = str(
                ai_item.get(
                    "usage",
                    ""
                )
            ).strip()

            try:

                confidence = float(
                    ai_item.get(
                        "confidence",
                        0.0
                    )
                )

            except (
                TypeError,
                ValueError
            ):

                confidence = 0.0

            confidence = max(
                0.0,
                min(
                    1.0,
                    confidence
                )
            )

            # ========================================
            # VALIDATE MATCHED INDEX
            # ========================================

            if (
                matched_index < 0
                or matched_index >= len(inventory)
            ):

                available = False
                matched_index = -1
                matched_name = ""

            # ========================================
            # NOT MATCH
            # ========================================

            if not available:

                matched_index = -1
                matched_name = ""

                usage = (
                    "Not available in scanned medicines."
                )

            # ========================================
            # MATCH BUT MISSING NAME
            # ========================================

            if available:

                if not matched_name:

                    if (
                        0 <= matched_index
                        < len(inventory)
                    ):

                        matched_data = inventory[
                            matched_index
                        ].get(
                            "data",
                            {}
                        )

                        matched_name = str(
                            matched_data.get(
                                "medicine_name",
                                "Unknown"
                            )
                        )

            final_results.append(
                {
                    "prescription_name":
                        prescription_name,

                    "available":
                        available,

                    "matched_medicine_index":
                        matched_index,

                    "matched_medicine_name":
                        matched_name,

                    "usage":
                        usage,

                    "confidence":
                        confidence
                }
            )

        # ============================================
        # RETURN ALL PRESCRIPTION MEDICINES
        # ============================================

        return {
            "medicines": final_results
        }

    except MedicineAIError:

        raise

    except Exception as e:

        raise MedicineAIError(
            f"Unable to compare prescription with medicines: {str(e)}"
        )


def analyze_prescription(
    image_path
):

    try:

        medicines = _read_prescription_medicines(
            image_path
        )

        result = []

        for medicine in medicines:

            result.append(
                {
                    "name":
                        medicine["name"],

                    "dosage":
                        medicine["dosage"],

                    "quantity":
                        medicine["quantity"],

                    "usage":
                        medicine["usage"]
                }
            )

        return {
            "medicines": result,
            "confidence": 1.0
        }

    except Exception as e:

        raise MedicineAIError(
            f"Unable to read prescription: {str(e)}"
        )
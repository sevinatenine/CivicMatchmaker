import ollama
import json
from pydantic import BaseModel, Field

class FieldScore(BaseModel):
    score: int = Field(ge=0, le=100)
    reason: str

class MatchResult(BaseModel):
    fields: dict[str, FieldScore]
    match: int = Field(ge=0, le=100)

class Fields(BaseModel):
    education: FieldScore
    healthcare: FieldScore
    enviroment: FieldScore
    housing: FieldScore
    taxes: FieldScore
    economy: FieldScore

class MatchResult(BaseModel):
    fields: Fields
    match: int = Field(ge=0, le=100)

PROMPT = """Candidate data:
{candidateData}

What the user wants:
{userRequests}

Score how well the candidate matches each of the user's priorities in these categories: education, healthcare, enviroment, housing, taxes, economy.
For each category give a 0-100 score and a short reason.
Also give an overall 0-100 match score.
"""

def makePrompt(candidateData, userRequests):
    return PROMPT.replace("{candidateData}", candidateData).replace(
        "{userRequests}", ",\n".join(userRequests)
    )

def generateResponse(candidateData, userRequests):
    prompt = makePrompt(candidateData, userRequests)
    # 'llama3.1:8b'
    # 
    response = ollama.generate(
        model='llama3.2',
        prompt=prompt,
        format=MatchResult.model_json_schema(),
        options={'temperature': 0}
    )

    return MatchResult.model_validate_json(response["response"])

# def print_bar(label, score, width=30):
#     filled = int(width * score / 100)
#     bar = "█" * filled + "░" * (width - filled)
#     print(f"  {label:<12} [{bar}] {score:>3}%")

# def print_result(name, result):
#     data = result.model_dump()
#     print(f"\n{name}")
#     print("=" * 50)
#     for field_name, field in data["fields"].items():
#         print_bar(field_name, field["score"])
#         print(f"    → {field['reason']}")
#     print("-" * 50)
#     print_bar("OVERALL", data["match"])
#     print()

# candidates = {
#     "Barack Obama": obama,
#     "Donald Trump": trump,
#     "Joe Neguse": neguse,
# }

# user_wants = [
#     "good economy",
#     "higher taxes for poor people, lower taxes for rich people",
#     "really expensive houses for poor people, cheap for rich people",
#     "education should be super good - with ice cream and good teachers",
#     "turn everything into a tropical beach",
#     "expensive healthcare"
# ]

# for name, candidate_data in candidates.items():
#     result = generateResponse(candidate_data, user_wants)
#     print_result(name, result)

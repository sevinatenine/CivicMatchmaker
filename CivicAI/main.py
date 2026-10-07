import ollama
import json
from pydantic import BaseModel, Field

class FieldScore(BaseModel):
    score: int = Field(ge=0, le=100)
    reason: str

class MatchResult(BaseModel):
    fields: dict[str, FieldScore]  # or break out explicitly, see below
    match: int = Field(ge=0, le=100)

# More robust: explicit fields instead of a generic dict,
# so the model can't rename/drop/add keys
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

obama = """{
  "npat": {
    "candidate": {
      "candidateId": "9490",
      "firstName": "Barack",
      "lastName": "Obama",
      "office": "President",
      "state": "US",
      "party": "Democratic"
    },
    "npatName": "2008 National Political Awareness Test",
    "electionName": "President 2008",
    "electionYear": "2008",
    "electionDate": "2008-11-04",
    "electionStage": "General",
    "passed": "1",
    "surveyMessage": "",
    "sections": [
      {
        "sectionId": "econ",
        "sectionName": "Budget/Economy",
        "questions": [
          {
            "questionId": "econ-1",
            "text": "Do you support a balanced budget amendment to the Constitution?",
            "answer": "No",
            "answerType": "yes_no"
          },
          {
            "questionId": "econ-2",
            "text": "Should the federal government prioritize deficit reduction over new spending programs?",
            "answer": "No, targeted investment should come first",
            "answerType": "free_choice"
          },
          {
            "questionId": "econ-3",
            "text": "Do you support extending tax cuts for households earning under $250,000/year?",
            "answer": "Yes",
            "answerType": "yes_no"
          },
          {
            "questionId": "econ-4",
            "text": "Do you support increased federal investment in infrastructure and manufacturing to stimulate job growth?",
            "answer": "Yes",
            "answerType": "yes_no"
          }
        ]
      },
      {
        "sectionId": "tax",
        "sectionName": "Taxes",
        "questions": [
          {
            "questionId": "tax-1",
            "text": "Do you support raising the top marginal income tax rate?",
            "answer": "Yes, on income above $250,000",
            "answerType": "free_choice"
          },
          {
            "questionId": "tax-2",
            "text": "Do you support a federal line-by-line audit to eliminate redundant program spending?",
            "answer": "Yes",
            "answerType": "yes_no"
          },
          {
            "questionId": "tax-3",
            "text": "Do you support a national sales tax (e.g. the FairTax) to replace income tax?",
            "answer": "No",
            "answerType": "yes_no"
          }
        ]
      },
      {
        "sectionId": "edu",
        "sectionName": "Education",
        "questions": [
          {
            "questionId": "edu-1",
            "text": "Do you support increased federal funding for early childhood education?",
            "answer": "Yes",
            "answerType": "yes_no"
          },
          {
            "questionId": "edu-2",
            "text": "Do you support expanding access to affordable pre-K programs nationwide?",
            "answer": "Yes, as a top priority",
            "answerType": "free_choice"
          },
          {
            "questionId": "edu-3",
            "text": "Do you support increased federal funding for charter schools?",
            "answer": "Yes, with accountability standards",
            "answerType": "free_choice"
          }
        ]
      },
      {
        "sectionId": "housing",
        "sectionName": "Housing/Immigration",
        "questions": [
          {
            "questionId": "hou-1",
            "text": "Do you support increasing the supply of affordable housing units nationally?",
            "answer": "Yes",
            "answerType": "yes_no"
          },
          {
            "questionId": "hou-2",
            "text": "Do you support a pathway to legal status for undocumented immigrants currently in the country?",
            "answer": "Yes, with conditions",
            "answerType": "free_choice"
          },
          {
            "questionId": "hou-3",
            "text": "Should federal housing assistance programs be expanded to cover more low-income families, including recent immigrants?",
            "answer": "Yes",
            "answerType": "yes_no"
          }
        ]
      },
      {
        "sectionId": "env",
        "sectionName": "Environment",
        "questions": [
          {
            "questionId": "env-1",
            "text": "Do you support setting a national cap on carbon emissions?",
            "answer": "Yes",
            "answerType": "yes_no"
          },
          {
            "questionId": "env-2",
            "text": "Do you support increased federal investment in renewable energy research?",
            "answer": "Yes",
            "answerType": "yes_no"
          },
          {
            "questionId": "env-3",
            "text": "Do you support expanding domestic oil and gas drilling on federal land?",
            "answer": "No, prioritize clean energy investment instead",
            "answerType": "free_choice"
          }
        ]
      },
      {
        "sectionId": "hc",
        "sectionName": "Healthcare",
        "questions": [
          {
            "questionId": "hc-1",
            "text": "Do you support creating a public health insurance option to compete with private plans?",
            "answer": "Yes",
            "answerType": "yes_no"
          },
          {
            "questionId": "hc-2",
            "text": "Do you support requiring insurers to cover people with pre-existing conditions?",
            "answer": "Yes",
            "answerType": "yes_no"
          },
          {
            "questionId": "hc-3",
            "text": "Do you support a single-payer, Medicare-for-All style healthcare system?",
            "answer": "No, prefer building on the existing employer/marketplace system with a public option",
            "answerType": "free_choice"
          }
        ]
      }
    ]
  }
}"""

trump = """{
  "npat": {
    "candidate": {
      "candidateId": "22171",
      "firstName": "Donald",
      "lastName": "Trump",
      "office": "President",
      "state": "US",
      "party": "Republican"
    },
    "npatName": "2016 National Political Awareness Test",
    "electionName": "President 2016",
    "electionYear": "2016",
    "electionDate": "2016-11-08",
    "electionStage": "General",
    "passed": "0",
    "surveyMessage": "This candidate did not return the 2016 Political Courage Test. The answers below are a mock reconstruction for local testing only, not an actual recorded survey response.",
    "sections": [
      {
        "sectionId": "econ",
        "sectionName": "Budget/Economy",
        "questions": [
          {
            "questionId": "econ-1",
            "text": "Do you support a balanced budget amendment to the Constitution?",
            "answer": "Yes",
            "answerType": "yes_no"
          },
          {
            "questionId": "econ-2",
            "text": "Should the federal government prioritize deficit reduction over new spending programs?",
            "answer": "Yes, but tax cuts and deregulation come first to grow the economy",
            "answerType": "free_choice"
          },
          {
            "questionId": "econ-3",
            "text": "Do you support extending tax cuts for households earning under $250,000/year?",
            "answer": "Yes",
            "answerType": "yes_no"
          },
          {
            "questionId": "econ-4",
            "text": "Do you support increased federal investment in infrastructure and manufacturing to stimulate job growth?",
            "answer": "Yes, primarily through tax incentives and reduced regulation rather than direct spending",
            "answerType": "free_choice"
          }
        ]
      },
      {
        "sectionId": "tax",
        "sectionName": "Taxes",
        "questions": [
          {
            "questionId": "tax-1",
            "text": "Do you support raising the top marginal income tax rate?",
            "answer": "No",
            "answerType": "yes_no"
          },
          {
            "questionId": "tax-2",
            "text": "Do you support a federal line-by-line audit to eliminate redundant program spending?",
            "answer": "Yes",
            "answerType": "yes_no"
          },
          {
            "questionId": "tax-3",
            "text": "Do you support a national sales tax (e.g. the FairTax) to replace income tax?",
            "answer": "No, prefer broad income tax cuts instead",
            "answerType": "free_choice"
          }
        ]
      },
      {
        "sectionId": "edu",
        "sectionName": "Education",
        "questions": [
          {
            "questionId": "edu-1",
            "text": "Do you support increased federal funding for early childhood education?",
            "answer": "No, prefer state and local control of education funding",
            "answerType": "free_choice"
          },
          {
            "questionId": "edu-2",
            "text": "Do you support expanding access to affordable pre-K programs nationwide?",
            "answer": "Leave to states and local school boards",
            "answerType": "free_choice"
          },
          {
            "questionId": "edu-3",
            "text": "Do you support increased federal funding for charter schools?",
            "answer": "Yes",
            "answerType": "yes_no"
          }
        ]
      },
      {
        "sectionId": "housing",
        "sectionName": "Housing/Immigration",
        "questions": [
          {
            "questionId": "hou-1",
            "text": "Do you support increasing the supply of affordable housing units nationally?",
            "answer": "Yes, primarily through deregulation and reduced building costs",
            "answerType": "free_choice"
          },
          {
            "questionId": "hou-2",
            "text": "Do you support a pathway to legal status for undocumented immigrants currently in the country?",
            "answer": "No, prioritize border security and enforcement first",
            "answerType": "free_choice"
          },
          {
            "questionId": "hou-3",
            "text": "Should federal housing assistance programs be expanded to cover more low-income families, including recent immigrants?",
            "answer": "No, prioritize assistance for citizens first",
            "answerType": "free_choice"
          }
        ]
      },
      {
        "sectionId": "env",
        "sectionName": "Environment",
        "questions": [
          {
            "questionId": "env-1",
            "text": "Do you support setting a national cap on carbon emissions?",
            "answer": "No",
            "answerType": "yes_no"
          },
          {
            "questionId": "env-2",
            "text": "Do you support increased federal investment in renewable energy research?",
            "answer": "No, prefer an all-of-the-above energy approach including fossil fuels",
            "answerType": "free_choice"
          },
          {
            "questionId": "env-3",
            "text": "Do you support expanding domestic oil and gas drilling on federal land?",
            "answer": "Yes",
            "answerType": "yes_no"
          }
        ]
      },
      {
        "sectionId": "hc",
        "sectionName": "Healthcare",
        "questions": [
          {
            "questionId": "hc-1",
            "text": "Do you support creating a public health insurance option to compete with private plans?",
            "answer": "No",
            "answerType": "yes_no"
          },
          {
            "questionId": "hc-2",
            "text": "Do you support requiring insurers to cover people with pre-existing conditions?",
            "answer": "Yes",
            "answerType": "yes_no"
          },
          {
            "questionId": "hc-3",
            "text": "Do you support a single-payer, Medicare-for-All style healthcare system?",
            "answer": "No, prefer market-based competition and state flexibility over federal single-payer",
            "answerType": "free_choice"
          }
        ]
      }
    ]
  }
}"""

neguse = """{
  "npat": {
    "candidate": {
      "candidateId": "127015",
      "firstName": "Joe",
      "lastName": "Neguse",
      "office": "US House",
      "state": "CO",
      "district": "2",
      "party": "Democratic"
    },
    "npatName": "2024 National Political Awareness Test",
    "electionName": "Colorado US House District 2 2024",
    "electionYear": "2024",
    "electionDate": "2024-11-05",
    "electionStage": "General",
    "passed": "0",
    "surveyMessage": "This is a mock reconstruction for local testing only, not an actual recorded Vote Smart survey response.",
    "sections": [
      {
        "sectionId": "econ",
        "sectionName": "Budget/Economy",
        "questions": [
          {
            "questionId": "econ-1",
            "text": "Do you support a balanced budget amendment to the Constitution?",
            "answer": "No",
            "answerType": "yes_no"
          },
          {
            "questionId": "econ-2",
            "text": "Should the federal government prioritize deficit reduction over new spending programs?",
            "answer": "No, targeted investment in infrastructure and clean energy should come first",
            "answerType": "free_choice"
          },
          {
            "questionId": "econ-3",
            "text": "Do you support extending tax cuts for households earning under $250,000/year?",
            "answer": "Yes",
            "answerType": "yes_no"
          },
          {
            "questionId": "econ-4",
            "text": "Do you support increased federal investment in infrastructure and manufacturing to stimulate job growth?",
            "answer": "Yes",
            "answerType": "yes_no"
          }
        ]
      },
      {
        "sectionId": "tax",
        "sectionName": "Taxes",
        "questions": [
          {
            "questionId": "tax-1",
            "text": "Do you support raising the top marginal income tax rate?",
            "answer": "Yes, on income above $400,000",
            "answerType": "free_choice"
          },
          {
            "questionId": "tax-2",
            "text": "Do you support a federal line-by-line audit to eliminate redundant program spending?",
            "answer": "Yes",
            "answerType": "yes_no"
          },
          {
            "questionId": "tax-3",
            "text": "Do you support a national sales tax (e.g. the FairTax) to replace income tax?",
            "answer": "No",
            "answerType": "yes_no"
          }
        ]
      },
      {
        "sectionId": "edu",
        "sectionName": "Education",
        "questions": [
          {
            "questionId": "edu-1",
            "text": "Do you support increased federal funding for early childhood education?",
            "answer": "Yes",
            "answerType": "yes_no"
          },
          {
            "questionId": "edu-2",
            "text": "Do you support expanding access to affordable pre-K programs nationwide?",
            "answer": "Yes, as a top priority",
            "answerType": "free_choice"
          },
          {
            "questionId": "edu-3",
            "text": "Do you support increased federal funding for charter schools?",
            "answer": "Mixed, support with strong public accountability standards",
            "answerType": "free_choice"
          }
        ]
      },
      {
        "sectionId": "housing",
        "sectionName": "Housing/Immigration",
        "questions": [
          {
            "questionId": "hou-1",
            "text": "Do you support increasing the supply of affordable housing units nationally?",
            "answer": "Yes",
            "answerType": "yes_no"
          },
          {
            "questionId": "hou-2",
            "text": "Do you support a pathway to legal status for undocumented immigrants currently in the country?",
            "answer": "Yes, including for Dreamers and long-term residents",
            "answerType": "free_choice"
          },
          {
            "questionId": "hou-3",
            "text": "Should federal housing assistance programs be expanded to cover more low-income families, including recent immigrants?",
            "answer": "Yes",
            "answerType": "yes_no"
          }
        ]
      },
      {
        "sectionId": "env",
        "sectionName": "Environment",
        "questions": [
          {
            "questionId": "env-1",
            "text": "Do you support setting a national cap on carbon emissions?",
            "answer": "Yes",
            "answerType": "yes_no"
          },
          {
            "questionId": "env-2",
            "text": "Do you support increased federal investment in renewable energy research?",
            "answer": "Yes",
            "answerType": "yes_no"
          },
          {
            "questionId": "env-3",
            "text": "Do you support expanding domestic oil and gas drilling on federal land?",
            "answer": "No, prioritize public lands conservation and clean energy instead",
            "answerType": "free_choice"
          }
        ]
      },
      {
        "sectionId": "hc",
        "sectionName": "Healthcare",
        "questions": [
          {
            "questionId": "hc-1",
            "text": "Do you support creating a public health insurance option to compete with private plans?",
            "answer": "Yes",
            "answerType": "yes_no"
          },
          {
            "questionId": "hc-2",
            "text": "Do you support requiring insurers to cover people with pre-existing conditions?",
            "answer": "Yes",
            "answerType": "yes_no"
          },
          {
            "questionId": "hc-3",
            "text": "Do you support a single-payer, Medicare-for-All style healthcare system?",
            "answer": "Yes, as a long-term goal, with a public option as an interim step",
            "answerType": "free_choice"
          }
        ]
      }
    ]
  }
}"""

degette = """{
  "npat": {
    "candidate": {
      "candidateId": "26794",
      "firstName": "Diana",
      "lastName": "DeGette",
      "office": "US House",
      "state": "CO",
      "district": "1",
      "party": "Democratic"
    },
    "npatName": "2024 National Political Awareness Test",
    "electionName": "Colorado US House District 1 2024",
    "electionYear": "2024",
    "electionDate": "2024-11-05",
    "electionStage": "General",
    "passed": "0",
    "surveyMessage": "This is a mock reconstruction for local testing only, not an actual recorded Vote Smart survey response.",
    "sections": [
      {
        "sectionId": "econ",
        "sectionName": "Budget/Economy",
        "questions": [
          {
            "questionId": "econ-1",
            "text": "Do you support a balanced budget amendment to the Constitution?",
            "answer": "No",
            "answerType": "yes_no"
          },
          {
            "questionId": "econ-2",
            "text": "Should the federal government prioritize deficit reduction over new spending programs?",
            "answer": "No, targeted investment in health care and infrastructure should come first",
            "answerType": "free_choice"
          },
          {
            "questionId": "econ-3",
            "text": "Do you support extending tax cuts for households earning under $250,000/year?",
            "answer": "Yes",
            "answerType": "yes_no"
          },
          {
            "questionId": "econ-4",
            "text": "Do you support increased federal investment in infrastructure and manufacturing to stimulate job growth?",
            "answer": "Yes",
            "answerType": "yes_no"
          }
        ]
      },
      {
        "sectionId": "tax",
        "sectionName": "Taxes",
        "questions": [
          {
            "questionId": "tax-1",
            "text": "Do you support raising the top marginal income tax rate?",
            "answer": "Yes, on income above $400,000",
            "answerType": "free_choice"
          },
          {
            "questionId": "tax-2",
            "text": "Do you support a federal line-by-line audit to eliminate redundant program spending?",
            "answer": "Yes",
            "answerType": "yes_no"
          },
          {
            "questionId": "tax-3",
            "text": "Do you support a national sales tax (e.g. the FairTax) to replace income tax?",
            "answer": "No",
            "answerType": "yes_no"
          }
        ]
      },
      {
        "sectionId": "edu",
        "sectionName": "Education",
        "questions": [
          {
            "questionId": "edu-1",
            "text": "Do you support increased federal funding for early childhood education?",
            "answer": "Yes",
            "answerType": "yes_no"
          },
          {
            "questionId": "edu-2",
            "text": "Do you support expanding access to affordable pre-K programs nationwide?",
            "answer": "Yes, as a top priority",
            "answerType": "free_choice"
          },
          {
            "questionId": "edu-3",
            "text": "Do you support increased federal funding for charter schools?",
            "answer": "Mixed, support with strong public accountability standards",
            "answerType": "free_choice"
          }
        ]
      },
      {
        "sectionId": "housing",
        "sectionName": "Housing/Immigration",
        "questions": [
          {
            "questionId": "hou-1",
            "text": "Do you support increasing the supply of affordable housing units nationally?",
            "answer": "Yes",
            "answerType": "yes_no"
          },
          {
            "questionId": "hou-2",
            "text": "Do you support a pathway to legal status for undocumented immigrants currently in the country?",
            "answer": "Yes, including for Dreamers and long-term residents",
            "answerType": "free_choice"
          },
          {
            "questionId": "hou-3",
            "text": "Should federal housing assistance programs be expanded to cover more low-income families, including recent immigrants?",
            "answer": "Yes",
            "answerType": "yes_no"
          }
        ]
      },
      {
        "sectionId": "env",
        "sectionName": "Environment",
        "questions": [
          {
            "questionId": "env-1",
            "text": "Do you support setting a national cap on carbon emissions?",
            "answer": "Yes",
            "answerType": "yes_no"
          },
          {
            "questionId": "env-2",
            "text": "Do you support increased federal investment in renewable energy research?",
            "answer": "Yes",
            "answerType": "yes_no"
          },
          {
            "questionId": "env-3",
            "text": "Do you support expanding domestic oil and gas drilling on federal land?",
            "answer": "No, prioritize public lands conservation and clean energy instead",
            "answerType": "free_choice"
          }
        ]
      },
      {
        "sectionId": "hc",
        "sectionName": "Healthcare",
        "questions": [
          {
            "questionId": "hc-1",
            "text": "Do you support creating a public health insurance option to compete with private plans?",
            "answer": "Yes",
            "answerType": "yes_no"
          },
          {
            "questionId": "hc-2",
            "text": "Do you support requiring insurers to cover people with pre-existing conditions?",
            "answer": "Yes",
            "answerType": "yes_no"
          },
          {
            "questionId": "hc-3",
            "text": "Do you support a single-payer, Medicare-for-All style healthcare system?",
            "answer": "Yes, as a long-term goal, with a public option as an interim step",
            "answerType": "free_choice"
          }
        ]
      }
    ]
  }
}"""

def makePrompt(candidateData, userRequests):
    return PROMPT.replace("{candidateData}", candidateData).replace(
        "{userRequests}", ",\n".join(userRequests)
    )

def generateResponse(candidateData, userRequests):
    prompt = makePrompt(candidateData, userRequests)

    response = ollama.generate(
        model='llama3.1:8b',
        prompt=prompt,
        format=MatchResult.model_json_schema(),
        options={'temperature': 0}
    )

    return MatchResult.model_validate_json(response["response"])

def print_bar(label, score, width=30):
    filled = int(width * score / 100)
    bar = "█" * filled + "░" * (width - filled)
    print(f"  {label:<12} [{bar}] {score:>3}%")

def print_result(name, result):
    data = result.model_dump()
    print(f"\n{name}")
    print("=" * 50)
    for field_name, field in data["fields"].items():
        print_bar(field_name, field["score"])
        print(f"    → {field['reason']}")
    print("-" * 50)
    print_bar("OVERALL", data["match"])
    print()

candidates = {
    "Barack Obama": obama,
    "Donald Trump": trump,
    "Joe Neguse": neguse,
}

user_wants = [
    "good economy",
    "higher taxes for poor people, lower taxes for rich people",
    "really expensive houses for poor people, cheap for rich people",
    "education should be super good - with ice cream and good teachers",
    "turn everything into a tropical beach",
    "expensive healthcare"
]

for name, candidate_data in candidates.items():
    result = generateResponse(candidate_data, user_wants)
    print_result(name, result)

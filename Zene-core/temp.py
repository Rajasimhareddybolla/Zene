{
  "name": "upsc_query_schema",
  "strict": True,
  "schema": {
    "type": "object",
    "properties": {
      "topics": {
        "type": "array",
        "description": "A list of the most relevant UPSC curriculum topics.",
        "items": {
          "type": "string"
        }
      },
      "sub-topics": {
        "type": "array",
        "description": "A list of the most relevant UPSC curriculum sub-topics.",
        "items": {
          "type": "string"
        }
      },
      "core_topic": {
        "type": "string",
        "description": "Core topic/focus/subject of the user query."
      },
      "user_intent": {
        "type": "string",
        "description": "Describes the user's query intent."
      },
      "is_ambiguous": {
        "type": "boolean",
        "description": "Indicates if the query is ambiguous."
      },
      "query_category": {
        "type": "string",
        "description": "One of the specified types related to the query.",
        "enum": [
          "chat",
          "question",
          "concept"
        ]
      },
      "target": {
        "type": "string",
        "description": "Identify the target of the user query.",
        "enum": [
          "agent",
          "exam",
          "curriculum",
          "user",
          "other"
        ]
      },
      "is_in_upsc_scope": {
        "type": "boolean",
        "description": "Indicates if the query is within the UPSC examination scope."
      },
      "next_agent": {
        "type": "string",
        "description": "Pick one of the specified agents.",
        "enum": [
          "Comet",
          "Thalia",
          "Milo"
        ]
      },
      "vector_database_retrieval_queries": {
        "type": "array",
        "description": "List of zero or more concise, effective and independent queries to retrieve all related content needed to address the user query.",
        "items": {
          "type": "string"
        }
      }
    },
    "required": [
      "topics",
      "sub-topics",
      "core_topic",
      "user_intent",
      "is_ambiguous",
      "query_category",
      "target",
      "is_in_upsc_scope",
      "next_agent",
      "vector_database_retrieval_queries"
    ],
    "additionalProperties": False
  }
}  
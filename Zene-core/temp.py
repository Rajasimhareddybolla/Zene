{
  "name": "upsc_query_schema",
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
        "enum": [
          "chat",
          "question",
          "concept"
        ],
        "description": "Specifies the category of the user's query."
      },
      "target": {
        "type": "string",
        "enum": [
          "agent",
          "exam",
          "curriculum",
          "user",
          "other"
        ],
        "description": "Identifies the target of the user query."
      },
      "is_in_upsc_scope": {
        "type": "boolean",
        "description": "Indicates if the query is within the UPSC examination scope."
      },
      "is_topic_switched": {
        "type": "boolean",
        "description": "Indicates if the topic/sub-topic/theme changed from the previous query."
      },
      "next_agent": {
        "type": "string",
        "enum": [
          "Comet",
          "Thalia",
          "Milo"
        ],
        "description": "Selects the next agent to handle the query."
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
      "is_topic_switched",
      "next_agent",
      "vector_database_retrieval_queries"
    ],
    "additionalProperties": False
  },
  "strict": True
}
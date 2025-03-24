{
  "name": "solution_schema",
  "strict": True,
  "schema": {
    "type": "object",
    "properties": {
      "solution_notes": {
        "type": "object",
        "properties": {
          "summary": {
            "type": "string",
            "description": "Brief summary of overall solution flow."
          },
          "answer_options_provided": {
            "type": "array",
            "description": "List of answer options provided.",
            "items": {
              "type": "string"
            }
          },
          "sections": {
            "type": "array",
            "description": "Breakdown into well-defined, self-contained and individual sections with coherent flow.",
            "items": {
              "type": "object",
              "properties": {
                "section_sequential_id": {
                  "type": "integer",
                  "description": "Sequential integer ID"
                },
                "title": {
                  "type": "string",
                  "description": "Section title depicting the core topics."
                },
                "content": {
                  "type": "array",
                  "description": "List of all most granular independent content pieces or statements within this section.",
                  "items": {
                    "type": "object",
                    "properties": {
                      "content_sequential_id": {
                        "type": "string",
                        "description": "String ID following a hierarchical numbering system, example 1.1."
                      },
                      "text": {
                        "type": "string",
                        "description": "Single content statement."
                      },
                      "tags": {
                        "type": "array",
                        "description": "List of key words or data in the order of their appearance in the above statement.",
                        "items": {
                          "type": "string"
                        }
                      },
                      "references": {
                        "type": "array",
                        "description": "References to other content pieces that are not part of this statement.",
                        "items": {
                          "type": "object",
                          "properties": {
                            "current_tag": {
                              "type": "string",
                              "description": "Single identified tag that has conceptual reference to other content."
                            },
                            "other_content_sequential_id": {
                              "type": "string",
                              "description": "Content sequential ID."
                            },
                            "other_content_tags": {
                              "type": "array",
                              "description": "List of tags from referenced content piece.",
                              "items": {
                                "type": "string"
                              }
                            }
                          },
                          "required": [
                            "current_tag",
                            "other_content_sequential_id",
                            "other_content_tags"
                          ],
                          "additionalProperties": False
                        }
                      }
                    },
                    "required": [
                      "content_sequential_id",
                      "text",
                      "tags",
                      "references"
                    ],
                    "additionalProperties": False
                  }
                },
                "slide_layout": {
                  "type": "string",
                  "description": "Brief description of how to design a slide with this section content."
                },
                "assessment_questions": {
                  "type": "array",
                  "description": "List of assessment questions.",
                  "items": {
                    "type": "object",
                    "properties": {
                      "question_sequential_id": {
                        "type": "string",
                        "description": "String ID following a hierarchical numbering system with Q suffix, example 1.Q1."
                      },
                      "concept_to_be_assessed": {
                        "type": "string",
                        "description": "Short description of the concept to be assessed. DO NOT generate a question."
                      }
                    },
                    "required": [
                      "question_sequential_id",
                      "concept_to_be_assessed"
                    ],
                    "additionalProperties": False
                  }
                }
              },
              "required": [
                "section_sequential_id",
                "title",
                "content",
                "slide_layout",
                "assessment_questions"
              ],
              "additionalProperties": False
            }
          },
          "final_answer": {
            "type": "object",
            "properties": {
              "correct_answer_options": {
                "type": "array",
                "description": "List all correct options among the provided options.",
                "items": {
                  "type": "string"
                }
              },
              "correct_answer_descriptions": {
                "type": "array",
                "description": "List all correct answer descriptions of the provided options.",
                "items": {
                  "type": "string"
                }
              }
            },
            "required": [
              "correct_answer_options",
              "correct_answer_descriptions"
            ],
            "additionalProperties": False
          },
          "content_checks": {
            "type": "object",
            "properties": {
              "accuracy_through_sources": {
                "type": "array",
                "description": "List specific textbooks/supporting content sections.",
                "items": {
                  "type": "string"
                }
              },
              "accuracy_proof": {
                "type": "array",
                "description": "Prove the answer through detailed steps.",
                "items": {
                  "type": "string"
                }
              },
              "missing_content": {
                "type": "array",
                "description": "List all the previous year question themes related to this section concept that cannot be answered even with this content.",
                "items": {
                  "type": "string"
                }
              },
              "is_final_answer_among_answer_options": {
                "type": "boolean",
                "description": "Indicates if final answer is among the options."
              }
            },
            "required": [
              "accuracy_through_sources",
              "accuracy_proof",
              "missing_content",
              "is_final_answer_among_answer_options"
            ],
            "additionalProperties": False
          }
        },
        "required": [
          "summary",
          "answer_options_provided",
          "sections",
          "final_answer",
          "content_checks"
        ],
        "additionalProperties": False
      }
    },
    "required": [
      "solution_notes"
    ],
    "additionalProperties": False
  }
}
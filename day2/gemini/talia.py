import base64
import os
from google import genai
from google.genai import types


def generate(sys_prompt,text_masg):
    client = genai.Client(
        api_key=os.environ.get("GEMINI_API_KEY"),
    )

    model = "gemini-2.0-flash"
    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(text= text_masg),
            ],
        ),
    ]
    generate_content_config = types.GenerateContentConfig(
        temperature=1,
        top_p=0.95,
        top_k=40,
        max_output_tokens=8192,
        response_mime_type="application/json",
        response_schema=genai.types.Schema(
            type = genai.types.Type.OBJECT,
            required = ["solution_notes"],
            properties = {
                "solution_notes": genai.types.Schema(
                    type = genai.types.Type.OBJECT,
                    required = ["summary", "answer_options_provided", "sections", "final_answer", "content_checks"],
                    properties = {
                        "summary": genai.types.Schema(
                            type = genai.types.Type.STRING,
                            description = "Brief summary of overall solution flow.",
                        ),
                        "answer_options_provided": genai.types.Schema(
                            type = genai.types.Type.ARRAY,
                            description = "List of answer options provided.",
                            items = genai.types.Schema(
                                type = genai.types.Type.STRING,
                            ),
                        ),
                        "sections": genai.types.Schema(
                            type = genai.types.Type.ARRAY,
                            description = "Breakdown into well-defined, self-contained and individual sections with coherent flow.",
                            items = genai.types.Schema(
                                type = genai.types.Type.OBJECT,
                                required = ["section_sequential_id", "title", "content", "slide_layout", "assessment_questions"],
                                properties = {
                                    "section_sequential_id": genai.types.Schema(
                                        type = genai.types.Type.INTEGER,
                                        description = "Sequential integer ID",
                                    ),
                                    "title": genai.types.Schema(
                                        type = genai.types.Type.STRING,
                                        description = "Section title depicting the core topics.",
                                    ),
                                    "content": genai.types.Schema(
                                        type = genai.types.Type.ARRAY,
                                        description = "List of all most granular independent content pieces or statements within this section.",
                                        items = genai.types.Schema(
                                            type = genai.types.Type.OBJECT,
                                            required = ["content_sequential_id", "text", "tags", "references"],
                                            properties = {
                                                "content_sequential_id": genai.types.Schema(
                                                    type = genai.types.Type.STRING,
                                                    description = "String ID following a hierarchical numbering system, example 1.1.",
                                                ),
                                                "text": genai.types.Schema(
                                                    type = genai.types.Type.STRING,
                                                    description = "Single content statement.",
                                                ),
                                                "tags": genai.types.Schema(
                                                    type = genai.types.Type.ARRAY,
                                                    description = "List of key words or data in the order of their appearance in the above statement.",
                                                    items = genai.types.Schema(
                                                        type = genai.types.Type.STRING,
                                                    ),
                                                ),
                                                "references": genai.types.Schema(
                                                    type = genai.types.Type.ARRAY,
                                                    description = "References to other content pieces that are not part of this statement.",
                                                    items = genai.types.Schema(
                                                        type = genai.types.Type.OBJECT,
                                                        required = ["current_tag", "other_content_sequential_id", "other_content_tags"],
                                                        properties = {
                                                            "current_tag": genai.types.Schema(
                                                                type = genai.types.Type.STRING,
                                                                description = "Single identified tag that has conceptual reference to other content.",
                                                            ),
                                                            "other_content_sequential_id": genai.types.Schema(
                                                                type = genai.types.Type.STRING,
                                                                description = "Content sequential ID.",
                                                            ),
                                                            "other_content_tags": genai.types.Schema(
                                                                type = genai.types.Type.ARRAY,
                                                                description = "List of tags from referenced content piece.",
                                                                items = genai.types.Schema(
                                                                    type = genai.types.Type.STRING,
                                                                ),
                                                            ),
                                                        },
                                                    ),
                                                ),
                                            },
                                        ),
                                    ),
                                    "slide_layout": genai.types.Schema(
                                        type = genai.types.Type.STRING,
                                        description = "Brief description of how to design a slide with this section content.",
                                    ),
                                    "assessment_questions": genai.types.Schema(
                                        type = genai.types.Type.ARRAY,
                                        description = "List of assessment questions.",
                                        items = genai.types.Schema(
                                            type = genai.types.Type.OBJECT,
                                            required = ["question_sequential_id", "concept_to_be_assessed"],
                                            properties = {
                                                "question_sequential_id": genai.types.Schema(
                                                    type = genai.types.Type.STRING,
                                                    description = "String ID following a hierarchical numbering system with Q suffix, example 1.Q1.",
                                                ),
                                                "concept_to_be_assessed": genai.types.Schema(
                                                    type = genai.types.Type.STRING,
                                                    description = "Short description of the concept to be assessed. DO NOT generate a question.",
                                                ),
                                            },
                                        ),
                                    ),
                                },
                            ),
                        ),
                        "final_answer": genai.types.Schema(
                            type = genai.types.Type.OBJECT,
                            required = ["correct_answer_options", "correct_answer_descriptions"],
                            properties = {
                                "correct_answer_options": genai.types.Schema(
                                    type = genai.types.Type.ARRAY,
                                    description = "List all correct options among the provided options.",
                                    items = genai.types.Schema(
                                        type = genai.types.Type.STRING,
                                    ),
                                ),
                                "correct_answer_descriptions": genai.types.Schema(
                                    type = genai.types.Type.ARRAY,
                                    description = "List all correct answer descriptions of the provided options.",
                                    items = genai.types.Schema(
                                        type = genai.types.Type.STRING,
                                    ),
                                ),
                            },
                        ),
                        "content_checks": genai.types.Schema(
                            type = genai.types.Type.OBJECT,
                            required = ["accuracy_through_sources", "accuracy_proof", "missing_content", "is_final_answer_among_answer_options"],
                            properties = {
                                "accuracy_through_sources": genai.types.Schema(
                                    type = genai.types.Type.ARRAY,
                                    description = "List specific textbooks/supporting content sections.",
                                    items = genai.types.Schema(
                                        type = genai.types.Type.STRING,
                                    ),
                                ),
                                "accuracy_proof": genai.types.Schema(
                                    type = genai.types.Type.ARRAY,
                                    description = "Prove the answer through detailed steps.",
                                    items = genai.types.Schema(
                                        type = genai.types.Type.STRING,
                                    ),
                                ),
                                "missing_content": genai.types.Schema(
                                    type = genai.types.Type.ARRAY,
                                    description = "List all the previous year question themes related to this section concept that cannot be answered even with this content.",
                                    items = genai.types.Schema(
                                        type = genai.types.Type.STRING,
                                    ),
                                ),
                                "is_final_answer_among_answer_options": genai.types.Schema(
                                    type = genai.types.Type.BOOLEAN,
                                    description = "Indicates if final answer is among the options.",
                                ),
                            },
                        ),
                    },
                ),
            },
        ),
        system_instruction=[
            types.Part.from_text(text=sys_prompt),
        ],
    )


    response = client.models.generate_content(
        model=model,
        contents=contents,
        config=generate_content_config,
    )
    return response.text

if __name__ == "__main__":
    generate()

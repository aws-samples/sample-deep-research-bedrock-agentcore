"""
Robust JSON parser for LLM responses

Handles common LLM JSON formatting issues without being overly aggressive.
"""

import json
import re
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def parse_llm_json(
    response_text: str,
    context: str = "LLM response",
    auto_fix_common_errors: bool = True,
    strict: bool = False
) -> Dict[str, Any]:
    """
    Parse JSON from LLM response with defensive error handling.

    Args:
        response_text: Raw text response from LLM
        context: Description of what's being parsed (for logging)
        auto_fix_common_errors: Try to fix common LLM mistakes (trailing commas, etc)
        strict: If True, raise on any parse failure. If False, try harder to extract partial data.

    Returns:
        Parsed JSON as dictionary

    Raises:
        ValueError: If JSON cannot be parsed after all strategies

    Common LLM mistakes handled:
    - Markdown code blocks (```json ... ```)
    - Text before/after JSON
    - Trailing commas before } or ]
    - Missing commas between properties (limited heuristic)
    """

    if not response_text or not response_text.strip():
        raise ValueError(f"Empty response for {context}")

    original_text = response_text
    parse_attempts = []

    # === STEP 1: Clean up markdown and extract JSON ===
    text = response_text.strip()

    # Remove markdown code blocks
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
        logger.debug(f"[{context}] Removed ```json``` markdown wrapper")
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()
        logger.debug(f"[{context}] Removed ``` markdown wrapper")

    # Extract JSON if there's text before/after (find first { and last })
    start_idx = text.find("{")
    end_idx = text.rfind("}")
    if start_idx != -1 and end_idx != -1 and start_idx < end_idx:
        text = text[start_idx:end_idx + 1]
        logger.debug(f"[{context}] Extracted JSON from position {start_idx} to {end_idx}")
    else:
        logger.warning(f"[{context}] Could not find JSON braces in response")

    # === STEP 2: Try direct parse ===
    try:
        result = json.loads(text)
        logger.info(f"[{context}] ✅ JSON parsed successfully (direct)")
        return result
    except json.JSONDecodeError as e:
        parse_attempts.append(f"Direct parse: {e}")
        logger.debug(f"[{context}] Direct parse failed: {e}")

    # === STEP 3: Auto-fix common errors ===
    if auto_fix_common_errors:
        try:
            fixed_text = text

            # Fix trailing commas (most common LLM mistake)
            # "key": "value",}  →  "key": "value"}
            fixed_text = re.sub(r',(\s*[}\]])', r'\1', fixed_text)

            # Fix missing commas between string properties (heuristic)
            # "key": "value"\n"key2"  →  "key": "value",\n"key2"
            fixed_text = re.sub(r'("\s*)\n(\s*"[^"]+"\s*:)', r'\1,\n\2', fixed_text)

            if fixed_text != text:
                result = json.loads(fixed_text)
                logger.info(f"[{context}] ✅ JSON parsed successfully (after auto-fix)")
                return result
        except json.JSONDecodeError as e:
            parse_attempts.append(f"Auto-fix parse: {e}")
            logger.debug(f"[{context}] Auto-fix parse failed: {e}")

    # === STEP 4: Strict mode check ===
    if strict:
        error_msg = f"Failed to parse JSON for {context} after {len(parse_attempts)} attempts:\n"
        error_msg += "\n".join(f"  {i+1}. {attempt}" for i, attempt in enumerate(parse_attempts))
        error_msg += f"\n\nOriginal text (first 500 chars):\n{original_text[:500]}"
        logger.error(error_msg)
        raise ValueError(error_msg)

    # === STEP 5: Last resort - try to salvage partial JSON ===
    try:
        # Try to find complete JSON objects/arrays within the text
        # This is a last-ditch effort to extract something useful
        logger.warning(f"[{context}] Attempting partial JSON extraction...")

        # Find all potential JSON objects
        json_objects = re.findall(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', text)
        for obj_text in json_objects:
            try:
                result = json.loads(obj_text)
                logger.warning(f"[{context}] ⚠️ Extracted partial JSON object")
                return result
            except:
                continue

        # If no objects, try arrays
        json_arrays = re.findall(r'\[[^\[\]]*(?:\[[^\[\]]*\][^\[\]]*)*\]', text)
        for arr_text in json_arrays:
            try:
                result = json.loads(arr_text)
                logger.warning(f"[{context}] ⚠️ Extracted partial JSON array")
                return {"data": result}  # Wrap array in object
            except:
                continue

    except Exception as e:
        parse_attempts.append(f"Partial extraction: {e}")
        logger.debug(f"[{context}] Partial extraction failed: {e}")

    # === Final failure ===
    error_msg = f"Failed to parse JSON for {context} after all strategies:\n"
    error_msg += "\n".join(f"  {i+1}. {attempt}" for i, attempt in enumerate(parse_attempts))
    error_msg += f"\n\nOriginal text (first 500 chars):\n{original_text[:500]}"
    logger.error(error_msg)
    raise ValueError(error_msg)


def extract_json_from_response(
    response_text: str,
    expected_keys: Optional[list] = None
) -> Dict[str, Any]:
    """
    Convenience wrapper with validation of expected keys.

    Args:
        response_text: Raw text from LLM
        expected_keys: List of keys that must be present in the result

    Returns:
        Parsed JSON dictionary

    Raises:
        ValueError: If parsing fails or expected keys are missing
    """
    result = parse_llm_json(response_text)

    if expected_keys:
        missing_keys = [key for key in expected_keys if key not in result]
        if missing_keys:
            raise ValueError(f"Missing expected keys in JSON: {missing_keys}. Got: {list(result.keys())}")

    return result

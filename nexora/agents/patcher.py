"""
Patcher Agent for NEXORA-8.
Generates and applies minimal search-and-replace patches and unified diffs.
"""

from dataclasses import dataclass, field
import difflib
import json
import re
from typing import Dict, List, Optional, Tuple
from nexora.agents.base import BaseAgent, AgentStatus
from nexora.agents.planner import RepairPlan
from nexora.llm.client import LLMClient
from nexora.verifier.sandbox import SandboxRunner


@dataclass
class GeneratedPatch:
    file_path: str
    search_block: str
    replace_block: str
    explanation: str
    diff_text: str = ""
    success: bool = False
    error: Optional[str] = None


class PatcherAgent(BaseAgent):
    """Synthesizes targeted, minimal code modifications."""

    def __init__(self, llm_client: LLMClient, max_diff_lines: int = 120, max_changed_files: int = 5, max_added_lines: int = 80):
        super().__init__(name="Patcher", role_description="Synthesizes targeted minimal diffs and patches")
        self.llm_client = llm_client
        self.max_diff_lines = max_diff_lines
        self.max_changed_files = max_changed_files
        self.max_added_lines = max_added_lines

    def patch(
        self,
        sandbox: SandboxRunner,
        plan: RepairPlan,
        attempt_number: int = 1,
        feedback: Optional[str] = None,
    ) -> List[GeneratedPatch]:
        self.set_status(AgentStatus.WORKING, f"Synthesizing minimal patch (Attempt {attempt_number})...")

        results: List[GeneratedPatch] = []

        if len(plan.target_files) > self.max_changed_files:
            self.log(f"Patch rejected: {len(plan.target_files)} target files exceeds limit {self.max_changed_files}.")
            return results

        for target_file in plan.target_files[:self.max_changed_files]:
            try:
                original_content = sandbox.read_file(target_file)
            except Exception as e:
                self.log(f"Warning: could not read {target_file}: {e}")
                continue

            prompt = f"""You are an expert software engineer generating a minimal Python fix.

FILE: {target_file}
ORIGINAL CODE:
```python
{original_content}
```

TASK & ROOT CAUSE:
- Strategy: {plan.strategy}
- Root Cause: {plan.root_cause}
- Feedback from previous attempt (if any):
{feedback or "None. First attempt."}

CRITICAL RULES:
1. Make the SMALLEST possible modification. Do NOT rewrite unrelated functions.
2. DO NOT make up fake APIs or imports. Only use standard Python library or symbols already present in the file.
3. The 'search' string must match lines in the ORIGINAL CODE EXACTLY, including indentation.
4. Output STRICT JSON:
{{
  "search": "<exact original lines to replace>",
  "replace": "<new replacement lines>",
  "explanation": "<short explanation>"
}}
"""
            response = self.llm_client.generate(
                prompt=prompt,
                system_prompt="You are an expert Python patch engineer. Output JSON only with exact string matching.",
            )

            parsed = self._parse_patch_json(response.content)
            if "patches" in parsed and isinstance(parsed["patches"], list) and len(parsed["patches"]) > 0:
                p_item = parsed["patches"][0]
                search_str = p_item.get("search", "")
                replace_str = p_item.get("replace", "")
                explanation = p_item.get("explanation", "Targeted bug fix")
            else:
                search_str = parsed.get("search", "")
                replace_str = parsed.get("replace", "")
                explanation = parsed.get("explanation", "Targeted bug fix")

            patch_obj = GeneratedPatch(
                file_path=target_file,
                search_block=search_str,
                replace_block=replace_str,
                explanation=explanation,
            )

            # Apply patch to content
            if search_str and search_str in original_content:
                new_content = original_content.replace(search_str, replace_str, 1)
                patch_obj.diff_text = self._make_diff(original_content, new_content, target_file)
                if self._within_budget(patch_obj.diff_text):
                    sandbox.write_file(target_file, new_content)
                    patch_obj.success = True
                    self.log(f"Successfully applied patch to {target_file}: {explanation}")
                else:
                    patch_obj.error = "Minimal-change policy rejected patch size."
                    self.log(f"Rejected oversized patch for {target_file}")
            else:
                # Fuzzy fallback if exact whitespace was slightly off
                applied, new_content = self._fuzzy_replace(original_content, search_str, replace_str)
                if applied:
                    patch_obj.diff_text = self._make_diff(original_content, new_content, target_file)
                    patch_obj.diff_text = self._make_diff(original_content, new_content, target_file)
                    if self._within_budget(patch_obj.diff_text):
                        sandbox.write_file(target_file, new_content)
                        patch_obj.success = True
                    else:
                        patch_obj.error = "Minimal-change policy rejected patch size."
                    self.log(f"Fuzzy-matched and applied patch to {target_file}")
                else:
                    patch_obj.success = False
                    patch_obj.error = "Search block did not match file content exactly."
                    self.log(f"Failed to match search block in {target_file}")

            results.append(patch_obj)

        self.set_status(
            AgentStatus.COMPLETED if any(p.success for p in results) else AgentStatus.FAILED,
            f"Generated {len(results)} patch(es).",
        )
        return results

    def _within_budget(self, diff_text: str) -> bool:
        lines = diff_text.splitlines()
        added = sum(1 for line in lines if line.startswith("+") and not line.startswith("+++"))
        changed = sum(1 for line in lines if line.startswith(("+", "-")) and not line.startswith(("+++", "---")))
        return changed <= self.max_diff_lines and added <= self.max_added_lines

    def _make_diff(self, old_text: str, new_text: str, filename: str) -> str:
        diff_lines = difflib.unified_diff(
            old_text.splitlines(keepends=True),
            new_text.splitlines(keepends=True),
            fromfile=f"a/{filename}",
            tofile=f"b/{filename}",
        )
        return "".join(diff_lines)

    def _fuzzy_replace(self, content: str, search: str, replace: str) -> Tuple[bool, str]:
        if not search:
            return False, content
        search_clean = re.sub(r'\s+', ' ', search.strip())
        lines = content.splitlines()
        for i in range(len(lines)):
            for j in range(i + 1, min(len(lines) + 1, i + 15)):
                block = "\n".join(lines[i:j])
                if re.sub(r'\s+', ' ', block.strip()) == search_clean:
                    new_lines = lines[:i] + [replace] + lines[j:]
                    return True, "\n".join(new_lines)
        return False, content

    def _parse_patch_json(self, content: str) -> Dict:
        try:
            m = re.search(r'```json\s*(\{.*?\})\s*```', content, re.DOTALL)
            if m:
                return json.loads(m.group(1))
            m2 = re.search(r'(\{.*\})', content, re.DOTALL)
            if m2:
                return json.loads(m2.group(1))
            return json.loads(content)
        except Exception:
            return {}

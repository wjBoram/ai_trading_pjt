"""로컬 설치된 claude/codex CLI를 subprocess로 구동"""

import json
import shutil
import subprocess
from typing import Optional

import structlog

from core.exceptions import AgentError, AgentTimeoutError

logger = structlog.get_logger(__name__)


def check_cli_available() -> dict[str, bool]:
    """시작 시 두 CLI 설치 여부 확인"""
    return {
        "claude": shutil.which("claude") is not None,
        "codex": shutil.which("codex") is not None,
    }


def run_claude_cli(prompt: str, timeout_sec: int = 120) -> str:
    """로컬 claude CLI 실행 (claude --print 모드)

    claude CLI는 stdin으로 프롬프트를 받아 stdout으로 응답 출력.
    """
    try:
        result = subprocess.run(
            ["claude", "--print", "--output-format", "text"],
            input=prompt,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=timeout_sec,
        )
        if result.returncode != 0:
            logger.error("claude CLI 오류", returncode=result.returncode, stderr=result.stderr[:500])
            raise AgentError(f"claude CLI 실패: {result.stderr[:200]}")

        output = result.stdout.strip()
        logger.info("claude CLI 응답", length=len(output))
        return output

    except subprocess.TimeoutExpired as e:
        logger.error("claude CLI 타임아웃", timeout_sec=timeout_sec)
        raise AgentTimeoutError(f"claude CLI {timeout_sec}초 타임아웃") from e
    except FileNotFoundError as e:
        raise AgentError("claude CLI 미설치. npm install -g @anthropic-ai/claude-code 실행 필요") from e


def run_codex_cli(prompt: str, timeout_sec: int = 120) -> str:
    """로컬 codex CLI 실행 (OpenAI Codex CLI)

    codex CLI는 stdin으로 프롬프트를 받아 stdout으로 응답 출력.
    """
    try:
        result = subprocess.run(
            ["codex", "--quiet"],
            input=prompt,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=timeout_sec,
        )
        if result.returncode != 0:
            logger.error("codex CLI 오류", returncode=result.returncode, stderr=result.stderr[:500])
            raise AgentError(f"codex CLI 실패: {result.stderr[:200]}")

        output = result.stdout.strip()
        logger.info("codex CLI 응답", length=len(output))
        return output

    except subprocess.TimeoutExpired as e:
        logger.error("codex CLI 타임아웃", timeout_sec=timeout_sec)
        raise AgentTimeoutError(f"codex CLI {timeout_sec}초 타임아웃") from e
    except FileNotFoundError as e:
        raise AgentError("codex CLI 미설치. npm install -g @openai/codex 실행 필요") from e


def run_claude_api_fallback(prompt: str) -> str:
    """CLI 미설치 시 Anthropic SDK로 폴백"""
    from anthropic import Anthropic
    from config.settings import settings

    client = Anthropic(api_key=settings.anthropic_api_key)
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


def run_openai_api_fallback(prompt: str) -> str:
    """CLI 미설치 시 OpenAI SDK로 폴백"""
    from openai import OpenAI
    from config.settings import settings

    client = OpenAI(api_key=settings.openai_api_key)
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=2048,
    )
    return response.choices[0].message.content or ""


def run_agent(agent: str, prompt: str, timeout_sec: int = 120) -> str:
    """에이전트 실행 (CLI 우선, SDK 폴백)"""
    availability = check_cli_available()

    if agent == "claude":
        if availability["claude"]:
            return run_claude_cli(prompt, timeout_sec)
        else:
            logger.warning("claude CLI 미설치 - SDK 폴백 사용")
            return run_claude_api_fallback(prompt)
    elif agent == "codex":
        if availability["codex"]:
            return run_codex_cli(prompt, timeout_sec)
        else:
            logger.warning("codex CLI 미설치 - OpenAI SDK 폴백 사용")
            return run_openai_api_fallback(prompt)
    else:
        raise AgentError(f"알 수 없는 에이전트: {agent}")


def extract_json_from_response(response: str) -> Optional[dict]:
    """AI 응답에서 JSON 블록 추출"""
    import re

    # ```json ... ``` 블록 우선 탐색
    json_block = re.search(r"```json\s*([\s\S]+?)\s*```", response)
    if json_block:
        try:
            return json.loads(json_block.group(1))
        except json.JSONDecodeError:
            pass

    # 전체 응답이 JSON인 경우
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        pass

    # JSON 객체 패턴 탐색
    obj_match = re.search(r"\{[\s\S]+\}", response)
    if obj_match:
        try:
            return json.loads(obj_match.group(0))
        except json.JSONDecodeError:
            pass

    return None

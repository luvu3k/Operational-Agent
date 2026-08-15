"""
作用：
- 为每次求解创建独立运行目录，保存 `problem_spec`、生成的求解代码、执行日志和结果 JSON。
- 让用户能够拿到可复现的求解代码文件，而不仅是聊天中的文本片段。

调用关系：
- 被 `tools.exact_solver_tool` 调用，用于落盘生成的 `gurobipy` 代码并执行。
- 后续可被 `heuristic_solver_tool`、`code_repair_tool`、`memory` 和 `rag` 复用，用于记录历史运行经验。
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
from uuid import uuid4


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_ROOT = PROJECT_ROOT / "artifacts" / "runs"


@dataclass
class RunArtifact:
    run_id: str
    run_dir: Path
    problem_spec_path: Path
    code_path: Path
    result_path: Path
    stdout_path: Path
    stderr_path: Path
    route_graph_path: Path
    answer_path: Path

    def to_dict(self) -> Dict[str, str]:
        """转换为便于 tool 返回的字符串路径。"""
        return {
            "run_id": self.run_id,
            "run_dir": str(self.run_dir),
            "problem_spec_path": str(self.problem_spec_path),
            "code_path": str(self.code_path),
            "result_path": str(self.result_path),
            "stdout_path": str(self.stdout_path),
            "stderr_path": str(self.stderr_path),
            "route_graph_path": str(self.route_graph_path),
            "answer_path": str(self.answer_path),
        }


def _slugify(value: str) -> str:
    """把任意字符串转成可安全用于目录名的片段。"""
    slug = re.sub(r"[^0-9A-Za-z_]+", "-", str(value)).strip("-")
    return slug or ""


def create_run_artifact(task_name: str = "task", method: str = "solve") -> RunArtifact:
    """
    创建一次求解运行的目录与标准文件路径。

    目录命名规则：`{任务名}_{日期}_{求解方式}_{时刻}`，
    其中时刻用于保证同一天多次运行不冲突，前三段即用户要求的 `{任务名}_{data}_{求解方式}`。
    """
    date_str = datetime.now().strftime("%Y%m%d")
    time_str = datetime.now().strftime("%H%M%S")
    safe_task = _slugify(task_name) or "task"
    safe_method = _slugify(method) or "solve"
    run_id = f"{safe_task}_{date_str}_{safe_method}_{time_str}"
    run_dir = ARTIFACT_ROOT / run_id
    if run_dir.exists():
        run_id = f"{run_id}_{uuid4().hex[:4]}"
        run_dir = ARTIFACT_ROOT / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    return RunArtifact(
        run_id=run_id,
        run_dir=run_dir,
        problem_spec_path=run_dir / "problem_spec.json",
        code_path=run_dir / "generated_solver.py",
        result_path=run_dir / "result.json",
        stdout_path=run_dir / "stdout.txt",
        stderr_path=run_dir / "stderr.txt",
        route_graph_path=run_dir / "route_graph.svg",
        answer_path=run_dir / "answer.md",
    )


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    """写入 JSON 文件。"""
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def read_json(path: Path) -> Dict[str, Any]:
    """读取 JSON 文件，文件不存在或解析失败时返回错误结构。"""
    if not path.exists():
        return {"status": "error", "message": f"结果文件不存在: {path}"}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {"status": "error", "message": f"结果文件不是合法 JSON: {exc}"}


def write_text(path: Path, content: str) -> None:
    """写入文本文件。"""
    path.write_text(content, encoding="utf-8")


def run_python_file(code_path: Path, *, cwd: Optional[Path] = None, timeout: int = 120) -> Dict[str, Any]:
    """执行生成的 Python 求解代码，并保存 stdout/stderr。"""
    working_dir = cwd or code_path.parent
    process = subprocess.run(
        [sys.executable, str(code_path)],
        cwd=str(working_dir),
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    return {
        "returncode": process.returncode,
        "stdout": process.stdout,
        "stderr": process.stderr,
    }


def save_execution_logs(artifact: RunArtifact, execution: Dict[str, Any]) -> None:
    """保存一次代码执行的标准输出和错误输出。"""
    write_text(artifact.stdout_path, str(execution.get("stdout", "")))
    write_text(artifact.stderr_path, str(execution.get("stderr", "")))


if __name__ == "__main__":
    print("=== artifact_store.py 本地测试 ===")
    artifact = create_run_artifact("selftest", "exact")
    write_json(artifact.problem_spec_path, {"hello": "world"})
    write_text(artifact.code_path, "import json\njson.dump({'status': 'ok'}, open('result.json', 'w'))\n")
    execution_result = run_python_file(artifact.code_path, cwd=artifact.run_dir)
    save_execution_logs(artifact, execution_result)
    print(artifact.to_dict())
    print(read_json(artifact.result_path))

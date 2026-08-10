"""L4 计算层 —— 纯代码，零 LLM（铁律 1）。

本包内任何模块都不得 import 网络库、不得调用模型、不得读取时钟或随机数。
``engine.verify_scores`` 会双跑并断言结果完全一致 —— 违反上述任一条都会使它失败。
"""

from oic.scoring.engine import ScoreResult, compute_all_scores, verify_scores

__all__ = ["ScoreResult", "compute_all_scores", "verify_scores"]

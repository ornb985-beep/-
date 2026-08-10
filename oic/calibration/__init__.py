"""L5 校准层 —— 整个系统唯一有硬科学支撑的部分。

核心判据：系统有用 ⟺ RES > REL ⟺ BS < UNC。
未达标不得对外宣称有效。

参考基准（ForecastBench, Zou et al. arXiv:2409.19839）：
    超级预测者聚合  Brier = 0.096
    普通公众        Brier = 0.121
    最强 LLM        Brier = 0.122

最后一行的含义很重要：**LLM 单独做概率判断，天花板就是普通人水平。**
系统要超过它只能靠架构（强制基础率 + extremization 聚合 + 确定性公式接管），
不能靠换模型。
"""

from oic.calibration.brier import (
    BrierReport,
    brier_score,
    brier_skill_score,
    calibration_status,
    murphy_decomposition,
    root_brier_score,
)

__all__ = [
    "BrierReport",
    "brier_score",
    "brier_skill_score",
    "calibration_status",
    "murphy_decomposition",
    "root_brier_score",
]

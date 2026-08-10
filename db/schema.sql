-- OIC v4 数据契约
-- 目标库：PostgreSQL 15+（Supabase）。pgvector 与 RLS 部分标注为可选。
--
-- 设计要点：
--   1. 六张决策表（Opportunity/Evidence/Hypothesis/Experiment/Decision/Outcome）
--      是 v3 已定的核心，原样保留。
--   2. Outcome 是整个系统的命门。没有它，权重学习空转，
--      系统只学到用户偏好，学不到市场真相。今天不开始记，永远补不回来。
--   3. 预测存档（forecast）与 Outcome 分离：预测在前，结局在后，
--      靠 resolution_date 对账。绝不允许事后修改预测。
--   4. 审计日志 append-only —— 用触发器禁止 UPDATE/DELETE。

BEGIN;

CREATE EXTENSION IF NOT EXISTS pgcrypto;
-- CREATE EXTENSION IF NOT EXISTS vector;   -- 需要语义检索时开启

-- ===========================================================================
-- 0. 合规内核
-- ===========================================================================

-- 数据源登记表：未登记 / 未放行的源不得被采集层调用。
-- 应用层的 oic.compliance.provenance.Registry 是这张表的镜像。
CREATE TABLE source_registry (
    key                  text PRIMARY KEY,
    name                 text NOT NULL,
    access_method        text NOT NULL
        CHECK (access_method IN ('official_api','licensed','public_download',
                                 'user_provided','scraping')),
    tos_url              text NOT NULL DEFAULT '',
    legal_status         text NOT NULL DEFAULT 'not_assessed'
        CHECK (legal_status IN ('cleared','pending','rejected','not_assessed')),
    legal_note           text NOT NULL DEFAULT '',
    reviewed_on          date,
    handles_personal_info    boolean NOT NULL DEFAULT false,
    handles_sensitive_pi     boolean NOT NULL DEFAULT false,
    pipia_completed          boolean NOT NULL DEFAULT false,
    created_at           timestamptz NOT NULL DEFAULT now(),
    -- 爬取一律不放行；敏感 PI 未做 PIPIA 不放行。
    CONSTRAINT scraping_never_cleared
        CHECK (NOT (access_method = 'scraping' AND legal_status = 'cleared')),
    CONSTRAINT sensitive_pi_requires_pipia
        CHECK (NOT (handles_sensitive_pi AND legal_status = 'cleared'
                    AND NOT pipia_completed))
);

COMMENT ON CONSTRAINT scraping_never_cleared ON source_registry IS
    '2011-2022 的 12 起爬虫不正当竞争案，爬取方胜诉率 <16.67%。'
    '这条约束把"优先用官方 API"从文档承诺变成数据库不变式。';

-- ===========================================================================
-- 1. Opportunity —— 定义验证对象
-- ===========================================================================

CREATE TABLE opportunity (
    id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id         uuid NOT NULL,
    slug              text NOT NULL,
    title             text NOT NULL,
    track_key         text NOT NULL DEFAULT 'consumer_goods',
    category          text NOT NULL DEFAULT 'unknown',

    icp               text NOT NULL DEFAULT '',   -- 理想客户画像
    pain_point        text NOT NULL DEFAULT '',
    alternatives      text NOT NULL DEFAULT '',   -- 用户当前怎么解决
    wedge             text NOT NULL DEFAULT '',   -- 机会楔子
    market_note       text NOT NULL DEFAULT '',
    resource_note     text NOT NULL DEFAULT '',

    decision_state    text NOT NULL DEFAULT 'research'
        CHECK (decision_state IN ('research','validate','pilot','scale','hold','stop')),

    created_at        timestamptz NOT NULL DEFAULT now(),
    updated_at        timestamptz NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, slug)
);

CREATE INDEX opportunity_tenant_state_idx ON opportunity (tenant_id, decision_state);
CREATE INDEX opportunity_category_idx ON opportunity (category);

-- ===========================================================================
-- 2. Evidence —— 结论可追溯
-- ===========================================================================

CREATE TABLE evidence (
    id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    opportunity_id    uuid NOT NULL REFERENCES opportunity(id) ON DELETE CASCADE,
    source_key        text NOT NULL REFERENCES source_registry(key),

    entity            text NOT NULL,          -- 实体
    metric            text NOT NULL,          -- 指标
    fingerprint       text NOT NULL,          -- 实体×指标指纹：转载合并的键
    value_num         numeric,
    value_unit        text NOT NULL DEFAULT '',
    raw_text          text NOT NULL,

    -- Span-grounding：抽出的数字必须在原文字符级匹配，否则整条不入库
    span_start        integer,
    span_end          integer,
    grounded          boolean NOT NULL DEFAULT false,

    source_url        text NOT NULL DEFAULT '',
    snapshot_hash     text NOT NULL DEFAULT '',
    published_at      timestamptz,
    collected_at      timestamptz NOT NULL,
    region            text NOT NULL DEFAULT 'CN',
    source_grade      text NOT NULL CHECK (source_grade IN ('A','B','C')),

    stance            text NOT NULL DEFAULT 'supports'
        CHECK (stance IN ('supports','refutes','context')),
    supports_claim    text NOT NULL DEFAULT '',

    extractor_model   text NOT NULL DEFAULT '',   -- 抽取模型版本，用于漂移归因
    authorization     text NOT NULL DEFAULT '',

    created_at        timestamptz NOT NULL DEFAULT now(),

    -- 未通过 grounding 的数值证据不得入库
    CONSTRAINT numeric_evidence_must_be_grounded
        CHECK (value_num IS NULL OR grounded = true),
    CONSTRAINT span_well_formed
        CHECK (span_start IS NULL OR span_end IS NULL OR span_start < span_end)
);

CREATE INDEX evidence_opportunity_idx ON evidence (opportunity_id);
CREATE INDEX evidence_fingerprint_idx ON evidence (fingerprint);

COMMENT ON COLUMN evidence.fingerprint IS
    '转载十篇同一新闻仍只算一条证据 —— 按此指纹合并，防止"虚假的多源"。';

-- ===========================================================================
-- 3. Hypothesis —— 防自嗨
-- ===========================================================================

CREATE TABLE hypothesis (
    id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    opportunity_id    uuid NOT NULL REFERENCES opportunity(id) ON DELETE CASCADE,
    claim             text NOT NULL,
    falsifiable_when  text NOT NULL,          -- 什么观测会证伪它
    impact            text NOT NULL DEFAULT 'medium'
        CHECK (impact IN ('low','medium','high')),
    prior_probability numeric NOT NULL CHECK (prior_probability BETWEEN 0 AND 1),
    status            text NOT NULL DEFAULT 'open'
        CHECK (status IN ('open','supported','refuted','abandoned')),
    created_at        timestamptz NOT NULL DEFAULT now(),
    -- 不可证伪的假设不许入库
    CONSTRAINT must_be_falsifiable CHECK (length(trim(falsifiable_when)) > 0)
);

-- ===========================================================================
-- 4. Experiment —— 真实结果替代猜测
-- ===========================================================================

CREATE TABLE experiment (
    id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    opportunity_id    uuid NOT NULL REFERENCES opportunity(id) ON DELETE CASCADE,
    hypothesis_id     uuid REFERENCES hypothesis(id) ON DELETE SET NULL,

    action            text NOT NULL,          -- 最小验证动作
    cost_cap_rmb      numeric NOT NULL CHECK (cost_cap_rmb >= 0),
    success_criteria  text NOT NULL,
    stop_loss         text NOT NULL,          -- 止损线
    expected_info_gain numeric,               -- EVSI，用于排序先验证哪几个

    status            text NOT NULL DEFAULT 'designed'
        CHECK (status IN ('designed','approved','running','done','aborted')),
    approved_by       text,                   -- 花钱需人工批准
    started_at        timestamptz,
    finished_at       timestamptz,
    created_at        timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT stop_loss_required CHECK (length(trim(stop_loss)) > 0)
);

-- ===========================================================================
-- 5. Decision —— 行动结论
-- ===========================================================================

CREATE TABLE decision (
    id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    opportunity_id    uuid NOT NULL REFERENCES opportunity(id) ON DELETE CASCADE,
    verdict           text NOT NULL
        CHECK (verdict IN ('advance','observe','gather_evidence','pivot','stop')),
    rationale         text NOT NULL,
    decided_by        text NOT NULL,
    approval_status   text NOT NULL DEFAULT 'pending'
        CHECK (approval_status IN ('pending','approved','rejected')),
    rank_score        numeric,                -- 决策时刻的排序分，冻结留痕
    engine_version    integer NOT NULL,
    created_at        timestamptz NOT NULL DEFAULT now()
);

-- ===========================================================================
-- 6. Outcome —— 校准的唯一来源（系统命门）
-- ===========================================================================

CREATE TABLE outcome (
    id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    opportunity_id    uuid NOT NULL REFERENCES opportunity(id) ON DELETE CASCADE,

    label_definition  text NOT NULL,          -- 口径原文，防事后漂移
    succeeded         boolean,                -- NULL = 尚未解析，不做插补
    resolved_on       date,

    conversion_rate   numeric,
    revenue_rmb       numeric,
    retention_rate    numeric,
    cost_rmb          numeric,
    failure_reason    text NOT NULL DEFAULT '',

    -- 代理结局：快通道，只用于实验排序，不得写入校准
    is_surrogate      boolean NOT NULL DEFAULT false,

    created_at        timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT resolved_needs_date
        CHECK (succeeded IS NULL OR resolved_on IS NOT NULL)
);

CREATE INDEX outcome_opportunity_idx ON outcome (opportunity_id);
CREATE INDEX outcome_resolved_idx ON outcome (resolved_on) WHERE succeeded IS NOT NULL;

COMMENT ON TABLE outcome IS
    'Outcome 表是整个系统的命门。没有它，权重学习空转，'
    '系统只学到用户偏好，学不到市场真相。今天不开始记，永远补不回来。';
COMMENT ON COLUMN outcome.is_surrogate IS
    '代理结局（如 7 天留资率）只能用于实验排序。'
    '让它进校准 = 把系统训练成优化代理本身（Goodhart）。';

-- ===========================================================================
-- 7. 预测存档 —— 前瞻式记录，事后不可改
-- ===========================================================================

CREATE TABLE forecast (
    id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    opportunity_id    uuid NOT NULL REFERENCES opportunity(id) ON DELETE CASCADE,

    predicted_at      timestamptz NOT NULL DEFAULT now(),
    base_rate_value   numeric NOT NULL CHECK (base_rate_value BETWEEN 0 AND 1),
    base_rate_source  text NOT NULL,          -- 强制先给基础率再调整

    p10               numeric NOT NULL CHECK (p10 BETWEEN 0 AND 1),
    p50               numeric NOT NULL CHECK (p50 BETWEEN 0 AND 1),
    p90               numeric NOT NULL CHECK (p90 BETWEEN 0 AND 1),

    resolution_date   date NOT NULL,
    engine_version    integer NOT NULL,
    model_snapshot    text NOT NULL DEFAULT '',
    aggregation_note  text NOT NULL DEFAULT '',  -- logit pooling / extremize 参数
    disagreement      numeric,                   -- 多 agent 分歧度

    actual_outcome    boolean,                   -- 回填；NULL = 未解析
    resolved_at       timestamptz,

    CONSTRAINT quantiles_ordered CHECK (p10 <= p50 AND p50 <= p90),
    CONSTRAINT base_rate_source_required CHECK (length(trim(base_rate_source)) > 0)
);

CREATE INDEX forecast_resolution_idx ON forecast (resolution_date)
    WHERE actual_outcome IS NULL;

COMMENT ON CONSTRAINT base_rate_source_required ON forecast IS
    '标记 comparison class（基础率）的预测平均 Brier=0.17，次好标签 0.26。'
    '这是实证里最大的单点提升，因此设为非空约束而非建议。';

-- 预测一旦写入不得修改（只允许回填结局）
CREATE OR REPLACE FUNCTION forecast_immutable() RETURNS trigger AS $$
BEGIN
    IF NEW.predicted_at IS DISTINCT FROM OLD.predicted_at
       OR NEW.p10 IS DISTINCT FROM OLD.p10
       OR NEW.p50 IS DISTINCT FROM OLD.p50
       OR NEW.p90 IS DISTINCT FROM OLD.p90
       OR NEW.base_rate_value IS DISTINCT FROM OLD.base_rate_value
       OR NEW.resolution_date IS DISTINCT FROM OLD.resolution_date THEN
        RAISE EXCEPTION '预测存档不可修改 —— 事后改预测等于自欺，校准将失去意义';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER forecast_no_rewrite
    BEFORE UPDATE ON forecast
    FOR EACH ROW EXECUTE FUNCTION forecast_immutable();

-- ===========================================================================
-- 8. 组合与仓位（操盘层）
-- ===========================================================================

CREATE TABLE portfolio_position (
    id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id         uuid NOT NULL,
    opportunity_id    uuid NOT NULL REFERENCES opportunity(id) ON DELETE CASCADE,

    stage             text NOT NULL DEFAULT 'candidate'
        CHECK (stage IN ('candidate','testing','scaling','paused','exited')),
    allocated_rmb     numeric NOT NULL DEFAULT 0 CHECK (allocated_rmb >= 0),
    spent_rmb         numeric NOT NULL DEFAULT 0 CHECK (spent_rmb >= 0),
    stop_loss_rmb     numeric NOT NULL CHECK (stop_loss_rmb >= 0),

    kelly_fraction    numeric CHECK (kelly_fraction IS NULL
                                     OR kelly_fraction BETWEEN 0 AND 0.25),
    win_rate_lower    numeric CHECK (win_rate_lower IS NULL
                                     OR win_rate_lower BETWEEN 0 AND 1),
    sample_size       integer NOT NULL DEFAULT 0,

    opened_at         timestamptz NOT NULL DEFAULT now(),
    closed_at         timestamptz,

    UNIQUE (tenant_id, opportunity_id),
    CONSTRAINT spend_within_allocation CHECK (spent_rmb <= allocated_rmb)
);

COMMENT ON CONSTRAINT portfolio_position_kelly_fraction_check ON portfolio_position IS
    '硬上限 ¼ Kelly。Kelly 对胜率估计误差极度敏感 —— '
    '高估 2 倍胜率会导致长期资本归零，所以上限写进数据库而非只写在代码里。';

-- ===========================================================================
-- 9. 权重学习与影子权重
-- ===========================================================================

CREATE TABLE weight_correction (
    id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id         uuid NOT NULL,
    opportunity_id    uuid REFERENCES opportunity(id) ON DELETE SET NULL,

    user_action       text NOT NULL CHECK (user_action IN ('adopt','shelve','reject')),
    reason_text       text NOT NULL DEFAULT '',
    dimension         text CHECK (dimension IN ('c','o','d','e')),
    delta             numeric NOT NULL DEFAULT 0,

    weights_before    jsonb NOT NULL,
    weights_after     jsonb NOT NULL,

    -- 影子权重：先记录不生效，等真实 Outcome 验证方向正确后才写入正式权重
    is_shadow         boolean NOT NULL DEFAULT true,
    promoted_at       timestamptz,
    validated_by_outcome uuid REFERENCES outcome(id) ON DELETE SET NULL,
    discarded_reason  text NOT NULL DEFAULT '',

    created_at        timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT promotion_requires_outcome
        CHECK (promoted_at IS NULL OR validated_by_outcome IS NOT NULL)
);

COMMENT ON CONSTRAINT promotion_requires_outcome ON weight_correction IS
    '人一否决权重立刻改，但此时还没有真实 Outcome 验证这次否决是不是对的。'
    '不加这条约束，系统学到的只是当下偏见，不是市场真相。';

-- 被动信号回流：点击/收藏/深扫/忽略作为弱信号，解"参与度死穴"
CREATE TABLE passive_signal (
    id                bigserial PRIMARY KEY,
    tenant_id         uuid NOT NULL,
    opportunity_id    uuid NOT NULL REFERENCES opportunity(id) ON DELETE CASCADE,
    signal_type       text NOT NULL
        CHECK (signal_type IN ('view','click','save','deep_scan','ignore','share')),
    weight            numeric NOT NULL DEFAULT 0.1,
    occurred_at       timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX passive_signal_opportunity_idx ON passive_signal (opportunity_id, occurred_at);

-- ===========================================================================
-- 10. 审计日志 —— append-only
-- ===========================================================================

CREATE TABLE audit_log (
    id                bigserial PRIMARY KEY,
    tenant_id         uuid,
    actor             text NOT NULL,          -- 'system' | 用户 id | agent 名
    action            text NOT NULL,
    subject_table     text NOT NULL,
    subject_id        text NOT NULL,
    payload           jsonb NOT NULL DEFAULT '{}'::jsonb,
    engine_version    integer,
    occurred_at       timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX audit_log_subject_idx ON audit_log (subject_table, subject_id);

CREATE OR REPLACE FUNCTION audit_log_append_only() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION '审计日志只可追加，不可 % —— 可篡改的日志不是审计', TG_OP;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER audit_log_no_update
    BEFORE UPDATE OR DELETE ON audit_log
    FOR EACH ROW EXECUTE FUNCTION audit_log_append_only();

-- ===========================================================================
-- 11. 多租户隔离（Supabase RLS）
-- ===========================================================================
-- 在数据库层强制隔离，而不是靠应用层记得加 WHERE tenant_id = ...

ALTER TABLE opportunity        ENABLE ROW LEVEL SECURITY;
ALTER TABLE portfolio_position ENABLE ROW LEVEL SECURITY;
ALTER TABLE weight_correction  ENABLE ROW LEVEL SECURITY;
ALTER TABLE passive_signal     ENABLE ROW LEVEL SECURITY;

-- 示例策略：需按实际鉴权方案调整 current_setting 的键名
CREATE POLICY opportunity_tenant_isolation ON opportunity
    USING (tenant_id::text = current_setting('app.tenant_id', true));
CREATE POLICY portfolio_tenant_isolation ON portfolio_position
    USING (tenant_id::text = current_setting('app.tenant_id', true));
CREATE POLICY correction_tenant_isolation ON weight_correction
    USING (tenant_id::text = current_setting('app.tenant_id', true));
CREATE POLICY passive_tenant_isolation ON passive_signal
    USING (tenant_id::text = current_setting('app.tenant_id', true));

COMMIT;

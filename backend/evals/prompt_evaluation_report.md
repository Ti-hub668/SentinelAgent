# SentinelAgent Prompt Evaluation Report

## 1. Evaluation Objective

SentinelAgent 使用本地大语言模型对 Nuclei 等安全扫描器产生的 Findings 进行自动分析，并输出结构化的安全研判结果。

Prompt Evaluation 的主要目标不是单纯提高某一组测试数据上的准确率，而是验证模型能否在不同类型的安全发现中稳定区分以下四种 Verdict：

- `informational`
- `likely_true_positive`
- `likely_false_positive`
- `needs_review`

评测重点关注以下几个方面：

1. 模型输出是否符合预定义 JSON Schema；
2. Verdict 是否与人工标注结果一致；
3. 模型能否正确区分信息观察与实际安全问题；
4. 模型能否根据 Evidence 的充分程度调整 Verdict；
5. Prompt 修改后是否会在已有数据集上产生 Regression。

整个评测过程采用“Baseline → Error Analysis → Ablation Study → Prompt Refinement → Regression Test”的迭代方式进行。

---

## 2. Evaluation Datasets

SentinelAgent 当前使用四组数据进行 Prompt Evaluation。

| Dataset | Cases | Purpose |
|---|---:|---|
| Development | 8 | Prompt 开发与基础能力验证 |
| Holdout | 8 | 检查 Prompt 修改后的泛化表现 |
| Benchmark v1 | 16 | 覆盖四种 Verdict 的平衡安全评测集 |
| Real Findings v1 | 6 | 来源于 SentinelAgent 实际本地扫描结果的人工标注数据 |

其中 Benchmark v1 包含四类 Verdict，每类 4 个 Case，用于检查模型是否在不同判断类型之间产生明显偏移。

Real Findings v1 来源于 SentinelAgent 的实际扫描链路，包括 API 文档暴露、HTTP Security Headers、Prometheus Metrics 等 Finding，用于验证 Prompt 在真实扫描输出格式下的表现。

---

## 3. Verdict Definitions

### informational

Finding 主要属于资产信息、技术栈识别、接口信息或其他信息观察，本身不代表已经确认的安全问题。

### likely_true_positive

Evidence 能够较明确地支持 Finding 所描述的安全问题确实存在。

该判断关注“Finding 是否成立”，而不是风险等级高低，因此低风险安全配置问题在证据充分时同样可能属于 `likely_true_positive`。

### likely_false_positive

扫描器报告了安全问题，但现有 Evidence 与 Finding 不匹配，或者 Evidence 更支持正常行为、误匹配等解释。

### needs_review

Finding 存在合理的安全信号，但现有 Evidence 不足以可靠确认或否定该问题，需要进一步人工检查或补充证据。

Verdict 与 Severity / Risk Score 分别描述不同维度：

- Verdict：Evidence 对 Finding 的支持程度以及 Finding 的性质；
- Severity / Risk Score：安全问题成立后的风险程度。

---

## 4. Prompt v2 Baseline

Prompt v2 在原有 Prompt 基础上进一步明确了 Evidence-first 的判断原则，并要求模型根据 Finding 与 Evidence 的关系输出结构化 Verdict。

在 qwen3:8b 模型上的主要评测结果如下：

| Dataset | Correct | Accuracy | Schema Success Rate |
|---|---:|---:|---:|
| Development | 8 / 8 | 100.00% | 100.00% |
| Holdout | 7 / 8 | 87.50% | 100.00% |
| Benchmark v1 | 16 / 16 | 100.00% | 100.00% |
| Real Findings v1 | 6 / 6 | 100.00% | 100.00% |

Holdout 中唯一的错误为 `holdout_002`：

- Title: `Missing Content Security Policy Header`
- Expected Verdict: `likely_true_positive`
- Actual Verdict: `informational`
- Confidence: `0.95`

该 Case 的 Evidence 已明确说明 HTTP Response Headers 中不存在 `Content-Security-Policy`，但模型仍将其解释为信息类结果。

这一错误说明：模型虽然能够理解“CSP Header 缺失”这一事实，但可能没有正确区分“普通信息观察”和“已确认的安全配置缺陷”。

---

## 5. Prompt v3 Experiment

针对 `holdout_002`，Prompt v3 进一步强调：

- Verdict 与 Severity / Risk Score 属于不同判断维度；
- 低风险不代表 `informational`；
- 已确认的安全配置问题即使风险较低，也可能属于 `likely_true_positive`；
- 不应仅根据 Severity 或 Risk Score 推断 Verdict。

Prompt v3 的回归结果如下：

| Dataset | Correct | Accuracy |
|---|---:|---:|
| Development | 8 / 8 | 100.00% |
| Holdout | 7 / 8 | 87.50% |

其中 `holdout_002` 仍被判断为：

- Actual Verdict: `informational`
- Confidence: `0.95`

因此，仅加强“风险等级与 Verdict 分离”的 Prompt 约束，并没有修复该错误。

这一结果表明，最初关于模型受到 `low severity`、`low risk score` 等字段影响的解释仍需要进一步验证，不能直接将错误归因于 Risk-field Anchoring。

---

## 6. Error Analysis

针对 `holdout_002`，初步建立错误分类并分析可能原因。

原始输入中包含：

- `severity = low`
- `risk_score = 30`
- `risk_level = low`
- Finding 为 `Missing Content Security Policy Header`
- Evidence 明确确认 CSP Header 缺失

模型输出为 `informational`。

最初假设模型可能受到低风险字段影响，将“低风险”错误映射成了“信息类结果”。

为了验证这一假设，没有继续直接修改 Prompt，而是设计 Ablation Study，对辅助风险字段进行控制变量实验。

---

## 7. Ablation Study

### 7.1 Ablation #1: Neutralizing Risk Fields

第一组消融实验保持 Finding 的 Title、Description 和 Evidence 不变，仅中和辅助风险字段：

- `severity: low → unknown`
- `risk_score: 30 → 0`
- `risk_level: low → unknown`
- `risk_reason → N/A`

实验结果：

- Actual Verdict: `informational`
- Confidence: `0.95`

模型仍然将该 Finding 判断为 `informational`。

同时模型在解释中将该 Finding 描述为“信息识别类”和“技术栈特征”。

因此，该实验结果不支持“错误主要由低风险字段锚定导致”的简单解释。

相反，结果提示模型可能正确识别了 Evidence 中的事实，却错误理解了 Finding 本身的安全语义。

### 7.2 Ablation #2: Explicit Security Semantics

第二组实验继续保持风险字段中性，但将 Finding 明确描述为 Security Misconfiguration。

主要修改包括：

- Title 明确加入 `Security Misconfiguration`
- Description 明确说明其属于 Security Configuration Weakness
- Evidence 明确描述缺失的是 Security Header

实验结果：

- Actual Verdict: `likely_true_positive`
- Confidence: `0.95`

模型成功从 `informational` 转变为 `likely_true_positive`。

这一结果支持以下假设：

> `holdout_002` 的主要问题更可能是 Finding Semantic Classification，而不是简单的 Risk-field Anchoring。

因此，错误分类被进一步归纳为：

`finding_type_semantic_confusion`

即模型能够理解 Evidence 中“CSP Header 确实缺失”的事实，但没有正确识别该 Finding 属于安全配置缺陷，而将其错误归入普通信息观察。

需要注意的是，该结论来自有限 Case 的控制实验，因此应理解为实验结果对该假设提供支持，而不是证明了唯一因果关系。

---

## 8. Prompt v4: Semantic Classification

根据 Ablation Study 的结果，Prompt v4 不再继续强化 Severity / Risk Score 约束，而是在 Verdict 判断之前增加 Finding Semantic Classification。

Prompt v4 将 Finding 进一步区分为：

- Information Observation
- Security Misconfiguration
- Exposure
- Vulnerability
- Ambiguous Security Signal

其中重点明确：

- 已确认的技术栈、产品版本和资产信息通常属于 Information Observation；
- 已确认的安全配置缺陷不能仅因为风险较低而归为 informational；
- Security Misconfiguration 是否属于 likely_true_positive，仍然需要结合 Evidence 判断；
- finding_type 等扫描器字段不能直接决定最终 Verdict。

### 8.1 Regression Results

Prompt v4 的测试结果如下：

| Dataset | Correct | Accuracy | Avg. Latency | Avg. Confidence |
|---|---:|---:|---:|---:|
| Development | 8 / 8 | 100.00% | 36.70 s | 0.89 |
| Holdout | 8 / 8 | 100.00% | 31.81 s | 0.88 |
| Benchmark v1 | 16 / 16 | 100.00% | 41.43 s | 0.91 |
| Real Findings v1 | 5 / 6 | 83.33% | 50.09 s | 0.88 |

原先错误的 `holdout_002` 在 v4 中被正确判断为 `likely_true_positive`，说明 Semantic Classification 的调整解决了该已知 Failure Case。

但是，Real Findings v1 出现新的 Regression：

- Case ID: `real_002`
- Title: `HTTP Missing Security Headers`
- Expected Verdict: `needs_review`
- Actual Verdict: `informational`
- Confidence: `0.50`

模型生成的 Summary 已经指出：

> 扫描器检测到 HTTP 响应中缺少部分安全头，但证据未明确具体缺失的头信息。

Risk Explanation 同样指出，由于 Evidence 没有明确保存触发模板的具体安全头信息，因此无法确认是否存在实际安全配置问题。

这表明模型实际上识别到了 Evidence 不充分，但在 Evidence Sufficiency 到 Verdict 的映射阶段仍然发生错误。

因此，v4 虽然修复了 Finding Semantic Classification 问题，却暴露出新的 Evidence Sufficiency Mapping Error。

---

## 9. Prompt v5: Evidence Sufficiency Mapping

针对 v4 的 Regression，Prompt v5 进一步明确安全问题类 Finding 在 Evidence 不充分时的判断规则。

核心原则为：

1. Finding 本身只是信息观察：
   - `informational`

2. Finding 声称存在安全问题，且 Evidence 明确确认：
   - `likely_true_positive`

3. Finding 声称存在安全问题，但 Evidence 缺少确认该问题所必需的信息，同时也没有足够证据否定：
   - `needs_review`

4. Finding 声称存在安全问题，但 Evidence 明显与结论不符，或者更支持正常行为、误匹配等解释：
   - `likely_false_positive`

Prompt v5 特别强调：

> “无法确认安全问题”不等于“该 Finding 是 informational”。

对于 Security Misconfiguration，如果 Evidence 明确指出具体配置缺陷存在，可以判断为 `likely_true_positive`；如果扫描器声称存在配置缺陷，但 Evidence 没有明确指出具体缺失、错误或不安全的配置项，则应优先考虑 `needs_review`。

### 9.1 Final Regression Results

Prompt v5 在 qwen3:8b 上的最终回归结果如下：

| Dataset | Cases | Correct | Accuracy | Schema Success | Avg. Latency | Avg. Confidence |
|---|---:|---:|---:|---:|---:|---:|
| Development | 8 | 8 | 100.00% | 100.00% | 38.15 s | 0.89 |
| Holdout | 8 | 8 | 100.00% | 100.00% | 35.01 s | 0.89 |
| Real Findings v1 | 6 | 6 | 100.00% | 100.00% | 47.06 s | 0.90 |
| Benchmark v1 | 16 | 16 | 100.00% | 100.00% | 36.32 s | 0.90 |
| **Total** | **38** | **38** | **100.00%** | **100.00%** | — | — |

Prompt v5 同时正确处理了两个具有代表性的边界 Case：

### holdout_002

`Missing Content Security Policy Header`

Evidence 明确确认 CSP Header 缺失，因此：

`likely_true_positive`

### real_002

`HTTP Missing Security Headers`

扫描器报告存在安全头缺失，但当前 Evidence 没有明确指出具体缺失项，因此：

`needs_review`

这两个 Case 表明，最终 Prompt 不仅需要识别 Finding 的安全语义，还需要进一步判断 Evidence 是否足以支持该安全结论。

---

## 10. Prompt Evolution Summary

整个 Prompt 优化过程可以概括为：

`Prompt v2`
→ 发现 holdout_002 错误
→ `Prompt v3`
→ 错误仍然存在
→ Error Analysis
→ Ablation #1 排查 Risk-field Anchoring
→ Ablation #2 支持 Finding Semantic Confusion 假设
→ `Prompt v4`
→ 修复 holdout_002
→ Real Findings 出现 real_002 Regression
→ 定位 Evidence Sufficiency Mapping Error
→ `Prompt v5`
→ 完成最终 Regression Test

这一过程说明 Prompt Engineering 并不是单纯增加规则，而是一个持续进行错误分析、提出假设、实验验证和回归测试的迭代过程。

---

## 11. Limitations

虽然 Prompt v5 在当前四组内部评测数据上取得了 38 / 38 的最终回归结果，但这一结果存在以下限制：

1. 当前评测集规模仍然较小，共 38 个 Case；
2. Benchmark v1 属于人工设计的安全评测数据，不能完全代表真实网络环境中的 Finding 分布；
3. Real Findings v1 目前仅包含 6 个 Case，真实扫描数据的覆盖范围仍然有限；
4. 部分 Failure Case 已参与 Prompt Error Analysis 和后续 Prompt 调优，因此最终结果不能视为完全独立的泛化评测；
5. 当前主要使用 qwen3:8b 进行最终 Prompt 回归，模型更换后仍需要重新评测；
6. LLM 输出具有一定随机性，单次评测结果不能完全代表多次运行下的稳定性；
7. 当前评测主要关注 Verdict、Schema、Latency 和 Confidence，后续还可以进一步评估 Explanation Quality、Calibration 和跨模型稳定性。

因此，本报告中的 100% Accuracy 应理解为：

> Prompt v5 在当前 SentinelAgent 内部评测集上的最终回归结果。

该结果不代表模型在未知真实世界安全场景中具有 100% 的准确率。

---

## 12. Conclusion

SentinelAgent 建立了一套面向安全 Finding 分析的 Prompt Evaluation 流程，包括数据集构建、人工标签、Schema Validation、Prompt Versioning、Error Analysis、Ablation Study 和 Regression Test。

实验过程中，首先发现模型容易将已确认的低风险安全配置问题误判为 informational。通过消融实验进一步发现，该问题更可能与 Finding Semantic Classification 有关，而不是简单由 Severity 或 Risk Score 引起。

在引入 Semantic Classification 后，虽然原有 Holdout Failure Case 得到修复，但 Real Findings 中又出现 Evidence 不充分却被判断为 informational 的 Regression。随后通过进一步明确 Evidence Sufficiency 与 Verdict 的映射关系，形成 Prompt v5。

最终，Prompt v5 在当前 Development、Holdout、Benchmark v1 和 Real Findings v1 共 38 个内部评测 Case 上全部通过，同时保持 100% Schema Success Rate。

基于当前实验结果，Prompt v5 作为 SentinelAgent 当前阶段的默认 Prompt 版本。后续工作将重点转向安全知识库与 RAG，而不是继续针对现有评测集进行 Prompt 迭代，以降低对当前数据集过拟合的风险。
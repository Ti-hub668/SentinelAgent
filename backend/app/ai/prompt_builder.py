from app.schemas.ai_analysis import AIAnalysisInput


PROMPT_VERSION = "v5.1"


def build_risk_analysis_prompt(
    data: AIAnalysisInput,
    rag_context: str | None = None,
    structured_intelligence: str | None = None,
) -> str:

   structured_intelligence_section = ""

   if (
      structured_intelligence
      and structured_intelligence.strip()
   ):
      structured_intelligence_section = f"""
==================================================
四、结构化安全情报
==================================================

以下内容来自 SentinelAgent 对当前 Finding 中明确安全标识符
进行的结构化安全情报精确查询。

当前可能包含的情报来源包括：

- CISA KEV
- NVD

这些信息属于外部安全情报，
不属于当前目标的直接扫描证据。

你必须遵守以下规则：

1. 当前 Finding 的 Evidence 优先级高于结构化安全情报。

2. 只有当前 Finding 明确提供了对应 CVE 等标识符时，
   才能使用与该标识符精确匹配的安全情报。

3. CISA KEV 中 known_exploited=true 表示该 CVE
   已进入 Known Exploited Vulnerabilities Catalog。

   它说明该漏洞存在已知现实利用情况，
   但不代表当前目标已经遭到利用，
   也不能单独证明当前目标存在该漏洞。

4. NVD 中的 CVE 描述、CVSS、Severity、CWE、
   affected configuration 和 references
   描述的是该漏洞本身的公开安全信息。

   NVD 中存在某个 CVE 记录，
   不代表当前目标一定存在该漏洞。

5. NVD 中的 affected configuration
   表示该漏洞已知的适用或受影响配置范围。

   除非当前 Finding 的 Evidence 已经确认
   当前目标的产品、版本或其他必要条件与之匹配，
   否则不得假设当前目标属于该 affected configuration。

6. NVD CVSS 和 Severity 描述漏洞本身的严重程度，
   不表示当前 Finding 已经被证实，
   也不得直接替代 SentinelAgent 的 Rule-based Risk Score。

7. CISA KEV 未匹配或 NVD 本地记录未匹配，
   都不能作为该 Finding 为假的直接证据。

   “本地情报中没有匹配记录”
   不等于
   “漏洞不存在”或“扫描结果一定是误报”。

8. 是否将 Finding 判断为 likely_true_positive，
   仍然必须依据当前 Finding 的 Evidence
   是否足以支持该 Finding。

9. 如果 Evidence 已经支持该漏洞 Finding，
   NVD、CISA KEV 等情报可以进一步用于：

   - 理解漏洞机制
   - 补充漏洞严重程度背景
   - 判断现实利用背景
   - 辅助处置优先级
   - 提供修复建议

10. 不得根据结构化安全情报虚构当前目标的：

   - 产品
   - 版本
   - 配置
   - 攻击行为
   - 利用成功情况
   - 其他未提供的 Evidence

特别注意：

Structured Intelligence 描述的是
“这个漏洞是什么”。

Finding Evidence 描述的是
“当前目标上实际观察到了什么”。

不得用前者替代后者。

Structured Security Intelligence:

{structured_intelligence}
"""

   rag_section = ""

   if rag_context and rag_context.strip():
            rag_section = f"""
==================================================
五、检索到的安全知识
==================

以下内容来自 SentinelAgent 安全知识库的语义检索结果。

这些知识只能作为辅助分析上下文，不属于当前 Finding 的直接证据。

你必须遵守以下规则：

1. 当前 Finding 的 Evidence 优先级高于检索知识。

2. 不得因为知识库描述某类漏洞、配置缺陷或暴露通常存在，
   就推断当前目标一定存在该问题。

3. 检索知识用于帮助理解：
   - Finding 的安全语义
   - 常见安全配置
   - 暴露类型
   - 判断该类 Finding 通常需要什么证据

4. 如果检索知识与当前 Evidence 不一致，
   应优先依据当前 Finding 的实际 Evidence。

5. 检索结果中的 Similarity 只表示语义相似度，
   不代表 Finding 为真的概率，也不代表风险严重程度。

Retrieved Security Knowledge:

{rag_context}
"""

   return f"""
你是一名安全运营中心（SOC）的安全分析专家。

你的任务是根据扫描发现及已有证据，对该 Finding 进行安全研判。

你必须严格依据提供的信息进行判断。
不得虚构不存在的漏洞、CVE、攻击行为、利用结果或其他证据。

==================================================
一、Verdict 定义
==================================================

你只能从以下四种 verdict 中选择一个：

1. informational

表示该结果本身主要属于信息收集、技术识别、资产指纹、
版本信息或其他已经确认但不直接代表安全问题的信息。

典型情况：
- 技术栈识别
- Web Server 类型识别
- 普通版本信息
- 资产指纹信息

注意：
如果扫描器试图报告一个安全问题，但当前证据不足，
不要因为风险低就直接判断为 informational。


2. likely_true_positive

表示现有证据已经能够较明确地支持该 Finding 所描述的问题真实存在。

注意：

likely_true_positive 并不要求已经证明漏洞可以被成功利用。

判断的是：
“当前证据是否足以支持扫描器报告的发现本身？”

例如：
- 管理后台已经确认可以访问
- Debug 接口已经确认暴露并返回诊断信息
- 组件版本已经与漏洞检测规则明确匹配
- 敏感资源已经确认真实存在

如果 Finding 本身已经被证据直接支持，
不要仅仅因为没有进行漏洞利用就降级为 needs_review。


3. likely_false_positive

表示扫描器虽然报告了一个潜在安全问题，
但现有证据很弱、过于通用、与结论不匹配，
或者更可能由正常行为造成。

典型情况：
- 仅因为一个普通错误关键词就判断存在漏洞
- 通用错误页面被误识别为安全问题
- 检测规则命中，但证据明显无法支持扫描结果

注意：

likely_false_positive 与 informational 不同。

informational：
发现本身就是信息类结果。

likely_false_positive：
扫描器试图报告安全问题，
但证据无法有效支持该安全问题。


4. needs_review

表示存在合理的安全风险迹象，
但当前证据既不足以确认，也不足以否定，
因此需要人工进一步验证。

典型情况：
- URL 返回 HTTP 200，但不知道实际内容是什么
- 疑似备份文件存在，但没有确认文件内容
- 疑似敏感文件暴露，但没有足够响应内容证明
- 存在可疑行为，但缺少关键证据

==================================================
二、判断原则
======

请严格按照以下顺序进行判断。

第一步：先判断 Finding 的安全语义类别。

在判断 verdict 之前，必须先理解 Finding 本身描述的是什么，
不要仅根据标题中的单个关键词进行分类。

请在内部将 Finding 理解为以下类别之一：

A. Information Observation

Finding 本身只是描述资产、产品、技术、版本、
服务、证书元数据或其他环境信息，
并没有声称存在安全缺陷。

例如：

- 技术栈识别
- Web Server 类型识别
- 产品或框架识别
- 普通版本信息
- 资产指纹信息

这类 Finding 在证据确认后通常属于 informational。


B. Security Misconfiguration

Finding 声称某项安全配置缺失、错误、不安全或未按预期启用。

例如：

- 缺少安全响应头
- 不安全的 Cookie 安全属性
- 不安全的服务配置
- 目录浏览被启用
- 调试配置不当
- 其他已经被扫描器作为安全配置问题报告的状态

注意：

Security Misconfiguration 与 Information Observation 不同。

即使配置问题风险较低，
或者尚未证明攻击者可以立即利用，
也不能因此把它当成普通信息识别。

这类 Finding 的 verdict 应继续根据 Evidence
是否确认该配置问题真实存在来判断。


C. Exposure

Finding 声称某个接口、资源、管理页面、
调试信息、监控数据或敏感内容存在非预期暴露。

例如：

- 管理后台暴露
- Debug 接口暴露
- Metrics 暴露
- 敏感文件暴露
- 备份文件暴露

是否属于真实安全问题取决于 Evidence
是否能够确认资源性质及暴露状态。


D. Vulnerability

Finding 声称存在具体漏洞或可被安全检测规则识别的漏洞条件。

不得因为扫描器给出了 vulnerability 类型，
就自动判断 likely_true_positive。

仍然必须检查 Evidence 是否真正支持漏洞结论。


E. Ambiguous Security Signal

Finding 声称可能存在安全问题，
但从当前输入无法可靠确定问题性质，
或者 Evidence 与 Finding 之间仍存在明显解释空间。

这类情况继续检查 Evidence，
通常可能需要 needs_review。


完成上述语义判断后，再进行 Evidence 判断。

特别注意：

“已经确认某个事实”
并不自动意味着 informational。

必须先判断这个事实本身是：

普通信息，

还是

扫描器所报告的安全配置缺陷、暴露或漏洞条件。

例如：

确认服务器使用某种 Web 技术，
属于信息识别。

确认某项安全配置确实缺失，
属于对安全配置 Finding 的证据确认。

两者不能因为都属于“已经确认的事实”
而统一分类为 informational。

第二步：如果 Finding 声称存在安全问题，
判断 Evidence 是否直接支持“该问题确实存在”。

这里判断的是 Finding 的真实性，
不是判断该问题是否高危，
也不是判断攻击者是否已经成功利用。

必须严格区分：

Finding 是否真实
和
Finding 的风险是否严重。

如果 Evidence 已经直接确认 Finding 所描述的
安全状态、配置缺陷、暴露行为或其他安全问题确实存在，
应选择 likely_true_positive。

即使：

- severity 为 info 或 low
- risk_score 较低
- 尚未发生攻击
- 尚未证明可以进一步利用
- 尚未造成实际数据泄露

也不能仅凭这些原因将已经确认存在的安全问题
降级为 informational。

例如，对于“缺少某项安全配置”这一类 Finding：

如果 Evidence 已经明确证明该配置确实缺失，
那么 Finding 本身已经得到证据支持。

此时应根据 Finding 是否真实进行 verdict 判断，
而不是根据该配置缺失是否能够立即造成严重攻击
来决定 verdict。

第三步：检查确认 Finding 所需的关键证据是否缺失。
特别注意安全问题类 Finding 在 Evidence 不充分时的处理：

如果 Finding 本身声称的是安全配置缺陷、资源暴露、
漏洞或其他安全问题，则 Evidence 不足并不意味着
该 Finding 变成了信息类结果。

必须区分：

1. Finding 本身只是信息观察
   → informational

2. Finding 声称存在安全问题，并且 Evidence 已明确确认
   → likely_true_positive

3. Finding 声称存在安全问题，但 Evidence 缺少确认该问题
   所必需的具体信息，同时也没有足够证据否定该问题
   → needs_review

4. Finding 声称存在安全问题，但 Evidence 明显与结论不符，
   或更支持正常行为、误匹配等解释
   → likely_false_positive

因此：

“无法确认安全问题”
不等于
“该 Finding 是 informational”。

对于 Security Misconfiguration：

如果 Evidence 明确指出具体配置缺陷确实存在，
可以选择 likely_true_positive。

如果扫描器声称存在配置缺陷，
但 Evidence 没有明确指出具体缺失、错误或不安全的配置项，
应优先考虑 needs_review，而不是 informational。

只有 Finding 本身属于技术识别、资产指纹、
普通版本信息等 Information Observation 时，
才应因为其性质选择 informational。

如果存在合理的安全风险迹象，
但 Evidence 缺少确认该 Finding 所必需的信息，
选择 needs_review。

例如：

- 扫描器报告缺少安全配置，但 Evidence 没有明确指出具体缺失项
- URL 返回成功状态，但没有足够响应内容确认资源性质
- 响应发生异常变化，但无法确认具体漏洞
- 疑似敏感资源存在，但内容没有被验证

不要因为“可能存在风险”就直接选择 likely_true_positive。

第四步：判断 Evidence 是否实际上反驳了 Finding。

如果扫描器声称存在安全问题，
但 Evidence 与该结论明显不匹配，
或者已经显示命中来自正常页面、错误页面、
示例数据、重写规则等正常行为，
选择 likely_false_positive。

第五步：最终检查 verdict 与 severity 是否被混淆。

在输出 verdict 前再次确认：

- likely_true_positive 表示 Finding 被证据支持，
  不表示它一定是高危漏洞。

- informational 表示 Finding 本身属于信息类结果，
  不表示“风险较低”。

- needs_review 表示证据不足以确认或否定，
  不表示“风险中等”。

- likely_false_positive 表示现有证据更支持扫描器误报，
  不表示“风险很低”。

Verdict 反映证据对 Finding 的支持程度和 Finding 的性质。

Severity 和 Risk Score 反映问题的风险程度。

两者不得混为一谈。
==================================================
三、Confidence 规则
==================================================

confidence 必须在 0.0 到 1.0 之间。

请合理校准置信度：

0.90 - 1.00：
证据非常明确，判断边界清楚。

0.70 - 0.89：
判断较有把握，但仍有一定不确定性。

0.50 - 0.69：
证据有限，存在明显不确定性。

不要在证据不足时轻易给出 0.95 或更高的置信度。

{structured_intelligence_section}

{rag_section}

==================================================
六、当前 Finding
==================================================

以下内容是当前目标的实际 Finding 数据。

在最终选择 verdict 时，
必须优先依据这里的 Evidence，
不得让前面的外部安全情报替代当前目标的实际证据。

Finding ID:
{data.finding_id}

Source:
{data.source}

Finding Type:
{data.finding_type}

Title:
{data.title}

Severity:
{data.severity}

Target:
{data.target}

Description:
{data.description or "N/A"}

Evidence:
{data.evidence or "N/A"}

Remediation:
{data.remediation or "N/A"}

Rule-based Risk Score:
{data.risk_score}

Rule-based Risk Level:
{data.risk_level}

Rule-based Risk Reason:
{data.risk_reason or "N/A"}

==================================================
七、重要约束
======

severity 和 risk_score 只能作为辅助信息。

不要因为 severity 为 high 就自动判断 likely_true_positive。

不要因为 severity 为 info 或 low 就自动判断 informational。

最重要的判断依据是：

1. Finding 声称的是什么
2. Evidence 实际证明了什么
3. Evidence 是否足以支持 Finding

不得虚构：
- CVE 编号
- 漏洞利用过程
- 未提供的 HTTP 响应
- 未提供的版本
- 未提供的攻击证据

==================================================
八、输出要求
==================================================

只返回合法 JSON。

不要输出 Markdown。
不要输出代码块。
不要输出 JSON 之外的任何文字。

verdict 必须严格为以下值之一：

informational
likely_true_positive
likely_false_positive
needs_review

输出 JSON 必须包含以下五个字段：

- verdict
- confidence
- summary
- risk_explanation
- recommended_action

其中：

verdict 必须根据当前 Finding 的实际分析结果，
从前述四种合法值中选择。

confidence 必须根据当前证据充分程度进行评估，
不得使用固定默认值。

summary、risk_explanation 和 recommended_action
必须与最终 verdict 保持语义一致。

特别注意：

不得复制固定的 verdict 或 confidence 作为输出模板。

如果分析认为“证据不足，需要进一步验证”，
则 verdict 应与这一判断保持一致，
不得输出与分析理由相矛盾的 verdict。
""".strip()
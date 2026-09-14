# SentinelAgent Security Finding Annotation Guidelines

## 1. 标注目标

每条安全 Finding 需要人工标注一个 expected_verdict，
作为 LLM Evaluation 的 Ground Truth。

允许的标签共有四种：

- informational
- likely_true_positive
- likely_false_positive
- needs_review

标注时应优先依据 evidence，
其次参考 description、title、risk_reason 等信息。

severity 和 risk_score 只能作为辅助信息，
不能直接决定 verdict。


## 2. informational

定义：

当前 Finding 本身主要属于信息收集、资产识别、
技术指纹或普通元数据，不直接声称存在安全问题。

典型情况：

- Web 技术栈识别
- HTTP Server Banner
- TLS 证书基本信息
- 软件产品名称识别
- 操作系统指纹
- 服务版本信息收集

示例：

Title:
Wappalyzer Technology Detection

Evidence:
Detected web framework and server technology.

Verdict:
informational

注意：

“风险较低”不等于 informational。

如果扫描器明确声称发现了一个安全配置问题，
并且证据已经确认这个问题存在，
即使 severity=low，也应该考虑 likely_true_positive。


## 3. likely_true_positive

定义：

Finding 所声称的安全问题已经被现有证据直接支持。

不要求证明攻击者已经完成漏洞利用，
只要求证据能够支持“这个发现本身确实存在”。

典型情况：

- 缺少某个安全响应头，且响应头已经确认缺失
- 默认凭证成功登录
- Debug Endpoint 已确认可访问
- 敏感文件内容已经实际返回
- 管理后台确实暴露
- 组件版本与漏洞检测规则明确匹配

示例：

Title:
Missing Content Security Policy Header

Evidence:
Content-Security-Policy header was confirmed absent.

Verdict:
likely_true_positive

注意：

它可以同时是：

severity = low
verdict = likely_true_positive

因为：

真实性 != 严重程度


## 4. likely_false_positive

定义：

扫描器声称发现了一个安全问题，
但现有证据明显与该问题不匹配，
或者证据可以被正常、无害的行为解释。

典型情况：

- 请求 /.git 返回 HTTP 200，
  但实际只是网站统一 fallback 页面
- 扫描器匹配 password 关键词，
  但只是公开帮助文档中的普通文字
- 错误页面关键词触发漏洞规则，
  但不存在对应敏感信息
- 扫描规则匹配到了无害内容

示例：

Title:
Possible Git Repository Exposure

Evidence:
HTTP 200 returned, but response body was the generic
application fallback page and contained no Git metadata.

Verdict:
likely_false_positive

核心判断：

扫描器声称的问题
        ↓
与实际证据不匹配
        ↓
likely_false_positive


## 5. needs_review

定义：

Finding 所声称的安全问题具有一定可能性，
现有证据也提供了一些支持，
但仍不足以确认或者否定。

典型情况：

- 疑似 SQL 注入，只看到异常响应
- 疑似目录遍历，但没有读取到真实文件
- 疑似备份文件，但没有验证响应内容
- 疑似敏感文件，只得到 HTTP 200
- 疑似目录列表，只出现 "Index of"，没有实际列表内容

示例：

Title:
Possible SQL Injection Behavior

Evidence:
Modified request returned HTTP 500,
but no database error or additional confirmation exists.

Verdict:
needs_review


## 6. 标注决策顺序

对每条 Finding 按照以下顺序判断：

### Step 1

这个 Finding 本身是否只是信息收集或资产指纹？

是：
informational

否：
继续。


### Step 2

Evidence 是否直接支持 Finding 声称的问题确实存在？

是：
likely_true_positive

否：
继续。


### Step 3

Evidence 是否明显与 Finding 声称的问题不匹配，
或者能够被正常行为解释？

是：
likely_false_positive

否：
继续。


### Step 4

是否存在一些可疑迹象，
但证据仍不足以确认或否定？

是：
needs_review


## 7. 不允许的标注方法

不要仅依据 severity：

错误示例：

severity = info
→ informational

severity = high
→ likely_true_positive

这种判断方式是错误的。


不要仅依据 risk_score：

risk_score 高低描述的是风险程度，
不是 Finding 是否真实。


不要让待评测模型自动生成 Ground Truth。

expected_verdict 必须来自人工标注规则。


## 8. 核心原则

真实性和风险等级必须分开。

例如：

Finding:
缺少 CSP Header

真实性：
已确认缺失

风险等级：
Low

正确结果：

verdict = likely_true_positive
severity = low


再例如：

Finding:
疑似 Git Repository 暴露

Evidence:
返回 HTTP 200，
但内容实际上是普通 fallback 页面。

正确结果：

verdict = likely_false_positive
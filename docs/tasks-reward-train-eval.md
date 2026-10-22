# 任务集与奖励设计（150 条源文校核任务）

> **审核声明：** 本数据集是助手基于 `data/labor_subset.jsonl` 逐题设计并校对的，
> 执行了自动法条 / 哈希 / 日期一致性检查，也做了部分官方公开法源抽查；
> **没有经过独立律师或法学专家逐题人工签字核验**，
> `review.independent_human_legal_expert_review` 全为 `pending`。
> 训练实验可先行；发表研究或作为可靠法律基准前应做外部专家复核。

## 一、内容

| 文件 | 说明 |
| --- | --- |
| `data/tasks/tasks_all_reviewed.jsonl` | 完整 150 条 *assistant-reviewed* 数据，含 gold labels / 引用证据 / 审查状态 |
| `data/tasks/tasks_{train,dev,test}_labeled.jsonl` | 90/25/35 条含标签数据，**只供 reward 与评估器加载** |
| `data/tasks/tasks_{train,dev,test}_prompts_only.jsonl` | 模型可见的任务，**不含 gold / 任务类型 / 难度** |
| `data/tasks/audit_summary.json` | 数量、条文覆盖与已知限制 |
| `legalagent/data/build_tasks.py` | 150 条任务的构造定义（可复现构建） |
| `legalagent/data/validate_tasks.py` | 引用段落、哈希、日期、拆分隔离、标签泄漏的自动校验 |
| `legalagent/data/create_review_sheet.py` | 重新生成专家复核 CSV → `results/reviews/` |
| `docs/review_protocol.md` | 独立法律专家的复核清单 |

## 二、任务构成

| 任务类型 | 数量 |
| --- | ---: |
| `direct_retrieval`（直接法条检索） | 15 |
| `fact_application`（事实适用） | 20 |
| `multi_article`（多法条推理） | 10 |
| `insufficient_information`（不确定性识别） | 5 |

- 法域 CN；统一假设事实与法源适用日期为 `2024-06-01`；
- 覆盖 5 部法律 / 条例 / 司法解释，共 37 个不同法条 ID；
- `gold_article_ids` 是**参考的必要或关键依据集合，不是所有合法引用的穷尽列表**。
  额外引用应逐条查真、查时效、查支持关系，不能仅因不在 gold 中就直接判错。

## 三、构建与校验

```bash
# 在仓库根目录执行
python -m legalagent.data.build_tasks
python -m legalagent.data.validate_tasks
python -m legalagent.data.create_review_sheet
```

读入方式（标签绝不能进入 prompt）：

```python
import json


def read_jsonl(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(s) for s in f if s.strip()]


agent_prompts = read_jsonl("data/tasks/tasks_train_prompts_only.jsonl")
ground_truth = {t["task_id"]: t for t in read_jsonl("data/tasks/tasks_train_labeled.jsonl")}
```

> 训练脚本通过 `legalagent.paths.TASKS` 找文件；`--curriculum` 传入的课程文件
> 也只取其中的 prompt，标签仍从 `tasks_train_labeled.jsonl` 按 `task_id` 回连。

## 四、Reward 实现

`legalagent/reward.py` 把每题拆成六个可复核的分量，全部由数据字段决定，。

| 分量 | 权重 | 依据 | 说明 |
| --- | ---: | --- | --- |
| `tool_use` | 0.10 | rollout 轨迹 | 是否真的调用了工具且 `ok=True`（过程分，只作冷启动信号） |
| `grounding` | 0.10 | 工具返回的 article_id | 引用必须落在工具输出内 |
| `gold` | 0.35 | `gold_article_ids` | **F1(recall, precision)**；额外但有据的引用只拉低 precision，不清零 |
| `answer_points` | 0.35 | `expected_answer_points` | 按「；」拆子句，字符 2-gram 覆盖度连续给分（`min(1, cov/0.6)`），避免断崖 |
| `insufficiency` | 0.10 | `missing_facts` + 兜底措辞 | 仅对 `insufficient_information` 生效：`0.6×缺失事实覆盖 + 0.4×是否明说无法判断` |
| 幻觉惩罚 | −0.15/个，上限 −0.45 | 对照工具输出 | 引用了工具从未返回的 ID |
| 过度引用 | 超出 3 条有据但非 gold 的引用，每条 −0.03，上限 −0.15 | 对照 gold | 防「把工具返回的 ID 全抄一遍」 |
| 零引用 | 非「信息不足」题完全没有引用：−0.20 | 引用解析 | 任务明确要求给条文 ID，不给就是没完成 |

总分 = 适用分量的加权平均（不适用分量剔除后重新归一）− 各惩罚，裁剪到 `[-0.5, 1.0]`。

引用解析同时支持 `labor_contract_law:39` 和《劳动合同法》第三十九条两种写法，
并优先匹配最长别名（实施条例不会被误判成劳动合同法）；正文比较前去掉标点与空白，
只保留汉字 / 字母 / 数字的 2-gram。

**这套惩罚的设计目标**是让「堆引用」不划算：把工具返回的 ID 全部抄进答案、正文只写一句
「收取押金违法」，F1 与过度引用惩罚会同时压分，最终低于「引对且改写表述」的答案。
量化效果取决于你的数据与题目，建议用 `python -m legalagent.reward` 的三个合成样例先建立手感。

```powershell
python -m legalagent.reward                                    # 三个合成样例，纯 CPU
python -m unittest discover -s tests -t . -p "test_reward.py"  # 15 条单测
```

### 已知局限

- `answer_points` 是字面重合度，改写幅度大时会低估；目前靠连续给分缓解，
  但**可能奖励关键词堆砌**，v2 应加长度 / 冗余惩罚或改用离线 LLM 判官校准；
- `insufficiency` 只有 15 道题（test 里 2 道），权重小、方差大，别据此下结论；
- 同一模型 + 同一 split + 同一配置才能横比，`score_*.json` 里已固化这些字段。



## 五、Agentic GRPO（多轮工具调用）

`train_grpo_agentic.py` 把训练目标换成真实的多轮：模型自己调
`search_compact` / `get_compact`，不再预注入候选。关键实现点：

1. **工具返回必须精简**：完整 payload 会被 TRL 判定超预算并整体回滚，
   模型看不到结果、reward 只看到悬空的 tool_call；精简版只回 ID + 条号 + 80 字摘要；
2. **工具结果用 JSON 字符串返回**：TRL 用 Python `repr` 序列化 dict（单引号），不是合法 JSON；
3. **必须 `enable_thinking=False`**：否则 1.7B 把预算全花在思考上，答案为空；
4. **reward 从 TRL 的消息轨迹里取**：tool 消息 → article_id，最后一条 assistant → 答案。


## 六、记录你自己的实验

仓库不发布作者的历史运行。建议每次跑完把这三样写进 `runs/<name>/`：

| 文件 | 来源 |
| --- | --- |
| `config.json` | 训练脚本自动写（`GRPOConfig.to_dict()`） |
| `reward_stats.json` | 训练脚本自动写（每条样本的分量明细） |
| `results/eval_*.json` | 评测脚本写出，含 `summary.component_means` |

对比时只认「同初始 checkpoint、同数据、同步数、同采样参数」的一组；
GRPO 是采样训练，换一次随机种子就是另一组权重。


## 七、免责

这里的 `expected_answer_points` 旨在对可验证的法律原则评分，不能作为面向具体客户的律师意见。
现实案件必须考虑适用时期、事实、地方规范、司法实践与最新修法。

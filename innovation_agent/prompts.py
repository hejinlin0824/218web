import textwrap
from datetime import datetime
from typing import Dict, Optional

class PromptManager:
    """
    提示词管理器 v3.1 (Draft Protocol Edition)
    核心特性：引入 <DRAFT> 标签协议，分离“对话思考”与“文档生成”。
    """

    # =============================================================================
    # 0. System Context (核心宪法)
    # =============================================================================
    CORE_SYSTEM_CONTEXT = textwrap.dedent("""
        <role_definition>
        你是一位计算机科学（联邦学习/分布式优化）领域的**顶尖科研合作者 (Co-author / PI)**。
        
        **你的核心特质：**
        1. **建设性 (Constructive)**：帮助用户把“模糊的直觉”转化为“严谨的数学论文”。如果想法不成熟，你要修补它、完善它。
        2. **数学直觉 (Math Intuition)**：用户可能只说“我想用动量”，你要立刻写出 $v_{t+1} = \beta v_t + (1-\beta) g_t$ 并解释其在当前 FL 场景下的具体形态。
        3. **系统性 (Systematic)**：时刻关注 Innovation 1, 2, 3 之间的联系。
        </role_definition>

        <output_rules>
        1. **Language**: 全程使用**中文**与用户交流。
        2. **Format**: 关键数学公式必须使用 LaTeX 格式（如 $\mathcal{L}(\\theta)$）。
        </output_rules>

        <interaction_protocol> (CRITICAL)
        你有两种输出模式，请根据用户意图切换：
        
        **模式 A：对话讨论 (Chat Mode)**
        - 当用户还在构思、询问建议、或者你的想法需要修改时。
        - 直接输出文本，**不要**包含 Markdown 的大标题或长篇大论的文档结构。
        - 仅在聊天框与用户交互。

        **模式 B：正式起草 (Draft Mode)**
        - 当用户明确表示“确认”、“生成文档”、“写下来”，或者你认为当前方案已经成熟可以形成文档时。
        - **必须**将正式的 Markdown 文档内容包裹在 `<DRAFT>` 和 `</DRAFT>` 标签中。
        - 格式示例：
          好的，根据讨论，这是定稿方案：
          <DRAFT>
          # 创新点标题
          ## 数学推导
          ...
          </DRAFT>
        - 只有包裹在标签里的内容会被写入右侧的文档工作台。
        </interaction_protocol>
    """).strip()

    # =============================================================================
    # 辅助函数
    # =============================================================================
    @staticmethod
    def _get_today() -> str:
        return datetime.now().strftime("%Y-%m-%d")

    @staticmethod
    def _sanitize(text: str) -> str:
        if not text: return "（暂无内容）"
        # 防止 Python format 报错，转义大括号
        return text.replace("{", "{{").replace("}", "}}")

    @staticmethod
    def _get_system_context() -> str:
        return PromptManager.CORE_SYSTEM_CONTEXT

    # =============================================================================
    # 1. Phase 1: Baseline 总结 (直接生成)
    # =============================================================================
    @staticmethod
    def get_baseline_prompt(text_content: str) -> str:
        sys_ctx = PromptManager._get_system_context()
        safe_text = PromptManager._sanitize(text_content[:50000])

        mission_prompt = textwrap.dedent(f"""
            <current_mission>
            用户上传了一篇 Baseline 论文。请你作为合伙人，总结它并**敏锐地发现它留下的坑（Research Gaps）**。
            这是一次性生成任务，请直接输出详细的 Markdown 文档，无需使用 DRAFT 标签。
            </current_mission>

            <raw_content_excerpt>
            {safe_text}
            ...
            </raw_content_excerpt>

            <output_requirement>
            请生成一份 `base.md`，包含：
            1. **核心痛点 (Problem Statement)**：用数学语言定义它解决了什么（如 $\\min F(w)$）。
            2. **算法骨架 (Algorithm Skeleton)**：用伪代码或公式描述它的核心步骤。
            3. **潜在缺陷 (Critical Gaps)**：**这是最重要的一步**。请列出 3 个它没解决好的问题（例如：是否忽略了 Non-IID？通信效率是否太低？隐私保护是否不够？）。这将是我们后续创新的直接靶子。
            </output_requirement>
        """).strip()

        return f"{sys_ctx}\n\n{mission_prompt}"

    # =============================================================================
    # 2. Phase 2: 创新点挖掘 (支持 DRAFT 协议)
    # =============================================================================
    @staticmethod
    def get_innovation_prompt(stage_num: int, base_content: str, prev_innovations: str, user_idea: str) -> str:
        sys_ctx = PromptManager._get_system_context()
        
        base_summary = PromptManager._sanitize(base_content)
        prev_innovs = PromptManager._sanitize(prev_innovations)
        idea = PromptManager._sanitize(user_idea)

        # 智能判断模式
        is_brainstorm_mode = len(user_idea) < 10 or "推荐" in user_idea or "不知道" in user_idea

        brainstorm_instruction = ""
        if is_brainstorm_mode:
            brainstorm_instruction = """
            **用户意图分析：** 用户似乎没有具体思路，或者请求建议。
            **行动：** 请进入 **对话讨论模式**。基于 Baseline 的 Gaps，主动提出 2-3 个具体的数学创新方向供用户选择。**不要生成 DRAFT**。
            """
        else:
            brainstorm_instruction = """
            **用户意图分析：** 用户提出了初步想法。
            **行动：** 1. 首先评估想法。如果想法太简单或有误，请在 **对话讨论模式** 指出并建议修改。
            2. 如果想法可行，或者用户明确要求生成/确认，请进入 **正式起草模式**，将完善后的数学推导包裹在 `<DRAFT>` 标签中输出。
            """

        mission_prompt = textwrap.dedent(f"""
            <project_status>
            当前正在构思：创新点 #{stage_num}
            </project_status>

            <context>
            **Baseline 分析:**
            {base_summary}

            **已定稿的前序创新:**
            {prev_innovs}
            </context>

            <user_input>
            "{idea}"
            </user_input>

            <instruction>
            {brainstorm_instruction}
            
            **如果进入 Draft Mode，DRAFT 内部结构要求:**
            <DRAFT>
            # 创新点 #{stage_num} 方案详情
            ## 1. 核心洞察 (Insight)
            ## 2. 数学建模 (Mathematical Formulation)
            *(修正后的目标函数与更新规则)*
            ## 3. 理论支撑 (Why it works)
            ## 4. 与系统的融合
            </DRAFT>
            </instruction>
        """).strip()

        return f"{sys_ctx}\n\n{mission_prompt}"

    # =============================================================================
    # 3. Phase 3: 实验设计 (直接 DRAFT)
    # =============================================================================
    @staticmethod
    def get_experiment_prompt(base_content: str, innov1: str, innov2: str, innov3: str) -> str:
        sys_ctx = PromptManager._get_system_context()
        
        full_context = f"Base:\n{base_content}\n\nInnov1:\n{innov1}\n\nInnov2:\n{innov2}\n\nInnov3:\n{innov3}"
        safe_context = PromptManager._sanitize(full_context)

        mission_prompt = textwrap.dedent(f"""
            <mission>
            我们的三个创新点已经由你（AI合伙人）协助用户完善定稿。
            现在，请设计一份能够验证这套组合拳（Framework）有效性的实验方案。
            这是一个生成任务，请直接输出包含 `<DRAFT>` 标签的内容。
            </mission>

            <context>
            {safe_context}
            </context>

            <requirements>
            1. **Datasets**: 推荐使用 FEMNIST, CIFAR-10, 以及一个 NLP 数据集。
            2. **Non-IID**: 必须包含 Dirichlet $\\alpha=0.1$ (Extreme) 和 $\\alpha=0.5$ (Moderate)。
            3. **Baselines**: 根据我们的创新点类型，挑选 5 个最强劲的对手（如 FedAvg, FedProx, SCAFFOLD, Moon, FedDyn）。
            4. **Ablation**: 必须设计实验证明 Innov 1, 2, 3 是缺一不可的（Synergy）。
            </requirements>

            <output_format>
            请输出：
            简短的开场白（如“好的，这是为你设计的实验方案...”）
            <DRAFT>
            # 实验设置 (Experimental Setup)
            ... (Markdown 表格和配置)
            </DRAFT>
            </output_format>
        """).strip()

        return f"{sys_ctx}\n\n{mission_prompt}"
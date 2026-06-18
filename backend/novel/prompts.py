"""博学式 Prompt 模板 — 一次生成，上下文丰富"""

import json


def build_chapter_prompt(book, characters, outline, memories, recent_chapters, prev_ending="", style_example="", template_author=""):
    """构建写章节的 system + user message。去掉结构化标题，改用自然段落。"""

    parts = ["你是一位优秀的长篇网络小说作家。直接写出完整的章节内容。注意直接开始写正文，不要输出任何额外说明。"]

    # 字数约束
    writing_config = book.get("writing_config", {})

    # 风格参考（来自写手配置）
    if style_example:
        parts.append("")
        parts.append("参考这样的写法：")
        parts.append(style_example)
    if template_author:
        parts.append("")
        parts.append(f"文风可以参考{template_author}的感觉来写。")

    if isinstance(writing_config, str):
        try:
            writing_config = json.loads(writing_config)
        except (json.JSONDecodeError, TypeError):
            writing_config = {}
    min_words = writing_config.get("min_words", 2000)
    max_words = writing_config.get("max_words", 4000)
    parts.append(f"单章字数控制在 {min_words}-{max_words} 字之间。")

    # 创作意图
    if book.get("author_intent"):
        parts.append("")
        parts.append(f"这部小说的创作意图是：{book['author_intent']}")

    # 故事简介
    if book.get("brief"):
        parts.append("")
        parts.append(book["brief"])

    # 世界观
    if book.get("world_building"):
        parts.append("")
        parts.append(book["world_building"])

    # 角色
    if characters:
        char_texts = []
        for ch in characters:
            desc_parts = []
            name = ch.get("name", "")
            desc = ch.get("description", "")
            bg = ch.get("background", "")
            traits = ch.get("traits", [])
            appearance = ch.get("appearance", "")
            rels = ch.get("relationships", [])

            desc_parts.append(f"{name}")
            if desc:
                desc_parts.append(f"，{desc}")
            if bg:
                desc_parts.append(f"。{bg}")
            if traits:
                desc_parts.append(f"。性格{'、'.join(traits[:3])}")
            if appearance:
                desc_parts.append(f"。{appearance}")
            if rels:
                rel_texts = []
                for r in rels:
                    if isinstance(r, dict):
                        rel_texts.append(f"{r.get('relation','')}（{r.get('target','')}）")
                if rel_texts:
                    desc_parts.append(f"。和{'、'.join(rel_texts)}")
            char_texts.append("".join(desc_parts))
        parts.append("")
        parts.append("故事中有这些人物：")
        for t in char_texts:
            parts.append(t)

    # 写作规则
    writing_rules = writing_config.get("writing_rules", "")
    if writing_rules:
        parts.append("")
        parts.append("写的时候注意：")
        for line in writing_rules.strip().split("\n"):
            line = line.strip()
            if line:
                parts.append(f"· {line}")

    # 禁用词
    prohibited = writing_config.get("prohibited_words", "")
    if prohibited:
        parts.append("")
        parts.append(f"注意避免这些词汇：{prohibited}")

    # 行为锁
    behavior_locks = writing_config.get("behavior_locks", "")
    if behavior_locks:
        parts.append("")
        parts.append("角色的行为约束：")
        for line in behavior_locks.strip().split("\n"):
            line = line.strip()
            if line:
                parts.append(f"· {line}")

    # 高级设置
    advanced = writing_config.get("advanced", {})
    if advanced:
        advs = []
        if advanced.get("natural_dialogue"):
            advs.append("对话要口语化自然，每人口吻有差异，带个人毛边")
        if advanced.get("no_useless_details"):
            advs.append("所有环境描写必须服务情节，不要无用的装饰性细节")
        max_env = advanced.get("max_env_sentences", 0)
        if max_env:
            advs.append(f"连续环境描写不超过{max_env}句")
        max_inner = advanced.get("max_inner_sentences", 0)
        if max_inner:
            advs.append(f"每页内心戏不超过{max_inner}句")
        if advs:
            parts.append("")
            parts.append("写作控制：")
            for p in advs:
                parts.append(f"· {p}")

    # 故事记忆（自然叙述）
    if memories:
        mem_texts = [f"第{m['chapter_number']}章的时候，{m['fact']}" for m in memories]
        parts.append("")
        parts.append("到目前为止，故事已经发展到了这些情节：")
        for mt in mem_texts:
            parts.append(mt)

    # 最近章节摘要
    if recent_chapters:
        parts.append("")
        parts.append("之前几章的故事回顾：")
        for ch in recent_chapters:
            parts.append(f"· 第{ch['chapter_number']}章《{ch['title']}》：{ch['summary']}")

    # 上一章结尾
    if prev_ending:
        parts.append("")
        parts.append("上一章结尾的内容是这样的——你必须从这里接着往下写，不能重复、不能跳过：")
        parts.append(prev_ending)
        parts.append("")
        parts.append("注意：上一章结尾的剧情、对话、场景要直接衔接过来，不要重新开启一个新场景，不要重复上一章已经说过的事。")

    system_prompt = "\n".join(parts)

    # User message
    user_parts = []
    if outline:
        user_parts.append(f"下面要写的是第{outline['chapter_number']}章。")
        if outline.get("title"):
            user_parts.append(f"章节标题：{outline['title']}")
        if outline.get("outline_content"):
            user_parts.append(f"这章的大致情节是：{outline['outline_content']}")
        if outline.get("word_target"):
            user_parts.append(f"目标写{outline['word_target']}字左右。")
        if outline.get("conflict"):
            user_parts.append(f"核心矛盾是{outline['conflict']}")
        if outline.get("excitement"):
            user_parts.append(f"爽点在{outline['excitement']}")
        if outline.get("hook"):
            user_parts.append(f"章末的悬念是{outline['hook']}")
        if outline.get("storyline"):
            user_parts.append(f"推进的故事线是{outline['storyline']}")
        if outline.get("foreshadowing"):
            user_parts.append(f"埋下的伏笔是{outline['foreshadowing']}")
        if outline.get("foreshadowing_payoff"):
            user_parts.append(f"回收的伏笔是{outline['foreshadowing_payoff']}")
    else:
        user_parts.append("请根据已有故事上下文，继续写出下一章内容。")

    user_parts.append("")
    user_parts.append("现在，直接写出本章正文。")

    user_prompt = "\n".join(user_parts)

    return system_prompt, user_prompt

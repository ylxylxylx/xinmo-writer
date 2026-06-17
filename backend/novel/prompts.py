"""博学式 Prompt 模板 — 一次生成，上下文丰富"""

import json


def build_chapter_prompt(book, characters, outline, memories, recent_chapters, prev_ending=""):
    """构建写章节的 system + user message。使用 writing_config 替代 injections + qc_rules。"""

    system_parts = ["你是一位优秀的长篇网络小说作家。你的任务是根据以下设定和细纲，直接写出完整的章节内容。"]
    system_parts.append("")
    system_parts.append("## 写作要求")
    system_parts.append("- 直接开始写正文，不要输出任何额外说明、不要输出章节标题以外的格式。")
    system_parts.append("- 必须是流畅的中文小说正文，注重细节、对话、心理描写和场景刻画。")
    system_parts.append("- 保持人物性格一致性，遵守故事世界观设定。")
    system_parts.append("- 严格按照细纲中的矛盾、爽点、钩子、故事线、伏笔信息来写，不要遗漏。")

    # 写作风格配置（由调用方注入已合并的配置到 book["writing_config"]）
    writing_config = book.get("writing_config", {})
    if isinstance(writing_config, str):
        try:
            writing_config = json.loads(writing_config)
        except (json.JSONDecodeError, TypeError):
            writing_config = {}

    # 字数约束
    min_words = writing_config.get("min_words", 2000)
    max_words = writing_config.get("max_words", 4000)
    system_parts.append(f"- 单章字数控制在 {min_words}-{max_words} 字之间。")

    if book.get("author_intent"):
        system_parts.append("")
        system_parts.append(f"## 作者创作意图")
        system_parts.append(book["author_intent"])

    if book.get("brief"):
        system_parts.append("")
        system_parts.append(f"## 故事简介")
        system_parts.append(book["brief"])

    # 世界观设定
    if book.get("world_building"):
        system_parts.append("")
        system_parts.append("## 世界观设定")
        system_parts.append(book["world_building"])

    # 角色
    if characters:
        system_parts.append("")
        system_parts.append("## 角色设定")
        for ch in characters:
            parts = [f"### {ch['name']}"]
            if ch.get("description"):
                parts.append(f"简介：{ch['description']}")
            if ch.get("background"):
                parts.append(f"背景：{ch['background']}")
            if ch.get("traits"):
                parts.append(f"性格特点：{'、'.join(ch['traits'])}")
            if ch.get("appearance"):
                parts.append(f"外貌：{ch['appearance']}")
            if ch.get("relationships"):
                rels = [f"{r.get('relation','')}（{r.get('target','')}）" for r in ch["relationships"] if isinstance(r, dict)]
                if rels:
                    parts.append(f"关系：{'；'.join(rels)}")
            system_parts.append("\n".join(parts))

    # 写作规则
    writing_rules = writing_config.get("writing_rules", "")
    if writing_rules:
        system_parts.append("")
        system_parts.append("## 写作规则（必须遵守）")
        for line in writing_rules.strip().split("\n"):
            line = line.strip()
            if line:
                system_parts.append(f"- {line}")

    # 禁用词
    prohibited = writing_config.get("prohibited_words", "")
    if prohibited:
        system_parts.append("")
        system_parts.append("## 禁用词（正文不得出现以下词汇）")
        system_parts.append(prohibited)

    # 行为锁
    behavior_locks = writing_config.get("behavior_locks", "")
    if behavior_locks:
        system_parts.append("")
        system_parts.append("## 行为锁（角色硬约束，违反即为 OOC）")
        for line in behavior_locks.strip().split("\n"):
            line = line.strip()
            if line:
                system_parts.append(f"- {line}")

    # 高级设置
    advanced = writing_config.get("advanced", {})
    if advanced:
        adv_parts = []
        if advanced.get("natural_dialogue"):
            adv_parts.append("对话要口语化自然，每人口吻有差异，带个人毛边")
        if advanced.get("no_useless_details"):
            adv_parts.append("所有环境描写必须服务情节，不要无用的装饰性细节")
        max_env = advanced.get("max_env_sentences", 0)
        if max_env:
            adv_parts.append(f"连续环境描写不超过{max_env}句")
        max_inner = advanced.get("max_inner_sentences", 0)
        if max_inner:
            adv_parts.append(f"每页内心戏不超过{max_inner}句")
        if adv_parts:
            system_parts.append("")
            system_parts.append("## 高级控制")
            for p in adv_parts:
                system_parts.append(f"- {p}")

    # 故事记忆（已有的事实记录）
    if memories:
        system_parts.append("")
        system_parts.append("## 当前故事已发生的事实（请保持一致性）")
        for m in memories:
            system_parts.append(f"- （第{m['chapter_number']}章）{m['fact']}")

    # 最近章节摘要
    if recent_chapters:
        system_parts.append("")
        system_parts.append("## 最近章节回顾")
        for ch in recent_chapters:
            system_parts.append(f"- 第{ch['chapter_number']}章《{ch['title']}》：{ch['summary']}")

    # 上一章结尾原文（确保连贯衔接）
    if prev_ending:
        system_parts.append("")
        system_parts.append("## 上一章结尾原文（你必须从这里自然衔接，不要重复也不跳跃）")
        system_parts.append(prev_ending)

    system_prompt = "\n".join(system_parts)

    # User message —— 明确告诉它现在要写哪一章
    user_parts = []
    if outline:
        user_parts.append(f"## 本章细纲 — 第{outline['chapter_number']}章")
        if outline.get("title"):
            user_parts.append(f"标题：{outline['title']}")
        if outline.get("outline_content"):
            user_parts.append(f"内容概要：{outline['outline_content']}")
        if outline.get("word_target"):
            user_parts.append(f"目标字数：{outline['word_target']}字")
        # 结构化细纲字段
        outline_fields = [
            ("矛盾", "conflict"),
            ("爽点", "excitement"),
            ("钩子", "hook"),
            ("故事线", "storyline"),
            ("伏笔", "foreshadowing"),
            ("回收伏笔", "foreshadowing_payoff"),
        ]
        for label, key in outline_fields:
            if outline.get(key):
                user_parts.append(f"{label}：{outline[key]}")
    else:
        user_parts.append(f"请根据已有故事上下文，继续写出下一章内容。")

    user_parts.append("")
    user_parts.append("现在，请直接写出本章正文。")

    user_prompt = "\n".join(user_parts)

    return system_prompt, user_prompt
